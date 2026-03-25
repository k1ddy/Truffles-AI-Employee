# 2026-03-22 — Consultant Core Demo Salon Main Canary Turn 11 Check-Booking Reference Continuity Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN11-CHECK-BOOKING-REFERENCE-CONTINUITY-CANARY-REPLAY-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-canary-replay-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Started a fresh local worktree runtime on `127.0.0.1:18186`, executed one guarded comparable replay, and strict-audited the truthful artifact `/tmp/booking_quality/a922-check-booking-proof-r17`.
- `r17` is the first truthful post-fix replay for the landed turn-11 repair: `infra_valid=true`, `semantic_valid=false`, `responses_rows=14`, `trace_rows=14`, `turns_strict_failed=0`, `top_failures=none`.
- Fresh replay proves the bounded turn-11 runtime family is repaired on the real canary path, and the dialog now reaches turn `13`, where explicit-name progression is also repaired on the same artifact.
- Remaining semantic red is no longer turn-11 state drift. It now splits into:
  - one surviving runtime family at turn `8`, where question-like exact-time fill inside active booking interrupt still stalls `booking_slot_progress_rate`
  - advisory proof debt on turns `6`, `9`, and `11`, where judge/hq1 still conflict with contract-first truth
- Next honest move: `implement_consultant_core_demo_salon_turn8_booking_interrupt_exact_time_progression_runtime_family`.

## Truthful replay `r17`
- Run dir: `/tmp/booking_quality/a922-check-booking-proof-r17`
- Audit: `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r17 --status done --strict-artifacts`
- Core outcome:
  - `artifact_integrity.valid=true`
  - `infra_valid=true`
  - `semantic_valid=false`
  - `metrics.counts.turns_strict_failed=0`
  - `brief.top_failures=none`
  - `hq1_bad_turn_count=1`
  - `hq1_class_counts={'handoff_miss': 1}`
  - `judge_fail_advisory_turns=3`
  - `thresholds.breaches=['booking_slot_progress_rate']`
  - `blocking_reasons={'handoff_miss': 1}`
  - `oracle_arbitration.judge_alignment=conflicted`
  - `oracle_arbitration.winner=contract`
  - `oracle_arbitration.conflict_count=3`

## Repaired runtime families on fresh evidence
### Turn `11` is repaired
- user: `Подтвердите, пожалуйста, запись на маникюр.`
- bot: `Чтобы проверить, перенести или отменить запись, подскажите номер телефона и примерную дату/время записи.`
- facts from `/tmp/booking_quality/a922-check-booking-proof-r17/responses.jsonl`:
  - `expected_reply_type=name`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 11:00'}`
  - `decision_meta.action=check_booking_prompt`
  - `decision_meta.expected_reply_reason=calendar_get_booking_collect_reference`
  - `evaluation.strict_ok=true`
  - no `expected_state_mismatch`
  - no `expected_reply_mismatch`
- verdict:
  - the bounded turn-11 check-booking reference continuity family is now closed on truthful replay evidence

### Turn `13` is reached and repaired
- user: `Меня зовут Амина.`
- bot: `Сейчас календарь недоступен. Напишите удобное время, и мы уточним.`
- facts from `/tmp/booking_quality/a922-check-booking-proof-r17/responses.jsonl`:
  - `expected_reply_type=name`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 11:00', 'name': 'Амина'}`
  - `decision_meta.action=reply`
  - `decision_meta.tool_action=calendar.book_slot`
  - `decision_meta.tool_decision=provider_unavailable`
  - `evaluation.strict_ok=true`
  - `judge.verdict=pass`
- verdict:
  - explicit-name progression is no longer the surviving runtime blocker; fresh replay reaches and clears the turn on the same canary artifact

## New surviving runtime family
### Turn `8` still stalls question-like exact-time progression under booking interrupt
- user: `Я хочу записаться на 10 утра в субботу.`
- bot: `Понял, Я хочу записаться на 10 утра в субботу. по услуге «Маникюр». Подскажите, пожалуйста, точное время.`
- facts from `/tmp/booking_quality/a922-check-booking-proof-r17/responses.jsonl`:
  - `turn_tags=['time']`
  - `turn_expectations.reply_type=name`
  - `expected_reply_type=time`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу'}`
  - `booking_progressed=false`
  - `decision_meta.source=question_contract`
  - `decision_meta.expected_reply_reason=booking_interrupt`
  - `decision_meta.pending_question_act=slot_constraint`
  - `evaluation.strict_ok=true`
- metric evidence from `/tmp/booking_quality/a922-check-booking-proof-r17/summary.json`:
  - `booking.progress_opportunities=1`
  - `booking.progressed=0`
  - `booking_slot_progress_rate=0.0`
  - threshold `booking_slot_progress_rate >= 0.25` breached
- repo contract anchors for why this is runtime, not only judge drift:
  - `truffles-api/tests/test_message_endpoint.py` already accepts question-like exact-time fill for expected `time` and does not block it as info
  - `truffles-api/tests/test_reasoning_core.py` already requires exact-time progression to merge `11:00` into booking datetime and advance to `expected_reply_type=name`
  - scenario contract `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json` expects turn `8` to leave the dialog on `reply_type=name`
- verdict:
  - turn `8` is the next honest runtime family: active booking-interrupt exact-time fill is still stalling on the real canary path, and current llm-quality fallback is permissive enough to hide it from strict-turn failure while the threshold still exposes the stall

## Advisory proof debt kept out of the runtime lane
### Judge conflicts on turns `6`, `9`, and `11`
- turn `6`: `Кто из мастеров лучше делает маникюр?`
  - judge: `missed_question`
  - contract layer: strict-green turn with `winner=contract`
- turn `9`: `Могу ли я изменить время на 11 утра?`
  - judge: `missed_question`
  - HQ1 classifier: `handoff_miss`
  - contract layer: strict-green turn with `expected_reply_type=name` and `booking_slots.datetime='в субботу 11:00'`
- turn `11`: `Подтвердите, пожалуйста, запись на маникюр.`
  - judge: `missed_question`
  - contract layer: strict-green after the landed runtime repair
- verdict:
  - these conflicts remain `oracle/proof` debt only; do not patch `ops/diagnose.py` before the new turn-8 runtime family is classified and handled

## Residual debt
- turn `8` booking-interrupt exact-time progression runtime family is still open
- judge/hq1 conflicts on turns `6`, `9`, and `11` remain deferred proof debt
- duplicate top-level defs in `truffles-api/app/services/reasoning_core.py` remain recorded structural debt
- final acceptance / open-world closure remains pending

## Next move
- `implement_consultant_core_demo_salon_turn8_booking_interrupt_exact_time_progression_runtime_family`
