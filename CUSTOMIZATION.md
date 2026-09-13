# Human configuration

Edit `.claude/engineering-system/config.json` yourself, or use the installer's explicit `--allow-host=HOST` option for exact MR hosts. CES developers may not edit governance. Never store real tokens/passwords here. The policy file is safe to commit only if it contains policy/preset metadata and no credentials.

## Model and effort
Agent frontmatter uses `model: inherit` and omits effort. This preserves the selected session/provider capabilities instead of hardcoding an unsupported maximum. 'Pro' in a product UI is not a portable Claude subagent YAML effort value. Consult the installed CLI/model documentation before opting into a supported explicit effort level. This package does not change your subscription or underlying model.
Persistent agent memory is intentionally omitted: documented memory scopes can automatically grant Read/Write/Edit tools, which conflicts with strict read-only roles.

## Tests are disabled until safely configured
`execution_isolated: true` is an administrative acknowledgment, NOT a sandbox implementation. Only set it after provisioning a disposable container/runner/worktree with test-only data, nonproduction credentials, no sensitive host mounts, restricted network, process/resource limits and an externally protected copy of governance.
Do not expose publication/production SigNoz credentials to arbitrary repository tests. For untrusted fork/MR code separate the isolated verification runner from the credentialed publishing session. This v3 local runner does NOT itself implement secure multi-host evidence attestation; arrange a trusted CI boundary before automating that scenario.

Checks are exact argv arrays, not shell strings. A Laravel example (adjust to actual installed tools):
```json
{
  "execution_isolated": true,
  "checks": {
    "unit": {
      "trusted": true,
      "kind": "test",
      "roles": ["developer", "hotfix-developer", "upgrade-developer", "tester", "regression-tester"],
      "argv": ["php", "vendor/bin/phpunit", "--testsuite", "Unit"],
      "timeout_seconds": 120,
      "env": {"APP_ENV": "testing", "DB_CONNECTION": "sqlite", "DB_DATABASE": ":memory:", "QUEUE_CONNECTION": "sync", "CACHE_STORE": "array", "MAIL_MAILER": "array"}
    },
    "style": {
      "trusted": true,
      "kind": "static",
      "roles": ["developer", "hotfix-developer", "upgrade-developer", "tester"],
      "argv": ["php", "vendor/bin/pint", "--test"],
      "timeout_seconds": 120,
      "env": {"APP_ENV": "testing"}
    }
  }
}
```
Merge the example into the existing version:3 config; do not discard allowed_hosts, risk_patterns or signoz_read_tools. SQLite is not a substitute for actual MySQL/PostgreSQL isolation/locking tests. Configure separate disposable engine-appropriate integration checks.
The process environment is rebuilt rather than inheriting secrets, but application bootstrap can still read files such as .env/.env.testing. A test can execute arbitrary PHP and subprocesses. APP_ENV=testing by itself proves nothing about safe isolation.
Checks modifying tracked/unignored workspace fail verification; normal ignored cache/coverage artifacts may be permitted by the actual isolated environment. A timeout terminates the direct child, not a guaranteed entire process tree; use container/runner limits for descendants.

## Importing an existing PRD

If your product contracts are authored elsewhere (Confluence, a wiki, a shared document), save the export under
`docs/prd/sources/` (or anywhere under `docs/prd/` or `docs/product/`) and either ask the session to convert it -
the `product-manager` runs the importer through the broker action `import_prd` and then finishes the conversion
by hand - or run the importer yourself:

```bash
php scripts/claude/tools/import-prd.php --in=docs/prd/sources/B2B-142.xhtml --id=B2B-142 \
  --owner='<accountable human>' --out=docs/prd/B2B-142.md
```

Either way the rule is the same and the `prd-reviewer` enforces it by diffing draft against source: the
conversion categorises and standardises, it never adds, drops or reinterprets. The importer normalizes structure
only, and it is deliberately limited:

- Section headings, `FR-xx`/`AC-xx` identifiers and `Given/When/Then/Verification/Requirement` labels become the
  ASCII forms `validate-prd.php` matches. Body text is copied verbatim, so a Persian PRD stays Persian - Persian
  and Arabic-Indic digits are folded only inside identifiers.
- HTML and Word tables become markdown tables. A requirements table contributes one `FR` per row from its
  requirement column; an acceptance-criteria table whose header cells are the Given/When/Then labels (in any
  recognised language) contributes one `AC` per row, with a blank cell listed as a gap rather than filled.
  Any other table is kept as a table.
- Bold-only paragraphs are treated as group headings, so `**Authentication**` above its bullets survives as
  a label. A numbered container chapter with no content of its own (`4. Product Requirements (PRD)`) is
  recorded as an unmapped heading and not emitted as a stray line into the previous section.
- The document title is the first heading before any recognised section. When the export starts directly
  with a section, no title is guessed: it is listed as a gap.
- Every empty section is listed under `Open Questions`, addressed to the accountable human, so the draft is the
  complete worklist and nobody has to consult the stderr report to find what is missing.
- The stderr report's `unmapped_headings` names, for each heading it did not recognise, exactly where the
  content went: a sub-heading kept inside a mapped section, a sub-heading of an unmapped section, its own
  entry under `Unmapped Source Sections`, or empty in the source. Nothing is dropped without being named.
