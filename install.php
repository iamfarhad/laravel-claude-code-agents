<?php

declare(strict_types=1);

// Non-destructive installer. No network, no package-manager hooks, no shell execution.
require_once __DIR__ . '/scripts/claude/lib/common.php';

function installerJson(string $path): stdClass {
    $data=json_decode((string)file_get_contents($path),false,128,JSON_THROW_ON_ERROR);
    if (!$data instanceof stdClass) throw new RuntimeException('Expected a JSON object: '.$path);
    return $data;
}
function canonical(mixed $v): string {
    $normalize=function(mixed $x) use (&$normalize): mixed {
        if ($x instanceof stdClass) { $a=get_object_vars($x); ksort($a); foreach ($a as &$i) $i=$normalize($i); return (object)$a; }
        if (is_array($x)) return array_map($normalize,$x);
        return $x;
    };
    return json_encode($normalize($v),JSON_THROW_ON_ERROR);
}
function mergeSettings(stdClass $current,stdClass $fragment,bool $setAgent,bool $forceAgent,bool $migration): stdClass {
    if (isset($current->hooks) && !$current->hooks instanceof stdClass) throw new RuntimeException('settings.hooks must be an object.');
    $current->hooks ??= new stdClass;
    foreach (get_object_vars($current->hooks) as $event=>$entries) {
        if (!is_array($entries) || !array_is_list($entries)) throw new RuntimeException('Hook entries must be arrays.');
        foreach ($entries as $entry) if (!$entry instanceof stdClass || !is_array($entry->hooks ?? null)) throw new RuntimeException('Malformed existing hook entry.');
    }
    // Retain unrelated hooks, even when they share an event or matcher with CES.
    $owned=['pre-tool.php','output-gate.php','final-gate.php'];
    foreach (get_object_vars($current->hooks) as $event=>$entries) {
        $kept=[];
        foreach ($entries as $entry) {
            $entry->hooks=array_values(array_filter($entry->hooks,function($hook) use ($owned) {
                foreach ($owned as $file) if (($hook->type ?? '')==='command' && ($hook->command ?? '')==='php "${CLAUDE_PROJECT_DIR}/scripts/claude/hooks/'.$file.'"') return false;
                return true;
            }));
            if ($entry->hooks) $kept[]=$entry;
        }
        $current->hooks->$event=$kept;
    }
    foreach (get_object_vars($fragment->hooks) as $event=>$entries) {
        $existing=$current->hooks->$event ?? []; $seen=[];
        foreach (array_merge($existing,$entries) as $entry) $seen[canonical($entry)]=$entry;
        $current->hooks->$event=array_values($seen);
    }
    if ($migration && isset($current->permissions->allow)) {
        if (!is_array($current->permissions->allow)) throw new RuntimeException('permissions.allow must be an array.');
        $old=['Bash(php scripts/claude/mr/publish-review.php *)','Bash(php scripts/claude/mr/publish-review.php)'];
        $current->permissions->allow=array_values(array_diff($current->permissions->allow,$old));
    }
    if ($forceAgent || ($setAgent && !isset($current->agent))) $current->agent='engineering-orchestrator';
    return $current;
}
/** Append only the missing CES exclusion patterns, preserving existing content and order. */
function withManagedExclusions(string $current,array $managed,string $label): string {
    $lines=preg_split('/\R/',$current);
    if ($lines===false) throw new RuntimeException('Could not parse '.$label.'.');
    $normalized=array_map('trim',$lines); $next=rtrim($current,"\r\n");
    foreach ($managed as $pattern) if (!in_array($pattern,$normalized,true)) $next.=($next===''?'':"\n").$pattern;
    if ($next!=='' && !str_ends_with($next,"\n")) $next.="\n";
    return $next;
}
function writeInstall(string $target,string $relative,string $content,int $mode=0644): void {
    $path=CES\safePath($relative,false,$target);
    if (is_file($path) && (($stat=stat($path))===false || $stat['nlink']>1)) throw new RuntimeException('Refusing a multiply-linked target: '.$relative);
    if (!is_dir(dirname($path)) && !mkdir(dirname($path),str_contains($relative,'/backups/')?0700:0755,true) && !is_dir(dirname($path))) throw new RuntimeException('Cannot create target directory.');
    $tmp=tempnam(dirname($path),'.ces-install-');
    if ($tmp===false) throw new RuntimeException('Cannot create staged file.');
    try {
        if (file_put_contents($tmp,$content,LOCK_EX)!==strlen($content) || !chmod($tmp,$mode) || !rename($tmp,$path)) throw new RuntimeException('Failed to install '.$relative);
    } finally { if (is_file($tmp)) unlink($tmp); }
}
try {
    $options=array_slice($argv,1); $flags=[]; $allowHosts=[];
    foreach ($options as $option) {
        if (str_starts_with($option,'--allow-host=')) {
            $host=strtolower(trim(substr($option,13)));
            if ($host==='' || strlen($host)>253 || str_contains($host,'*') || str_contains($host,':') || str_contains($host,'/') || str_contains($host,'\\')) throw new RuntimeException('Invalid --allow-host value; use only an exact hostname such as git.example.com.');
            foreach (explode('.',$host) as $label) if ($label==='' || strlen($label)>63 || !preg_match('/\A[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\z/',$label)) throw new RuntimeException('Invalid --allow-host value; use only an exact hostname such as git.example.com.');
            $allowHosts[]=$host; continue;
        }
        if (!in_array($option,['--apply','--replace-existing','--set-default-agent','--force-default-agent','--add-gitignore','--add-git-exclude'],true)) throw new RuntimeException('Supported options: --apply --replace-existing --set-default-agent --force-default-agent --add-gitignore --add-git-exclude --allow-host=HOST');
        $flags[]=$option;
    }
    $allowHosts=array_values(array_unique($allowHosts)); sort($allowHosts,SORT_STRING);
    $apply=in_array('--apply',$flags,true); $replace=in_array('--replace-existing',$flags,true);
    $set=in_array('--set-default-agent',$flags,true); $force=in_array('--force-default-agent',$flags,true); $addGitignore=in_array('--add-gitignore',$flags,true); $addGitExclude=in_array('--add-git-exclude',$flags,true);
    if ($addGitignore && $addGitExclude) throw new RuntimeException('--add-gitignore and --add-git-exclude are alternatives; choose one. Use --add-gitignore for a team-shared installation, or --add-git-exclude to keep the tracked tree clean, which commit-bound MR review requires.');
    if ($force && !$set) throw new RuntimeException('--force-default-agent also requires --set-default-agent.');
    $source=__DIR__; $target=realpath(getcwd());
    if ($target===false || CES\within($target,$source) || CES\within($source,$target)) throw new RuntimeException('Extract the package outside the project and run this installer from the target repository root.');
    if (!is_dir($target.'/.git') && !is_file($target.'/.git')) throw new RuntimeException('Run from a Git repository root (worktrees with a .git file are supported).');
    $settingsPath=CES\safePath('.claude/settings.json',false,$target);
    // All existing configuration and ownership metadata is validated BEFORE any write.
    $settings=is_file($settingsPath)?installerJson($settingsPath):new stdClass;
    $fragment=installerJson($source.'/.claude/engineering-system/settings.fragment.json');
    $settings=mergeSettings($settings,$fragment,$set,$force,$replace);
    $merged=json_encode($settings,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR)."\n";
    $statePath=CES\safePath('.claude/engineering-system/installed-files.json',false,$target);
    $previous=is_file($statePath)?installerJson($statePath):new stdClass;
    $owned=(array)($previous->files ?? new stdClass);
    $integrityPath=$source.'/.claude/engineering-system/package-integrity.json';
    if (is_file($integrityPath)) {
        $integrity=installerJson($integrityPath);
        foreach ((array)$integrity->files as $rel=>$hash) {
            $p=CES\safePath($rel,true,$source);
            if (!hash_equals($hash,hash_file('sha256',$p))) throw new RuntimeException('Package integrity failure: '.$rel);
        }
    }
    $roots=['.claude/agents','.claude/rules/engineering-system','.claude/engineering-system','scripts/claude','docs/ai/claude-engineering-system'];
    $files=[];
    foreach ($roots as $relRoot) {
        $it=new RecursiveIteratorIterator(new RecursiveDirectoryIterator($source.'/'.$relRoot,FilesystemIterator::SKIP_DOTS));
        foreach ($it as $f) {
            if ($f->isLink()) throw new RuntimeException('Package contains a symlink.');
            if (!$f->isFile()) continue;
            $rel=substr($f->getPathname(),strlen($source)+1);
            if (preg_match('~/(runtime|backups|__pycache__)/~',$rel)) continue;
            $files[$rel]=(string)file_get_contents($f->getPathname());
        }
    }
    foreach (glob($source.'/*.md') ?: [] as $doc) $files['docs/ai/claude-engineering-system/setup/'.basename($doc)]=(string)file_get_contents($doc);
    ksort($files); $changes=[]; $conflicts=[]; $actions=[]; $newOwned=[];
    foreach ($files as $rel=>$bytes) {
        $dst=CES\safePath($rel,false,$target);
        if (is_dir($dst)) throw new RuntimeException('File destination is a directory: '.$rel);
        if (is_file($dst) && (($s=stat($dst))===false || $s['nlink']>1)) throw new RuntimeException('Hard-linked destination: '.$rel);
        if ($rel==='.claude/engineering-system/config.json') {
            $configObject=is_file($dst)?installerJson($dst):json_decode($bytes,false,128,JSON_THROW_ON_ERROR);
            if (!$configObject instanceof stdClass || ($configObject->version ?? null)!==3) throw new RuntimeException('Existing config requires a manual v3 migration.');
            if ($allowHosts) {
                $existingHosts=$configObject->allowed_hosts ?? [];
                if (!is_array($existingHosts) || !array_is_list($existingHosts)) throw new RuntimeException('config.allowed_hosts must be an array.');
                foreach ($existingHosts as $host) if (!is_string($host)) throw new RuntimeException('config.allowed_hosts entries must be strings.');
                $configObject->allowed_hosts=array_values(array_unique(array_merge($existingHosts,$allowHosts))); sort($configObject->allowed_hosts,SORT_STRING);
                $bytes=json_encode($configObject,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR)."\n";
                $hash=hash('sha256',$bytes); $newOwned[$rel]=$hash;
                if (is_file($dst)) {
                    $old=hash_file('sha256',$dst);
                    if ($hash===$old) { $actions[]='UNCHANGED '.$rel.' (host already trusted)'; continue; }
                    $actions[]='BACKUP + UPDATE '.$rel.' (explicit --allow-host)';
                } else $actions[]='CREATE '.$rel.' (explicit --allow-host)';
                $changes[$rel]=$bytes; continue;
            } elseif (is_file($dst)) {
                $actions[]='PRESERVE human configuration '.$rel; $newOwned[$rel]=hash_file('sha256',$dst); continue;
            }
        }
        $hash=hash('sha256',$bytes); $newOwned[$rel]=$hash;
        if (is_file($dst)) {
            $old=hash_file('sha256',$dst);
            if ($hash===$old) { $actions[]='UNCHANGED '.$rel; continue; }
            if (!$replace && ($owned[$rel] ?? null)!==$old) { $conflicts[]=$rel; continue; }
            $actions[]='BACKUP + UPDATE '.$rel;
        } else $actions[]='CREATE '.$rel;
        $changes[$rel]=$bytes;
    }
    if ($conflicts) throw new RuntimeException("Conflicting/customized files; nothing written. Inspect them, then explicitly use --replace-existing to back up and replace:\n".implode("\n",$conflicts));
    if (!is_file($settingsPath) || file_get_contents($settingsPath)!==$merged) $changes['.claude/settings.json']=$merged;
    $managed=['.claude/engineering-system/runtime/','.claude/engineering-system/backups/','.claude/engineering-system/installed-files.json'];
    if ($addGitignore) {
        $gitignorePath=CES\safePath('.gitignore',false,$target);
        $currentGitignore=is_file($gitignorePath)?(string)file_get_contents($gitignorePath):'';
        $next=withManagedExclusions($currentGitignore,$managed,'.gitignore');
        if ($next!==$currentGitignore) { $changes['.gitignore']=$next; $actions[]=(is_file($gitignorePath)?'BACKUP + UPDATE ':'CREATE ').'.gitignore (explicit --add-gitignore)'; }
    }
    // .gitignore is TRACKED, so appending to it dirties the working tree - and commit-bound MR
    // review requires a clean tracked tree. .git/info/exclude is local and never tracked, so it
    // gives the same exclusions without blocking a review of the checkout it lives in.
    if ($addGitExclude) {
        if (!is_dir($target.'/.git')) throw new RuntimeException('--add-git-exclude needs a normal .git directory. This checkout uses a linked worktree, so add the CES runtime exclusions to that worktree\'s own info/exclude by hand.');
        $excludeRel='.git/info/exclude';
        $excludePath=CES\safePath($excludeRel,false,$target);
        $currentExclude=is_file($excludePath)?(string)file_get_contents($excludePath):'';
        $next=withManagedExclusions($currentExclude,$managed,$excludeRel);
        if ($next!==$currentExclude) { $changes[$excludeRel]=$next; $actions[]=(is_file($excludePath)?'BACKUP + UPDATE ':'CREATE ').$excludeRel.' (explicit --add-git-exclude; leaves the tracked tree clean)'; }
    }
    $state=json_encode(['version'=>CES\VERSION,'files'=>(object)$newOwned],JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR)."\n";
    if (!is_file($statePath) || file_get_contents($statePath)!==$state) $changes['.claude/engineering-system/installed-files.json']=$state;
    foreach ($changes as $rel=>$unused) {
        $p=CES\safePath($rel,false,$target);
        if (is_dir($p)) throw new RuntimeException('Destination is a directory: '.$rel);
        if (is_file($p) && (($st=stat($p))===false || $st['nlink']>1)) throw new RuntimeException('Hard-linked managed destination: '.$rel);
    }
    echo ($apply?'APPLY':'DRY RUN')." - ".count($changes)." file changes\n";
    foreach ($actions as $a) echo $a."\n";
    if (!$apply) { echo "No files changed. Add --apply after reviewing this plan.\n"; exit(0); }
    $backupRel='.claude/engineering-system/backups/'.gmdate('Ymd-His').'-'.bin2hex(random_bytes(6));
    $originals=[]; $written=[];
    try {
        foreach ($changes as $rel=>$bytes) {
            $dst=CES\safePath($rel,false,$target); $originals[$rel]=is_file($dst)?(string)file_get_contents($dst):null;
            if ($originals[$rel]!==null) writeInstall($target,$backupRel.'/'.$rel,$originals[$rel],0600);
        }
        foreach ($changes as $rel=>$bytes) { writeInstall($target,$rel,$bytes,str_starts_with($rel,'.claude/engineering-system/installed-')?0600:0644); $written[]=$rel; }
    } catch (Throwable $e) {
        $rollback=[];
        foreach (array_reverse($written) as $rel) {
            try { if ($originals[$rel]===null) unlink($target.'/'.$rel); else writeInstall($target,$rel,$originals[$rel]); }
            catch (Throwable $r) { $rollback[]=$rel; }
        }
        throw new RuntimeException('Install failed; file rollback attempted. Failed rollbacks: '.implode(',',$rollback).'. '.$e->getMessage());
    }
    echo "Complete. CLAUDE.md and README.md were not modified. .gitignore changes occur only with explicit --add-gitignore.\n";
    echo 'Backups: '.$target.'/'.$backupRel."\n";
    echo "Exclude CES runtime/backups/installed-files local state from Git before committing (or use --add-gitignore).\n";
    echo "Run: php scripts/claude/checks/self-check.php\n";
} catch (Throwable $e) { fwrite(STDERR,'INSTALL_BLOCKED: '.$e->getMessage()."\n"); exit(2); }
