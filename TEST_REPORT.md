# Test report - v3.2.3

Date: 2026-09-09. Result: **PASS, 110 named tests, 0 failures, 0 errors.**

v3.2.1 re-ran the suite on macOS (Darwin 25.6, PHP 8.5.10) in addition to Linux. That second platform
exposed a real defect: the PreToolUse guard compared the raw session `cwd` against a `__DIR__`-derived
root, so any checkout reached through a symlinked ancestor had every tool call denied. It is fixed, and
all 103 tests now pass on both platforms. The restored agent/rule/config source is covered by the
self-check (20 agent frontmatters, hook fragment, 21 PHP files) and by the installer group. The final exact source state was re-verified by test group after the all-suite wrapper hit an environment wall-clock timeout; all five groups passed independently.

Coverage groups:
- GuardTests: 20
- PrdTests: 12
- WorkflowTests: 35
- PublisherTests: 24
- InstallerTests: 19

Reproduce locally:
```bash
python3 -S scripts/claude/tests/test_system.py
python3 tools/package_integrity.py --check
php scripts/claude/checks/self-check.php
```

v3.2 adds regression coverage for the Claude Code Stop lifecycle when `background_tasks` is non-empty. In that state the main session is paused waiting for in-flight background work and the final CES result gate is intentionally deferred; after background work completes, normal receipt, MR-publication and finalization requirements still apply.

Existing coverage remains for shell/policy bypasses, role/PRD gates, task immutability, AC evidence, stale evidence, MR publication SHA binding/dedup/fallback, provider errors, installer preservation/conflicts, host allowlisting, and runtime `.gitignore` management.

Machine-readable results are stored at `docs/ai/claude-engineering-system/audit/offline-test-results.json` and `v3.2-regression-summary.json`.

No live GitLab/GitHub account, SigNoz instance, Claude Code UI/runtime, or target Laravel application was exercised by this offline suite. Run the documented runtime smoke test in your own environment before team-wide rollout.
