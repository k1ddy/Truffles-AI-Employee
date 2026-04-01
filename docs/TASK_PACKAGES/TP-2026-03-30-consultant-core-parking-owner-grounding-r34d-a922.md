# TP-2026-03-30-consultant-core-parking-owner-grounding-r34d-a922

- Status: `done`
- Owner: `Hands`
- Date: `2026-03-30`

## Название/цель
Построить exact live-path RCA для re-opened family `parking fact composition regression` из replay `r34d`, доказать один слой классификации на уровне общего механизма `branch fact grounding specificity`, и только после этого предложить один bounded fix без scenario patching.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/REPORTS/2026-03-30-consultant-core-r34d-human-semantic-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-parking-fact-composition-a922.md`
- `/tmp/booking_quality/a922-practical-proof-20260330-r34d/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json,manual_audit_workspace.md,manual_audit_workspace.json,family_registry.json,judge_conflicts.jsonl,run_manifest.json}`
- `/tmp/booking_quality/a922-practical-proof-20260330-r33/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json,manual_audit_workspace.md,manual_audit_workspace.json,family_registry.json,judge_conflicts.jsonl,run_manifest.json}`

## Invariant
- Не лечить `dialog 6 / turn 1` как отдельный сценарий; фиксировать только repeatable failure family.
- Не объявлять второй semantic owner и не описывать архитектуру как broken-in-new-way без exact path evidence.
- Не добавлять phrase/regex branching под `парковка`.
- Не считать deterministic checks достаточным evidence; обязательны fresh replay + full human semantic audit.
- Failure family = evidence label; implementation unit = `broken invariant + shared mechanism`.

## Scope
- Только механизм `branch fact grounding specificity` внутри owner-side policy-core fact planning.
- Exact path reconstruction для `r34d` family: `input -> owner output -> validator/guard -> fallback/degrade -> final response -> trace/meta evidence -> layer classification`.
- Один bounded owner-contract fix после доказанного RCA.

## Out of scope
- check-booking families
- collect/commit booking families
- downstream fact-composition rewrites без evidence, если текущий live path их не показывает
- wording-only edits
- oracle-only taxonomy disagreements

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-parking-owner-grounding-r34d-a922.md`
- `prompts/llm_policy_core.md`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/tests/test_intent.py`
- `docs/REPORTS/2026-03-30-consultant-core-r35f-human-semantic-audit-a922.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `STATE.md`
- `STRUCTURE.md`

## Work mode
- `RCA -> bounded implementation -> replay -> human audit`

## Surfaced family / mechanism-first frame
- Surfaced family label:
  - `parking fact composition regression`
- Broken invariant:
  - when the user explicitly asks for one concrete branch fact and that fact is supported by pack/truth, owner planning must ground that exact fact in `pack_refs` instead of swapping to an adjacent sibling fact (`contact`, `hours`, `location`) and letting the final reply stay faithful to the wrong owner choice.
- Shared mechanism:
  - `branch fact grounding specificity`
- Why this surfaced family belongs to that mechanism:
  - the new `r34d` failure is not the old downstream info-class handoff bug; the wrong meaning is already present in the valid owner payload, and runtime preserves it unchanged.
- Open-world envelope expected to improve:
  - any direct branch-fact question where one concrete info ref is explicitly requested but owner currently under-specifies or swaps it to a sibling branch fact.

## One web search (mandatory before implementation)
- Query: `site:platform.openai.com/docs hallucinations retrieval grounding official OpenAI docs`
- Date/time: `2026-03-30 05:41 Asia/Almaty`
- Sources opened:
  - `https://developers.openai.com/api/docs/guides/retrieval`
- Source quality:
  - official vendor documentation
- Findings:
  - retrieval/grounding quality depends on keeping the most relevant grounded context instead of letting broader adjacent context crowd it out
  - evals should verify that grounded requested facts remain selected all the way to the final answer
