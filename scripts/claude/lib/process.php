<?php

declare(strict_types=1);
namespace CES;
require_once __DIR__ . '/common.php';

/** argv only; concurrent pipe reads, a wall-clock timeout, bounded output, no shell. */
function process(array $argv, string $stdin = '', int $timeout = 30, int $limit = 2097152, ?array $env = null, ?string $cwd = null): array {
    if ($argv === [] || count($argv) > 100) throw new \RuntimeException('Invalid process argv.');
    foreach ($argv as $arg) if (!is_string($arg) || str_contains($arg, "\0")) throw new \RuntimeException('Invalid process argument.');
    $p = proc_open($argv, [0=>['pipe','r'],1=>['pipe','w'],2=>['pipe','w']], $pipes, $cwd ?? root(), $env, ['bypass_shell'=>true]);
    if (!is_resource($p)) throw new \RuntimeException('Could not start process.');
    foreach ($pipes as $pipe) stream_set_blocking($pipe, false);
    $out=''; $err=''; $offset=0; $exit=-1; $started=microtime(true); $timedOut=false; $truncated=false;
    try {
        while (true) {
            if (isset($pipes[0])) {
                if ($offset < strlen($stdin)) {
                    $n = @fwrite($pipes[0], substr($stdin, $offset, 8192));
                    if ($n === false) { fclose($pipes[0]); unset($pipes[0]); }
                    else $offset += $n;
                } else { fclose($pipes[0]); unset($pipes[0]); }
            }
            foreach ([1,2] as $i) {
                $chunk = stream_get_contents($pipes[$i],65536);
                if ($chunk !== false && $chunk !== '') {
                    if ($i===1) $out.=$chunk; else $err.=$chunk;
                }
            }
            $s = proc_get_status($p);
            if (!$s['running']) {
                $exit=(int)$s['exitcode'];
                foreach ([1,2] as $i) { $chunk=stream_get_contents($pipes[$i],65536); if ($i===1) $out.=$chunk; else $err.=$chunk; }
                break;
            }
            if (strlen($out)+strlen($err)>$limit || microtime(true)-$started>$timeout) {
                $truncated = strlen($out)+strlen($err)>$limit;
                $timedOut = !$truncated;
                proc_terminate($p, 15); usleep(50000); proc_terminate($p, 9); $exit=124; break;
            }
            usleep(5000);
        }
    } finally {
        foreach ($pipes as $pipe) if (is_resource($pipe)) fclose($pipe);
        $closed=proc_close($p); if ($exit<0) $exit=$closed;
    }
    if (strlen($out)+strlen($err)>$limit) { $truncated=true; $exit=124; }
    return ['exit_code'=>$exit,'stdout'=>substr($out,0,$limit),'stderr'=>substr($err,0,$limit),'timed_out'=>$timedOut,'truncated'=>$truncated,'duration_ms'=>(int)((microtime(true)-$started)*1000)];
}
function git(array $args, int $limit=2097152): array {
    return process(array_merge(['git','--no-pager','-c','core.fsmonitor=false','-c','core.hooksPath=/dev/null','-c','diff.external=','-c','core.quotePath=false'], $args), '', 30, $limit);
}
function headSha(): string {
    $r=git(['rev-parse','--verify','HEAD']);
    $sha=trim($r['stdout']);
    if ($r['exit_code']!==0 || !preg_match('/\A[a-f0-9]{40,64}\z/', $sha)) throw new \RuntimeException('A Git checkout with an initial commit is required.');
    return $sha;
}
function workspaceDigest(): string {
    $r=git(['ls-files','-z','--cached','--others','--exclude-standard']);
    if ($r['exit_code']!==0 || $r['truncated']) throw new \RuntimeException('Cannot inventory workspace.');
    $files=array_unique(array_filter(explode("\0",$r['stdout']))); sort($files,SORT_STRING);
    $hash=hash_init('sha256'); hash_update($hash, headSha());
    foreach ($files as $rel) {
        if (str_starts_with($rel,'.claude/engineering-system/runtime/') || str_starts_with($rel,'.claude/engineering-system/backups/')) continue;
        $p=root().'/'.$rel;
        // Never follow links while fingerprinting a checkout.
        $cursor=root(); $linked=false;
        foreach (explode('/',$rel) as $part) { $cursor.='/'.$part; if (is_link($cursor)) { $linked=true; break; } }
        hash_update($hash,$rel."\0");
        if ($linked) hash_update($hash,'LINK:'.(readlink($cursor) ?: ''));
        elseif (is_file($p)) { hash_update($hash,hash_file('sha256',$p)); hash_update($hash,(string)(fileperms($p)&0111)); }
        elseif (is_dir($p)) hash_update($hash,'DIRECTORY');
        else hash_update($hash,'DELETED');
    }
    return hash_final($hash);
}
