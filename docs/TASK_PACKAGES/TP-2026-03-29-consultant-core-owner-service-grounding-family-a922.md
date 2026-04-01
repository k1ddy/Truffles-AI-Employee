# TP-2026-03-29-consultant-core-owner-service-grounding-family-a922

- Status: `completed`
- Owner: `Hands`
- Date: `2026-03-29`

## Название/цель
Построить exact live-path RCA для family `owner-side booking service grounding regression` из replay `r25`, доказать один слой классификации и только после этого внести bounded family-level fix без scenario patching.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/REPORTS/2026-03-29-consultant-core-r25-human-semantic-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-29-consultant-core-practical-closure-canon-correction-a922.md`
- `/tmp/booking_quality/a922-practical-proof-20260329-r25/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json}`

## Invariant
- Не утверждать и не подразумевать второй semantic owner без exact path evidence.
- Не лечить `dialog 2`, `dialog 8`, `dialog 10` как отдельные сценарии.
- Не добавлять phrase/regex hardcode под `маникюр`, `педикюр`, `стрижка`.
- Не закрывать блок по deterministic checks alone; обязательны fresh replay + full human semantic audit.

## Scope
- Только family `owner-side booking service grounding regression` на explicit-service booking openings из `r25`.
- Exact path reconstruction: `input -> owner output -> validator/guard -> fallback/degrade -> final response -> trace/meta evidence -> layer classification`.
- Один bounded family-level fix после доказанного RCA.

## Out of scope
- `live check-booking collect/fallback residue`
- `parking fact composition regression`
- oracle/action-taxonomy normalization
- wording-only tweaks without root cause

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-29-consultant-core-owner-service-grounding-family-a922.md`
- `docs/REPORTS/2026-03-29-consultant-core-r26c-human-semantic-audit-a922.md`
- `prompts/llm_policy_core.md`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/tests/test_intent.py`
- `STATE.md`
- `STRUCTURE.md`

## Work mode
- `RCA -> bounded implementation -> replay -> human audit`

## One web search (mandatory before implementation)
- Query: `site:rasa.com/docs/rasa/forms pre-filled slot entity ask next empty slot official`
- Date/time: `2026-03-29 18:13 Asia/Almaty`
- Sources opened:
  - `https://legacy-docs-oss.rasa.com/docs/rasa/forms/`
  - `https://legacy-docs-oss.rasa.com/docs/rasa/2.x/forms/`
- Source quality:
  - official vendor documentation
- Findings:
  - active slot-filling should ask for the next empty required slot, not re-ask a slot that was already filled from the user message
  - uniquely grounded entities can fill slots even if that slot was not explicitly requested yet
  - interruptions/unhappy paths should be explicit branches rather than accidental loss of already grounded slot state
- Decision:
  - `reuse/integrate`
  - keep Truffles owner/runtime aligned with the same slot-filling principle: explicit service mentions in booking openings must ground the service slot before the system chooses the next missing slot
- Rejected variants:
  - `special-case manicure/pedicure/haircut strings in runtime` — violates semantic-first/no-scenario-patch canon
  - `weaken replay oracle to tolerate generic service reprompts` — hides a product regression instead of fixing it

## Root cause (mandatory)
- Symptom:
  - `dialog 2 / turn 1`: `Хочу записаться на маникюр` -> bot asks `На какую услугу хотите записаться?`
  - `dialog 8 / turn 1`: `Хочу записаться на педикюр` -> same collapse
  - `dialog 10 / turn 1`: `Хочу записаться на стрижку` -> same collapse
- Minimal reproduction:
  - replay `a922-practical-proof-20260329-r25`
  - exact failing turns above
