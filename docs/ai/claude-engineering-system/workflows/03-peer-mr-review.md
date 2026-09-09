# peer-review

Task workflow: `peer-review`

peer-reviewer -> mr-review-publisher -> optional tester -> human author/reviewer

This is READ-ONLY analysis/review. No new PRD or developer delegation is required. Finish REVIEW_DELIVERED after current primary/specified specialist receipts. A FAIL review can be delivered; it is not acceptance of the change. Escalate missing evidence as BLOCKED.

Whenever peer-reviewer runs on an EXISTING MR, insert mr-review-publisher immediately after peer PASS/FAIL and preserve the full console report. A stale head requires a fresh task/review, not automatic retargeting.

Select semantic security/database/performance/TL/EM/release risk gates BEFORE implementation. Repeat every stale mandatory gate after changes. Maximum three total implementation attempts, then human escalation. Missing credentials/telemetry/product decisions are blockers, not grounds to guess.

Fetch canonical URL and full head SHA before task_open. Human/CI provisions a clean checkout at that head. Findings go to the original human author, not an auto-fixer. NITs console-only. Publishing is not approving or requesting changes in provider review state.
