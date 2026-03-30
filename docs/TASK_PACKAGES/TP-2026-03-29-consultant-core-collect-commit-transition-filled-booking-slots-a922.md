# TP-2026-03-29-consultant-core-collect-commit-transition-filled-booking-slots-a922

- Status: `completed`
- Owner: `Hands`
- Date: `2026-03-29`

## Название/цель
Построить exact live-path RCA для surfaced family `downstream booking completion residue after filled name` из replay `r26c`, доказать один слой классификации на уровне общего механизма `collect->commit transition when required booking slots are already complete`, и только после этого внести один bounded fix без scenario patching.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/REPORTS/2026-03-29-consultant-core-r26c-human-semantic-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-29-consultant-core-owner-service-grounding-family-a922.md`
- `/tmp/booking_quality/a922-practical-proof-20260329-r26c/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json}`

## Invariant
- Не лечить `dialog 2 / turn 5` как отдельный сценарий; фиксировать только repeatable failure family.
- Не объявлять второй semantic owner и не описывать архитектуру как broken-in-new-way без exact path evidence.
- Не добавлять phrase/regex branching под имена/услуги.
- Не считать deterministic checks достаточным evidence; обязательны fresh replay + full human semantic audit.
- Failure family = evidence label; implementation unit = `broken invariant + shared mechanism`.

## Scope
- Только механизм `collect->commit transition when required booking slots are already complete`.
- Exact path reconstruction для `r26c` family: `input -> owner output -> validator/guard -> fallback/degrade -> final response -> trace/meta evidence -> layer classification`.
- Один bounded mechanism-level fix после доказанного RCA.

## Out of scope
- `live check-booking collect/fallback residue`
- `parking fact composition regression`
- wording-only edits
- oracle-only taxonomy disagreements

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-29-consultant-core-collect-commit-transition-filled-booking-slots-a922.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/REPORTS/2026-03-29-consultant-core-r27-human-semantic-audit-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Work mode
- `RCA -> bounded implementation -> replay -> human audit`

## Surfaced family / mechanism-first frame
- Surfaced family label:
  - `downstream booking completion residue after filled name`
- Broken invariant:
  - when `service + datetime + name` are all complete for an active booking without booking reference, runtime must not reopen a missing-slot collect prompt; it must continue the booking flow toward verification/commit.
- Shared mechanism:
  - `collect->commit transition when required booking slots are already complete`
- Why this surfaced family belongs to that mechanism:
  - the failing turn is not about a particular service, name, or dialog wording; it is specifically the transition after the final missing booking slot is filled.
- Open-world envelope expected to improve:
  - any booking flow where the last missing slot is filled on the current turn and owner leaves no open booking questions.

## One web search (mandatory before implementation)
- Query: `site:rasa.com/docs/rasa/forms submit action once all required slots filled official`
- Date/time: `2026-03-29 19:28 Asia/Almaty`
- Sources opened:
  - `https://rasa.com/docs/rasa/forms/`
- Source quality:
  - official vendor documentation
- Findings:
  - once all required slots are filled, the dialogue should transition into submit/next-step logic rather than reopening an already completed slot
  - slot-filling logic should preserve already collected values across the transition into the execution step
- Decision:
  - `reuse/integrate`
  - keep Truffles collect/runtime aligned with the same invariant: when required booking slots are complete, boundary/runtime must continue into booking execution instead of re-deriving a stale collect prompt
- Rejected variants:
  - `patch only dialog 2 turn 5 wording` — violates no-scenario-patch canon
  - `special-case user names or services` — violates semantic-first / pack-agnostic contract
  - `treat service-choice reprompt as acceptable weak behavior` — hides a product regression instead of fixing the transition mechanism

## Root cause (mandatory)
- Symptom:
  - `dialog 2 / turn 5`: user `Алина` after active booking with `service=маникюр` and `datetime=15:00` -> bot asks `На какую услугу хотите записаться? После этого сразу проверю свободное время.`
