# 2026-03-22 — Consultant Core Demo Salon Main Canary Turn 9 Exact-Time Progression Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-EXACT-TIME-PROGRESSION-RUNTIME-IMPLEMENTATION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-implementation-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Implemented the bounded turn-9 runtime family in non-frozen `truffles-api/app/services/reasoning_core.py`.
- Reused `decision_router._apply_expected_reply_slot(...)` to merge question-like exact time into the existing partial booking datetime.
- Reused `_finalize_turn_planner_owner_cutover(...)` with `booking_payload_override` so the grounded datetime actually persists into canonical booking context.
- Added focused regression coverage for the real surfaced family: semantic booking recovery now advances `Могу ли я изменить время на 11 утра?` from partial `в субботу` to grounded `в субботу 11:00` and `expected_reply_type=name`.
- Left turn `12` untouched as deferred oracle/proof debt; the next honest move is guarded replay.

## Runtime change
- File changed: `truffles-api/app/services/reasoning_core.py`
- What landed:
  - `_apply_turn_planner_exact_time_progression_override(...)` detects grounded exact time under active time collect, reuses the existing expected-reply slot merger, and emits trace/meta evidence.
  - active booking-prompt owner now reapplies that override before final prompt selection and persists the merged booking payload when the override fires.
  - semantic booking recovery now applies the same override before reopening booking prompts and persists the merged booking payload in context.
- Guardrails preserved:
  - no edits to frozen `decision.py`, `booking.py`, or `pending.py`
  - no new phrase-hardcoded branches
  - no oracle weakening

## Regression coverage
- File changed: `truffles-api/tests/test_reasoning_core.py`
- Added:
  - `test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression`
- Existing adjacent tests kept green:
  - `test_reasoning_core_turn_planner_booking_prompt_owner_preserves_time_slot_constraint_after_pricing_interrupt`
  - `test_reasoning_core_turn_planner_booking_prompt_owner_keeps_time_followup_for_ambiguous_daypart_reply`
- Existing endpoint contracts kept green:
  - `test_expected_reply_time_merges_datetime_and_clears_stale_intent_queue`
  - `test_llm_policy_core_reschedule_missing_reference_escalates_to_handoff`
  - `test_llm_policy_core_reschedule_missing_reference_availability_phrase_escalates_to_handoff`

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_booking_prompt_owner_preserves_time_slot_constraint_after_pricing_interrupt truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_booking_prompt_owner_keeps_time_followup_for_ambiguous_daypart_reply truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression truffles-api/tests/test_message_endpoint.py::test_expected_reply_time_merges_datetime_and_clears_stale_intent_queue truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_reschedule_missing_reference_escalates_to_handoff truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_reschedule_missing_reference_availability_phrase_escalates_to_handoff` → `6 passed`
- `python3 scripts/build_agent_packet.py` → `OK`
- `python3 scripts/build_agent_packet.py --check` → `OK`
- `python3 scripts/semantic_bridge_growth_guard.py` → `OK`
- `python3 scripts/continuity_writer_guard.py` → `OK`
- `python3 scripts/legacy_freeze_guard.py` → `OK`
- `python3 scripts/arch_guard.py` → `OK`
- `pytest -q truffles-api/tests/architecture` → `18 passed`
- `git diff --check` → `pass`
- `SESSION_AGENT=a922 scripts/session_check.sh` → `Session OK`

## Residual debt
- no guarded replay yet; real canary evidence is still pending
- turn `12` remains deferred oracle/proof debt until replay proves whether it survives after the turn-9 fix
- broader acceptance / open-world closure remains pending

## Next move
- `rerun_consultant_core_demo_salon_turn9_exact_time_progression_canary_replay`
