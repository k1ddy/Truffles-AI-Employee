# File Analysis: `truffles-api/app/core/turn_planner.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
- `docs/system_forensics/ledgers/STATE_SURFACE_INVENTORY.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/SALVAGEABLE_COMPONENTS.md`
- `docs/system_forensics/ledgers/DO_NOT_REPEAT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: `turn_planner.py` is an 857-line / 26-method hotspot that defines the typed decision contract used by the active runtime: `InteractionContract`, `PendingQuestionContract`, `SemanticFrame`, `PolicyDecision`, `InboundTurnInput`, and `TurnPlanner`: `truffles-api/app/core/turn_planner.py:16`, `truffles-api/app/core/turn_planner.py:24`, `truffles-api/app/core/turn_planner.py:38`, `truffles-api/app/core/turn_planner.py:54`, `truffles-api/app/core/turn_planner.py:74`, `truffles-api/app/core/turn_planner.py:121`.
- `FACT`: The active runtime uses `TurnPlanner.plan(...)` from `ConsultantRuntime._plan_turn(...)` before execution, while `TurnExecutor` reuses planner factories for synthetic block/degrade decisions and `reasoning_core.py` reuses `InboundTurnInput` coercion for delegation normalization: `truffles-api/app/core/consultant_runtime.py:541`, `truffles-api/app/core/turn_executor.py:1442`, `truffles-api/app/core/turn_executor.py:1478`, `truffles-api/app/services/reasoning_core.py:497`.
- `INFERENCE`: This file is the typed decision-shaping seam between runtime orchestration and the policy-core owner gateway, not just a thin call wrapper.

## 2. Why This File Exists
- `FACT`: `plan(...)` normalizes inbound text, rejects empty non-media turns, merges booking slot state into the owner memory profile, calls `route_llm_policy_core(...)`, and returns a typed `PolicyDecision`: `truffles-api/app/core/turn_planner.py:140`, `truffles-api/app/core/turn_planner.py:150`, `truffles-api/app/core/turn_planner.py:154`, `truffles-api/app/core/turn_planner.py:162`, `truffles-api/app/core/turn_planner.py:166`.
- `FACT`: The file also owns synthetic planner decisions for preflight reject and controlled degrade via `build_preflight_reject(...)` and `build_controlled_degrade(...)`: `truffles-api/app/core/turn_planner.py:484`, `truffles-api/app/core/turn_planner.py:513`.
- `FACT`: It converts projected policy-core payloads into canonical typed planner output by building `PendingQuestionContract`, `SemanticFrame`, and `meta.semantic_contract`: `truffles-api/app/core/turn_planner.py:224`, `truffles-api/app/core/turn_planner.py:243`, `truffles-api/app/core/turn_planner.py:244`, `truffles-api/app/core/turn_planner.py:273`, `truffles-api/app/core/turn_planner.py:296`.
- `INFERENCE`: The file exists because the active runtime still needs a deterministic adapter that translates raw policy-core results into a runtime-owned decision dialect.

## 3. Active Callers And Entrypoints
- `FACT`: `ConsultantRuntime._plan_turn(...)` is the active runtime caller of `TurnPlanner.plan(...)`: `truffles-api/app/core/consultant_runtime.py:526`, `truffles-api/app/core/consultant_runtime.py:541`.
- `FACT`: `TurnExecutor` calls `TurnPlanner().build_preflight_reject(...)` and `TurnPlanner().build_controlled_degrade(...)` when building block/degrade boundary artifacts: `truffles-api/app/core/turn_executor.py:1442`, `truffles-api/app/core/turn_executor.py:1478`.
- `FACT`: `reasoning_core.py` uses `TurnPlanner().coerce_inbound(...)` through `_normalize_payload_for_delegation(...)` to normalize media/text payloads before delegation: `truffles-api/app/services/reasoning_core.py:496`, `truffles-api/app/core/turn_planner.py:130`, `truffles-api/app/core/turn_planner.py:135`.
- `INFERENCE`: `turn_planner.py` sits on both the active runtime path and the compatibility/preflight surface, so it is a shared authority seam rather than a purely internal helper.

## 4. Control Path Owned By This File
- `FACT`: `plan(...)` performs four planner stages: preflight empty-message reject, booking-state merge into owner input, `route_llm_policy_core(...)` owner call, and either decision building or synthetic degrade: `truffles-api/app/core/turn_planner.py:150`, `truffles-api/app/core/turn_planner.py:162`, `truffles-api/app/core/turn_planner.py:166`, `truffles-api/app/core/turn_planner.py:176`, `truffles-api/app/core/turn_planner.py:208`.
- `FACT`: On a successful owner call, planner records `policy_core_trace` via `_build_policy_core_trace_payload(...)` and returns `_build_policy_core_decision(...)`: `truffles-api/app/core/turn_planner.py:176`, `truffles-api/app/core/turn_planner.py:554`, `truffles-api/app/core/turn_planner.py:589`.
- `FACT`: `_build_policy_core_decision(...)` normalizes `tool_action`, slot names, `next_question`, `open_questions`, strips pending-question payload on handoff, and then routes into `build_from_policy_override(...)`: `truffles-api/app/core/turn_planner.py:594`, `truffles-api/app/core/turn_planner.py:598`, `truffles-api/app/core/turn_planner.py:603`, `truffles-api/app/core/turn_planner.py:615`, `truffles-api/app/core/turn_planner.py:619`, `truffles-api/app/core/turn_planner.py:629`.
- `FACT`: `build_from_policy_override(...)` is the point where projected owner payload becomes a `PolicyDecision`: it constructs `PendingQuestionContract`, `SemanticFrame`, `meta.semantic_contract`, and the final typed decision object: `truffles-api/app/core/turn_planner.py:224`, `truffles-api/app/core/turn_planner.py:243`, `truffles-api/app/core/turn_planner.py:244`, `truffles-api/app/core/turn_planner.py:273`, `truffles-api/app/core/turn_planner.py:283`.
- `INFERENCE`: The planner owns the last deterministic transformation before the executor sees the turn, so it is a strong control-path seam.

## 5. Data Reads
- `FACT`: `plan(...)` reads inbound runtime inputs: `message_text`, `client_slug`, `booking_state`, `memory_summary`, `memory_profile`, and `timing_context`: `truffles-api/app/core/turn_planner.py:140`, `truffles-api/app/core/turn_planner.py:162`, `truffles-api/app/core/turn_planner.py:166`.
- `FACT`: `build_from_policy_override(...)` reads projected owner payload fields including `action`, `intent`, `tool_action`, `tool_args`, `slots`, `pack_refs`, `capability`, `risk_signals`, `entity_refs`, `referents`, `goal`, `reason`, `subject_kind`, `temporal_scope`, `resolution_mode`, `pending_question_*`, and `active_question_relation`: `truffles-api/app/core/turn_planner.py:232`, `truffles-api/app/core/turn_planner.py:242`, `truffles-api/app/core/turn_planner.py:243`, `truffles-api/app/core/turn_planner.py:249`, `truffles-api/app/core/turn_planner.py:286`, `truffles-api/app/core/turn_planner.py:288`, `truffles-api/app/core/turn_planner.py:289`.
- `FACT`: `_build_semantic_frame_payload(...)` reads slots, referents, entity refs, pending-question payload, risk signals, capability, resolution mode, and tool-action hint to synthesize the frame: `truffles-api/app/core/turn_planner.py:357`, `truffles-api/app/core/turn_planner.py:365`, `truffles-api/app/core/turn_planner.py:367`, `truffles-api/app/core/turn_planner.py:397`, `truffles-api/app/core/turn_planner.py:424`, `truffles-api/app/core/turn_planner.py:433`, `truffles-api/app/core/turn_planner.py:440`.
- `FACT`: `_build_semantic_contract_payload(...)` reads the synthesized frame plus fallback payload fields to construct `semantic_contract.v1`: `truffles-api/app/core/turn_planner.py:301`, `truffles-api/app/core/turn_planner.py:310`, `truffles-api/app/core/turn_planner.py:332`, `truffles-api/app/core/turn_planner.py:346`.
- `INFERENCE`: The planner reads both pre-owner runtime memory and post-owner projected payload, so it bridges two semantic languages in one file.

## 6. Data Writes And Side Effects
- `FACT`: The planner writes a `PolicyDecision` carrying `outcome`, `action`, `intent`, `source`, `tool_action`, `tool_args`, `slots`, `pack_refs`, `capability_refs`, `interaction`, `semantic_frame`, `pending_question_contract`, and `meta`: `truffles-api/app/core/turn_planner.py:54`, `truffles-api/app/core/turn_planner.py:283`, `truffles-api/app/core/turn_planner.py:286`, `truffles-api/app/core/turn_planner.py:288`, `truffles-api/app/core/turn_planner.py:289`, `truffles-api/app/core/turn_planner.py:296`, `truffles-api/app/core/turn_planner.py:298`.
- `FACT`: The planner stores owner observability inside `decision.meta["policy_core_trace"]`, including owner input, raw output, semantic frame, projection trace, schema verdict, and model metadata: `truffles-api/app/core/turn_planner.py:176`, `truffles-api/app/core/turn_planner.py:217`, `truffles-api/app/core/turn_planner.py:554`.
- `FACT`: Synthetic preflight/degrade builders emit `PolicyDecision` objects with `meta.reason_code`, `preflight_path` / `degrade_path`, and `synthetic_policy_decision`: `truffles-api/app/core/turn_planner.py:484`, `truffles-api/app/core/turn_planner.py:499`, `truffles-api/app/core/turn_planner.py:507`, `truffles-api/app/core/turn_planner.py:513`, `truffles-api/app/core/turn_planner.py:533`.
- `INFERENCE`: The planner has no DB writes of its own, but it is the writer of the runtime decision artifact that downstream execution and persistence trust.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: `route_llm_policy_core(...)` already returns a projected payload after schema validation and `project_policy_tool_binding(...)`, including `tool_action` and optional `tool_args`: `truffles-api/app/services/intent_service.py:3091`, `truffles-api/app/services/intent_service.py:3122`, `truffles-api/app/services/intent_service.py:3137`, `truffles-api/app/services/intent_service.py:3140`.
- `FACT`: Even after that upstream projection, planner deterministically rebuilds `PendingQuestionContract`, `SemanticFrame`, and `meta.semantic_contract` from the projected payload: `truffles-api/app/core/turn_planner.py:243`, `truffles-api/app/core/turn_planner.py:244`, `truffles-api/app/core/turn_planner.py:273`, `truffles-api/app/core/turn_planner.py:301`, `truffles-api/app/core/turn_planner.py:357`, `truffles-api/app/core/turn_planner.py:646`.
- `FACT`: Planner also deterministically strips pending-question payload on handoff, normalizes slot aliases (`service_query -> service`, `time/date -> datetime`, `customer_name -> name`, `phone_number -> phone`), and chooses fallback booking slot names from `expected_reply_type`: `truffles-api/app/core/turn_planner.py:8`, `truffles-api/app/core/turn_planner.py:615`, `truffles-api/app/core/turn_planner.py:629`, `truffles-api/app/core/turn_planner.py:789`, `truffles-api/app/core/turn_planner.py:801`.
- `FACT`: Planner merges `booking_state` into `memory_profile.slot_state` before the owner call when the profile does not already carry slot state: `truffles-api/app/core/turn_planner.py:162`, `truffles-api/app/core/turn_planner.py:789`, `truffles-api/app/core/turn_planner.py:797`.
- `INFERENCE`: The planner is not a pure transport adapter around the owner. It shapes owner input, rebuilds owner output into internal semantic/state carriers, and fabricates deterministic fallback decisions.

## 8. Truth Carriers Touched Here
- `FACT`: The planner defines and emits `PolicyDecision.semantic_frame` and `PolicyDecision.pending_question_contract` as first-class runtime decision carriers: `truffles-api/app/core/turn_planner.py:70`, `truffles-api/app/core/turn_planner.py:71`, `truffles-api/app/core/turn_planner.py:296`, `truffles-api/app/core/turn_planner.py:297`.
- `FACT`: The planner also emits `meta.semantic_contract` as an additional semantic carrier derived from the same payload: `truffles-api/app/core/turn_planner.py:273`, `truffles-api/app/core/turn_planner.py:278`, `truffles-api/app/core/turn_planner.py:279`.
- `FACT`: `PolicyDecision` still carries `tool_args` as part of the decision object, even though these args were already reintroduced upstream by `project_policy_tool_binding(...)`: `truffles-api/app/core/turn_planner.py:63`, `truffles-api/app/core/turn_planner.py:286`, `truffles-api/app/services/intent_service.py:3122`, `truffles-api/app/services/intent_service.py:3140`.
- `FACT`: `PolicyDecision` still defines `fact_refs`, but `build_from_policy_override(...)` populates `pack_refs` and `capability_refs` only; `fact_refs` is not assigned on the active planner path and therefore remains the model default: `truffles-api/app/core/turn_planner.py:66`, `truffles-api/app/core/turn_planner.py:283`, `truffles-api/app/core/turn_planner.py:288`, `truffles-api/app/core/turn_planner.py:289`.
- `FACT`: `decision.meta["policy_core_trace"]` is a separate observability carrier containing owner input/raw output/semantic frame/projection trace: `truffles-api/app/core/turn_planner.py:176`, `truffles-api/app/core/turn_planner.py:217`, `truffles-api/app/core/turn_planner.py:554`.
- `INFERENCE`: The planner decision surface still mixes semantic carriers, binding carriers, and observability carriers in one typed object.

## 9. Violations Against The Target Canon
- `FACT`: The planner still rebuilds `semantic_frame` and `semantic_contract` locally after the owner call instead of treating the owner-emitted semantic frame as the single internal semantic artifact: `truffles-api/app/core/turn_planner.py:301`, `truffles-api/app/core/turn_planner.py:357`, `truffles-api/app/core/turn_planner.py:619`.
- `FACT`: The planner still carries `tool_args` inside `PolicyDecision`, so binding data remains embedded in the decision contract between planning and execution: `truffles-api/app/core/turn_planner.py:63`, `truffles-api/app/core/turn_planner.py:286`, `truffles-api/app/services/intent_service.py:3140`.
- `FACT`: The planner owns hardcoded semantic mappings such as `_ACTION_TO_OUTCOME`, requested-effect mapping, slot alias mapping, and handoff pending-question stripping: `truffles-api/app/core/turn_planner.py:8`, `truffles-api/app/core/turn_planner.py:124`, `truffles-api/app/core/turn_planner.py:468`, `truffles-api/app/core/turn_planner.py:629`.
- `FACT`: Synthetic degrade/preflight decisions are manufactured inside the planner instead of a more isolated boundary/degrade layer: `truffles-api/app/core/turn_planner.py:484`, `truffles-api/app/core/turn_planner.py:513`.
- `INFERENCE`: Strategic point `one semantic owner` remains `open` because planner still performs significant post-owner semantic shaping.
- `INFERENCE`: Strategic point `pure boundary runtime` remains `open` because planner still acts as a semantic/binding adapter rather than a thin typed transport around the owner contract.

## 10. Salvageable Parts
- `FACT`: The typed contract family is reusable: `InteractionContract`, `PendingQuestionContract`, `SemanticFrame`, `PolicyDecision`, and `InboundTurnInput`: `truffles-api/app/core/turn_planner.py:16`, `truffles-api/app/core/turn_planner.py:24`, `truffles-api/app/core/turn_planner.py:38`, `truffles-api/app/core/turn_planner.py:54`, `truffles-api/app/core/turn_planner.py:74`.
- `FACT`: Planner-level owner observability is reusable: `_build_policy_core_trace_payload(...)` already captures owner input, semantic frame, raw output, projection trace, schema verdict, projection verdict, model name, and retry/fallback signals: `truffles-api/app/core/turn_planner.py:554`.
- `FACT`: Inbound media/text normalization through `InboundTurnInput` is reusable as a bounded ingress utility: `truffles-api/app/core/turn_planner.py:74`, `truffles-api/app/core/turn_planner.py:96`, `truffles-api/app/core/turn_planner.py:100`.
- `INFERENCE`: The salvageable core is the typed planner contract and owner observability surface, not the whole current planner implementation.

## 11. Demotion / Removal Candidates
- `FACT`: Planner-owned semantic contract/frame builders are extraction candidates: `_build_semantic_contract_payload(...)`, `_build_semantic_frame_payload(...)`, `_build_pending_question_contract(...)`: `truffles-api/app/core/turn_planner.py:301`, `truffles-api/app/core/turn_planner.py:357`, `truffles-api/app/core/turn_planner.py:646`.
- `FACT`: `PolicyDecision.tool_args` is an extraction/demotion candidate because binding data still crosses the planner boundary in the decision object: `truffles-api/app/core/turn_planner.py:63`, `truffles-api/app/core/turn_planner.py:286`.
- `FACT`: `PolicyDecision.fact_refs` is a stale carrier candidate because it survives in the model while the active planner path does not populate it: `truffles-api/app/core/turn_planner.py:66`, `truffles-api/app/core/turn_planner.py:283`, `truffles-api/app/core/turn_planner.py:288`.
- `FACT`: Hardcoded slot alias and requested-effect mappings are demotion candidates if planner behavior is to become more contract/data-driven: `truffles-api/app/core/turn_planner.py:8`, `truffles-api/app/core/turn_planner.py:468`, `truffles-api/app/core/turn_planner.py:801`.
- `INFERENCE`: A real extraction likely separates the typed planner contract from semantic-frame rebuilding, binding carriers, and deterministic degrade synthesis.

## 12. What This Analysis Changes In System Understanding
- `FACT`: The active path is now mapped end-to-end through runtime, planner, owner gateway, executor, and state writer.
- `FACT`: `turn_planner.py` is not a thin bridge to `route_llm_policy_core(...)`; it shapes owner input, reconstructs internal semantic carriers from projected payload, and manufactures synthetic decisions for degrade/preflight.
- `INFERENCE`: After five hotspot analyses, the remaining architectural debt is not only in runtime/state/executor. The planner itself is part of the mixed authority boundary.
- `INFERENCE`: The next honest hotspot is `truffles-api/app/core/booking_prompt_owner.py`, because it is the remaining owner-adjacent core module that still needs to be classified as active debt, dormant compatibility residue, or salvageable secondary owner surface.

## 13. Open Questions
- `UNKNOWN`: Whether `SemanticFrame` and `PendingQuestionContract` should continue to be rebuilt in planner code or should arrive from the owner path as final internal contracts.
- `UNKNOWN`: Whether `PolicyDecision.tool_args` can be removed entirely once post-owner binding/projector boundaries are cleaned up.
- `UNKNOWN`: Whether `PolicyDecision.fact_refs` is simply stale model debt or still required for some unanalysed compatibility path.
