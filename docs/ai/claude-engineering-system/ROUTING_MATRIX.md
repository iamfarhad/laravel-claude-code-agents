# Routing matrix

| workflow | Path |
|---|---|
| `feature` | product-manager -> prd-reviewer -> architect if material -> developer -> peer-reviewer -> specialists -> tester |
| `production-bug` | qa-support -> product-manager (corrective PRD) -> prd-reviewer -> developer -> peer-reviewer -> specialists -> tester -> release-reviewer if risk requires |
| `peer-review` | peer-reviewer -> mr-review-publisher -> optional tester -> human author/reviewer |
| `tech-lead-review` | tech-lead-reviewer -> required specialists -> human technical lead |
| `engineering-manager-review` | engineering-manager-reviewer -> required technical/operational specialists -> human manager |
| `incident` | incident-investigator -> product-manager (minimal corrective PRD) -> prd-reviewer -> hotfix-developer -> peer-reviewer -> specialists -> tester -> release-reviewer -> human release -> later RCA |
| `performance` | performance-reviewer (baseline) -> product-manager -> prd-reviewer -> developer -> peer-reviewer -> performance-reviewer (fresh after) -> tester |
| `security` | security-reviewer (diagnosis) -> product-manager -> prd-reviewer -> developer -> peer-reviewer -> security-reviewer (fresh) -> tester |
| `refactor` | product-manager (preserved-behavior contract) -> prd-reviewer -> architect if needed -> developer -> peer-reviewer -> specialists -> regression-tester |
| `upgrade` | product-manager (compatibility contract) -> prd-reviewer -> architect if needed -> upgrade-developer -> peer-reviewer -> specialists -> regression-tester -> release-reviewer |
| `release` | release-reviewer -> human release owner |
| `architecture` | architect -> human design review |
| `development-bug` | qa-support -> product-manager (corrective PRD) -> prd-reviewer -> developer -> peer-reviewer -> tester |
| `ci-failure` | diagnose isolated CI failure -> product-manager (repair contract) -> prd-reviewer -> developer -> peer-reviewer -> tester |

## Risk gates
security-reviewer: authz/tenant/payment/PII/secrets/webhooks/trust boundaries.
database-reviewer: schema/index/query isolation/lock/backfill/data-integrity changes.
performance-reviewer: claimed latency/throughput improvement, hot paths/search/cache/queue.
tech-lead-reviewer: architecture/reliability/compatibility and cross-service semantics.
engineering-manager-reviewer: ownership/cross-team/cost/major irreversible decisions.
release-reviewer: incident, upgrades, risky migrations and rollout/rollback dependence.

Record these as task risk_gates. Mandatory semantic gates for incident/upgrade/performance/security are also added by the broker. Filename detection supplements, never replaces, human/model impact analysis. MR-only remote diffs are not fully classified by local filename rules; specify risk_gates from the fetched diff.
No nested delegation. Main coordinates specialists. Current PRD hashes and workspace digests prevent stale approvals from satisfying code completion.
