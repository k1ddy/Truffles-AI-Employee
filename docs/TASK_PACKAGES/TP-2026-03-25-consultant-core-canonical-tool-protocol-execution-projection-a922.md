# TP-2026-03-25 Consultant Core Canonical Tool Protocol + Execution Projection A922

## Block identity
- `BLOCK_ID`: CONSULTANT-CORE-CANONICAL-TOOL-PROTOCOL-EXECUTION-PROJECTION-A922
- `PARENT_BLOCK_ID`: CONSULTANT-CORE-CONTROLLED-DEMOLITION
- `DEPENDS_ON`: `527d286f`, `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-semantic-contract-referent-substrate-a922.md`, `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-contract-substrate-a922.md`
- `UNLOCKS`: one bounded cross-layer proof that `policy-core -> schema -> executor -> tool boundary -> runtime trace/meta` now speaks one canonical semantic substrate and that legacy `tool_args` semantic carriage is only execution projection

## Название/цель
Убрать оставшийся tool semantic dialect на active consultant-runtime path: policy-core must emit canonical referents directly, schema must validate those referents directly, and executor must deterministically project them into provider args so tool execution no longer depends semantically on legacy `tool_args.service_query` / `tool_args.specialist_*`.

## Canon refs
- `/home/zhan/AGENTS.md`
- `/home/zhan/truffles-main/STATE.md`
- `/home/zhan/truffles-main/STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-active-time-specialist-followup-continuity-policy-context-repair-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-semantic-contract-referent-substrate-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-contract-substrate-a922.md`
- `prompts/llm_policy_core.md`
- `truffles-api/app/schemas/intent.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`

## FACT pre-check (before implementation)
- `git log --oneline -8` matches the instructed chain ending at `527d286f`.
- `git status --short --branch` is clean on `feat/2026-03-15-consultant-core-governance-lock-a922`.
- Current active runtime still carries two tool-facing semantic dialects:
  - policy-core prompt/schema still present `tool_args.service_query`, `tool_args.specialist_name`, `tool_args.specialist_id` as semantic carriers
  - executor/tool boundary still resolves service/specialist meaning from `tool_args` and only uses canonical semantic contract as a bridge/fallback
- Current pack layer still carries its own dialect (`resolver_contract`, `slot_candidates`, legacy `entity_refs`), but active code evidence shows the next highest-leverage cut is tool protocol elimination first because the planner/schema/prompt/executor/tool chain still shares one live legacy carrier family.

## One web search (mandatory before implementation)
- **Query (exact):** `OpenAI structured outputs JSON schema official docs`
- **Date/time (local):** `2026-03-25 20:34:57 +05`
- **Sources opened (from this query):**
  - OpenAI, `Introducing Structured Outputs in the API` — `https://openai.com/index/introducing-structured-outputs-in-the-api/`
  - OpenAI API docs, `Structured model outputs` — `https://developers.openai.com/api/docs/guides/structured-outputs`
- **Existing solutions found:** strict structured outputs support nested schemas with `strict: true` and `additionalProperties: false`, but OpenAI explicitly notes that schema adherence does not remove semantic mistakes inside values; the contract itself must encode the canonical payload directly.
- **Decision:** reuse the existing structured-output path, add canonical referent objects directly to the policy-core payload, and validate/projection consistency at the boundary instead of keeping `tool_args.*` as a parallel semantic language.
- **Rejected options:**
  - keep legacy `tool_args.service_query` / `tool_args.specialist_*` as semantic source-of-truth and only enrich trace/meta
  - add a runtime semantic repair layer that infers service/specialist semantics after LLM output
  - skip direct referent objects and continue relying on loose `entity_refs` + ad hoc executor interpretation
- **Source quality:** official OpenAI primary sources only

## Root cause (mandatory)
- **Symptom:** even after semantic-contract and question-contract work, the active tool boundary still depends on legacy `tool_args` strings for service/specialist semantics, while canonical runtime/state/trace already uses semantic referents.
- **Minimal reproduction:** inspect `prompts/llm_policy_core.md`, `intent_service._build_policy_core_response_format()`, `LlmPolicyCoreOutput` / `validate_tool_args_shape()` in `truffles-api/app/schemas/intent.py`, `TurnExecutor._build_execution_semantic_contract()` / `_execute_fact()`, and `execute_tool_action()` in `truffles-api/app/services/tool_registry_service.py`.
- **Evidence:**
  - `prompts/llm_policy_core.md` still instructs semantic carriage through `tool_args.service_query` / `tool_args.specialist_name`
  - `truffles-api/app/services/intent_service.py` structured-output schema still requires those fields in the policy-core payload
  - `truffles-api/app/schemas/intent.py` still validates key semantic cases through `tool_args.service_query`
  - `truffles-api/app/core/turn_executor.py` still uses `tool_args` as semantic input when building execution semantic contract / calling tools
  - `truffles-api/app/services/tool_registry_service.py` still resolves service/specialist execution from legacy provider-shaped args
