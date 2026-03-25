# 2026-03-22 — Consultant Core Demo Salon Main Canary Turn 11 Check-Booking Reference Continuity Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN11-CHECK-BOOKING-REFERENCE-CONTINUITY-RUNTIME-IMPLEMENTATION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Implemented the bounded turn-11 runtime family in non-frozen `truffles-api/app/services/reasoning_core.py`.
- Repaired the live later duplicate `_try_handle_turn_planner_safe_check_booking_prompt_owner_cutover(...)` so repeated booking verification now rehydrates missing `service` / `datetime` from `conversation_snapshot`, recomputes the effective missing slot from the merged booking state, and preserves `expected_reply_type=name` instead of regressing to `service_choice`.
- Added focused deterministic regression coverage for the stale-service-choice / dropped-datetime family in `truffles-api/tests/test_reasoning_core.py`.
- Left acceptance/proof unchanged; the next honest move is still guarded replay on the same canary family.

## Runtime change
- File changed: `truffles-api/app/services/reasoning_core.py`
- What landed:
  - the live later duplicate check-booking prompt owner now restores missing `service`, `datetime`, and `active` flags from `conversation_snapshot` after message/LLM slot merging.
  - the owner now derives the effective reference collect slot from `decision_router._first_missing_booking_slot(...)` before finalizing the prompt, instead of trusting the raw `llm_candidate["collect_slot"]`.
  - when the raw candidate slot is normalized away, the owner records observability evidence via `llm_policy_core_collect_slot_original` and a `decision_trace` entry with `decision=normalize`, `reason=booking_verification_reference_continuity`.
- Guardrails preserved:
  - no edits to frozen `decision.py`, `booking.py`, or `pending.py`
  - no new phrase-hardcoded branches
  - no oracle/proof weakening
  - duplicate-def counts unchanged; only the live later duplicate was repaired

## Regression coverage
- File changed: `truffles-api/tests/test_reasoning_core.py`
- Added:
  - `test_reasoning_core_turn_planner_safe_check_booking_prompt_owner_repairs_repeated_reference_continuity_from_snapshot`
- Adjacent contracts kept green:
  - the whole `check_booking_prompt_owner` reasoning-core slice now passes (`7 passed`)
  - existing check-booking prompt owner coverage still preserves grounded `datetime`, expected-reply bypass evidence, and ambiguous-time fallback behavior

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "check_booking_prompt_owner"` → `7 passed, 180 deselected`
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
- downstream turn `13` remains unresolved until replay reaches it again
- broader acceptance / open-world closure remains pending

## Next move
- `rerun_consultant_core_demo_salon_turn11_check_booking_reference_continuity_canary_replay`
