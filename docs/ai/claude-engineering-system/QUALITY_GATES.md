# Quality gates
1. Intake binds task, workflow, PRD path, existing MR SHA and semantic risk gates.
2. Product gate structurally validates every required section/FR/AC, then requires independent author/reviewer receipts bound to the PRD hash.
3. Implementation gate denies protected paths and requires current product readiness and diagnosis where needed. Three total implementation attempts.
4. Peer/specialist results bind to current repository snapshot. Real blockers cannot be hidden under PASS.
5. Publication binds to the exact reviewed open MR head, deduplicates authenticated-actor comments with pagination, and preserves summary fallbacks. DRY_RUN/partial/stale does not pass.
6. Acceptance gate requires every AC to reference an independent real passing test receipt for the same workspace. Tests mutating tracked/unignored workspace, timing out or truncating output fail.
7. Finalize requires fresh relevant receipts and publication. Main Stop validates current receipts again. REVIEW_DELIVERED and READY_FOR_HUMAN_REVIEW are recommendations only.

These gates enforce shape, freshness and process evidence, NOT formal proof. Hooks can be disabled; repository scripts/tests can be malicious; regular non-CES sessions are out of scope. Protected CI/human review and external sandbox/least privilege are required for strong enforcement.
