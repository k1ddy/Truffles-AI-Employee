# 2026-03-22 — Consultant Core Demo Salon Main Canary R19 Oracle Conflict Proof Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-R19-ORACLE-CONFLICT-PROOF-DECISION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-oracle-conflict-proof-decision-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Promoted truthful replay `r19` from replay evidence to one bounded oracle/proof-family decision.
- Proved that no honest runtime blocker survives on the current canary artifact: turns `8`, `9`, `11`, `12`, `13`, and `14` are strict-green on the same run.
- Classified the remaining semantic-invalid state into two exact oracle subfamilies rooted in `ops/diagnose.py`, not in runtime:
  - semantic-blocking HQ1 false positives on turns `9` and `12`
  - advisory judge `missed_question` false positives on turns `6`, `9`, `11`, and `12`
- Locked the next move to one contract-aligned oracle implementation family inside `ops/diagnose.py` before any new replay or runtime change.

## Evidence chain
### 1. `r19` is runtime-green but still semantically invalid
- Run: `/tmp/booking_quality/a922-check-booking-proof-r19/summary.json`
- Audit: `/tmp/booking_quality/a922-check-booking-proof-r19/manual_audit.json`
- Core facts:
  - `infra_valid=true`
  - `semantic_valid=false`
  - `turns_strict_failed=0`
  - `blocking_reasons={'handoff_miss': 2}`
  - `oracle_arbitration.winner=contract`
  - `oracle_arbitration.conflict_count=4`
- Verdict:
  - the artifact is already runtime-green; the remaining red belongs to the oracle/proof lane only

### 2. Turns `9` and `12` are the semantic-blocking HQ1 false-positive family
- Artifact: `/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl`
- Turn `9` facts:
  - user: `Могу ли я изменить время на 11 утра?`
  - bot: `Отлично, время подходит. Как вас зовут?`
  - `expected_reply_type=name`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'субботу 11:00'}`
  - `evaluation.strict_ok=true`
- Turn `12` facts:
  - user: `Можно на 19:00?`
  - bot: `Отлично, время подходит. Как вас зовут?`
  - `expected_reply_type=name`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'субботу 19:00'}`
  - `evaluation.strict_ok=true`
- Why they still block semantic validity:
  - HQ1 raises `handoff_miss` on both turns because `ops/diagnose.py:9148-9162` treats `reschedule_signal + collect-like action` as blocking even when the contract already accepts active-booking `booking_prompt` continuation.
  - `ops/diagnose.py:4897-4931` already allows `booking_prompt` as a valid fallback for expected handoff during active booking continuity, so the HQ1 blocker is stricter than the contract it is supposed to summarize.
- Verdict:
  - turns `9` and `12` are not runtime regressions; they are the semantic-blocking oracle family

### 3. Turns `6`, `9`, `11`, and `12` are the judge false-positive family
- Turn `6` facts:
  - user: `Кто из мастеров лучше делает маникюр?`
  - bot: `Po usluge "Маникюр" utochnu dostupnyh masterov u administratora.`
  - `evaluation.strict_ok=true`
  - judge: `fail / missed_question`
- Turn `11` facts:
  - user: `Подтвердите, пожалуйста, запись на маникюр.`
  - bot: `Чтобы проверить, перенести или отменить запись, подскажите номер телефона и примерную дату/время записи.`
  - `decision_meta.action=check_booking_prompt`
  - `evaluation.strict_ok=true`
  - judge: `fail / missed_question`
- Turns `9` and `12` also carry judge `fail / missed_question` despite strict-green exact-time progression.
- Why this is a proof family, not a runtime family:
  - `ops/diagnose.py:12485-12488` already treats `check_booking_prompt` as a reference-collection step rather than terminal confirmation.
  - `ops/diagnose.py:4288-4443` suppresses only a narrower subset of follow-up contracts and therefore misses the currently valid booking continuity / booking verification / booking-interrupt info envelopes on this artifact.
- Verdict:
  - the judge layer is lagging behind the contract-first evaluator and manual arbitration

### 4. The root cause is oracle parity drift inside `ops/diagnose.py`
- Strict evaluator and audit already say `winner=contract`.
- Auxiliary oracle helpers still diverge:
  - `_llm_quality_should_suppress_missed_question_judge_fail(...)` is too narrow for the current strict-green follow-up envelopes.
  - `_llm_quality_collect_hq1_classes(...)` over-classifies `handoff_miss` on contract-valid active-booking continuity.
- Decision:
  - do not patch runtime
  - do not mutate the scenario first
  - do not weaken thresholds
  - fix the oracle helpers so they mirror the contract allowances already encoded elsewhere in the same file

## Admissible implementation lane
- Future implementation must stay bounded to `ops/diagnose.py` plus proof tests.
- It must do both:
  - remove false blocking `handoff_miss` for contract-valid turns `9` and `12`
  - suppress contract-valid judge `missed_question` for turns `6`, `9`, `11`, and `12`
- Explicitly not admissible:
  - runtime patching
  - threshold weakening
  - scenario mutation before oracle parity is fixed
  - generic judge-prompt churn without deterministic regression tests

## Residual debt
- contract-aligned oracle parity is still unfixed
- duplicate top-level defs in `truffles-api/app/services/reasoning_core.py` remain deferred structural debt
- final program acceptance / open-world closure remain pending

## Next move
- `implement_consultant_core_demo_salon_r19_contract_aligned_oracle_proof_family`
