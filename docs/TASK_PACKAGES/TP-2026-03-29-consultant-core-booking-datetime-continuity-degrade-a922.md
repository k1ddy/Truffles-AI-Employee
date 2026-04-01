# TP-2026-03-29-consultant-core-booking-datetime-continuity-degrade-a922

- Status: `completed`
- Owner: `Hands`
- Date: `2026-03-29`

## Название/цель
Построить exact live-path RCA для surfaced family `booking datetime continuity loss under policy-core degrade` из replay `r27`, доказать один слой классификации на уровне общего механизма `booking slot continuity across degrade / answer matching / commit handoff`, и только после этого предложить один bounded fix без scenario patching.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/REPORTS/2026-03-29-consultant-core-r27-human-semantic-audit-a922.md`
- `/tmp/booking_quality/a922-practical-proof-20260329-r27/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json}`

## Invariant
- Не лечить `dialog 2 / turns 4-5` как отдельный сценарий; фиксировать только repeatable failure family.
- Не объявлять второй semantic owner и не описывать архитектуру как broken-in-new-way без exact path evidence.
- Не добавлять phrase/regex branching под имена/услуги/даты.
- Не считать deterministic checks достаточным evidence; обязательны fresh replay + full human semantic audit.
- Failure family = evidence label; implementation unit = `broken invariant + shared mechanism`.

## Scope
- Только механизм `booking slot continuity across degrade / answer matching / commit handoff`.
- Exact path reconstruction для `r27` family: `input -> owner output -> validator/guard -> fallback/degrade -> final response -> trace/meta evidence -> layer classification`.
- Один bounded mechanism-level fix после доказанного RCA.

## Out of scope
- `live check-booking collect/fallback residue`
- `parking fact composition regression`
- wording-only edits
- oracle-only taxonomy disagreements

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-29-consultant-core-booking-datetime-continuity-degrade-a922.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/REPORTS/2026-03-29-consultant-core-r30-human-semantic-audit-a922.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`

## Work mode
- `RCA -> bounded implementation -> replay -> human audit`

## Surfaced family / mechanism-first frame
- Surfaced family label:
  - `booking datetime continuity loss under policy-core degrade`
- Broken invariant:
  - when a booking `datetime` reply is matched for an active booking, a degraded policy-core path must not reroute into an unrelated info reply; booking continuity must preserve the matched slot and advance the booking flow.
- Shared mechanism:
  - `booking slot continuity across degrade / answer matching / commit handoff`
- Why this surfaced family belongs to that mechanism:
  - the failure is not about wording or a specific service; it is a continuity break triggered by degraded policy-core handling after a matched slot.
- Open-world envelope expected to improve:
  - any booking flow where the user supplies a valid datetime but policy-core degrades should still advance booking (not collapse into info-class replies).

## One web search (mandatory before implementation)
- Query: `site:learn.microsoft.com bot framework dialog interruption return to original dialog continue dialog stack`
- Date/time: `2026-03-29 20:10 Asia/Almaty`
- Sources opened:
  - `https://learn.microsoft.com/en-us/azure/bot-service/bot-builder-concept-waterfall-dialogs?view=azure-bot-service-4.0`
- Source quality:
  - official vendor documentation (Microsoft Learn)
- Findings:
  - dialog stacks preserve context and return control to the original dialog after interrupts; step progression should continue rather than re-ask completed steps
- Decision:
  - `reuse/integrate`
  - keep Truffles booking continuity consistent with dialog-stack continuity: degrade/interrupt should not reset or overwrite already matched booking slots
- Rejected variants:
  - `patch only dialog 2 turn 4/5 wording` — violates no-scenario-patch canon
  - `special-case booking time phrases` — violates semantic-first / pack-agnostic contract

## Root cause (mandatory)
- Symptom:
  - `dialog 2 / turn 4`: user `Завтра в 15:00` -> bot answers `hours` instead of continuing booking
  - `dialog 2 / turn 5`: booking commit skips with `datetime_parse_failed`, then escalates
