# Routing rules

The authoritative table is `docs/ai/claude-engineering-system/ROUTING_MATRIX.md`; the per-flow detail is in
`docs/ai/claude-engineering-system/workflows/`. This file states the invariants.

## One task, one session
`task_open` binds task_id, workflow, PRD path, MR URL, reviewed head SHA and risk gates. That scope is immutable:
a different task needs a new session, and a changed scope needs a new task. Use one writer per checkout.

## Intake order
1. Classify the request into one of the 14 workflows.
2. For an existing MR/PR, the **main orchestrator** performs host/config preflight and `fetch_mr` itself, before
   any delegation. A non-allowlisted host is a configuration block reported with exact remediation - never a task
   to delegate to a specialist.
3. Determine risk gates from real impact, then `task_open`. On an MR task pass `base_sha` - the
   merge-base with the target branch from `fetch_mr`. The checkout is at the reviewed head, so the
   default base leaves the diff empty and derives no gates, and immutable scope means it cannot be
   fixed without a new task.
4. Delegate only after `task_open` succeeds.

## Read-only versus code-changing
`peer-review`, `tech-lead-review`, `engineering-manager-review`, `architecture` and `release` are read-only: no
PRD, no developer, no implementation. They end in `REVIEW_DELIVERED`, which is delivery of a review - a `FAIL`
review is a delivered result, not an acceptance.

Every other flow changes code and therefore requires a testable contract: a full PRD for features, a minimal
corrective PRD for bugs, incidents, CI failures and upgrades, and a preserved-behavior contract for refactors.

## Gate order for code-changing flows
diagnosis where the flow requires it (`qa-support` for bugs, `incident-investigator` for incidents) ->
`product-manager` -> independent `prd-reviewer` -> `architect` if the decision is material -> developer role ->
`peer-reviewer` -> specialist risk gates -> independent tester role -> `finalize` -> human review.

The developer role is determined by the flow: `hotfix-developer` for incidents, `upgrade-developer` for upgrades,
`developer` otherwise. The tester role is `regression-tester` for refactors and upgrades, `tester` otherwise.

## Specialist gates
Record semantic gates in `task_open.risk_gates`. Filename patterns in the human policy only supplement that
judgment and cannot classify a remote MR diff. The broker additionally mandates `security-reviewer` on security,
`performance-reviewer` on performance and `release-reviewer` on incident and upgrade flows.

Read-only specialists may run in parallel against the same immutable snapshot. Do not give them separate
worktrees - differing snapshots make their receipts incomparable. A gate that goes stale must be re-run.

## Failure routing
A reviewer `FAIL` on an implementation task returns to the developer within the three-attempt budget. A reviewer
`FAIL` on an MR-review task goes to the human author - there is no auto-fixer. After three implementation reports
the task requires human escalation.

## Waiting
While specialist work is in flight the session pauses. A pending receipt is not a `BLOCKED` result, and a running
specialist must not be re-delegated.