- Minimal reproduction:
  - replay `a922-practical-proof-20260329-r26c`
  - `responses.jsonl` / `trace_bundle.jsonl`, `dialog_id=2`, `turn_index=5`
- Evidence:
  - `/tmp/booking_quality/a922-practical-proof-20260329-r26c/responses.jsonl`
    - owner payload already carries `slots.service="маникюр"`, `slots.datetime="15:00"`, `slots.name="Алина"`
    - owner payload carries `action=collect`, `tool_action=collect`, `next_question=null`, `open_questions=[]`, `resolution_mode=direct`
    - owner reason: all slots are filled and runtime can proceed to calendar
  - `/tmp/booking_quality/a922-practical-proof-20260329-r26c/trace_bundle.jsonl`
    - `session_memory` before owner run: `pending_slots=["datetime","name"]`, `last_question_type=name`, `interaction_resume_slot=name`
    - `question_contract`: matched `name`, `answer_value=Алина`, `expected_reply_shortcircuit=true`
    - `llm_policy_plan_delta`: `plan_action=collect`, `final_action=collect`, `override_reason_codes=[]`
    - `policy_core_mode`: `policy_core`
    - `capability_contract`: `decision=live_calendar`, `contract_tool_action=calendar.list_slots`, while owner `tool_action=collect`
    - downstream `question_contract`: `decision=set`, `expected_reply_type=service_choice`
    - downstream `booking`: `decision=prompt`, `missing_slot=service`, `requested_slot=service`
  - `truffles-api/app/routers/webhook/decision.py:6280-6294`
    - `_select_plan_collect_slot(...)` falls back to `service` whenever `goal == "booking"` and owner leaves `next_question/open_questions` empty
  - `truffles-api/app/routers/webhook/decision.py:13778-13827`
    - after matched expected reply cleared current `expected_reply_type`, collect-slot derivation falls back through `_select_plan_collect_slot(...)`
  - `truffles-api/app/routers/webhook/decision.py:14037-14075`
    - the only existing complete-slot guard on `collect` currently routes into `semantic_owner_post_hoc_override_blocked`, not booking continuation, and it is bypassed here because `policy_collect_slot` was already backfilled to `service`
  - `truffles-api/app/routers/webhook/decision.py:22745-22924`
    - once `policy_collect_slot=service`, runtime persists `last_question=service`, sets `expected_reply_type=service_choice`, and emits the stale booking prompt
  - `truffles-api/app/routers/webhook/decision.py:1712-1915`
    - after `question_contract` matches the `name` answer, runtime clears `expected_reply_type` in context (`next_expected=None`) before policy-core collect-slot derivation, so downstream no longer sees the just-filled `name` stage as the active question
- Five Whys:
  1. Why does the bot reopen `service` after the user fills the final missing slot `name`? Because downstream booking prompt logic receives `policy_collect_slot=service`.
  2. Why does `policy_collect_slot` become `service`? Because current `expected_reply_type` is cleared after the matched `name` answer, owner leaves `next_question/open_questions` empty, and `_select_plan_collect_slot(... goal="booking")` falls back to `service`.
  3. Why is the meaning demoted downstream even though owner says all slots are filled? Because boundary/runtime does not have a success-path continuation for `collect + complete booking slots + no open questions`; it only knows how to reopen collect prompts.
  4. Why does the existing complete-slot guard not save this path? Because it only runs when `policy_collect_slot` stays empty; here the generic booking fallback already manufactured `service`, so the guard never fires.
  5. Why is this a mechanism-level family rather than a single dialog bug? Because any booking turn that fills the final required slot and produces owner `collect` with no `next_question/open_questions` can be demoted the same way once `expected_reply_type` has been cleared.
- Root cause statement:
  - The family is a `boundary_fallback_error`: after `question_contract` matches the final booking slot and clears the active expected-reply type, runtime re-derives `policy_collect_slot` from the generic booking fallback (`goal=booking -> service`) whenever owner returns `collect` with complete booking slots but no open questions, so boundary overwrites the completed `collect->commit` transition with a stale `service_choice` collect prompt.
