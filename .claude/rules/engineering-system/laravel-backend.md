# Laravel / backend implementation rules

Project-specific conventions live in this project's own `CLAUDE.md` and take precedence. These are baseline
engineering expectations for CES developer roles.

## Follow the code that is already there
Match the surrounding structure, naming and idiom before introducing a pattern the project does not use. Read
neighbouring classes and the existing tests first. Consistency with the codebase beats personal preference, and a
new pattern needs a stated reason - or an ADR when it is material.

## Never guess the environment
Read `composer.json`, `composer.lock` and the installed vendor tree for actual versions before using an API. Do
not rely on remembered framework behavior across major versions. A feature you are not certain exists in the
installed version is an unknown, not an assumption.

## Boundaries
- Controllers coordinate; they do not hold domain logic. Keep business rules in domain/service classes that are
  testable without HTTP.
- Validate at the boundary with a Form Request or explicit validation, not with ad-hoc checks scattered downstream.
- Authorize with policies/gates on the actual object being acted on, server-side. Never trust an id from input.
- Return purposeful response shapes through resources/DTOs rather than leaking a model's full attribute set.

## Data access
- Eager-load deliberately; assume every relation accessed in a loop is an N+1 until proven otherwise.
- Every list endpoint and every batch job is paginated or chunked. Unbounded queries are defects.
- Keep transactions narrow and explicit, and know which statements cannot take part in one. Treat
  read-modify-write as a race unless it is locked or made atomic.
- Make queued jobs and event handlers idempotent: they will be retried and occasionally delivered twice.

## Configuration and secrets
Read configuration through the config layer, never `env()` outside config files. Never hardcode a credential, a
host or a tenant id. `.env` files are protected from writing and from reading.

## Errors and observability
Fail loudly and specifically - no empty catch, no swallowed exception, no error path that silently returns a
success shape. Log with structured context and without PII or secrets. See `observability.md`.

## Tests belong with the change
Write the tests your `ac_mapping` references, asserting behavior rather than implementation detail. Cover the
negative and authorization paths named in the ACs. A test that executes a path without asserting its outcome is
not coverage.

## Migrations
Schema work follows `database-safety.md` and is reviewed by `database-reviewer`. Never write a destructive or
irreversible data operation as part of a routine change.
