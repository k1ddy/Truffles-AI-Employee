# 2026-03-22 — Consultant Core Demo Salon Main Canary Turn 8 Booking Interrupt Exact-Time Progression Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN8-BOOKING-INTERRUPT-EXACT-TIME-PROGRESSION-RUNTIME-IMPLEMENTATION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn8-booking-interrupt-exact-time-progression-runtime-implementation-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Implemented the bounded turn-8 runtime family in non-frozen `truffles-api/app/services/reasoning_core.py`.
- Repaired the live later duplicate `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)` so active booking-interrupt exact-time replies no longer stall on `time` when `_update_booking_from_messages(...)` pollutes `booking.datetime` with raw booking-request text.
- Added focused deterministic regression coverage for the direct booking-interrupt exact-time family in `truffles-api/tests/test_reasoning_core.py`.
- Left acceptance/proof unchanged; the next honest move is guarded replay on the same locked canary family.

## Runtime change
- File changed: `truffles-api/app/services/reasoning_core.py`
- What landed:
  - the live later duplicate booking-prompt owner now tracks `expected_reply_time_progression_meta` exactly like the earlier shadowed implementation.
  - during projected missing-slot calculation, if the merged booking state contaminates `datetime` with the raw booking request text, the owner restores the snapshot-grounded base datetime (`conversation_snapshot.booking_datetime_value`) before applying `_apply_turn_planner_exact_time_progression_override(...)`.
  - during the live merged booking-state path, the same snapshot-grounding repair now runs before the exact-time override is reapplied for the owner route.
  - successful progression now records exact-time meta/trace evidence and passes `booking_payload_override` through the shared owner finalizer so the repaired `booking.datetime='в субботу 10:00'` persists into context.
- Guardrails preserved:
  - no edits to frozen `decision.py`, `booking.py`, or `pending.py`
  - no new phrase-hardcoded branches
  - no oracle/proof weakening
  - duplicate-def counts unchanged; only the live later duplicate was repaired

## Regression coverage
- File changed: `truffles-api/tests/test_reasoning_core.py`
- Added:
  - `test_reasoning_core_turn_planner_booking_prompt_owner_repairs_booking_interrupt_exact_time_progression`
- Adjacent contracts kept green:
  - existing slot-constraint preservation after pricing interrupt
  - existing question-like exact-time progression contract
  - existing check-booking prompt owner slice

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_prompt_owner_preserves_time_slot_constraint_after_pricing_interrupt or booking_prompt_owner_repairs_booking_interrupt_exact_time_progression or semantic_booking_prompt_merges_question_like_exact_time_progression or check_booking_prompt_owner"` → `10 passed, 178 deselected`
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
- no guarded replay yet; truthful canary closure is still pending
- duplicate defs remain recorded structural debt in `truffles-api/app/services/reasoning_core.py`
- proof debt on turns `6`, `9`, and `11` remains unresolved until the next replay reclassifies the artifact lane
- broader acceptance / open-world closure remains pending

## Next move
- `rerun_consultant_core_demo_salon_turn8_booking_interrupt_exact_time_progression_canary_replay`
