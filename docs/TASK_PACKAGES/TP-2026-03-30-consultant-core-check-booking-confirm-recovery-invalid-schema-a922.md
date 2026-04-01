# TP-2026-03-30-consultant-core-check-booking-confirm-recovery-invalid-schema-a922

- Status: `done`
- Owner: `Hands`
- Date: `2026-03-30`

## Название/цель
Построить exact live-path RCA для surfaced weak family `booking verification confirm recovery under degraded invalid_schema` из replay `r33`, доказать один слой классификации на уровне общего механизма `booking-manage follow-up continuity`, и только после этого предложить один bounded fix без scenario patching.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/REPORTS/2026-03-30-consultant-core-r33-human-semantic-audit-a922.md`
- `/tmp/booking_quality/a922-practical-proof-20260330-r33/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json,manual_audit_workspace.md,manual_audit_workspace.json,family_registry.json,judge_conflicts.jsonl}`

## Invariant
- Не лечить `dialog 9 / turn 2` как отдельный сценарий; фиксировать только repeatable failure family.
- Не объявлять второй semantic owner и не описывать архитектуру как broken-in-new-way без exact path evidence.
- Не добавлять phrase-hardcode под `четверг` / `подтвердите`.
- Не считать deterministic checks достаточным evidence; обязательны fresh replay + full human semantic audit.
- Failure family = evidence label; implementation unit = `broken invariant + shared mechanism`.

## Scope
- Только механизм `booking-manage follow-up continuity`.
- Exact path reconstruction для `r33` family: `input -> owner output -> validator/guard -> fallback/degrade -> final response -> trace/meta evidence -> layer classification`.
- Один bounded mechanism-level fix после доказанного RCA.

## Out of scope
- `parking` / `fact composition`
- media/photo clarification
- oracle-only taxonomy disagreements
- wording-only edits без trace-backed mechanism fix

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-check-booking-confirm-recovery-invalid-schema-a922.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/REPORTS/2026-03-30-consultant-core-r34-human-semantic-audit-a922.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `STATE.md`
- `STRUCTURE.md`

## Work mode
- `RCA -> bounded implementation -> replay -> human audit`

## Surfaced family / mechanism-first frame
- Surfaced family label:
  - `booking verification confirm recovery under degraded invalid_schema`
- Broken invariant:
  - when booking verification is already collecting identity/reference and the follow-up message narrows the same request into a confirm/verify variant, degraded fallback must preserve the active booking-verification collect owner and confirmation-aware continuity instead of collapsing into a generic check-booking prompt.
- Shared mechanism:
  - `booking-manage follow-up continuity`
- Why this surfaced family belongs to that mechanism:
  - the failure is not one phrase on one dialog; it is a repeatable degraded fallback miss where an active booking-verification collect follow-up loses operation-mode continuity (`check` vs `confirm`) and falls back to the generic reference prompt.
- Open-world envelope expected to improve:
  - any degraded booking-verification follow-up where the user stays on the same missing identity/reference slot but adds confirm/verify intent wording after an active collect prompt.

## One web search (mandatory before implementation)
- Query: `site:platform.openai.com/docs structured outputs schema validation official`
- Date/time: `2026-03-30 05:18 Asia/Almaty`
- Sources opened:
  - `https://developers.openai.com/api/docs/guides/structured-outputs`
- Source quality:
  - official vendor documentation
- Findings:
  - strict structured outputs should follow the supplied schema, and schema design/validation must be paired with evals
  - unsupported or invalid schema paths can produce hard errors, so production fallback must preserve already-grounded interaction state instead of re-deriving semantics loosely
- Decision:
  - `reuse/integrate`
  - keep the existing invalid-schema degrade boundary, but preserve booking-verification follow-up mode and active expected-reply continuity through that boundary instead of letting degraded collect collapse into the generic verification prompt
- Rejected variants:
  - `patch only the exact sentence "Подтвердите, пожалуйста, мою запись на четверг."` — violates scenario-patch ban
  - `treat the owner as wrong on turn 2` — contradicted by the artifact evidence because the owner produced no valid structured output at all (`invalid_schema`)

## Root cause (mandatory)
- Symptom:
  - `dialog 9 / turn 2`: `Подтвердите, пожалуйста, мою запись на четверг.` -> bot stays on the correct identity/reference slot, but replies with the same generic `check-booking` prompt instead of a confirmation-aware follow-up.
- Minimal reproduction:
  - replay `a922-practical-proof-20260330-r33`
  - `responses.jsonl` / `trace_bundle.jsonl`, `dialog_id=9`, `turn_index=2`
