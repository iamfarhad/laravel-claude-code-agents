# <Task ID> - <Short outcome-focused title>

Status: DRAFT
Owner: <real accountable human, not the model>

<!--
Structural rules enforced by scripts/claude/checks/validate-prd.php:
  * exactly ONE `Status:` metadata line, and it must read READY_FOR_ENGINEERING before implementation;
  * one non-empty `Owner:` line naming a real person - never invent an approver;
  * every `##` section below present and non-empty;
  * `Open Questions` must literally be `None` at readiness;
  * no TBD / TODO / PLACEHOLDER / FILL ME / UNKNOWN_PRODUCT_DECISION anywhere;
  * Functional Requirements listed as `- FR-01: <definition>`;
  * Acceptance Criteria as `### AC-01` blocks with Given/When/Then/Verification/Requirement;
  * every FR referenced by at least one AC, and every AC referencing a defined FR.
Content inside fenced code blocks is ignored, so examples cannot satisfy a gate.
-->

## Problem Statement
<The observed problem in user/business terms. No solution wording.>

## Context / Evidence
<Concrete evidence: tickets, logs, traces, metrics, code paths, dates with UTC plus source timezone.>

## Goals
<What must be true when this is done.>

## Non-Goals
<Explicitly excluded outcomes that a reader might otherwise assume.>

## Users / Actors
<Who acts, and with which permissions or tenancy.>

## Functional Requirements
- FR-01: <A single verifiable behavior.>
- FR-02: <A single verifiable behavior.>

## Acceptance Criteria
### AC-01: <Short name>
Given: <Precondition and fixture/data state>
When: <The exact action>
Then: <The single observable, assertable outcome>
Verification: <The named automated assertion that proves it>
Requirement: FR-01

### AC-02: <Short name>
Given: <Precondition>
When: <The exact action>
Then: <The observable outcome>
Verification: <The named automated assertion>
Requirement: FR-02

## Failure / Negative Behavior
<Invalid input, authorization denial, dependency outage, partial failure, idempotency and retry expectations.>

## Non-Functional Requirements
<Latency/throughput budgets, limits, concurrency, data volume, compatibility.>

## Observability Requirements
<Log fields, metrics, trace attributes and the SigNoz query that would evidence correct behavior.>

## Dependencies
<Services, packages, migrations, feature flags, teams. State the actual installed versions - never guess.>

## Rollout / Migration Expectations
<Order of deployment, backfill, feature flag default, rollback path and its data implications.>

## Success Metrics
<Measurable signal, current baseline and the window in which it is evaluated.>

## Risks
<What could go wrong, with the mitigation or the accepted exposure.>

## Open Questions
<List them honestly while drafting. This section must read exactly `None` before readiness. Never delete a real
question just to unblock a gate - unresolved product decisions are a BLOCKED result, not an assumption.>

## Out of Scope
<Adjacent work deliberately deferred, so reviewers do not treat its absence as a defect.>