- Decision:
  - `reuse/integrate`
  - tighten the owner prompt/contract so explicit branch-fact asks ground the requested fact itself and do not substitute sibling refs from the same cluster
- Rejected variants:
  - `patch only the exact string "Есть ли у вас парковка?"` — violates scenario-patch ban
  - `re-open the old downstream info-class handoff fix as the presumed cause` — contradicted by `r34d` live-path evidence

## Root cause (mandatory)
- Symptom:
  - `dialog 6 / turn 1`: `Есть ли у вас парковка?` -> bot replies with after-hours banner + contact/Instagram and omits the parking fact.
- Minimal reproduction:
  - replay `a922-practical-proof-20260330-r34d`
  - `responses.jsonl` / `trace_bundle.jsonl`, `dialog_id=6`, `turn_index=1`
- Evidence:
  - `/tmp/booking_quality/a922-practical-proof-20260330-r34d/responses.jsonl`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r34d/trace_bundle.jsonl`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r34d/manual_audit_workspace.json`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r34d/family_registry.json`
  - `/tmp/booking_quality/a922-practical-proof-20260330-r33/trace_bundle.jsonl`
  - `prompts/llm_policy_core.md`
  - `truffles-api/app/services/intent_service.py`
- Five Whys:
  1. Why does the final reply omit parking and answer with contact? Because the visible reply stays aligned with `intent=contact`, `source=llm_policy_core`, `info_sections=["contact"]`.
  2. Why does runtime answer with contact? Because the valid owner payload already chooses `pack_refs=["contact"]` and `intent="other"` for the parking question.
  3. Why do validator/guard layers not recover parking? Because capability validation allows `info.contact`, there is no fallback/degrade, and downstream runtime preserves the owner plan unchanged.
  4. Why can owner legally choose `contact` for an explicit parking ask? Because the owner contract currently allows broad sibling branch refs under one `info` cluster but does not require the explicitly requested concrete fact to stay in `pack_refs`; the reason text itself shows the ambiguity (`parking/contact`).
  5. Why is this a mechanism-level family? Any explicit concrete branch-fact ask can drift to a sibling fact if the owner contract does not enforce specificity within the branch info cluster.
- Root cause statement:
  - the active policy-core owner contract under-specifies branch-fact specificity, so on an explicit parking question the owner can emit a valid `info` payload with sibling `pack_refs=["contact"]`; runtime then preserves that wrong owner meaning unchanged into the final reply.
- Fix mechanism:
  - strengthen the policy-core prompt/contract so that when one explicit concrete branch fact is requested, owner must ground that fact in `pack_refs` and must not substitute a sibling branch fact unless the user also asked for it.

## Exact path map
1. `input`
   - `dialog 6 / turn 1`: `turn_text="Есть ли у вас парковка?"`
2. `owner output`
   - valid owner payload with `intent="other"`, `action="fact"`, `tool_action="info"`, `pack_refs=["contact"]`, `goal="info"`, `subject_kind="branch"`, `resolution_mode="policy_fact"`, `capability="other"`
   - owner reason text: `Пользователь спрашивает про парковку; это справочная информация о локации/контактах, требуются данные через tool info (parking/contact).`
3. `validator / guard`
   - `capability_check` allows `fact_scope=info.contact`
   - `llm_policy_plan_delta` is `match`
   - `policy_core_mode=policy_core`
   - no validation error, no override, no rescue, no degrade
4. `fallback / degrade`
   - none
5. `final response`
   - `decision_meta.intent="contact"`
   - `decision_meta.action="reply"`
   - `decision_meta.source="llm_policy_core"`
   - visible reply: `Телефон в карточке салона не указан. Instagram: https://instagram.com/mira_beauty_kz.`