- Evidence:
  - `/tmp/booking_quality/a922-practical-proof-20260330-r33/responses.jsonl`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r33/trace_bundle.jsonl`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r33/manual_audit_workspace.json`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r33/family_registry.json`
  - `truffles-api/app/routers/webhook/decision.py`
- Five Whys:
  1. Why does the reply feel generic on the confirm follow-up? Because the visible prompt is the same generic booking-verification identity/reference prompt used for plain `check` requests.
  2. Why does the degraded path choose the generic prompt? Because `collect_verification_signal` routes to `_select_booking_verification_collect_prompt(...)`, and that selector only differentiates temporal grounding, not verification mode.
  3. Why is confirmation-aware continuity missing at that point? Because `question_contract` first bypasses the active expected reply on any booking-verification-looking text, clears session-memory expected reply, and the invalid-schema fallback then re-enters as a generic `check_booking_prompt`.
  4. Why does the boundary not recover the confirm nuance? Because confirm vs check is only resolved from valid policy intent/tool contract (`confirm_booking`/`check_booking`), but the `invalid_schema` path has no valid policy payload and no fallback mode-preservation for booking verification.
  5. Why is this a mechanism-level family? Any degraded booking-verification follow-up can lose confirmation-aware continuity the same way when the owner fails with `invalid_schema` and boundary fallback only preserves the slot, not the verification mode.
- Root cause statement:
  - the `invalid_schema` booking-verification degrade boundary preserves the missing identity/reference slot but drops verification operation mode, because `question_contract` bypass clears the active expected reply and `_select_booking_verification_collect_prompt(...)` only chooses between generic reference prompts by temporal grounding, not by follow-up mode (`check` vs `confirm`)
- Fix mechanism:
  - preserve booking-verification follow-up mode across the invalid-schema degrade path and let the degraded collect prompt selector choose a confirmation-aware identity/reference prompt when the active follow-up is confirm-like

## Exact path map
1. `input`
   - `dialog 9 / turn 2`: `turn_text="Подтвердите, пожалуйста, мою запись на четверг."`
2. `owner output`
   - no valid structured owner payload; `llm_policy_core.ok=false`, `error=invalid_schema`, `validated=false`, `semantic_owner=llm_policy_core`
3. `validator / guard`
   - active expected reply from turn 1 is `expected_reply_type=name`, `expected_reply_reason=calendar_get_booking_collect_reference`
   - `question_contract` bypass fires on `booking_verification`, clears expected reply, and records `expected_reply_bypassed=booking_verification`
4. `fallback / degrade`
   - `policy_core_mode=degraded_fallback`, `policy_core_degrade_reason=policy_error:invalid_schema`
   - degraded collect computes a generic collect path, briefly sets `expected_reply_type=service_choice` for `policy_core_degraded_collect`, then the booking-verification guard overwrites it back to `expected_reply_type=name`
   - `_select_booking_verification_collect_prompt(...)` chooses the identity-only reference prompt only from temporal grounding; it does not preserve confirm mode
5. `final response`
   - visible reply: `Чтобы проверить, перенести или отменить запись, подскажите имя или номер телефона.`
6. `trace/meta evidence`
   - `responses.jsonl`: `turn_tags=["confirm"]`, `decision_meta.action=check_booking_prompt`, `decision_meta.source=booking_verification`
   - `decision_meta.expected_reply_reason=calendar_get_booking_collect_reference`
   - `decision_meta.expected_reply_bypassed=booking_verification`
   - `decision_meta.policy_core_mode=degraded_fallback`
   - `decision_meta.policy_core_degrade_reason=policy_error:invalid_schema`
   - `decision_trace`: `question_contract bypass -> llm_policy_core invalid_schema -> policy_core_degraded_collect set(service_choice) -> booking_verification degraded_check_booking_prompt set(name)`
7. `layer classification`
   - `boundary_fallback_error`

## Required RCA questions
1. Where exactly is the user follow-up meaning first represented in the live path?
   - in `responses.jsonl` / `trace_bundle.jsonl` as `turn_tags=["confirm"]` and as booking-verification text matched by `question_contract` before policy-core fallback.
2. What exact structured owner output is produced for the failing turn?
   - none; `llm_policy_core` returns `ok=false`, `error=invalid_schema`, `validated=false`.
3. Does any validator/projector/guard mutate or demote that meaning?
   - yes; `question_contract` bypass clears the active expected reply, and degraded collect later preserves only the missing slot while dropping the confirm/check mode.
4. If no downstream mutation exists, what owner contract/prompt/context gap explains the failure?
   - not applicable; downstream mutation exists at the invalid-schema degrade boundary.
5. Is this a vocabulary issue, context issue, prompt issue, resolver issue, or pack grounding issue?
   - fallback/resolver issue in the degraded booking-verification continuity boundary.

## Plan
1. Freeze RCA in this TP with exact artifacts and one allowed layer classification.
2. Add focused deterministic coverage for confirm-aware degraded booking-verification follow-up continuity.
3. Implement one bounded continuity fix in `decision.py`.
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
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "collect_check_booking or pending_check_booking_reference_collect or collect_slot_order_invalid_check_booking_weekday_keeps_identity_only_prompt or pending_check_booking_collect_slot_order_invalid_weekday_keeps_identity_only_prompt or collect_verification_missing_subject_sets_name_expected_reply or low_confidence_booking_verification_degraded_collect_uses_reference_prompt or invalid_schema_check_booking_confirm_followup_preserves_confirm_prompt_mode"`
- `scripts/llm_quality_guarded.sh --mode replay --run-id a922-practical-proof-20260330-r34d --allow-pending-previous --allow-repeat-fingerprint -- ...`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r34d --status done --strict-artifacts --analyst a922 --human-semantic-valid false ...`
- `git diff --check`

## Evidence
- this TP with exact RCA and one web search
- focused deterministic test output
- fresh replay artifact bundle: `/tmp/booking_quality/a922-practical-proof-20260330-r34d/{summary.json,brief.md,scenarios.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json,manual_audit_workspace.md,manual_audit_workspace.json,family_registry.json,judge_conflicts.jsonl,run_manifest.json}`
- human semantic report: `docs/REPORTS/2026-03-30-consultant-core-r34d-human-semantic-audit-a922.md`
- `STATE.md` current-truth update

## Rollback
- Revert the bounded booking-verification continuity fix and its deterministic tests as one block if replay shows booking-verification prompts regress or generic check prompts leak into other booking follow-ups.

## No-go
- No dialog-id or wording patching without shared-mechanism proof.
- No new owner/prompt claim without exact path evidence.
- No product-green claim without replay + full human semantic audit.
- No claim that a second semantic owner was proven.

## Риски/блокеры
- The booking-verification degrade path is shared with reference collection; careless changes can overfit confirm wording or alter acceptable `check` prompts.
- Fresh replay may close this weak family but leave the lane human-semantic amber because other weak families remain.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- parking fact composition has resurfaced as the first visible product blocker on the fresh replay truth
- location replies still over-compose adjacent sections on some acceptable turns
- media/photo clarification remains service-first instead of explicitly acknowledging the photo offer
- trace-visible `dialog 2 / turn 5` booking completion residue remains acceptable but not fully semantically clean
### Why not in this block
- This block is explicitly scoped to the degraded booking-verification follow-up continuity family only.
### Risk if deferred
- Practical/product closure remains red because the current truth still has a visible parking fail.
### Linked follow-up Task Package(s)
- next: re-open `parking fact composition regression` from the fresh truth with a new exact RCA pass over `r34d`
- next: media/photo acknowledgement continuity if it becomes the primary visible blocker
### Expiry/trigger to stop deferral
- before any practical/product closure claim

## Next-block contract (mandatory)
### Next block objective
- start from current truth `r34d` and reopen `parking fact composition regression` as a mechanism-first block around `fact selection / fact composition`
### First deterministic check command
- `python3 - <<'PY'
import json
from pathlib import Path
run=Path('/tmp/booking_quality/a922-practical-proof-20260330-r34d/responses.jsonl')
for line in run.read_text().splitlines():
    row=json.loads(line)
    if row.get('dialog_id') == 6 and row.get('turn_index') == 1:
        print(row.get('bot_text'))
