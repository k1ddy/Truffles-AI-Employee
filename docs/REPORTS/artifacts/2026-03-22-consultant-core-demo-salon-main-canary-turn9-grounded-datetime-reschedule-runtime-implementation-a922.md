# 2026-03-22 — Consultant Core Demo Salon Main Canary Turn 9 Grounded Datetime Reschedule Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-GROUNDED-DATETIME-RESCHEDULE-RUNTIME-IMPLEMENTATION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-grounded-datetime-reschedule-runtime-implementation-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Implemented the bounded turn-9 runtime family in non-frozen `truffles-api/app/services/reasoning_core.py`.
- Repaired grounded reschedule continuity so `Могу ли я изменить время на 11 утра?` can update `booking.datetime` from `в субботу 10:00` to `в субботу 11:00` while the collect contract correctly stays on `name`.
- Added focused deterministic regression coverage for the grounded-datetime reschedule family in `truffles-api/tests/test_reasoning_core.py`.
- Left acceptance/proof unchanged; the next honest move is guarded replay on the same locked canary family.

## Runtime change
- File changed: `truffles-api/app/services/reasoning_core.py`
- What landed:
  - added `_restore_turn_planner_snapshot_datetime_if_message_echo(...)` to recover snapshot-grounded datetime when `_update_booking_from_messages(...)` echoes the raw user message into `booking.datetime`.
  - extended `_apply_turn_planner_exact_time_progression_override(...)` so it can replace an already-grounded exact time (`в субботу 10:00 -> в субботу 11:00`), not only fill missing `datetime`.
  - the live booking-prompt owner path now restores snapshot datetime before exact-time merge and reapplies the override on the merged booking state.
  - the semantic booking recovery path now runs exact-time progression while `reply_slot == name` before explicit-name progression finalizes the same collect step.
  - successful grounded reschedule progression now records exact-time meta/trace evidence and persists the repaired `booking.datetime='в субботу 11:00'` into context.
- Guardrails preserved:
  - no edits to frozen `decision.py`, `booking.py`, or `pending.py`
  - no new phrase-hardcoded branches
  - no oracle/proof weakening
  - duplicate-def counts unchanged; only the active non-frozen path was repaired

## Regression coverage
- File changed: `truffles-api/tests/test_reasoning_core.py`
- Added:
  - `test_reasoning_core_turn_planner_semantic_booking_prompt_updates_grounded_datetime_while_name_pending`
- Adjacent contracts kept green:
  - existing question-like exact-time progression contract
  - existing booking-interrupt exact-time progression contract
  - existing check-booking prompt owner slice

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "updates_grounded_datetime_while_name_pending or semantic_booking_prompt_merges_question_like_exact_time_progression or booking_prompt_owner_repairs_booking_interrupt_exact_time_progression or check_booking_prompt_owner"` → `10 passed, 179 deselected`
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
- no guarded replay yet; truthful canary closure for the repaired turn-9 family is still pending
- duplicate defs remain recorded structural debt in `truffles-api/app/services/reasoning_core.py`
- proof debt on turns `6`, `9`, and `11` remains unresolved until the next replay reclassifies the artifact lane
- broader acceptance / open-world closure remains pending

## Next move
- `rerun_consultant_core_demo_salon_turn9_grounded_datetime_reschedule_canary_replay`
