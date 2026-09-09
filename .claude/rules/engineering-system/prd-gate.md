# Product contract gate

No code-changing workflow proceeds without a structurally valid PRD and an independent reviewer's approval, both
bound to the current PRD hash.

## What the validator enforces
`scripts/claude/checks/validate-prd.php` requires: exactly one `Status:` line reading `READY_FOR_ENGINEERING`;
one non-empty `Owner:`; every required `##` section present and non-empty; `Open Questions` literally `None`; no
TBD/TODO/PLACEHOLDER/FILL ME/UNKNOWN_PRODUCT_DECISION; Functional Requirements as `- FR-01: ...`; Acceptance
Criteria as `### AC-01` blocks with Given, When, Then, Verification and `Requirement: FR-xx`; every FR covered by
an AC and every AC referencing a defined FR. Fenced code blocks are ignored, so an example cannot satisfy a gate.

Structural validity establishes that the contract is complete enough to review. It does not establish product
correctness, feasibility, stakeholder agreement or absence of defects.

## Independence
The `product-manager` writes it; the `prd-reviewer` assesses it. The same role cannot do both, and readiness alone
does not unlock implementation - the independent `PASS` does. The reviewer assesses substance: verifiability of
each AC, coverage of failure and authorization behavior, internal consistency, honesty about unknowns, and scope
discipline on corrective contracts.

## Writing acceptance criteria
Each AC is one observable outcome with a named automated verification. If the verification cannot be named, the
criterion is not ready. Cover the negative paths explicitly - authorization denial, invalid input, dependency
outage, partial failure, retries, idempotency - because reviewers and testers are gated on the ACs as written.

## Honesty
Never remove a real open question, invent an approver, or assert an unverified version or baseline to reach
readiness. An unresolved product decision is `NEEDS_INFORMATION` or `BLOCKED`. A model cannot create stakeholder
approval.

## Freshness
Any edit to the PRD changes its hash and invalidates the product and reviewer receipts, and with them the
developer's write access. Re-approve rather than working around the block.

## Minimal corrective contracts
Bugs, incidents and CI failures use the smallest contract that covers the reproduced evidence. Refactors and
upgrades state preserved behavior as the requirement. Do not expand scope while a defect is open.
