# File Analysis: `truffles-api/app/services/reasoning_core.py`

Status: `completed`
Baseline snapshot: `8319d9e1`
Related ledgers:
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/STATE_SURFACE_INVENTORY.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `docs/system_forensics/ledgers/SALVAGEABLE_COMPONENTS.md`
- `docs/system_forensics/ledgers/DO_NOT_REPEAT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## 1. Role Summary
- `FACT`: The module self-identifies as a legacy compatibility shim: active webhook runtime ownership lives in `app.core.consultant_core_v2`, while this file “only preserves the thin compatibility surface that tests and legacy wrappers still import while shadow runtime code is removed”: `truffles-api/app/services/reasoning_core.py:1`, `truffles-api/app/services/reasoning_core.py:3`, `truffles-api/app/services/reasoning_core.py:5`.
- `FACT`: `reasoning_core.py` is a 683-line / 27-top-level-definition service hotspot that imports `TurnExecutor`, `TurnPlanner`, `DialogStateService`, and frozen `decision_router`: `truffles-api/app/services/reasoning_core.py:18`, `truffles-api/app/services/reasoning_core.py:21`.
- `FACT`: The module still exposes compatibility dataclasses, block/degrade artifact builders, conversation snapshot helpers, secret-preflight wrappers, and the public `run_reasoning_core(...)` / `handle_webhook_payload(...)` functions: `truffles-api/app/services/reasoning_core.py:48`, `truffles-api/app/services/reasoning_core.py:64`, `truffles-api/app/services/reasoning_core.py:84`, `truffles-api/app/services/reasoning_core.py:115`, `truffles-api/app/services/reasoning_core.py:354`, `truffles-api/app/services/reasoning_core.py:603`, `truffles-api/app/services/reasoning_core.py:619`.
- `INFERENCE`: The file is no longer an active runtime owner, but it still preserves a significant compatibility/preflight/snapshot surface around the new runtime.

## 2. Why This File Exists
- `FACT`: `handle_webhook_payload(...)` now delegates directly to `app.core.consultant_core_v2.handle_webhook_payload(...)`: `truffles-api/app/services/reasoning_core.py:619`, `truffles-api/app/services/reasoning_core.py:633`.
- `FACT`: `run_reasoning_core(...)` exists as a request-wrapper entrypoint that forwards a `ReasoningCoreRequest` into that same delegate: `truffles-api/app/services/reasoning_core.py:603`, `truffles-api/app/services/reasoning_core.py:604`.
- `FACT`: The file also exists to preserve boundary/preflight compatibility builders such as `_build_runtime_exception_artifact(...)`, `_build_empty_message_artifact(...)`, `_build_missing_remote_jid_artifact(...)`, `_build_duplicate_message_artifact(...)`, and `_run_secret_enforced_preflight(...)`: `truffles-api/app/services/reasoning_core.py:115`, `truffles-api/app/services/reasoning_core.py:141`, `truffles-api/app/services/reasoning_core.py:158`, `truffles-api/app/services/reasoning_core.py:254`, `truffles-api/app/services/reasoning_core.py:574`.
- `INFERENCE`: The file exists to bridge old wrapper/preflight/test surfaces to the new runtime, not to own semantic runtime behavior directly.

## 3. Active Callers And Entrypoints
- `FACT`: The public compatibility entrypoints are `run_reasoning_core(...)` and `handle_webhook_payload(...)`: `truffles-api/app/services/reasoning_core.py:603`, `truffles-api/app/services/reasoning_core.py:619`.
- `FACT`: Visible direct repo callsites for those entrypoints are test-only: `truffles-api/tests/test_reasoning_core.py:391`, `truffles-api/tests/test_reasoning_core.py:459`.
- `FACT`: Active app routing goes directly through `public_entrypoint_contract -> consultant_core_v2`, not through `reasoning_core.py`: `truffles-api/app/routers/public_entrypoint_contract.py:42`, `truffles-api/app/core/consultant_core_v2.py:22`.
- `INFERENCE`: Like `booking_prompt_owner.py`, this module currently looks dormant from the main runtime call graph, but it remains a compatibility surface in code and tests.

## 4. Control Path Owned By This File
- `FACT`: `run_reasoning_core(...)` is a thin wrapper: it forwards the request to `handle_webhook_payload(...)`, which forwards directly to `consultant_core_v2.handle_webhook_payload(...)`: `truffles-api/app/services/reasoning_core.py:603`, `truffles-api/app/services/reasoning_core.py:604`, `truffles-api/app/services/reasoning_core.py:619`, `truffles-api/app/services/reasoning_core.py:633`.
- `FACT`: The module still owns block/degrade preflight artifact construction through `TurnExecutor().build_*_boundary_artifact_from_request(...)`: `_build_runtime_exception_artifact(...)`, `_build_empty_message_artifact(...)`, `_build_missing_remote_jid_artifact(...)`, `_build_sender_branch_ignore_artifact(...)`, `_build_duplicate_message_artifact(...)`: `truffles-api/app/services/reasoning_core.py:115`, `truffles-api/app/services/reasoning_core.py:121`, `truffles-api/app/services/reasoning_core.py:141`, `truffles-api/app/services/reasoning_core.py:192`, `truffles-api/app/services/reasoning_core.py:254`.
- `FACT`: `_build_conversation_snapshot(...)` reconstructs a derived compatibility snapshot from context using `DialogStateService`, session-memory freshness checks, pending-resume boundary payload, and `decision_router` short-reply heuristics: `truffles-api/app/services/reasoning_core.py:354`, `truffles-api/app/services/reasoning_core.py:371`, `truffles-api/app/services/reasoning_core.py:394`, `truffles-api/app/services/reasoning_core.py:410`, `truffles-api/app/services/reasoning_core.py:438`.
- `FACT`: `_normalize_payload_for_delegation(...)` uses `TurnPlanner().coerce_inbound(...)` plus media extraction to rewrite inbound message text before delegation when media caption normalization changes the message: `truffles-api/app/services/reasoning_core.py:495`, `truffles-api/app/services/reasoning_core.py:497`, `truffles-api/app/services/reasoning_core.py:506`.
- `INFERENCE`: The file is only thin at the final runtime handoff. Around that handoff it still owns several compatibility transformations and typed boundary construction paths.

## 5. Data Reads
- `FACT`: The file reads request payloads, DB handles, secrets, `conversation_id`, `outbox_ids`, and preflight payloads through `ReasoningCoreRequest` and the public entrypoint signatures: `truffles-api/app/services/reasoning_core.py:48`, `truffles-api/app/services/reasoning_core.py:603`, `truffles-api/app/services/reasoning_core.py:619`.
- `FACT`: `_build_conversation_snapshot(...)` reads `conversation.context`, runtime booking state, context-manager canonical state and service carryover, top-level expected-reply fields, session memory, pending-resume boundary payload, and routing matrix entries from frozen `decision_router`: `truffles-api/app/services/reasoning_core.py:361`, `truffles-api/app/services/reasoning_core.py:364`, `truffles-api/app/services/reasoning_core.py:371`, `truffles-api/app/services/reasoning_core.py:394`, `truffles-api/app/services/reasoning_core.py:410`, `truffles-api/app/services/reasoning_core.py:438`, `truffles-api/app/services/reasoning_core.py:458`.
- `FACT`: `_resolve_snapshot_service_referent(...)` reads canonical dialog state projections and legacy `service_carryover` from the context manager: `truffles-api/app/services/reasoning_core.py:311`, `truffles-api/app/services/reasoning_core.py:324`, `truffles-api/app/services/reasoning_core.py:338`.
- `FACT`: `_lookup_preexisting_duplicate_message(...)` reads dedup state from `app.routers.webhook.dedup`: `truffles-api/app/services/reasoning_core.py:475`, `truffles-api/app/services/reasoning_core.py:480`.
- `INFERENCE`: The file still reads a wide set of compatibility/state surfaces even though runtime ownership has been delegated away.

## 6. Data Writes And Side Effects
- `FACT`: The module writes early decision traces through `_record_secret_preflight_trace(...)`, which calls `_record_decision_trace(...)`: `truffles-api/app/services/reasoning_core.py:557`, `truffles-api/app/services/reasoning_core.py:571`.
- `FACT`: `_run_secret_enforced_preflight(...)` invokes `webhook.http._run_preflight(...)` and can therefore trigger the same early-return/preflight side effects as that HTTP helper: `truffles-api/app/services/reasoning_core.py:574`, `truffles-api/app/services/reasoning_core.py:580`.
- `FACT`: Block/degrade artifact builders emit typed `turn_result` / `turn_outcome` artifacts via `TurnExecutor`: `truffles-api/app/services/reasoning_core.py:121`, `truffles-api/app/services/reasoning_core.py:142`, `truffles-api/app/services/reasoning_core.py:259`.
- `FACT`: Public runtime handling itself is only delegated to `consultant_core_v2`: `truffles-api/app/services/reasoning_core.py:633`.
- `INFERENCE`: This module still performs preflight/trace side effects and typed boundary artifact construction even though it no longer owns runtime orchestration.

## 7. Semantic Authority / Deterministic Authority
- `FACT`: `_build_runtime_exception_artifact(...)` and the other `_build_*_artifact(...)` helpers manufacture synthetic block/degrade decisions with explicit reason codes and interaction owners through `TurnExecutor` request builders: `truffles-api/app/services/reasoning_core.py:115`, `truffles-api/app/services/reasoning_core.py:121`, `truffles-api/app/services/reasoning_core.py:141`, `truffles-api/app/services/reasoning_core.py:192`, `truffles-api/app/services/reasoning_core.py:254`.
- `FACT`: `_build_conversation_snapshot(...)` still applies deterministic semantic inference on short replies by checking session memory pending-question contract, `decision_router._is_short_reply(...)`, `_extract_datetime(...)`, `_looks_like_info_query(...)`, `_looks_like_policy_topic(...)`, and pending-resume boundary payload before deriving `reply_slot` and `resume_reason`: `truffles-api/app/services/reasoning_core.py:394`, `truffles-api/app/services/reasoning_core.py:410`, `truffles-api/app/services/reasoning_core.py:419`, `truffles-api/app/services/reasoning_core.py:424`, `truffles-api/app/services/reasoning_core.py:438`, `truffles-api/app/services/reasoning_core.py:443`.
- `FACT`: `_normalize_payload_for_delegation(...)` still rewrites inbound message text based on media caption normalization before delegation: `truffles-api/app/services/reasoning_core.py:495`, `truffles-api/app/services/reasoning_core.py:506`.
- `FACT`: `_finalize_turn_planner_owner_cutover(...)` is retained only as a raising stub that enforces the old shadow owner path is removed: `truffles-api/app/services/reasoning_core.py:599`.
- `INFERENCE`: The file is not a semantic owner, but it still contains deterministic semantic and boundary authority in its compatibility helpers.

## 8. Truth Carriers Touched Here
- `FACT`: `_build_conversation_snapshot(...)` reconstructs `reply_slot`, `resume_reason`, `current_goal`, booking activity, booking datetime, booking time token, and service referent from context carriers such as `booking`, projected expected reply, session memory, pending boundary payload, canonical dialog state, and service carryover: `truffles-api/app/services/reasoning_core.py:354`, `truffles-api/app/services/reasoning_core.py:371`, `truffles-api/app/services/reasoning_core.py:394`, `truffles-api/app/services/reasoning_core.py:438`, `truffles-api/app/services/reasoning_core.py:454`, `truffles-api/app/services/reasoning_core.py:458`.
- `FACT`: The module therefore touches both canonical and legacy compatibility carriers: context `booking`, top-level expected reply, session memory, pending boundary payload, canonical dialog state projections, and legacy `service_carryover`: `truffles-api/app/services/reasoning_core.py:361`, `truffles-api/app/services/reasoning_core.py:371`, `truffles-api/app/services/reasoning_core.py:394`, `truffles-api/app/services/reasoning_core.py:438`, `truffles-api/app/services/reasoning_core.py:324`, `truffles-api/app/services/reasoning_core.py:338`.
- `INFERENCE`: The file is a derived compatibility-view builder over multiple truth carriers, even though it no longer persists the runtime itself.

## 9. Violations Against The Target Canon
- `FACT`: The module still imports and uses frozen `decision_router` helpers for semantic reconstruction and routing-state interpretation: `truffles-api/app/services/reasoning_core.py:21`, `truffles-api/app/services/reasoning_core.py:410`, `truffles-api/app/services/reasoning_core.py:458`.
- `FACT`: It still builds synthetic boundary artifacts in the compatibility layer rather than delegating all such shaping to a narrower preflight/boundary module: `truffles-api/app/services/reasoning_core.py:115`, `truffles-api/app/services/reasoning_core.py:141`, `truffles-api/app/services/reasoning_core.py:192`, `truffles-api/app/services/reasoning_core.py:254`.
- `FACT`: `_build_conversation_snapshot(...)` still reconstructs reply-slot/goal semantics from compatibility carriers after runtime ownership moved elsewhere: `truffles-api/app/services/reasoning_core.py:354`, `truffles-api/app/services/reasoning_core.py:394`, `truffles-api/app/services/reasoning_core.py:438`.
- `INFERENCE`: This file no longer violates `one control path` at the main runtime entrypoint, but it still violates the target cleanup spirit by preserving mixed compatibility semantics and frozen-helper dependencies in a supposedly thin shim.

## 10. Salvageable Parts
- `FACT`: The final delegation surface is salvageable as a temporary compatibility wrapper: `run_reasoning_core(...)` and `handle_webhook_payload(...)` now only forward to `consultant_core_v2`: `truffles-api/app/services/reasoning_core.py:603`, `truffles-api/app/services/reasoning_core.py:619`, `truffles-api/app/services/reasoning_core.py:633`.
- `FACT`: Explicit block/degrade request dataclasses and typed artifact wrappers are potentially reusable if moved into a dedicated compatibility/preflight boundary module: `truffles-api/app/services/reasoning_core.py:48`, `truffles-api/app/services/reasoning_core.py:64`, `truffles-api/app/services/reasoning_core.py:84`, `truffles-api/app/services/reasoning_core.py:115`.
- `INFERENCE`: The salvageable core is the thin delegation shell and explicit typed preflight interfaces, not the snapshot heuristics or frozen-helper dependencies.

## 11. Demotion / Removal Candidates
- `FACT`: `_build_conversation_snapshot(...)` is a demotion candidate because it is a compatibility semantic-view builder over many frozen/context carriers: `truffles-api/app/services/reasoning_core.py:354`.
- `FACT`: `_finalize_turn_planner_owner_cutover(...)` is a dead raiser stub candidate for deletion once no legacy caller depends on it: `truffles-api/app/services/reasoning_core.py:599`.
- `FACT`: The various `_build_*_artifact(...)` helpers are demotion/extraction candidates if preflight/boundary handling is moved out of this shim: `truffles-api/app/services/reasoning_core.py:115`, `truffles-api/app/services/reasoning_core.py:141`, `truffles-api/app/services/reasoning_core.py:192`, `truffles-api/app/services/reasoning_core.py:254`.
- `INFERENCE`: If no non-test caller still imports this module, most of it should either be deleted or reduced to a very small wrapper around `consultant_core_v2`.

## 12. What This Analysis Changes In System Understanding
- `FACT`: `reasoning_core.py` is no longer the active runtime owner path; visible app routing already bypasses it in favor of `consultant_core_v2`.
- `FACT`: The module still carries compatibility logic for boundary artifacts, preflight wrappers, conversation snapshots, and frozen-router helper usage.
- `INFERENCE`: The correct classification today is “dormant/thin runtime delegation shell with non-thin compatibility residue.”
- `INFERENCE`: The next honest hotspot is `truffles-api/app/routers/webhook/decision.py`, because it is the large surviving frozen helper/residual routing surface imported by multiple analyzed hotspots.

## 13. Open Questions
- `UNKNOWN`: Whether any hidden non-test caller still imports `reasoning_core.py` as a public compatibility API.
- `UNKNOWN`: Which, if any, of the conversation-snapshot heuristics are still needed outside tests or diagnostics.
- `UNKNOWN`: Whether all `_build_*_artifact(...)` helpers can be relocated or deleted once compatibility wrappers are finally removed.
