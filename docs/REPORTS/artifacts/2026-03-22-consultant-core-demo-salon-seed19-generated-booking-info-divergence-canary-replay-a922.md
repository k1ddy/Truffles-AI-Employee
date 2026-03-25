# 2026-03-22 — Consultant Core Demo Salon Seed19 Generated Booking Info Divergence Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-GENERATED-BOOKING-INFO-DIVERGENCE-CANARY-REPLAY-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Rejected two non-canonical pre-runs before closure:
  - `a922-go2f-seed19-r2` fail-closed at preflight because the command omitted explicit `--quality-lane dev` and was interpreted as acceptance lock
  - `a922-go2f-seed19-r3` was interrupted after proving scenario drift because it regenerated new seed scenarios instead of replaying `/tmp/booking_quality/a922-go2f-seed19/scenarios.json`
- Ran one exact replay on the original blocker surface as `/tmp/booking_quality/a922-go2f-seed19-r4` with runtime parity `HEAD == /admin/version.git_commit`.
- Fresh exact replay `r4` is not a new runtime-proof closure artifact:
  - `infra_valid=false`
  - `semantic_valid=false`
  - `stop_reason=max_failures_reached:1`
  - `tool_evidence_reasons=['confirm_hook_missing']`
- The bounded seed-`19` runtime family is therefore not yet reclassified from `r4`; the new first blocker is an infra/tool-evidence gap on confirm-hook materialization under the replay surface.

## Fresh replay evidence
- Exact replay command reused the original blocker scenarios and baseline:
  - `--scenarios-file /tmp/booking_quality/a922-go2f-seed19/scenarios.json`
  - `--baseline-summary /tmp/booking_quality/a922-go2f-seed19/summary.json`
  - runtime parity: `0d8d2078697193832a2d6cae6709a2d7489bf9ca == /admin/version.git_commit`
- Fresh exact replay artifact:
  - `/tmp/booking_quality/a922-go2f-seed19-r4/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r4/responses.jsonl`
  - `/tmp/booking_quality/a922-go2f-seed19-r4/manual_audit.json`

## Truthful split
- `r4` is a valid exact replay attempt on the original scenarios, but it is not a valid closure artifact because tool evidence is infra-red:
  - previous blocker artifact `/tmp/booking_quality/a922-go2f-seed19/summary.json` had `infra_valid=true`, `tool_evidence_valid=true`, `confirm_tool_events=8`, `confirm_hook_events=2`
  - fresh exact replay `/tmp/booking_quality/a922-go2f-seed19-r4/summary.json` has `infra_valid=false`, `tool_evidence_valid=false`, `confirm_tool_events=2`, `confirm_hook_events=0`
- This makes the first surviving blocker an infra/tool-evidence family, not a fresh runtime-semantics decision.
- The semantic row that stopped fail-fast is downstream until infra is restored:
  - `LLM-QUAL-a922-go2f-seed19-r4-002-09-070349`
  - user: `На какое время лучше записаться?`
  - actual runtime path: `turn_planner_safe_explicit_handoff_owner`
  - strict reasons: `expected_meta_mismatch`, `expected_trace_miss`
  - current audit still keeps oracle conflict as advisory: `winner=contract`, `conflict_count=2`

## Replay hygiene findings
- `r2` is closed as invalid command-shape drift; it cannot be used for replay truth.
- `r3` is closed as non-canonical scenario drift; it cannot be used for replay truth.
- `r4` is the first truthful exact replay attempt on the original blocker scenarios.
- Because `r4` is infra-invalid, the seed-`19` runtime family remains unresolved and must not trigger new runtime code before the infra family is classified.

## Checks
- `pytest -q truffles-api/tests/test_master_info_flow.py -k "hours or promotions"` → `11 passed, 25 deselected`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_prompt_owner_answers_promotions_interrupt_and_resumes_time_collect or booking_prompt_owner_answers_explicit_hours_interrupt or direct_service_query_fact_defers_active_booking_interrupt or direct_catalog_fact_defers_active_booking_interrupt"` → `4 passed, 188 deselected`
- runtime parity probe against `http://127.0.0.1:18186/admin/version` → `match=True`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r4 --status done --strict-artifacts`

## Closure verdict
- No new runtime fix is admissible yet from `r4`.
- The next honest move is `classify_consultant_core_demo_salon_seed19_r4_confirm_hook_gap_before_any_runtime_changes`.
