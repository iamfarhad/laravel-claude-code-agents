<?php

declare(strict_types=1);
require_once dirname(__DIR__) . '/lib/workflow.php';
$input=[];
try {
    $input=CES\jsonObject((string)stream_get_contents(STDIN));
    $session=(string)($input['session_id'] ?? '');
    if ($session==='' || !CES\taskExists($session)) exit(0);

    // Claude Code Stop hooks expose in-flight background work. A non-empty
    // background_tasks array means the main session is paused waiting for
    // background work to wake it back up, not actually completing the CES task.
    // Do not force a terminal ces-result during that pause.
    if (array_key_exists('background_tasks',$input)) {
        if (!is_array($input['background_tasks'])) throw new RuntimeException('Invalid background_tasks hook input.');
        if ($input['background_tasks']!==[]) exit(0);
    }

    $message=(string)($input['last_assistant_message'] ?? '');
    // Human-readable console summary is allowed; one machine-readable ending is required.
    if (!preg_match('/```ces-result\s*\R([\s\S]*?)\R```\s*\z/',$message,$m)) throw new RuntimeException('End the task response with a ces-result JSON block.');
    $r=CES\jsonObject($m[1]);
    if (($r['task_id'] ?? '')!==CES\loadTask($session)['task_id']) throw new RuntimeException('Final result has the wrong task ID.');
    if (in_array($r['status'] ?? '',['BLOCKED','HUMAN_ESCALATION_REQUIRED'],true)) exit(0);
    $f=CES\readJson(CES\sessionDir($session).'/finalization.json');
    if (!in_array($r['status'] ?? '',['READY_FOR_HUMAN_REVIEW','REVIEW_DELIVERED'],true) || $r['status']!==$f['status'] || !CES\sameHash(CES\workspaceDigest(),$f['workspace_digest'] ?? null)) throw new RuntimeException('No current broker finalization supports this completion claim.');
    // Re-check receipts as well: a later rejected report must invalidate an old completion.
    CES\finalizeTask($session);
    exit(0);
} catch (Throwable $e) {
    if (($input['stop_hook_active'] ?? false)===true) {
        CES\output(['systemMessage'=>'CES_FINAL_GATE_BLOCKED: '.$e->getMessage().'. This task must not be treated as complete.']); exit(0);
    }
    CES\output(['decision'=>'block','reason'=>'CES final gate: '.$e->getMessage().'. Report BLOCKED honestly or complete the missing gates; do not repeat indefinitely.']);
}