- Evidence:
  - `docs/REPORTS/2026-03-29-consultant-core-r25-human-semantic-audit-a922.md`
  - `/tmp/booking_quality/a922-practical-proof-20260329-r25/{summary.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json}`
  - `responses.jsonl` / `trace_bundle.jsonl` show the same owner-shaped output on all three openings:
    - `dialog 2 / turn 1`: owner payload already says `slots.service=""`, `next_question="service"`, `resolution_mode="clarify_missing_subject"`, while `entity_refs=[{"entity_id":"svc:manicure","source_ref":"user_message"}]`
    - `dialog 8 / turn 1`: owner payload says `slots.service=""`, `next_question="service"`, `resolution_mode="clarify_missing_subject"`, `entity_refs=[]`
    - `dialog 10 / turn 1`: owner payload says `slots.service=""`, `next_question="service"`, `resolution_mode="clarify_missing_subject"`, `entity_refs=[]`
  - `trace_bundle.jsonl` proves no downstream semantic rewrite:
    - `llm_policy_plan_delta`: `plan_action=collect`, `final_action=collect`, `override_reason_codes=[]`
    - `llm_policy_core`: `validated=true`, `validation_error=None`, `semantic_action_changed=false`, `semantic_tool_action_changed=false`, `semantic_intent_changed=false`
    - `policy_core_mode`: `policy_core`
    - `booking prompt`: `missing_slot=service`, `requested_slot=service`
  - `truffles-api/app/services/intent_service.py:2234` shows policy-core input contains only `message`, `expected_reply_type`, `current_goal`, `slot_state`, `allowed`, and optional memory summary/profile; there is no dedicated current-turn `service_query` field passed into policy-core.
  - `truffles-api/app/services/intent_service.py:1436` shows runtime loads `prompts/llm_policy_core.md` when the file exists, so the checked-in prompt file is the active owner contract.
  - `prompts/llm_policy_core.md:16` lacks an explicit rule that inflected/prepositional booking-service phrases must fill `slots.service` and advance to the next missing slot, while `truffles-api/app/services/intent_service.py:1358` fallback still contains the critical “Treat inflected or prepositional service phrases as explicit service mention” instruction.
  - Local deterministic check proved runtime service validation is not the blocker:
    - `PYTHONPATH=truffles-api python3 - <<'PY' ... _validate_service_slot/_extract_service_hint ... PY`
    - result: `Хочу записаться на маникюр|педикюр|стрижку` resolve to `Маникюр|Педикюр|Стрижка`
- Five Whys:
  1. Why does runtime ask for service again when the user already supplied one? Because owner output already sets `slots.service=""` and `next_question="service"` on the first turn.
  2. Why is the service mention not preserved into the next slot choice? Because policy-core does not convert the explicit service phrase into `slots.service`; at most it emits `entity_refs`, and runtime does not semantically rewrite empty slots from those refs.
  3. Why does runtime keep the bad meaning instead of correcting it? Because validator/arbiter accept the owner payload unchanged (`validated=true`, no semantic override, `policy_core_mode=policy_core`).
  4. Why does the owner choose `clarify_missing_subject` on explicit-service booking openings? Because the active prompt file under-specifies this booking-opening contract: it says “slots contains service if known” but does not explicitly instruct the model to treat inflected booking-service phrases as filled `service` slots and advance to `datetime`.
  5. Why is this a family and not isolated wording drift? Because the same owner output shape repeats across three explicit-service booking openings with different services (`маникюр`, `педикюр`, `стрижка`).
- Root cause statement:
  - The family is an `owner_error`: on first-turn booking openings, the active policy-core prompt/input contract does not reliably force explicit service mentions into `slots.service`, so the semantic owner emits `next_question="service"` / `resolution_mode="clarify_missing_subject"` even when the user already named the service, and runtime preserves that owner output without mutation.
- Fix mechanism:
  - Make one bounded owner-layer fix:
    - update `prompts/llm_policy_core.md` so explicit booking-service mentions, including inflected/prepositional forms, must fill `slots.service` and move `next_question` to the next actually missing slot (`datetime`, then `name`)
    - sync the fallback copy in `truffles-api/app/services/intent_service.py` so the runtime contract does not diverge again
    - add focused deterministic tests that guard the prompt contract for this family

## Exact path map
1. `input`
   - `turn_text`: `Хочу записаться на маникюр|педикюр|стрижку`
2. `owner input envelope`
   - `route_llm_policy_core(...)` receives raw `message`, empty `slot_state`, and memory profile without current-turn service grounding (`truffles-api/app/services/intent_service.py:2234`, `truffles-api/app/routers/webhook/decision.py:13021`)
3. `owner output`
   - `llm_policy_core.payload.action=collect`
   - `llm_policy_core.payload.slots.service=""`
   - `llm_policy_core.payload.next_question="service"`
   - `llm_policy_core.payload.resolution_mode="clarify_missing_subject"`
   - `llm_policy_core.payload.entity_refs` = manicure only on `dialog 2 / turn 1`, empty on dialogs `8` and `10`
4. `validator / guard`
   - payload validates successfully
   - `plan_action == final_action == collect`
   - no semantic override, no rescue rewrite, no degraded fallback
5. `fallback / degrade`
   - none for this family; live path stays in `policy_core_mode=policy_core`
6. `final response`
   - booking prompt chooses `missing_slot=service`
   - outbound text: `На какую услугу хотите записаться? После этого сразу проверю свободное время.`
7. `trace/meta evidence`
   - `decision_meta.action=booking_prompt`
   - `decision_meta.source=llm_policy_core`
   - `decision_meta.expected_reply_type=service_choice`
   - `decision_trace.stage=booking prompt requested_slot=service`
8. `layer classification`
   - `owner_error`

