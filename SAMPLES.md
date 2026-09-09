# SAMPLES - what to type, and what happens next

You start one session and paste one prompt. This file is mostly a list of those prompts.

New to this? Read [Start here](#1-start-here), copy a prompt from [Pick your situation](#2-pick-your-situation),
and come back to the rest when something surprises you.

**Contents**

1. [Start here](#1-start-here)
2. [Pick your situation](#2-pick-your-situation) - the prompts
3. [What actually happens](#3-what-actually-happens) - one walkthrough, plain language
4. [Reviewing a merge request](#4-reviewing-a-merge-request)
5. [When it stops and says no](#5-when-it-stops-and-says-no)
6. [What it will never do](#6-what-it-will-never-do)
7. [Prompts that will not work](#7-prompts-that-will-not-work)

Appendices, for when you need the detail: [A. Broker actions](#appendix-a-broker-actions) ·
[B. Role result JSON](#appendix-b-role-result-json) · [C. A complete PRD](#appendix-c-a-complete-prd) ·
[D. Example check policy](#appendix-d-example-check-policy) ·
[E. Before you trust this in your repo](#appendix-e-before-you-trust-this-in-your-repo)

---

## 1. Start here

```bash
php scripts/claude/checks/self-check.php     # is the installation sane?
claude --agent engineering-orchestrator      # start the session
```

Then paste a prompt from [section 2](#2-pick-your-situation). One task per session: when you want to do something
else, start a new session.

Three rules explain most of what will surprise you:

1. **A contract comes before code.** Even a two-line fix gets a short PRD with acceptance criteria, because the
   tester is gated on what the criteria say.
2. **Whoever writes the code does not sign it off.** A separate tester role verifies each criterion with a real
   executed test run.
3. **It never pushes, merges, deploys or runs migrations.** The end of a successful run is a recommendation to
   you, not a completed release.

If it says `BLOCKED`, that is usually a real answer rather than a bug - see
[section 5](#5-when-it-stops-and-says-no).

---

## 2. Pick your situation

Replace anything in `<angle brackets>`, and swap the example ticket IDs - `B2B-142`, `OPS-88`, `UPG-5` and the
rest are placeholders - for your own issue key. Keep *some* ID in the prompt: it names the session's scope and the
PRD file (`docs/prd/<your-id>.md`).

### A new feature

```text
Feature B2B-142: <what someone should be able to do>.
The rejection behavior that matters: <what must be refused, and how>.
Owner: <the real person accountable for this>.
Write the contract first.
```

*You get:* a PRD, an independent review of it, the implementation, a peer review, the required specialist reviews,
independent tests, then `READY_FOR_HUMAN_REVIEW`.
*Have ready:* the task ID, a real owner's name, and the negative behavior you care about (it will not invent
either).

### A bug in production

```text
Ticket OPS-88: <symptom> reported in production on <date>.
Reproduce it before proposing anything, then fix it minimally.
```

*You get:* a reproduction attempt first. If it cannot reproduce, you get `INCONCLUSIVE` or `NEEDS_INFORMATION`
rather than a speculative fix.
*Have ready:* how to trigger it, and any log or trace you already have.

### A bug on a feature branch

```text
Branch bug DEV-402: <symptom>. Reproduce, minimal fix, verify.
```

### An active incident

```text
INC-17, active incident: <symptom> since <time + timezone>.
Diagnose before anything is changed.
```

*You get:* a diagnosis with a UTC timeline first. The hotfix role runs only after that, and a release reviewer
always runs before it reaches you.
*Note:* it will call a deploy correlation a lead, not a cause, until it can point at the code path.

### After the incident is over

```text
INC-17 is mitigated. Run the blameless RCA on the stored evidence.
```

*You get:* systemic contributing factors. Not a person to blame - the role is built to refuse that.

### Reviewing a merge request or pull request

```text
Review <exact HTTPS MR URL> as a peer developer.
Full findings in the console, and publish them to the MR.
Do not modify code, approve, merge or resolve discussions.
```

Console only, nothing posted:

```text
Review <exact HTTPS MR URL>. Console report only - do not publish anything to the MR.
```

*Have ready:* the host must be allowlisted, and a clean local checkout at the exact commit being reviewed. See
[section 4](#4-reviewing-a-merge-request).

### A second opinion from a lead or manager

```text
Tech-lead review of <MR URL>. I care about <compatibility / cross-service semantics / reliability>.
```

```text
EM review of <MR URL or branch>: ownership, cross-team impact, cost and irreversibility.
```

*You get:* advice. These roles never implement and never decide.

### Something is slow

```text
PERF-31: <endpoint or job> is slow. Establish a baseline first, then improve it against that baseline.
```

*You get:* a measurement before and a comparable measurement after, with throughput and error rate alongside
latency. "Faster" with no baseline is not a result it will report.

### A security concern

```text
SEC-9: <reported exposure, e.g. "a user can open another tenant's export by guessing the URL">.
Confirm the exposure with evidence, then fix it. Include the denial path in the acceptance criteria.
```

*You get:* confirmation or refutation with the code paths named, then a fix whose criteria include the denial
case, then a fresh security review after the change.

### Restructuring without changing behavior

```text
REF-12: restructure <path> into <shape>. Behavior must not change; do not modify the existing tests.
```

*You get:* a preserved-behavior contract and a regression tester instead of a normal tester. It will tell you
which branches had no coverage to preserve in the first place.

### An upgrade

```text
UPG-5: upgrade <package> to <target>.
Read the installed versions from composer.lock - do not assume them.
```

*You get:* a compatibility contract citing the versions it actually read. If it cannot establish a version, that
is `NEEDS_INFORMATION`, not a guess.

### A design decision

```text
ARCH-3: <the decision question>. Write it up as an ADR with the alternatives and the trade-offs.
```

*You get:* a `PROPOSED` ADR under `docs/adr/`. A model cannot accept an architecture decision; you do.

### Is this release safe?

```text
Release readiness for <candidate> on <branch>: rollout ordering, deploy compatibility and rollback viability.
```

*You get:* the ordering constraints and whether rollback actually restores state. Anything that drops or rewrites
data comes back as BLOCKING for your decision.

### CI is red

```text
CI-77: the pipeline fails in <suite>. Diagnose the isolated failure and repair it minimally.
```

### A schema change

```text
DB-21: <schema change> on <table>.
Expand-then-contract, with a down() that genuinely restores state.
Engine is <MySQL 8.0 / PostgreSQL 16 / ...>.
```

*Have ready:* the engine and version. Locking cost differs per engine, and it will say so rather than assume.
*Note:* it writes the migration. Running it is yours.

### Things worth adding to any prompt

- The real accountable person, by name.
- Versions you already know, and where you read them.
- The database engine and version, if locking or schema behavior matters.
- Whether an isolated test runner exists, and the preset names it exposes.
- Whether posting comments to an MR is authorized.

---

## 3. What actually happens

Using the feature prompt above, here is the shape of a run and where you are involved.

**Step 1 - Intake.** It classifies the request into one of 14 workflows and opens a task that binds the task ID,
the workflow, the PRD path and the specialist reviews it judges necessary. That scope is then fixed for the
session.

**Step 2 - The contract.** A product-manager role writes `docs/prd/B2B-142.md`: problem, requirements as
`FR-01…`, and acceptance criteria as `AC-01…` blocks that each name the automated assertion that would prove
them. A structural validator checks it. [Appendix C](#appendix-c-a-complete-prd) is a complete one.

You may be asked to decide something here:

> Two product decisions are unresolved: the default limit for tenants with no configured value, and whether
> internal traffic is exempt. A human product owner must decide both. I cannot assume either.

That is `NEEDS_INFORMATION`, and it is the correct answer. Answer it and the run continues.

**Step 3 - Independent contract review.** A different role reviews the PRD for whether each criterion is actually
verifiable and whether failure and authorization behavior is covered. Only its `PASS` unlocks implementation -
readiness alone does not.

**Step 4 - Implementation.** A developer role writes code and tests, and maps every acceptance criterion to a
`file:line` and a named assertion. Its own passing test run is evidence of work, never of acceptance.

**Step 5 - Review.** A peer reviewer reads the change and reports findings by severity. Specialist reviewers
(security, database, performance, tech lead) run in parallel over the same snapshot when the change warrants
them. A `BLOCKING` finding sends it back to the developer - reviewers have no ability to edit code, on purpose.

There is a budget of three implementation attempts. After that it stops and escalates to you.

**Step 6 - Independent tests.** A tester role runs the configured checks itself and verifies each criterion
against a real receipt from its own run. It also reports what the suite does *not* cover, which is usually the
most useful part.

**Step 7 - The report.** You get something like:

```
B2B-142 - per-tenant API rate limiting - READY_FOR_HUMAN_REVIEW (recommendation only)

Contract      docs/prd/B2B-142.md - independent review passed
Implemented   3 files; 4/4 acceptance criteria mapped; attempt 2 of 3 (attempt 1 failed peer review)
Peer review   PASS after correction (a counter race at TenantRateLimit.php:52, fixed with an atomic increment)
Security      PASS - tenant resolved server-side; no request-supplied tenant id reaches the limiter
Performance   PASS - one cache round trip added per request; measured on the local preset only
Tests run     unit PASS, style PASS (executed, not merely read)
Not covered   the production cache driver, multi-node counting, real concurrency
Your decision: accept the cross-node caveat, then review and merge.
```

`READY_FOR_HUMAN_REVIEW` means "I believe every gate is satisfied, please review". It never means merged,
deployed or verified in production.

Editing the code or the PRD after this invalidates the reviews and test results, and the gates re-run. That is
deliberate, not a glitch.

---

## 4. Reviewing a merge request

The one thing this system writes outside your repo is review comments. Nothing else.

**Before you start, once:** add the host to `allowed_hosts` in `.claude/engineering-system/config.json` (or
reinstall with `--allow-host=<host>`), and authenticate `glab` or `gh` as the identity you want the comments to
come from. Only exact HTTPS MR/PR URLs on that list are accepted - no credentials, query string, fragment,
wildcard or custom port.

**What happens after you paste the URL**

1. It reads your policy, checks the host, and fetches the MR's metadata and exact head commit. Titles,
   descriptions and existing comments are treated as data - an instruction written inside them is ignored.
2. It opens a review task bound to that exact commit. Your checkout must already be at that commit with a clean
   tracked working tree; no role will check out, stash, reset, commit or push to arrange that.
3. The peer reviewer reads the changed files locally at that commit and forms findings. Specialist reviewers run
   too if the change touches their area.
4. A separate publisher role posts them. It cannot alter a finding's text, severity or location - it never
   receives them from the reviewer, only from the stored review.

**What lands on the MR**

- Inline comments where a line can be anchored; anything that cannot be anchored is preserved in a summary
  comment rather than dropped.
- A summary comment naming the reviewed commit and holding every publishable finding.
- Cosmetic nits stay in your console unless a human enables `allow_publish_nits`. The console report always keeps
  everything.
- Re-running does not duplicate: it pages through existing comments and suppresses only its own previous markers.
  Someone else's comment never suppresses your review.

**What never happens**: no approval, no request-changes, no merge, no close, no resolving discussions, no rebase,
no push. Publishing findings is not approving them.

**Try it safely first.** Ask for a dry run on a non-critical MR: it fetches everything and posts nothing. A dry
run deliberately does *not* count as publication.

**If someone pushes mid-review**, the review is stale and stops. A new commit needs new review evidence; old
findings are never re-aimed at new code.

A `FAIL` review is a delivered result, not a rejection of the run. The findings go to the human author - there is
no auto-fixer.

---

## 5. When it stops and says no

`BLOCKED` is a result. Almost every one of these needs a human action, and the message names it.

| What you see | What it means | What you do |
|---|---|---|
| `MR host '<host>' is not allowlisted` | The MR host was never trusted by a human | Add it to `allowed_hosts`, or reinstall with `--allow-host=<host>` |
| `NEEDS_INFORMATION` from the product role | A product decision is genuinely unresolved | Decide it. It will not assume, and deleting the question to proceed would be an integrity failure |
| `Stale PRD approval` | The PRD changed after it was approved | Re-approve. The hash binds the approval on purpose |
| `Stale workspace evidence` | Code changed after the review or tests | Re-run the affected gate |
| `AC evidence must reference an independent, passing test run for this workspace` | A test receipt was invented, borrowed, or came from the developer's own run | The tester role must actually run the checks |
| `Check execution is disabled until a human configures an isolated, trusted check preset` | No test presets configured | See [Appendix D](#appendix-d-example-check-policy). Test presets are code execution, so this is deliberately opt-in |
| `Gate not satisfied: <role>` | A required specialist review never ran, or failed | Run it, or fix what it found |
| `Checkout does not match reviewed MR head` | Someone pushed, or your checkout drifted | Check out the exact reviewed commit, or start a fresh review of the new head |
| `Autonomous implementation budget exhausted` | Three attempts failed | It stops and escalates. Read the last review findings first |
| `CES_DENIED: Bash is restricted to the exact CES JSON-heredoc broker` | A role tried a raw shell command | Nothing. Roles reach the shell only through the broker |
| `CES_DENIED: Protected governance/product path` | A role tried to edit `.claude/`, CI config, or product docs it does not own | Nothing. You edit those |
| `CES_DENIED: Direct secret-file access is denied` | Something tried to read `.env` or a key | Nothing. Reference the location instead |
| `CES_DENIED: SigNoz tool is not explicitly allowlisted` | Telemetry access is default-deny | Add the exact read-only tool names to `signoz_read_tools`, or accept that the conclusion stays unverified |
| `No CES task is open` | A specialist was asked to work before intake finished | Nothing. Preflight happens before delegation by design |
| An empty diff on an MR review | The task was opened without the merge-base | Start a new task; scope is immutable. Fetch the target branch first so the merge-base exists locally |

One that is *not* a block: while specialist reviews are still running, the session pauses. Waiting is not failing.

---

## 6. What it will never do

| It will not | Because | Do this instead |
|---|---|---|
| Push, merge, close or rebase | Those are your decisions | Review the report, then do it yourself |
| Approve or request changes on an MR | Publishing findings is not approving them | Approve it yourself if you agree |
| Deploy or authorize a release | Release is human authority | Use the release readiness report as input |
| Run a migration, backfill or rollback | Running schema changes is a deployment step | It writes and reviews the migration; you run it |
| Delete, truncate or rewrite data | Least recoverable class of defect | It surfaces such a step as BLOCKING for your decision |
| Let a reviewer fix what it found | Reviewers have no write tool, so review stays independent | Send the findings back through a developer role |
| Let the author verify their own work | A developer's passing run is not acceptance | The tester role verifies |
| Edit `.claude/`, CI config, or your `CLAUDE.md` | Governance is not self-modifiable | Edit it yourself |
| Read or echo `.env`, keys or credentials | Secrets stay out of transcripts and comments | Reference the location |
| Invent a version, owner, metric, SLO or approval | An unverified fact is worse than an unknown | Supply it, or accept the `unknown` |
| Claim something is verified in production | Nothing here observes production | Verify after you deploy |

---

## 7. Prompts that will not work

| Prompt | Why |
|---|---|
| `Fix the bug and push it` | No role pushes, commits or merges |
| `Review this MR and approve it if it looks fine` | There is no approval state |
| `Skip the PRD, it is a two-line change` | Code changes need a contract; for a two-line fix it is a short one |
| `You wrote it, so you can test it` | The developer's own run never satisfies acceptance |
| `Have the reviewer fix what it found` | Reviewers cannot write |
| `Run the migration on staging` | No role runs migrations |
| `Just mark the criteria as passing, CI is green` | Criteria need real receipts from this workspace |
| `Add the host to the allowlist for me` | `.claude/` is protected from every role |
| `Review the MR and also fix those other two bugs` | One task, one session, fixed scope |
| `Check production for me` | Only read-only telemetry, only if you allowlisted it |

---

## Appendix A. Broker actions

Roles cannot run arbitrary shell. Every command is exactly this envelope, and the action is re-authorized against
the role that sent it:

```bash
php scripts/claude/bin/ces.php <<'CES_REQUEST'
{"action":"task_status"}
CES_REQUEST
```

| Action | Who can call it | What it does |
|---|---|---|
| `task_open` | orchestrator | Binds the task once; on an MR task also the reviewed commit and merge-base |
| `task_status` | every role | The task, the workspace fingerprint, the receipts recorded so far |
| `context` | all but the publisher | `status`, `head`, `log` or `diff` - no arbitrary git arguments |
| `fetch_mr` | orchestrator, peer, tech lead, EM | MR metadata, exact head commit and the changed-file list (not the diff bodies) |
| `validate_prd` | all but the publisher | Structurally validates the current task's PRD |
| `run_check` | configured developer, tester, QA and performance roles | Runs a named preset from your policy and records a receipt |
| `publish_review` | publisher | Posts the stored review to the exact reviewed commit; `dry_run` posts nothing |
| `finalize` | orchestrator | Re-checks every receipt, criterion, gate and publication before recommending completion |

Full request schemas: [COMMANDS.md](docs/ai/claude-engineering-system/COMMANDS.md).

## Appendix B. Role result JSON

Each specialist ends with one JSON object; the orchestrator turns those into the readable report. Full field
rules: [REPORT_CONTRACTS.md](docs/ai/claude-engineering-system/REPORT_CONTRACTS.md).

Common shape:

```json
{"task_id":"B2B-142","status":"PASS","summary":"<the conclusion the evidence supports>",
 "evidence":["<what was actually read, run or queried>"],"findings":[],"risks":[],
 "unknowns":["<what could not be established>"],"handoff":"<the next action and its owner>"}
```

A finding, and what makes it reviewable:

```json
{"severity":"BLOCKING","location":"app/Services/Wallet.php:42",
 "problem":"Withdrawal reads the balance, then writes the decremented value outside a lock or transaction",
 "impact":"Two concurrent withdrawals can both pass the balance check, overdrawing the wallet",
 "evidence":"Read :31-:58; no lockForUpdate, no atomic decrement, no surrounding transaction",
 "recommended_direction":"Lock the wallet row for the read-modify-write, or make the decrement atomic"}
```

`BLOCKING` (must not ship), `WARNING` (a risk you may knowingly accept), `SUGGESTION`, `NIT` (cosmetic,
console-only by default). A `PASS` may not contain a `BLOCKING` finding - if it found a blocker, the status is
`FAIL`.

Statuses by role:

| Role | Statuses |
|---|---|
| product manager | `READY_FOR_ENGINEERING`, `DRAFT`, `NEEDS_INFORMATION`, `BLOCKED` |
| developers | `IMPLEMENTED`, `FAIL`, `BLOCKED` |
| reviewers and testers | `PASS`, `FAIL`, `BLOCKED` |
| QA support | `VALID_BUG`, `NOT_A_BUG`, `INCONCLUSIVE`, `NEEDS_INFORMATION`, `BLOCKED` |
| architect | `PROPOSED`, `BLOCKED` |
| incident investigator | `INVESTIGATED`, `BLOCKED` |
| MR publisher | `PUBLISHED`, `PUBLISHED_WITH_FALLBACK`, `ALREADY_PUBLISHED`, `DRY_RUN`, `BLOCKED` |
| the session's final line | `READY_FOR_HUMAN_REVIEW`, `REVIEW_DELIVERED`, `BLOCKED`, `HUMAN_ESCALATION_REQUIRED` |

## Appendix C. A complete PRD

This is what the product role produces, and what the tester is gated on. It passes the structural validator -
though passing means "complete enough to argue about", not correct. (Fenced examples are ignored by the
validator, so this one cannot satisfy a gate.)

```markdown
# B2B-142 - Public order endpoints enforce a per-tenant request limit

Status: READY_FOR_ENGINEERING
Owner: Nadia Rahmani (Payments team lead)

## Problem Statement
A single tenant's integration can saturate the public order endpoints, degrading response times for every other
tenant on the same cluster.

## Context / Evidence
On 2026-09-02 between 11:20 and 11:55 Asia/Tehran (07:50-08:25 UTC), one tenant issued 42,000 requests to
POST /api/orders. Read from the SigNoz query recorded in Observability Requirements. The endpoints currently pass
through app/Http/Middleware/ThrottleRequests with a global limit only (routes/api.php:31-58).

## Goals
Per-tenant limits are enforced server-side on the three public order endpoints, with a documented rejection shape.

## Non-Goals
Per-endpoint or per-user limits, dynamic limit tuning, and billing consequences for exceeding a limit.

## Users / Actors
Tenant API integrations authenticating with a tenant-scoped token. Internal service traffic is out of scope.

## Functional Requirements
- FR-01: Requests below the tenant's configured limit are served normally.
- FR-02: Requests above the tenant's configured limit are rejected with HTTP 429.
- FR-03: A 429 response carries a Retry-After header in seconds.
- FR-04: The limit applied is resolved from the authenticated actor's tenant, never from request input.

## Acceptance Criteria
### AC-01: Requests under the limit are served
Given: A tenant configured with a limit of 5 requests per minute and 4 requests already counted
When: The tenant issues one more request to POST /api/orders
Then: The response status is 201 and the request is counted
Verification: tests/Feature/TenantRateLimitTest.php - it_allows_requests_under_the_tenant_limit
Requirement: FR-01

### AC-02: Requests over the limit are rejected
Given: A tenant configured with a limit of 5 requests per minute and 5 requests already counted
When: The tenant issues one more request to POST /api/orders
Then: The response status is 429 and no order is created
Verification: tests/Feature/TenantRateLimitTest.php - it_rejects_requests_over_the_tenant_limit
Requirement: FR-02

### AC-03: Retry-After is present on rejection
Given: A tenant whose limit is already exhausted
When: The tenant issues one more request to POST /api/orders
Then: The 429 response includes a Retry-After header whose value is a positive integer
Verification: tests/Feature/TenantRateLimitTest.php - it_returns_retry_after_on_429
Requirement: FR-03

### AC-04: A tenant id in the request body is ignored
Given: Actor A authenticated for tenant 1, whose limit is exhausted, and tenant 2 with an unused limit
When: Actor A issues a request carrying tenant_id 2 in the body
Then: The response status is 429 and tenant 2's counter is unchanged
Verification: tests/Feature/TenantRateLimitTest.php - it_ignores_a_tenant_id_supplied_in_the_request
Requirement: FR-04

## Failure / Negative Behavior
An unauthenticated request is rejected by the existing auth middleware before the limiter runs. If the counter
store is unavailable, the request is served and the failure is logged with the tenant id - the limiter fails open,
and that choice is deliberate. Counting is idempotent per request: a retried request that already incremented the
counter does not increment it twice.

## Non-Functional Requirements
The limiter adds at most one counter round trip per request. Counting must be correct under concurrent requests
for the same tenant.

## Observability Requirements
Structured log field tenant_id and limit_applied on every rejection. Counter metric of rejections per tenant.
Evidencing query: SigNoz logs, service=api, env=production, filter http.status_code=429, grouped by tenant_id,
bounded to a 15-minute window.

## Dependencies
laravel/framework <exact version read from composer.lock> and the cache store configured in
config/cache.php (both read at commit <40-hex>). No migration.

## Rollout / Migration Expectations
Deploy behind the limits config with a permissive default so existing tenants are unaffected until a limit is set.
Rollback is a redeploy of the prior release; no data implication.

## Success Metrics
No tenant exceeds its configured limit for more than one minute, measured by the rejection query above over the
first 24 hours after rollout. Current baseline: no per-tenant enforcement exists.

## Risks
A limit set too low degrades a tenant's legitimate throughput. Mitigation: permissive default and per-tenant
configuration under human control.

## Open Questions
None

## Out of Scope
Per-endpoint limits, burst allowances, and surfacing remaining quota to the tenant.
```

Every requirement is covered by a criterion, and every criterion names a real assertion. If the verification
cannot be named, the criterion is not ready.

## Appendix D. Example check policy

Until you configure this, tests cannot run and acceptance stays blocked. Edit
`.claude/engineering-system/config.json` yourself - no role can. Merge into the existing `version: 3` document
rather than replacing it, and keep `allowed_hosts`, `risk_patterns` and `signoz_read_tools`.

```json
{
  "version": 3,
  "allowed_hosts": ["gitlab.your-company.example"],
  "allow_publish_nits": false,
  "execution_isolated": true,
  "checks": {
    "unit": {
      "trusted": true,
      "kind": "test",
      "roles": ["developer","hotfix-developer","upgrade-developer","tester","regression-tester","qa-support"],
      "argv": ["php","vendor/bin/phpunit","--testsuite","Unit"],
      "timeout_seconds": 300,
      "env": {"APP_ENV":"testing","DB_CONNECTION":"sqlite","DB_DATABASE":":memory:","QUEUE_CONNECTION":"sync","CACHE_STORE":"array","MAIL_MAILER":"array"}
    },
    "feature": {
      "trusted": true,
      "kind": "test",
      "roles": ["developer","tester","regression-tester"],
      "argv": ["php","vendor/bin/phpunit","--testsuite","Feature"],
      "timeout_seconds": 600,
      "env": {"APP_ENV":"testing","DB_CONNECTION":"sqlite","DB_DATABASE":":memory:","QUEUE_CONNECTION":"sync","CACHE_STORE":"array"}
    },
    "style": {
      "trusted": true,
      "kind": "static",
      "roles": ["developer","hotfix-developer","upgrade-developer","tester"],
      "argv": ["php","vendor/bin/pint","--test"],
      "timeout_seconds": 120,
      "env": {"APP_ENV":"testing"}
    }
  },
  "signoz_read_tools": []
}
```

Read this before setting `execution_isolated: true`:

- It is your acknowledgement that a disposable runner with test-only data exists. It is not a sandbox. A configured
  command is code execution: it can read `.env` files and spawn subprocesses.
- `APP_ENV=testing` proves nothing about isolation by itself.
- SQLite does not reproduce MySQL or PostgreSQL locking and isolation behavior. Configure a separate integration
  check on the real engine if that matters.
- A check that modifies tracked files fails verification even when its assertions pass.
- Never run untrusted MR code in a session that holds publication or telemetry credentials.

## Appendix E. Before you trust this in your repo

The offline suite mocks hook inputs and providers, not a running Claude installation. Walk
[RUNTIME_SMOKE_TEST.md](docs/ai/claude-engineering-system/RUNTIME_SMOKE_TEST.md) on your own CLI version, in a
disposable checkout, with no production data or credentials:

```bash
php scripts/claude/checks/self-check.php
python3 -S scripts/claude/tests/test_system.py
python3 tools/package_integrity.py --check
```

Then confirm on your installation that the refusals actually refuse: a raw `echo` from a review role, a file write
from a reviewer, a made-up test receipt, and a stale receipt after you touch a source file. A `PASS` printed in
this document is not evidence about your environment.

Merge, deploy, release and final engineering judgment stay with you. `READY_FOR_HUMAN_REVIEW` and
`REVIEW_DELIVERED` are recommendations.