- Minimal reproduction:
  - replay `a922-practical-proof-20260329-r27`
  - `responses.jsonl` / `trace_bundle.jsonl`, `dialog_id=2`, `turn_index=4-5`
- Evidence:
  - `/tmp/booking_quality/a922-practical-proof-20260329-r27/responses.jsonl`
  - `/tmp/booking_quality/a922-practical-proof-20260329-r27/trace_bundle.jsonl`
  - `truffles-api/app/routers/webhook/decision.py` (policy-core degrade + booking interrupt selection)
  - `truffles-api/app/routers/webhook/booking.py` (booking interrupt info reply + expected-reply advancement)
  - `truffles-api/app/routers/webhook/booking.py` (appointment skip reason `datetime_parse_failed`)
- Five Whys:
  1. Why does the bot answer `hours` after a matched datetime? Because policy-core degrades and booking interrupt routes to info reply for `hours` based on info-class detection.
  2. Why is booking interrupt allowed after a matched slot? Because the matched expected reply clears the active `expected_reply_type`, and the degrade path no longer carries the matched booking-slot owner guard into booking interrupt selection.
  3. Why is booking continuity still advanced to `name` despite an info reply? Because booking interrupt updates booking_state and sets `expected_reply_type` from `booking_expected` even when responding with info.
  4. Why does booking commit skip with `datetime_parse_failed`? Because booking_state datetime is either absent/invalid when `_parse_booking_datetime` runs.
  5. Why is this a mechanism-level family? Any booking flow with matched datetime and policy-core degrade can be diverted into info-class replies, breaking slot continuity.
- Root cause statement:
  - after `question_contract` successfully matches a booking `datetime` answer and clears the current `expected_reply_type`, the degrade path loses the matched-owner slot guard and lets `booking_interrupt` treat the same turn as a strict non-service info interrupt (`hours`), while still advancing booking question state to `name`; this creates invisible booking continuity drift and later exposes `datetime_parse_failed` on commit
- Fix mechanism:
  - preserve the matched expected-reply owner slot across degrade-time booking-interrupt evaluation so that a turn which already satisfied booking `datetime` cannot be reclassified into an info interrupt just because `expected_reply_type` has already been cleared for the next step

## Exact path map
1. `input`
   - `dialog 2 / turn 4`: `turn_text="Завтра в 15:00"`
2. `owner input`
   - active booking state already exists from earlier turns with `service=Маникюр`, booking flow active, and `last_question=datetime`
   - `question_contract` matches the turn as booking `datetime` with `answer_value=15:00`
   - `matched_expected_reply_type=datetime`, `expected_reply_matched=true`, `expected_reply_shortcircuit=true`
3. `owner output`
   - policy-core does not produce a valid semantic payload on this turn
   - trace shows `policy_core_mode=degraded_fallback`
   - failure reason is `deadline_exceeded`
4. `validator / guard`
   - no downstream validator rewrites an owner payload because there is no valid owner payload to validate
   - the boundary keeps the matched booking slot in local state but clears the current `expected_reply_type` before degrade routing
5. `fallback / degrade`
   - because current `expected_reply_type` is now empty and `info_class_intents` includes `hours`, `_handle_booking_interrupt(...)` allows strict non-service interrupt handling
   - `_handle_booking_interrupt(...)` selects the `hours` info reply path instead of skipping interrupt evaluation for the already matched booking owner slot
   - the same path still advances booking expected reply to `name`
6. `final response`
   - outbound turn 4 becomes an `hours` info answer instead of continuing booking
   - `dialog 2 / turn 5` then consumes `Алина` as `name`, but booking commit later skips with `appointment_skip_reason=datetime_parse_failed` and escalates
