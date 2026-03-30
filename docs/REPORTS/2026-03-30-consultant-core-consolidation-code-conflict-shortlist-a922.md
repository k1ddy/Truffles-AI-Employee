# Consultant-Core Consolidation Code Conflict Shortlist

## Goal

Prioritize the remaining consultant-core code/test conflicts inside the single consolidation worktree so the next manual merge block can start on the highest-value hotspots only.

## Priority Rule

- `P0`: files touched by both consultant-core governance work and practical-closure work, or quality/oracle hotspots needed to continue product work.
- `P1`: consultant-core runtime/core/service/webhook files touched by governance-lock and truffles-main only.
- `P2`: supporting tests and lower-risk operational files.

## P0 shortlist

- `ops/diagnose.py` :: governance-lock,practical-closure,truffles-main
- `prompts/llm_policy_core.md` :: governance-lock,practical-closure,truffles-main
- `truffles-api/app/routers/webhook/booking.py` :: governance-lock,practical-closure,truffles-main
- `truffles-api/app/routers/webhook/decision.py` :: governance-lock,practical-closure,truffles-main
- `truffles-api/app/routers/webhook/info.py` :: governance-lock,practical-closure,truffles-main
- `truffles-api/app/services/intent_service.py` :: governance-lock,practical-closure,truffles-main
- `truffles-api/tests/test_booking_quality_status_gate.py` :: governance-lock,practical-closure,truffles-main
- `truffles-api/tests/test_intent.py` :: governance-lock,practical-closure,truffles-main
- `truffles-api/tests/test_message_endpoint.py` :: governance-lock,practical-closure,truffles-main

## P1 shortlist

- `truffles-api/app/routers/webhook/__init__.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/webhook/_legacy.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/webhook/branch_selection.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/webhook/context_manager.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/webhook/dedup.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/webhook/guards.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/webhook/media.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/webhook/outbox.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/webhook/pending.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/webhook/policy.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/webhook/response.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/webhook/runtime_primitives.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/webhook/session_memory.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/webhook/shield.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/webhook/trace.py` :: governance-lock,truffles-main
- `truffles-api/app/services/calendar_sync_service.py` :: governance-lock,truffles-main
- `truffles-api/app/services/capability_manifest_service.py` :: governance-lock,truffles-main
- `truffles-api/app/services/console_consultant_verification.py` :: governance-lock,truffles-main
- `truffles-api/app/services/manager_message_service.py` :: governance-lock,truffles-main
- `truffles-api/app/services/reasoning_core.py` :: governance-lock,truffles-main
- `truffles-api/app/services/reminder_service.py` :: governance-lock,truffles-main
- `truffles-api/app/services/runtime_safety.py` :: governance-lock,truffles-main
- `truffles-api/app/services/state_service.py` :: governance-lock,truffles-main
- `truffles-api/app/services/tool_certification_service.py` :: governance-lock,truffles-main
- `truffles-api/app/services/tool_registry_service.py` :: governance-lock,truffles-main

## P2 shortlist

- `ops/shadow_replay.py` :: governance-lock,truffles-main
- `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml` :: governance-lock,truffles-main
- `truffles-api/app/routers/admin.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/calendar.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/console.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/outbox_service.py` :: governance-lock,truffles-main
- `truffles-api/app/routers/telegram_webhook.py` :: governance-lock,truffles-main
- `truffles-api/app/schemas/intent.py` :: governance-lock,truffles-main
- `truffles-api/app/webhook.py` :: governance-lock,truffles-main
- `truffles-api/app/workers/outbox.py` :: governance-lock,truffles-main
- `truffles-api/tests/__init__.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_booking_dialog_scenarios_script.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_booking_quality_chain_controller.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_booking_quality_judge_suppression.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_booking_quality_response_guard.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_booking_quality_scenario_contract_gate.py` :: practical-closure,truffles-main
- `truffles-api/tests/test_booking_quality_tool_evidence_gate.py` :: practical-closure,truffles-main
- `truffles-api/tests/test_console_ops_jobs.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_llm_policy_core.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_master_info_flow.py` :: practical-closure,truffles-main
- `truffles-api/tests/test_outbox_service_app.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_outbox_transport_degraded.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_outbox_worker_settings.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_owner_resolver.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_pending_pack_lexicons.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_planner_wiring.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_policy_handler_runtime.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_provider_gateway_integration.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_reasoning_core.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_state_service.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_tool_certification_service.py` :: governance-lock,truffles-main
- `truffles-api/tests/test_webhook_dedup.py` :: governance-lock,truffles-main
