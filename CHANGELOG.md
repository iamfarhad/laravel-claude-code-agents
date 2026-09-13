# Changelog

## 3.2.6 - agent prompts match what the broker and the tool allowlist actually grant (2026-09-13)
- Reviewed all 20 role definitions against the PreToolUse hook, the broker permission table, the
  report contracts and the finalize gate, and fixed every place where a prompt promised a capability
  the role could not reach - each one a dead end an agent would walk into and then have to explain.
- **Telemetry was unreachable for every role written to use it.** Each role declares an explicit
  `tools:` allowlist, and Claude Code hides MCP tools that allowlist does not name, so allowlisting a
  SigNoz tool in `signoz_read_tools` could never make it callable by `incident-investigator`,
  `qa-support`, `performance-reviewer`, `release-reviewer` or `tech-lead-reviewer`. SIGNOZ_SETUP.md now
  documents the missing step (append `mcp__signoz__*` to the role's `tools:` line; the hook remains the
  read-only enforcement), the five prompts say exactly when telemetry is unavailable to them, and the
  self-check warns when a telemetry role has no SigNoz entry and fails when a frontmatter names a
  SigNoz tool the config does not allowlist, or any non-SigNoz MCP tool.
- **`incident-investigator` was told it could reproduce with check presets, but the broker denied it
  `run_check`.** The diagnosis role now has the same reproduction path as `qa-support` (still gated by
  the preset's own `roles` list), and its prompt shows the envelope. `security-reviewer` and
  `database-reviewer` claimed the same thing and are pure reviewers; their prompts now say they never
  execute and read tester/QA receipts through `task_status` instead.
- **`product-manager` was pointed at `validate-prd.php`, a script its Bash can never run**, and was not
  told where the PRD must live. It now reads `prd_path` from `task_status` and runs the broker
  `validate_prd` action before reporting readiness; `prd-reviewer` runs the same action and is told
  its PASS is refused without a current product-manager readiness receipt.
- `upgrade-developer` was told to "read the official upgrade guide" with no network access; it now reads
  the vendor upgrade notes on disk and reports a missing guide as an unknown. `architect` was told to
  map to PRD IDs on `architecture` tasks, which have no PRD. `peer-reviewer` now knows where findings
  go on an in-repo task versus an MR task. Testers read the task's `prd_path` from `task_status`.
- `engineering-orchestrator` now states that every delegation must carry the task_id and scope (a
  specialist that does not know the task_id cannot produce an accepted receipt), that the PRD path is
  `docs/prd/<task_id>.md` and need not exist at `task_open`, and which developer/tester role each flow
  finalizes on.
- The broker permission table moved into `CES\actionPermissions()` so the hook, the broker and the
  self-check share one source of truth; the self-check now fails when any prompt demonstrates a broker
  action its role cannot call. Regression tests cover the new permission, the reviewer denials and the
  three new self-check rules.
- **PRD import is now a first-class, model-assisted conversion that cannot change the product's meaning.**
  `import_prd` is a new broker action for `product-manager` only: it runs the package's own importer on an
  export a human placed under `docs/prd/` or `docs/product/` and writes the `DRAFT` to the task's own
  `prd_path` (refusing to overwrite without `overwrite: true`). The product-manager then finishes the
  conversion by hand under an explicit mandate - categorise and standardise only; every source statement
  once, in its section, in its own words; nothing added, softened or resolved on the source's behalf; every
  gap listed under Open Questions for the accountable human - and `prd-reviewer` now diffs an imported
  draft against its source and treats untraceable content as BLOCKING. The orchestrator routes a conversion
  request to the target workflow's task and expects it to end `BLOCKED` on the source's open questions.
- The importer itself now converts what real Confluence and Word exports contain: HTML and `.docx` tables
  become markdown tables (previously one cell per line, which read as stray requirement lines); an
  acceptance-criteria table with Given/When/Then header cells, in Persian or English, yields one AC per row;
  a requirements table contributes one FR per row from its requirement column; bold-only paragraphs are
  group headings; a numbered container chapter with no content of its own is no longer emitted as a stray
  bold line into the previous section; the document title comes from the first heading before any section
  instead of a section heading such as `1. Executive Summary`; every empty section is listed under Open
  Questions in the draft itself; and every message addresses the accountable human, never "the converter".
  `--id` accepts every task_id the broker accepts.
- Tested against a second real PRD shape (a 30-page Confluence "Cross-selling" document): bilingual
  numbered headings such as `2 توصیف مساله (Problem Definition)` now match on the text outside or inside
  the parentheses (exact aliases only, no guessing); heading levels are tracked, so a source section with
  no CES equivalent - solution options, user flow, algorithm rules, FAQ, approvers, the author/status
  block before the first section - is kept verbatim under `## Unmapped Source Sections` instead of being
  merged into the previous section, and `validate-prd.php` refuses readiness while that section exists;
  nested sub-bullets stay indented under their requirement instead of becoming requirements; user stories
  map to Functional Requirements; status-macro text and CDATA link bodies survive; PDF exports are refused
  with guidance, because their text layer scrambles right-to-left text. New aliases cover
  Supportive Data, Metrics & Goals, Roadmap and Iteration, Constraints and Risks, Requirements from Other
  teams and suggested Events.
- A person reference now says why it carries no name. Confluence stores only an opaque user key and
  resolves the display name at render time, so an author or approver name is genuinely absent from the
  export; the placeholder states that instead of reading as though a name had been dropped.
- **The heading alias table is now deliberately conservative.** Every alias is a mapping decision taken in
  code without having seen the document, and a wrong one silently files the source's meaning under the wrong
  contract - `phase 2` sent a roadmap phase to Out of Scope on a real page. An alias now has to name exactly
  one canonical section, so headings that are broader (`Metrics & Goals` covers two), a different concept
  that merely overlaps (`Executive Summary`, `Market Opportunity`, `Business Opportunity`, `benchmark`), a
  whole document (`BRD`, `MRD`) or a bare generic word (`requirements`, `data`, `events`, `future scope`,
  `target audience`) are left unrecognised on purpose. Their text is preserved under `Unmapped Source
  Sections` and the product-manager, who can read it, decides. A missed mapping costs a manual move; a wrong
  one costs correctness.
- **A sub-heading of a recognised section is no longer discarded when the source left its body empty.**
  It was held back and emitted only if text followed, so on a live page the roadmap's three iteration
  names vanished and `Rollout / Migration Expectations` was reported both as mapped and as empty, and the
  label grouping five problem categories was lost because a bold-paragraph heading followed it directly.
  A sub-heading belongs to its section and is now always written; the container-chapter leakage this
  guarded against is already handled by heading levels.
- **The import report now says where every unrecognised heading's content went.** `unmapped_headings` was a
  flat list of names, so a heading that appeared there but not in `unmapped_sections_kept` was
  indistinguishable between "kept as a sub-heading inside a mapped section", "kept inside another unmapped
  section" and "gone" - and diagnosing one real page cost a full round trip. Each entry is now
  `{heading, level, kept_as}` naming the exact destination, and a source heading with no content under it is
  reported as empty in the source, with its own Open Questions line, instead of vanishing from the report.
- **Two content-loss defects found by importing a live page and fixed.** Confluence images, attachments and
  links were deleted without trace by the HTML-to-text pass, and a source section whose body was only
  sub-headings was then dropped entirely by the unmapped-section filter - so a PRD's design and flow chapter,
  which is typically nothing but wireframe images, a Figma link and phase headings, vanished from the draft
  with no mention in the report. Images and links now become explicit bracketed references that name the
  attachment, URL or linked page (`[image - attachment: wireframe.png]`), and an unrecognised section is kept
  whenever it carries anything at all, sub-headings included. Only a heading with literally nothing under it
  is dropped, and it still appears in the report.
- Verified against a live Confluence Data Center page ("نمایش خریدهای قبلی"): a sub-heading that names the
  section it sits in ("Goal" under "Metrics & Goals") is now kept as a label inside that section instead
  of lowering the section's depth and pushing its siblings ("Key Results", "Guardrail Metrics") into the
  unmapped bucket; Key Results and Guardrail Metrics map to Success Metrics; Business Opportunity and
  market benchmarks map to Context / Evidence; the presumptuous `phase 2` alias for Out of Scope is gone,
  so roadmap phases stay under Rollout.
- **Import straight from a Confluence URL.** `import_prd` accepts `url` in place of `source`, and
  `import-prd.php --url=` does the same for humans. The page body is fetched in storage format over the
  content REST API (`/rest/api/content/<id>`, falling back to `/wiki/...` for Cloud) from a host a human
  listed in the new `confluence_hosts` config key, HTTPS only, no redirects, bounded to 4 MiB, with
  credentials from `CONFLUENCE_TOKEN` or `CONFLUENCE_USER`/`CONFLUENCE_API_TOKEN` passed through curl's
  config stdin so they never appear in a process list or in output. The fetched page is saved as
  `docs/prd/sources/<task_id>.xhtml` so the prd-reviewer can diff draft against source. Offline tests cover
  the fetch, the Cloud fallback, denial, unreachable network, non-allowlisted host and missing credentials.
- **Installer: upgrades now add new policy keys.** An existing `config.json` was preserved byte for byte, so
  a project upgraded to this version never received `confluence_hosts` and the new capability was
  unconfigurable without knowing the key name. The installer now adds any top-level policy key the existing
  file lacks, with its shipped default, backs the file up and names the added keys in the plan; human values
  are never changed and a config that lacks nothing is still untouched. `--allow-confluence-host=HOST` is
  the Confluence counterpart of `--allow-host=HOST`, since a Confluence hostname in `allowed_hosts` (the
  MR/PR list) does nothing.
- `tools/package_integrity.py` no longer hashes `docs/prd/`, `docs/product/`, `docs/adr/` or
  `docs/architecture/`: those are project documents CES roles write into a target repository, and a PRD
  drafted in the package checkout was being baked into the shipped manifest.

## 3.2.5 - non-dirtying install option + package-layout risk patterns (2026-09-09)
- Added installer `--add-git-exclude`, which writes the CES runtime exclusions to `.git/info/exclude`
  instead of `.gitignore`. The existing `--add-gitignore` appends to a TRACKED file, which leaves the
  working tree dirty - and commit-bound MR review requires a clean tracked tree, so the documented
  convenience flag permanently blocked the package's main use case on the checkout it was run in.
  `.git/info/exclude` is local and never tracked. The two flags are mutually exclusive, and
  `--add-git-exclude` refuses a linked worktree rather than writing outside the project root.
  Both paths now share one append helper that preserves existing entries and is idempotent.
- Extended `risk_patterns` to Bagisto/Webkul `packages/<Vendor>/<Package>/src/` layouts. The shipped
  patterns anchored on stock Laravel paths (`app/Http/Middleware/`, `app/Policies/`, `config/auth.php`),
  so on a package-based project every changed file matched nothing and no specialist gate was ever
  derived - silently, since an unmatched path is indistinguishable from a low-risk one. Now covers
  package `Http/Middleware`, `Http/Requests`, `Policies`, security-relevant `Http/Controllers`,
  `Database/Migrations|Seeders|Factories`, `Models`, `Repositories`, `Jobs`, `Console/Commands`,
  `Providers` and `Contracts`, plus `Address` and `Customer` in the security token list.
  Deliberately selective: a generic package controller still derives no gate.

## 3.2.4 - MR tasks can scope their own diff (2026-09-09)
- `task_open` now accepts an optional `base_sha` that sets the task's diff scope, validated as a
  full hash of a commit actually present in the checkout and covered by immutable task scope.
- This fixes a real dead end on MR reviews. `base_sha` was always the local HEAD, but an MR review
  checkout sits AT the reviewed head, so `base_sha == reviewed_head_sha`: `context kind=diff`
  returned nothing and `derivedRiskGates()` had no changed files to classify, silently deriving
  zero specialist gates. A reviewer could conclude "no diff" from what was actually an
  unscoped task. Passing the merge-base with the target branch - `fetch_mr` returns it as
  `metadata.base_sha` - makes the canonical diff reachable.
- Because `task_status` is available to every role, the task's `base_sha` is also how a specialist
  that is not granted `fetch_mr` (security, database, performance, release reviewers) now obtains a
  usable diff scope. `fetch_mr` stays restricted to orchestrator/peer/TL/EM: the local checkout at
  the reviewed head is the authoritative copy of the code, so the fix is to give every role the
  scope rather than to widen provider network access.
- Instructed the orchestrator to always pass `base_sha` on MR tasks and to refuse to open a task
  that cannot see its own diff, and gave all seven reviewing roles an explicit Diff scope section:
  read `base_sha` from `task_status`, pass it to `context kind=diff`, and when it equals
  `reviewed_head_sha` report the coverage limitation instead of guessing which lines are new.

## 3.2.3 - bounded fetch_mr result (2026-09-09)
- `fetch_mr` no longer returns the raw provider object or any diff body. It previously returned
  the entire MR/PR payload - description, repeated actor blobs, pipeline objects, avatar URLs -
  plus the full patch for every changed file. On a 134-file MR that is ~637 KB, which overran the
  transcript, forced the CLI to persist the result to a file, and then dominated the
  orchestrator's context for the rest of the task.
- It now returns a provider-normalized summary (head SHA, open state, title, branches,
  author/reviewers/assignees, merge status and conflicts, pipeline status, counts, labels, base
  and start SHAs, plus a description excerpt bounded to 8 KB with a truncation flag and a
  sha256 of the full text) and one entry per changed file carrying `new_path`, `old_path`, the
  change kind, line counts and `diff_available`. Measured on that same shape: 637 KB -> 52 KB,
  a 91.8% reduction, with the head SHA and every risk-gate input preserved.
- Diff bodies were redundant: `peer-reviewer` is required to review a clean local checkout at
  the exact reviewed head, and the workflow already refuses a commit-bound review otherwise.
  Per-file `diff_available` now says exactly which files the provider diff did not cover,
  instead of only the aggregate `diff_incomplete` flag.
- Extended the offline provider fixture to return realistic MR metadata, and added tests
  asserting no diff body or raw-payload field survives, that a huge description is bounded, and
  that an uncovered file is individually marked.

## 3.2.2 - harness interop: reading back persisted tool output (2026-09-09)
- Fixed the read guard denying Claude Code's own persisted tool output. When a broker result
  is too large for the transcript, the CLI writes it to
  `~/.claude/projects/<slug>/<session>/tool-results/<id>.txt` and reads it back; `authorizeRead()`
  routed every read through `safePath()`, so that read failed with "Path is outside the project"
  and any flow with a large `fetch_mr` result dead-ended. Reads are now permitted for exactly
  `<projects>/<slug>/<THIS session id>/tool-results/`, matched on the RESOLVED real path so a
  planted symlink cannot escape it. Another session's directory, other projects' transcripts,
  `$HOME` secrets and the rest of the host stay denied, and the denial message now says what is
  actually allowed. Regression tests cover the positive case, three near-miss paths and the
  symlink escape.
- Hardened `process()` to drain both pipes to EOF after the child exits. It previously did one
  bounded 64 KiB read per pipe, which cannot be guaranteed to empty a pipe whose buffer has been
  enlarged - a large provider response could be silently truncated into invalid JSON and surface
  as a confusing "Provider returned non-JSON or incomplete output". Not reproduced at default
  pipe sizes; fixed as defence in depth, with a test asserting a 600 KB two-pipe response
  arrives byte-complete.

## 3.2.1 - source restoration + symlinked-checkout fix (2026-09-09)
- Fixed the PreToolUse guard's repository-root check, which compared the raw session `cwd`
  against a `__DIR__`-derived root. Because PHP always resolves `__DIR__` through symlinks, any
  checkout reached through a symlinked ancestor - every macOS temp path via `/var` -> `/private/var`,
  and any project under a symlinked parent - had EVERY tool call denied with the misleading message
  "Path is outside the project". Both sides are now canonicalized. `safePath()` is deliberately not
  used for this comparison: its symlink-component rejection guards write destinations and would
  reject a legitimate root. Write/Read path guards are unchanged, so symlinked and hard-linked
  destinations are still denied.
- Restored the package source that was missing from the repository: the 20 agent definitions, the
  10 shared rule files, `config.json`, `settings.fragment.json`, the PRD/ADR templates, `.gitignore`,
  `.mcp.json.example` and the CI workflow. The `.bootstrap/source.tar.gz` archive that was supposed
  to publish them was truncated (15 KB of a 1.55 MB stream) and failed to decompress, so its
  workflow could never have restored them.
- Removed the corrupt `.bootstrap/` archive and its `bootstrap-source.yml` workflow, which ran on
  every push to `main` and force-committed to the branch. The real `ci.yml` is now the only workflow.
- Excluded `.claude/settings.json` and `.claude/settings.local.json` from the integrity manifest.
  They are checkout-local Claude Code state, like `installed-files.json`, and hashing them made
  `package_integrity.py --check` fail in CI whenever a developer's local settings differed.

## 3.2.0 - background-review lifecycle fix + repository CI (2026-09-09)
- Fixed the Stop final gate so non-empty Claude Code `background_tasks` means the main session is paused for in-flight work, not task completion. It no longer forces a premature terminal `ces-result` while background specialists are running.
- Updated the orchestrator contract to allow parallel read-only specialist reviews on the same immutable snapshot and to pause naturally rather than reporting `BLOCKED` for pending receipts.
- Added regression coverage for the background-task pause lifecycle.
- Added repository CI for PHP lint, the offline regression suite and self-check.
- Added a source-repository `.gitignore` for CES runtime/backups/installer state and test caches.

## 3.1.0 - MR preflight/setup UX fix (2026-09-09)
- Clarified that an empty `allowed_hosts` is a deliberate fail-closed prerequisite, not a task/delegation loop to solve with a subagent.
- Main orchestrator now performs MR allowlist/config preflight itself before any specialist delegation.
- Allowlist errors include the exact blocked hostname and remediation.
- Added installer `--allow-host=HOST` for explicit, validated host trust without hand-editing JSON.
- Added opt-in `--add-gitignore` to append only CES runtime/backups/installer-state exclusions while preserving and backing up the existing `.gitignore`.
- Documented what should be committed versus ignored for a team-shared installation.

## 3.0.0 - audited revision (2026-09-09)
Breaking safety/process revision; do not mix agent files/scripts from v2.

- Replaced bypassable shell deny/prefix lists with exact role-aware JSON broker requests and single-use hook-issued tickets.
- Removed persistent agent memory and automatic per-role worktree settings; model/effort inherit session capability.
- Added real per-task PRD and current-hash independent reviewer gates before any code-changing route.
- Added structurally validated FR/AC definitions plus current independent check receipts for all ACs at completion.
- Added snapshot freshness, bounded implementation reports, bounded invalid-output repair and final receipt revalidation.
- Reworked MR publisher: immutable reviewed SHA, clean local commit binding, remote checks, pagination, actor-aware dedup, stable fallback summaries, no-write dry runs, partial-error reporting and local locking.
- Replaced SigNoz mutation blacklist with default-deny explicit read-tool policy and server-side least-privilege guidance.
- Installer now preflights before writes, preserves root documents/user settings, detects conflicts/symlinks/hardlinks, stages writes/backups and retains custom v3 config.
- Added executable offline regression fixtures and detailed limitations instead of asserting zero-risk or live integration success.

## Earlier v2
Retained as the audit input only. Its original 'hardened' label did not establish the invariants now tested; see AUDIT_REPORT.md.
