# 2026-02-19 Onboarding Any-Niche Acceptance (A131)

## Scope

- Target spec: `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-any-niche-end2end-tz.md`
- Executed TP: `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-any-niche-acceptance-a131.md`
- Branch: `feat/2026-02-19-onboarding-any-niche-acceptance-a131`
- Worktree: `/home/zhan/worktrees/2026-02-19-onboarding-any-niche-acceptance-a131`
- Runtime snapshot date: 2026-02-19

## Evidence Paths

- Raw logs/json: `/tmp/onboarding_any_niche_acceptance_a131/`
- Runtime scorecard (API-like payload): `/tmp/onboarding_any_niche_acceptance_a131/runtime_scorecard_api_like.json`
- Runtime gate payloads (shadow/enforced): `/tmp/onboarding_any_niche_acceptance_a131/runtime_scorecard_gate_evidence.json`

## Acceptance Matrix (2.5 A/B/C)

### A) Contract Acceptance

- `python3 -m py_compile ...` -> PASS (`/tmp/onboarding_any_niche_acceptance_a131/py_compile.exit=0`)
- `ruff check ...` -> PASS (`/tmp/onboarding_any_niche_acceptance_a131/ruff_check.exit=0`)
- `python3 truffles-api/scripts/generate_openapi.py --check` -> PASS (`/tmp/onboarding_any_niche_acceptance_a131/openapi_check.exit=0`)
- `pytest -q truffles-api/tests/test_console_onboarding_state.py` -> PASS (`22 passed`)
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "onboarding_scorecard or onboarding_autopilot or go_live or require_branch_scorecard"` -> PASS (`15 passed, 25 deselected`)
- `pytest -q truffles-api/tests/test_onboarding_intake_service.py` -> PASS (`14 passed`)
- `pytest -q truffles-api/tests/test_knowledge_validation.py` -> PASS (`10 passed`)
- `pytest -q truffles-api/tests/test_reference_pack_integrity.py` -> PASS (`4 passed`)
- `pytest -q truffles-api/tests/test_diagnose_onboarding_fleet.py` -> PASS (`7 passed`)
- `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py` -> PASS (`7 passed`)

Verdict A: PASS

### B) Runtime Acceptance

1. Readiness API returns readiness kernel:
- Evidence: `/tmp/onboarding_any_niche_acceptance_a131/runtime_scorecard_api_like.json`
- Fact: `ready=false`, `missing_count=2`, `readiness_kernel.status=fail`, `readiness_kernel` present.
- Verdict: PASS (payload contract present in runtime data).

2. Hard gate modes (shadow/enforced):
- Runtime evidence: `/tmp/onboarding_any_niche_acceptance_a131/runtime_scorecard_gate_evidence.json`
  - `shadow`: blocked with `GO_LIVE_GATE_REQUIRED`
  - `enforced`: blocked with `GO_LIVE_GATE_REQUIRED`
  - branch: `demo_salon/main` is already `scorecard_ready=false`, so both modes block.
- Deterministic gate semantics (shadow allows, enforced blocks on shadow blockers) additionally confirmed by tests:
  - `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "allows_shadow_blockers_when_hard_gate_disabled or blocks_when_hard_gate_enabled"` -> `2 passed`.
- Verdict: PASS with runtime caveat (no scorecard-ready branch in current snapshot to show a live "allowed in shadow" case).

3. Autopilot/intake evidence:
- Intake quality/missing evidence: `/tmp/onboarding_any_niche_acceptance_a131/onboarding_pack_quality.json` + summary json.
- Fact: intake returns `missing_questions`, `quality_matrix`, `critical_missing_fields`; sample text produced `status=fail`, `missing_fields_count=13`.
- Missing blocks go-live evidence: runtime gate payload contains `GO_LIVE_GATE_REQUIRED` with `missing` + readiness details in `/tmp/onboarding_any_niche_acceptance_a131/runtime_scorecard_gate_evidence.json`.
- Autopilot API contract behavior additionally confirmed by tests:
  - `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "run_onboarding_autopilot_activate_requires_scorecard_pass or run_onboarding_autopilot_preserves_existing_provider_binding"` -> `2 passed`.
- Verdict: PASS

Verdict B: PASS (with explicit runtime caveat in B2)

### C) Ops Acceptance

- `python3 ops/diagnose.py onboarding-fleet-check --fail-on-active-missing --json`
  - exit=1 (`/tmp/onboarding_any_niche_acceptance_a131/onboarding_fleet_check.exit`)
  - fact: one active branch not ready (`reference_pack_required_fields`, `reference_pack_required_fields_checksum`).
  - criterion result: FAIL ("Нет active branches с критичными missing" не выполнен).

- `python3 ops/diagnose.py onboarding-quality-smoke --domains beauty,clinic,legal,ecom --fail-on-regression --json`
  - exit=0 (`/tmp/onboarding_any_niche_acceptance_a131/onboarding_quality_smoke.exit`)
  - fact: domains pass, regressions none.
  - criterion result: PASS.

- `python3 ops/diagnose.py onboarding-pack-quality --domain-slug beauty --require-booking auto --client-data-text-file /tmp/onboarding_any_niche_acceptance_client_data.txt --save-summary /tmp/onboarding_any_niche_acceptance_a131/onboarding_pack_quality_summary.json --json`
  - exit=1 (`/tmp/onboarding_any_niche_acceptance_a131/onboarding_pack_quality.exit`)
  - fact: sample intake data incomplete/non-schema policy blocks compile (`pack_compile=fail`, `policy_bundle_present=false`, `signal_graph_present=false`).
  - criterion result: FAIL for this input sample.

Verdict C: FAIL (ops readiness gates currently not fully green in runtime snapshot)

## Final Verdict for TP-A

- Overall: PARTIAL
- What is closed:
  - Full contract acceptance A is green.
  - Runtime acceptance B is evidenced and contract-valid.
- What is not closed:
  - Ops acceptance C remains red on current runtime (`fleet-check` and sample `pack-quality`).

## Next Actions (to fully close end-to-end TZ)

1. Fix active branch integrity gaps (`reference_pack_required_fields*`) for `demo_salon/main`, then rerun `onboarding-fleet-check` until exit=0.
2. Provide production-grade intake payload fixture for beauty (schema-valid policy objects), then rerun `onboarding-pack-quality` until `status=pass`.
3. Re-run full C-section commands and append updated evidence to this report.
