# TP-2026-03-30-consultant-core-quality-workflow-hardening-a922

- Status: `done`
- Owner: `Hands`
- Date: `2026-03-30`

## Название/цель
Закрыть перед следующим product-family блоком весь user-approved improvement plan для testing/audit workflow: отделить product path от test-harness path, сделать human audit быстрее и глубже, разделить backlog buckets, сделать failure families first-class artifacts, добавить trend analytics, и зафиксировать это в canon.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/REPORTS/2026-03-30-consultant-core-r32g-human-semantic-audit-a922.md`

## Invariant
- Не ослаблять acceptance gates.
- Не подменять product fixes workflow-only fixes.
- Не объявлять product closure green.
- Любой workflow fix должен быть observable через deterministic tests и machine-readable artifacts.

## Scope
- Replay/audit tooling hardening.
- Mechanism-first evidence artifacts.
- Canon updates for the new workflow contract.

## Out of scope
- New product-family fixes beyond workflow hardening.
- Parking runtime remediation.
- Booking runtime remediation beyond already closed blocks.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-quality-workflow-hardening-a922.md`
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `truffles-api/tests/test_booking_quality_scenario_contract_gate.py`
- `truffles-api/tests/test_booking_quality_audit_artifacts.py`
- `TECH.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/REPORTS/2026-03-30-consultant-core-quality-workflow-hardening-a922.md`

## Surfaced workflow debt / mechanism-first frame
- Surfaced workflow debt labels:
  - `harness can distort product path`
  - `manual audit is still too expensive and too implicit`
  - `product/oracle/evaluator/infra debt are not first-class separated artifacts`
  - `failure families are not yet machine-readable backlog objects`
  - `run comparison is still run-centric more than mechanism-centric`
- Broken invariants:
  - test harness must not mutate the product path unless the scenario explicitly asks for it
  - every expensive replay must end with machine-readable backlog separation and turn-by-turn audit workspace
  - family tracking must survive across runs at the mechanism level, not only as per-run prose
- Shared mechanisms:
  - replay harness isolation
  - human-audit workspace generation
  - failure-family registry / backlog routing
  - mechanism trend analytics
  - scenario-contract metadata coverage

## One web search (mandatory before implementation)
- Query: `site:bazel.build hermetic tests official`
- Date/time: `2026-03-30 03:03 Asia/Almaty`
- Sources opened:
  - `https://bazel.build/concepts/hermeticity`
- Source quality:
  - official vendor documentation
- Findings:
  - hermetic tests should minimize external dependencies and side effects
  - a test harness should not change the behavior it is trying to measure except through explicit, controlled inputs
- Decision:
  - `reuse/integrate`
  - adapt the hermeticity principle into Truffles replay: make synthetic tool hooks and audit helpers observable and non-distorting by default, and emit separate artifacts when evaluator/oracle seams are the source of drift
- Rejected variants:
  - `treat evaluator side effects as acceptable replay noise` — violates evidence quality
  - `document the problem without machine-readable artifacts` — does not change the workflow itself

## Root cause (mandatory)
- Symptom:
  - even after bounded runtime fixes, replay/audit work still required ad hoc forensic reconstruction to separate product blockers from oracle/evaluator/harness residue
- Minimal reproduction:
  - `r31`, `r32e`, `r32f`, `r32g`
- Evidence:
  - `/tmp/booking_quality/a922-practical-proof-20260330-r31/*`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r32g/*`
  - `ops/diagnose.py`
  - `docs/REPORTS/2026-03-30-consultant-core-r32g-human-semantic-audit-a922.md`
- Five Whys:
  1. Why was family RCA still expensive after replay? Because machine-readable artifacts stopped at summary/brief/manual audit and did not emit backlog-bucket, calibration, or path-scaffold artifacts.
  2. Why did replay still need forensic separation of product vs evaluator residue? Because harness/evaluator side effects were not exported as first-class artifacts.
  3. Why was human audit slower than needed? Because turn-by-turn review still had to be reconstructed manually from raw responses/trace for each run.
  4. Why did trend reasoning stay fragile? Because runs were compared mostly by run summaries, not by a durable family registry grouped by mechanisms and buckets.
  5. Why is this a workflow mechanism block rather than a single bugfix? Because every future product block depends on this audit/replay discipline, not on one surfaced dialog.
- Root cause statement:
  - the current replay/audit workflow lacks first-class artifacts for harness isolation, turn-by-turn audit workspaces, backlog-bucket routing, family registries, and mechanism trend summaries, so expensive runs still require manual reconstruction before the team can distinguish product blockers from oracle/evaluator/infra residue
- Fix mechanism:
  - extend `ops/diagnose.py` and canon docs so every run emits machine-readable audit workspace + family registry + judge conflict export + trend summary inputs, while scenario contract reporting begins tracking mechanism/product-contract metadata and the canon requires using those artifacts before the next product block

## Plan
1. Add workflow artifacts to `llm-quality-audit`.
2. Add backlog-bucket and family-registry helpers.
3. Add judge-conflict export for calibration.
4. Add mechanism trend analytics command.
5. Add optional scenario-contract metadata coverage counters.
6. Add focused deterministic tests.
7. Update canon/runbooks and write the workflow-hardening report.
8. Update `STATE.md` truth and next-block contract.

## DoD
- Audit run emits machine-readable turn workspace.
- Audit run emits machine-readable family registry with separated buckets.
- Audit run emits judge-conflict export for calibration.
- Trend command exists and is tested.
- Scenario contract reports optional mechanism/product metadata coverage.
- Canon docs require the new artifacts before future blocks.
- Focused deterministic checks are green.

## Checks
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_tool_evidence_gate.py truffles-api/tests/test_booking_quality_scenario_contract_gate.py truffles-api/tests/test_booking_quality_audit_artifacts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_scenario_contract_gate.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_audit_artifacts.py`
- `python3 ops/diagnose.py llm-quality-trends --run-dir /tmp/booking_quality/a922-practical-proof-20260329-r30 --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r32g`
- `git diff --check`

## Evidence
- updated workflow artifacts under fresh audited run directories
- deterministic test output
- updated canon docs and workflow report

## Rollback
- Revert the workflow-hardening changes in `ops/diagnose.py`, tests, and canon docs as one block if the new artifacts break existing audit or replay flows.

## No-go
- No weakening of manual audit gate.
- No weakening of tool-evidence strictness.
- No claim that workflow hardening itself fixes parking/product families.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- parking runtime family remains open
- oracle taxonomy drift remains open
### Why not in this block
- user requested workflow hardening first
### Risk if deferred
- future product RCA will stay slower and noisier
### Linked follow-up Task Package(s)
- next: parking fact composition family
### Expiry/trigger to stop deferral
- before any further product-family implementation

## Next-block contract (mandatory)
### Next block objective
- Open the parking RCA block only after this workflow-hardening block is fully merged into canon and tools.
### First deterministic check command
- `python3 ops/diagnose.py llm-quality-trends --run-dir /tmp/booking_quality/a922-practical-proof-20260329-r30 --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r32g`
### Blocked-by conditions
- workflow artifacts/tests not complete
### Owner role for closure
- `Brain/Architect`

## Completion note
- Closed as a workflow/canon block only; no product family was changed.
- Current practical truth remains `r32g`.
- Delivered:
  - `llm-quality-audit` aux artifacts (`manual_audit_workspace.*`, `family_registry.json`, `judge_conflicts.jsonl`)
  - `llm-quality-trends`
  - scenario-contract optional mechanism/product metadata coverage
  - refreshed `r30` / `r32g` audit bundles through the new path
  - canon/report updates that require the new artifacts before the next product RCA
