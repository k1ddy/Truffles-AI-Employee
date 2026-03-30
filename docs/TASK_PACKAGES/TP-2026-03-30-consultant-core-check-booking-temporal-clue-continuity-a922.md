# TP-2026-03-30-consultant-core-check-booking-temporal-clue-continuity-a922

- Status: `done`
- Owner: `Hands`
- Date: `2026-03-30`

## Название/цель
Построить exact live-path RCA для surfaced family `live check-booking collect/fallback residue` из replay `r30`, доказать один слой классификации на уровне общего механизма `booking-manage temporal clue grounding / follow-up continuity`, и только после этого предложить один bounded fix без scenario patching.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/REPORTS/2026-03-29-consultant-core-r30-human-semantic-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-29-consultant-core-check-booking-temporal-grounding-followup-a922.md`
- `/tmp/booking_quality/a922-practical-proof-20260329-r30/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json}`

## Invariant
- Не лечить `dialog 9 / turns 1-2` как отдельный сценарий; фиксировать только repeatable failure family.
- Не объявлять второй semantic owner и не описывать архитектуру как broken-in-new-way без exact path evidence.
- Не добавлять phrase/regex branching под `четверг` или другие weekdays.
- Не считать deterministic checks достаточным evidence; обязательны fresh replay + full human semantic audit.
- Failure family = evidence label; implementation unit = `broken invariant + shared mechanism`.

## Scope
- Только механизм `booking-manage temporal clue grounding / follow-up continuity`.
- Exact path reconstruction для `r30` family: `input -> owner output -> validator/guard -> fallback/degrade -> final response -> trace/meta evidence -> layer classification`.
- Один bounded mechanism-level fix после доказанного RCA.

## Out of scope
- `parking fact composition regression`
- trace-visible `dialog 2 / turn 5` `datetime_parse_failed` residue
- wording-only edits
- oracle-only taxonomy disagreements

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-check-booking-temporal-clue-continuity-a922.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `docs/REPORTS/2026-03-30-consultant-core-r32g-human-semantic-audit-a922.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `STATE.md`
- `STRUCTURE.md`

## Work mode
- `RCA -> bounded implementation -> replay -> human audit`

## Surfaced family / mechanism-first frame
- Surfaced family label:
  - `live check-booking collect/fallback residue`
- Broken invariant:
  - when a booking-verification turn already contains a temporal clue, runtime must preserve that grounding and collect only the missing identity/reference slot instead of re-asking temporal information.
- Shared mechanism:
  - `booking-manage temporal clue grounding / follow-up continuity`
- Why this surfaced family belongs to that mechanism:
  - the failure is not about one weekday wording; it is a repeated verification-collection continuity miss where temporal grounding exists but the follow-up collect prompt ignores it.
- Open-world envelope expected to improve:
  - any check/confirm booking turn with a grounded relative/weekday temporal clue but missing identity/reference.

## One web search (mandatory before implementation)
- Query: `site:rasa.com/docs/rasa/forms pre-filled slots next required slot official`
- Date/time: `2026-03-30 00:03 Asia/Almaty`
- Sources opened:
  - `https://legacy-docs-oss.rasa.com/docs/rasa/forms/`
- Source quality:
  - official vendor documentation
- Findings:
  - an active collection flow should ask for the next empty required slot rather than re-asking an already grounded slot
  - dynamic form behavior should preserve already collected slot information across interruptions/follow-ups
- Decision:
  - `reuse/integrate`
  - keep booking-verification follow-up aligned with the same invariant: when temporal grounding already exists, collect only the missing identity/reference slot and preserve it across follow-up turns
- Rejected variants:
  - `teach weekday-specific regex in the default runtime path` — violates semantic-first contract
  - `weaken the human audit verdict on dialog 9` — hides a live product blocker instead of fixing the mechanism

## Root cause (mandatory)
- Symptom:
  - `dialog 9 / turn 1`: `Проверьте мою запись на четверг.` -> bot asks for `номер телефона и примерную дату/время`
  - `dialog 9 / turn 2`: `Подтвердите, пожалуйста, мою запись на четверг.` -> bot repeats the same generic prompt
- Minimal reproduction:
  - replay `a922-practical-proof-20260329-r30`
  - `responses.jsonl` / `trace_bundle.jsonl`, `dialog_id=9`, `turn_index=1-2`
- Evidence:
  - `/tmp/booking_quality/a922-practical-proof-20260329-r30/responses.jsonl`
  - `/tmp/booking_quality/a922-practical-proof-20260329-r30/trace_bundle.jsonl`
  - `truffles-api/app/routers/webhook/decision.py:5170`
  - `truffles-api/app/routers/webhook/decision.py:12782`
  - `truffles-api/app/routers/webhook/decision.py:14904`
  - `truffles-api/app/routers/webhook/decision.py:15487`
