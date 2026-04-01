# 2026-03-22 — Consultant Core Demo Salon Main Canary Turn 13 Name Progression Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN13-NAME-PROGRESSION-CANARY-REPLAY-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-canary-replay-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Started a fresh local worktree runtime on `127.0.0.1:18186`, reran the locked canary scenario, and completed strict audit on the truthful replay artifact `/tmp/booking_quality/a922-check-booking-proof-r16`.
- Two pre-run attempts were audited and excluded as non-canonical infra events:
  - `/tmp/booking_quality/20260322-045721-2026-03-15-consultant-core-governance-lock-a922-a6f123ec-p577437-ec5bea` failed replay-isolation preflight (`reset_before_dialog_required`)
  - `/tmp/booking_quality/a922-check-booking-proof-r15` failed because the guard blocked on that pending manual audit, then consumed the same replay fingerprint
- Fresh replay `r16` is the first truthful post-fix artifact for this lane: `infra_valid=true`, `semantic_valid=false`, `stop_reason=max_failures_reached:1`.
- Turn `9` remains repaired on the fresh runtime, but the replay now stops earlier at turn `11`, where the booking-verification collect-reference path drops grounded `datetime`, flips `expected_reply_type` from `name` to `service_choice`, and fails strict contract checks before turn `13` is reached.
- Because the canary never reaches turn `13` on `r16`, the old explicit-name family is no longer the first surviving blocker; the next honest move is bounded classification/implementation for turn `11` check-booking reference continuity.

## Runtime evidence
- Fresh runtime was started from the current worktree with the canonical repo env sourced and `TEST_MODE=1` forced.
- Runtime health/version:
  - `http://127.0.0.1:18186/admin/version` → `200`, `git_commit=0d8d2078697193832a2d6cae6709a2d7489bf9ca`
  - `http://127.0.0.1:18186/admin/health` → `200`
- Focused deterministic pre-check remained green:
  - `pytest -q truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_safe_booking_completion_owner_bypasses_frozen_delegate_for_complete_name_turn truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_completes_explicit_name_progression truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_book_slot_prefers_customer_name_hint_when_slot_name_matches_specialist` → `4 passed`

## Non-canonical replay attempts (audited, excluded)
### 1. Ad-hoc direct replay preflight
- Run dir: `/tmp/booking_quality/20260322-045721-2026-03-15-consultant-core-governance-lock-a922-a6f123ec-p577437-ec5bea`
- Outcome:
  - `infra_valid=false`
  - `semantic_valid=false`
  - `stop_reason=invalid_preflight`
  - root reason: `reset_before_dialog_required`
- Audit: `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/20260322-045721-2026-03-15-consultant-core-governance-lock-a922-a6f123ec-p577437-ec5bea --status done --strict-artifacts`
- Verdict:
  - non-canonical command-shape attempt; excluded from replay truth

### 2. Guarded run `r15`
- Run dir: `/tmp/booking_quality/a922-check-booking-proof-r15`
- Outcome:
  - `infra_valid=false`
  - `semantic_valid=false`
  - `stop_reason=invalid_preflight`
  - root reason: guard stop on pending manual audit from the prior invalid attempt
- Audit: `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r15 --status done --strict-artifacts`
- Verdict:
  - non-canonical guard/gate artifact; excluded from replay truth

## Truthful replay `r16`
- Run dir: `/tmp/booking_quality/a922-check-booking-proof-r16`
- Audit: `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r16 --status done --strict-artifacts`
- Core outcome:
  - `artifact_integrity.valid=true`
  - `infra_valid=true`
  - `semantic_valid=false`
  - `stop_reason=max_failures_reached:1`
  - `run_integrity_reasons=['run_completion_gap']`
  - `oracle_arbitration.judge_alignment=conflicted`
  - `oracle_arbitration.winner=contract`
  - `oracle_conflict_count=2`

## Surfaced turns
### Turn `9` stays repaired
- user: `Могу ли я изменить время на 11 утра?`
- bot: `Отлично, время подходит. Как вас зовут?`
- facts:
  - `expected_reply_type=name`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 11:00'}`
  - `decision_meta.expected_reply_time_progression_override=true`
  - `evaluation.strict_ok=true`
- verdict:
  - the exact-time runtime family remains closed on fresh post-fix evidence

### Turn `10` stays non-blocking
- user: `Проверьте, пожалуйста, мою запись на маникюр в выходные.`
- bot: `Чтобы проверить, перенести или отменить запись, подскажите номер телефона и примерную дату/время записи.`
- facts:
  - `expected_reply_type=name`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 11:00'}`
  - `evaluation.strict_ok=true`
- verdict:
  - stale turn-10 proof drift remains closed

### Turn `11` is the new first surviving blocker
- user: `Подтвердите, пожалуйста, запись на маникюр.`
- bot: `Чтобы проверить, перенести или отменить запись, подскажите номер телефона и примерную дату/время записи.`
- facts:
  - `evaluation.reasons=['expected_state_mismatch', 'expected_reply_mismatch']`
  - `expected_reply_type=service_choice`
  - `booking_slots={'service': 'Маникюр'}`
  - `decision_meta.expected_reply_reason=calendar_get_booking_collect_reference`
  - `decision_meta.llm_policy_core_collect_slot=service`
- contrast with truthful pre-fix artifact `r14`:
  - same turn previously preserved `expected_reply_type=name`
  - same turn previously preserved `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 11:00'}`
  - same turn previously passed strict contract checks
- verdict:
  - the canary now surfaces a bounded runtime continuity contradiction in the check-booking reference collect lane before the dialog can reach turn `13`

## Classification
- `turn 11` = `runtime contract bug`
- `turn 13` = `not re-evaluated on truthful post-fix replay`
- Why:
  - `r16` is infra-valid and comparable on the locked scenario surface
  - the first strict failure is not judge-only wording drift; it is state/expected-reply contract drift in runtime metadata
  - because `max_failures=1` stops at turn `11`, turn `13` can no longer be treated as the first surviving blocker on fresh evidence

## Residual debt
- turn `11` check-booking reference continuity runtime family is now unfixed
- turn `13` explicit-name progression remains unresolved because fresh replay no longer reaches it
- judge conflicts on turns `6` and `9` remain advisory proof debt only
- final acceptance / open-world closure remains pending

## Next move
- `author_consultant_core_demo_salon_turn11_check_booking_reference_continuity_runtime_tp`
