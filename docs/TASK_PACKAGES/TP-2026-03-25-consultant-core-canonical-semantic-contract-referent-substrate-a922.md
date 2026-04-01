# TP-2026-03-25 Consultant Core Canonical Semantic Contract + Referent Substrate A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-CANONICAL-SEMANTIC-CONTRACT-REFERENT-SUBSTRATE-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `d30f4674`, `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-active-time-specialist-followup-continuity-policy-context-repair-a922.md`
- `UNLOCKS`: bounded local proof that the active semantic contract is preserved across policy-core, continuity, tools, grounding, and trace/meta without scenario logic

## Название/цель
Закрыть следующий системный дефект после continuity repair: активный runtime path still lacks one canonical semantic contract for grounded referents and active question semantics. This block lands one shared semantic contract slice so the same grounded meaning is represented consistently in policy-core output, persisted state, tool execution context, pack-grounding evidence, and trace/meta.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `prompts/llm_policy_core.md`
- `truffles-api/app/schemas/intent.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`

## FACT pre-check (before implementation)
- `git log --oneline -3` matches the instructed head: `d30f4674`, `f6017fc5`, `8350f0f2`.
- `git status --short --branch` is clean on `feat/2026-03-15-consultant-core-governance-lock-a922`.
- Live bounded evidence on conversation `55cfaab1-cbf2-468d-a974-2474f4d786c4` still shows the repaired followup family on turn `Можно выбрать Айгерим?`: `decision_meta.action=booking_prompt`, `tool_decision=datetime`, `expected_reply_type=time`, `pending_question_target=specialist`, `active_question_relation=referent_followup`.
- The same live conversation also shows the remaining substrate drift in persisted runtime state: `consultant_runtime.dialog_state.current_referents.service="svc:manicure"` while booking/tool layers still use human service labels like `Маникюр`.
- Current code mismatch is cross-layer, not scenario-local:
  - policy-core emits semantic fields + `entity_refs`
  - schema normalizes them partially and drops display labels
  - runtime continuity persists only fragments of that meaning
  - tool contracts still speak `service_query` / `specialist_name`
  - pack-grounding emits `id/type/label` but active runtime stores only lossy strings
  - trace/meta mostly expose execution remnants, not the canonical semantic contract

## One web search (mandatory before implementation)
- **Query (exact):** `OpenAI structured outputs JSON schema official docs`
- **Date/time (local):** 2026-03-25 18:19:37 +05
- **Sources opened (from this query):**
  - OpenAI official docs, `Structured outputs` — `https://platform.openai.com/docs/guides/structured-outputs`
- **Existing solutions found:** OpenAI structured outputs require a stricter JSON-schema contract than the current loose response-format path; schema design should encode the canonical payload directly instead of relying on post-hoc parsing/repair.
- **Decision:** reuse the existing policy-core structured-output path, but tighten it to a strict canonical semantic contract and make referent semantics first-class in the runtime path instead of compressing them into lossy strings.
- **Rejected options:**
  - runtime semantic repair after LLM output
  - phrase/regex recovery for specialist/service followups
  - booking-only slot rename without shared contract migration
- **Source quality:** official OpenAI primary source

## Root cause (mandatory)
- **Symptom:** cross-layer semantic drift remains even after the bounded followup continuity fix; active runtime preserves only part of the meaning and rewrites grounded referents into lossy values (`svc:manicure` vs `Маникюр`).
- **Minimal reproduction:** inspect `prompts/llm_policy_core.md`, `intent.py`, runtime state writing/loading in `dialog_state_service.py`, live conversation `55cfaab1-cbf2-468d-a974-2474f4d786c4`, and pack-grounding/tool contracts.
- **Evidence:**
  - `prompts/llm_policy_core.md`
  - `truffles-api/app/schemas/intent.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/services/tool_registry_service.py`
  - `truffles-api/app/services/pack_runtime_service.py`
  - live SQL evidence from `public.conversations` / `public.messages` for conversation `55cfaab1-cbf2-468d-a974-2474f4d786c4`
- **Five Whys (or equivalent):**
  1. Why does meaning drift across turns? Because policy-core emits semantic contract pieces that are not preserved as one object.
  2. Why are they not preserved? Because runtime/state keeps only `expected_reply_type`, target/relation fragments, and stringified referents.
  3. Why are referents lossy? Because schema/runtime accept `entity_refs` but drop display labels and then persist `entity_id` or raw strings depending on the source layer.
  4. Why do tools/grounding diverge? Because tool contracts still consume ad-hoc strings (`service_query`, `specialist_name`) while pack-grounding speaks entity refs with ids/types/labels.
  5. Why does this remain open-world fragile? Because no single canonical semantic contract spans policy output, continuity, execution context, grounding, and observability.
