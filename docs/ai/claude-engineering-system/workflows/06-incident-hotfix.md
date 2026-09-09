# incident

Task workflow: `incident`

incident-investigator -> product-manager (minimal corrective PRD) -> prd-reviewer -> hotfix-developer -> peer-reviewer -> specialists -> tester -> release-reviewer -> human release -> later RCA

Open with docs/prd/<task>.md. Implementation requires complete PM readiness plus independent PRD review. Complete every AC; map to code/tests and independent current test receipts. Final recommendation is READY_FOR_HUMAN_REVIEW, never automatic deployment.

Whenever peer-reviewer runs on an EXISTING MR, insert mr-review-publisher immediately after peer PASS/FAIL and preserve the full console report. A stale head requires a fresh task/review, not automatic retargeting.

Select semantic security/database/performance/TL/EM/release risk gates BEFORE implementation. Repeat every stale mandatory gate after changes. Maximum three total implementation attempts, then human escalation. Missing credentials/telemetry/product decisions are blockers, not grounds to guess.

Read-only investigation and human emergency containment may start immediately. Do not delay a human incident commander for a full product-planning exercise. AI hotfix code still needs a short explicit contract. Post-release verification and RCA require actual new evidence; pre-release PASS does not prove recovery.
