<?php

declare(strict_types=1);
namespace CES;
require_once __DIR__ . '/workflow.php';

function parseBrokerCommand(string $command): array {
    if (!preg_match("/\\Aphp scripts\\/claude\\/bin\\/ces\\.php <<'CES_REQUEST'\\r?\\n([\\s\\S]*?)\\r?\\nCES_REQUEST(?:\\r?\\n)?\\z/",$command,$m)) throw new \RuntimeException("Bash is restricted to the exact CES JSON-heredoc broker. Arbitrary shell, interpreters, pipelines and redirects are denied.");
    if (preg_match('/^CES_REQUEST\r?$/m',$m[1])) throw new \RuntimeException('Embedded heredoc delimiter is forbidden.');
    return jsonObject($m[1]);
}
function authorizeAction(string $role,array $request,string $session): void {
    $action=$request['action'] ?? '';
    $permissions=[
        'task_open'=>['engineering-orchestrator'],
        'task_status'=>ROLES,
        'context'=>array_diff(ROLES,['mr-review-publisher']),
        'validate_prd'=>array_diff(ROLES,['mr-review-publisher']),
        'fetch_mr'=>['engineering-orchestrator','peer-reviewer','tech-lead-reviewer','engineering-manager-reviewer'],
        'run_check'=>array_merge(DEVELOPERS,TESTERS,['qa-support','performance-reviewer']),
        'publish_review'=>['mr-review-publisher'],
        'finalize'=>['engineering-orchestrator'],
    ];
    if (!in_array($role,$permissions[$action] ?? [],true)) throw new \RuntimeException('Action not allowed for this role.');
    $keys=match($action) {
        'task_open'=>['action','task_id','workflow','prd_path','mr_url','reviewed_head_sha','risk_gates','base_sha'],
        'context'=>['action','kind','base_sha'],
        'fetch_mr'=>['action','mr_url'],
        'run_check'=>['action','name'],
        'publish_review'=>['action','dry_run'],
        default=>['action'],
    };
    if (array_diff(array_keys($request),$keys)) throw new \RuntimeException('Unknown broker request fields.');
    if (!in_array($action,['task_open','fetch_mr','context'],true) && !taskExists($session)) throw new \RuntimeException('Open a CES task first.');
    if ($action==='run_check') {
        $c=config(); $name=requireText($request['name'] ?? null,'check name',100); $check=$c['checks'][$name] ?? null;
        if (($c['execution_isolated'] ?? false)!==true || !is_array($check) || ($check['trusted'] ?? false)!==true) throw new \RuntimeException('Check execution is disabled until a human configures an isolated, trusted check preset.');
        if (!in_array($role,$check['roles'] ?? [],true)) throw new \RuntimeException('This role cannot run this check.');
        if (($check['env']['APP_ENV'] ?? '')!=='testing') throw new \RuntimeException('Test presets require APP_ENV=testing; this alone is not isolation.');
        if (in_array($role,DEVELOPERS,true)) implementationGate($session);
    }
}
function authorizeWrite(string $role,string $path,string $session): void {
    $p=safePath($path); $rel=relative($p);
    if (is_file($p) && (($s=stat($p))===false || $s['nlink']>1)) throw new \RuntimeException('Writing hard-linked files is forbidden.');
    if ($role==='product-manager') {
        if (!within($p,root().'/docs/prd') && !within($p,root().'/docs/product')) throw new \RuntimeException('PM may write only product documents.');
        if (!str_ends_with($p,'.md')) throw new \RuntimeException('Product documents must be markdown.');
        return;
    }
    if ($role==='architect') {
        if ((!within($p,root().'/docs/adr') && !within($p,root().'/docs/architecture')) || !str_ends_with($p,'.md')) throw new \RuntimeException('Architect may write only markdown ADR/architecture documents.');
        return;
    }
    if (!in_array($role,DEVELOPERS,true)) throw new \RuntimeException('This role has no repository write permission.');
    foreach (['.claude','.git','.github','scripts/claude','docs/prd','docs/product','docs/adr','docs/architecture','docs/ai/claude-engineering-system'] as $protected) if (within($p,root().'/'.$protected)) throw new \RuntimeException('Protected governance/product path.');
    if (in_array($rel,['CLAUDE.md','claude.md','README.md','.gitignore','.gitmodules','.gitattributes','.gitlab-ci.yml'],true) || preg_match('~(^|/)\.env(?:\.|$)~',$rel)) throw new \RuntimeException('Protected project configuration.');
    implementationGate($session);
}
/**
 * Claude Code persists oversized tool output under its own session directory and then reads
 * it back. That file is this session's OWN authorized broker output, and no CES role can
 * write there, so it stays readable even though it sits outside the repository. Scoped to
 * exactly `<projects>/<slug>/<this session id>/tool-results/`: another session's directory,
 * another project's transcripts and the rest of the host all remain denied. The resolved
 * real path is what gets checked, so a symlink planted there cannot escape the root.
 */
function sessionOutputRoots(?string $transcript): array {
    $candidates=[];
    $home=getenv('HOME');
    if (is_string($home) && $home!=='') $candidates[]=rtrim($home,'/').'/.claude/projects';
    if (is_string($transcript) && $transcript!=='' && !str_contains($transcript,"\0")) {
        $slug=realpath(dirname($transcript));
        if ($slug!==false) $candidates[]=dirname($slug);
    }
    $roots=[];
    foreach ($candidates as $candidate) { $real=realpath($candidate); if ($real!==false) $roots[$real]=true; }
    return array_keys($roots);
}
function readableSessionOutput(string $path, string $session, ?string $transcript): bool {
    if ($path==='' || str_contains($path,"\0") || trim($session)==='') return false;
    $real=realpath($path);
    if ($real===false) return false;
    foreach (sessionOutputRoots($transcript) as $root) {
        if (!within($real,$root)) continue;
        $parts=explode('/',trim(substr($real,strlen($root)),'/'));
        if (count($parts)>=3 && $parts[1]===$session && $parts[2]==='tool-results') return true;
    }
    return false;
}
function authorizeRead(string $path, string $session='', ?string $transcript=null): void {
    if (readableSessionOutput($path,$session,$transcript)) return;
    try { $p=safePath($path); }
    catch (\Throwable $e) { throw new \RuntimeException($e->getMessage().' CES roles read inside the repository; the only exception is this session\'s own persisted tool output.'); }
    $rel=relative($p);
    if (preg_match('~(^|/)(\.env(?:\.[^/]*)?|id_rsa|id_ed25519|credentials(?:\.json)?)$~',$rel) && !str_ends_with($rel,'.env.example')) throw new \RuntimeException('Direct secret-file access is denied.');
    if (within($p,root().'/.claude/engineering-system/runtime/tickets')) throw new \RuntimeException('Broker tickets are not agent-readable artifacts.');
}
function issueTicket(array $request,string $role,string $session,string $agentId): string {
    $token=bin2hex(random_bytes(32));
    $path=root().'/.claude/engineering-system/runtime/tickets/'.$token.'.json';
    atomicWrite($path,encode(['issued_at'=>time(),'request'=>$request,'role'=>$role,'session_id'=>$session,'agent_id'=>$agentId,'config_sha256'=>hash_file('sha256',root().'/.claude/engineering-system/config.json')]));
    return $token;
}