- **Root-cause classification (mandatory):**
  - A. tool semantic dialect: `semantic protocol/model` mismatch — chosen for this block
  - B. pack/grounding dialect: `semantic protocol/model` mismatch — deferred; still real after this block
  - C. legacy `expected_reply_*` / `last_question_type` projections: `continuity/state` + `observability` mismatch — deferred after tool slice
  - D. final cross-layer closure proof: `evaluation/process` gap — deferred until after tool slice lands and is verified
- **Five Whys:**
  1. Why do tools still speak a different semantic language? Because policy-core output still treats `tool_args.service_query` / `specialist_*` as valid semantic carriers.
  2. Why is that a real protocol mismatch? Because runtime/state/trace already preserve canonical semantic referents separately, so service/specialist meaning exists in two co-equal dialects.
  3. Why does executor preserve the mismatch? Because it still reads/merges service/specialist meaning from `tool_args` instead of projecting provider args from canonical referents.
  4. Why does schema allow the mismatch? Because the structured-output contract validates tool-shaped strings but does not require a canonical referent object as the semantic source-of-truth.
  5. Why does this keep resurfacing as residual failures? Because the semantic owner can output meaning in one language while the tool layer executes in another, forcing compatibility bridges instead of one canonical substrate.
- **Root cause statement:** the remaining active defect is a cross-layer semantic protocol mismatch: policy-core, schema, executor, and tool boundary still preserve a second semantic language inside legacy `tool_args.*`, so service/specialist meaning is not owned and transported by one canonical referent contract end-to-end.
- **Fix mechanism:** add direct canonical referent objects to the policy-core payload/schema, persist them in the policy decision semantic contract, deterministically project provider args from that canonical contract in the executor, and demote legacy tool arg carriers to consistency-checked execution projection only.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing `semantic_contract.v1` substrate and `entity_refs`
  - existing `DialogStateService` / `ConsultantRuntime` canonical memory path
  - existing structured-output path in `intent_service.route_llm_policy_core()`
  - existing tool execution seam in `TurnExecutor` / `execute_tool_action()`
- **External reuse:** OpenAI structured-output docs only
- **Decision:** `reuse -> integrate -> build`
- **Why not pure reuse:** the repo already has canonical semantic contract storage, but policy-core output and executor projection are missing the direct referent payload needed to remove `tool_args` as semantic truth.

## Invariant
- Policy-core remains the only semantic owner.
- Deterministic layers may validate, persist, project, and execute canonical meaning; they must not reinterpret user text.
- No new regex/phrase branching in core.
- No booking-only or surfaced-phrase fix masquerading as architecture work.

## Scope
- add canonical referent payload to policy-core structured output and prompt
- validate service/specialist semantics directly from canonical referents in `intent.py`
- project provider args from canonical referents at the executor/tool boundary
- make active runtime/state/trace/meta carry the same canonical referent contract through execution
- add targeted tests proving tool execution no longer depends semantically on legacy `tool_args.service_query` / `tool_args.specialist_*`

## Out of scope
- pack/grounding dialect migration (`resolver_contract`, `slot_candidates`, pack-native `entity_refs`)
- legacy router/runtime cleanup outside the active consultant-runtime path
- retrieval engine changes
- acceptance baseline reset / full lock replay
- final open-world closure artifact

