# Peer review: console plus actual MR/PR comments

The code reviewer analyzes; mr-review-publisher publishes the stored result. The main console report retains ALL findings, including NITs. This separation is intentional.

## Configure trusted hosts and identity
Manually set `allowed_hosts` in `.claude/engineering-system/config.json`, for example `["gitlab.your-company.example", "github.com"]`, or rerun the installer with an explicit host trust flag such as `--allow-host=git.internal.example`. Only exact HTTPS MR/PR URLs on that list are accepted; no credentials/query/fragment, wildcard or custom port.
Authenticate the appropriate CLI as a limited bot or your explicit review identity:
```bash
glab auth status
gh auth status
```
Configure tokens outside version-controlled files and ensure the account can read the MR and create comments. Do not run untrusted application tests in the same credential-exposed runtime; see SECURITY_MODEL.md.

## Review request
Start `claude --agent engineering-orchestrator` and provide the actual URL plus your role:
```text
Review https://gitlab.your-company.example/group/project/-/merge_requests/123 as a peer developer.
Return the full findings in the console and publish them to this MR.
Do not modify code, approve, merge or resolve discussions.
```
Before delegation, the MAIN orchestrator reads the human policy, verifies the MR host is allowlisted, fetches metadata, and opens a read-only task with the exact head SHA. The fetch returns a bounded summary and the changed-file list, not the diff bodies: pick risk gates from those paths and change kinds, and read the code itself from the clean local checkout at the reviewed head. If the host is not trusted, it must stop with the exact configuration remediation; it must not spawn a specialist to diagnose configuration. A human/CI must provision a clean checkout at that same commit. A new human push requires new review evidence; the publisher never silently retargets old findings.

## Publication behavior
- Inline findings use exact side/path/line (GitLab also diff refs/old path as appropriate).
- Unknown anchors use line:null; invalid-anchor responses 400/422 fall back to summary.
- A stable summary retains all publishable findings and reviewed commit, whether inline succeeded or not.
- Full pagination is required before dedup. Only the authenticated publisher's markers suppress repeats.
- NITs are console-only by default. No custom fingerprint from an agent is trusted.
- Current open head is checked before each write; local lock limits concurrent same-checkout publication.
- Authentication, rate limits, read failures and partial writes are BLOCKED. Do not blanket-retry ambiguous POST failures.
- PUBLISHED, PUBLISHED_WITH_FALLBACK and ALREADY_PUBLISHED can satisfy the gate. DRY_RUN cannot.
No approval/request-changes review-state, merge, close, resolve, rebase or push operation is provided.

## Human/CI diagnostic adapter
The role broker normally supplies the stored peer receipt. To manually test a prepared payload after reviewing it:
```bash
php scripts/claude/mr/publish-review.php --dry-run < /secure/path/review.json
```
Template: docs/ai/claude-engineering-system/templates/mr-review-publish.json. Its example hash/content must be replaced with ACTUAL inspected evidence. Dry run fetches metadata/comments but performs zero POSTs. Remove --dry-run only when you intentionally authorize posting those exact comments. Agents cannot run this unrestricted manual entrypoint from their Bash tool.

## Verification boundary
Offline tests exercise both provider payload shapes, pagination, stale/closed heads, fallback/dedup, foreign-actor markers, zero-write dry runs, partial failures and a local lock. Live glab/gh authentication, provider versions, visibility rules and comment rendering still need a real noncritical test MR in your environment.
