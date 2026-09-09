# Changelog

## 3.2.0 - background-review lifecycle fix + repository CI (2026-09-09)
- Fixed the Stop final gate so non-empty Claude Code `background_tasks` means the main session is paused for in-flight work, not task completion. It no longer forces a premature terminal `ces-result` while background specialists are running.
- Updated the orchestrator contract to allow parallel read-only specialist reviews on the same immutable snapshot and to pause naturally rather than reporting `BLOCKED` for pending receipts.
- Added regression coverage for the background-task pause lifecycle.
- Added repository CI for PHP lint, the offline regression suite and self-check.
- Added a source-repository `.gitignore` for CES runtime/backups/installer state and test caches.

## 3.1.0 - MR preflight/setup UX fix (2026-09-09)
- Clarified that an empty `allowed_hosts` is a deliberate fail-closed prerequisite, not a task/delegation loop to solve with a subagent.
- Main orchestrator now performs MR allowlist/config preflight itself before any specialist delegation.
- Allowlist errors include the exact blocked hostname and remediation.
- Added installer `--allow-host=HOST` for explicit, validated host trust without hand-editing JSON.
- Added opt-in `--add-gitignore` to append only CES runtime/backups/installer-state exclusions while preserving and backing up the existing `.gitignore`.
- Documented what should be committed versus ignored for a team-shared installation.

## 3.0.0 - audited revision (2026-09-09)
Breaking safety/process revision; do not mix agent files/scripts from v2.

- Replaced bypassable shell deny/prefix lists with exact role-aware JSON broker requests and single-use hook-issued tickets.
- Removed persistent agent memory and automatic per-role worktree settings; model/effort inherit session capability.
- Added real per-task PRD and current-hash independent reviewer gates before any code-changing route.
- Added structurally validated FR/AC definitions plus current independent check receipts for all ACs at completion.
- Added snapshot freshness, bounded implementation reports, bounded invalid-output repair and final receipt revalidation.
- Reworked MR publisher: immutable reviewed SHA, clean local commit binding, remote checks, pagination, actor-aware dedup, stable fallback summaries, no-write dry runs, partial-error reporting and local locking.
- Replaced SigNoz mutation blacklist with default-deny explicit read-tool policy and server-side least-privilege guidance.
- Installer now preflights before writes, preserves root documents/user settings, detects conflicts/symlinks/hardlinks, stages writes/backups and retains custom v3 config.
- Added executable offline regression fixtures and detailed limitations instead of asserting zero-risk or live integration success.

## Earlier v2
Retained as the audit input only. Its original 'hardened' label did not establish the invariants now tested; see AUDIT_REPORT.md.