PY`
### Blocked-by conditions
- none; `r34d` is the active practical truth.
### Owner role for closure
- `Brain/Architect`

## Outcome
- Fresh replay truth for this block: `a922-practical-proof-20260330-r34d`
- Deterministic checks:
  - `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "collect_check_booking or pending_check_booking_reference_collect or collect_slot_order_invalid_check_booking_weekday_keeps_identity_only_prompt or pending_check_booking_collect_slot_order_invalid_weekday_keeps_identity_only_prompt or collect_verification_missing_subject_sets_name_expected_reply or low_confidence_booking_verification_degraded_collect_uses_reference_prompt or invalid_schema_check_booking_confirm_followup_preserves_confirm_prompt_mode"` -> `7 passed`
- Fresh replay + audit:
  - `scripts/llm_quality_guarded.sh --mode replay --run-id a922-practical-proof-20260330-r34d --allow-pending-previous --allow-repeat-fingerprint -- ...` -> `infra_valid=true`, `semantic_valid=false`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r34d --status done --strict-artifacts --analyst a922 --human-semantic-valid false ...` -> `done`
- Family verdict:
  - `booking verification confirm recovery under degraded invalid_schema` is `closed as scoped`
- Closure evidence:
  - `dialog 9 / turn 2` now responds `Чтобы подтвердить запись, подскажите имя или номер телефона.`
  - `decision_meta.booking_verification_mode=confirm`
  - `decision_meta.expected_reply_type=name`
  - `decision_meta.policy_core_mode=degraded_fallback`
  - `decision_meta.policy_core_degrade_reason=policy_error:invalid_schema`
  - `decision_trace` preserves `booking_verification_mode=confirm` through the invalid-schema degrade boundary
- Current truth impact:
  - practical/product closure remains open because `dialog 6 / turn 1` re-surfaces `parking fact composition regression` on `r34d`
