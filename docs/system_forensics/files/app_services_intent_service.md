# File Analysis: `truffles-api/app/services/intent_service.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/SALVAGEABLE_COMPONENTS.md`
- `docs/system_forensics/ledgers/DO_NOT_REPEAT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: `intent_service.py` is a 3720-line hotspot with 74 top-level functions that mixes the active policy-core owner gateway with retired controller/answer-interpreter paths, LLM hint extractors, regex/phrase semantic shortcuts, domain-anchor heuristics, and hybrid retrieval helpers: `truffles-api/app/services/intent_service.py`, `truffles-api/app/services/intent_service.py:2465`, `truffles-api/app/services/intent_service.py:2546`, `truffles-api/app/services/intent_service.py:2581`, `truffles-api/app/services/intent_service.py:2615`, `truffles-api/app/services/intent_service.py:3270`, `truffles-api/app/services/intent_service.py:3607`.
- `FACT`: The active owner-facing function is `route_llm_policy_core(...)`; it builds the policy-core input envelope, calls the LLM with strict structured output, validates the contract, and then delegates tool binding to `project_policy_tool_binding(...)`: `truffles-api/app/services/intent_service.py:2615`, `truffles-api/app/services/intent_service.py:3091`, `truffles-api/app/services/intent_service.py:3122`, `truffles-api/app/core/policy_tool_projector.py:117`.
- `INFERENCE`: This file is currently the semantic-owner gateway for the active planner path, but it is not a clean owner boundary because it still contains multiple older semantic systems and local repair logic in the same module.

## 2. Why This File Exists
- `FACT`: The file loads and caches controller/plan/policy-core prompts and also provides code-level fallback prompts when files are missing: `truffles-api/app/services/intent_service.py:2165`, `truffles-api/app/services/intent_service.py:2180`, `truffles-api/app/services/intent_service.py:2195`, `truffles-api/app/services/intent_service.py:1980`.
- `FACT`: It constructs the policy-core structured-output JSON schema, compact-input retry envelopes, memory normalization, allowed context, and LLM retry/fallback policy around the owner call: `truffles-api/app/services/intent_service.py:467`, `truffles-api/app/services/intent_service.py:618`, `truffles-api/app/services/intent_service.py:1337`, `truffles-api/app/services/intent_service.py:1844`, `truffles-api/app/services/intent_service.py:2615`.
- `FACT`: It still also exports secondary/retired semantic surfaces (`route_dialogue_controller`, `route_llm_plan`, `interpret_expected_reply`) and regex-driven helpers (`is_human_request_message`, `is_opt_out_message`, `is_frustration_message`, `classify_intent`, `classify_domain_with_scores`): `truffles-api/app/services/intent_service.py:2442`, `truffles-api/app/services/intent_service.py:2465`, `truffles-api/app/services/intent_service.py:2546`, `truffles-api/app/services/intent_service.py:2581`, `truffles-api/app/services/intent_service.py:3147`, `truffles-api/app/services/intent_service.py:3270`.
- `INFERENCE`: Historically this file accumulated every semantic-adjacent LLM and lexical helper, so the active owner path is embedded in a mixed-era module rather than isolated in a dedicated owner package.

## 3. Main Function Families
- `FACT`: Active policy-core structured-output and message-building functions: `_build_policy_core_response_format(...)`, `_build_policy_core_messages(...)`, `_build_policy_core_compact_input(...)`, `_sanitize_policy_core_payload(...)`: `truffles-api/app/services/intent_service.py:467`, `truffles-api/app/services/intent_service.py:611`, `truffles-api/app/services/intent_service.py:618`, `truffles-api/app/services/intent_service.py:679`.
- `FACT`: Active policy-core memory/context normalization and dynamic context assembly: `_normalize_policy_core_memory_profile(...)`, `_build_policy_core_policy_cards(...)`, `_build_policy_core_capability_cards(...)`, `_load_policy_core_consult_catalog(...)`, `_filter_policy_core_fact_refs(...)`, `_build_policy_core_allowed_context(...)`, `_compact_policy_core_context(...)`: `truffles-api/app/services/intent_service.py:1337`, `truffles-api/app/services/intent_service.py:1693`, `truffles-api/app/services/intent_service.py:1718`, `truffles-api/app/services/intent_service.py:1773`, `truffles-api/app/services/intent_service.py:1830`, `truffles-api/app/services/intent_service.py:1844`, `truffles-api/app/services/intent_service.py:1914`.
- `FACT`: Active owner call path lives in `route_llm_policy_core(...)`: prompt load, budget checks, manifest-scoped context assembly, strict `response_format`, retries/timeouts/fallback model, schema validation, pack-ref gate, semantic-frame cleanup, and projector call: `truffles-api/app/services/intent_service.py:2615`, `truffles-api/app/services/intent_service.py:2715`, `truffles-api/app/services/intent_service.py:2761`, `truffles-api/app/services/intent_service.py:3088`, `truffles-api/app/services/intent_service.py:3091`, `truffles-api/app/services/intent_service.py:3122`.
- `FACT`: LLM hint extractors for specialist/customer/service query are separate subpaths with their own response formats and timeouts: `truffles-api/app/services/intent_service.py:827`, `truffles-api/app/services/intent_service.py:989`, `truffles-api/app/services/intent_service.py:1155`.
- `FACT`: Retired semantic-owner functions remain exported but deliberately return errors and warnings: `route_dialogue_controller(...)`, `route_llm_plan(...)`, `interpret_expected_reply(...)`: `truffles-api/app/services/intent_service.py:2546`, `truffles-api/app/services/intent_service.py:2581`, `truffles-api/app/services/intent_service.py:3147`.
- `FACT`: Regex/lexicon/domain-router helpers remain in the same module and are still callable: `is_human_request_message(...)`, `is_opt_out_message(...)`, `is_frustration_message(...)`, `classify_intent(...)`, `classify_domain_with_scores(...)`, `is_strong_out_of_domain(...)`: `truffles-api/app/services/intent_service.py:2442`, `truffles-api/app/services/intent_service.py:2449`, `truffles-api/app/services/intent_service.py:2458`, `truffles-api/app/services/intent_service.py:2465`, `truffles-api/app/services/intent_service.py:3270`, `truffles-api/app/services/intent_service.py:3353`.
- `INFERENCE`: The file groups active owner logic, legacy owner logic, lexical shortcuts, and retrieval heuristics together, which makes its architectural boundary impure even when the active path is clearer than before.

## 4. Active Callers And Usage Surface
- `FACT`: The active planner path calls `route_llm_policy_core(...)` directly from `TurnPlanner.plan(...)`: `truffles-api/app/core/turn_planner.py:166`, `truffles-api/app/services/intent_service.py:2615`.
- `FACT`: `validate_llm_policy_core_output(...)` is supplied by the external schema contract in `app/schemas/intent.py`, not by this service: `truffles-api/app/schemas/intent.py:779`, `truffles-api/app/services/intent_service.py:3091`.
- `FACT`: Tool binding after owner output is delegated outside this file to `project_policy_tool_binding(...)`: `truffles-api/app/core/policy_tool_projector.py:117`, `truffles-api/app/services/intent_service.py:3122`.
- `FACT`: Legacy webhook/router surfaces still depend on the regex/secondary helpers in this file: `truffles-api/app/routers/webhook/decision.py:637`, `truffles-api/app/routers/webhook/decision.py:661`, `truffles-api/app/routers/webhook/decision.py:3073`, `truffles-api/app/routers/webhook/decision.py:6988`, `truffles-api/app/routers/webhook/booking.py:266`, `truffles-api/app/routers/webhook/pending.py:353`, `truffles-api/app/routers/webhook/guards.py:390`, `truffles-api/app/services/state_service.py:910`.
- `INFERENCE`: The active semantic owner path is concentrated in `TurnPlanner -> route_llm_policy_core`, but the file still has many live dependencies from frozen/legacy webhook surfaces. That complicates extraction.

## 5. Active Owner Boundary Inside This File
- `FACT`: `route_llm_policy_core(...)` is the active owner gateway used by `TurnPlanner`; it builds a `policy_input` envelope with `task`, `message`, `allowed`, optional `context`, and optional `memory`: `truffles-api/app/services/intent_service.py:2715`, `truffles-api/app/services/intent_service.py:2724`, `truffles-api/app/services/intent_service.py:2730`.
- `FACT`: The owner envelope is not caller-hardcoded at the planner callsite anymore; `route_llm_policy_core(...)` itself calls `_build_policy_core_allowed_context(...)` to assemble the tool/fact/card context: `truffles-api/app/services/intent_service.py:2715`, `truffles-api/app/core/turn_planner.py:166`.
- `FACT`: Strict response-format schema is constructed inside this file and passed to `llm.generate(...)` as `response_format`: `truffles-api/app/services/intent_service.py:467`, `truffles-api/app/services/intent_service.py:2761`, `truffles-api/app/services/intent_service.py:2827`, `truffles-api/app/services/intent_service.py:2975`.
- `FACT`: After raw JSON is parsed, the file sanitizes payload shape, validates it with `validate_llm_policy_core_output(...)`, enforces pack-ref allowlist, and only then calls the external projector: `truffles-api/app/services/intent_service.py:3088`, `truffles-api/app/services/intent_service.py:3091`, `truffles-api/app/services/intent_service.py:3109`, `truffles-api/app/services/intent_service.py:3122`.
- `FACT`: `tool_args` is explicitly stripped before schema validation in `_sanitize_policy_core_payload(...)` and only reintroduced after projection from `project_policy_tool_binding(...)`: `truffles-api/app/services/intent_service.py:679`, `truffles-api/app/services/intent_service.py:682`, `truffles-api/app/services/intent_service.py:3139`.
- `INFERENCE`: This is a real improvement toward the target architecture: owner output is closer to semantic frame + capability decision, while tool binding is downstream. But the boundary is still not fully pure because this same file also contains local semantic cleanup and schema/domain enums.

## 6. Owner Input / Context Assembly
- `FACT`: `_build_policy_core_allowed_context(...)` is the core owner-input assembler. It uses runtime capabilities, capability-manifest decisions, consult playbooks, and tool registry actions to build:
  - allowed `tool_actions`
  - allowed `info_refs`
  - allowed `consult_refs`
  - dynamic `context.capability_cards`
  - dynamic `context.policy_cards`
  - dynamic `context.consult_cards`
  Refs: `truffles-api/app/services/intent_service.py:1844`, `truffles-api/app/services/intent_service.py:1851`, `truffles-api/app/services/intent_service.py:1855`, `truffles-api/app/services/intent_service.py:1874`, `truffles-api/app/services/intent_service.py:1891`, `truffles-api/app/services/intent_service.py:1906`.
- `FACT`: Fact refs are filtered through capability-manifest decisions rather than blindly accepted: `truffles-api/app/services/intent_service.py:1830`, `truffles-api/app/services/intent_service.py:1861`, `truffles-api/app/services/intent_service.py:1872`.
- `FACT`: Tool actions are filtered through manifest/tool-protocol decisions before they become owner-visible actions: `truffles-api/app/services/intent_service.py:1851`, `truffles-api/app/services/intent_service.py:1887`.
- `FACT`: Memory profile normalization carries canonical surfaces such as `pending_question_contract`, `semantic_contract`, `consult_state`, `slot_state`, and `active_goal` into owner input: `truffles-api/app/services/intent_service.py:1337`, `truffles-api/app/services/intent_service.py:1378`, `truffles-api/app/services/intent_service.py:1460`, `truffles-api/app/services/intent_service.py:1628`.
- `INFERENCE`: Capability-manifest-centered growth has started here, but the assembly is still centralized and partially hardcoded inside one core file rather than being fully data-driven.

## 7. Hardcoded / Non-Manifest Owner Vocabulary Still In This File
- `FACT`: `_POLICY_CORE_DEFAULT_INFO_REFS` is a hardcoded default fact list (`pricing`, `hours`, `duration`, `location`, `parking`, `promotions`, `master`, `contact`): `truffles-api/app/services/intent_service.py:1985`.
- `FACT`: `_POLICY_CORE_GENERIC_TOOL_ACTIONS` is a hardcoded generic action list (`info`, `consult`, `booking`, `handoff`, `collect`): `truffles-api/app/services/intent_service.py:1996`.
- `FACT`: `_build_policy_core_response_format(...)` hardcodes enums for intents, actions, subject kinds, capability names, temporal scopes, resolution modes, pending-question acts/targets, and active question relations: `truffles-api/app/services/intent_service.py:467`, `truffles-api/app/services/intent_service.py:521`, `truffles-api/app/services/intent_service.py:544`, `truffles-api/app/services/intent_service.py:548`, `truffles-api/app/services/intent_service.py:561`, `truffles-api/app/services/intent_service.py:573`, `truffles-api/app/services/intent_service.py:584`, `truffles-api/app/services/intent_service.py:586`.
- `FACT`: `POLICY_CORE_PROMPT_FALLBACK` hardcodes detailed semantic instructions and business examples directly in code, including `master_query`, `calendar.get_booking` follow-up behavior, and specialist-follow-up semantics: `truffles-api/app/services/intent_service.py:2000`, `truffles-api/app/services/intent_service.py:2112`, `truffles-api/app/services/intent_service.py:2131`.
- `INFERENCE`: The file is partially manifest-aware, but it still owns too much policy vocabulary and semantic contract surface in code.

## 8. Deterministic Semantic Cleanup / Rewrite Inside Owner Gateway
- `FACT`: `_sanitize_policy_core_payload(...)` performs local semantic cleanup before schema validation. It removes `tool_args`, converts `tool_action` -> `tool_action_hint`, and contains a specific rewrite for `calendar.get_booking` name-followup to drop stale `pending_question_*` fields: `truffles-api/app/services/intent_service.py:679`, `truffles-api/app/services/intent_service.py:709`.
- `FACT`: `_build_policy_core_pending_contract_from_expected_reply_type(...)` constructs pending-question semantics from legacy `expected_reply_type` if `memory_profile` lacks a canonical pending contract: `truffles-api/app/services/intent_service.py:1950`, `truffles-api/app/services/intent_service.py:2698`.
- `FACT`: `route_llm_policy_core(...)` compacts or retries the owner input and can fall back from structured output to plain generation if provider/request compatibility fails: `truffles-api/app/services/intent_service.py:2761`, `truffles-api/app/services/intent_service.py:2855`, `truffles-api/app/services/intent_service.py:2881`, `truffles-api/app/services/intent_service.py:2986`, `truffles-api/app/services/intent_service.py:3006`.
- `INFERENCE`: The active owner gateway still contains deterministic repair and fallback policy. Some of this is transport/schema hygiene, but some of it remains semantic enough to matter architecturally.

## 9. Legacy / Secondary Semantic Surfaces Still Present
- `FACT`: `route_dialogue_controller(...)`, `route_llm_plan(...)`, and `interpret_expected_reply(...)` are explicitly retired, but they remain in the file and on import surfaces: `truffles-api/app/services/intent_service.py:2546`, `truffles-api/app/services/intent_service.py:2581`, `truffles-api/app/services/intent_service.py:3147`.
- `FACT`: Regex/phrase hardcodes for human request, opt-out, and frustration are still defined and used by legacy webhook/state flows: `truffles-api/app/services/intent_service.py:2393`, `truffles-api/app/services/intent_service.py:2401`, `truffles-api/app/services/intent_service.py:2431`, `truffles-api/app/routers/webhook/booking.py:266`, `truffles-api/app/routers/webhook/decision.py:637`, `truffles-api/app/services/state_service.py:910`.
- `FACT`: Domain-anchor heuristics are still defined here and used by webhook decision flows: `truffles-api/app/services/intent_service.py:3270`, `truffles-api/app/services/intent_service.py:3353`, `truffles-api/app/routers/webhook/decision.py:3073`, `truffles-api/app/routers/webhook/decision.py:6988`.
- `INFERENCE`: The file still carries a second semantic world of lexical/domain heuristics even if the active runtime owner has moved to policy-core.

## 10. Violations Against The Target Canon
- `FACT`: Owner input/context assembly is partially manifest-centered, but still anchored in hardcoded defaults and action vocabularies inside this file: `_POLICY_CORE_DEFAULT_INFO_REFS`, `_POLICY_CORE_GENERIC_TOOL_ACTIONS`, and schema enums in `_build_policy_core_response_format(...)`: `truffles-api/app/services/intent_service.py:467`, `truffles-api/app/services/intent_service.py:1985`, `truffles-api/app/services/intent_service.py:1996`.
- `FACT`: The same file still exports active owner logic and retired legacy semantic helpers, plus regex/domain heuristics: `truffles-api/app/services/intent_service.py:2442`, `truffles-api/app/services/intent_service.py:2546`, `truffles-api/app/services/intent_service.py:2615`, `truffles-api/app/services/intent_service.py:3270`.
- `FACT`: Fallback prompt text still embeds detailed semantic rules in core code rather than in a cleaner data/prompt boundary: `truffles-api/app/services/intent_service.py:2000`.
- `FACT`: `_sanitize_policy_core_payload(...)` still contains action-specific cleanup logic at the owner boundary: `truffles-api/app/services/intent_service.py:709`.
- `INFERENCE`: Strategic point `capability-manifest-centered growth` remains `open` because the file still centralizes policy-core vocabulary, default fact scopes, generic actions, and fallback semantic rules in code.
- `INFERENCE`: Strategic point `one semantic owner` remains `open` at the whole-system level because this file still co-locates active owner logic with older regex/domain semantic paths that are used elsewhere.

## 11. Salvageable Parts
- `FACT`: The active owner gateway shape is salvageable: strict `response_format`, explicit `policy_input`, schema validation via `validate_llm_policy_core_output(...)`, and downstream binding via `project_policy_tool_binding(...)`: `truffles-api/app/services/intent_service.py:467`, `truffles-api/app/services/intent_service.py:2715`, `truffles-api/app/services/intent_service.py:3091`, `truffles-api/app/services/intent_service.py:3122`.
- `FACT`: Dynamic card assembly from runtime capabilities and consult packs is salvageable: `_build_policy_core_policy_cards(...)`, `_build_policy_core_capability_cards(...)`, `_load_policy_core_consult_catalog(...)`, `_build_policy_core_allowed_context(...)`: `truffles-api/app/services/intent_service.py:1693`, `truffles-api/app/services/intent_service.py:1718`, `truffles-api/app/services/intent_service.py:1773`, `truffles-api/app/services/intent_service.py:1844`.
- `FACT`: Removal of `tool_args` from owner output before schema validation is salvageable and aligned with the target boundary: `truffles-api/app/services/intent_service.py:682`.
- `INFERENCE`: The salvageable core is the active policy-core gateway plus manifest-filtered context assembly, not the whole mixed-era service file.

## 12. Demotion / Extraction Candidates
- `FACT`: Retired `route_dialogue_controller(...)`, `route_llm_plan(...)`, and `interpret_expected_reply(...)` are demotion candidates that should stop living beside the active owner path: `truffles-api/app/services/intent_service.py:2546`, `truffles-api/app/services/intent_service.py:2581`, `truffles-api/app/services/intent_service.py:3147`.
- `FACT`: Regex/phrase/domain helpers are active elsewhere but are not part of the target policy-core owner boundary, so they are extraction or sunset candidates: `truffles-api/app/services/intent_service.py:2393`, `truffles-api/app/services/intent_service.py:2431`, `truffles-api/app/services/intent_service.py:3270`, `truffles-api/app/routers/webhook/decision.py:3073`.
- `FACT`: Code-level policy-core fallback prompt text and hardcoded defaults are demotion candidates if growth is to become more manifest/data-driven: `truffles-api/app/services/intent_service.py:1985`, `truffles-api/app/services/intent_service.py:1996`, `truffles-api/app/services/intent_service.py:2000`.
- `INFERENCE`: A real extraction likely needs a dedicated policy-core owner package or module-set, while legacy lexical/domain helpers move to clearly separate compatibility gates.

## 13. What This Analysis Changes In System Understanding
- `FACT`: The active semantic owner path is now clearer than before: `TurnPlanner` calls exactly one owner gateway, `route_llm_policy_core(...)`, which validates semantic output before binding tools.
- `FACT`: The same file still contains legacy regex/domain semantic helpers used by webhook/router flows.
- `INFERENCE`: This means the architecture is in a mixed transition state: active owner centralization improved, but the service boundary itself still mixes target and legacy semantics.
- `INFERENCE`: The next honest hotspot is `truffles-api/app/core/turn_executor.py`, because after owner gateway analysis the next unresolved question is how execution/boundary code still reshapes owner meaning downstream.

## 14. Open Questions
- `UNKNOWN`: Which policy-core defaults can be moved fully into manifests/config without breaking current packs or fallback behavior.
- `UNKNOWN`: Whether regex/domain-router helpers should be split by capability/guard type or frozen and sunset as a whole.
- `UNKNOWN`: How much of the action-specific sanitization in `_sanitize_policy_core_payload(...)` can be eliminated once upstream prompt/schema and downstream runtime are cleaner.