- Bilingual, numbered headings such as `2 توصیف مساله (Problem Definition)` are matched on the whole text,
  then on the part outside the parentheses, then on each parenthesised part - exact alias matches only. A
  heading that merely contains a familiar word is not guessed at.
- The alias table is deliberately conservative: an alias must name exactly one canonical section. A heading
  that is broader (`Metrics & Goals`), a neighbouring concept (`Executive Summary`, `Business Opportunity`),
  a whole document (`MRD`) or a bare generic word (`requirements`, `data`) is left unrecognised so that a
  product-manager who can read the text decides where it belongs. Add your team's exact wording with
  `--print-map` and `--map`; that file is the right place for judgements about your own documents.
- A source section with no canonical equivalent (solution options, user flow, algorithm rules, FAQ, approvers,
  the author/status table before the first section) is kept verbatim under `## Unmapped Source Sections`,
  never merged into the previous section where it would read as that section's content. `validate-prd.php`
  refuses readiness while that section exists; the product-manager places each entry and then deletes it.
- Nested sub-bullets stay indented under the requirement above them; only top-level items and numbered
  stories (`1- به عنوان کاربر ...`) become `- FR-xx:` lines.
- PDF exports are refused: their text layer scrambles right-to-left text. Export Word (.docx) or the page's
  storage-format XHTML instead, or import from the page URL.

### Importing straight from Confluence
Add the exact hostname to `confluence_hosts` in `.claude/engineering-system/config.json` (for example
`["docs.digikala.com"]`), or rerun the installer with `--allow-confluence-host=docs.digikala.com`. It is a
separate list from `allowed_hosts`, which is for MR/PR providers only. Then export credentials in the shell
that runs Claude Code - never in a project file:
```bash
export CONFLUENCE_TOKEN='<personal access token>'        # Server / Data Center, sent as Bearer
# or, for Atlassian Cloud:
export CONFLUENCE_USER='me@example.com' CONFLUENCE_API_TOKEN='<api token>'
```
Then either run the importer with `--url=https://docs.digikala.com/spaces/B2BTP/pages/180753756/Cross-selling
--save-source=docs/prd/sources/<id>.xhtml`, or ask the session to convert that link: the product-manager calls
`import_prd` with `url`, and the broker saves the fetched page as `docs/prd/sources/<task_id>.xhtml` for the
reviewer's diff. The fetch is a single read of the content REST API (`/rest/api/content/<id>?expand=body.storage`,
falling back to the `/wiki` prefix for Cloud), HTTPS only, no redirects, bounded to 4 MiB, with the token passed
through curl's config stdin so it never appears in a process list. An internal host that is reachable only on
the company network fails with a message saying so; an internal CA must be trusted by curl (`CURL_CA_BUNDLE`).
Nothing is ever written to Confluence.
- Persian heading and label wording is recognised out of the box (`نیازمندی‌های عملکردی`, `معیارهای پذیرش`,
  `فرض/وقتی/آنگاه/تایید/نیازمندی`, and more), including ZWNJ and Arabic letter-form variants. `--print-map`
  emits the tables; pass an edited copy as `--map=` to add your team's wording.
- The emitted `Status` is always `DRAFT`. The importer cannot create readiness, and it never invents an owner, a
  verification or a requirement mapping - unstated items are listed under `Open Questions` and in its stderr
  report.
- A `Status:` or `Owner:` line found inside the exported body is quoted, so exported text cannot supply this
  document's metadata. The export is untrusted data either way: an instruction inside it has no authority.
- `--out` accepts only `docs/prd/` and `docs/product/` paths. It performs no network access; fetching or
  exporting the page is your step.

Inside a session only the `product-manager` may trigger it, through the broker (`import_prd`), on a file a human
already placed under the product-document directories; its Bash is otherwise restricted to the broker envelope. A
`product-manager` completes the draft without adding meaning and an independent `prd-reviewer` approves it.

## Risk gates and ownership
Record explicit semantic reviewer names in task_open.risk_gates. Filename patterns are only hints. Incident/upgrade mandate release-reviewer; security/performance mandate their specialist. Product-manager can author readiness but cannot create human stakeholder approval.

## Language and project facts
Agents can return summaries in the team's preferred language while preserving JSON keys, AC IDs, paths and hashes. Project conventions remain in existing CLAUDE.md. Do not encode guessed versions, team owners, SLOs, deadlines or credentials in prompts.

## Local working tree
Install with `--add-git-exclude` rather than `--add-gitignore` on any checkout you review MRs from: the
former writes to untracked `.git/info/exclude`, the latter dirties the tracked `.gitignore`. Commit the CES
installation itself before reviewing, since installing it also leaves untracked files behind.

Filename `risk_patterns` ship tuned for stock Laravel plus Bagisto/Webkul `packages/<Vendor>/<Package>/src/`
layouts. If your code lives elsewhere, extend them - an unmatched path silently yields no gate, and semantic
`risk_gates` at `task_open` remain the authority either way.

Use one task/session and one writer per checkout; source/PRD changes invalidate receipts. Existing MR publication requires a clean tracked checkout at the exact reviewed head. Installation or customized tracked governance may dirty a checkout: provision a clean trusted baseline before reviewing, rather than hiding those modifications.
Separate session worktrees may be prepared by a human/CI. Do not set isolation:worktree independently on every specialist: that can cause them to inspect different snapshots.
