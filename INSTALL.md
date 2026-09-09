# Install / upgrade without replacing your project documentation

## Prerequisites and boundaries
PHP 8.2+ with JSON, proc_open and normal filesystem functions; Git with an initial commit; a Unix-like runtime (Linux/macOS). Optional Python 3.10+ for the offline regression suite. Optional glab/gh only for actual MR/PR access. Use a current Claude Code release supporting documented agent_type hooks and PreToolUse.updatedInput.
The audit ran locally on Linux/PHP 8.4.23. macOS and live Claude behavior are not claimed as tested. Windows is not supported by this package's paths/process assumptions.

## New installation
Extract the package OUTSIDE your repository. In a clean, trusted project root:
```bash
php /absolute/path/laravel-claude-code-agents/install.php
```
This is a dry run; it creates no files. Then:
```bash
php /absolute/path/laravel-claude-code-agents/install.php --apply
```
To set the default main agent only when one is not already configured, add `--set-default-agent`. An existing agent remains unchanged; replacing it requires BOTH `--set-default-agent --force-default-agent` explicitly.
Prefer explicit startup when you use multiple Claude workflows:
```bash
claude --agent engineering-orchestrator
```
Do NOT ask a generic main session to spawn engineering-orchestrator as a subagent. This design requires its main-session role in hook events.

For MR/PR review, you may explicitly trust the exact provider host during install:
```bash
php /absolute/path/laravel-claude-code-agents/install.php --apply --allow-host=git.internal.example
```
This is an explicit human trust decision. Wildcards, schemes, paths and ports are rejected. Repeat `--allow-host=...` to trust more than one exact host.

If you want the installer to append only the CES runtime exclusions to the existing `.gitignore`, add `--add-gitignore`. It preserves existing entries and backs up the file before changing it.

## Upgrade from the earlier ZIP
Start with a dry run. Existing unowned/customized package paths may conflict. Inspect the conflicts, then intentionally migrate:
```bash
php /absolute/path/laravel-claude-code-agents/install.php --replace-existing
php /absolute/path/laravel-claude-code-agents/install.php --apply --replace-existing
```
Replacement is scoped to package-owned destinations, backed up under `.claude/engineering-system/backups/`. Project CLAUDE.md and README.md remain byte-for-byte untouched. `.gitignore` is untouched unless you explicitly pass `--add-gitignore`. Custom edits to package agents will be backed up, NOT semantically merged; compare and reapply appropriate custom role instructions manually.
Existing human v3 config is preserved. Unsupported older config versions block for manual migration. Unrelated settings/hooks are preserved; known managed CES hook entries are replaced; the exact old unrestricted publisher allow-rule is removed only during explicit replacement.
Obsolete per-agent guard script paths remain fail-closed migration stubs. Agent frontmatter must be upgraded together with global hooks; mixing v2 agents and v3 scripts is unsupported.

## After installation
```bash
php scripts/claude/checks/self-check.php
python3 -S scripts/claude/tests/test_system.py
```
The tests use controlled fixtures/mocked providers, not your production data. Avoid running them as root or inside untrusted repositories with secrets.
Add these patterns to project `.gitignore` (recommended for a shared CES installation) or to your local `.git/info/exclude` if CES is strictly personal. You can also let the installer append them with explicit `--add-gitignore`:
```gitignore
.claude/engineering-system/runtime/
.claude/engineering-system/backups/
.claude/engineering-system/installed-files.json
```
Runtime receipts/logs can contain sensitive operational context, backups may contain prior project settings, and `installed-files.json` is checkout-local installer ownership state. Never commit those local artifacts. Do NOT ignore the whole `.claude/` directory when CES is meant to be shared: agents, rules, hooks/scripts and the non-secret policy config should normally be version-controlled. Avoid opening two writing sessions on the same checkout.

Configure CUSTOMIZATION.md for isolated checks, MR_REVIEW_SETUP.md for host/identity authorization, and SIGNOZ_SETUP.md for read-only telemetry. Until configured, these capabilities deliberately block rather than fake success.
Inside Claude run `/doctor`, then follow docs/ai/claude-engineering-system/RUNTIME_SMOKE_TEST.md. If agent_type/updatedInput/hooks are not behaving as documented in your installed CLI, stop using automation; never disable guards merely to make it run.

## Integrity and recovery
The source archive contains package-integrity.json; the installer checks listed source hashes before any write. This detects accidental changes, NOT authenticity against an attacker replacing both files and hashes.
Installation preflights settings JSON and target paths, backs up originals, and uses staged atomic file replacement. On write failure it attempts file rollback; empty newly created directories may remain, and filesystem failure can defeat rollback. Inspect reported failures rather than assuming transaction-level installation.
To recover, compare the printed backup directory and restore only intended package files/settings. No automatic destructive uninstall is provided.

## Existing Laravel CLAUDE.md / README.md
Leave both where they are. New rules live under .claude/rules/engineering-system/. Package documentation is installed under docs/ai/claude-engineering-system/setup/, not as a replacement project README.
If your original rules contradict this workflow, resolve the specific conflict explicitly. Loading multiple rule files does not mathematically establish which business instruction is right.