6. `trace/meta evidence`
   - `responses.jsonl`: `decision_meta.info_sections=["contact"]`, `fact_source="truth"`
   - `trace_bundle.jsonl`: `llm_policy_core fact -> pack_refs=["contact"] -> capability_contract policy_fact -> info_class reply intent=contact -> fact_resolver resolved`
   - compare replay `r33`: same runtime/core path produced `pack_refs=["parking"]` and final `info_sections=["address","hours","parking"]`, proving the current `r34d` miss originates before downstream handoff
7. `layer classification`
   - `owner_error`

## Required RCA questions
1. Where exactly is the user fact mention first represented in the live path?
   - in the raw input text and then in the owner reason text mentioning `parking/contact`; the first structured semantic representation is the owner payload, which incorrectly grounds `pack_refs=["contact"]`.
2. What exact structured owner output is produced for the failing turn?
   - `intent="other"`, `action="fact"`, `tool_action="info"`, `pack_refs=["contact"]`, `goal="info"`, `subject_kind="branch"`, `capability="other"`, `resolution_mode="policy_fact"`, `confidence=0.2`.
3. Does any validator/projector/guard mutate or demote that meaning?
   - no; runtime preserves the owner choice unchanged.
4. If no downstream mutation exists, what owner contract/prompt/context gap explains the failure?
   - the prompt/contract does not require the explicitly requested concrete branch fact to remain in `pack_refs`; sibling branch facts stay allowed, so owner can output `contact` for a parking ask.
5. Is this a vocabulary issue, context issue, prompt issue, resolver issue, or pack grounding issue?
   - owner prompt/contract issue with branch-fact grounding specificity.

