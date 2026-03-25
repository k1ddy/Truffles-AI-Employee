# 2026-03-22 — Consultant Core Demo Salon Main Canary Turn 13 Name Progression Runtime Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN13-NAME-PROGRESSION-RUNTIME-DECISION-A922`
- `TP`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-decision-a922.md`
- `Worktree`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`

## Summary
- Promoted fresh canary turn `13` from replay finding to an explicit bounded runtime-family decision.
- Proved on the refreshed-runtime artifact that turn `9` is repaired and turn `12` now satisfies the handoff contract.
- Locked turn `13` (`Меня зовут Амина.`) as the next real runtime contract bug because the runtime keeps `expected_reply_type=name`, re-asks `Как вас зовут?`, and records `booking_slot_stall` instead of consuming the provided name.
- Switched canon to this decision block and set the next non-negotiable move to bounded runtime implementation for turn-13 name progression.

## Evidence chain
### 1. Fresh replay truth
- Run: `/tmp/booking_quality/a922-check-booking-proof-r14/summary.json`
- Audit: `/tmp/booking_quality/a922-check-booking-proof-r14/manual_audit.json`
- Core outcome:
  - `infra_valid=true`
  - `semantic_valid=false`
  - `stop_reason=max_failures_reached:1`
  - `run_integrity_reasons=['run_completion_gap']`
  - failure family collapses to turn `13` only

### 2. Turn `9` is repaired on the refreshed runtime
- Artifact: `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl`
- Turn `9` facts:
  - user: `Могу ли я изменить время на 11 утра?`
  - bot: `Отлично, время подходит. Как вас зовут?`
  - `expected_reply_type=name`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 11:00'}`
  - `decision_meta.expected_reply_time_progression_override=true`
- Verdict:
  - the bounded turn-9 exact-time runtime family is now closed on the fresh replay path

### 3. Turn `12` is no longer the active blocker
- Artifact: `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl`
- Turn `12` facts:
  - user: `Можно на 19:00?`
  - bot: `Передал менеджеру...`
  - `conversation_state=pending`
  - `decision_meta.tool_action=handoff`
  - `evaluation.ok=true`
- Verdict:
  - the old turn-12 runtime-vs-oracle debt does not survive on the fresh artifact

### 4. Turn `13` is the surviving runtime contradiction
- Artifact: `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl`
- Turn `13` facts:
  - user: `Меня зовут Амина.`
  - bot: `Отлично, время подходит. Как вас зовут?`
  - `expected_reply_type=name`
  - `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 11:00'}`
  - `evaluation.reasons=['booking_slot_stall']`
  - `evaluation.strict_reasons=['booking_slot_stall', 'judge_fail']`
  - `hq1_classes=['booking_flow_break']`
- Why that contradicts repo truth:
  - `truffles-api/tests/test_reasoning_core.py:8689-8788` requires complete-name progression to booking completion under active `expected_reply_type=name`.
  - `truffles-api/tests/test_message_endpoint.py:16162-16327` requires terminal booking success to clear follow-up expected-reply state.
  - `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml:903-943` forbids collapsing active `name` resume back into generic `booking_prompt` churn.
- Verdict:
  - turn `13` is a real runtime contract bug on the fresh runtime, not a replay-freshness or turn-12 oracle problem.

### 5. Advisory proof debt that stays out of the runtime lane
- `/tmp/booking_quality/a922-check-booking-proof-r14/manual_audit.json` reports `judge_alignment=conflicted`, `winner=contract`, `conflict_count=3`.
- Conflicted judge-only turns on this artifact are `6`, `9`, and `11`.
- Decision:
  - keep these as proof/oracle debt only; do not mix them into the turn-13 runtime implementation lane.

## Admissible implementation lane
- Future implementation must stay bounded to existing generic contracts:
  - consume explicit customer-name fill under active `expected_reply_type=name`
  - progress into booking completion or bounded degrade/handoff with observable reason codes
  - clear or update expected-reply state contractually after the slot is consumed
- Explicitly not admissible:
  - phrase-hardcoded handling for `Меня зовут ...`
  - proof/oracle weakening as a substitute for runtime repair
  - reopening turn `9` or turn `12` as active blockers on stale evidence
  - widening into frozen `decision.py`, `booking.py`, or `pending.py`

## Residual debt
- turn `13` runtime family is still unfixed
- judge/oracle conflicts on turns `6`, `9`, and `11` remain deferred proof debt
- guarded `demo_salon/main` acceptance rerun is blocked until turn `13` lands
- multi-pack / open-world closure remains pending

## Next move
- `implement_consultant_core_demo_salon_turn13_name_progression_runtime_family`