- Fix mechanism:
  - add one bounded boundary-continuity path for `collect + complete booking slots + no open questions` so runtime continues the booking flow instead of backfilling a stale collect slot
  - add focused deterministic coverage proving that a final-slot fill on active booking commits to booking flow rather than reopening `service`

## Exact path map
1. `input`
   - `dialog 2 / turn 5`: `turn_text="Алина"`
2. `owner input`
   - live context already has active booking with `service=Маникюр`, `datetime=15:00`, `last_question=name`
   - `question_contract` matches the answer as `name`
3. `owner output`
   - `action=collect`
   - `tool_action=collect`
   - `slots={service="маникюр", datetime="15:00", name="Алина"}`
   - `next_question=null`
   - `open_questions=[]`
   - `resolution_mode=direct`
   - `reason=all slots filled, can proceed to calendar`
4. `validator / guard`
   - owner payload validates
   - `plan_action == final_action == collect`
   - no `policy_core_guard`, no degraded fallback, no semantic override
5. `fallback / degrade`
   - `question_contract` had already cleared `expected_reply_type` after the matched answer
   - collect-slot derivation falls back through `_select_plan_collect_slot(... goal="booking") -> service`
   - existing complete-slot guard is skipped because `policy_collect_slot` is no longer empty
6. `final response`
   - runtime sets `expected_reply_type=service_choice`
   - runtime emits booking prompt with `missing_slot=service`
   - outbound text: `На какую услугу хотите записаться? После этого сразу проверю свободное время.`
7. `trace/meta evidence`
   - `decision_meta.action=booking_prompt`
   - `decision_meta.source=llm_policy_core`
   - `decision_meta.expected_reply_type=service_choice`
   - `decision_trace.stage=booking`, `missing_slot=service`, `requested_slot=service`
8. `layer classification`
   - `boundary_fallback_error`

## Required RCA questions
1. Where exactly is the user service mention first represented in the live path?
   - in active booking state carried into turn 5 (`booking.service=Маникюр`) and again in owner payload `slots.service="маникюр"`.
2. What exact structured owner output is produced for the failing turn?
   - `action=collect`, `tool_action=collect`, `slots.service/datetime/name all filled`, `next_question=null`, `open_questions=[]`, `resolution_mode=direct`.
3. Does any validator/projector/guard mutate or demote that meaning?
   - yes: boundary collect-slot fallback demotes it by manufacturing `policy_collect_slot=service`, which then resets question contract and final prompt.
4. If no downstream mutation exists, what owner contract/prompt/context gap explains the failure?
   - not applicable; downstream mutation does exist.
5. Is this a vocabulary issue, context issue, prompt issue, resolver issue, or pack grounding issue?
   - runtime/boundary continuation issue: stale collect-slot fallback after expected-reply shortcircuit clears the current booking question.

## Plan
1. Freeze the RCA in this TP with exact artifacts and one allowed layer classification.
2. Add focused deterministic coverage for `collect + complete booking slots + no open questions` on name-stage booking continuation.
3. Implement one bounded boundary continuity fix in `decision.py`.
4. Run focused deterministic checks.
5. Run fresh replay and full human semantic audit.
6. Update `STATE.md` / `STRUCTURE.md` with new truth and residual families.

