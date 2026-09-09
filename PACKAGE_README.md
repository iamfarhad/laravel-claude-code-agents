# Claude Engineering System - v3.2

A 20-role Claude Code engineering workflow with product/acceptance gates, separate peer/TL/EM review, scoped MR comment publication and optional read-only SigNoz evidence.

The audited v3 line replaces the previous claim that a Bash denylist makes an agent read-only with a narrow role-aware command broker and an explicit security model. It is a locally tested engineering aid, NOT a certified sandbox or a guarantee of bug-free code.

Start with INSTALL.md. Existing CLAUDE.md and README.md are not replaced. `.gitignore` is changed only with explicit `--add-gitignore`. Settings merge; conflicting custom files stop installation unless you explicitly request backed-up replacement. Existing Laravel conventions remain in their original file.

## Components
- 20 role definitions, inherited model and session effort; no automatic persistent agent memory.
- 14 workflow documents, including CI failures and development bugs.
- Mandatory PRD/independent PRD review before all code-changing flows; minimal corrective contracts for bugs/hotfixes.
- Snapshot/PRD-bound receipts and actual independent test-run IDs for every AC.
- Console + exact-commit MR/PR inline/summary publication, stale-head protection, pagination and deduplication.
- Human-configured check presets and optional explicit SigNoz read-tool allowlist; both disabled by default.
- Non-destructive installer, local self-check, offline regression suite and audit report.

## Start
Extract outside the target repository. From the target Git repository root:
```bash
php /absolute/path/laravel-claude-code-agents/install.php
php /absolute/path/laravel-claude-code-agents/install.php --apply
php scripts/claude/checks/self-check.php
claude --agent engineering-orchestrator
```
Run `/doctor` and the runtime smoke checklist before team use. Configure isolated tests and provider access separately. No installer contacts production or publishes comments.

Read AUDIT_REPORT.md, SECURITY_MODEL.md and TEST_REPORT.md for the tested scope and remaining limitations. No live Claude CLI, real GitLab/GitHub account or SigNoz instance was available in the audit environment.

## 3.2 setup helpers
- `--allow-host=HOST` explicitly adds an exact MR/PR provider hostname to the human policy.
- `--add-gitignore` appends only CES runtime/backups/installer-state exclusions and preserves existing entries.
- Pre-task MR/config preflight is performed directly by the main orchestrator; specialists cannot be delegated before task_open.
