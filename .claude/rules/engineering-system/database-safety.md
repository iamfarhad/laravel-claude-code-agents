# Database safety rules

No CES role runs a migration, a backfill, a rollback or any statement against a database. Migrations are code to
be written and reviewed here; running them is a deployment step under human authority.

## Live-table safety
Assess the locking behavior of each statement on the **engine and version this project actually uses**, not on a
different engine where the operation happens to be online. Adding a column with a default, changing a column
type, adding an index, adding a foreign key and renaming a column all have materially different costs. If the
engine version or the table's row count is not established by something you read, say which conclusion depends
on it.

## Reversibility
Every migration needs a `down()` that genuinely restores the prior state. A `down()` that loses data is not a
rollback. Any statement that drops, truncates or rewrites data is a human release decision: surface it as a
BLOCKING finding for release review rather than treating it as routine.

## Deploy compatibility
The old code must run against the new schema, and the new code against the old schema, for the duration of the
deploy. Prefer expand-then-contract: add, backfill, switch reads, then remove in a later release. Where an
ordering constraint is unavoidable, state it explicitly for the release reviewer.

## Indexes
An index must match the query's actual predicate and ordering, with correct column order in composite indexes.
Note selectivity, redundancy with existing indexes, and the write-path cost. An index added "to be safe" is a
cost with no established benefit.

## Backfills
Chunked, idempotent, resumable and throttled, with defined behavior when rows change mid-run. A backfill inside a
migration blocks the deploy; separate them unless the data volume is genuinely trivial and you can say why.

## Transactions and concurrency
Keep transaction scope narrow. Know which statements cannot participate. Watch lock ordering across tables for
deadlock potential, and treat read-modify-write as a race unless it is locked or atomic. Do not rely on an
isolation level the project does not configure.

## Integrity
Prefer enforcing invariants in the schema - nullability, defaults, uniqueness, foreign keys and deliberate cascade
behavior - over enforcing them only in application code. State what the schema cannot enforce, and see
`data-integrity.md`.
