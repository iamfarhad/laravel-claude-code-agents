# Data integrity rules

Corrupted or lost data is the least recoverable class of defect. It outlives the deploy, the rollback and the
incident review.

## Destructive operations
No CES role deletes, truncates or rewrites data, and none does so as a side effect of a routine change. A
migration or job that removes or overwrites data is an explicit, reviewed, human-authorized release decision.
Prefer soft deletion or an archive table where the domain allows it, and state the retention consequence.

## Correctness of writes
- Make every write idempotent where it can be retried - and assume queued work, webhooks and event handlers will
  be retried and occasionally delivered twice.
- Treat read-modify-write as a race unless it is locked or expressed as an atomic operation. Increments,
  balances, counters, stock levels and status transitions are the usual casualties.
- Enforce state machines explicitly. An invalid transition must be rejected, not silently applied.
- Keep the transaction boundary around the whole invariant. A partial write that leaves the domain inconsistent
  is worse than a clean failure.
- Never let a network call inside a transaction decide whether the transaction commits.

## Money, quantities and time
Never represent money as a float. Keep currency with the amount and be explicit about rounding direction and the
point at which it happens. Store timestamps in UTC, and record the original timezone when it carries meaning.
Be explicit about precision and about which side of a boundary a comparison includes.

## Multi-tenancy and scoping
Every query that touches tenant-owned data is scoped server-side. Check global scopes, raw queries, joins,
cache keys, queued job payloads and exported files - a scope that is bypassed in one raw query is bypassed.

## Backfills and repairs
A data repair is a reviewed change with a dry-run, a bounded batch, a verification query and a documented way to
tell what it touched. "It should only affect a few rows" is not a verification.

## Evidence
When you claim data is correct, name the query or assertion that establishes it. When you cannot verify it, say
which conclusion is unverified. Never assert a row count, a distribution or a clean state you did not measure.
