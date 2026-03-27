# File Analysis: `truffles-api/app/core/consultant_runtime.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
- `docs/system_forensics/ledgers/STATE_SURFACE_INVENTORY.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: `ConsultantRuntime.handle_webhook_payload(...)` is the real orchestration entrypoint for the active runtime path; it resolves preflight, loads context/state, runs planner/boundary/executor, writes runtime state, sends replies, and records trace/meta inside one class in `truffles-api/app/core/consultant_runtime.py:88`.
- `FACT`: `consultant_core_v2` is currently a thin subclass/wrapper around `ConsultantRuntime`, not a separate orchestration module-set, in `truffles-api/app/core/consultant_core_v2.py:8`, `truffles-api/app/core/consultant_core_v2.py:14`, and `truffles-api/app/core/consultant_core_v2.py:36`.
- `INFERENCE`: Despite the new active import surface named `consultant_core_v2`, semantic runtime ownership still materially lives in `consultant_runtime.py` because that file contains the real control path.

## 2. Why This File Exists
- `FACT`: The file instantiates all main runtime seams in one constructor: `TurnPlanner`, `BoundaryValidator`, `DialogStateService`, `TurnExecutor`, and `ResponseRealizer` in `truffles-api/app/core/consultant_runtime.py:80`.
- `FACT`: The same file also owns transport send/persist behavior, handoff activation/resume, trace/meta recording, runtime payload writes, and user message persistence in `truffles-api/app/core/consultant_runtime.py:828`, `truffles-api/app/core/consultant_runtime.py:857`, `truffles-api/app/core/consultant_runtime.py:897`, `truffles-api/app/core/consultant_runtime.py:914`, `truffles-api/app/core/consultant_runtime.py:978`, and `truffles-api/app/core/consultant_runtime.py:1256`.
- `INFERENCE`: Historically this file became the integration hotspot that glued together semantic planning, deterministic boundary logic, persistence, transport, and observability, which is why it remains the active runtime owner even after wrapper-level cutover renaming.

## 3. Active Callers And Entrypoints
- `FACT`: Public/materialized wrapper entrypoints route through `handle_public_webhook_payload(...)` in `truffles-api/app/routers/public_entrypoint_contract.py:29`, then into `app.core.consultant_core_v2.handle_webhook_payload(...)` from direct webhook, legacy webhook, `/message`, `/provider/inbound`, and `/decision/handle` in `truffles-api/app/routers/webhook/http.py:686`, `truffles-api/app/routers/webhook/http.py:769`, `truffles-api/app/routers/message.py:21`, `truffles-api/app/routers/provider_gateway.py:56`, and `truffles-api/app/routers/decision_core.py:44`.
- `FACT`: Additional active callers import `app.core.consultant_core_v2.handle_webhook_payload`, not `consultant_runtime.handle_webhook_payload`, in `truffles-api/app/routers/webhook/decision.py:8598`, `truffles-api/app/routers/webhook/outbox.py:1265`, `truffles-api/app/routers/webhook/outbox.py:1536`, `truffles-api/app/services/reasoning_core.py:633`, and `truffles-api/app/services/console_consultant_verification.py:1671`.
- `FACT`: `app.core.consultant_core_v2.handle_webhook_payload(...)` simply forwards to `_RUNTIME.handle_webhook_payload(...)` where `_RUNTIME` is `ConsultantCoreV2Runtime(ConsultantRuntime)` in `truffles-api/app/core/consultant_core_v2.py:14`, `truffles-api/app/core/consultant_core_v2.py:20`, and `truffles-api/app/core/consultant_core_v2.py:36`.
- `FACT`: The legacy module-level `app.core.consultant_runtime.handle_webhook_payload(...)` now delegates back to `consultant_core_v2.handle_webhook_payload(...)` in `truffles-api/app/core/consultant_runtime.py:1339` and `truffles-api/app/core/consultant_runtime.py:1353`.
- `INFERENCE`: The import surface has been rerouted, but the orchestration code was not extracted. The system therefore has a naming cutover, not a runtime cutover.

## 4. Control Path Owned By This File
- `FACT`: The main runtime path is linear and centralized in `ConsultantRuntime.handle_webhook_payload(...)`: `_resolve_preflight` -> `_prepare_conversation` -> `_load_runtime_state` -> `_handle_control_turn` -> `_prime_runtime_context` -> `_plan_turn` -> `boundary.validate` -> `_execute_turn` -> `_apply_execution_boundary_override` -> `_write_runtime_state` -> `_activate_handoff` or `_resume_bot_if_needed` -> `realizer.realize` -> `executor.assemble` -> `_send_and_persist_reply` -> `_record_turn_trace` in `truffles-api/app/core/consultant_runtime.py:105`, `truffles-api/app/core/consultant_runtime.py:116`, `truffles-api/app/core/consultant_runtime.py:123`, `truffles-api/app/core/consultant_runtime.py:127`, `truffles-api/app/core/consultant_runtime.py:139`, `truffles-api/app/core/consultant_runtime.py:146`, `truffles-api/app/core/consultant_runtime.py:152`, `truffles-api/app/core/consultant_runtime.py:168`, `truffles-api/app/core/consultant_runtime.py:176`, `truffles-api/app/core/consultant_runtime.py:182`, `truffles-api/app/core/consultant_runtime.py:191`, `truffles-api/app/core/consultant_runtime.py:204`, `truffles-api/app/core/consultant_runtime.py:210`, `truffles-api/app/core/consultant_runtime.py:219`, and `truffles-api/app/core/consultant_runtime.py:227`.
- `FACT`: The file also owns an early deterministic control path for session reset / reset-only traffic in `_handle_control_turn(...)` and `_reset_runtime_context(...)` in `truffles-api/app/core/consultant_runtime.py:378` and `truffles-api/app/core/consultant_runtime.py:472`.
- `FACT`: The file labels the assembled stages as `ingress`, `planner`, `boundary`, `state`, `executor`, `realizer` in `truffles-api/app/core/consultant_runtime.py:210`.
- `INFERENCE`: This is the real active control path of consultant-core today. Any claim that `consultant_core_v2` is already a separate runtime is contradicted by this file.

## 5. Data Reads
- `FACT`: The file reads user payload text, metadata, and client slug during planning and persistence in `truffles-api/app/core/consultant_runtime.py:319`, `truffles-api/app/core/consultant_runtime.py:542`, and `truffles-api/app/core/consultant_runtime.py:1268`.
- `FACT`: It reads conversation context and canonicalized runtime payload through `DialogStateService.load_runtime_payload(...)` in `truffles-api/app/core/consultant_runtime.py:363`.
- `FACT`: It reads recent message history directly from the database for memory summary in `truffles-api/app/core/consultant_runtime.py:1311`.
- `FACT`: It reads runtime semantic frame, semantic contract, current goal, grounded referents, and pending question contract via `DialogStateService` projection helpers inside `_build_policy_core_memory_profile(...)`, `_project_runtime_semantic_contract(...)`, and `_project_runtime_pending_question_contract(...)` in `truffles-api/app/core/consultant_runtime.py:564`, `truffles-api/app/core/consultant_runtime.py:668`, and `truffles-api/app/core/consultant_runtime.py:734`.
- `FACT`: It reads handover state and instance routing data through `get_active_handover(...)` and `get_instance_id(...)` in `truffles-api/app/core/consultant_runtime.py:865` and `truffles-api/app/core/consultant_runtime.py:951`.
- `INFERENCE`: This file is not only orchestration glue. It is also a major semantic/context reader and merger.

## 6. Data Writes And Side Effects
- `FACT`: The file writes user conversation/user timestamps and branch assignment in `_prepare_conversation(...)` at `truffles-api/app/core/consultant_runtime.py:314`, `truffles-api/app/core/consultant_runtime.py:316`, and `truffles-api/app/core/consultant_runtime.py:317`.
- `FACT`: It persists user messages and assistant messages with decision metadata in `_persist_user_message(...)`, `_send_and_persist_reply(...)`, and `_record_turn_trace(...)` at `truffles-api/app/core/consultant_runtime.py:1256`, `truffles-api/app/core/consultant_runtime.py:928`, and `truffles-api/app/core/consultant_runtime.py:1202`.
- `FACT`: It writes conversation runtime context and runtime trace through `_write_runtime_state(...)` and `_record_turn_trace(...)` at `truffles-api/app/core/consultant_runtime.py:828` and `truffles-api/app/core/consultant_runtime.py:1106`.
- `FACT`: It can create a handover, transition conversation state, update handover status, and notify Telegram in `_activate_handoff(...)` and `_resume_bot_if_needed(...)` at `truffles-api/app/core/consultant_runtime.py:857`, `truffles-api/app/core/consultant_runtime.py:875`, and `truffles-api/app/core/consultant_runtime.py:911`.
- `FACT`: It mutates runtime globals for capabilities and truth through `_prime_runtime_context(...)` in `truffles-api/app/core/consultant_runtime.py:494`, `truffles-api/app/core/consultant_runtime.py:502`, `truffles-api/app/core/consultant_runtime.py:508`, and `truffles-api/app/core/consultant_runtime.py:515`.
- `FACT`: It performs outbound delivery side effects in `_send_and_persist_reply(...)` at `truffles-api/app/core/consultant_runtime.py:956`.
- `INFERENCE`: This file mixes semantic orchestration with persistence and transport side effects, which enlarges cutover scope and makes isolated extraction harder.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: The primary semantic decision is delegated to `TurnPlanner.plan(...)` inside `_plan_turn(...)` in `truffles-api/app/core/consultant_runtime.py:539`.
- `FACT`: The file adds deterministic gates before and after planning: manager-active handoff in `_plan_turn(...)` at `truffles-api/app/core/consultant_runtime.py:525`, invalid outcome degrade at `truffles-api/app/core/consultant_runtime.py:549`, boundary validation at `truffles-api/app/core/consultant_runtime.py:152`, executor-triggered handoff degrade at `truffles-api/app/core/consultant_runtime.py:792`, and reset-only control handling at `truffles-api/app/core/consultant_runtime.py:378`.
- `FACT`: The file also derives final trace/meta action names post-owner in `_derive_contract_action(...)`; for example, successful `calendar.book_slot` becomes `booking_confirm`, and a booking collect with pending reply type becomes `booking_prompt` in `truffles-api/app/core/consultant_runtime.py:1220`.
- `FACT`: Runtime semantic contract and pending question contract are merged from dialog state, decision, and execution metadata in `_project_runtime_semantic_contract(...)` and `_project_runtime_pending_question_contract(...)` at `truffles-api/app/core/consultant_runtime.py:668` and `truffles-api/app/core/consultant_runtime.py:734`.
- `INFERENCE`: The file does not claim primary semantic ownership, but it still performs post-owner shaping and merging substantial enough to matter architecturally. This is compatible-runtime orchestration, not a pure boundary shell.

## 8. Truth Carriers Touched Here
- `FACT`: The file consumes and writes the runtime payload under `conversation.context['consultant_runtime']` via `DialogStateService.load_runtime_payload(...)` and `DialogStateService.write_runtime_payload(...)` in `truffles-api/app/core/consultant_runtime.py:363` and `truffles-api/app/core/consultant_runtime.py:828`.
- `FACT`: It reads and re-emits `semantic_state.materialized_frame`, runtime `semantic_contract`, pending-question state, booking payload, current goal, and grounded referents through its projection helpers and memory-profile builder in `truffles-api/app/core/consultant_runtime.py:564`, `truffles-api/app/core/consultant_runtime.py:668`, `truffles-api/app/core/consultant_runtime.py:734`, and `truffles-api/app/core/consultant_runtime.py:1220`.
- `FACT`: It writes trace and message metadata surfaces such as `decision_trace`, `decision_meta`, `semantic_contract`, `semantic_frame`, `semantic_state_before`, `semantic_state_after`, `pending_question_contract`, `expected_reply_type`, and `expected_reply_reason` in `truffles-api/app/core/consultant_runtime.py:978` and `truffles-api/app/core/consultant_runtime.py:1137`.
- `INFERENCE`: Even after previous canonicalization work, this file remains one of the main places where canonical state, compatibility projections, and observability surfaces are assembled together.

## 9. Violations Against The Target Canon
- `FACT`: `consultant_core_v2.py` is only a thin subclass and wrapper over this file, so the new runtime path has not been structurally extracted yet: `truffles-api/app/core/consultant_core_v2.py:8`, `truffles-api/app/core/consultant_core_v2.py:14`, and `truffles-api/app/core/consultant_core_v2.py:36`.
- `FACT`: The legacy runtime module still exports a module-level `handle_webhook_payload(...)` that delegates back to `consultant_core_v2`, preserving name-level compatibility loops in `truffles-api/app/core/consultant_runtime.py:1339` and `truffles-api/app/core/consultant_runtime.py:1353`.
- `FACT`: The runtime context key and payload schema still use legacy naming (`consultant_runtime`, `consultant_runtime.v1`) in `truffles-api/app/core/dialog_state_service.py:21` and `truffles-api/app/core/dialog_state_service.py:2619`.
- `INFERENCE`: Strategic point `consultant-core-v2 as a new semantic path` is still `open` because the old runtime file remains the orchestration owner.
- `INFERENCE`: Strategic point `pure boundary runtime` is still `open` because this file performs post-owner action shaping, semantic-contract merging, pending-question merging, transport orchestration, and state writes in one place.

## 10. Salvageable Parts
- `FACT`: The file already expresses a clean high-level stage order that can be preserved during extraction: preflight -> state load -> planner -> boundary -> executor -> state write -> realize -> trace in `truffles-api/app/core/consultant_runtime.py:88` and `truffles-api/app/core/consultant_runtime.py:210`.
- `FACT`: The file provides bounded helper seams that can be kept but moved: `_resolve_preflight(...)`, `_load_runtime_state(...)`, `_execute_turn(...)`, `_send_and_persist_reply(...)`, and `_build_memory_summary(...)` in `truffles-api/app/core/consultant_runtime.py:268`, `truffles-api/app/core/consultant_runtime.py:363`, `truffles-api/app/core/consultant_runtime.py:766`, `truffles-api/app/core/consultant_runtime.py:914`, and `truffles-api/app/core/consultant_runtime.py:1311`.
- `INFERENCE`: The runtime should not be deleted wholesale. Its useful pieces are the orchestration sequence and bounded adapters, but they need relocation into a real `consultant_core_v2` module-set.

## 11. Demotion / Removal Candidates
- `FACT`: The module-level compatibility wrapper in `consultant_runtime.py` should remain only as a temporary adapter because it contains no unique runtime logic, only a back-delegation to `consultant_core_v2` in `truffles-api/app/core/consultant_runtime.py:1339` and `truffles-api/app/core/consultant_runtime.py:1353`.
- `INFERENCE`: The class `ConsultantRuntime` itself is the real demotion target. Either its orchestration must move out, or the file cannot stop being the semantic runtime owner.
- `INFERENCE`: The runtime-specific semantic contract and pending-question merge helpers in this file are prime extraction candidates because they entangle canonical state projection with runtime orchestration.

## 12. What This Analysis Changes In System Understanding
- `FACT`: Active callers already route to `consultant_core_v2`, but active orchestration still lives in `consultant_runtime.py`.
- `INFERENCE`: This proves that previous cutover work changed import surfaces but did not yet create a new runtime authority boundary.
- `INFERENCE`: The next hotspot analysis must focus on `dialog_state_service.py`, because this file's orchestration depends heavily on that service for loading, projecting, and writing runtime/canonical state.

## 13. Open Questions
- `UNKNOWN`: How much of `_project_runtime_semantic_contract(...)` and `_project_runtime_pending_question_contract(...)` can move into `DialogStateService` without simply shifting the same ownership problem.
- `UNKNOWN`: Whether outbound send/persist logic should stay inside the future v2 runtime package or move into a separate transport/persistence boundary adapter.
- `UNKNOWN`: Whether `reasoning_core` and `public_entrypoint_contract` still contain hidden compatibility assumptions beyond the direct import reroutes already visible.
