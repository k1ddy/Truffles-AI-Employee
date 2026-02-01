# 2026-02-01 Pack Compiler Implementation Report

## Scope
- Pack compiler + compiled artifacts (pack-index + signal graph + policy bundle).
- Runtime consumption of compiled artifacts only.
- Policy/Signal DSL schemas + validation.
- Auto-ingest learned responses approval flow (manual + auto-approve roles).
- Shadow replay report tool (decision_meta/trace).
- Time-only guard restore for legacy routing (prevents 500s).

## Evidence (tests and runs)
- pytest: `pytest -q truffles-api/tests/test_pack_compiler.py`
  - log: `/tmp/pytest_pack_compiler_2026-02-01.txt`
- pytest: `pytest -q truffles-api/tests/test_policy_dsl.py`
  - log: `/tmp/pytest_policy_dsl_2026-02-01.txt`
- pytest: `pytest -q truffles-api/tests/test_knowledge_snapshot_gateway.py`
  - log: `/tmp/pytest_knowledge_snapshot_gateway_2026-02-01.txt`
- pytest: `pytest -q truffles-api/tests/test_learning_service.py`
  - log: `/tmp/pytest_learning_service_2026-02-01.txt`
- pytest: `pytest -q truffles-api/tests/test_message_endpoint.py -k "signal_snapshot and pack_index"`
  - log: `/tmp/pytest_message_signal_snapshot_2026-02-01.txt`
- golden eval: `EVAL_TIER=core pytest -q truffles-api/tests/test_demo_salon_eval.py::test_demo_salon_eval_cases`
  - log: `/tmp/pytest_golden_eval_pack_compiler_2026-02-01.txt`
- time-only guard test: `pytest -q truffles-api/tests/test_webhook_response.py::test_time_only_guard_detection`
  - log: `/tmp/pytest_time_only_guard_2026-02-01.txt`

## Chaos-sim + shadow replay
- chaos-sim command (booking, logic mode): see Task Package
  - artifacts: `/tmp/chaos_pack_compiler` (report.md, failures.partial.jsonl)
  - log: `/tmp/chaos_pack_compiler_run_2026-02-01.txt`
  - summary: failures=21 (action_mismatch/ood_false_positive/pending_action_mismatch/state_mismatch)
- shadow replay report:
  - input: `/tmp/trace_bundle_pack_compiler.json`
  - report: `/tmp/shadow_replay_pack_compiler.md`

## Notes
- Chaos-sim failures included HTTP 500 in the earlier run. Root cause: missing
  `_looks_like_time_only_request` symbol in webhook legacy adapter.
- Fix landed in `truffles-api/app/routers/webhook/decision.py`; chaos-sim not rerun after fix.
