# Human configuration

Edit `.claude/engineering-system/config.json` yourself, or use the installer's explicit `--allow-host=HOST` option for exact MR hosts. CES developers may not edit governance. Never store real tokens/passwords here. The policy file is safe to commit only if it contains policy/preset metadata and no credentials.

## Model and effort
Agent frontmatter uses `model: inherit` and omits effort. This preserves the selected session/provider capabilities instead of hardcoding an unsupported maximum. 'Pro' in a product UI is not a portable Claude subagent YAML effort value. Consult the installed CLI/model documentation before opting into a supported explicit effort level. This package does not change your subscription or underlying model.
Persistent agent memory is intentionally omitted: documented memory scopes can automatically grant Read/Write/Edit tools, which conflicts with strict read-only roles.

## Tests are disabled until safely configured
`execution_isolated: true` is an administrative acknowledgment, NOT a sandbox implementation. Only set it after provisioning a disposable container/runner/worktree with test-only data, nonproduction credentials, no sensitive host mounts, restricted network, process/resource limits and an externally protected copy of governance.
Do not expose publication/production SigNoz credentials to arbitrary repository tests. For untrusted fork/MR code separate the isolated verification runner from the credentialed publishing session. This v3 local runner does NOT itself implement secure multi-host evidence attestation; arrange a trusted CI boundary before automating that scenario.

Checks are exact argv arrays, not shell strings. A Laravel example (adjust to actual installed tools):
```json
{
  "execution_isolated": true,
  "checks": {
    "unit": {
      "trusted": true,
      "kind": "test",
      "roles": ["developer", "hotfix-developer", "upgrade-developer", "tester", "regression-tester"],
      "argv": ["php", "vendor/bin/phpunit", "--testsuite", "Unit"],
      "timeout_seconds": 120,
      "env": {"APP_ENV": "testing", "DB_CONNECTION": "sqlite", "DB_DATABASE": ":memory:", "QUEUE_CONNECTION": "sync", "CACHE_STORE": "array", "MAIL_MAILER": "array"}
    },
    "style": {
      "trusted": true,
      "kind": "static",
      "roles": ["developer", "hotfix-developer", "upgrade-developer", "tester"],
      "argv": ["php", "vendor/bin/pint", "--test"],
      "timeout_seconds": 120,
      "env": {"APP_ENV": "testing"}
    }
  }
}
```
Merge the example into the existing version:3 config; do not discard allowed_hosts, risk_patterns or signoz_read_tools. SQLite is not a substitute for actual MySQL/PostgreSQL isolation/locking tests. Configure separate disposable engine-appropriate integration checks.
The process environment is rebuilt rather than inheriting secrets, but application bootstrap can still read files such as .env/.env.testing. A test can execute arbitrary PHP and subprocesses. APP_ENV=testing by itself proves nothing about safe isolation.
Checks modifying tracked/unignored workspace fail verification; normal ignored cache/coverage artifacts may be permitted by the actual isolated environment. A timeout terminates the direct child, not a guaranteed entire process tree; use container/runner limits for descendants.

## Risk gates and ownership
Record explicit semantic reviewer names in task_open.risk_gates. Filename patterns are only hints. Incident/upgrade mandate release-reviewer; security/performance mandate their specialist. Product-manager can author readiness but cannot create human stakeholder approval.

## Language and project facts
Agents can return summaries in the team's preferred language while preserving JSON keys, AC IDs, paths and hashes. Project conventions remain in existing CLAUDE.md. Do not encode guessed versions, team owners, SLOs, deadlines or credentials in prompts.

## Local working tree
Install with `--add-git-exclude` rather than `--add-gitignore` on any checkout you review MRs from: the
former writes to untracked `.git/info/exclude`, the latter dirties the tracked `.gitignore`. Commit the CES
installation itself before reviewing, since installing it also leaves untracked files behind.

Filename `risk_patterns` ship tuned for stock Laravel plus Bagisto/Webkul `packages/<Vendor>/<Package>/src/`
layouts. If your code lives elsewhere, extend them - an unmatched path silently yields no gate, and semantic
`risk_gates` at `task_open` remain the authority either way.

Use one task/session and one writer per checkout; source/PRD changes invalidate receipts. Existing MR publication requires a clean tracked checkout at the exact reviewed head. Installation or customized tracked governance may dirty a checkout: provision a clean trusted baseline before reviewing, rather than hiding those modifications.
Separate session worktrees may be prepared by a human/CI. Do not set isolation:worktree independently on every specialist: that can cause them to inspect different snapshots.
