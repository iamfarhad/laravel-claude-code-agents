<?php

declare(strict_types=1);
require_once dirname(__DIR__) . '/lib/policy.php';
try {
    $input=CES\jsonObject((string)stream_get_contents(STDIN));
    $role=$input['agent_type'] ?? '';
    // Unknown non-CES subagents are outside this package's authority.
    if (!in_array($role,CES\ROLES,true)) exit(0);
    $session=CES\requireText($input['session_id'] ?? null,'session_id',300);
    $cwd=CES\safePath(CES\requireText($input['cwd'] ?? null,'cwd'));
    if ($cwd!==CES\root()) throw new RuntimeException('Start the CES session from the repository root; nested CWDs and other worktrees are not supported by this installation.');
    $tool=CES\requireText($input['tool_name'] ?? null,'tool_name',200);
    $args=$input['tool_input'] ?? null;
    if (!is_array($args)) throw new RuntimeException('Missing tool input.');
    if ($tool==='Bash') {
        if (($args['run_in_background'] ?? false)===true) throw new RuntimeException('Broker calls must run in the foreground.');
        $request=CES\parseBrokerCommand(CES\requireText($args['command'] ?? null,'command',2097152));
        CES\authorizeAction($role,$request,$session);
        unset($args['dangerouslyDisableSandbox']);
        $ticket=CES\issueTicket($request,$role,$session,(string)($input['agent_id'] ?? 'main'));
        $args['command']=escapeshellarg(PHP_BINARY).' '.escapeshellarg(CES\root().'/scripts/claude/bin/ces.php').' --ticket '.$ticket;
        CES\output(['hookSpecificOutput'=>['hookEventName'=>'PreToolUse','updatedInput'=>$args]]); exit(0);
    }
    if (in_array($tool,['Write','Edit'],true)) {
        CES\authorizeWrite($role,CES\requireText($args['file_path'] ?? null,'file_path'),$session); exit(0);
    }
    if (in_array($tool,['Read','Grep','Glob'],true)) {
        $path=$args['file_path'] ?? $args['path'] ?? CES\root();
        CES\authorizeRead((string)$path); exit(0);
    }
    if ($tool==='Agent') {
        if ($role!=='engineering-orchestrator' || !in_array($args['subagent_type'] ?? '',array_diff(CES\ROLES,['engineering-orchestrator']),true)) throw new RuntimeException('Only the main orchestrator may delegate to a listed CES specialist.');
        if (!CES\taskExists($session)) throw new RuntimeException('No CES task is open. Pre-task MR/config preflight must be performed directly by engineering-orchestrator; do not delegate a specialist until task_open succeeds.');
        if (in_array($args['subagent_type'],CES\DEVELOPERS,true)) CES\implementationGate($session);
        exit(0);
    }
    if (str_starts_with($tool,'mcp__signoz__')) {
        $allowed=CES\config()['signoz_read_tools'] ?? [];
        if (!in_array($tool,$allowed,true)) throw new RuntimeException('SigNoz tool is not explicitly allowlisted as read-only by a human.');
        if (!preg_match('/\Amcp__signoz__(?:signoz_)?(?:get|list|query|search|fetch|aggregate|check)[A-Za-z0-9_]*\z/',$tool)) throw new RuntimeException('Only read/query SigNoz tools are supported.');
        exit(0);
    }
    throw new RuntimeException('Tool is not part of the CES role contract.');
} catch (Throwable $e) {
    fwrite(STDERR,'CES_DENIED: '.$e->getMessage()."\n"); exit(2);
}
