<?php

declare(strict_types=1);
require_once dirname(__DIR__) . '/lib/workflow.php';
$input=[]; $role=''; $session='';
try {
    $input=CES\jsonObject((string)stream_get_contents(STDIN));
    $role=(string)($input['agent_type'] ?? '');
    if (!in_array($role,CES\ROLES,true) || $role==='engineering-orchestrator') exit(0);
    $session=CES\requireText($input['session_id'] ?? null,'session_id',300);
    $report=CES\decodeReport((string)($input['last_assistant_message'] ?? ''));
    CES\recordReport($session,$role,(string)($input['agent_id'] ?? 'unknown'),$report);
    exit(0);
} catch (Throwable $e) {
    try { if ($session!=='' && in_array($role,CES\ROLES,true)) CES\markInvalid($session,$role,$e->getMessage()); } catch (Throwable $ignored) {}
    if (($input['stop_hook_active'] ?? false)===true) {
        CES\output(['systemMessage'=>'CES report rejected after one repair attempt. The task gate remains BLOCKED: '.$e->getMessage()]); exit(0);
    }
    CES\output(['decision'=>'block','reason'=>'CES handoff is invalid: '.$e->getMessage().'. Return the role JSON contract. If evidence is unavailable, return BLOCKED instead of claiming success.']);
}
