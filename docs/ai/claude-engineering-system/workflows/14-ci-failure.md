# ci-failure

Task workflow: `ci-failure`

diagnose isolated CI failure -> product-manager (repair contract) -> prd-reviewer -> developer -> peer-reviewer -> tester

Open with docs/prd/<task>.md. Implementation requires complete PM readiness plus independent PRD review. Complete every AC; map to code/tests and independent current test receipts. Final recommendation is READY_FOR_HUMAN_REVIEW, never automatic deployment.

Whenever peer-reviewer runs on an EXISTING MR, insert mr-review-publisher immediately after peer PASS/FAIL and preserve the full console report. A stale head requires a fresh task/review, not automatic retargeting.

Select semantic security/database/performance/TL/EM/release risk gates BEFORE implementation. Repeat every stale mandatory gate after changes. Maximum three total implementation attempts, then human escalation. Missing credentials/telemetry/product decisions are blockers, not grounds to guess.