- Five Whys:
  1. Why does turn 1 re-ask approximate date/time? Because the degraded booking-verification collect prompt emits the generic `MSG_BOOKING_ASK_REFERENCE` text.
  2. Why does the degraded path emit the generic prompt even though owner already marks `temporal_scope=weekday`? Because `_send_policy_validation_collect_prompt(...)` hardcodes `MSG_BOOKING_ASK_REFERENCE` for booking-verification reference collection instead of routing through `_select_booking_verification_collect_prompt(...)`.
  3. Why does turn 2 repeat the same generic prompt? Because the second turn reproduces the same owner output (`temporal_scope=weekday`, `next_question=datetime`) and the same validation guard path re-emits the same hardcoded generic prompt.
  4. Why is that wrong? Because the temporal clue has already been grounded at the owner layer (`temporal_scope=weekday`), so the only missing slot is identity/reference.
  5. Why is this a mechanism-level family? Any booking-verification turn with coarse temporal grounding but missing identity/reference can fall into the same generic prompt repetition.
- Root cause statement:
  - boundary booking-verification collect/fallback prompt selection does not preserve owner-grounded temporal clues (`temporal_scope=weekday`) across degraded validation and pending follow-up paths, so runtime re-asks temporal information via the generic reference prompt instead of collecting only the missing identity/reference slot
- Fix mechanism:
  - route booking-verification degraded/pending collect prompts through one temporal-grounding-aware selector that consumes the owner temporal scope and preserves it across the follow-up boundary

## Exact path map
1. `input`
   - `dialog 9 / turn 1`: `turn_text="Проверьте мою запись на четверг."`
   - `dialog 9 / turn 2`: `turn_text="Подтвердите, пожалуйста, мою запись на четверг."`
2. `owner output`
   - both turns: valid owner payload with `intent=booking`, `action=collect`, `tool_action=collect`, `capability=booking_manage`, `next_question=datetime`, `open_questions=["datetime"]`, `temporal_scope=weekday`, `resolution_mode=clarify_missing_time`
3. `validator / guard`
   - both turns: `validation_error=collect_slot_order_invalid`
   - both turns: `policy_core_mode=degraded_fallback`
4. `fallback / degrade`
   - both turns: `_send_policy_validation_collect_prompt(...)` identifies booking-verification reference collect and sets `expected_reply_type=name`, but emits hardcoded `MSG_BOOKING_ASK_REFERENCE` instead of the temporal-grounding-aware selector
5. `final response`
   - both turns: `action=check_booking_prompt`, `source=booking_verification`, visible text still asks for `номер телефона и примерную дату/время`
6. `trace/meta evidence`
   - turn 1: `llm_policy_core.temporal_scope=weekday`, `policy_core_guard.decision=collect_slot_order_collect_prompt`, `question_contract.reason=calendar_get_booking_collect_reference`, `expected_reply_type=name`
   - turn 2: same owner shape, same guard decision, same final generic prompt
7. `layer classification`
   - `boundary_fallback_error`

## Required RCA questions
1. Where exactly is the user temporal clue first represented in the live path?
   - in the owner output for both failing turns as `temporal_scope=weekday`; runtime does not receive a filled `datetime` slot value, but it does receive explicit owner evidence that temporal grounding exists.
2. What exact structured owner output is produced for the failing turns?
   - `intent=booking`, `action=collect`, `tool_action=collect`, `capability=booking_manage`, `next_question=datetime`, `open_questions=["datetime"]`, `temporal_scope=weekday`, `resolution_mode=clarify_missing_time`, `validation_error=collect_slot_order_invalid`.
3. Does any validator/projector/guard mutate or demote that meaning?
   - yes: the boundary degraded/pending prompt composition demotes the owner-grounded temporal clue into a generic `номер телефона и примерную дату/время` prompt.
4. If no downstream mutation exists, what owner contract/prompt/context gap explains the failure?
   - not applicable; downstream mutation exists and is user-visible.
5. Is this a vocabulary issue, context issue, prompt issue, resolver issue, or pack grounding issue?
   - boundary prompt-selection / follow-up continuity issue.

## Plan
1. Freeze RCA in this TP with exact artifacts and one allowed layer classification.
2. Add focused deterministic coverage for booking-verification temporal-grounding preservation.
3. Implement one bounded boundary fix in `decision.py`.
4. If the first fresh replay exposes non-product replay distortion, classify it separately and fix only the evaluator/runtime seam that distorts the same family proof.
5. Run focused deterministic checks.
6. Run fresh replay and full human semantic audit.
7. Update `STATE.md` / `STRUCTURE.md` with new truth and residual families.