## DoD
- Exact mechanism path is written with trace/meta evidence.
- One allowed layer classification is proven.
- Fix is mechanism-level and bounded.
- Focused deterministic checks are green.
- Fresh replay is run and a fresh full human semantic audit is completed.
- `STATE.md` records the new practical truth without overclaim.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "collect_complete_booking_slots_continues_booking_flow"`
- `scripts/llm_quality_guarded.sh --mode replay --run-id a922-practical-proof-20260329-r27 --owner-file truffles-api/app/routers/webhook/decision.py --owner-file truffles-api/tests/test_message_endpoint.py --quick-check "python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py" --quick-check "PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k collect_complete_booking_slots_continues_booking_flow" --allow-pending-previous -- --base-url http://127.0.0.1:18086 --client-slug demo_salon --scenarios-file /tmp/booking_quality/a922-practical-proof-20260329-r25/scenarios.json --baseline-summary /tmp/booking_quality/a922-practical-proof-20260329-r26c/summary.json --count 10 --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.0 --max-wait 0.15 --jid-mode unique --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --skip-outbox --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text "ок" --tool-hooks auto --tool-confirm-text "да" --tool-cancel-text "отмена" --tool-calendar-text "проверь запись" --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --history-max 20 --fail-on-thresholds --fail-on-regression --max-failures 20 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate warn --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --quality-lane dev --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260329-r27 --status done --strict-artifacts --analyst a922 --human-semantic-valid false --human-semantic-summary "fill after final booking slot no longer reopens service, but residual practical blockers remain if replay still fails elsewhere"`
- `git diff --check`

## Evidence
- this TP with exact RCA and one web search
- focused deterministic test output from `python3 -m py_compile ...` and `pytest -q truffles-api/tests/test_message_endpoint.py -k ...`
- fresh replay artifact bundle: `/tmp/booking_quality/a922-practical-proof-20260329-r27/{summary.json,brief.md,scenarios.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json,run_manifest.json}`
- human semantic report: `docs/REPORTS/2026-03-29-consultant-core-r27-human-semantic-audit-a922.md`
- `STATE.md` current-truth update

## Outcome
- Fresh replay `a922-practical-proof-20260329-r27` completed with `infra_valid=true`, `semantic_valid=false`.
- Full human semantic audit is complete: `dialogs 7 pass / 1 weak / 2 fail`, `turns 10 pass / 1 weak / 4 fail`.
- The original surfaced family for this TP is closed on replay:
  - `dialog 2 / turn 5` no longer reopens `service`
  - the stale `service_choice` collect residue is absent
- Practical/product closure remains open because replay `r27` surfaced a new first blocker:
  - `booking datetime continuity loss under policy-core degrade` (`dialog 2 / turns 4-5`)
- `live check-booking collect/fallback residue` remains open.
- `parking fact composition regression` was not reproduced on `r27`, but this TP does not claim that family closed.

## Rollback
- Revert the bounded boundary fix and accompanying deterministic test as one block if replay shows the transition still regresses or booking commit degrades elsewhere.

## No-go
- No scenario/dialog-id patching.
- No service/name hardcodes in runtime core.
- No product-green claim without replay + full human semantic audit.
- No claim that owner error was proven here; this block is about boundary continuation only.

## Риски/блокеры
- A bounded continuity fix could expose a deeper owner inconsistency if owner starts emitting conflicting complete-slot outputs on other turns.
- Fresh replay may improve this family but still remain product-red due residual check-booking / parking families.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `booking datetime continuity loss under policy-core degrade`
- `live check-booking collect/fallback residue`
- `parking fact composition regression` without closure claim
### Why not in this block
- Canon/user scope allows one mechanism block at a time.
### Risk if deferred
- Replay can remain product-red after this mechanism fix.
### Linked follow-up Task Package(s)
- next: booking datetime continuity loss under policy-core degrade
- next: check-booking fallback residue family
- next: parking fact composition family
### Expiry/trigger to stop deferral
- Before any practical/product closure claim.

## Next-block contract (mandatory)
### Next block objective
- RCA the new first surfaced blocker `booking datetime continuity loss under policy-core degrade` from `dialog 2 / turns 4-5` as a mechanism-level family, then return to `check-booking` and `parking` only in the order fresh truth supports.
### First deterministic check command
- `python3 - <<'PY'
import json
from pathlib import Path
p=Path('/tmp/booking_quality/a922-practical-proof-20260329-r27/summary.json')
print(json.loads(p.read_text())['metrics']['counts'])
PY`
### Blocked-by conditions
- fresh replay/audit for this mechanism not yet completed
- residual-family ordering may change after the replay
### Owner role for closure
- `Brain/Architect`
