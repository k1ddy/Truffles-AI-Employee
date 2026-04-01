# TP-2026-03-30-consultant-core-parking-fact-composition-a922

- Status: `done`
- Owner: `Hands`
- Date: `2026-03-30`

## Название/цель
Построить exact live-path RCA для surfaced family `parking fact composition regression` из replay `r32g`, доказать один слой классификации на уровне общего механизма `fact selection / fact composition`, и только после этого предложить один bounded fix без scenario patching.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/REPORTS/2026-03-30-consultant-core-r32g-human-semantic-audit-a922.md`
- `/tmp/booking_quality/a922-practical-proof-20260330-r32g/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json}`

## Invariant
- Не лечить `dialog 6 / turn 1` как отдельный сценарий; фиксировать только repeatable failure family.
- Не объявлять второй semantic owner и не описывать архитектуру как broken-in-new-way без exact path evidence.
- Не добавлять phrase/regex branching под `парковка`.
- Не считать deterministic checks достаточным evidence; обязательны fresh replay + full human semantic audit.
- Failure family = evidence label; implementation unit = `broken invariant + shared mechanism`.

## Scope
- Только механизм `fact selection / fact composition`.
- Exact path reconstruction для `r32g` family: `input -> owner output -> validator/guard -> fallback/degrade -> final response -> trace/meta evidence -> layer classification`.
- Один bounded mechanism-level fix после доказанного RCA.

## Out of scope
- любые новые owner/prompt claims без exact path evidence
- `booking-manage` families
- wording-only edits
- oracle-only taxonomy disagreements

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-parking-fact-composition-a922.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/REPORTS/2026-03-30-consultant-core-r33-human-semantic-audit-a922.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `STATE.md`
- `STRUCTURE.md`

## Work mode
- `RCA -> bounded implementation -> replay -> human audit`

## Surfaced family / mechanism-first frame
- Surfaced family label:
  - `parking fact composition regression`
- Broken invariant:
  - when the owner grounds a concrete info ref `parking` and truth data contains that fact, runtime must preserve that ref through info selection/composition and surface the parking fact in the final reply instead of falling back to the default location/hours bundle.
- Shared mechanism:
  - `fact selection / fact composition`
- Why this surfaced family belongs to that mechanism:
  - the failure is not one parking wording; it is a repeatable composition miss where a grounded fact ref exists in owner/truth evidence but is dropped before final reply assembly.
- Open-world envelope expected to improve:
  - any info turn where owner grounds a specific non-service fact ref and downstream composition currently falls back to a broader base bundle.

## One web search (mandatory before implementation)
- Query: `site:platform.openai.com/docs rerank relevant context filters official`
- Date/time: `2026-03-30 03:44 Asia/Almaty`
- Sources opened:
  - `https://platform.openai.com/docs/guides/retrieval`
- Source quality:
  - official vendor documentation
- Findings:
  - retrieval/composition should preserve the most relevant grounded context instead of letting broader context crowd out the requested fact
  - downstream composition should treat grounded refs as selection constraints, not optional flavor
- Decision:
  - `reuse/integrate`
  - keep parking as an owner-grounded fact-selection constraint through the info-class composition path instead of letting the generic base bundle overwrite it
- Rejected variants:
  - `patch only the exact string "Есть ли у вас парковка?"` — violates scenario-patch ban
  - `treat owner output as the bug despite preserved pack_refs=["parking"]` — contradicted by the live path evidence

## Root cause (mandatory)
- Symptom:
  - `dialog 6 / turn 1`: `Есть ли у вас парковка?` -> bot replies with after-hours banner + address + hours and omits the parking fact.
- Minimal reproduction:
  - replay `a922-practical-proof-20260330-r32g`
  - `responses.jsonl` / `trace_bundle.jsonl`, `dialog_id=6`, `turn_index=1`
- Evidence:
  - `/tmp/booking_quality/a922-practical-proof-20260330-r32g/responses.jsonl`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r32g/trace_bundle.jsonl`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/app/services/pack_runtime_neutral_adapter.py`
- Five Whys:
  1. Why does the final reply omit parking? Because the reply is composed as the default location/hours bundle without `include_parking=True`.
  2. Why does info composition miss `include_parking=True` even though the owner grounded parking? Because the policy-core info path hands off to `_handle_info_flow(...)` with `info_class_meta={}`, so the downstream info composer loses the `info_signals["parking"]` signal that controls parking inclusion.
  3. Why does the handoff still choose location/hours? Because the class-router/controller info-bundle path overrides reply intents with `location/hours/pricing/duration`, so the response is composed around the generic bundle once the parking signal is missing.
  4. Why is that wrong? Because the owner output still carries `pack_refs=["parking"]`, capability checks allow `info.parking`, and fact evidence still includes `parking`; the user-visible loss happens only in downstream selection/composition.
  5. Why is this a mechanism-level family? Any owner-grounded specific info ref can be dropped the same way if the handoff to info composition loses the grounded section signal and falls back to the generic base bundle.
- Root cause statement:
  - the policy-core `tool_action=info` handoff drops owner-grounded fact-selection signals by delegating into `info_class` with empty `info_class_meta`, so downstream info composition loses `parking` as a required section and falls back to the default `location/hours` bundle even though owner refs and truth evidence still contain `parking`
- Fix mechanism:
  - preserve owner-grounded info-section signals when `policy_tool_action=info` delegates into `info_class`, so the composer keeps `include_parking=True` for grounded parking refs

## Exact path map
1. `input`
   - `dialog 6 / turn 1`: `turn_text="Есть ли у вас парковка?"`
2. `owner output`
   - valid owner payload with `intent=hours`, `action=fact`, `tool_action=info`, `pack_refs=["parking"]`, `resolution_mode=policy_fact`, `subject_kind=branch`
