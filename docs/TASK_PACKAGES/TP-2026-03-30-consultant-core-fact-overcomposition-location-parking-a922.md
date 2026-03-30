# TP-2026-03-30-consultant-core-fact-overcomposition-location-parking-a922

- Status: `in_progress`
- Owner: `Hands`
- Date: `2026-03-30`

## Название/цель
Построить exact live-path RCA для weak family `fact over-composition on location/parking replies` из replay `r35f`, доказать один слой классификации на уровне общего механизма `fact selection / fact composition`, и только после этого предложить один bounded fix без scenario patching.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/REPORTS/2026-03-30-consultant-core-r35f-human-semantic-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-parking-owner-grounding-r34d-a922.md`
- `/tmp/booking_quality/a922-practical-proof-20260330-r35f/{summary.json,brief.md,scenarios.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json,manual_audit_workspace.md,manual_audit_workspace.json,family_registry.json,judge_conflicts.jsonl,run_manifest.json}`
- `/tmp/booking_quality/a922-practical-proof-20260330-r34d/{summary.json,brief.md,scenarios.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json,manual_audit_workspace.md,manual_audit_workspace.json,family_registry.json,judge_conflicts.jsonl,run_manifest.json}`

## Invariant
- Не лечить `dialog 5 / turn 1` и `dialog 6 / turn 1` как отдельные сценарии; фиксировать только repeatable failure family.
- Не объявлять второй semantic owner и не описывать архитектуру как broken-in-new-way без exact path evidence.
- Не добавлять phrase/regex branching под `адрес`, `парковка`, `часы работы`.
- Не считать deterministic checks достаточным evidence; обязательны fresh replay + full human semantic audit.
- Failure family = evidence label; implementation unit = `broken invariant + shared mechanism`.

## Scope
- Только механизм `fact selection / fact composition` для branch info replies на текущем truth `r35f`.
- Exact path reconstruction для weak family: `input -> owner output -> validator/guard -> fallback/degrade -> final response -> trace/meta evidence -> layer classification`.
- Один bounded fix после доказанного RCA.

## Out of scope
- booking families
- check-booking families
- owner-side service grounding families
- wording-only edits
- oracle-only taxonomy disagreements, если visible path остаётся acceptable

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-fact-overcomposition-location-parking-a922.md`
- `truffles-api/app/routers/webhook/info.py`
- `truffles-api/app/services/pack_runtime_neutral_adapter.py`
- `truffles-api/tests/test_message_endpoint.py`
- `docs/REPORTS/2026-03-30-consultant-core-r36-human-semantic-audit-a922.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `STATE.md`
- `STRUCTURE.md`

## Work mode
- `RCA -> bounded implementation -> replay -> human audit`

## Surfaced family / mechanism-first frame
- Surfaced family label:
  - `fact over-composition on location/parking replies`
- Broken invariant:
  - when the user asks for one concrete branch fact and owner grounding is already correct, the final reply should answer that fact without automatically composing adjacent sibling branch facts that were not requested.
- Shared mechanism:
  - `fact selection / fact composition`
- Why this surfaced family belongs to that mechanism:
  - on current truth `r35f`, the visible weakness is no longer owner grounding; the extra breadth appears only in the final composed fact reply after the valid owner plan passes unchanged through validation.
- Open-world envelope expected to improve:
  - direct branch-fact asks for location/parking/hours/contact where runtime currently widens the final fact bundle beyond the explicitly requested fact.

## One web search (mandatory before implementation)
- Query: `site:developers.openai.com grounding retrieval focus answer only requested facts official docs`
- Date/time: `2026-03-30 07:22 +05`
- Sources opened:
  - `https://developers.openai.com/api/docs/guides/retrieval`
- Source quality:
  - official vendor documentation
- Findings:
  - retrieval quality improves when the system keeps results narrowly focused on the most relevant facts instead of widening the answer with adjacent context by default
  - query rewriting / narrowing is useful when a user asks for one specific fact, because broad neighboring context can dilute the requested answer
- Decision:
  - `reuse/integrate`
  - tighten fact-composition rules so direct branch-fact answers stay scoped to the requested fact unless the user explicitly asks for a wider bundle
- Rejected variants:
  - `patch only the exact strings "Где находится салон?" / "Есть ли у вас парковка?"` — violates scenario-patch ban
  - `treat the weak turns as oracle-only and leave the broad reply unchanged` — contradicted by the full human audit, which still marks both turns as product-weak

