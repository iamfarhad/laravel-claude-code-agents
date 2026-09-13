<?php

declare(strict_types=1);
require_once dirname(__DIR__) . '/lib/policy.php';
$errors=[]; $warnings=[]; $checked=0;
try {
    $config=CES\config(); $permissions=CES\actionPermissions(); $signozAllowed=$config['signoz_read_tools'] ?? [];
    foreach (CES\ROLES as $role) {
        $path=CES\root().'/.claude/agents/'.$role.'.md';
        if (!is_file($path)) { $errors[]='Missing agent '.$role; continue; }
        $s=(string)file_get_contents($path);
        if (!preg_match('/\A---\R([\s\S]*?)\R---\R/',$s,$m)) { $errors[]='Invalid frontmatter: '.$role; continue; }
        if (!preg_match('/^name: '.preg_quote($role,'/').'$/m',$m[1])) $errors[]='Mismatched name '.$role;
        if (preg_match('/^(memory|hooks|isolation):/m',$m[1])) $errors[]='Unexpected memory/local hooks/isolation: '.$role;
        if (!preg_match('/^model: inherit$/m',$m[1])) $errors[]='Expected inherited model: '.$role;
        if (!in_array($role,array_merge(CES\DEVELOPERS,['product-manager','architect']),true) && preg_match('/^tools:.*\b(Edit|Write)\b/m',$m[1])) $errors[]='Unexpected write tool: '.$role;
        if (!preg_match('/^tools:[ \t]*([^\r\n]+)$/m',$m[1],$t)) { $errors[]='Missing tools list: '.$role; continue; }
        $tools=array_values(array_filter(array_map('trim',explode(',',$t[1])),fn($x)=>$x!==''));
        $body=substr($s,strlen($m[0]));
        // A role's Bash is the broker envelope, so the prompt must not demonstrate an action the
        // broker denies to that role: the agent would follow the example straight into a denial.
        if (in_array('Bash',$tools,true) && preg_match_all('/"action"[ \t]*:[ \t]*"([a-z_]+)"/',$body,$acts)) {
            foreach (array_unique($acts[1]) as $action) if (!in_array($role,$permissions[$action] ?? [],true)) $errors[]="Prompt of {$role} demonstrates broker action '{$action}', which the broker denies to that role";
        }
        // A tools allowlist hides every MCP tool that is not listed. Claude Code accepts the server-level
        // form (mcp__signoz or mcp__signoz__*) in agent frontmatter; that form is NOT read-only by itself -
        // the PreToolUse hook is what restricts calls to the exact names in signoz_read_tools.
        $listedSignoz=false;
        foreach ($tools as $tool) {
            if (!str_starts_with($tool,'mcp__')) continue;
            if ($tool!=='mcp__signoz' && !str_starts_with($tool,'mcp__signoz__')) { $errors[]="Agent {$role} lists MCP tool {$tool}; only SigNoz read tools are part of the CES role contract"; continue; }
            $listedSignoz=true;
            if (in_array($tool,['mcp__signoz','mcp__signoz__*'],true)) { if (!$signozAllowed) $warnings[]="Agent {$role} exposes the SigNoz server, but config signoz_read_tools is empty, so the hook denies every call."; continue; }
            if (!in_array($tool,$signozAllowed,true)) $errors[]="Agent {$role} lists SigNoz tool {$tool}, which is not allowlisted in config signoz_read_tools";
        }
        if (!$listedSignoz && preg_match('/SigNoz/i',$body)) $warnings[]="Agent {$role} may use SigNoz evidence, but its tools frontmatter lists no SigNoz entry, so telemetry stays unavailable to it until a human adds mcp__signoz__* there (see setup/SIGNOZ_SETUP.md).";
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
    if (empty(CES\config()['confluence_hosts'])) $warnings[]='PRD import from a Confluence URL is disabled until confluence_hosts is configured; file exports still import.';
    CES\output(['status'=>$errors?'FAIL':'PASS','version'=>CES\VERSION,'agent_files_checked'=>$checked,'php_files_linted'=>$linted,'errors'=>$errors,'warnings'=>$warnings,'scope'=>'Local static/configuration checks only; not a live Claude/provider/production integration test.']);
    exit($errors?2:0);
} catch (Throwable $e) { CES\output(['status'=>'FAIL','errors'=>[$e->getMessage()]]); exit(2); }
