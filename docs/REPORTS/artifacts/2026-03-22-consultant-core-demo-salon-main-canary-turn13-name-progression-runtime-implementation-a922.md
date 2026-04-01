# 2026-03-22 — Consultant Core Demo Salon Main Canary Turn 13 Name Progression Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN13-NAME-PROGRESSION-RUNTIME-IMPLEMENTATION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Implemented the bounded turn-13 runtime family in non-frozen `truffles-api/app/services/reasoning_core.py`.
- Added `_apply_turn_planner_explicit_name_progression_override(...)` so semantic booking recovery now reuses existing explicit-name extraction/validation before it can reopen a stale `name` prompt.
- Reused the existing booking-completion owner once the progressed `name` makes booking slots complete; no frozen router edits and no oracle weakening.
- Added focused regression coverage for the surfaced family: semantic arbitration now turns `Меня зовут Амина.` under active `expected_reply_type=name` into booking completion with `customer_name='Амина'` instead of a repeated `Как вас зовут?` prompt.
- Left replay/proof for the next block only; the next honest move is the same canary rerun on fresh runtime.

## Runtime change
- File changed: `truffles-api/app/services/reasoning_core.py`
- What landed:
  - `_apply_turn_planner_explicit_name_progression_override(...)` reuses `decision_router._update_booking_from_messages(...)` plus `decision_router._validate_expected_reply_value(...)` to capture explicit customer names without phrase hardcodes.
  - semantic booking recovery now applies that override before deciding whether to reopen `booking_prompt`; if the progressed `name` makes booking slots complete, the function now falls through to the existing booking-completion owner instead of returning early with a stale prompt.
  - semantic completion replies now carry `expected_reply_name_progression_override`, `expected_reply_name_value`, and `expected_reply_progression_override/name_merge` trace evidence when this family fires.
- Guardrails preserved:
  - no edits to frozen `decision.py`, `booking.py`, or `pending.py`
  - no new phrase-hardcoded branches
  - no proof/oracle weakening

## Regression coverage
- File changed: `truffles-api/tests/test_reasoning_core.py`
- Added:
  - `test_reasoning_core_turn_planner_semantic_booking_prompt_completes_explicit_name_progression`
- Adjacent contracts kept green:
  - `test_reasoning_core_turn_planner_safe_booking_completion_owner_bypasses_frozen_delegate_for_complete_name_turn`
  - `test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression`
  - `test_llm_policy_core_book_slot_prefers_customer_name_hint_when_slot_name_matches_specialist`

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_safe_booking_completion_owner_bypasses_frozen_delegate_for_complete_name_turn truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_completes_explicit_name_progression truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_book_slot_prefers_customer_name_hint_when_slot_name_matches_specialist` → `4 passed`
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
- judge/oracle conflicts on turns `6`, `9`, and `11` remain deferred proof debt
- broader acceptance / open-world closure remains pending

## Next move
- `rerun_consultant_core_demo_salon_turn13_name_progression_canary_replay`
