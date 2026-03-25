# 2026-03-21 — Consultant Core Demo Salon Main Canary Preflight Proof Gap A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-PREFLIGHT-PROOF-GAP-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-demo-salon-main-canary-preflight-proof-gap-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Proved that `a922-promo-l2-preflight-r9` turn `10` was a stale oracle/proof artifact, not the next runtime blocker.
- Refreshed the scenario artifact via the existing sanitizer and reran the same dialog on the fresh runtime as `a922-check-booking-proof-r12`.
- `r12` finished `infra_valid=true`, `turns_strict_failed=0`, `failure_family_count=0`, so the old `check_booking_prompt` mismatch is closed as a proof-layer drift.
- 2026-03-22 classification split the residual red truthfully:
  - turn `9` is a real runtime-contract bug on exact-time progression under active `time` collect
  - turn `12` is an oracle/proof weakness on the current artifact because strict fallback still permits `booking_prompt` for expected `handoff` while booking remains active

## Evidence chain
### 1. Stale turn-10 blocker in `r9`
- Run: `/tmp/booking_quality/a922-promo-l2-preflight-r9/summary.json`
- First fail:
  - `message_id=LLM-QUAL-a922-promo-l2-preflight-r9-001-10-c0363e`
  - user text: `Проверьте, пожалуйста, мою запись на маникюр в выходные.`
  - actual runtime path: `decision_meta.action=check_booking_prompt`, `source=booking_verification`
  - strict reason: `expected_action_mismatch`
- Repo anchors already agreed with runtime, not the scenario:
  - `truffles-api/tests/test_reasoning_core.py:9518`
  - `truffles-api/tests/test_reasoning_core.py:9649`
  - `truffles-api/tests/test_reasoning_core.py:9655`
  - `truffles-api/tests/test_message_endpoint.py:29096`
  - `truffles-api/tests/test_message_endpoint.py:29256`

### 2. Refreshed scenario artifact
- Refreshed file: `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`
- Turn `10` after sanitization:
  - `tags=['check_booking']`
  - `expect.action=null`
  - `expect.reply_type=null`
  - `expect.state='bot_active'`
- Key observation:
  - current sanitizer already removes the stale action claim, so replaying the old file was the proof drift.

### 3. Refreshed run `r12`
- Run: `/tmp/booking_quality/a922-check-booking-proof-r12/summary.json`
- Audit: `/tmp/booking_quality/a922-check-booking-proof-r12/manual_audit.json`
- Outcome:
  - `infra_valid=true`
  - `semantic_valid=false`
  - `turns_strict_failed=0`
  - `failure_family_count=0`
  - `run_integrity_valid=true`
- `r12` no longer stops on turn `10`; the dialog completes all 14 turns.

## Classification verdict
- `manual_audit.json` records:
  - `judge_alignment='conflicted'`
  - `winner='contract'`
  - `analyst_root_causes=['judge_oracle_alignment_gap']`
- Turn `9` — `runtime contract bug`
  - turn text: `Могу ли я изменить время на 11 утра?`
  - bot: `Понял, в субботу по услуге «Маникюр». Подскажите, пожалуйста, точное время.`
  - current artifact keeps `expected_reply_type=time` and `booking_slots.datetime='в субботу'`
  - repo anchors contradict that outcome:
    - `truffles-api/tests/test_message_endpoint.py` already proves exact time should merge into the active time prompt contract and clear the stale expected-reply queue
    - `truffles-api/tests/test_booking_dialog_scenarios_script.py` already normalizes explicit time fill out of `slot_constraint` into `reply_type=name`
    - `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml` row `M13` already states that once `datetime` is grounded under active `slot_constraint`, canonical post-grounding contract becomes `expected_reply_type=name`
    - `truffles-api/tests/test_message_endpoint.py` already escalates exact-time reschedule-without-reference turns to handoff rather than re-asking for exact time
  - verdict:
    - the runtime is regressing to stale `time` re-ask semantics on an explicit exact-time fill; this is the next bounded runtime family, not a judge-only disagreement
- Turn `12` — `oracle/proof gap`
  - turn text: `Можно на 19:00?`
  - bot: `Отлично, время подходит. Как вас зовут?`
  - judge: `missed_question`
  - HQ1 class: `handoff_miss`
  - strict evaluation still passes because `ops/diagnose.py` fallback currently accepts `booking_prompt` for expected `handoff/escalate` turns while `booking_active=true`
  - current `r12` trace/meta do not prove that the runtime actually resolved this turn through the explicit reschedule-handoff contract; they only prove that permissive fallback left it advisory
  - verdict:
    - turn `12` is an oracle/proof weakness on the current artifact, not a proved runtime bug yet
- Sequencing consequence:
  - turn `9` must be fixed or reproduced into a bounded runtime family first
  - turn `12` cannot be tightened truthfully until a post-fix rerun shows whether it survives independently of the turn-9 stall/state drift

## Operational nuances
- `r10` and `r11` were invalid dry evidence only:
  - both failed scenario preflight because `run_economy_gate` defaulted to `block` on the ad-hoc command shape
  - both were manually audited and discarded
- Stale-scenario risk remains real:
  - `ops/diagnose.py llm-quality` replays `--scenarios-file` payloads as-is; old scenario artifacts can reopen already-closed proof families.

## Residual debt
- turn `9` runtime exact-time progression family remains unfixed
- turn `12` oracle/proof weakness remains untightened until a post-fix rerun proves it survives independently
- guarded `demo_salon/main` acceptance lock/replay/full remains blocked until that classification is closed
- multi-pack / open-world closure remains pending

## Next move
- `author_consultant_core_demo_salon_turn9_exact_time_progression_runtime_tp`