## Plan
1. Freeze RCA in this TP with exact artifacts and one allowed layer classification.
2. Add focused deterministic coverage for branch-fact specificity in the owner prompt contract.
3. Implement one bounded owner-contract fix in `prompts/llm_policy_core.md` and fallback prompt sync.
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
- `python3 -m py_compile truffles-api/app/services/intent_service.py truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "policy_core_prompt_branch_fact_specificity_contract or policy_core_prompt_explicit_booking_service_grounding_contract"`
- `scripts/llm_quality_guarded.sh --mode replay --run-id a922-practical-proof-20260330-r35f --allow-pending-previous --allow-repeat-fingerprint -- --base-url http://127.0.0.1:18086 --client-slug demo_salon --scenarios-file /tmp/booking_quality/a922-practical-proof-20260330-r34d/scenarios.json --baseline-summary /tmp/booking_quality/a922-practical-proof-20260330-r34d/summary.json --count 10 --include-media --tool-hooks auto --reset-before-dialog --jid-mode unique --skip-outbox --judge-mode all --quality-lane dev --run-economy-gate warn --fail-on-thresholds --max-failures 20`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r35f --status done --strict-artifacts --analyst a922 --human-semantic-valid false --human-semantic-summary "r35f closes the re-opened parking owner-grounding family on the visible path, but the replay remains human-semantic amber because location and parking replies are still broader than needed while the deterministic contract lane stays red on secondary oracle/validation residue" --root-cause "parking owner-grounding family is closed as scoped: dialog 6 now grounds parking in owner output and surfaces the parking fact again on the visible path" --root-cause "fact replies for location and parking still over-compose adjacent branch facts, so the visible lane remains weak even without an outright fail turn" --root-cause "dialog 9 turn 2 still carries secondary contract residue: owner hands off under handoff_not_allowed and runtime overrides to a collect prompt, leaving the deterministic lane red even though the visible reply is product-acceptable" --next-step "update the practical truth to r35f and mark the re-opened parking family closed as scoped" --next-step "if continuing product work, take the next mechanism-first block as fact over-composition on location/parking replies" --next-step "keep dialog 9 turn 2 contract residue separate from product-path blocker claims" --oracle-judge-alignment conflicted --oracle-winner contract --oracle-resolution-summary "Contract-first arbitration applied; the replay has no clear human-semantic fail turns, but location/parking broadness remains weak and dialog 9 turn 2 keeps secondary contract-red residue under an acceptable visible reply." --notes "Full turn-by-turn human review completed against responses.jsonl and trace_bundle.jsonl; r35f is the current truth input for this block." --pretty`
- `git diff --check`

## Evidence
- this TP with exact RCA and one web search
- focused deterministic test output
- fresh replay artifact bundle: `/tmp/booking_quality/a922-practical-proof-20260330-r35f/{summary.json,brief.md,scenarios.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json,manual_audit_workspace.md,manual_audit_workspace.json,family_registry.json,judge_conflicts.jsonl,run_manifest.json}`
- human semantic report: `docs/REPORTS/2026-03-30-consultant-core-r35f-human-semantic-audit-a922.md`
- `STATE.md` current-truth update

## Rollback
- Revert the bounded owner-contract prompt change and accompanying prompt-contract tests as one block if replay shows other direct branch-fact asks regress or if contact/location questions lose their intended grounding.

## No-go
- No dialog-id or wording patching.
- No deterministic post-hoc semantic rewrite for `parking`.
- No new architecture claim without exact path evidence.
- No product-green claim without replay + full human semantic audit.
- No claim that a second semantic owner was proven.

## Риски/блокеры
- Tightening owner specificity too narrowly could over-constrain multi-fact branch questions (`адрес и парковка`, `телефон и адрес`).
- Fresh replay may close parking but leave the lane red because of other weak families.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- location/parking replies still over-compose adjacent sections on some acceptable turns
- `dialog 9 / turn 2` still carries secondary contract-red residue even though the visible reply is acceptable
- oracle/evaluator taxonomy drift still leaves some acceptable turns strict-red
### Why not in this block
- This block is explicitly scoped to the owner-side branch-fact grounding specificity family only.
### Risk if deferred
- Practical/product closure remains open even though the parking miss itself is fixed on the visible path.
### Linked follow-up Task Package(s)
- next: fact over-composition on location/parking replies if it remains the next visible weak family after truth update
- next: secondary booking-verification contract residue if it ever becomes user-visible
### Expiry/trigger to stop deferral
- before any practical/product closure claim

## Next-block contract (mandatory)
### Next block objective
- if this block closes as scoped, take `fact over-composition on location/parking replies` from the fresh replay and translate it into `broken invariant + shared mechanism`
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
- none; `r35f` establishes the active visible weak family.
### Owner role for closure
- `Brain/Architect`

## Outcome
- Fresh replay truth for this block: `a922-practical-proof-20260330-r35f`
- Deterministic checks:
  - `python3 -m py_compile truffles-api/app/services/intent_service.py truffles-api/tests/test_intent.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "policy_core_prompt_branch_fact_specificity_contract or policy_core_prompt_explicit_booking_service_grounding_contract"` -> `2 passed`
- Fresh replay + audit:
  - `scripts/llm_quality_guarded.sh --mode replay --run-id a922-practical-proof-20260330-r35f --allow-pending-previous --allow-repeat-fingerprint -- ...` -> `infra_valid=true`, `semantic_valid=false`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260330-r35f --status done --strict-artifacts --analyst a922 ...` -> `done`
- Human audit verdict:
  - `dialogs 8 pass / 2 weak / 0 fail`
  - `turns 13 pass / 2 weak / 0 fail`
- Family verdict:
  - `parking owner-grounding` is `closed as scoped`
- Closure evidence:
  - `dialog 6 / turn 1` owner output now grounds `intent="parking"` with `pack_refs=["parking"]`
  - the visible reply now includes `Парковка: Бесплатная парковка во дворе, обычно 5–6 мест.`
  - runtime preserves the owner-grounded parking meaning instead of substituting sibling `contact`
- Current truth impact:
  - practical/product closure remains open because `r35f` is still human-semantic amber on `fact over-composition on location/parking replies`
  - deterministic contract lane remains red on secondary oracle/validation residue, including `dialog 9 / turn 2`
