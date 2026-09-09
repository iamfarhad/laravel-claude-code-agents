# Review severity and finding quality

## The four severities
- **BLOCKING** - must not ship as-is: incorrect behavior, a security or data-integrity exposure, a broken
  contract, or an irreversible step without a rollback. A `PASS` or `IMPLEMENTED` report may not contain one; if
  you found a blocker, the status is `FAIL`.
- **WARNING** - a real risk a human may knowingly accept, with the trade-off stated.
- **SUGGESTION** - a genuine improvement that is not a risk.
- **NIT** - cosmetic. Console-only by default; not published to an MR unless a human enables it.

Do not inflate severity to appear thorough, and do not deflate it to be agreeable. Calibration is the whole value
of an independent review.

## Every finding needs five things
`severity`, `location` (real `path:line` from actual inspection), `problem` (the specific defect),
`impact` (the concrete consequence) and `evidence` (the verified path, test or measurement). Publishable comments
additionally need a stable `id` and a `recommended_direction` - a narrow correction, not a rewrite.

A finding without a mechanism is an opinion. "This could be a problem" is not reviewable; "this path accepts an
unvalidated tenant id, so actor A can read actor B's rows" is.

## Precision rules
- Point at code you actually read. A fabricated path, line or test name is an integrity failure, not a typo.
- Say what you did **not** inspect. An unexamined surface is an `unknown`, never an implicit pass.
- One finding per defect. Do not bundle three problems into one comment, and do not split one problem across
  three to raise the count.
- Review against the project's existing conventions in `CLAUDE.md`, not a style the project does not use.
- Do not restate another reviewer's finding as your own. Specialists cover distinct dimensions on purpose.

## Reviewers do not fix
No reviewer or tester has a write tool. Findings go to the author. On an MR-review task the author is the human
who opened it; there is no auto-fixer.

## Binding
Review conclusions bind to the workspace digest, and MR conclusions bind to the exact reviewed head SHA with a
clean tracked checkout. If the code or the remote head moves, the review is stale and must be re-run - old
findings are never retargeted at new code.
