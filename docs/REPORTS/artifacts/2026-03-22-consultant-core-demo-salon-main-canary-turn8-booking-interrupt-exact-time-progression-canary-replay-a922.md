# 2026-03-22 — Consultant Core Demo Salon Main Canary Turn 8 Booking Interrupt Exact-Time Progression Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN8-BOOKING-INTERRUPT-EXACT-TIME-PROGRESSION-CANARY-REPLAY-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn8-booking-interrupt-exact-time-progression-canary-replay-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Started a fresh local worktree runtime on `127.0.0.1:18186`, executed one guarded comparable replay, and strict-audited the fresh artifact `/tmp/booking_quality/a922-check-booking-proof-r18`.
- `r18` is infra-truthful but semantic-red: `infra_valid=true`, `semantic_valid=false`, `turns_strict_failed=0`, `responses_rows=14`, `trace_rows=14`, `blocking_reasons={'handoff_miss': 1}`.
- Fresh replay proves the bounded turn-8 runtime family is repaired on the real canary path: turn `8` now advances to `expected_reply_type=name` and persists `booking_slots.datetime='в субботу 10:00'`.
- The next surviving runtime family is no longer turn `8`. It is turn `9`, where grounded reschedule continuity keeps stale `booking_slots.datetime='в субботу 10:00'` instead of applying the new exact time `11:00` while the collect contract correctly stays on `name`.
- `r18` also exposes a proof/oracle gap: current strict/oracle lanes do not flag that stale-datetime regression as a turn failure, so runtime and proof debt must stay split.

## Truthful replay `r18`
- Run dir: `/tmp/booking_quality/a922-check-booking-proof-r18`
- Audit: `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r18 --status done --strict-artifacts`
- Run manifest: `/tmp/booking_quality/a922-check-booking-proof-r18/run_manifest.json`
- Core outcome:
  - `artifact_integrity.valid=true`
  - `infra_valid=true`
  - `semantic_valid=false`
  - `metrics.counts.turns_strict_failed=0`
  - `brief.top_failures=none`
  - `hq1_bad_turn_count=1`
  - `hq1_class_counts={'handoff_miss': 1}`
  - `judge_fail_advisory_turns=3`
  - `thresholds.breaches=[]`
  - `oracle_arbitration.judge_alignment=conflicted`
  - `oracle_arbitration.winner=contract`
  - `oracle_arbitration.conflict_count=3`
  - `run_manifest.status=invalid`
  - `run_manifest.governance_closure_reasons=['semantic_invalid_or_missing']`

## Repaired runtime family on fresh evidence
### Turn `8` exact-time progression is now closed
- user: `Я хочу записаться на 10 утра в субботу.`
- bot: `Отлично, время подходит. Как вас зовут?`
- facts from `/tmp/booking_quality/a922-check-booking-proof-r18/responses.jsonl`:
  - `expected_reply_type=name`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 10:00'}`
  - `decision_meta.action=booking_prompt`
  - `decision_meta.expected_reply_time_progression_override=true`
  - `evaluation.strict_ok=true`
- verdict:
  - the bounded turn-8 booking-interrupt exact-time progression family is now closed on truthful replay evidence

## New surviving runtime family
### Turn `9` grounded reschedule keeps stale datetime while name is pending
- user: `Могу ли я изменить время на 11 утра?`
- bot: `Отлично, время подходит. Как вас зовут?`
- facts from `/tmp/booking_quality/a922-check-booking-proof-r18/responses.jsonl`:
  - `expected_reply_type=name`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 10:00'}`
  - `decision_meta.action=booking_prompt`
  - `decision_meta.llm_policy_core_collect_slot=name`
  - `decision_meta.expected_reply_time_progression_override` is absent
  - `evaluation.strict_ok=true`
  - `hq1_classes=['handoff_miss']`
- downstream confirmation on the same artifact:
  - turn `11` stays strict-green but still carries `booking_slots.datetime='в субботу 10:00'`
  - turn `13` stays strict-green and records `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 10:00', 'name': 'Амина'}`
  - turn `14` remains strict-green handoff
- verdict:
  - turn `9` is the next honest runtime family: after turn `8` grounds `10:00`, the runtime fails to replace that grounded exact time with `11:00` when the user reschedules while `expected_reply_type=name`

## Advisory proof debt kept out of the runtime lane
### Current strict/oracle surface misses the stale-datetime regression
- `/tmp/booking_quality/a922-check-booking-proof-r18/summary.json` keeps `turns_strict_failed=0` even though turn `9` preserves stale grounded state.
- `/tmp/booking_quality/a922-check-booking-proof-r18/manual_audit.json` classifies the artifact under `judge_oracle_alignment_gap` and keeps `winner=contract`.
- HQ1 raises only `handoff_miss`, which is not the actual state regression.
- verdict:
  - this remains `oracle/proof` debt only; the next runtime move is still turn `9` grounded datetime reschedule continuity, not oracle tuning first

## Residual debt
- turn `9` grounded datetime reschedule runtime family is still open
- judge/hq1 conflicts on turns `6`, `9`, and `11` remain deferred proof debt
- duplicate top-level defs in `truffles-api/app/services/reasoning_core.py` remain recorded structural debt
- final acceptance / open-world closure remains pending

## Next move
- `implement_consultant_core_demo_salon_turn9_grounded_datetime_reschedule_runtime_family`
