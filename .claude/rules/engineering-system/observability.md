# Observability rules

Telemetry is evidence. It is not a control plane, and it is not a substitute for reading the code.

## Access is default-deny
Every SigNoz MCP tool is denied unless a human has added its exact name to `signoz_read_tools` in
`.claude/engineering-system/config.json`, and the name must be a read/query tool. A wildcard is not read-only:
the official server also exposes mutating tools. Server-side least privilege is required as well - the local
allowlist is a supplementary check, not the enforcement. See `setup/SIGNOZ_SETUP.md`.

No CES role creates, updates or deletes a dashboard, an alert or any telemetry object.

## Query discipline
- Bound every query by time window, and filter by service, environment, release and tenant.
- Record the exact query parameters, the window in UTC **and** the original timezone, the sample size, and any
  sampling or retention caveat that affects the conclusion.
- Correlation is not cause. A spike that begins at a deploy is a strong lead and not a mechanism; trace it to the
  code path that produces the failure before calling it a cause.
- For performance, compare equivalent load, data volume, version and environment windows, and report throughput
  and error rate alongside a latency distribution - never a favorable p95 alone.
- For release verification, distinguish planned monitoring from observations actually made. Before a human
  deploys there are no post-deploy observations.

## When telemetry is unavailable
Return the honest limitation and state which conclusions cannot be verified. Local code and test evidence may
support a narrower finding. Never fabricate a trace, a metric, a zero-error window or an improvement percentage.

## What to instrument
Structured logs with correlation and tenant identifiers, metrics for the behavior an AC actually asserts, and
trace attributes at the boundaries where latency and failure originate. A PRD's Observability Requirements section
should name the query that would evidence correct behavior.

## Never leak
Keep customer payloads, credentials, tokens and PII out of logs, traces, metric labels, console reports and MR
comments. Reference a location instead of quoting sensitive content.
