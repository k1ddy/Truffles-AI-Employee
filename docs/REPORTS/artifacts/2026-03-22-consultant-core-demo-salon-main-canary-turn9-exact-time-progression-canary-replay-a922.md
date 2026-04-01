# 2026-03-22 — Consultant Core Demo Salon Main Canary Turn 9 Exact-Time Progression Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-EXACT-TIME-PROGRESSION-CANARY-REPLAY-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Refreshed the local worktree runtime on `:18186`, reran the exact comparable scenario as `/tmp/booking_quality/a922-check-booking-proof-r14`, and completed strict audit.
- The fresh replay is now truthful runtime evidence for the landed turn-9 fix: `infra_valid=true`, refreshed runtime parity is real, and turn `9` now progresses to `expected_reply_type=name` with `booking_slots.datetime='в субботу 11:00'`.
- Turn `12` no longer survives as an independent blocker on the fresh artifact; it now emits the expected handoff state and reply.
- The replay remains semantically red only because a new bounded runtime family surfaced at turn `13` (`Меня зовут Амина.`), where explicit name fill loops back into stale `booking_prompt/name`.
- Next honest move: bounded runtime decision and implementation for turn `13`; do not reopen runtime freshness or turn-12 oracle arguments.

## Replay artifact
- Run dir: `/tmp/booking_quality/a922-check-booking-proof-r14`
- Manual audit: `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r14 --status done --strict-artifacts`
- Audit verdict:
  - `artifact_integrity.valid=true`
  - `infra_valid=true`
  - `semantic_valid=false`
  - `stop_reason=max_failures_reached:1`
  - `run_integrity_reasons=['run_completion_gap']`
  - `oracle_arbitration.judge_alignment=conflicted`
  - `oracle_arbitration.winner=contract`

## Refreshed-runtime evidence
- Local uvicorn was restarted from the current worktree with the repo `.env` sourced.
- Post-refresh runtime checks:
  - `http://127.0.0.1:18186/admin/version` → `200`
  - `http://127.0.0.1:18186/admin/health` → `200`
  - fresh listener PID differs from stale `r13` process and postdates the landed `reasoning_core.py` change
- Conclusion:
  - `r14` is the first truthful post-fix replay artifact for this family; stale-runtime objections from `r13` are closed.

## Surfaced turns
- `turn 9`:
  - user: `Могу ли я изменить время на 11 утра?`
  - bot: `Отлично, время подходит. Как вас зовут?`
  - `expected_reply_type=name`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 11:00'}`
  - verdict: repaired on the fresh runtime
- `turn 12`:
  - user: `Можно на 19:00?`
  - bot: `Передал менеджеру — сообщения уходят администратору...`
  - `conversation_state=pending`
  - `decision_meta.tool_action=handoff`
  - verdict: old turn-12 blocker no longer survives on fresh evidence
- `turn 13`:
  - user: `Меня зовут Амина.`
  - bot: `Отлично, время подходит. Как вас зовут?`
  - `expected_reply_type=name`
  - `evaluation.reasons=['booking_slot_stall']`
  - verdict: new surviving runtime family

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_booking_prompt_owner_preserves_time_slot_constraint_after_pricing_interrupt truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_booking_prompt_owner_keeps_time_followup_for_ambiguous_daypart_reply truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression truffles-api/tests/test_message_endpoint.py::test_expected_reply_time_merges_datetime_and_clears_stale_intent_queue truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_reschedule_missing_reference_escalates_to_handoff truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_reschedule_missing_reference_availability_phrase_escalates_to_handoff` → `6 passed`
- `python3 ops/diagnose.py llm-quality ... --run-id a922-check-booking-proof-r14 ...` → produced fresh comparable replay artifact on the refreshed runtime
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r14 --status done --strict-artifacts` → `done`

## Residual debt
- turn `13` name progression now becomes the active runtime family
- judge/oracle advisory conflicts on turns `6`, `9`, and `11` remain proof debt only
- final acceptance / open-world closure remains pending

## Next move
- `implement_consultant_core_demo_salon_turn13_name_progression_runtime_family`
