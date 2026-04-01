# TP-2026-03-30-consultant-core-booking-manage-temporal-clue-grounding-follow-up-continuity-a922

- Status: `materially_complete_in_repo`
- Owner: `Hands`
- Date: `2026-03-30`

## Название/цель
Зафиксировать exact live-path RCA для surfaced family `booking-manage temporal clue grounding / follow-up continuity` из fresh replay `r36g`, доказать один механизм и один слой ответственности, и не допустить нового symptom patching по `dialog 9 / turns 1-2`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/REPORTS/2026-03-30-consultant-core-r36g-human-semantic-audit-a922.md`
- `/tmp/booking_quality/a922-practical-proof-20260330-r36g/{summary.json,brief.md,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit_workspace.md,family_registry.json,judge_conflicts.jsonl,run_manifest.json}`
- `/tmp/booking_quality/a922-practical-proof-20260330-r36g/trends-r36c-vs-r36g.{json,md}`

## Invariant
- Не лечить `dialog 9 / turn 1` или `dialog 9 / turn 2` как отдельные сценарии; implementation unit = только shared mechanism.
- Не добавлять domain-branching вида `if check_booking ...` в runtime core.
- Не трогать runtime code в этом блоке до завершения exact path map и layer classification.
- Не смешивать этот блок с `oracle contract / taxonomy alignment` и `replay harness / evaluator isolation` вокруг `dialog 2 / turns 4-5`.
- Не re-open `consult/media cue continuity`; `r36g` уже доказал, что это больше не первый live blocker.
- Не ослаблять `r36g` truth; никаких claims о product/program closure.

## Scope
- Только механизм `booking-manage temporal clue grounding / follow-up continuity`.
- Exact path reconstruction для `dialog 9 / turns 1-2` из `r36g`.
- Доказать:
  - что semantic owner уже видит temporal clue (`temporal_scope=weekday`),
  - где именно теряется narrowed follow-up contract,
  - почему итоговый reply расширяется обратно до generic `дата и время или имя`,
  - почему follow-up continuity не сужается на втором turn.

## Out of scope
- любые code changes в `truffles-api/app/core/*`, `truffles-api/app/services/*`, `truffles-api/app/routers/webhook/*`
- `oracle contract / taxonomy alignment` for `dialog 2 / turn 4` as a standalone implementation unit
- `replay harness / evaluator isolation` for `dialog 2 / turn 5`
- any new replay until this RCA is frozen and accepted

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-booking-manage-temporal-clue-grounding-follow-up-continuity-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-r36g-human-semantic-audit-a922.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `STATE.md`
- `STRUCTURE.md`

## Work mode
- `RCA only -> no code in this block`

## Surfaced family / mechanism-first frame
- Surfaced family labels:
  - `oracle::booking-manage temporal clue grounding / follow-up continuity::expected_reply_mismatch,judge_fail,missed_question`
  - `oracle::booking-manage temporal clue grounding / follow-up continuity::expected_action_mismatch,expected_meta_mismatch,judge_eval_conflict`
- Broken invariant:
  - when the user already grounds an existing-booking lookup with a temporal clue (`на четверг`), runtime may not widen the missing-reference prompt back to generic `дата и время или имя`; it must preserve the narrowed follow-up contract and reuse it on the next turn.
- Shared mechanism:
  - `booking-manage temporal clue grounding / follow-up continuity`
- Why this surfaced family belongs to that mechanism:
  - both turns keep the same generic verification prompt even though the semantic frame already grounds `temporal_scope=weekday` and the canonical pending-question contract says `next_question=name`.
- Open-world envelope expected to improve:
  - any existing-booking lookup or confirmation turn where the customer gives a temporal clue before the booking reference or customer referent is fully grounded.

## Root cause (mandatory)
- Symptom:
  - `dialog 9 / turn 1`: `Проверьте мою запись на четверг.` -> bot: `Чтобы проверить запись, подскажите примерную дату и время или имя, на которое оформляли запись.`
  - `dialog 9 / turn 2`: `Подтвердите, пожалуйста, мою запись на четверг.` -> bot repeats the same generic prompt.
- Minimal reproduction:
  - replay `a922-practical-proof-20260330-r36g`
  - `responses.jsonl` / `trace_bundle.jsonl`, `dialog_id=9`, `turn_index in {1,2}`
- Evidence:
  - `/tmp/booking_quality/a922-practical-proof-20260330-r36g/responses.jsonl`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r36g/trace_bundle.jsonl`
  - `truffles-api/app/services/policy_prompt_snapshot_service.py`
  - `truffles-api/app/services/intent_service.py`
  - `truffles-api/app/core/turn_executor.py`
- Five Whys:
  1. Why does the visible path keep asking for `дату и время или имя`? Because `turn_executor` emits the generic `booking_verification_prompt` for `calendar.get_booking` lookup fallback.
  2. Why does the fact path enter that prompt? Because the `calendar.get_booking` binding executes with no grounded booking reference or customer referent and returns the synthetic verification prompt path (`tool_decision=not_found`, `resolution_reason=booking_verification_prompt`).
  3. Why is that still too broad when the user already said `на четверг`? Because the semantic frame already narrows the turn to `temporal_scope=weekday`, but the final prompt composition ignores that narrowed continuity and widens the missing-reference prompt back to generic `дата и время или имя`.
  4. Why does the second turn not narrow the follow-up? Because the canonical pending-question contract remains `next_question=name`, yet the same prompt path is re-emitted unchanged on the next turn instead of consuming the already-grounded temporal clue.
  5. Why is this mechanism-wide? Because any booking-manage lookup with partial temporal grounding and missing customer/booking reference can fall through the same `calendar.get_booking -> booking_verification_prompt` path.
- Root cause statement:
  - the current governed path preserves temporal grounding in the semantic frame and canonical pending-question contract, but the `calendar.get_booking` fallback prompt composition widens the missing-reference request back to generic `дата и время или имя`, so follow-up continuity never narrows on the visible path.
- Fix mechanism:
  - not in this block; the future bounded implementation must keep the owner-grounded `temporal_scope` and canonical `next_question=name` intact through fact composition / final response so the verification prompt does not widen beyond the governed contract.

## Exact path map
1. `input`
   - `dialog 9 / turn 1`: `Проверьте мою запись на четверг.`
   - `dialog 9 / turn 2`: `Подтвердите, пожалуйста, мою запись на четверг.`
2. `owner output`
   - `intent=check_booking`
   - `action=fact`
   - `tool_action=calendar.get_booking`
   - `reason=calendar_get_booking_collect_reference`
   - `temporal_scope=weekday`
   - `next_question=name`
   - `open_questions=[name]`
   - `current_goal=check_booking`
3. `validator / guard`
   - `intent_service` keeps the booking-manage fact path and strips stale booking-create collect fields for `next_question=name`
   - no boundary deny/degrade path fires
4. `binding / fact path`
   - `turn_executor` builds the fact-chain for `calendar.get_booking`
   - `binding_transition.resolved_args` remains `{}` because there is no grounded booking reference or customer referent
5. `fact composition`
   - `turn_executor` enters the `booking_verification_prompt` branch for `calendar.get_booking`
   - that branch returns the fixed generic text `Чтобы проверить запись, подскажите примерную дату и время или имя, на которое оформляли запись.`
   - this widens beyond the canonical pending-question contract, which still says `next_question=name`
6. `final response / continuity`
   - visible reply is the same generic verification prompt on both turns
   - `state_transition.pending_question_contract` remains `next_question=name`, `expected_reply_type=name`
   - the second turn replays the same prompt instead of narrowing the follow-up
7. `trace/meta evidence`
   - `semantic_frame.constraints.temporal_scope=weekday`
   - `semantic_frame.continuation.next_question=name`
   - `runtime_trace_contract.state_transition.pending_question_contract.next_question=name`
   - `binding_transition.resolved_args={}`
   - `fact_result.resolution_reason=booking_verification_prompt`
   - `decision_meta.tool_decision=not_found`

## Layer classification
- `fact_composition_error`
- rationale:
  - the semantic owner already narrows the turn to `temporal_scope=weekday` and `next_question=name`
  - no boundary/degrade branch rewrites the turn
  - the widening occurs when the fact path composes the generic booking verification prompt and ignores the narrower pending-question contract

## Required RCA questions
1. Should `calendar.get_booking` fallback prompt composition consume `temporal_scope` and `pending_question_contract.next_question` directly, or should the narrowing happen earlier in the fact plan/binding layer?
2. What exact contract should distinguish `ask for customer name only` from `ask for date/time or name` in booking-manage verification?
3. How should the second follow-up turn preserve or narrow the missing-reference contract without turning `check_booking` into a booking-create collect path?
4. Which part of the current prompt/oracle disagreement around dialog `2 / turns 4-5` is true residual debt and which part is only evaluator noise after this mechanism is isolated?

## Plan
1. Freeze `r36g` as the active practical truth in canon/docs.
2. Freeze this mechanism-first RCA in a dedicated TP.
3. Keep implementation blocked until Brain/Architect accept the exact path and layer classification.
4. Open one bounded implementation TP only after RCA closure.

## DoD
- Exact live path is written and tied to specific artifacts/code.
- One broken invariant and one shared mechanism are named explicitly.
- One layer classification is chosen and defended.
- No runtime code is changed in this block.
- Canon/docs point to `r36g` and to this RCA block as the next admissible move.

## Checks
- `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-practical-proof-20260330-r36g/trace_bundle.jsonl').read_text().splitlines()]
row=next(item for item in rows if item['dialog_id']==9 and item['turn_index']==1)
meta=row['decision_meta']
trace=meta['decision_trace']
assert meta['intent']=='check_booking'
assert meta['tool_action']=='calendar.get_booking'
assert trace['semantic_frame']['constraints']['temporal_scope']=='weekday'
assert trace['semantic_frame']['continuation']['next_question']=='name'
assert trace['runtime_trace_contract']['state_transition']['pending_question_contract']['next_question']=='name'
assert trace['runtime_trace_contract']['binding_transition']['resolved_args']=={}
assert meta['tool_decision']=='not_found'
print('booking_manage_temporal_clue_rca_seed_ok')
PY`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-30-consultant-core-r36g-human-semantic-audit-a922.md`
- `/tmp/booking_quality/a922-practical-proof-20260330-r36g/{summary.json,brief.md,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit_workspace.md,family_registry.json,judge_conflicts.jsonl,run_manifest.json}`
- `/tmp/booking_quality/a922-practical-proof-20260330-r36g/trends-r36c-vs-r36g.{json,md}`
- updated canon/docs pointing to `r36g`

## Rollback
- Revert the doc-only truth sync and RCA TP as one block if the exact path or layer classification is disproven.

## No-go
- No runtime code changes.
- No dialog-level or wording-level patching.
- No blending with `oracle contract / taxonomy alignment` or evaluator cleanup before this RCA is accepted.
- No claim that `consult/media cue continuity` is still the first live blocker on current head.

## Риски/блокеры
- The visible failure sits on the owner-to-fact-composition seam; a careless future fix could widen into booking-create collect logic or domain hardcodes.
- The scenario/oracle residue around `dialog 2 / turns 4-5` can obscure the primary blocker if it is not kept separate.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- bounded runtime implementation for `booking-manage temporal clue grounding / follow-up continuity`
- `oracle contract / taxonomy alignment`
- `replay harness / evaluator isolation`
- broader architecture debt outside the touched canary envelope

### Why not in this block
- User/canon scope now demands one shared mechanism at a time after `r36g`, and this block is RCA-only.

### Risk if deferred
- Product closure remains blocked, and future work can drift back into scenario patching if the next implementation unit is not bounded to the exact path above.

### Linked follow-up Task Package(s)
- next: bounded implementation TP for `booking-manage temporal clue grounding / follow-up continuity`
- queued after that: RCA/cleanup decision for `oracle contract / taxonomy alignment`

### Expiry/trigger to stop deferral
- Before any runtime code is changed for the booking-manage family.

## Next-block contract (mandatory)
### Next block objective
- Open one bounded implementation TP that preserves owner-grounded temporal scope and canonical `next_question=name` through the booking verification fact path without widening the final prompt back to `дата и время или имя`.

### First deterministic check command
- `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-practical-proof-20260330-r36g/responses.jsonl').read_text().splitlines()]
row=next(item for item in rows if item['dialog_id']==9 and item['turn_index']==1)
print(row['turn_text'])
print(row['inline_response_text'])
print(row['decision_meta']['decision_trace']['semantic_frame']['constraints'])
print(row['decision_meta']['decision_trace']['semantic_frame']['continuation'])
PY`

### Blocked-by conditions
- Brain/Architect have not yet accepted the exact path and chosen layer classification.

### Owner role for closure
- `Brain/Architect`