## Root cause (mandatory)
- Symptom:
  - `dialog 5 / turn 1`: location answer also includes hours
  - `dialog 6 / turn 1`: parking answer also includes address + hours
- Minimal reproduction:
  - replay `a922-practical-proof-20260330-r35f`
  - `responses.jsonl` / `trace_bundle.jsonl`, `dialog_id in {5,6}`, `turn_index=1`
- Evidence:
  - `/tmp/booking_quality/a922-practical-proof-20260330-r35f/responses.jsonl`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r35f/trace_bundle.jsonl`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r35f/manual_audit_workspace.json`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r35f/family_registry.json`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r35f/judge_conflicts.jsonl`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r34d/trace_bundle.jsonl`
  - `truffles-api/app/routers/webhook/info.py`
  - `truffles-api/app/services/pack_runtime_neutral_adapter.py`
- Five Whys:
  1. Why are the visible replies broader than requested? Because final fact composition adds sibling branch facts (`hours`, `address`) after the owner-grounded single-fact plan has already validated.
  2. Why does the direct location reply add hours? Because `_build_info_intent_reply("location", ...)` always calls `build_info_combined_reply(...)`, which composes `location + hours` together.
  3. Why does the parking reply add address + hours? Because `_build_info_intent_reply("parking", ...)` has no direct scoped parking branch, so the runtime falls through to generic `info_class` / `class_router`; there, parking sets `location_signal`, `include_base_bundle=True`, and the composed reply becomes `location + hours + parking`.
  4. Why do validator/guard layers not stop this widening? Because validation succeeds, there is no degrade/fallback, and the widening happens later inside the fact-rendering/composition path rather than in a guard.
  5. Why is this a mechanism-level family? Any owner-grounded single branch-fact ask can be widened by the same downstream composition rules when the renderer defaults to a base bundle instead of the requested fact set.
- Root cause statement:
  - the downstream branch fact renderer is scoped incorrectly: it composes the default `location + hours` bundle for direct location asks and lacks a scoped parking reply path, so owner-grounded single-fact requests are widened into composite branch bundles after validation.
- Fix mechanism:
  - introduce a scoped branch-fact rendering path that composes only the explicitly requested branch facts for owner-grounded direct info replies, and use the existing wider bundle only when multiple branch facts are explicitly requested.

## Exact path map
1. `input`
   - `dialog 5 / turn 1`: `turn_text="Где находится салон?"`
   - `dialog 6 / turn 1`: `turn_text="Есть ли у вас парковка?"`
2. `owner output`
   - `dialog 5 / turn 1`: valid owner payload with `intent="location"`, `action="fact"`, `tool_action="info"`, `pack_refs=["location"]`, `subject_kind="branch"`, `resolution_mode="policy_fact"`
   - `dialog 6 / turn 1`: valid owner payload with `intent="parking"`, `action="fact"`, `tool_action="info"`, `pack_refs=["parking"]`, `subject_kind="branch"`, `resolution_mode="policy_fact"`
3. `validator / guard`
   - both turns: `capability_check` allows the requested info scope, `llm_policy_plan_delta=match`, `policy_core_mode=policy_core`, no validation error, no override, no degrade
4. `fallback / degrade`
   - none on either weak turn
5. `final response`
   - `dialog 5 / turn 1`: visible reply contains address + hours; `decision_meta.info_sections=["address","hours"]`, `source="llm_policy_core"`
   - `dialog 6 / turn 1`: visible reply contains address + hours + parking; `decision_meta.info_sections=["address","hours","parking"]`, `source="class_router"`
6. `trace/meta evidence`
   - `dialog 5 / turn 1`: `trace_bundle.jsonl` shows `llm_policy_core fact -> capability_contract policy_fact -> info_class reply intent=location -> fact_resolver resolved info_sections=["address","hours"]`
   - `dialog 6 / turn 1`: `trace_bundle.jsonl` shows `llm_policy_core fact -> capability_contract policy_fact -> class_router info_bundle -> info_class reply -> fact_refs=["address","hours","parking"]`
   - `dialog 6 / turn 1`: `r34d` proves the older product fail was owner grounding (`contact`), while `r35f` proves owner grounding is fixed and the remaining breadth is introduced after validation
7. `layer classification`
   - `fact_composition_error`

## Required RCA questions
1. Where exactly is the requested fact first represented in the live path?
   - `dialog 5`: first structured as owner `pack_refs=["location"]`
   - `dialog 6`: first structured as owner `pack_refs=["parking"]`
2. What exact structured owner output is produced for the weak turns?
   - `dialog 5`: `intent="location"`, `tool_action="info"`, `pack_refs=["location"]`
   - `dialog 6`: `intent="parking"`, `tool_action="info"`, `pack_refs=["parking"]`
3. Does any validator/projector/guard mutate or widen that meaning?
   - no; widening happens later in the reply-composition path after validation succeeds
4. If downstream widening exists, which composition rule or resolver chooses the broader fact bundle?
   - `dialog 5`: `_build_info_intent_reply("location") -> build_info_combined_reply()` adds `hours`
   - `dialog 6`: lack of a scoped parking direct reply falls into `info_class/class_router`, where parking implies `location_signal` and `include_base_bundle=True`, producing `address + hours + parking`
5. Is this a prompt issue, composition rule issue, resolver issue, or boundary policy issue?
   - downstream composition rule issue

## Plan
1. Freeze the one-web-search entry and current truth refs in this TP before code edits.
2. Reconstruct the exact live path for `dialog 5 / turn 1` and `dialog 6 / turn 1`.
3. Prove one allowed layer classification and one mechanism-level root cause.
4. Add focused deterministic coverage for the proven composition invariant.
5. Implement one bounded fix.
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
- `python3 -m py_compile truffles-api/app/routers/webhook/info.py truffles-api/app/services/pack_runtime_neutral_adapter.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "location or parking"`
- `scripts/llm_quality_guarded.sh --mode replay --run-id a922-practical-proof-20260330-r36 ...`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r36 --status done --strict-artifacts --analyst a922 --human-semantic-valid ...`
- `git diff --check`

