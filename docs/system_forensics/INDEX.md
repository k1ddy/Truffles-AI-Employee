# Consultant Core System Forensics Index

Status: `open`
Baseline snapshot: `8319d9e1` at `2026-03-26T23:01:58+05:00`

## Purpose
This directory is the repo-backed memory system for consultant-core forensic work. It exists to answer, with evidence:
- what the system currently does,
- why it does it,
- what is unfinished,
- what must be removed or demoted,
- what is salvageable,
- and which exact architectural objects must appear before any strategic point can be called `done`.

## Rules
- Every assertion must be tagged as `FACT`, `INFERENCE`, or `UNKNOWN`.
- `FACT` must include file references.
- `UNKNOWN` is mandatory when evidence is incomplete.
- File analyses update cross-cut ledgers after each completed hotspot.
- The final synthesis document is derived from the file analyses and ledgers, not from memory.

## Document Map
- `docs/system_forensics/WORK_METHOD.md` — forensic method and evidence discipline.
- `docs/system_forensics/TEMPLATE_FILE_ANALYSIS.md` — template for each hotspot file.
- `docs/system_forensics/files/app_core_consultant_runtime.md` — completed deep runtime-owner analysis.
- `docs/system_forensics/files/app_core_dialog_state_service.md` — completed deep continuity/state analysis.
- `docs/system_forensics/files/app_services_intent_service.md` — completed deep owner-gateway/context-assembly analysis.
- `docs/system_forensics/files/app_core_turn_executor.md` — completed deep downstream-execution/boundary analysis.
- `docs/system_forensics/files/app_core_turn_planner.md` — completed deep planner/decision-shaping analysis.
- `docs/system_forensics/files/app_core_booking_prompt_owner.md` — completed booking-prompt owner classification (dormant owner-adjacent residue / partial salvage ideas).
- `docs/system_forensics/files/app_services_reasoning_core.md` — completed reasoning-core compatibility shim analysis.
- `docs/system_forensics/files/app_routers_webhook_decision.md` — completed webhook decision megafile / compatibility symbol warehouse analysis.
- `docs/system_forensics/files/app_routers_webhook_legacy.md` — completed `_legacy.py` compatibility import-bus / frozen namespace analysis.
- `docs/system_forensics/files/app_routers_webhook_context_manager.md` — completed context-manager bridge / canonical-dialog-state reconciliation analysis.
- `docs/system_forensics/files/app_routers_webhook_response.md` — completed response-stage orchestration / fallback subsystem analysis.
- `docs/system_forensics/files/app_routers_webhook_booking.md` — completed booking-domain orchestration / prompt / commit subsystem analysis.
- `docs/system_forensics/files/app_routers_webhook_info.md` — completed info-domain orchestration / truth-fallback / carryover subsystem analysis.
- `docs/system_forensics/files/app_routers_webhook_pending.md` — completed pending/manager-active continuity transport / handover subsystem analysis.
- `docs/system_forensics/files/app_routers_webhook_policy.md` — completed policy helper warehouse / law-gate / pack-policy subsystem analysis.
- `docs/system_forensics/files/app_routers_webhook_guards.md` — completed guard / mute / human-lock / clarify subsystem analysis.
- `docs/system_forensics/files/app_routers_webhook_dedup.md` — completed dedup / debounce / duplicate-preflight subsystem analysis.
- `docs/system_forensics/files/app_webhook.md` — completed root-level legacy webhook wrapper / shadow helper warehouse analysis.
- `docs/system_forensics/files/app_main.md` — completed main FastAPI composition-root / mounted-router evidence analysis.
- `docs/system_forensics/files/app_routers_webhook_init.md` — completed narrowed webhook-package export-contract analysis.
- `docs/system_forensics/files/tests_test_message_endpoint.md` — completed mixed active-ingress plus legacy-wrapper/_legacy contract warehouse analysis.
- `docs/system_forensics/files/tests_test_webhook_dedup.md` — completed dedup-family package-surface vs extracted-module contract split analysis.
- `docs/system_forensics/files/tests_test_webhook_response.md` — completed response-family package-surface vs extracted-module contract split analysis.
- `docs/system_forensics/files/tests_test_webhook_booking.md` — completed booking-family package-surface vs extracted-module contract split analysis.
- `docs/system_forensics/files/tests_test_booking_chaos_dialogs.md` — completed explicit narrowed-package split guard analysis.
- `docs/system_forensics/files/app_routers_outbox_service.md` — completed dedicated outbox-worker endpoint / package-export caller analysis.
- `docs/system_forensics/files/app_routers_webhook_outbox.md` — completed real outbox transport-helper implementation / wrapper-chain analysis.
- `docs/system_forensics/files/tests_test_outbox_service_app.md` — completed dedicated outbox-service contract / package-export pin analysis.
- `docs/system_forensics/files/tests_test_provider_gateway_integration.md` — completed direct outbox-helper contract / provider-transport coverage analysis.
- `docs/system_forensics/files/app_outbox_service_app.md` — completed dedicated outbox-service FastAPI composition-root / deployment-surface analysis.
- `docs/system_forensics/files/app_routers_admin.md` — completed mounted admin router / duplicated outbox-entrypoint analysis.
- `docs/system_forensics/files/tests_test_admin_legacy_auth.md` — completed mounted admin-router auth coverage / outbox-route omission analysis.
- `docs/system_forensics/files/tests_test_outbox_transport_degraded.md` — completed direct outbox transport-degradation helper contract analysis.
- `docs/system_forensics/files/app_workers_outbox.md` — completed standalone outbox-worker loop and package-seam caller analysis.
- `docs/system_forensics/files/app_routers_console.md` — completed mounted console ops-job outbox execute caller analysis.
- `docs/system_forensics/ledgers/CONTROL_PATHS.md` — active and compatibility control-path ledger.
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md` — semantic authority and rewrite map.
- `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md` — truth carriers and their roles.
- `docs/system_forensics/ledgers/STATE_SURFACE_INVENTORY.md` — persistent/runtime/message state surfaces.
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md` — deterministic stages that validate, block, or rewrite.
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md` — extraction blockers and dependency graph.
- `docs/system_forensics/ledgers/SALVAGEABLE_COMPONENTS.md` — reusable parts vs demotion targets.
- `docs/system_forensics/ledgers/DO_NOT_REPEAT.md` — proven failure modes and forbidden execution patterns.
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md` — accumulating whole-system synthesis.
- `docs/system_forensics/final/RESEARCH_BRIEF.md` — external research contract: mission, constraints, open questions, and acceptance rubric.
- `docs/system_forensics/final/RESEARCH_SOURCE_PACK.md` — prioritized reading order for internal forensic evidence plus external framing materials.
- `docs/system_forensics/final/RESEARCH_OUTPUT_SCHEMA.md` — required structure for external research deliverables.
- `docs/system_forensics/final/EXTERNAL_RESEARCH_PROMPT.md` — ready-to-send prompt for external architecture researchers.
- `docs/system_forensics/final/TARGET_DECISION.md` — accepted target architecture decision distilled from forensic plus external research.
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — finite workstream program translating the target decision into ordered execution families.
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md` — contract for the only hot-path semantic owner artifact.
- `docs/system_forensics/final/BINDING_PLAN_V1.md` — contract for the deterministic binding boundary between meaning and execution.
- `docs/system_forensics/final/TURN_JOURNAL_V1.md` — contract for the append-only canonical turn journal.
- `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md` — contract for the single primary canonical conversation read model.
- `docs/system_forensics/final/NEXT_AGENT_FULL_PROMPT.md` — full zero-context execution brief for the next implementation agent.

## Analysis Order
1. `truffles-api/app/core/consultant_runtime.py` — completed.
2. `truffles-api/app/core/dialog_state_service.py` — completed.
3. `truffles-api/app/services/intent_service.py` — completed.
4. `truffles-api/app/core/turn_executor.py` — completed.
5. `truffles-api/app/core/turn_planner.py` — completed.
6. `truffles-api/app/core/booking_prompt_owner.py` — completed.
7. `truffles-api/app/services/reasoning_core.py` — completed.
8. `truffles-api/app/routers/webhook/decision.py` — completed.
9. `truffles-api/app/routers/webhook/_legacy.py` — completed.
10. `truffles-api/app/routers/webhook/context_manager.py` — completed.
11. `truffles-api/app/routers/webhook/response.py` — completed.
12. `truffles-api/app/routers/webhook/booking.py` — completed.
13. `truffles-api/app/routers/webhook/info.py` — completed.
14. `truffles-api/app/routers/webhook/pending.py` — completed.
15. `truffles-api/app/routers/webhook/policy.py` — completed.
16. `truffles-api/app/routers/webhook/guards.py` — completed.
17. `truffles-api/app/routers/webhook/dedup.py` — completed.
18. `truffles-api/app/webhook.py` — completed.
19. `truffles-api/app/main.py` — completed.
20. `truffles-api/app/routers/webhook/__init__.py` — completed.
21. `truffles-api/tests/test_message_endpoint.py` — completed.
22. `truffles-api/tests/test_webhook_dedup.py` — completed.
23. `truffles-api/tests/test_webhook_response.py` — completed.
24. `truffles-api/tests/test_webhook_booking.py` — completed.
25. `truffles-api/tests/test_booking_chaos_dialogs.py` — completed.
26. `truffles-api/app/routers/outbox_service.py` — completed.
27. `truffles-api/app/routers/webhook/outbox.py` — completed.
28. `truffles-api/tests/test_outbox_service_app.py` — completed.
29. `truffles-api/tests/test_provider_gateway_integration.py` — completed.
30. `truffles-api/app/outbox_service_app.py` — completed.
31. `truffles-api/app/routers/admin.py` — completed.
32. `truffles-api/tests/test_admin_legacy_auth.py` — completed.
33. `truffles-api/tests/test_outbox_transport_degraded.py` — completed.
34. `truffles-api/app/workers/outbox.py` — completed.
35. `truffles-api/app/routers/console.py` — completed.
36. `truffles-api/tests/test_outbox_worker_settings.py` and `truffles-api/tests/test_console_ops_jobs.py` outbox caller contract pins — next.

## Current Scope Completed
- The forensic system itself is created.
- Deep runtime-owner analysis is recorded for `consultant_runtime.py`.
- Deep continuity/state analysis is recorded for `dialog_state_service.py`.
- Deep owner-gateway/context-assembly analysis is recorded for `intent_service.py`.
- Deep downstream-execution/boundary analysis is recorded for `turn_executor.py`.
- Deep planner/decision-shaping analysis is recorded for `turn_planner.py`.
- Booking-prompt owner classification is recorded for `booking_prompt_owner.py`.
- Reasoning-core compatibility-shim analysis is recorded for `reasoning_core.py`.
- Webhook decision megafile / compatibility symbol warehouse analysis is recorded for `decision.py`.
- `_legacy.py` compatibility import-bus / frozen namespace analysis is recorded.
- Context-manager bridge / canonical-dialog-state reconciliation analysis is recorded.
- Response-stage orchestration / fallback subsystem analysis is recorded.
- Booking-domain orchestration / prompt / commit subsystem analysis is recorded.
- Info-domain orchestration / truth-fallback / carryover subsystem analysis is recorded.
- Pending/manager-active continuity transport / handover subsystem analysis is recorded.
- Policy helper warehouse / law-gate / pack-policy subsystem analysis is recorded.
- Root-level legacy webhook wrapper / shadow helper warehouse analysis is recorded.
- Main FastAPI composition-root / mounted-router evidence analysis is recorded.
- Narrowed webhook-package export-contract analysis is recorded.
- Mixed active-ingress plus legacy-wrapper/_legacy contract warehouse analysis is recorded for `test_message_endpoint.py`.
- Dedup-family package-surface vs extracted-module contract split analysis is recorded.
- Response-family package-surface vs extracted-module contract split analysis is recorded.
- Booking-family package-surface vs extracted-module contract split analysis is recorded.
- Explicit narrowed-package split guard analysis is recorded.
- Dedicated outbox-worker endpoint / package-export caller analysis is recorded.
- Real outbox transport-helper implementation / wrapper-chain analysis is recorded.
- Dedicated outbox-service contract / package-export pin analysis is recorded.
- Direct outbox-helper contract / provider-transport coverage analysis is recorded.
- Dedicated outbox-service FastAPI composition-root / deployment-surface analysis is recorded.
- Mounted admin router / duplicated outbox-entrypoint analysis is recorded.
- Mounted admin-router auth coverage / outbox-route omission analysis is recorded.
- Direct outbox transport-degradation helper contract analysis is recorded.
- Standalone outbox-worker loop and package-seam caller analysis is recorded.
- Mounted console ops-job outbox execute caller analysis is recorded.
- Cross-cut ledgers and final synthesis have been updated from the first thirty-five hotspot analyses.

## Current Scope Not Completed
- No strategic architecture point is closed.
- `consultant_core_v2` is still not a standalone runtime module-set.
- The system still has multiple continuity/truth carriers.
- The active owner gateway still lives beside legacy semantic helpers in `intent_service.py`.
- `booking_prompt_owner.py` and `reasoning_core.py` are now classified as compatibility residue/shims; `decision.py` is now classified as a frozen compatibility symbol warehouse; `_legacy.py` is now classified as the active compatibility import bus that keeps that frozen namespace live across modular webhook code; `context_manager.py` is now classified as the state-side compatibility bridge that reconciles canonical-dialog-state and legacy sidecars; `response.py` is now classified as the legacy response-stage orchestration/fallback subsystem; `booking.py` is now classified as the legacy booking-domain orchestration / prompt / commit subsystem; `info.py` is now classified as the legacy info-domain orchestration / truth-fallback / carryover subsystem; `pending.py` is now classified as the legacy pending/manager-active continuity transport / handover subsystem; `policy.py` is now classified as the legacy policy helper warehouse / law-gate / pack-policy subsystem; `guards.py` is now classified as the legacy guard / mute / human-lock / clarify subsystem; `dedup.py` is now classified as the extracted-but-shadowed dedup / debounce preflight subsystem; `app/webhook.py` is now classified as an unmounted legacy wrapper plus stale shadow helper warehouse with weaker debug/secret semantics than the mounted HTTP wrapper; `app/main.py` and `app/routers/webhook/__init__.py` now prove the mounted/runtime package split is already narrow; `outbox_service.py` is now classified as a live worker endpoint that keeps the package export `_process_outbox_rows` alive; `webhook/outbox.py` is now classified as the actual transport-helper implementation owner behind that chain; `app/outbox_service_app.py` is now classified as a separate worker-app deployment surface for that same chain; `admin.py` is now classified as a mounted admin router that duplicates the outbox worker orchestration on the main app; `test_admin_legacy_auth.py` is now classified as selective admin coverage that proves the outbox admin route is not visibly pinned; `test_outbox_transport_degraded.py` is now classified as direct helper coverage that does not preserve the wrapper/export seam; `app/workers/outbox.py` is now classified as the live standalone outbox-worker loop plus scheduler bundle that still imports the package seam; `app/routers/console.py` is now classified as the mounted console ops-job caller and another live outbox execute surface; and the remaining caller-surface debt in this slice is now concentrated in the direct repo-contract pins around those worker/console outbox paths, especially `test_outbox_worker_settings.py` and `test_console_ops_jobs.py`.