3. `validator / guard`
   - capability check allows `fact_scope=info.parking`
   - no validation error blocks the owner plan
4. `fallback / degrade`
   - none at the policy-validation layer; the demotion happens inside downstream info selection/composition
5. `final response`
   - `source=class_router`, visible text contains only after-hours banner + address + hours
6. `trace/meta evidence`
   - `llm_policy_core.payload.pack_refs=["parking"]`
   - `class_router.output.reason="Вопрос о парковке"`
   - `info_class.info_sections=["address","hours"]`
   - `fact_resolver.fact_evidence_refs=["address","hours","parking"]`
7. `layer classification`
   - `fact_composition_error`

## Required RCA questions
1. Where exactly is the user service/fact mention first represented in the live path?
   - in the owner output as `pack_refs=["parking"]`; the deterministic info detector also marks `info_signals["parking"]=True` on the raw text path, but the failing policy-info handoff does not preserve that signal.
2. What exact structured owner output is produced for the failing turn?
   - `intent=hours`, `action=fact`, `tool_action=info`, `pack_refs=["parking"]`, `goal=info`, `resolution_mode=policy_fact`, `subject_kind=branch`, `confidence=0.42`
3. Does any validator/projector/guard mutate or demote that meaning?
   - yes: the policy-info handoff to `_handle_info_flow(...)` clears `info_class_meta`, and the downstream class-router reply composition then demotes the grounded parking ref into the generic location/hours bundle.
4. If no downstream mutation exists, what owner contract/prompt/context gap explains the failure?
   - not applicable; downstream mutation exists and is user-visible.
5. Is this a vocabulary issue, context issue, prompt issue, resolver issue, or pack grounding issue?
   - fact-selection / composition issue in the policy-info handoff boundary.

## Plan
1. Freeze RCA in this TP with exact artifacts and one allowed layer classification.
2. Add focused deterministic coverage for owner-grounded parking preservation through the policy-info path.
3. Implement one bounded fact-composition fix in `decision.py`.
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
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "parking and policy_core"`
- `scripts/llm_quality_guarded.sh --mode replay --run-id a922-practical-proof-20260330-r33 ...`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r33 --status done --strict-artifacts --analyst a922 --human-semantic-valid ...`
- `git diff --check`

## Evidence
- this TP with exact RCA and one web search
- focused deterministic test output
- fresh replay artifact bundle: `/tmp/booking_quality/a922-practical-proof-20260330-r33/{summary.json,brief.md,scenarios.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json,run_manifest.json}`
- human semantic report: `docs/REPORTS/2026-03-30-consultant-core-r33-human-semantic-audit-a922.md`
- `STATE.md` current-truth update

## Rollback
- Revert the bounded fact-composition fix and accompanying deterministic tests as one block if replay shows info replies regress or other policy-info turns lose grounded facts.

## No-go
- No dialog-id or wording patching.
- No new owner/prompt claim without exact path evidence.
- No product-green claim without replay + full human semantic audit.
- No claim that a second semantic owner was proven.

## Риски/блокеры
- The policy-info handoff is shared by multiple info families; careless changes can over-preserve stale info signals across unrelated turns.
- Fresh replay may close parking but expose a different residual info family.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- location/parking fact replies still over-compose adjacent sections on some acceptable turns
- media/photo clarification remains service-first instead of explicitly acknowledging the photo offer
- booking verification confirm follow-up remains generic on the degraded invalid-schema turn
### Why not in this block
- This block was explicitly scoped to the parking fact-composition fail family only.
### Risk if deferred
- The visible lane stays human-semantic amber even though the parking fail family is closed.
### Linked follow-up Task Package(s)
- next: booking verification confirm recovery under degraded invalid_schema
- next: fact over-composition broadness if it becomes the primary visible blocker
### Expiry/trigger to stop deferral
- before any practical/product closure claim

## Next-block contract (mandatory)
### Next block objective
- if product work continues, take the next mechanism-first block as `booking verification confirm recovery under degraded invalid_schema`
### First deterministic check command
- `python3 - <<'PY'
import json
from pathlib import Path
run=Path('/tmp/booking_quality/a922-practical-proof-20260330-r33/responses.jsonl')
for line in run.read_text().splitlines():
    row=json.loads(line)
    if row.get('dialog_id') == 9 and row.get('turn_index') == 2:
        print(row.get('inline_response_text'))
PY`
### Blocked-by conditions
- none; `r33` establishes the next visible weak family.
### Owner role for closure
- `Brain/Architect`

## Final outcome
- Bounded fix implemented:
  - `_build_policy_info_class_meta(...)` now preserves owner-grounded info-section signals for the policy-info -> info-class handoff
  - the policy-info runtime path now passes non-empty `info_class_meta` into `_handle_info_flow(...)`
- Deterministic evidence:
  - `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "build_policy_info_class_meta_preserves_owner_grounded_parking_signal or preserves_owner_grounded_parking_in_info_class_handoff or catalog_location_passes_parking_info_hint or catalog_location_does_not_use_policy_reason_for_parking_hint or catalog_location_does_not_use_parking_intent_hint"`
- Fresh replay:
  - `/tmp/booking_quality/a922-practical-proof-20260330-r33`
- Fresh audit:
  - `/tmp/booking_quality/a922-practical-proof-20260330-r33/manual_audit.md`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r33/manual_audit.json`
  - `docs/REPORTS/2026-03-30-consultant-core-r33-human-semantic-audit-a922.md`
- Family verdict:
  - `parking fact composition regression` = `closed as scoped`
- Current truth after closure:
  - no outright human-semantic fail turns remain on `r33`, but practical/product closure stays open because the run is still human-semantic amber and contract-red
