# engineering-manager-review

Task workflow: `engineering-manager-review`

engineering-manager-reviewer -> required technical/operational specialists -> human manager

This is READ-ONLY analysis/review. No new PRD or developer delegation is required. Finish REVIEW_DELIVERED after current primary/specified specialist receipts. A FAIL review can be delivered; it is not acceptance of the change. Escalate missing evidence as BLOCKED.

Whenever peer-reviewer runs on an EXISTING MR, insert mr-review-publisher immediately after peer PASS/FAIL and preserve the full console report. A stale head requires a fresh task/review, not automatic retargeting.

Select semantic security/database/performance/TL/EM/release risk gates BEFORE implementation. Repeat every stale mandatory gate after changes. Maximum three total implementation attempts, then human escalation. Missing credentials/telemetry/product decisions are blockers, not grounds to guess.