## DoD
- Exact mechanism path is written with trace/meta evidence.
- One allowed layer classification is proven.
- Fix is mechanism-level and bounded.
- Focused deterministic checks are green.
- Fresh replay is run and a fresh full human semantic audit is completed.
- `STATE.md` records the new practical truth without overclaim.

## Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "check_booking and reference"`
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_tool_evidence_gate.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_tool_evidence_gate.py -k "check_booking or calendar_hook or tool_evidence_strict_policy_ignores_check_booking_reference_collect_prompts or booking_commit_trace_without_calendar_intent_counter"`
- `scripts/llm_quality_guarded.sh --mode replay --run-id a922-practical-proof-20260330-r32g ...`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r32g --status done --strict-artifacts --analyst a922 --human-semantic-valid false --human-semantic-summary "...parking fact composition still fails..."`
- `git diff --check`

## Evidence
- this TP with exact RCA and one web search
- focused deterministic test output
- fresh replay artifact bundle: `/tmp/booking_quality/a922-practical-proof-20260330-r32g/{summary.json,brief.md,scenarios.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json,run_manifest.json}`
- human semantic report: `docs/REPORTS/2026-03-30-consultant-core-r32g-human-semantic-audit-a922.md`
- `STATE.md` current-truth update

## Rollback
- Revert the bounded boundary fix and accompanying deterministic tests as one block if replay shows booking-verification prompts regress or true handoff paths stop working.

## No-go
- No scenario/dialog-id patching.
- No weekday-specific hardcode in runtime core.
- No product-green claim without replay + full human semantic audit.
- No claim that owner error was proven here; this block is about boundary booking-verification continuity.

## Риски/блокеры
- Booking-verification prompt selection is shared across degraded/pending paths; careless changes can suppress legitimate requests for precise booking reference.
- Fresh replay may close this family but still leave the overall lane contract-red due oracle taxonomy drift or evaluator/tool-evidence drift.

## Replay extension after first fix
- `r31` outcome:
  - product-side turn 1 regression was fixed, but replay injected synthetic `confirm/calendar` tool hooks from `check_booking_prompt` reference-collect turns and distorted `dialog 9 / turn 2` into a pending/handoff path
- exact replay-distortion path:
  1. `dialog 9 / turn 1` final response already asks only for `name/phone`
  2. `ops/diagnose.py` still interpreted `intent=check_booking` as a calendar/confirm tool opportunity even when `action=check_booking_prompt`
  3. auto tool hooks sent synthetic follow-up messages (`LLM-QUAL-TOOL-CONFIRM...`, `LLM-QUAL-TOOL-CALENDAR...`)
  4. those synthetic turns pushed the conversation into a degraded pending/handoff branch before the scripted turn 2
- replay-distortion classification:
  - `oracle_or_evaluator_error`
- bounded evaluator fix:
  - suppress tool-hook generation and strict tool-evidence opportunities for `check_booking_prompt` reference-collect turns, while preserving evidence requirements for actual booking lookup/commit turns

## Final outcome
- final fresh replay used for truth update:
  - `a922-practical-proof-20260330-r32g`
- final verdict for the scoped family:
  - `closed`
- practical status after closure:
  - replay remains product-red only because `parking fact composition regression` is again the sole human-semantic fail family on current truth

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `parking fact composition regression` without closure claim
- trace-visible `dialog 2 / turn 5` `datetime_parse_failed` residue
- strict/oracle drift on otherwise acceptable `dialog 9 / turn 2` identity-only recovery
### Why not in this block
- Canon/user scope allows one mechanism block at a time.
### Risk if deferred
- Parking can reappear on a later replay, and the booking trace residue can become user-visible again.
### Linked follow-up Task Package(s)
- next: parking fact composition family
- next: trace-visible booking commit residue if it becomes human-visible
### Expiry/trigger to stop deferral
- Before any practical/product closure claim.

## Next-block contract (mandatory)
### Next block objective
- Open the next mechanism-first TP for `parking fact composition regression`, framed as `fact selection / fact composition`.
### First deterministic check command
- `python3 - <<'PY'
import json
from pathlib import Path
run=Path('/tmp/booking_quality/a922-practical-proof-20260330-r32g/responses.jsonl')
for line in run.read_text().splitlines():
    row=json.loads(line)
    if row.get('dialog_id') == 6:
        print(row.get('inline_response_text'))
PY`
### Blocked-by conditions
- parking RCA not yet reconstructed from `r32g`
### Owner role for closure
- `Brain/Architect`
