# Official references checked during audit
Checked on 2026-09-09. These references justify API/configuration choices, not claims that your deployment was tested.

- Claude custom subagents, memory/tool effects, main-agent tool restrictions and frontmatter: https://code.claude.com/docs/en/sub-agents
- Claude hooks, agent_type, PreToolUse.updatedInput, Stop/SubagentStop semantics, including `background_tasks` as the documented paused-vs-done signal: https://code.claude.com/docs/en/hooks
- Project rules and existing instructions: https://code.claude.com/docs/en/memory
- GitLab MR metadata and diff versions: https://docs.gitlab.com/api/merge_requests/
- GitLab diff discussions/positions: https://docs.gitlab.com/api/discussions/
- GitHub PR review comments/commit_id/side/line: https://docs.github.com/en/rest/pulls/comments
- SigNoz MCP tools/setup/read and mutation capabilities: https://signoz.io/docs/ai/signoz-mcp-server/

Release/API behavior can change. Validate actual tool names and hook event behavior in your installed CLI/version. No undocumented `effort: pro` value is emitted by this package.
