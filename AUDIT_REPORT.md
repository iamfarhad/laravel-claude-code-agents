# Audit report - v3.2.1 patch note

v3.2.1 is a correctness patch, not a new audit. Two classes of problem were found and fixed. First, the
repository was missing the package source it documented - the 20 agent definitions, 10 shared rules,
`config.json`, `settings.fragment.json` and the templates - because the `.bootstrap/source.tar.gz`
archive intended to publish them was truncated to 15 KB of a 1.55 MB stream and could not decompress.
Those files are restored and verified by the self-check and the installer test group. Second, running the
offline suite on a second platform (macOS) exposed a genuine guard defect: the PreToolUse root check
compared an unresolved session `cwd` against a symlink-resolved root, denying every tool call on any
symlinked checkout path. Both sides are now canonicalized; the write/read path guards are unchanged, so
symlinked and hard-linked destinations are still rejected. The residual risks below remain unchanged.

# Audit report - v3.2 lifecycle patch note

v3.2 fixes the main-session lifecycle when Claude Code has in-flight background specialist agents. The Stop hook now consumes the documented `background_tasks` array: non-empty means the session is paused waiting for background work, so the CES final-result gate is deferred until the parent session wakes and no background work remains. A dedicated regression test covers this behavior.

The detailed v3.0 security/process audit and v3.1 setup patch notes remain historical baseline evidence below.

# Audit report - v3.0.0

Audit date: 2026-09-09. Input: the uploaded `claude-engineering-system-hardened.zip` (v2). Output: revised v3 source/package.
Original archive SHA-256: `4a39b78a18b92592044cc937945da02eccd5bb4b7c5e2dd626e5c47a90370c9e`.

## Conclusion
The earlier hardened label was too strong for the tested invariants. The audit found reproducible bypasses and process gaps; this revision changes the code, prompts, workflow contracts and installer rather than simply increasing prompt length or declaring a higher effort level.
**96 offline automated tests pass. This is not proof of zero defects or a live integration certification.** Strong security still requires the external controls in SECURITY_MODEL.md.

## Reproduced against v2 before changing it
The local baseline contains nine probes: eight exposed a weakness and one was a negative control that the old code correctly rejected. See audit/v2-baseline-probes.json.

| Finding | What was observed | v3 change and regression coverage |
|---|---|---|
| Publisher prefix bypass | Adding a permitted-looking argument before a shell suffix passed the old guard. No live command was executed by the probe. | Exact JSON envelope with no extra shell; role/session-bound broker ticket. Guard shell-bypass tests. |
| Read-only interpreter bypass | A PHP interpreter write command was accepted by the old Bash guard. | No arbitrary interpreter/shell actions; enumerated broker operations. |
| Read-only Git option bypass | `git -C . reset --hard` passed the deny pattern. The probe tested authorization only, not a destructive reset. | No arbitrary Git argv; only fixed read-context operations. |
| Developer governance write | The old Write guard accepted paths under project rules and its own guard scripts. | Protected rules, hooks, scripts, product/ADR and root documentation paths. |
| Developer outside-project write | An absolute external path was accepted by the old Write guard. | Root containment plus traversal/symlink/hardlink checks. |
| Empty DRAFT PRD accepted | Readiness mentioned in prose and an AC token outside empty sections produced PASS. | Exact readiness metadata, nonempty sections, FR definitions, structured ACs and mappings, independent hash-bound reviewer. |
| Installer mutation before validation | Invalid settings JSON was discovered only after package files had been copied. | Complete preflight before writes, conflict detection, source hashes, staging/backups and rollback attempt. |

## Additional issues established by inspection and addressed
- Persistent `memory: project` was incompatible with the claimed tool boundary: current Claude documentation says memory automatically enables Read/Write/Edit. It is removed; roles inherit session model/effort rather than hardcoding a maximum unsupported on some models.
- A text PASS/heading was not proof of a current verified result. Role JSON shape, exact task/PRD/workspace freshness, actual independent test receipt IDs and full AC coverage now control completion.
- A developer's successful test output cannot substitute for tester evidence. The runner records exit code, timeout/truncation, workspace mutation and role; negative/stale/fabricated receipts block.
- MR publication lacked a binding to the reviewed head and robust dedup/partial-failure behavior. The adapter now binds exact SHA, checks open remote head, paginates reads, trusts only its own actor markers, preserves fallback findings in summary, distinguishes dry-run from actual writes and reports partial failures.
- Reviewer/PRD/test receipt updates can invalidate an earlier finalization. The final gate revalidates current receipts, not just an old final status.
- Invalid output could cause repeated or misleading completion. One formatting repair is allowed; invalid receipts remain blocked afterwards. Three total autonomous implementation attempts cap rework.
- The SigNoz denylist missed other mutation surfaces. Access now starts empty and requires exact human-verified read tools plus server-side least privilege. No actual SigNoz credentials are in the package.
- Rules and workflow exceptions disagreed about when PRDs were mandatory. All code-changing flows now require a testable contract; bugs/hotfixes can use a short corrective PRD. Read-only investigation/review and human emergency containment remain separate.
- Installer preservation tests cover root CLAUDE.md/README.md/.gitignore byte equality, empty-object settings, unrelated hooks/default agent, custom-file conflicts, explicit backed-up replacement and repeat-run idempotence.

## Validation evidence
Runtime: PHP 8.4.23 (cli) (built: Jul  3 2026 12:26:56) (NTS); Linux. All test providers were controlled local fixtures.

| Suite | Named tests | Result |
|---|---:|---|
| GuardTests | 16 | PASS |
| InstallerTests | 14 | PASS |
| PrdTests | 12 | PASS |
| PublisherTests | 21 | PASS |
| WorkflowTests | 33 | PASS |

PHP lint and all 20 YAML frontmatter parses also passed. The package includes the executable regression suite, controlled provider fixtures, local self-check and machine-readable result records.

## Not verified / residual risks
- The `claude` executable was not available here. Real model behavior, tool routing, hook event delivery, installed version compatibility, settings composition and permissions require RUNTIME_SMOKE_TEST.md in your environment.
- No live GitLab/GitHub account, real MR, SigNoz endpoint/RBAC, application codebase, production workload or Laravel test database was supplied. API mocks test the adapter contract, not your actual integration.
- The installer preserved fixture project documents; the actual contents of your Laravel CLAUDE.md and project README were not inspected. Conflicting custom rules still require a deliberate human decision.
- Hooks, tickets and repository scripts are not an adversarial OS sandbox. A malicious executable test, mutable governance, another session, ignored file/submodule changes, credential exposure and filesystem/network races require external isolation and protected CI.
- A passing process plus an AC assertion reference does not prove that the test semantically covers that AC. Independent reviewer/tester judgment and human acceptance remain essential.
- Local publication locks/fingerprints are not globally exactly-once under multiple runners or ambiguous network failures. A provider version/line-anchor change can still require manual remediation.
- Mac/Windows runtime portability and full failure recovery under disk/permission faults were not exhaustively exercised. Windows is unsupported; macOS requires the documented smoke test.

## Adoption recommendation
Use v3 rather than mixing earlier agents/hooks. Start on a disposable trusted checkout, retain human merge/deploy authority, configure test-only isolation and narrow credentials, then run the real smoke checklist on a noncritical MR and bounded SigNoz query.