## Touch-list (files/tables)
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-tool-protocol-execution-projection-a922.md`
- `prompts/llm_policy_core.md`
- `truffles-api/app/schemas/intent.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_demo_salon_eval.py`

## Plan (1..N)
1. Add canonical `referents` payload to the policy-core prompt/schema/output validator and make service/specialist contract checks depend on canonical referents rather than legacy `tool_args`.
2. Persist those referents inside the active `semantic_contract.v1` policy decision / runtime state path and keep legacy execution shadows consistency-checked only.
3. Add deterministic executor projection from canonical referents to provider args (`service_query`, `specialist_id`, `specialist_name`) before `tool_registry_service.execute_tool_action()`.
4. Remove active semantic dependence on legacy `tool_args` in the executor/tool seam and update trace/meta evidence to expose canonical referents + projected execution args.
5. Add targeted regressions for `policy-core -> schema`, `semantic_contract -> tool execution projection`, and `trace/meta carries canonical referents`.
6. Run the mandated deterministic + local realism suites; if they pass, update `STATE.md` before merge and produce one bounded closure fact for the tool slice.

## DoD
- canonical referents are first-class in the policy-core structured output
- schema validates service/specialist semantic cases directly from canonical referents
- executor projects provider args from canonical referents and does not require legacy `tool_args.service_query` / `tool_args.specialist_*` as semantic truth
- trace/meta expose canonical referents together with execution projection evidence
- at least one real tool-facing failure family is shown closed because canonical referents now cross the planner/executor/tool boundary end-to-end

## Work mode (mandatory)
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/schemas/intent.py truffles-api/app/services/intent_service.py truffles-api/app/core/turn_planner.py truffles-api/app/core/turn_executor.py truffles-api/app/core/consultant_runtime.py truffles-api/app/core/dialog_state_service.py truffles-api/app/services/tool_registry_service.py truffles-api/tests/test_intent.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_demo_salon_eval.py`
- targeted proof commands:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k 'policy_core.*referent or response_format_is_strict_and_canonical'`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k 'tool_execution_projection or semantic_contract'`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k 'semantic_contract or referent_followup'`

## Evidence
- git diff + single commit
- targeted unit/contract test outputs
- required local realism suite outputs
- trace/meta proof from the targeted runtime tests showing canonical referents + projected provider args
- updated `STATE.md` entry before merge because this block changes active core behavior/contracts

## Token / run budget (mandatory for expensive suites)
- **Max expensive runs:** `0` extra replays before deterministic closure; this block uses only the mandatory local suites unless a deterministic failure forces RCA.
- **Stop condition:** any failing mandatory suite or any new surfaced first-fail family outside the tool protocol slice.
- **Escalation path:** if the mandatory local suites expose a different first-fail family, stop and publish that evidence instead of stretching scope.

## Release safety (mandatory for non-doc changes)
- **Strategy:** active worktree only; no new worktree, no new architecture pivot
- **Go/no-go signals:** targeted tool-contract tests green, mandatory local suites green, trace/meta evidence shows canonical referents plus projected provider args
- **Rollback:** `git revert <commit>` for the bounded tool-protocol migration commit
- **Post-release monitoring window:** next block may only move to pack/grounding or legacy projection cleanup after this tool slice is green

## Rollback
- `git revert <commit>` for the single bounded recovery commit
- if execution regressions show adjacent semantic drift, stop and reopen RCA instead of reintroducing legacy semantic carriers as a fallback

## No-go
- no new semantic regex/phrase routing
- no runtime semantic repair layer
- no pack-layer rewrite in this block
- no keeping legacy `tool_args.service_query` / `tool_args.specialist_*` as semantic source-of-truth
- no closure claim based only on green local micro-tests without cross-layer contract evidence

## Risks/Blockers
- shared validators are used by non-active paths; tightening policy-core payload may surface latent drift outside the active runtime seam
- strict nested referent schemas can expose prompt/test fixtures that still assume entity-only payloads
- some compatibility tests may still assert legacy tool-arg shadows and will need explicit migration or reclassification

## Which semantic dialect is being eliminated in this block?
- The active tool semantic dialect: legacy `tool_args.service_query` / `tool_args.specialist_id` / `tool_args.specialist_name` as semantic carriers in the policy-core -> schema -> executor -> tool chain.

## Which layers will speak one language after this block?
- `prompts/llm_policy_core.md`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/schemas/intent.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/tool_registry_service.py` at the execution boundary
- runtime trace/meta emitted from `consultant_runtime`

## Which semantic dialect still remains afterward, if any, and why?
- pack/grounding still has a separate dialect (`resolver_contract`, `slot_candidates`, pack-native `entity_refs`) because this block is bounded to the tool boundary first.
- legacy projection fields (`expected_reply_*`, `last_question_type`) still exist as transport/compatibility surfaces outside full closure and will need a dedicated cleanup/reduction block after tool + pack semantic slices are aligned.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: pack/grounding still emits its own semantic dialect; legacy `expected_reply_*` / `last_question_type` still exist as compatibility projections outside the canonical active runtime seam.
- `Why not in this block`: this block is bounded to the highest-leverage active mismatch first: the tool/executor contract.
- `Risk if deferred`: pack or compatibility layers can still reintroduce drift even after the tool boundary is canonicalized.
- `Linked follow-up Task Package(s)`: create the next TP for canonical pack/grounding projection onto the same referent substrate, then a separate TP for shrinking/removing legacy projection fields as source-of-truth.
- `Expiry/trigger to stop deferral`: before any claim that consultant-core now has one semantic protocol across owner/state/tools/packs/trace end-to-end.

## Next-block contract (mandatory)
- `Next block objective`: eliminate the pack/grounding dialect by projecting `pack_runtime_service` outputs into the same canonical referent/provenance substrate and then reassess legacy projection shrinkage.
- `First deterministic check command`: `rg -n "resolver_contract|slot_candidates|entity_refs" truffles-api/app/services/pack_runtime_service.py`
- `Blocked-by conditions`: this tool-protocol block not yet green, or mandatory local suites reveal a different first-fail family
- `Owner role for closure`: Brain / Top Architect
