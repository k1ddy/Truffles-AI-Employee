# Universal Control Plane v1 - Phase 9 Runtime Pack-Agnostic Decoupling (a500)

Date
- 2026-02-28

## Block identity
- `BLOCK_ID`: UCPV1-PHASE9
- `PARENT_BLOCK_ID`: UCPV1
- `DEPENDS_ON`: UCPV1-PHASE8
- `UNLOCKS`: UCPV1-PHASE10

## Input baseline (FACT)
- `UCPV1-PHASE8` passed and unlocked `UCPV1-PHASE9`.
- FACT pre-check identified residual demo coupling in runtime boundary:
  - hardcoded slug routing map in `pack_runtime_default`,
  - explicit `demo_salon` handler key in webhook decision map,
  - legacy demo alias wrappers in policy helpers.

## FACT pre-check evidence (before changes)
- Command: `rg -n "_PACK_ADAPTER_BY_SLUG|demo_salon" truffles-api/app/services/pack_runtime_default.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/policy.py`
- Findings:
  - `truffles-api/app/services/pack_runtime_default.py` had hardcoded demo slug route.
  - `truffles-api/app/routers/webhook/decision.py` had explicit `demo_salon` entry in `_POLICY_HANDLERS`.
  - `truffles-api/app/routers/webhook/policy.py` had demo alias helper wrappers.

## One web search evidence
- `Query (exact)` -> `Python importlib import_module documentation dynamic module loading`
- `Date/time (local)` -> `2026-02-28 06:35 (+05)`
- `Sources opened`:
  - Python docs `importlib`: https://docs.python.org/3/library/importlib.html
- `Decision`:
  - use slug-based dynamic adapter discovery via `importlib.import_module` and fail-closed fallback to generic adapter.

## Root cause validation
- `Symptom` -> phase9 remained open because runtime core still had demo-specific routing artifacts.
- `Root cause statement` -> previous dedemo waves left explicit demo mappings in core boundary instead of pure adapter discovery.
- `Proof after fix`:
  - hardcoded `_PACK_ADAPTER_BY_SLUG` removed,
  - explicit `demo_salon` key removed from `_POLICY_HANDLERS`,
  - demo alias helper wrappers removed from policy module,
  - deterministic runtime/policy suites green.

## Reuse-first outcome
- Internal reuse:
  - existing `pack_runtime_demo_adapter`,
  - existing generic fallback adapter and runtime service contracts.
- External reuse:
  - official Python `importlib` dynamic import path.
- Build-new scope:
  - only thin slug bridge module (`pack_runtime_demo_salon_adapter`) to align naming contract.

## Contract delta
- No external API contract changes.
- Internal runtime resolution contract updated:
  - adapter lookup now uses `app.services.pack_runtime_{slug}_adapter`,
  - unresolved slug falls back to `app.services.pack_runtime_generic_adapter`.

## Implemented changes
- `truffles-api/app/services/pack_runtime_default.py`
  - removed hardcoded slug map and switched to dynamic slug-based adapter resolution.
- `truffles-api/app/services/pack_runtime_demo_salon_adapter.py`
  - added slug bridge module that re-exports `pack_runtime_demo_adapter`.
- `truffles-api/app/routers/webhook/decision.py`
  - removed explicit demo key in `_POLICY_HANDLERS`.
- `truffles-api/app/routers/webhook/policy.py`
  - removed legacy demo alias helper wrappers.
- `truffles-api/tests/test_pack_runtime_service.py`
  - updated adapter-name expectation and asserted no hardcoded slug map remains.

## Checks + outcomes
- `cd truffles-api && ruff check app/services/pack_runtime_default.py app/services/pack_runtime_demo_salon_adapter.py app/routers/webhook/decision.py app/routers/webhook/policy.py tests/test_pack_runtime_service.py tests/test_policy_handler_runtime.py`
  - `All checks passed!`
- `cd truffles-api && pytest -q tests/test_pack_runtime_service.py tests/test_policy_handler_runtime.py`
  - `22 passed in 2.44s`
- `cd truffles-api && pytest -q tests/test_pack_query_engine_contract.py tests/test_pack_query_engine_abstain.py`
  - `6 passed in 1.01s`