## Evidence
- this TP with exact RCA and one web search
- focused deterministic test output
- fresh replay artifact bundle: `/tmp/booking_quality/a922-practical-proof-20260330-r36/{summary.json,brief.md,scenarios.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json,manual_audit_workspace.md,manual_audit_workspace.json,family_registry.json,judge_conflicts.jsonl,run_manifest.json}`
- human semantic report: `docs/REPORTS/2026-03-30-consultant-core-r36-human-semantic-audit-a922.md`
- `STATE.md` current-truth update

## Rollback
- Revert the bounded composition change and accompanying deterministic tests as one block if replay shows direct branch-fact answers become too narrow or lose needed safety context.

## No-go
- No dialog-id or wording patching.
- No deterministic post-hoc semantic rewrite of user text.
- No new architecture claim without exact path evidence.
- No product-green claim without replay + full human semantic audit.
- No claim that a second semantic owner was proven.

## Риски/блокеры
- Narrowing replies too aggressively may remove genuinely helpful safety/location context from some branch fact answers.
- Fresh replay may improve this family but leave the lane amber because of the secondary booking-verification contract residue.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `dialog 9 / turn 2` still carries secondary contract-red residue even though the visible reply is acceptable
- oracle/evaluator taxonomy drift still leaves some acceptable turns strict-red
- trace-visible booking handoff residue on `dialog 2 / turn 5`
### Why not in this block
- This block is explicitly scoped to branch fact composition breadth only.
### Risk if deferred
- Practical/product closure remains open while the current truth stays human-semantic amber.
### Linked follow-up Task Package(s)
- next: secondary booking-verification contract residue if it ever becomes user-visible
- next: oracle/evaluator calibration if product path becomes green first
### Expiry/trigger to stop deferral
- before any practical/product closure claim

## Next-block contract (mandatory)
### Next block objective
- if this block closes as scoped, take the next visible residue from the fresh replay and translate it into `broken invariant + shared mechanism`
### First deterministic check command
- `python3 - <<'PY'
import json
from pathlib import Path
run=Path('/tmp/booking_quality/a922-practical-proof-20260330-r35f/responses.jsonl')
for line in run.read_text().splitlines():
    row=json.loads(line)
    if (row.get('dialog_id'), row.get('turn_index')) in {(5, 1), (6, 1)}:
        print(row.get('dialog_id'), row.get('turn_index'), row.get('inline_response_text'))
PY`
### Blocked-by conditions
- exact live-path RCA for the weak family has not yet been written
### Owner role for closure
- `Brain/Architect`
