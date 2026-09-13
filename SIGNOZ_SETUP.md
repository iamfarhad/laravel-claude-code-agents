# Optional read-only SigNoz evidence

SigNoz belongs in QA/production diagnosis, incidents, performance analysis, technical-lead/release verification and post-incident RCA. It is evidence, not an autonomous control plane.

Official SigNoz MCP includes mutating tools as well as reads. An agent wildcard is NOT read-only. This package denies every SigNoz tool by default and requires exact human-verified read-only names in config plus a least-privilege account enforced by SigNoz itself.

## Register user-scoped MCP
Use the official SigNoz setup appropriate to your Cloud/self-hosted deployment; server alias must be `signoz` for this package's tool policy. Cloud example:
```bash
claude mcp add --scope user --transport http signoz https://mcp.YOUR-REGION.signoz.cloud/mcp
```
Replace the region using your real SigNoz deployment instructions; it is not a working default. Use `/mcp` to authenticate and inspect available tools. For self-hosted, install the official server from your approved distribution and keep URL/API key in user secret storage, not project files or this archive.
The official SigNoz plugin is another setup route. If it registers a different MCP alias, explicitly align it with this package and inspect tool names; do not simply enable wildcard mutations to make it work.

## Add only verified read tools
After inspecting your actual `/mcp` tool names, merge an explicit allowlist such as:
```json
{
  "signoz_read_tools": [
    "mcp__signoz__signoz_search_logs",
    "mcp__signoz__signoz_search_traces",
    "mcp__signoz__signoz_get_trace_details",
    "mcp__signoz__signoz_query_metrics",
    "mcp__signoz__signoz_list_services"
  ]
}
```
Names above follow the official documented tools; actual client namespaces/version can differ. If mismatched, remain blocked until a human verifies and updates exact names. Do not allow generic executors or create/update/delete tools. The naming check is supplementary, not a replacement for reviewing tool behavior/permissions.

## Expose the server to the roles that need it
Every CES role declares an explicit `tools:` allowlist in its frontmatter, and Claude Code hides any MCP tool that
allowlist does not name. Allowlisting a tool in `signoz_read_tools` is therefore necessary but not sufficient:
until the role's frontmatter also lists the SigNoz server, the tool never reaches the agent and the role must
report telemetry as unavailable. The roles written to use telemetry are `incident-investigator`, `qa-support`,
`performance-reviewer`, `release-reviewer` and `tech-lead-reviewer`.

Claude Code accepts the server-level form in agent frontmatter, so append it to the `tools:` line of each role you
want to have evidence access:
```yaml
tools: Read, Grep, Glob, Bash, mcp__signoz__*
```
That entry is deliberately not shipped by default, and it is NOT a read-only grant by itself: what keeps the role
read-only is the PreToolUse hook, which denies every SigNoz call whose exact name is not in `signoz_read_tools`
and whose name does not look like a read/query tool. Keep both layers - never widen the config allowlist to make a
tool "work". `php scripts/claude/checks/self-check.php` warns when a telemetry role has no SigNoz entry, and
fails when a frontmatter names a specific SigNoz tool that the config does not allowlist.

Frontmatter edits are package-owned files: a later `install.php --replace-existing` backs them up and replaces
them, so re-apply the `tools:` change after an upgrade and re-run the self-check.

## Query discipline
Use bounded time windows and service/environment/release/tenant filters. Record UTC plus original timezone, query parameters, trace references, sample sizes and sampling/retention caveats. Correlation does not establish cause. Avoid customer payloads and credentials in console/MR artifacts.
For performance, compare equivalent load/data/version windows and include errors/throughput, not just favorable p95. For release, distinguish planned monitoring from observations actually made after human deployment.
When unavailable, return OBSERVABILITY_UNAVAILABLE and state which conclusions cannot be verified. Local code/test evidence may support narrower findings, but never fabricate production traces, zero errors or improvement metrics.

Live connectivity and your RBAC configuration were not tested in this audit. Use a non-sensitive read query to verify them before the first operational task.