- **Root cause statement:** the active runtime path still lacks one canonical semantic contract object; semantic referents and active-question semantics are flattened differently in each layer, so grounded meaning becomes lossy and inconsistent as it crosses policy-core, state, tools, grounding, and trace/meta.
- **Fix mechanism:** define one strict semantic contract slice, preserve grounded referents as first-class payloads with stable ids + human values, persist that contract through dialog state, pass it into tool execution context, and expose it in trace/meta.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `entity_refs` field in policy-core output
  - existing `DialogStateService` canonical referent storage
  - existing structured-output path in `intent_service.route_llm_policy_core()`
  - existing old semantic-arbiter contract shape from webhook decision path as a compatibility reference only
- **External reuse:** OpenAI official structured-output constraints only
- **Why not reinvent the wheel:** the repo already has the semantic tokens and referent notions; the defect is that the active runtime path does not preserve them as one canonical payload.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** 2
- **Code dominance:** `on`
- **Override token:** `none`
- **Why this profile fits:** this block changes the active core contract, state persistence, and observability in one bounded runtime slice.

## Invariant
- Policy-core remains the only semantic owner.
- No new semantic regex/phrase branching in runtime core.
- Deterministic code may validate, persist, project, or transport the semantic contract, but must not reinterpret user meaning.
- No booking-only or language-only special casing.

## Scope
- tighten policy-core structured output schema to a strict canonical semantic contract envelope
- preserve first-class referent semantics (`entity_id` + human value + type/source`) in the active runtime path
- persist the active semantic contract in runtime state / continuity
- pass the same contract into tool execution context and emit it in trace/meta
- add targeted tests for this contract slice

## Out of scope
- retrieval engine changes
- acceptance baseline refresh / full lock replay
- legacy router cleanup outside the active runtime path
- full multi-pack open-world closure proof

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-semantic-contract-referent-substrate-a922.md`
- `prompts/llm_policy_core.md`
- `truffles-api/app/schemas/intent.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`

## Plan (1..N)
1. Define the canonical semantic contract slice and tighten the policy-core structured-output/schema contract around it.
2. Persist that contract through active runtime state and preserve referent bundles without losing human values.
3. Pass the same contract into tool execution context and surface it in trace/meta.
4. Add/update focused tests for schema validation, runtime persistence, and trace/meta truthfulness.
5. Run deterministic checks and the mandated local suites.

## DoD
- policy-core output is validated against one strict semantic contract shape
- active runtime state preserves the semantic contract and grounded referents without lossy id-only rewriting
- tool execution context receives the same semantic contract slice
- decision trace/meta expose the canonical contract instead of only execution leftovers
- one surfaced family is closed because shared contract continuity is truthful, not because of scenario logic

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/schemas/intent.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/consultant_runtime.py truffles-api/app/core/turn_planner.py truffles-api/app/core/turn_executor.py truffles-api/app/services/intent_service.py truffles-api/app/services/tool_registry_service.py truffles-api/tests/test_intent.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_demo_salon_eval.py`

## Evidence
- git diff / commit
- targeted test output
- required local suites output
- live SQL/runtime evidence for conversation `55cfaab1-cbf2-468d-a974-2474f4d786c4`
- updated `STATE.md` entry before merge if closure is claimed

## Rollback
- `git revert <commit>` for the bounded fix commit
- if runtime evidence shows adjacent semantic regression, stop and reopen RCA from the new artifacts instead of layering patches

## No-go
- no semantic regex/phrase repair layer
- no second semantic owner
- no booking-only local optimization presented as the substrate fix
- no acceptance lock/full before local contract closure
- no silent schema aliasing that rewrites semantic meaning after LLM output

## Risks/Blockers
- targeted tests may encode the previous lossy referent shape
- stricter structured-output schema may expose pre-existing contract drift in prompts/tests
- full required suites still depend on healthy local runtime and API key availability

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: the system still has multiple legacy semantic helpers outside the active runtime path (`routers/webhook/decision.py`, old reasoning helpers).
- `Why not in this block`: the task is bounded to the active runtime path and one canonical contract slice.
- `Risk if deferred`: adjacent non-active paths can continue to speak older semantic dialects until they are migrated or deleted.
- `Linked follow-up Task Package(s)`: next block should either migrate the next active semantic slice onto the same contract or delete the remaining non-active semantic helpers that shadow it.
- `Expiry/trigger to stop deferral`: before claiming full consultant-core substrate closure or open-world robustness.

## Next-block contract (mandatory)
- `Next block objective`: extend the same canonical semantic contract into the next surfaced continuity/tool family or delete the next shadow semantic path that still speaks a different contract.
- `First deterministic check command`: `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k semantic_contract`
- `Blocked-by conditions`: failing required local suites, broken structured-output compatibility, or evidence that tools still receive a different semantic dialect than runtime state.
- `Owner role for closure`: Brain / Top Architect