7. `trace/meta evidence`
   - turn 4: `question_contract` matched the datetime answer before degrade
   - turn 4: `policy_core_mode=degraded_fallback`
   - turn 4: `booking_interrupt=info_reply` on `hours`
   - turn 5: commit path records `appointment_skip_reason=datetime_parse_failed`
8. `layer classification`
   - `boundary_fallback_error`

## Required RCA questions
1. Where exactly is the user datetime mention first represented in the live path?
   - in `question_contract` for `dialog 2 / turn 4`, where the active booking reply is matched as `datetime` and the normalized answer value is carried into matched booking slot state before policy-core degrade handling.
2. What exact structured owner output is produced for the failing turns?
   - turn 4: no valid structured owner payload is produced because policy-core ends in `deadline_exceeded` and runtime enters `degraded_fallback`.
   - turn 5: policy-core also fails to return a valid payload (`invalid_schema`), but by then the dialog has already been semantically broken by the turn-4 boundary diversion.
3. Does any validator/projector/guard mutate or demote that meaning?
   - yes: the boundary/fallback layer demotes the matched booking `datetime` turn into a strict non-service info interrupt because booking-interrupt evaluation no longer sees the matched expected-reply owner slot after `expected_reply_type` has been cleared.
4. If no downstream mutation exists, what owner contract/prompt/context gap explains the failure?
   - not applicable; the failure is downstream of the owner because the bad visible behavior is introduced by degrade-time boundary routing after a matched slot.
5. Is this a vocabulary issue, context issue, prompt issue, resolver issue, or pack grounding issue?
   - boundary continuity / degrade routing issue: the matched-slot owner guard is lost when moving from `question_contract` into booking-interrupt evaluation.

## Plan
1. Freeze RCA in this TP with exact artifacts and one allowed layer classification.
2. Add focused deterministic coverage for booking datetime continuity under degrade (after RCA).
3. Implement one bounded boundary continuity fix.
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
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/booking.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "active_time_slot_question_hours_phrase_keeps_booking_guidance or empty_response_matched_time_reply_stays_on_booking_path or deadline_exceeded_matched_time_reply_skips_info_interrupt_and_keeps_booking_path or collect_complete_booking_slots_continues_booking_flow"`
- `scripts/llm_quality_guarded.sh --mode replay --run-id a922-practical-proof-20260329-r30 --owner-file truffles-api/app/routers/webhook/decision.py --owner-file truffles-api/app/routers/webhook/booking.py --owner-file truffles-api/tests/test_message_endpoint.py --quick-check "python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/booking.py truffles-api/tests/test_message_endpoint.py" --quick-check "PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k \"active_time_slot_question_hours_phrase_keeps_booking_guidance or empty_response_matched_time_reply_stays_on_booking_path or deadline_exceeded_matched_time_reply_skips_info_interrupt_and_keeps_booking_path or collect_complete_booking_slots_continues_booking_flow\"" --allow-repeat-fingerprint --allow-pending-previous -- --base-url http://127.0.0.1:18086 --client-slug demo_salon --scenarios-file /tmp/booking_quality/a922-practical-proof-20260329-r25/scenarios.json --baseline-summary /tmp/booking_quality/a922-practical-proof-20260329-r27/summary.json --count 10 --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.0 --max-wait 0.15 --jid-mode unique --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --skip-outbox --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text "ок" --tool-hooks auto --tool-confirm-text "да" --tool-cancel-text "отмена" --tool-calendar-text "проверь запись" --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --history-max 20 --fail-on-thresholds --fail-on-regression --max-failures 20 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate warn --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --quality-lane dev --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260329-r30 --status done --strict-artifacts --analyst a922 --human-semantic-valid false --human-semantic-summary "r30 closes the booking datetime continuity family; replay stays product-red only because the live check-booking collect/fallback residue remains" --notes "Full turn-by-turn human semantic audit completed. Dialog 2 now preserves booking continuity on the matched datetime turn and the follow-up handoff remains product-acceptable; dialog 9 is still the only human-semantic fail family on current truth."`
- `git diff --check`

