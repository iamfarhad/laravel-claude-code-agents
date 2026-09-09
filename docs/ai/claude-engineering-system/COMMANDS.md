# Broker actions
Run from repository root in an actual main session: `claude --agent engineering-orchestrator`.
The PreToolUse hook must be enabled. Use /doctor and a safe smoke test on your installed CLI version before relying on it. A user default agent is optional; it is not imposed on other workflows.

Every Bash call MUST be exactly:
```bash
php scripts/claude/bin/ces.php <<'CES_REQUEST'
{"action":"task_status"}
CES_REQUEST
```
No leading commands, pipes, redirects, trailing arguments, background execution or arbitrary PHP. The hook turns this request into a short-lived one-use ticket. The broker checks real agent role and configuration again. Permissions may still request human confirmation.

## Request schemas
Unknown fields are rejected. JSON values below are examples, not authorization.
- `task_open`: orchestrator only. Fields task_id, workflow, prd_path for code-changing flows; optional mr_url + reviewed_head_sha (full immutable hash), risk_gates (reviewer names). One task/session; scope cannot silently change.
- `task_status`: all roles, no additional fields. Returns task, workspace digest and recorded role receipts.
- `context`: all except publisher. kind is status, head, log or diff; optional full base_sha for diff. No untrusted git arguments.
- `fetch_mr`: orchestrator/peer/TL/EM. mr_url must be an exact HTTPS URL on configured allowed_hosts. Can run before task_open. In the normal MR flow, the MAIN orchestrator performs this preflight directly before any delegation. Returns a bounded, provider-normalized summary: head SHA, open state, review facts (title, branches, author/reviewers, merge status, conflicts, pipeline status, counts, a description excerpt with a truncation flag and a hash of the full text) and one entry per changed file with its paths, change kind and `diff_available`. Diff BODIES are deliberately not returned - the raw provider object plus every patch outgrew the transcript on a large MR, and the reviewer must read code from a clean local checkout at the reviewed head anyway. Select risk gates from the returned file paths and change kinds. Files with `diff_available: false`, and any `diff_incomplete`, must be inspected locally.
- `validate_prd`: all except publisher. Reads the current task's PRD; no caller-chosen alternative path.
- `run_check`: configured developers/testers/QA/performance. name is an exact preset from human config. No arbitrary command string. Returns a real check ID, exit code, evidence and digest.
- `publish_review`: publisher only. Optional dry_run boolean. No caller-provided findings/URL/SHA; it uses the current peer receipt and task.
- `finalize`: orchestrator only. Checks mandatory receipts, AC/test evidence, risk gates and publication before recording a completion recommendation.

## Example task
```json
{"action":"task_open","task_id":"B2B-142","workflow":"feature","prd_path":"docs/prd/B2B-142.md","risk_gates":["security-reviewer","tech-lead-reviewer"]}
```

For an existing MR first fetch metadata, then open peer-review with mr_url and the returned reviewed_head_sha. A clean checkout of that exact head must already be provisioned by a human/CI; agents do not checkout, commit or push for you.

Human-only local validators: `php scripts/claude/checks/self-check.php` and `php scripts/claude/checks/validate-prd.php docs/prd/B2B-142.md`. Human/CI publisher STDIN adapter is documented in setup/MR_REVIEW_SETUP.md. These raw commands are not allowed inside CES agent Bash.
