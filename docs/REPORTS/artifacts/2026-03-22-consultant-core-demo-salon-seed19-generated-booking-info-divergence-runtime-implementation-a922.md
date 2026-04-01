# 2026-03-22 — Consultant Core Demo Salon Seed19 Generated Booking Info Divergence Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-GENERATED-BOOKING-INFO-DIVERGENCE-RUNTIME-IMPLEMENTATION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-implementation-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Implemented the bounded seed-`19` runtime family in non-frozen `truffles-api/app/services/reasoning_core.py` and `truffles-api/app/routers/webhook/info.py`.
- Active booking/check-booking follow-ups no longer let direct side owners preempt booking continuity for the surfaced seed-`19` hours / promo / weekend variants.
- Added focused deterministic coverage in `truffles-api/tests/test_reasoning_core.py` and `truffles-api/tests/test_master_info_flow.py`.
- Acceptance/oracle lanes remain unchanged; the next honest move is guarded replay on the same generated seed family.

## Root cause carried into implementation
- Direct side owners in `truffles-api/app/services/reasoning_core.py` can win before booking continuity recovery when active `service`/`time` requested-slot context is open.
- Explicit hours/promo phrasing is not fully normalized into the intended interruption owner for the surfaced seed-`19` variants.

## Runtime change
- File changed: `truffles-api/app/services/reasoning_core.py`
- What landed:
  - added `_should_defer_turn_planner_active_booking_side_owner(...)` and wired it into the direct `catalog_fact`, `service_query_fact`, `pricing_collect`, and `duration_collect` owner cutovers
  - the direct side-owner chain now defers when booking continuity is active on requested slot `service` or `time`, so the later booking interruption owner can recover the turn instead of leaking into irrelevant fact owners
  - explicit hours interruption resolution now prefers the `info_signals.hours=true` / `info_signals.duration!=true` envelope before duration fallback when booking interruption semantics are already active
- File changed: `truffles-api/app/routers/webhook/info.py`
- What landed:
  - added `promotions_request_rescue` so promo questions with service mention still resolve as `promotions`
  - kept explicit hours intent normalization aligned with the resolver-level `hours` signal
- Guardrails preserved:
  - no edits to frozen `decision.py`, `booking.py`, or `pending.py`
  - no oracle/proof weakening
  - no acceptance threshold changes

## Regression coverage
- File changed: `truffles-api/tests/test_reasoning_core.py`
- Added:
  - `test_reasoning_core_turn_planner_booking_prompt_owner_answers_explicit_hours_interrupt`
  - `test_reasoning_core_turn_planner_direct_catalog_fact_defers_active_booking_interrupt`
  - `test_reasoning_core_turn_planner_direct_service_query_fact_defers_active_booking_interrupt`
- File changed: `truffles-api/tests/test_master_info_flow.py`
- Added:
  - `test_detect_info_class_intents_promotions_signal_with_service_mention_rescue`

## Checks
- `pytest -q truffles-api/tests/test_master_info_flow.py -k "hours or promotions"` → `11 passed, 25 deselected`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_prompt_owner_answers_promotions_interrupt_and_resumes_time_collect or booking_prompt_owner_answers_explicit_hours_interrupt or direct_service_query_fact_defers_active_booking_interrupt or direct_catalog_fact_defers_active_booking_interrupt"` → `4 passed, 188 deselected`
- `python3 scripts/build_agent_packet.py` → `OK`
- `python3 scripts/build_agent_packet.py --check` → `OK`
- `python3 scripts/semantic_bridge_growth_guard.py` → `OK`
- `python3 scripts/continuity_writer_guard.py` → `OK`
- `python3 scripts/legacy_freeze_guard.py` → `OK`
- `python3 scripts/arch_guard.py` → `OK`
- `pytest -q truffles-api/tests/architecture` → `19 passed`
- `git diff --check` → `pass`
- `SESSION_AGENT=a922 scripts/session_check.sh` → `Session OK`

## Residual debt
- truthful replay on fresh seed `19` is still pending
- duplicate top-level defs remain recorded structural debt in `truffles-api/app/services/reasoning_core.py`
- seed `42`, PG checklist assembly, and acceptance `lock` retry remain deferred until this runtime family closes truthfully

## Next move
- `rerun_consultant_core_demo_salon_seed19_generated_booking_info_divergence_canary_replay`