## Evidence
- this TP with exact RCA and one web search
- focused deterministic test output from `python3 -m py_compile ...` and the four-case `pytest -k ...` bundle
- fresh replay artifact bundle: `/tmp/booking_quality/a922-practical-proof-20260329-r30/{summary.json,brief.md,scenarios.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json,run_manifest.json}`
- human semantic report: `docs/REPORTS/2026-03-29-consultant-core-r30-human-semantic-audit-a922.md`
- `STATE.md` current-truth update

## Outcome
- Fresh replay `a922-practical-proof-20260329-r30` completed with `infra_valid=true`, `semantic_valid=false`.
- Full human semantic audit is complete: `dialogs 8 pass / 1 weak / 1 fail`, `turns 12 pass / 1 weak / 2 fail`.
- The original surfaced family for this TP is closed on replay:
  - `dialog 2 / turn 4` no longer diverts `Завтра в 15:00` into `hours`
  - the bot now asks for `name`, preserving booking continuity on the covered turn
- Practical/product closure remains open because replay `r30` leaves one human-semantic blocker family:
  - `live check-booking collect/fallback residue` (`dialog 9 / turns 1-2`)
- `parking fact composition regression` was not reproduced on `r30`, but this TP does not claim that family closed.
- A trace-visible residual remains on `dialog 2 / turn 5`:
  - `appointment_skip_reason=datetime_parse_failed` still appears before a transparent manager handoff
  - this is recorded as technical debt, not as the current practical blocker, because the visible turn is product-acceptable on `r30`
- Intermediate procedural runs:
  - `r28` was audited as a stale pre-restart runtime replay and is not used for closure evidence
  - `r29` was audited as a preflight-invalid run and is not used for closure evidence

## Rollback
- Revert the bounded boundary fix and accompanying deterministic test as one block if replay shows the continuity still regresses or booking commit degrades elsewhere.

## No-go
- No scenario/dialog-id patching.
- No service/name/datetime hardcodes in runtime core.
- No product-green claim without replay + full human semantic audit.
- No claim that owner error was proven here; this block is about boundary continuity under degrade.

## Риски/блокеры
- Degrade path fixes can expose deeper owner or timing inconsistencies in other booking stages.
- Fresh replay may improve this family but remain product-red due residual check-booking family.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `live check-booking collect/fallback residue`
- `parking fact composition regression` without closure claim
- non-blocking trace residue: `dialog 2 / turn 5` still records `appointment_skip_reason=datetime_parse_failed` before transparent handoff
### Why not in this block
- Canon/user scope allows one mechanism block at a time.
- The trace-visible commit residue no longer harms visible product behavior on the current truth, so it does not outrank the still-live check-booking family.
### Risk if deferred
- Replay can remain product-red after this mechanism fix.
- The trace-visible booking residue can resurface as a product blocker if later changes make the final handoff less transparent.
### Linked follow-up Task Package(s)
- next: check-booking temporal clue grounding / continuity family
- next: parking fact composition family
### Expiry/trigger to stop deferral
- Before any practical/product closure claim.

## Next-block contract (mandatory)
### Next block objective
- RCA the now-first surfaced blocker `live check-booking collect/fallback residue` from `r30` as the shared mechanism `booking-manage temporal clue grounding / follow-up continuity`.
### First deterministic check command
- `python3 - <<'PY'
import json
from pathlib import Path
p=Path('/tmp/booking_quality/a922-practical-proof-20260329-r30/summary.json')
print(json.loads(p.read_text())['metrics']['counts'])
PY`
### Blocked-by conditions
- a new TP and one web search for the check-booking mechanism have not yet been opened
- exact live-path RCA for `dialog 9 / turns 1-2` has not yet been written
### Owner role for closure
- `Brain/Architect`