- `cd truffles-api && pytest -q tests/test_message_endpoint.py`
  - `265 passed, 2 warnings in 68.78s`
- `cd truffles-api && pytest -q tests/test_booking_chaos_dialogs.py tests/test_booking_quality_response_guard.py tests/test_demo_salon_eval.py`
  - `70 passed in 198.79s`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
  - exit `0`
- Short smoke (non-canonical):
  - `TEST_MODE=1 python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:8031 --mode llm --count 1 --min-turns 2 --max-turns 2 --scenario-coverage none --tool-hooks off --tool-evidence-policy off --judge-mode sample --judge-sample 1 --allow-non-allowlist --skip-outbox --manager-mode skip --pending-mode skip --manual-audit-gate off --run-economy-gate off --run-id phase9-short-a521-r9`
  - `infra_valid=true`, `semantic_valid=true`, run dir `/tmp/booking_quality/phase9-short-a521-r9`.
- Canonical long acceptance run:
  - `TEST_MODE=1 python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:8041 --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --judge-mode all --fail-on-thresholds --run-id phase9-canonical-a521-r3`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/phase9-canonical-a521-r3 --status done --strict-artifacts`
  - outcome: `infra_valid=true`, `semantic_valid=false`, `run_integrity_valid=true`, `scenario_contract_valid=true`, `manual_audit_status=done`.
  - blocking reasons: `expected_action_mismatch=1`, `expected_reply_type_mismatch=3`, `judge_fail=3`, `handoff_miss=1`, `booking_flow_break=3`.

## Iteration budget outcomes
- `Planned max runs` -> `3`
- `Actual runs` -> `4` llm-quality runs (`r1`,`r2` preflight invalid and audited, `r3` canonical full, short smoke `phase9-short-a521-r9`) + deterministic suites
- `Stop condition respected` -> `yes`

## Evidence
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase9-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase9-a500.md`
- `truffles-api/app/services/pack_runtime_default.py`
- `truffles-api/app/services/pack_runtime_demo_salon_adapter.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/policy.py`
- `truffles-api/tests/test_pack_runtime_service.py`
- `/tmp/booking_quality/phase9-short-a521-r9/summary.json`
- `/tmp/booking_quality/phase9-short-a521-r9/brief.md`
- `/tmp/booking_quality/phase9-canonical-a521-r3/summary.json`
- `/tmp/booking_quality/phase9-canonical-a521-r3/brief.md`
- `/tmp/booking_quality/phase9-canonical-a521-r3/responses.jsonl`
- `/tmp/booking_quality/phase9-canonical-a521-r3/trace_bundle.jsonl`
- `/tmp/booking_quality/phase9-canonical-a521-r3/manual_audit.md`

## Release safety decision
- Production rollout status: not finalized in this session.
- Stop-the-line is active: canonical long run is complete but semantic gate is red.
- Block status moved to `blocked`; rollout to next phase is not allowed.
- Rollback path validated at code level: revert phase9 commit(s) restores prior adapter resolution.

## Canon/doc sync updates
- Updated:
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase9-a500.md`
  - `docs/BLOCK_GRAPH.yaml`
  - `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-02-28-ucpv1-phase9-pass-a521.md`
- Drift status: reduced (implementation + canonical evidence aligned), semantic remediation pending.

## Residual GAP / Risks
- Canonical long acceptance run failed semantic gate (`semantic_valid=false`) despite valid infra/integrity.
- High-signal blockers are concentrated in action/reply-type alignment and handoff/booking behavior:
  - `expected_reply_type_mismatch`
  - `booking_flow_break`
  - `handoff_miss`
- `UCPV1-PHASE10` remains locked until `UCPV1-PHASE9` is rerun with `semantic_valid=true`.

## Handoff (for zero-context next agent)
- `Ready for next agent`: yes
- `Start from`: `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase9-a500.md`
- `Do not touch`: unrelated UCP tracks and non-phase9 branches
- `Open risks`: semantic blockers from `phase9-canonical-a521-r3`
- `First command to verify`: `jq '.quality_status,.blocking_reasons,.metrics.hq1_class_counts' /tmp/booking_quality/phase9-canonical-a521-r3/summary.json`

## Verdict
- `Blocked`
