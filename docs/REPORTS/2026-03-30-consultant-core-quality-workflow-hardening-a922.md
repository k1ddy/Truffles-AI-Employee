# 2026-03-30 Consultant-Core Quality Workflow Hardening (a922)

## Scope
Close the user-approved workflow/tooling block before the next product-family RCA:
- keep replay/audit artifacts mechanism-first
- separate product/oracle/evaluator/infra backlog buckets
- make human audit faster without weakening it
- add machine-readable family/trend artifacts
- keep current practical truth unchanged

## Outcome
- Status: `done`
- Practical truth: unchanged (`r32g` remains current truth)
- Product closure: still `open`
- Next admissible product block: `parking fact composition regression`

## Implemented workflow changes
1. `ops/diagnose.py llm-quality-audit` now emits four additional first-class artifacts per audited run:
   - `manual_audit_workspace.md`
   - `manual_audit_workspace.json`
   - `family_registry.json`
   - `judge_conflicts.jsonl`
2. Manual-audit payloads and summary sync now carry those artifact paths and fail forensic/evidence handoff when they are missing on a completed audit.
3. Evidence handoff / governance closure / run manifest now include the new workflow artifacts.
4. New command `python3 ops/diagnose.py llm-quality-trends --run-dir ...` aggregates run-level backlog buckets and mechanism trends across audited runs.
5. Scenario-contract reporting now tracks optional mechanism/product metadata coverage:
   - `mechanism_metadata_coverage`
   - `product_contract_coverage`
   - `product_outcome_coverage`
6. Existing audited runs `r30` and `r32g` were regenerated through the new audit path so they now contain the new workflow artifacts.

## Fresh workflow evidence
- `r30` refreshed audit bundle:
  - `/tmp/booking_quality/a922-practical-proof-20260329-r30/manual_audit_workspace.md`
  - `/tmp/booking_quality/a922-practical-proof-20260329-r30/manual_audit_workspace.json`
  - `/tmp/booking_quality/a922-practical-proof-20260329-r30/family_registry.json`
  - `/tmp/booking_quality/a922-practical-proof-20260329-r30/judge_conflicts.jsonl`
- `r32g` refreshed audit bundle:
  - `/tmp/booking_quality/a922-practical-proof-20260330-r32g/manual_audit_workspace.md`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r32g/manual_audit_workspace.json`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r32g/family_registry.json`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r32g/judge_conflicts.jsonl`
- Trend aggregation:
  - `python3 ops/diagnose.py llm-quality-trends --run-dir /tmp/booking_quality/a922-practical-proof-20260329-r30 --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r32g --pretty`

## Checks
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_tool_evidence_gate.py truffles-api/tests/test_booking_quality_scenario_contract_gate.py truffles-api/tests/test_booking_quality_audit_artifacts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_tool_evidence_gate.py truffles-api/tests/test_booking_quality_scenario_contract_gate.py truffles-api/tests/test_booking_quality_audit_artifacts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_status_gate.py`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260329-r30 ... --strict-artifacts`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r32g ... --strict-artifacts`
- `python3 ops/diagnose.py llm-quality-trends --run-dir /tmp/booking_quality/a922-practical-proof-20260329-r30 --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r32g --pretty`
- `git diff --check`

## Residuals
- Workflow tooling does not close `parking`; it only hardens the evidence path for the next RCA block.
- Trend bucketing is still provisional and automated; final family/layer decisions remain human-owned.

## Next-block contract
- Start `parking fact composition regression` only after using:
  - `manual_audit_workspace.*`
  - `family_registry.json`
  - `judge_conflicts.jsonl`
  - `llm-quality-trends`
- Shared mechanism framing remains mandatory:
  - `fact selection / fact composition`
