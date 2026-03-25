# 2026-03-22 — Consultant Core Demo Salon Main Canary Turn 9 Grounded Datetime Reschedule Canary Replay A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-GROUNDED-DATETIME-RESCHEDULE-CANARY-REPLAY-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-grounded-datetime-reschedule-canary-replay-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Started a fresh local worktree runtime on `127.0.0.1:18186`, executed one guarded comparable replay, and strict-audited the fresh artifact `/tmp/booking_quality/a922-check-booking-proof-r19`.
- `r19` is now the truthful post-fix replay for the turn-9 family: `infra_valid=true`, `semantic_valid=false`, `turns_strict_failed=0`, `responses_rows=14`, `trace_rows=14`, `stop_reason=null`.
- Fresh replay proves the bounded turn-9 grounded-datetime reschedule runtime family is repaired on the real canary path: turn `9` now keeps the collect contract on `name` and updates grounded `booking.datetime` to `субботу 11:00`.
- No new runtime blocker survives on `r19`. Turns `8`, `11`, `12`, `13`, and `14` are strict-green on the same artifact.
- Remaining semantic red is proof-only: judge/HQ1 conflict with contract-first truth on turns `6`, `9`, `11`, and `12` (`winner=contract`).

## Truthful replay `r19`
- Run dir: `/tmp/booking_quality/a922-check-booking-proof-r19`
- Audit: `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r19 --status done --strict-artifacts`
- Run manifest: `/tmp/booking_quality/a922-check-booking-proof-r19/run_manifest.json`
- Core outcome:
  - `artifact_integrity.valid=true`
  - `infra_valid=true`
  - `semantic_valid=false`
  - `metrics.counts.turns_strict_failed=0`
  - `brief.top_failures=none`
  - `hq1_bad_turn_count=2`
  - `hq1_class_counts={'handoff_miss': 2}`
  - `blocking_reasons={'handoff_miss': 2}`
  - `oracle_arbitration.judge_alignment=conflicted`
  - `oracle_arbitration.winner=contract`
  - `oracle_arbitration.conflict_count=4`
  - `thresholds.breaches=[]`

## Runtime closure proved on fresh evidence
### Turn `9` grounded-datetime reschedule is now closed
- user: `Могу ли я изменить время на 11 утра?`
- bot: `Отлично, время подходит. Как вас зовут?`
- facts from `/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl`:
  - `expected_reply_type=name`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'субботу 11:00'}`
  - `decision_meta.action=booking_prompt`
  - `decision_meta.llm_policy_core_collect_slot=name`
  - `decision_meta.expected_reply_time_progression_override=true`
  - `evaluation.strict_ok=true`
- verdict:
  - the bounded turn-9 grounded-datetime reschedule runtime family is now closed on truthful replay evidence

### Adjacent runtime path remains contract-green
- turn `8` stays repaired:
  - `booking_slots={'service': 'Маникюр', 'datetime': 'субботу 10:00'}`
  - `expected_reply_type=name`
  - `evaluation.strict_ok=true`
- turn `11` stays repaired:
  - `action=check_booking_prompt`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'субботу 11:00'}`
  - `evaluation.strict_ok=true`
- turn `12` is contract-green on the same path:
  - `booking_slots={'service': 'Маникюр', 'datetime': 'субботу 19:00'}`
  - `expected_reply_type=name`
  - `decision_meta.expected_reply_time_progression_override=true`
  - `evaluation.strict_ok=true`
- turns `13` and `14` remain strict-green handoff/escalation turns.
- note:
  - the replay normalizes grounded datetime strings to `субботу HH:MM` without the leading preposition `в`; strict contract acceptance remains green, so this artifact does not establish a new runtime blocker.

## Remaining semantic red is proof debt only
### Judge/HQ1 conflicts on turns `6`, `9`, `11`, and `12`
- turn `6`: `Кто из мастеров лучше делает маникюр?`
  - judge: `fail / missed_question`
  - contract layer: strict-green turn with `winner=contract`
- turn `9`: `Могу ли я изменить время на 11 утра?`
  - judge: `fail / missed_question`
  - HQ1: `handoff_miss`
  - contract layer: strict-green turn with repaired grounded datetime
- turn `11`: `Подтвердите, пожалуйста, запись на маникюр.`
  - judge: `fail / missed_question`
  - contract layer: strict-green verification collect reference turn
- turn `12`: `Можно на 19:00?`
  - judge: `fail / missed_question`
  - HQ1: `handoff_miss`
  - contract layer: strict-green exact-time follow-up under active booking continuity
- verdict:
  - `r19` leaves no honest runtime blocker; the remaining semantic invalid status belongs to the oracle/proof lane only

## Residual debt
- proof/oracle debt remains on turns `6`, `9`, `11`, and `12`
- duplicate top-level defs in `truffles-api/app/services/reasoning_core.py` remain recorded structural debt
- final acceptance / open-world closure remains pending

## Next move
- `classify_consultant_core_demo_salon_r19_oracle_conflict_proof_gap_before_any_runtime_changes`