## Required RCA questions
1. Where exactly is the user service mention first represented in the live path?
2. What exact structured owner output is produced for the failing turns?
3. Does any validator/projector/guard mutate or demote that meaning?
4. If no downstream mutation exists, what owner contract/prompt/context gap explains `clarify_missing_subject` on explicit service turns?
5. Is this a vocabulary issue, context issue, prompt issue, resolver issue, or pack grounding issue?

## Plan
1. Read `summary.json` and `manual_audit.*` and isolate the explicit-service family turns.
2. Reconstruct the failing turns from `responses.jsonl` and `trace_bundle.jsonl`; use `dialog-report` only if artifact correlation is insufficient.
3. Prove one layer classification from the allowed set and write one root-cause statement for the family.
4. Add focused deterministic checks only after RCA is proven.
5. Implement one bounded family fix.
6. Run focused checks, fresh replay, and full human semantic audit.
7. Update `STATE.md` / `STRUCTURE.md` with the new practical truth and residual families.

## DoD
- Exact family path is written down with trace/meta evidence.
- One allowed layer classification is proven for the family.
- Fix is family-level and bounded.
- Focused deterministic checks are green.
- Fresh replay is run and a fresh full human semantic audit is completed.
- `STATE.md` records the new practical truth without overclaim.

## Checks
- `python3 -m py_compile truffles-api/app/services/intent_service.py truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "policy_core_prompt_explicit_booking_service_grounding_contract or policy_core_prompt_free_slots_question_keeps_pending_time_contract"`
- `scripts/llm_quality_guarded.sh --mode replay --run-id a922-practical-proof-20260329-r26c --owner-file prompts/llm_policy_core.md --owner-file truffles-api/app/services/intent_service.py --owner-file truffles-api/tests/test_intent.py --quick-check "python3 -m py_compile truffles-api/app/services/intent_service.py truffles-api/tests/test_intent.py" --quick-check "PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k policy_core_prompt_explicit_booking_service_grounding_contract" --allow-pending-previous -- --base-url http://127.0.0.1:18086 --client-slug demo_salon --scenarios-file /tmp/booking_quality/a922-practical-proof-20260329-r25/scenarios.json --baseline-summary /tmp/booking_quality/a922-practical-proof-20260329-r25/summary.json --count 10 --mode llm --min-turns 10 --max-turns 15 --include-media --media-mode text --media-kind photo --scenario-coverage booking,info,interrupt,handoff --batch-size 5 --retry-count 2 --retry-backoff 0.6 --min-wait 0.0 --max-wait 0.15 --jid-mode unique --timeout-profile realistic --timeout 30.0 --poll-timeout 25.0 --poll-interval 0.5 --trace-timeout 25.0 --trace-interval 0.5 --skip-outbox --manager-mode simulate --manager-channel telegram --manager-actions take,resolve --manager-wait 1.0 --pending-mode ack --ack-text "ок" --tool-hooks auto --tool-confirm-text "да" --tool-cancel-text "отмена" --tool-calendar-text "проверь запись" --tool-hook-wait 0.8 --tool-hook-limit 2 --tool-evidence-policy strict --reset-before-dialog --console-env /home/zhan/secrets/console-contract.env --console-mode real --history-max 20 --fail-on-thresholds --fail-on-regression --max-failures 20 --regression-tolerance 0.02 --max-post-llm-semantic-rewrite-rate 0.0 --max-keyword-override-rate 0.0 --lexicon-regex-delta-gate block --delta-gate-base-ref origin/main --hardcode-core-gate block --hardcode-core-base-ref origin/main --run-economy-gate warn --run-economy-base-ref origin/main --manual-audit-gate block --forensic-sla-gate block --oracle-conflict-gate block --secret-transport-gate block --quality-lane dev --scenario-governance-gate block --scenario-governance-registry /tmp/booking_quality/_scenario_governance_registry.json --judge-mode all --judge-sample 0.1 --judge-model gpt-4o-mini --judge-base-url https://api.openai.com --judge-timeout 25.0 --judge-max-tokens 320 --judge-cache-max-entries 5000`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-practical-proof-20260329-r26c --status done --strict-artifacts --analyst a922 --human-semantic-valid false --human-semantic-summary "explicit booking-service grounding no longer collapses on opening turns, but replay r26c stays product-red because booking completion residue, live check-booking collect residue, and parking regression remain" --root-cause "The owner-side explicit-service grounding family is closed on this replay: dialogs 2/8/10 no longer re-ask for service on booking openings." --root-cause "A new/live downstream booking completion residue remains: after service+datetime+name are present, dialog 2 turn 5 still emits a service-choice prompt instead of progressing to booking verification/commit." --root-cause "The pre-existing residual families remain live: dialog 9 still re-asks date/time on check-booking follow-up, and dialog 6 still misses parking in fact composition." --next-step "Treat owner-side explicit-service grounding as closed for this block and update canon truth accordingly." --next-step "RCA the post-name booking completion residue on dialog 2 turn 5 before starting wording or scenario-level edits." --next-step "Keep check-booking collect residue and parking composition explicitly open as residual families." --oracle-judge-alignment conflicted --oracle-winner contract --oracle-resolution-summary "Contract-first arbitration remains required because strict expectation taxonomy still marks several human-correct fact/handoff turns red; parking remains a true failure under both views." --notes "Full turn-by-turn human semantic audit completed. The bounded owner-side service-grounding fix landed, but practical/product closure remains open."`
- `git diff --check`

## Evidence
- updated TP with exact RCA
- focused deterministic test output from `python3 -m py_compile ...` and `pytest -q truffles-api/tests/test_intent.py -k ...`
- fresh replay artifact bundle: `/tmp/booking_quality/a922-practical-proof-20260329-r26c/{summary.json,brief.md,scenarios.json,responses.jsonl,trace_bundle.jsonl,manual_audit.md,manual_audit.json,run_manifest.json}`
- invalid preflight attempts closed via audit so gates are truthful but no longer blocking:
  - `/tmp/booking_quality/a922-practical-proof-20260329-r26/{summary.json,manual_audit.md,manual_audit.json}`
  - `/tmp/booking_quality/a922-practical-proof-20260329-r26b/{summary.json,manual_audit.md,manual_audit.json}`
- human semantic report: `docs/REPORTS/2026-03-29-consultant-core-r26c-human-semantic-audit-a922.md`
- `STATE.md` current-truth update

## Outcome
- Proven family classification: `owner_error`
- Root-cause statement: the active policy-core prompt/input contract under-specified explicit booking-service grounding, so owner output on `r25` treated already supplied services as missing and runtime preserved that owner meaning unchanged
- Bounded fix applied:
  - `prompts/llm_policy_core.md` now explicitly requires inflected/prepositional booking-service mentions to fill `slots.service` and advance to `datetime`
  - `truffles-api/app/services/intent_service.py` fallback prompt is kept in sync with the checked-in owner contract
  - `truffles-api/tests/test_intent.py` guards the prompt contract
- Fresh replay verdict:
  - `r26c`: `infra_valid=true`, `semantic_valid=false`, `human_semantic_valid=false`
  - full audit: `dialogs 5 pass / 2 weak / 3 fail`, `turns 9 pass / 2 weak / 4 fail`
- Family closure verdict:
  - `owner-side booking service grounding regression` is `closed on r26c`
  - practical/product closure is still `open`
- Residual families after this block:
  - `downstream booking completion residue after filled name`
  - `live check-booking collect/fallback residue`
  - `parking fact composition regression`
  - secondary `oracle/action-taxonomy drift`

## Rollback
- Revert the bounded family fix and accompanying deterministic checks as one block if replay proves the regression persists or explicit service grounding degrades elsewhere.

## No-go
- No claim that current evidence proves a second semantic owner.
- No isolated dialog-turn patching.
- No hardcoded service strings in runtime core.
- No product-green claim without replay + full human semantic audit.

## Риски/блокеры
- RCA may show the current suspicion `owner_error` is wrong; the fix target must then move with evidence, not with prior expectation.
- Fresh replay may expose additional weak turns even if the explicit-service family improves.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `live check-booking collect/fallback residue`
- `parking fact composition regression`
- oracle/action-taxonomy drift on otherwise human-correct turns
### Why not in this block
- Current block is limited to one family by canon and user instruction.
### Risk if deferred
- Replay can remain product-red after this family fix.
### Linked follow-up Task Package(s)
- next: check-booking fallback residue family
- next: parking fact composition family
### Expiry/trigger to stop deferral
- Before any practical/product closure claim.

## Next-block contract (mandatory)
### Next block objective
- RCA the surfaced family `downstream booking completion residue after filled name` as the shared mechanism `collect->commit transition when required booking slots are already complete`, where all booking slots are present but runtime still emits a service-choice prompt.
### First deterministic check command
- `python3 ops/diagnose.py dialog-report --date 2026-03-29 --start 19:36:30 --end 19:36:50 --tz Asia/Almaty --conversation-id 7f64887e-2571-4e8b-984f-733ac6895e06 --output -`
### Blocked-by conditions
- post-name booking-completion path not yet reconstructed end-to-end
- fresh replay/audit truth from `r26c` not yet incorporated into the next TP
- scenario-level wording patch temptation instead of family RCA
### Owner role for closure
- `Brain/Architect`
