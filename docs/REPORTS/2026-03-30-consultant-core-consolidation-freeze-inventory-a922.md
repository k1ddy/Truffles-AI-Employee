# Consultant-Core Consolidation Freeze Inventory

## Scope

- `truffles-main`: `/home/zhan/truffles-main`
- `governance-lock`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `practical-closure`: `/home/zhan/worktrees/2026-03-29-consultant-core-practical-closure-a922`
- freeze bundle root: `/home/zhan/consolidation_freeze/2026-03-30-consultant-core-consolidation-a922`

## Facts

- consultant-core `W1-W8` code artifacts are present only in `governance-lock`
- `practical-closure` is not a descendant of `531001fc` and does not carry the consultant-core implementation line
- `truffles-main` remains forensic residue and must not be used as continuation base

## Inventory Summary

- total changed paths: 2627
- unique paths: 2552
- overlap-identical paths: 1
- true-conflict paths: 74
- doc conflicts: 8
- code conflicts: 66

## Recommended Consolidation Base

- base worktree: `/home/zhan/worktrees/2026-03-30-consultant-core-consolidation-a922`
- base commit: `531001fc`
- branch: `feat/2026-03-30-consultant-core-consolidation-a922`

## First Transfer Rule

- move all consultant-core implementation artifacts from `governance-lock` first
- import practical/canon docs from `practical-closure` second
- inspect `truffles-main` only for unique residual artifacts not present elsewhere
- no wholesale merge from any dirty checkout

## True-Conflict Shortlist

- `STATE.md` :: governance-lock, practical-closure, truffles-main
- `STRUCTURE.md` :: governance-lock, practical-closure, truffles-main
- `TECH.md` :: practical-closure, truffles-main
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md` :: practical-closure, truffles-main
- `docs/REPORTS/2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md` :: governance-lock, truffles-main
- `docs/TASK_PACKAGES/TP-2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md` :: governance-lock, truffles-main
- `docs/TASK_PACKAGES/TP-2026-03-29-consultant-core-practical-closure-canon-correction-a922.md` :: practical-closure, truffles-main
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md` :: practical-closure, truffles-main
- `ops/diagnose.py` :: governance-lock, practical-closure, truffles-main
- `ops/shadow_replay.py` :: governance-lock, truffles-main
- `prompts/llm_policy_core.md` :: governance-lock, practical-closure, truffles-main
- `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml` :: governance-lock, truffles-main
- `truffles-api/app/routers/admin.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/calendar.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/console.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/outbox_service.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/telegram_webhook.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/webhook/__init__.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/webhook/_legacy.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/webhook/booking.py` :: governance-lock, practical-closure, truffles-main
- `truffles-api/app/routers/webhook/branch_selection.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/webhook/context_manager.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/webhook/decision.py` :: governance-lock, practical-closure, truffles-main
- `truffles-api/app/routers/webhook/dedup.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/webhook/guards.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/webhook/info.py` :: governance-lock, practical-closure, truffles-main
- `truffles-api/app/routers/webhook/media.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/webhook/outbox.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/webhook/pending.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/webhook/policy.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/webhook/response.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/webhook/runtime_primitives.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/webhook/session_memory.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/webhook/shield.py` :: governance-lock, truffles-main
- `truffles-api/app/routers/webhook/trace.py` :: governance-lock, truffles-main
- `truffles-api/app/schemas/intent.py` :: governance-lock, truffles-main
- `truffles-api/app/services/calendar_sync_service.py` :: governance-lock, truffles-main
- `truffles-api/app/services/capability_manifest_service.py` :: governance-lock, truffles-main
- `truffles-api/app/services/console_consultant_verification.py` :: governance-lock, truffles-main
- `truffles-api/app/services/intent_service.py` :: governance-lock, practical-closure, truffles-main
- `truffles-api/app/services/manager_message_service.py` :: governance-lock, truffles-main
- `truffles-api/app/services/reasoning_core.py` :: governance-lock, truffles-main
- `truffles-api/app/services/reminder_service.py` :: governance-lock, truffles-main
- `truffles-api/app/services/runtime_safety.py` :: governance-lock, truffles-main
- `truffles-api/app/services/state_service.py` :: governance-lock, truffles-main
- `truffles-api/app/services/tool_certification_service.py` :: governance-lock, truffles-main
- `truffles-api/app/services/tool_registry_service.py` :: governance-lock, truffles-main
- `truffles-api/app/webhook.py` :: governance-lock, truffles-main
- `truffles-api/app/workers/outbox.py` :: governance-lock, truffles-main
- `truffles-api/tests/__init__.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_booking_dialog_scenarios_script.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_booking_quality_chain_controller.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_booking_quality_judge_suppression.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_booking_quality_response_guard.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_booking_quality_scenario_contract_gate.py` :: practical-closure, truffles-main
- `truffles-api/tests/test_booking_quality_status_gate.py` :: governance-lock, practical-closure, truffles-main
- `truffles-api/tests/test_booking_quality_tool_evidence_gate.py` :: practical-closure, truffles-main
- `truffles-api/tests/test_console_ops_jobs.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_intent.py` :: governance-lock, practical-closure, truffles-main
- `truffles-api/tests/test_llm_policy_core.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_master_info_flow.py` :: practical-closure, truffles-main
- `truffles-api/tests/test_message_endpoint.py` :: governance-lock, practical-closure, truffles-main
- `truffles-api/tests/test_outbox_service_app.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_outbox_transport_degraded.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_outbox_worker_settings.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_owner_resolver.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_pending_pack_lexicons.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_planner_wiring.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_policy_handler_runtime.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_provider_gateway_integration.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_reasoning_core.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_state_service.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_tool_certification_service.py` :: governance-lock, truffles-main
- `truffles-api/tests/test_webhook_dedup.py` :: governance-lock, truffles-main

## Next Step

- build a file-level transfer matrix in this consolidation worktree: `unique -> copy`, `overlap-identical -> verify`, `true-conflict -> manual resolve`