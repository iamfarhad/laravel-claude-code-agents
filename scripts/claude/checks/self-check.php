<?php

declare(strict_types=1);
require_once dirname(__DIR__) . '/lib/workflow.php';
$errors=[]; $warnings=[]; $checked=0;
try {
    CES\config();
    foreach (CES\ROLES as $role) {
        $path=CES\root().'/.claude/agents/'.$role.'.md';
        if (!is_file($path)) { $errors[]='Missing agent '.$role; continue; }
        $s=(string)file_get_contents($path);
        if (!preg_match('/\A---\R([\s\S]*?)\R---\R/',$s,$m)) { $errors[]='Invalid frontmatter: '.$role; continue; }
        if (!preg_match('/^name: '.preg_quote($role,'/').'$/m',$m[1])) $errors[]='Mismatched name '.$role;
        if (preg_match('/^(memory|hooks|isolation):/m',$m[1])) $errors[]='Unexpected memory/local hooks/isolation: '.$role;
        if (!preg_match('/^model: inherit$/m',$m[1])) $errors[]='Expected inherited model: '.$role;
        if (!in_array($role,array_merge(CES\DEVELOPERS,['product-manager','architect']),true) && preg_match('/^tools:.*\b(Edit|Write)\b/m',$m[1])) $errors[]='Unexpected write tool: '.$role;
        $checked++;
    }
    $fragment=CES\readJson(CES\root().'/.claude/engineering-system/settings.fragment.json');
    foreach (['PreToolUse','SubagentStop','Stop'] as $event) if (empty($fragment['hooks'][$event])) $errors[]='Missing hook event: '.$event;
    $it=new RecursiveIteratorIterator(new RecursiveDirectoryIterator(CES\root().'/scripts/claude',FilesystemIterator::SKIP_DOTS));
    $linted=0;
    foreach ($it as $f) if ($f->isFile() && $f->getExtension()==='php') {
        $r=CES\process([PHP_BINARY,'-l',$f->getPathname()]);
        if ($r['exit_code']!==0) $errors[]='PHP lint: '.$f->getPathname();
        $linted++;
    }
    $settings=CES\root().'/.claude/settings.json';
    if (is_file($settings)) {
        $installed=CES\readJson($settings); $flat=json_encode($installed['hooks'] ?? []);
        foreach (['pre-tool.php','output-gate.php','final-gate.php'] as $name) if (!str_contains($flat,$name)) $errors[]='Installed settings missing '.$name;
    } else $warnings[]='Package mode: hooks are not installed into this directory.';
    if (!CES\config()['execution_isolated'] || !CES\config()['checks']) $warnings[]='Check execution is intentionally disabled until human isolation and test presets are configured.';
    if (!CES\config()['allowed_hosts']) $warnings[]='MR fetch/review publication is disabled until allowed_hosts and CLI authentication are configured.';
    if (!CES\config()['signoz_read_tools']) $warnings[]='SigNoz tools are denied until read-only names are explicitly configured.';
    CES\output(['status'=>$errors?'FAIL':'PASS','version'=>CES\VERSION,'agent_files_checked'=>$checked,'php_files_linted'=>$linted,'errors'=>$errors,'warnings'=>$warnings,'scope'=>'Local static/configuration checks only; not a live Claude/provider/production integration test.']);
    exit($errors?2:0);
} catch (Throwable $e) { CES\output(['status'=>'FAIL','errors'=>[$e->getMessage()]]); exit(2); }
