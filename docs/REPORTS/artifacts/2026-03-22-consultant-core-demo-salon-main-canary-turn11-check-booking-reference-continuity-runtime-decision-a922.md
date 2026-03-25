# 2026-03-22 — Consultant Core Demo Salon Main Canary Turn 11 Check-Booking Reference Continuity Runtime Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN11-CHECK-BOOKING-REFERENCE-CONTINUITY-RUNTIME-DECISION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-decision-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Promoted fresh canary turn `11` from replay finding to an explicit bounded runtime-family decision.
- Proved on the truthful post-fix replay `r16` that turn `9` stays repaired and turn `10` stays non-blocking.
- Locked turn `11` (`Подтвердите, пожалуйста, запись на маникюр.`) as the next real runtime contract bug because the runtime keeps the same product reply text but drops grounded `datetime`, rewrites `expected_reply_type` from `name` to `service_choice`, and fails strict state/reply continuity checks.
- Demoted turn `13` from active blocker to downstream unresolved debt because fresh replay no longer reaches it after the new turn-11 failure.
- Switched canon to this decision block and set the next non-negotiable move to bounded runtime implementation for turn-11 check-booking reference continuity.

## Evidence chain
### 1. Fresh replay truth
- Run: `/tmp/booking_quality/a922-check-booking-proof-r16/summary.json`
- Audit: `/tmp/booking_quality/a922-check-booking-proof-r16/manual_audit.json`
- Core outcome:
  - `infra_valid=true`
  - `semantic_valid=false`
  - `stop_reason=max_failures_reached:1`
  - `run_integrity_reasons=['run_completion_gap']`
  - `oracle_arbitration.judge_alignment=conflicted`
  - `oracle_arbitration.winner=contract`

### 2. Turn `9` remains repaired on the fresh runtime
- Artifact: `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl`
- Turn `9` facts:
  - user: `Могу ли я изменить время на 11 утра?`
  - bot: `Отлично, время подходит. Как вас зовут?`
  - `expected_reply_type=name`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 11:00'}`
  - `evaluation.strict_ok=true`
- Verdict:
  - the bounded turn-9 exact-time runtime family stays closed on the fresh replay path

### 3. Turn `10` remains non-blocking
- Artifact: `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl`
- Turn `10` facts:
  - user: `Проверьте, пожалуйста, мою запись на маникюр в выходные.`
  - bot: `Чтобы проверить, перенести или отменить запись, подскажите номер телефона и примерную дату/время записи.`
  - `expected_reply_type=name`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 11:00'}`
  - `evaluation.strict_ok=true`
- Verdict:
  - old stale turn-10 proof drift remains closed

### 4. Turn `11` is the surviving runtime contradiction
- Artifact: `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl`
- Turn `11` facts:
  - user: `Подтвердите, пожалуйста, запись на маникюр.`
  - bot: `Чтобы проверить, перенести или отменить запись, подскажите номер телефона и примерную дату/время записи.`
  - `expected_reply_type=service_choice`
  - `booking_slots={'service': 'Маникюр'}`
  - `evaluation.reasons=['expected_state_mismatch', 'expected_reply_mismatch']`
  - `decision_meta.expected_reply_reason=calendar_get_booking_collect_reference`
  - `decision_meta.expected_reply_bypassed=booking_verification`
  - `decision_meta.llm_policy_core_collect_slot=service`
- Contrast against the last truthful predecessor:
  - `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl` on the same turn kept `expected_reply_type=name`
  - `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl` on the same turn kept `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 11:00'}`
  - the same turn previously passed strict contract checks
- Verdict:
  - turn `11` is a real runtime contract bug on the fresh runtime, not a judge-only or replay-freshness dispute

### 5. What this means for turn `13`
- `r16` stops at turn `11` because `max_failures=1` is reached on the new state/reply mismatch.
- Fresh replay therefore never reaches `Меня зовут Амина.`.
- Decision:
  - turn `13` remains unresolved downstream debt only; it is no longer the first admissible blocker for the next runtime block.

### 6. Advisory proof debt that stays out of the runtime lane
- `/tmp/booking_quality/a922-check-booking-proof-r16/manual_audit.json` reports `judge_alignment=conflicted`, `winner=contract`, `conflict_count=2`.
- Conflicted judge-only turns on this artifact are advisory proof debt, not the turn-11 runtime bug itself.
- Decision:
  - keep judge conflicts out of the next runtime implementation lane.

## Admissible implementation lane
- Future implementation must stay bounded to existing generic contracts:
  - preserve grounded booking verification reference state once `name`/`datetime` are already active
  - avoid rewriting the requested slot from `name` to `service` mid-verification without contract cause
  - keep observable `decision_meta/decision_trace` evidence for the preserved continuity path
- Explicitly not admissible:
  - proof/oracle weakening as a substitute for runtime repair
  - phrase-hardcoded handling for booking confirmation wording
  - reopening turn `9` or stale turn `13` work before the new blocker is fixed
  - widening into frozen `decision.py`, `booking.py`, or `pending.py`

## Residual debt
- turn `11` runtime family is still unfixed
- turn `13` explicit-name progression remains unresolved downstream because fresh replay no longer reaches it
- judge conflicts on turns `6` and `9` remain deferred proof debt
- guarded acceptance rerun is blocked until turn `11` lands
- multi-pack / open-world closure remains pending

## Next move
- `implement_consultant_core_demo_salon_turn11_check_booking_reference_continuity_runtime_family`
