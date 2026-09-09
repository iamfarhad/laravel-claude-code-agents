# Test evidence rules

## Independence
Acceptance requires a check receipt recorded under a **tester** role (`tester` or `regression-tester`), of kind
`test`, for the current workspace digest. A developer's passing run cannot satisfy it, and neither can a
narrative claim that tests pass.

## Receipts are real or they are nothing
Every `check_id` cited in `ac_results` must come from a run actually performed through the broker in this task and
this workspace. Invented, borrowed, cross-task and stale IDs are rejected by the gate. Fabricating one is an
integrity failure, not a shortcut.

## Running a check
Use the broker `run_check` action with an exact preset name from the human-configured policy. There is no
arbitrary command string. The receipt records exit code, timeout, truncation, workspace mutation and role.

A run is a `FAIL` if it exits non-zero, times out, truncates its output, or mutates the tracked, unignored
workspace. Report the failure; never re-run hoping for a different outcome. If the workspace changes after a run,
the receipt goes stale and the check must be repeated.

## Coverage is a judgment, not a count
A passing process is not proof that its assertions test an AC. Read the assertion code and judge whether it
exercises the AC's `Then`. A test asserting a 200 response does not cover an authorization criterion. Verify the
negative and failure ACs specifically - they are most often mapped to tests that do not really exercise them.

Every AC must appear exactly once in `ac_results`, each with a named assertion and a real `check_id`. Missing or
duplicate entries are rejected.

## What to say when it passes
Report the gaps. What the suite does not cover is the useful part of a test report: untested branches, behavior
with no regression coverage, and anything only verifiable at runtime.

## Isolation is external
`execution_isolated: true` is a human's administrative acknowledgement that a disposable runner with test-only
data exists. It is not a sandbox, and `APP_ENV=testing` proves nothing by itself. Configured check argv is code
execution: it can read `.env` files and spawn subprocesses. Never run untrusted MR code in a session whose
filesystem holds publication or observability credentials. See `setup/CUSTOMIZATION.md`.
