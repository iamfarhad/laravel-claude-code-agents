<?php

declare(strict_types=1);
namespace CES;
require_once __DIR__ . '/contracts.php';
require_once __DIR__ . '/process.php';

const READ_ONLY_FLOWS = ['peer-review','tech-lead-review','engineering-manager-review','architecture','release'];
const FLOWS = ['feature','production-bug','development-bug','peer-review','tech-lead-review','engineering-manager-review','incident','performance','security','refactor','upgrade','architecture','release','ci-failure'];
function openTask(string $session, array $request): array {
    $id=requireText($request['task_id'] ?? null,'task_id',100);
    if (!preg_match('/\A[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\z/',$id)) throw new \RuntimeException('Invalid task_id.');
    $flow=$request['workflow'] ?? '';
    if (!in_array($flow,FLOWS,true)) throw new \RuntimeException('Unsupported workflow.');
    if (taskExists($session)) {
        $existing=loadTask($session);
        if ($existing['task_id']===$id) {
            $request['risk_gates']=array_values(array_unique(array_merge($request['risk_gates'] ?? [],match($flow) {'performance'=>['performance-reviewer'],'security'=>['security-reviewer'],'incident','upgrade'=>['release-reviewer'],default=>[]})));
            foreach (['workflow','prd_path','mr_url','reviewed_head_sha','risk_gates'] as $key) {
                if (($request[$key] ?? ($key==='risk_gates'?[]:null))!==($existing[$key] ?? null)) throw new \RuntimeException('Task already exists with different scope; start a new session.');
            }
            return $existing;
        }
        throw new \RuntimeException('One task per session. Start a new Claude session for a different task.');
    }
    $prd=$request['prd_path'] ?? null;
    if (!in_array($flow,READ_ONLY_FLOWS,true)) {
        $p=safePath(requireText($prd,'prd_path'));
        if (!within($p,root().'/docs/prd') || !str_ends_with($p,'.md')) throw new \RuntimeException('PRD must be a markdown file under docs/prd/.');
        $prd=relative($p);
    }
    $gates=$request['risk_gates'] ?? [];
    if (!is_array($gates) || !array_is_list($gates) || array_diff($gates,REVIEWERS)) throw new \RuntimeException('Invalid specialist gates.');
    $gates=array_merge($gates,match($flow) {'performance'=>['performance-reviewer'],'security'=>['security-reviewer'],'incident','upgrade'=>['release-reviewer'],default=>[]});
    $mr=$request['mr_url'] ?? null;
    $sha=$request['reviewed_head_sha'] ?? null;
    if ($mr!==null) {
        requireText($mr,'mr_url',1000);
        if (!is_string($sha) || !preg_match('/\A[a-f0-9]{40,64}\z/',$sha)) throw new \RuntimeException('An existing MR needs the exact reviewed_head_sha. Fetch metadata before opening the task.');
    }
    $task=['task_id'=>$id,'workflow'=>$flow,'prd_path'=>$prd,'mr_url'=>$mr,'reviewed_head_sha'=>$sha,'risk_gates'=>array_values(array_unique($gates)),'base_sha'=>headSha(),'opened_at'=>gmdate('c'),'repair_attempts'=>0];
    saveTask($session,$task);
    return $task;
}
function receiptPath(string $session,string $role): string {
    if (!in_array($role,ROLES,true)) throw new \RuntimeException('Unknown role.');
    return sessionDir($session).'/receipts/'.$role.'.json';
}
function getReceipt(string $session,string $role): array { return readJson(receiptPath($session,$role)); }
function currentPrd(array $task): array {
    $r=validatePrd(requireText($task['prd_path'] ?? null,'task PRD'));
    if ($r['status']!=='PASS') throw new \RuntimeException('PRD gate: '.implode('; ',$r['errors']));
    return $r;
}
function requireReceipt(string $session,string $role,array $statuses, ?string $digest=null, ?string $prdHash=null): array {
    $r=getReceipt($session,$role); $task=loadTask($session);
    if (($r['valid'] ?? false)!==true || ($r['task_id'] ?? '')!==$task['task_id'] || !in_array($r['report']['status'] ?? '',$statuses,true)) throw new \RuntimeException('Gate not satisfied: '.$role);
    if ($digest!==null && !sameHash($digest,$r['workspace_digest'] ?? null)) throw new \RuntimeException('Stale workspace evidence: '.$role);
    if ($prdHash!==null && !sameHash($prdHash,$r['prd_sha256'] ?? null)) throw new \RuntimeException('Stale PRD approval: '.$role);
    return $r;
}
function implementationGate(string $session): array {
    $task=loadTask($session);
    if (in_array($task['workflow'],READ_ONLY_FLOWS,true)) throw new \RuntimeException('Review-only tasks may not modify implementation.');
    if (($task['repair_attempts'] ?? 0)>=3) throw new \RuntimeException('Autonomous implementation budget exhausted; human escalation required.');
    $prd=currentPrd($task);
    requireReceipt($session,'product-manager',['READY_FOR_ENGINEERING'],null,$prd['sha256']);
    requireReceipt($session,'prd-reviewer',['PASS'],null,$prd['sha256']);
    if (in_array($task['workflow'],['production-bug','development-bug'],true)) requireReceipt($session,'qa-support',['VALID_BUG']);
    if ($task['workflow']==='incident') requireReceipt($session,'incident-investigator',['INVESTIGATED']);
    return $prd;
}
function validateAcResults(string $session,array $report,array $prd,string $digest): void {
    $results=$report['ac_results'] ?? null;
    if (!is_array($results) || !array_is_list($results)) throw new \RuntimeException('ac_results must be an array.');
    $seen=[];
    foreach ($results as $row) {
        $id=$row['id'] ?? '';
        if (!in_array($id,$prd['ac_ids'],true) || isset($seen[$id])) throw new \RuntimeException('Unknown or duplicate AC result: '.$id);
        $seen[$id]=true;
        if (($row['status'] ?? '')!=='PASS') throw new \RuntimeException('All required ACs must be PASS.');
        requireText($row['assertion'] ?? null,'AC assertion');
        $run=requireText($row['check_id'] ?? null,'check_id',100);
        if (!preg_match('/\A[a-f0-9]{32}\z/',$run)) throw new \RuntimeException('Invalid check receipt ID.');
        $ev=readJson(sessionDir($session).'/checks/'.$run.'.json');
        if (($ev['task_id'] ?? null)!==loadTask($session)['task_id'] || !in_array($ev['role'] ?? '',TESTERS,true) || ($ev['kind'] ?? '')!=='test' || ($ev['status'] ?? '')!=='PASS' || !sameHash($digest,$ev['workspace_digest'] ?? null)) throw new \RuntimeException('AC evidence must reference an independent, passing test run for this workspace.');
    }
    if (array_diff($prd['ac_ids'],array_keys($seen))) throw new \RuntimeException('One or more required ACs are missing.');
}
function recordReport(string $session,string $role,string $agentId,array $report): array {
    validateReportShape($report,$role); $task=loadTask($session);
    if ($report['task_id']!==$task['task_id']) throw new \RuntimeException('Report belongs to a different task.');
    $digest=workspaceDigest(); $prdHash=null;
    if (is_file(receiptPath($session,$role))) {
        $previous=getReceipt($session,$role);
        if (($previous['valid'] ?? false)===true && ($previous['agent_id'] ?? '')===$agentId && ($previous['report'] ?? null)===$report && sameHash($digest,$previous['workspace_digest'] ?? null)) return $previous;
    }
    $success=in_array($report['status'],['PASS','IMPLEMENTED','PROPOSED','READY_FOR_ENGINEERING','INVESTIGATED'],true);
    if ($role==='product-manager' && $report['status']==='READY_FOR_ENGINEERING') {
        $prd=currentPrd($task); $prdHash=$prd['sha256'];
        if (($report['prd_path'] ?? '')!==$task['prd_path']) throw new \RuntimeException('PRD path differs from task.');
    }
    if ($role==='prd-reviewer' && $report['status']==='PASS') {
        $prd=currentPrd($task); $prdHash=$prd['sha256'];
        requireReceipt($session,'product-manager',['READY_FOR_ENGINEERING'],null,$prdHash);
    }
    if (in_array($role,DEVELOPERS,true) && $report['status']==='IMPLEMENTED') {
        $prd=implementationGate($session); $prdHash=$prd['sha256'];
        $mapping=$report['ac_mapping'] ?? [];
        foreach ($prd['ac_ids'] as $id) if (!is_array($mapping[$id] ?? null) || empty($mapping[$id]['implementation']) || empty($mapping[$id]['tests'])) throw new \RuntimeException('Incomplete implementation/test mapping: '.$id);
        requireText($report['root_cause_or_requirement'] ?? null,'root_cause_or_requirement');
    }
    if (in_array($role,TESTERS,true) && $report['status']==='PASS' && $task['prd_path']!==null) {
        $prd=currentPrd($task); $prdHash=$prd['sha256']; validateAcResults($session,$report,$prd,$digest);
    }
    if ($role==='peer-reviewer' && $task['mr_url']!==null && in_array($report['status'],['PASS','FAIL'],true)) {
        if (($report['reviewed_head_sha'] ?? '')!==$task['reviewed_head_sha']) throw new \RuntimeException('Peer review must bind to the exact task SHA.');
        if (headSha()!==$task['reviewed_head_sha']) throw new \RuntimeException('Checkout does not match reviewed MR head.');
        $r=git(['status','--porcelain=v1','--untracked-files=no']);
        if ($r['exit_code']!==0 || trim($r['stdout'])!=='') throw new \RuntimeException('Commit-bound MR review requires a clean tracked checkout.');
        if (!isset($report['publishable_comments']) || !is_array($report['publishable_comments'])) throw new \RuntimeException('Peer review needs publishable_comments.');
    }
    if ($role==='mr-review-publisher' && $report['status']!=='BLOCKED') {
        $p=readJson(sessionDir($session).'/publication.json');
        if (($p['status'] ?? '')!==$report['status'] || !sameHash($digest,$p['workspace_digest'] ?? null)) throw new \RuntimeException('Publication is not supported by broker evidence.');
    }
    $receipt=['valid'=>true,'task_id'=>$task['task_id'],'role'=>$role,'agent_id'=>$agentId,'recorded_at'=>gmdate('c'),'workspace_digest'=>$digest,'prd_sha256'=>$prdHash,'report'=>$report];
    atomicWrite(receiptPath($session,$role),encode($receipt));
    if (in_array($role,DEVELOPERS,true) && in_array($report['status'],['IMPLEMENTED','FAIL'],true)) { $task['repair_attempts']++; saveTask($session,$task); }
    return $receipt;
}
function markInvalid(string $session,string $role,string $error): void {
    if (!taskExists($session)) return;
    atomicWrite(receiptPath($session,$role),encode(['valid'=>false,'task_id'=>loadTask($session)['task_id'],'error'=>$error,'recorded_at'=>gmdate('c')]));
}
function derivedRiskGates(array $task): array {
    $gates=$task['risk_gates']; $r=git(['diff','--no-ext-diff','--no-textconv','--name-only',$task['base_sha'],'--']);
    if ($r['exit_code']!==0 || $r['truncated']) throw new \RuntimeException('Cannot determine changed-file risk.');
    $untracked=git(['ls-files','--others','--exclude-standard']);
    if ($untracked['exit_code']!==0 || $untracked['truncated']) throw new \RuntimeException('Cannot inspect untracked changes.');
    $rawPaths=explode("\n",$r['stdout']."\n".$untracked['stdout']);
    $applicationPaths=array_filter($rawPaths,function($path) {
        foreach (['.claude/','scripts/claude/','docs/ai/claude-engineering-system/'] as $prefix) if (str_starts_with($path,$prefix)) return false;
        return trim($path)!=='';
    });
    $paths=implode("\n",$applicationPaths);
    foreach (config()['risk_patterns'] ?? [] as $role=>$pattern) {
        if (!in_array($role,REVIEWERS,true) || !is_string($pattern)) throw new \RuntimeException('Invalid risk policy.');
        $match=preg_match($pattern,$paths); if ($match===false) throw new \RuntimeException('Invalid risk regex.');
        if ($match===1) $gates[]=$role;
    }
    return array_values(array_unique($gates));
}
function finalizeTask(string $session): array {
    $t=loadTask($session); $digest=workspaceDigest(); $gates=derivedRiskGates($t);
    $readOnly=in_array($t['workflow'],READ_ONLY_FLOWS,true);
    if ($readOnly) {
        $primary=match($t['workflow']) {'peer-review'=>'peer-reviewer','tech-lead-review'=>'tech-lead-reviewer','engineering-manager-review'=>'engineering-manager-reviewer','architecture'=>'architect','release'=>'release-reviewer'};
        requireReceipt($session,$primary,['PASS','FAIL','PROPOSED'],$digest);
        foreach ($t['risk_gates'] as $role) requireReceipt($session,$role,['PASS','FAIL'],$digest);
    } else {
        $prd=currentPrd($t);
        requireReceipt($session,'product-manager',['READY_FOR_ENGINEERING'],null,$prd['sha256']);
        requireReceipt($session,'prd-reviewer',['PASS'],null,$prd['sha256']);
        $dev=match($t['workflow']) {'incident'=>'hotfix-developer','upgrade'=>'upgrade-developer',default=>'developer'};
        requireReceipt($session,$dev,['IMPLEMENTED'],$digest,$prd['sha256']);
        requireReceipt($session,'peer-reviewer',['PASS'],$digest);
        foreach ($gates as $role) requireReceipt($session,$role,['PASS'],$digest);
        $tester=in_array($t['workflow'],['refactor','upgrade'],true)?'regression-tester':'tester';
        requireReceipt($session,$tester,['PASS'],$digest,$prd['sha256']);
        if (in_array($t['workflow'],['production-bug','development-bug'],true)) requireReceipt($session,'qa-support',['VALID_BUG']);
    }
    if ($t['mr_url']!==null && is_file(receiptPath($session,'peer-reviewer'))) {
        $peer=getReceipt($session,'peer-reviewer');
        $p=readJson(sessionDir($session).'/publication.json');
        if (!in_array($p['status'] ?? '',['PUBLISHED','PUBLISHED_WITH_FALLBACK','ALREADY_PUBLISHED'],true) || !sameHash(hash('sha256',encode($peer['report'])),$p['peer_report_sha256'] ?? null) || ($p['reviewed_head_sha'] ?? '')!==$t['reviewed_head_sha']) throw new \RuntimeException('MR publication gate is incomplete or stale.');
    }
    $result=['status'=>$readOnly?'REVIEW_DELIVERED':'READY_FOR_HUMAN_REVIEW','task_id'=>$t['task_id'],'workspace_digest'=>$digest,'risk_gates'=>$gates,'at'=>gmdate('c'),'merge_authorized'=>false,'deploy_authorized'=>false];
    atomicWrite(sessionDir($session).'/finalization.json',encode($result)); return $result;
}
