# Laravel Claude Code Agents

A production-oriented **Claude Code engineering operating system** for Laravel/backend teams: gated product requirements, specialized engineering agents, independent review roles, exact-MR publication, test evidence, incident flows, and optional SigNoz observability.

**Current version: 3.2.0**

> This repository is the source of truth. The installer is designed to layer onto an existing project without replacing that project's `CLAUDE.md` or `README.md`.

## What is included

20 specialized roles:

- Product Manager + independent PRD Reviewer
- Architect
- Developer / Hotfix Developer / Upgrade Developer
- QA Support
- Peer Reviewer
- Tech Lead Reviewer
- Engineering Manager Reviewer
- Security Reviewer
- Database Reviewer
- Performance Reviewer
- Tester / Regression Tester
- Incident Investigator + RCA Analyzer
- Release Reviewer
- Engineering Orchestrator
- MR Review Publisher

14 documented workflows cover feature delivery, production/development bugs, peer/TL/EM review, incidents/hotfixes, performance, security, refactoring, upgrades, release readiness, architecture review, and CI failures.

## Core guarantees and boundaries

CES is designed around explicit gates rather than persona prompts alone:

- code-changing workflows require a structurally valid PRD plus independent `prd-reviewer` approval;
- Acceptance Criteria are mapped to implementation and independent executed test receipts;
- reviewers/testers are prevented from silently becoming developers through role-aware broker/hook controls;
- MR/PR review conclusions are bound to the exact reviewed head SHA;
- peer findings are returned in the console and published inline/summary to the actual MR/PR when configured;
- stale code, stale tests, stale reviews and missing mandatory specialist gates block completion;
- SigNoz access is default-deny and may be configured as read-only evidence for logs, traces, metrics and APM;
- merge, deployment and final human engineering judgment remain human authority.

This is an engineering control layer, **not** a certified sandbox or a guarantee of defect-free software. Read [SECURITY_MODEL.md](SECURITY_MODEL.md).

## Quick start

Clone this repository **outside** the Laravel project you want to install into. From the target project root:

```bash
php /absolute/path/laravel-claude-code-agents/install.php
```

Review the dry-run, then apply:

```bash
php /absolute/path/laravel-claude-code-agents/install.php \
  --apply \
  --add-gitignore
```

For an internal GitLab/GitHub Enterprise host, trust the exact hostname explicitly:

```bash
php /absolute/path/laravel-claude-code-agents/install.php \
  --apply \
  --allow-host=git.example.com \
  --add-gitignore
```

Then:

```bash
php scripts/claude/checks/self-check.php
claude --agent engineering-orchestrator
```

Run `/doctor` and the runtime smoke checklist before team-wide rollout.

## Existing Laravel instructions remain intact

Your project's current `CLAUDE.md` remains the place for project-specific Laravel conventions, architecture rules, package decisions and domain knowledge. CES installs shared engineering rules under `.claude/rules/engineering-system/` and merges its hooks into `.claude/settings.json` non-destructively.

The target project's root `README.md` is not replaced.

## MR review flow

For an existing MR:

```text
MR URL
  -> host/config preflight
  -> exact MR metadata + reviewed head SHA
  -> task_open on matching checkout
  -> peer + semantic risk reviewers
  -> MR review publisher
  -> optional independent verification
  -> human review
```

Independent read-only reviewers may run in parallel against the same immutable task snapshot.

### v3.2 lifecycle fix

Claude Code Stop hooks expose a `background_tasks` array. CES now treats a non-empty array as a **pause while specialist work is still in flight**, not task completion. The final `ces-result` gate is deferred until the parent session wakes and background work is finished. This fixes premature `BLOCKED` conclusions during parallel MR reviews.

## Runtime files and Git

For a team-shared installation, commit the agents, rules, scripts and team policy. Do **not** ignore the whole `.claude/` directory.

Local CES state should normally be ignored:

```gitignore
.claude/engineering-system/runtime/
.claude/engineering-system/backups/
.claude/engineering-system/installed-files.json
```

`--add-gitignore` adds only those entries and preserves the existing project `.gitignore`.

## Verification

Offline regression suite:

```bash
python3 -S scripts/claude/tests/test_system.py
python3 tools/package_integrity.py --check
php scripts/claude/checks/self-check.php
```

v3.2 is verified by **103 regression tests** across guards, PRD validation, workflow gates, MR publishing and installer behavior. See [TEST_REPORT.md](TEST_REPORT.md) for the scope and limitations.

GitHub Actions runs lint, integrity verification, regression tests and self-check on pushes and pull requests.

## Documentation

- [Installation](INSTALL.md)
- [Customization](CUSTOMIZATION.md)
- [MR review publishing](MR_REVIEW_SETUP.md)
- [SigNoz setup](SIGNOZ_SETUP.md)
- [Security model](SECURITY_MODEL.md)
- [Audit report](AUDIT_REPORT.md)
- [Test report](TEST_REPORT.md)
- [Changelog](CHANGELOG.md)
- [Routing matrix](docs/ai/claude-engineering-system/ROUTING_MATRIX.md)
- [Flow map](docs/ai/claude-engineering-system/FLOW_MAP.md)
- [Quality gates](docs/ai/claude-engineering-system/QUALITY_GATES.md)
- [Runtime smoke test](docs/ai/claude-engineering-system/RUNTIME_SMOKE_TEST.md)
