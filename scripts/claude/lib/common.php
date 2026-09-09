<?php

declare(strict_types=1);
namespace CES;

const VERSION = '3.2.3';
const ROLES = ['engineering-orchestrator','product-manager','prd-reviewer','architect','qa-support','developer','hotfix-developer','upgrade-developer','peer-reviewer','mr-review-publisher','tech-lead-reviewer','engineering-manager-reviewer','security-reviewer','performance-reviewer','database-reviewer','tester','regression-tester','incident-investigator','rca-analyzer','release-reviewer'];
const DEVELOPERS = ['developer','hotfix-developer','upgrade-developer'];
const TESTERS = ['tester','regression-tester'];
const REVIEWERS = ['peer-reviewer','tech-lead-reviewer','engineering-manager-reviewer','security-reviewer','performance-reviewer','database-reviewer','release-reviewer'];

function root(): string { return dirname(__DIR__, 3); }
function jsonObject(string $raw, int $limit = 2097152): array {
    if (strlen($raw) > $limit) throw new \RuntimeException('JSON input exceeds size limit.');
    $obj = json_decode($raw, false, 64, JSON_THROW_ON_ERROR);
    if (!$obj instanceof \stdClass) throw new \RuntimeException('Expected a JSON object.');
    return json_decode($raw, true, 64, JSON_THROW_ON_ERROR);
}
function encode(mixed $data): string { return json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR) . "\n"; }
function output(mixed $data): void { echo encode($data); }
function requireText(mixed $value, string $field, int $limit = 10000): string {
    if (!is_string($value) || trim($value) === '' || strlen($value) > $limit) throw new \RuntimeException("Invalid or empty {$field}.");
    return trim($value);
}
function within(string $path, string $prefix): bool { return $path === $prefix || str_starts_with($path, rtrim($prefix, '/') . '/'); }
/** Reject traversal, symlinks and multiply-linked writable files. This is not an OS sandbox. */
function safePath(string $path, bool $mustExist = false, ?string $base = null): string {
    $base = rtrim($base ?? root(), '/');
    if ($path === '' || str_contains($path, "\0") || str_contains($path, '\\')) throw new \RuntimeException('Invalid path.');
    if (!str_starts_with($path, '/')) $path = $base . '/' . $path;
    $parts = explode('/', $path);
    if (in_array('..', $parts, true)) throw new \RuntimeException('Parent traversal is forbidden.');
    $path = '/' . implode('/', array_values(array_filter($parts, fn($p) => $p !== '' && $p !== '.')));
    if (!within($path, $base)) throw new \RuntimeException('Path is outside the project.');
    $cursor = '';
    foreach (explode('/', ltrim($path, '/')) as $part) {
        $cursor .= '/' . $part;
        if (is_link($cursor)) throw new \RuntimeException('Symlink paths are forbidden: ' . $cursor);
    }
    if ($mustExist && !file_exists($path)) throw new \RuntimeException('Required path does not exist: ' . $path);
    return $path;
}
function relative(string $path): string { return ltrim(substr(safePath($path), strlen(root())), '/'); }
function atomicWrite(string $path, string $bytes, int $mode = 0600): void {
    $path = safePath($path);
    if (is_file($path) && (($s = stat($path)) === false || $s['nlink'] > 1)) throw new \RuntimeException('Refusing hard-linked destination.');
    if (!is_dir(dirname($path)) && !mkdir(dirname($path), 0700, true) && !is_dir(dirname($path))) throw new \RuntimeException('Cannot create directory.');
    $tmp = tempnam(dirname($path), '.ces-');
    if ($tmp === false) throw new \RuntimeException('Cannot create temporary file.');
    try {
        if (file_put_contents($tmp, $bytes, LOCK_EX) !== strlen($bytes) || !chmod($tmp, $mode) || !rename($tmp, $path)) throw new \RuntimeException('Atomic write failed.');
    } finally { if (is_file($tmp)) unlink($tmp); }
}
function readJson(string $path): array { return jsonObject((string)file_get_contents(safePath($path, true))); }
function config(): array {
    $c = readJson(root() . '/.claude/engineering-system/config.json');
    if (($c['version'] ?? null) !== 3) throw new \RuntimeException('Unsupported engineering-system config version.');
    return $c;
}
function sessionDir(string $session): string {
    requireText($session, 'session_id', 300);
    return safePath(root() . '/.claude/engineering-system/runtime/sessions/' . hash('sha256', $session));
}
function loadTask(string $session): array { return readJson(sessionDir($session) . '/task.json'); }
function taskExists(string $session): bool { return is_file(sessionDir($session) . '/task.json'); }
function saveTask(string $session, array $task): void { atomicWrite(sessionDir($session) . '/task.json', encode($task)); }
function redact(string $text): string {
    $text = preg_replace('/(Bearer\s+)[A-Za-z0-9._~+\/-]+/i', '$1[REDACTED]', $text) ?? $text;
    $text = preg_replace('/((?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\s,;]+/i', '$1[REDACTED]', $text) ?? $text;
    return $text;
}
function sameHash(string $actual, mixed $expected): bool { return is_string($expected) && hash_equals($actual, $expected); }
