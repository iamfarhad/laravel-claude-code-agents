<?php

declare(strict_types=1);
require_once dirname(__DIR__) . '/lib/policy.php';
require_once dirname(__DIR__) . '/lib/mr.php';

try {
    if (count($argv)!==3 || $argv[1]!=='--ticket' || !preg_match('/\A[a-f0-9]{64}\z/',$argv[2])) throw new RuntimeException('This broker accepts only one-use hook-issued tickets. Submit JSON through the documented CES_REQUEST heredoc in Claude Code.');
    $path=CES\safePath(CES\root().'/.claude/engineering-system/runtime/tickets/'.$argv[2].'.json',true);
    // Rename atomically before consuming, so the same ticket cannot be replayed.
    $used=$path.'.used-'.bin2hex(random_bytes(8));
    if (!rename($path,$used)) throw new RuntimeException('Ticket already consumed.');
    try { $ticket=CES\readJson($used); } finally { unlink($used); }
    if (time()-($ticket['issued_at'] ?? 0)>300 || ($ticket['issued_at'] ?? PHP_INT_MAX)>time()+5) throw new RuntimeException('Ticket expired. Retry the original broker call.');
    if (!CES\sameHash(hash_file('sha256',CES\root().'/.claude/engineering-system/config.json'),$ticket['config_sha256'] ?? null)) throw new RuntimeException('Configuration changed since authorization.');
    $request=$ticket['request']; $session=$ticket['session_id']; $role=$ticket['role'];
    CES\authorizeAction($role,$request,$session);
    $action=$request['action'];
    if ($action==='task_open') $result=CES\openTask($session,$request);
    elseif ($action==='task_status') {
        $receipts=[];
        foreach (CES\ROLES as $name) { $p=CES\receiptPath($session,$name); if (is_file($p)) $receipts[$name]=CES\readJson($p); }
        $result=['task'=>CES\loadTask($session),'workspace_digest'=>CES\workspaceDigest(),'receipts'=>$receipts];
    } elseif ($action==='validate_prd') $result=CES\currentPrd(CES\loadTask($session));
    elseif ($action==='fetch_mr') $result=CES\fetchMr(CES\requireText($request['mr_url'] ?? null,'mr_url',1000));
    elseif ($action==='context') {
        $kind=$request['kind'] ?? 'status';
        $args=match($kind) {
            'status'=>['status','--porcelain=v1'],
            'head'=>['rev-parse','--verify','HEAD'],
            'log'=>['log','-10','--format=%H %s'],
            'diff'=>['diff','--no-ext-diff','--no-textconv','--no-color', $request['base_sha'] ?? 'HEAD','--'],
            default=>throw new RuntimeException('Unknown context kind.'),
        };
        if (isset($request['base_sha']) && !preg_match('/\A[a-f0-9]{40,64}\z/',$request['base_sha'])) throw new RuntimeException('base_sha must be a full immutable commit hash.');
        $result=CES\git($args);
    } elseif ($action==='run_check') {
        $task=CES\loadTask($session); $c=CES\config()['checks'][$request['name']];
        $before=CES\workspaceDigest();
        $env=['PATH'=>(string)getenv('PATH'),'LANG'=>'C.UTF-8','HOME'=>CES\sessionDir($session).'/test-home','TMPDIR'=>CES\sessionDir($session).'/test-tmp'];
        foreach (['HOME','TMPDIR'] as $key) if (!is_dir($env[$key]) && !mkdir($env[$key],0700,true) && !is_dir($env[$key])) throw new RuntimeException('Cannot create isolated runtime directories.');
        foreach ($c['env'] as $k=>$v) {
            if (!is_string($k) || !is_string($v) || in_array($k,['PATH','HOME','LD_PRELOAD','LD_LIBRARY_PATH','DYLD_INSERT_LIBRARIES','BASH_ENV','ENV'],true)) throw new RuntimeException('Unsupported preset environment override.');
            $env[$k]=$v;
        }
        $r=CES\process($c['argv'],'',min(600,max(1,(int)($c['timeout_seconds'] ?? 120))),2097152,$env);
        $after=CES\workspaceDigest(); $id=bin2hex(random_bytes(16));
        $log=CES\redact($r['stdout']."\nSTDERR:\n".$r['stderr']);
        CES\atomicWrite(CES\sessionDir($session).'/checks/'.$id.'.log',$log);
        $result=['id'=>$id,'task_id'=>$task['task_id'],'role'=>$role,'kind'=>$c['kind'] ?? 'test','name'=>$request['name'],'status'=>$r['exit_code']===0 && !$r['truncated'] && !$r['timed_out'] && $before===$after?'PASS':'FAIL','exit_code'=>$r['exit_code'],'timed_out'=>$r['timed_out'],'truncated'=>$r['truncated'],'duration_ms'=>$r['duration_ms'],'workspace_digest'=>$after,'workspace_mutated'=>$before!==$after,'log_sha256'=>hash('sha256',$log),'log_path'=>CES\relative(CES\sessionDir($session).'/checks/'.$id.'.log'),'command'=>$c['argv'],'completed_at'=>gmdate('c')];
        CES\atomicWrite(CES\sessionDir($session).'/checks/'.$id.'.json',CES\encode($result));
        $result['output']=$log;
    } elseif ($action==='publish_review') {
        $task=CES\loadTask($session); $digest=CES\workspaceDigest();
        $peer=CES\requireReceipt($session,'peer-reviewer',['PASS','FAIL'],$digest);
        $payload=['mr_url'=>$task['mr_url'],'reviewed_head_sha'=>$task['reviewed_head_sha'],'review_status'=>$peer['report']['status'],'review_summary'=>$peer['report']['summary'],'comments'=>$peer['report']['publishable_comments'] ?? []];
        if (isset($request['dry_run']) && !is_bool($request['dry_run'])) throw new RuntimeException('dry_run must be boolean.');
        $result=CES\publishReview($payload,$request['dry_run'] ?? false);
        $result['workspace_digest']=$digest; $result['peer_report_sha256']=hash('sha256',CES\encode($peer['report']));
        CES\atomicWrite(CES\sessionDir($session).'/publication.json',CES\encode($result));
    } elseif ($action==='finalize') {
        $t=CES\loadTask($session);
        if ($t['mr_url']!==null) CES\assertMrHead(CES\mrTarget($t['mr_url']),$t['reviewed_head_sha']);
        $result=CES\finalizeTask($session);
    } else throw new RuntimeException('Unknown broker action.');
    CES\output($result);
    exit(in_array($result['status'] ?? '',['BLOCKED','FAIL'],true)?2:0);
} catch (Throwable $e) { CES\output(['status'=>'BLOCKED','error'=>CES\redact($e->getMessage())]); exit(2); }
