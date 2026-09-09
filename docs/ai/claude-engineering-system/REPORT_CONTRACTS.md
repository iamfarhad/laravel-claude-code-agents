# Role result contracts
Each specialist ends with ONE JSON object (optionally wrapped in a json code fence). No header prose. The orchestrator renders readable console output and preserves review findings.

Common fields:
```json
{"task_id":"ACTUAL-ID","status":"BLOCKED","summary":"Supported conclusion","evidence":[],"findings":[],"risks":[],"unknowns":["Evidence not available"],"handoff":"Exact next action and owner"}
```
Success needs nonempty actual evidence. Findings: severity, location, problem, impact, evidence, and recommended_direction. PASS/IMPLEMENTED cannot contain BLOCKING findings.

## Specific fields
- product-manager READY_FOR_ENGINEERING: prd_path equals current task path; validator must pass. Independent prd-reviewer PASS required next. DRAFT/NEEDS_INFORMATION/BLOCKED are valid incomplete results.
- developers IMPLEMENTED: root_cause_or_requirement; ac_mapping object for every AC: `{"AC-01":{"implementation":["app/...php:42"],"tests":["tests/...php:20 / named assertion"]}}`. These references are claims for independent review, not machine proof of semantics.
- testers PASS: ac_results list covering all ACs. Each item has id, status PASS, assertion and check_id (the actual 32-hex ID from a passing tester/regression run of kind test). IDs from developer runs, other tasks or stale workspace are rejected.
- peer-reviewer PASS/FAIL on MR: reviewed_head_sha, publishable_comments array (empty is valid). Fields below. A tracked dirty checkout or wrong head blocks commit-bound publication.
- publisher: status must match a broker publication result. Include result counts and gaps. DRY_RUN does not satisfy publication.
- QA: VALID_BUG/NOT_A_BUG/INCONCLUSIVE/NEEDS_INFORMATION/BLOCKED. Valid bug requires evidence, not just confidence.
- architect: PROPOSED/BLOCKED. Incident: INVESTIGATED/BLOCKED. Other reviewers: PASS/FAIL/BLOCKED.

## Publishable comment
```json
{"id":"PEER-001","severity":"BLOCKING","path":"app/Services/Wallet.php","line":42,"side":"RIGHT","problem":"Specific evidenced failure","impact":"Concrete consequence","evidence":"Verified execution path or test","recommended_direction":"Narrow corrective direction"}
```
Use line:null (and optionally path:null) for summary-only. GitLab renames may require old_path; context lines may require old_line. IDs/paths/lines must come from actual inspection. NITs remain in console by default.

## Receipt meaning and limitations
Hooks save validated results with task, PRD hash and workspace digest. They bind freshness and real check execution, not semantic truth. A malicious test printing PASS still needs independent code/test review and CI. A model cannot approve its own stakeholder decisions.
An invalid stop is retried once, then recorded invalid and allowed to end to prevent a loop. Downstream gates remain blocked even if the agent stops. Treat the final status as evidence only if finalize succeeded.

The main console response ends with a ces-result code fence containing task_id and status READY_FOR_HUMAN_REVIEW/REVIEW_DELIVERED/BLOCKED/HUMAN_ESCALATION_REQUIRED. No merge/deploy authorization is implied.
