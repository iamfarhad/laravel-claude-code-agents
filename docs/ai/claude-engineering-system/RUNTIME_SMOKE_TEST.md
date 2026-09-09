# First real Claude Code smoke test (manual)

This checklist is required because the archive's regression tests mock event inputs/providers, not a running Claude installation.

1. Install into a disposable, trusted Git checkout with an initial commit. Keep real production data and credentials out. Run self-check and `/doctor`.
2. Start `claude --agent engineering-orchestrator`. Ask for a local peer-review task without MR publication. Verify task_open/context broker calls work and task_status records the correct role/session.
3. Ask a read-only CES role to run a harmless raw `echo smoke-test` command. It should be denied because only the broker envelope is allowed. Do not test destructive commands. Verify a read-only Write attempt on a disposable test path is denied.
4. Have product-manager draft a small PRD, then independent prd-reviewer assess it. DRAFT, missing AC fields and changed PRD hashes must block developer delegation. Never remove open questions just to force readiness.
5. Configure a safe isolated fixture/test preset. Verify a genuine tester run creates a receipt and a made-up check_id is rejected. Modify a disposable source file and verify the old test/review receipt no longer satisfies finalization.
6. Use a noncritical authorized MR for live dry-run first, then one intentionally authorized comment. Confirm exact commit, rendered anchor, summary, and rerun dedup. Change the branch head and verify stale review blocks. Do not run untrusted MR application code with the publishing credentials.
7. Register SigNoz at user scope; inspect exact tools and least-privilege access. Run a bounded non-sensitive read. Ensure a nonallowlisted tool is denied without attempting production mutation.
8. Verify the final response includes full console findings plus actual publication state and never says merged/deployed. Keep the run's CLI version and sanitized results for your team.

If your CLI does not provide the documented hook fields or correctly apply updatedInput, stop adoption and adjust/test for that exact version. Existing user/managed hooks may affect composition. A static PASS cannot replace this integration check.
