# Changelog

## 3.2.4 - MR tasks can scope their own diff (2026-09-09)
- `task_open` now accepts an optional `base_sha` that sets the task's diff scope, validated as a
  full hash of a commit actually present in the checkout and covered by immutable task scope.
- This fixes a real dead end on MR reviews. `base_sha` was always the local HEAD, but an MR review
  checkout sits AT the reviewed head, so `base_sha == reviewed_head_sha`: `context kind=diff`
  returned nothing and `derivedRiskGates()` had no changed files to classify, silently deriving
  zero specialist gates. A reviewer could conclude "no diff" from what was actually an
  unscoped task. Passing the merge-base with the target branch - `fetch_mr` returns it as
  `metadata.base_sha` - makes the canonical diff reachable.
- Because `task_status` is available to every role, the task's `base_sha` is also how a specialist
  that is not granted `fetch_mr` (security, database, performance, release reviewers) now obtains a
  usable diff scope. `fetch_mr` stays restricted to orchestrator/peer/TL/EM: the local checkout at
  the reviewed head is the authoritative copy of the code, so the fix is to give every role the
  scope rather than to widen provider network access.
- Instructed the orchestrator to always pass `base_sha` on MR tasks and to refuse to open a task
  that cannot see its own diff, and gave all seven reviewing roles an explicit Diff scope section:
  read `base_sha` from `task_status`, pass it to `context kind=diff`, and when it equals
  `reviewed_head_sha` report the coverage limitation instead of guessing which lines are new.

## 3.2.3 - bounded fetch_mr result (2026-09-09)
- `fetch_mr` no longer returns the raw provider object or any diff body. It previously returned
  the entire MR/PR payload - description, repeated actor blobs, pipeline objects, avatar URLs -
  plus the full patch for every changed file. On a 134-file MR that is ~637 KB, which overran the
  transcript, forced the CLI to persist the result to a file, and then dominated the
  orchestrator's context for the rest of the task.
- It now returns a provider-normalized summary (head SHA, open state, title, branches,
  author/reviewers/assignees, merge status and conflicts, pipeline status, counts, labels, base
  and start SHAs, plus a description excerpt bounded to 8 KB with a truncation flag and a
  sha256 of the full text) and one entry per changed file carrying `new_path`, `old_path`, the
  change kind, line counts and `diff_available`. Measured on that same shape: 637 KB -> 52 KB,
  a 91.8% reduction, with the head SHA and every risk-gate input preserved.
- Diff bodies were redundant: `peer-reviewer` is required to review a clean local checkout at
  the exact reviewed head, and the workflow already refuses a commit-bound review otherwise.
  Per-file `diff_available` now says exactly which files the provider diff did not cover,
  instead of only the aggregate `diff_incomplete` flag.
- Extended the offline provider fixture to return realistic MR metadata, and added tests
  asserting no diff body or raw-payload field survives, that a huge description is bounded, and
  that an uncovered file is individually marked.

## 3.2.2 - harness interop: reading back persisted tool output (2026-09-09)
- Fixed the read guard denying Claude Code's own persisted tool output. When a broker result
  is too large for the transcript, the CLI writes it to
  `~/.claude/projects/<slug>/<session>/tool-results/<id>.txt` and reads it back; `authorizeRead()`
  routed every read through `safePath()`, so that read failed with "Path is outside the project"
  and any flow with a large `fetch_mr` result dead-ended. Reads are now permitted for exactly
  `<projects>/<slug>/<THIS session id>/tool-results/`, matched on the RESOLVED real path so a
  planted symlink cannot escape it. Another session's directory, other projects' transcripts,
  `$HOME` secrets and the rest of the host stay denied, and the denial message now says what is
  actually allowed. Regression tests cover the positive case, three near-miss paths and the
  symlink escape.
- Hardened `process()` to drain both pipes to EOF after the child exits. It previously did one
  bounded 64 KiB read per pipe, which cannot be guaranteed to empty a pipe whose buffer has been
  enlarged - a large provider response could be silently truncated into invalid JSON and surface
  as a confusing "Provider returned non-JSON or incomplete output". Not reproduced at default
  pipe sizes; fixed as defence in depth, with a test asserting a 600 KB two-pipe response
  arrives byte-complete.

## 3.2.1 - source restoration + symlinked-checkout fix (2026-09-09)
- Fixed the PreToolUse guard's repository-root check, which compared the raw session `cwd`
  against a `__DIR__`-derived root. Because PHP always resolves `__DIR__` through symlinks, any
  checkout reached through a symlinked ancestor - every macOS temp path via `/var` -> `/private/var`,
  and any project under a symlinked parent - had EVERY tool call denied with the misleading message
  "Path is outside the project". Both sides are now canonicalized. `safePath()` is deliberately not
  used for this comparison: its symlink-component rejection guards write destinations and would
  reject a legitimate root. Write/Read path guards are unchanged, so symlinked and hard-linked
  destinations are still denied.
- Restored the package source that was missing from the repository: the 20 agent definitions, the
  10 shared rule files, `config.json`, `settings.fragment.json`, the PRD/ADR templates, `.gitignore`,
  `.mcp.json.example` and the CI workflow. The `.bootstrap/source.tar.gz` archive that was supposed
  to publish them was truncated (15 KB of a 1.55 MB stream) and failed to decompress, so its
  workflow could never have restored them.
- Removed the corrupt `.bootstrap/` archive and its `bootstrap-source.yml` workflow, which ran on
  every push to `main` and force-committed to the branch. The real `ci.yml` is now the only workflow.
- Excluded `.claude/settings.json` and `.claude/settings.local.json` from the integrity manifest.
  They are checkout-local Claude Code state, like `installed-files.json`, and hashing them made
  `package_integrity.py --check` fail in CI whenever a developer's local settings differed.

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
