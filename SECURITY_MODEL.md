# Security model and limitations

## Threats addressed locally
- Ordinary role confusion and attempts to edit outside assigned document/implementation scope.
- Shell-prefix and denylist bypasses: known CES agents use a strictly parsed JSON envelope, with actual role/session-bound one-use tickets and no caller-supplied command.
- Stale PRD approvals, stale code reviews/checks, fabricated test receipt IDs and incomplete AC coverage.
- Accidental comments on a newer/closed MR, incomplete dedup pagination, dropped fallback findings and repeated local publication.
- Destructive installation over existing project documents/configuration, invalid settings JSON, path traversal and existing symlink/hardlink destinations.

## What this does NOT secure
Hooks are project-level software, not an OS sandbox or unbreakable policy. A human can disable them; a different non-CES session is not governed; a malicious repository can alter files via executed code or untrusted config. Tool allowlists are not filesystem/network isolation. Regex/read-name checks do not prove the behavior of arbitrary tools.
The hook supports known CES agent_type values. Start main with --agent engineering-orchestrator; verify real hook events in your CLI. Unknown agent types are intentionally outside scope to avoid taking over unrelated workflows. Existing conflicting user/managed hooks or settings can change behavior; test their composition.
Tokens/receipts under runtime are local coordination artifacts, not cryptographic proof against a malicious process with filesystem access. Keep governance externally protected for hostile source. Directory/TOCTOU races, hostile Git configuration, submodule internals, ignored sources, LFS/filter behavior and processes rewriting trusted files need stronger runner controls.
Read/Grep/Glob restrictions do not implement a complete DLP system. Secret filenames are partly blocked; secrets embedded in source/logs can still be exposed. Restrict available data and credentials, redact before MR publication and use server-side read-only telemetry credentials.
Configured test argv is code execution. The runner reconstructs environment and limits output/time, but does not containerize, enforce network policy, revoke mounted credentials or kill every grandchild. Use actual external isolation and test-only data. Never run untrusted MR code in a session whose filesystem exposes publication or observability secrets.
Workspace digests cover HEAD and tracked/unignored file contents/execute bits, not ignored files, running services, database state, package authenticity or recursive submodule contents. A passing process receipt is not proof that its assertions truly test an AC; independent test/code review and protected CI remain necessary.
PRD validation checks structural completeness and maps FR/AC IDs. It cannot prove stakeholder agreement, feasibility, semantic correctness or zero bugs. Any material ambiguity still needs human judgment.
MR comments use local locks and authenticated-actor fingerprints; these do not guarantee globally exactly-once delivery across runners or ambiguous network timeouts. Remote heads can race between checks and server writes; inline comments retain reviewed SHA, while summaries label it explicitly. Report partial/stale states honestly and inspect before retrying.

## Required external controls
Protected branches/CI, independent human approval, least-privilege provider identities, human release authority, disposable verification runners, test-only databases/network, protected governance and sensible retention of runtime evidence. Do not use privileged broad tokens merely to avoid permission prompts.

## Failures and escape hatches
A malformed specialist result gets one repair request; then it may stop, but its receipt is invalid and downstream completion stays blocked. Missing configuration/access/test evidence causes BLOCKED, not a silent bypass. Three total implementation reports consuming attempts bound autonomous rework, but do not cap all model/tool costs; use session/runner budgets too.
No approve, merge, resolve, close, push, rebase, deploy or production mutation is implemented. The one scoped external write is human-authorized review comments.
