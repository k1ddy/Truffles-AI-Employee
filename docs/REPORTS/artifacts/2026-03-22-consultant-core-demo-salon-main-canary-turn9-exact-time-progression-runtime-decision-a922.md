# 2026-03-22 — Consultant Core Demo Salon Main Canary Turn 9 Exact-Time Progression Runtime Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-EXACT-TIME-PROGRESSION-RUNTIME-DECISION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-decision-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Promoted refreshed canary turn `9` from classification note to an explicit bounded runtime-family decision.
- Proved the issue is not judge-only drift: explicit exact-time fill (`11 утра`) under active `expected_reply_type=time` still leaves stale `booking_slots.datetime='в субботу'` and repeats `Подскажите, пожалуйста, точное время.`.
- Locked turn `12` as downstream oracle/proof debt only on the current artifact; no truthful turn-12 runtime implementation may start before the turn-9 rerun.
- Switched canon to this decision block and set the next non-negotiable move to bounded runtime implementation for exact-time progression.

## Evidence chain
### 1. Refreshed canary artifact
- Run: `/tmp/booking_quality/a922-check-booking-proof-r12/summary.json`
- Audit: `/tmp/booking_quality/a922-check-booking-proof-r12/manual_audit.json`
- Core outcome:
  - `infra_valid=true`
  - `turns_strict_failed=0`
  - `failure_family_count=0`
  - stale turn `10` blocker stays closed

### 2. Turn `9` runtime contradiction
- Artifact: `/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl`
- Turn `9` facts:
  - user: `Могу ли я изменить время на 11 утра?`
  - bot: `Понял, в субботу по услуге «Маникюр». Подскажите, пожалуйста, точное время.`
  - `expected_reply_type=time`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу'}`
  - `decision_meta.action=booking_prompt`
  - `decision_meta.source=llm_policy_core`
- Why that contradicts repo truth:
  - `truffles-api/tests/test_message_endpoint.py:9006-9066` requires exact-time merge plus stale expected-reply cleanup.
  - `truffles-api/tests/test_booking_dialog_scenarios_script.py:1582-1609` requires explicit time fill under `slot_constraint` to normalize to `reply_type=name`.
  - `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml:316-325` row `M13` requires canonical post-grounding state `expected_reply_type=name`.
  - `truffles-api/tests/test_message_endpoint.py:17864-18182` requires bounded handoff when exact-time reschedule lacks booking reference.
- Verdict:
  - turn `9` is a real runtime contract bug on the current runtime, not an oracle-only disagreement.

### 3. Turn `12` remains deferred oracle debt
- Artifact: `/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl`
- Turn `12` facts:
  - user: `Можно на 19:00?`
  - bot: `Отлично, время подходит. Как вас зовут?`
  - `hq1_classes=['handoff_miss']`
  - strict path still passes because current oracle fallback accepts `booking_prompt` while `booking_active=true`
- Decision:
  - do not tighten or implement turn `12` first
  - rerun only after the turn-9 runtime family is fixed

## Admissible implementation lane
- Future implementation must stay bounded to existing generic contracts:
  - exact-time merge under active expected-reply time collect
  - canonical progression to `expected_reply_type=name` when the slot is grounded
  - bounded handoff when the runtime resolves this family as reschedule-without-reference
- Explicitly not admissible:
  - phrase-hardcoded handling for `11 утра`
  - proof/oracle weakening as a substitute for runtime repair
  - reopening stale turn-10 drift as the active blocker
  - widening into frozen `decision.py`, `booking.py`, or `pending.py`

## Residual debt
- turn `9` runtime family is still unfixed
- turn `12` oracle/proof weakness remains pending post-fix rerun
- guarded `demo_salon/main` acceptance rerun is blocked until turn `9` lands
- multi-pack / open-world closure remains pending

## Next move
- `implement_consultant_core_demo_salon_turn9_exact_time_progression_runtime_family`
