# СТРУКТУРА ПРОЕКТА

**Карта: что где лежит, зачем нужно, кому читать.**

---

## КОРЕНЬ

| Файл | Назначение | Кому |
|------|------------|------|
| `STATE.md` | Состояние, план, backlog, история | Архитектор (каждую сессию) |
| `AGENTS.md` | Принципы работы, роли, ошибки | Архитектор (каждую сессию) |
| `STRUCTURE.md` | Этот файл — карта проекта | Оба (каждую сессию) |
| `TECH.md` | Доступы, команды, данные сервера | Кодер |
| `docs/SESSION_INDEX.md` | Индекс активных сессий (single source of truth) | Архитектор/Brain/Hands |
| `docs/SESSIONS/` | Логи сессий (контекст, планы, worktree/branch) | Архитектор/Brain/Hands |
| `docs/SESSIONS/SESSION_TEMPLATE.md` | Шаблон сессионного лога | Архитектор/Brain/Hands |
| `docs/BLOCK_GRAPH.yaml` | Граф блоков (BLOCK_ID/DEPENDS_ON/UNLOCKS/status) для zero-context исполнения | Архитектор/Brain/Hands |
| `docs/DECISIONS/` | Архитектурные DEC и управляющие решения | Архитектор/Brain |
| `docs/ACTIVE_CANON.md` | Короткий operational canon для consultant controlled demolition | Архитектор/Brain/Hands |
| `docs/SOURCE_OF_TRUTH.yaml` | Machine-readable source-of-truth map для semantic/continuity/proof governance | Архитектор/Brain/Hands |
| `docs/LEGACY_SUNSET.yaml` | Sunset/freeze карта legacy consultant core + guard config | Архитектор/Brain/Hands |
| `docs/ACTIVE_PROGRAM.md` | Активная program summary для consultant controlled demolition | Архитектор/Brain/Hands |
| `docs/_generated/` | Generated zero-context agent packet и сопутствующие артефакты | Архитектор/Brain/Hands |
| `docs/_generated/AGENT_PACKET.md` | Минимальный zero-context briefing для нового агента | Архитектор/Brain/Hands |
| `docs/_generated/AGENT_PACKET.json` | Machine-readable agent packet для governance/tooling | Архитектор/Brain/Hands |
| `contracts/` | Канон контрактов (Console API, ошибки) | Архитектор/Frontend |
| `contracts/console_api/schemathesis.toml` | Seed/overrides для Schemathesis contract smoke | Backend/QA |
| `contracts/events/` | Контракты событий (outbox) | Архитектор/Backend |
| `contracts/tenancy/tenant_context.v1.jsonschema` | Канон tenant_context (company/client/branch) | Архитектор/Backend |
| `contracts/capabilities/capabilities.v1.jsonschema` | Канон capabilities (channels/providers/features) | Архитектор/Backend |
| `contracts/consult/consult_playbook.v1.jsonschema` | Канон схемы consult playbooks (domain‑agnostic) | Архитектор/Backend |
| `contracts/consult/consult_controller_output.v1.jsonschema` | Канон контракта consult LLM‑контроллера | Архитектор/Backend |
| `contracts/runtime/` | Versioned runtime contracts for consultant controlled-demolition target core | Architect/Backend |
| `contracts/runtime/policy_decision.v1.jsonschema` | Канон typed semantic owner decision (`PolicyDecision`) | Architect/Backend |
| `contracts/runtime/semantic_decision.v1.jsonschema` | Канон typed hot-path semantic owner artifact (`SemanticDecisionV1`) | Architect/Backend |
| `contracts/runtime/dialog_state.v1.jsonschema` | Канон writable continuity state (`DialogState`) | Architect/Backend |
| `contracts/runtime/boundary_override.v1.jsonschema` | Канон explicit deterministic boundary override | Architect/Backend |
| `contracts/runtime/turn_result.v1.jsonschema` | Канон assembled runtime turn result (`planner -> boundary -> executor -> reply`) | Architect/Backend |
| `contracts/llm/` | Контракты LLM outputs (router + answer_interpreter) | Архитектор/Backend |
| `contracts/llm/dialogue_controller_output.v1.jsonschema` | Контракт LLM‑контроллера (router) | Архитектор/Backend |
| `contracts/llm/answer_interpreter_output.v1.jsonschema` | Контракт LLM answer_interpreter | Архитектор/Backend |
| `contracts/llm/llm_plan_output.v1.jsonschema` | Контракт Hybrid LLM plan | Архитектор/Backend |
| `contracts/llm/llm_policy_core_output.v1.jsonschema` | Контракт LLM policy core | Архитектор/Backend |
| `contracts/packs/` | Pack-compiler artifacts (signal graph, indexes) | Архитектор/Backend |
| `contracts/packs/signal_graph.v1.jsonschema` | Канон сигнального графа (anchors/lexicons) | Архитектор/Backend |
| `contracts/packs/signal_manifest.v1.jsonschema` | Канон signal manifest (regex/tokens/layout map) для signal-layer | Архитектор/Backend |
| `contracts/policy/` | Policy DSL bundles | Архитектор/Backend |
| `contracts/policy/interaction_owner_matrix.v1.jsonschema` | Канон machine-readable owner matrix для active pending-question rows (`M1..M41`) | Архитектор/Backend |
| `contracts/policy/policy_bundle.v1.jsonschema` | Канон policy bundle (guards/sections) | Архитектор/Backend |
| `contracts/integrations/provider_inbound.v1.jsonschema` | Provider inbound envelope (gateway) | Архитектор/Backend |
| `contracts/integrations/provider_outbound.v1.jsonschema` | Provider outbound envelope (gateway) | Архитектор/Backend |
| `contracts/integrations/media_send.v1.jsonschema` | Media send payload (signed URL) | Архитектор/Backend |
| `contracts/integrations/knowledge_snapshot.v1.jsonschema` | Knowledge snapshot payload (signed) | Архитектор/Backend |
| `contracts/events/inbox_event.v1.jsonschema` | Inbox durable event (ingest) | Архитектор/Backend |
| `contracts/events/provider_status.v1.jsonschema` | Provider status callback event | Архитектор/Backend |
| `contracts/integrations/` | Контракты портов/адаптеров | Архитектор/Backend |
| `.pre-commit-config.yaml` | Pre-commit hooks (gitleaks secret scan) | Кодер |
| `.githooks/` | Обязательные git hooks (session_check + session_gate) | Все роли |
| `.github/workflows/monitor-prod-version.yml` | Cron CI alert: prod `/admin/version` must match main | OPS |
| `.github/workflows/platform-admin-control-loop.yml` | Scheduled/dispatch workflow: Platform Admin control-loop (`kpi + anti-drift + optional e2e`) | OPS/Brain/Architect |
| `.github/workflows/session-gate.yml` | CI gate: session log + doc-only policy | Brain/Architect |
| `SUMMARY.md` | Сводка текущей инвентаризации и GAP | Архитектор |
| `scripts/restart_workers.sh` | Перезапуск контейнеров воркеров (`outbox`, `knowledge_activation`, `sentinel`) | OPS |
| `scripts/restart_knowledge_activation_service.sh` | Shadow restart для Knowledge Activation Service (`/knowledge-activation/process`, port `8015`) с image verify + `/health` poll | OPS |
| `scripts/restart_api.sh` | Канонический деплой API (migration gate + version verify) | OPS |
| `scripts/restart_release.sh` | Канонический release API+workers (+ optional activation service + canary artifact) | OPS |
| `scripts/knowledge_activation_postdeploy.sh` | Post-deploy wrapper: reuse `release_guard`, optionally run tenant closeout, and emit machine-readable proof manifest/summary | OPS/Brain |
| `scripts/check_migration_governance.py` | Governance check для SQL миграций (naming/frozen ops migrations) | Backend/OPS |
| `scripts/session_start.sh` | Создать worktree/branch и session log (agent suffix обязателен) | Все роли |
| `scripts/session_check.sh` | Проверка сессии перед commit/push | Все роли |
| `scripts/zero_context_gate.sh` | Проверка полноты TP+Report для zero-context блока | Brain/Architect/Hands |
| `scripts/session_end.sh` | Закрытие сессии + index обновление | Все роли |
| `scripts/session_resume.sh` | Возобновить активную сессию после compaction (по умолчанию SESSION_AGENT) | Все роли |
| `scripts/session_index_rebuild.sh` | Пересобрать `docs/SESSION_INDEX.md` из `docs/SESSIONS/*` | Brain/Architect |
| `scripts/session_audit.sh` | Аудит сессий (статусы/сироты) | Brain/Architect |
| `scripts/session_gate.sh` | Gate для doc-only и session log | Brain/Architect |
| `scripts/build_agent_packet.py` | Генератор/validator для `docs/_generated/AGENT_PACKET.*` | Architect/Brain/Hands |
| `scripts/legacy_freeze_guard.py` | Diff-based guard: freeze новых executable additions в sunset legacy router files | Architect/Backend |
| `scripts/continuity_writer_guard.py` | Diff-based guard: блокирует новые continuity writes вне текущего canonical writer set | Architect/Backend |
| `scripts/proof_path_guard.py` | Diff-based guard: блокирует proof-path drift и proof-only imports | Architect/Backend |
| `scripts/arch_guard.py` | Единый architecture gate (`source_of_truth` consistency + governance guards) | Architect/Backend/QA |
| `scripts/install_hooks.sh` | Установка обязательных hooks | Все роли |
| `scripts/test_api_container.sh` | Контейнерный pytest (drift‑safe, sanitized env) | Backend/QA |
| `scripts/booking_confirm_verify.sh` | Runbook скрипт: booking confirm verification + evidence | QA/OPS/Brain |
| `scripts/booking_dialog_scenarios.py` | Генератор/adaptor booking‑диалогов (10–15 ходов, перебивки, медиа‑шаблоны) с proof-path sanitize ownership, делегированным в `llm_quality_contracts.py` | QA/OPS |
| `scripts/booking_quality_matrix_resumable.sh` | Resumable LLM-quality matrix runner (skip completed, retry/backoff, stop-the-line, report/state) | QA/OPS/Brain |
| `scripts/quality_artifact_report.py` | Отчёт по последним llm‑quality артефактам (по часам/типам) | QA/OPS/Brain |
| `scripts/platform_admin_control_loop.sh` | Единый wrapper Platform Admin control-loop (`kpi guard + anti-drift + optional e2e`) | OPS/Brain/QA |
| `scripts/restart_knowledge_gateway.sh` | Перезапуск Knowledge Gateway (shadow) | OPS |
| `scripts/restart_provider_gateway.sh` | Перезапуск Provider Gateway (shadow) | OPS |
| `scripts/restart_inbox_service.sh` | Перезапуск Inbox Service (shadow) | OPS |
| `scripts/restart_decision_core.sh` | Перезапуск Decision Core (shadow) | OPS |
| `scripts/restart_outbox_service.sh` | Перезапуск Outbox Service (shadow) | OPS |
| `scripts/restart_console_web.sh` | Пересборка + перезапуск Console Web (build info) | OPS/Frontend |
| `docker-compose.yml` | **Заглушка:** инфра‑стек в `/home/zhan/infrastructure/docker-compose*.yml` | DevOps |
| `ops/reset.sql` | **Emergency:** закрыть все open handovers + вернуть `bot_active` | Кодер/OPS |
| `ops/diagnose.py` | Диагностика диалогов/trace/outbox + `dialog-report` (one-command) | QA/OPS/Brain |
| `ops/console_platform_admin_kpi_snapshot.py` | Weekly KPI snapshot для Platform Admin (runtime + LOC + UX/e2e signals) | Brain/OPS/QA |
| `ops/platform_admin_remediation_assist.py` | Deterministic remediation-assist plan/brief generator from Platform Admin KPI snapshot | Brain/OPS/QA |
| `ops/console_owner_admin_kpi_snapshot.py` | KPI snapshot для Owner/Admin (`T+0/T+24`, impact baseline/replay, fail-fast guard) | Brain/OPS/QA |
| `ops/owner_admin_control_loop.py` | Orchestration wrapper Owner/Admin control-loop (`t0/t24`: snapshot + gate + brief + log) | Brain/OPS/QA |
| `ops/knowledge_activation_closeout.py` | Tenant-level closeout artifact for Knowledge Activation (`release guard + branch preview/live invariants`) | Brain/OPS/QA |
| `ops/shadow_replay.py` | Shadow replay report (decision_meta/trace comparison) | QA/OPS/Brain |
| `ops/backfill_branch_rag.py` | Backfill Qdrant branch metadata from published knowledge | OPS/Brain |
| `ops/keycloak-theme/` | Тема Keycloak (CSS + лого) для брендинга auth | OPS/Frontend |
| `truffles-api/` | Backend API + workers | Backend |
| `truffles-api/docker-compose.test.yml` | Test‑compose overrides (test containers, no prod env) | Backend/QA |
| `truffles-api/scripts/apply_sql_migrations.py` | SQL migration runner (`schema_migrations` + checksum guard) | Backend/OPS |
| `truffles-api/scripts/knowledge_activation_release_guard.py` | Release/canary guard for Knowledge Activation (`go/no_go` JSON from health/process/admin metrics) | Backend/OPS |
| `truffles-api/app/services/onboarding_state.py` | Server-side onboarding state machine (Console) | Backend |
| `truffles-api/app/services/console_confirmations.py` | Confirmation safeguards for destructive Console actions | Backend |
| `truffles-api/app/services/console_owner_admin.py` | Owner/Admin business helpers extracted from `console.py` | Backend |
| `truffles-api/app/services/console_consultant_verification.py` | Owner/Admin consultant verification overview + safe simulation session service | Backend |
| `truffles-api/app/services/console_knowledge_preflight.py` | Knowledge publish preflight helpers (`draft_hash`, recent validate gate) | Backend |
| `truffles-api/app/services/capabilities_runtime.py` | Runtime capabilities context (client_capabilities → decision/booking) | Backend |
| `truffles-api/app/services/knowledge_runtime.py` | Runtime published pack truth (knowledge_versions → demo_salon resolver) | Backend |
| `truffles-api/app/services/reasoning_core.py` | Unified Reasoning Core API (signals -> gates -> actions -> compose -> trace); now also owns bounded direct owner-replacement cuts for safe info, catalog, service-query, master-query, and booking-verification fact slices | Backend/Architect |
| `truffles-api/app/services/pack_compiler_service.py` | Pack compiler (compiled artifacts, hashing, schema validation) | Backend/Architect |
| `truffles-api/app/core/` | Typed target consultant runtime core scaffolding (`planner/boundary/executor/dialog_state/realizer`) | Backend/Architect |
| `truffles-api/app/core/booking_prompt_owner.py` | Canonical non-frozen booking-prompt candidate owner for initial booking prompt resolution and timeout-recovery shaping | Backend/Architect |
| `truffles-api/app/core/intent_routing.py` | Typed lexical intent-routing primitive detector for new-core ingress bridges | Backend/Architect |
| `truffles-api/app/core/turn_planner.py` | Typed `PolicyDecision` seam for future planner cutover | Backend/Architect |
| `truffles-api/app/core/semantic_decision.py` | Typed `SemanticDecisionV1` owner artifact and normalization contract for canaried hot-path meaning | Backend/Architect |
| `truffles-api/app/core/boundary_validator.py` | Typed `BoundaryOverride` seam for deterministic boundary validation | Backend/Architect |
| `truffles-api/app/core/dialog_state_service.py` | Typed `DialogState` seam for future single continuity writer; now also owns expected-reply/question-contract plus session-memory question-writer, session-memory normalization, canonical referent shaping, session-memory freshness, ancillary context-carrier writer bridges, and carryover manager-writer bridges | Backend/Architect |
| `truffles-api/app/services/llm_quality_contracts.py` | Shared proof-path expectation/scenario-contract owner extracted from proof-only `ops/diagnose.py` and `scripts/booking_dialog_scenarios.py`, including booking-scenario merge, post-coverage repair, and llm-turn sanitize orchestration | Backend/QA/Architect |
| `truffles-api/app/core/response_realizer.py` | Typed reply envelope seam for future response realization | Backend/Architect |
| `truffles-api/app/core/turn_executor.py` | Typed `TurnResult`/owner-cutover/bounded-boundary execution seam for future core execution pipeline; now also owns planner-owner artifact assembly and bounded runtime-exception plus preflight/ignore boundary request carriers | Backend/Architect |
| `truffles-api/app/services/learned_response_service.py` | Auto-ingest + approval wiring for learned responses | Backend |
| `truffles-api/app/services/calendar_sync_service.py` | Calendar provider sync via outbox + cursors + busy blocks | Backend |
| `truffles-api/app/services/tool_registry_service.py` | Tool registry executor (calendar/catalog) for LLM plan | Backend |
| `truffles-api/app/services/pack_query_backend_service.py` | Distributed pack-query backend adapter contract (runtime_local/shadow/primary) | Backend |
| `truffles-api/app/services/booking_signal_service.py` | Booking/date/time signal helpers (manifest-backed regex/tokens + lexicon) | Backend |
| `truffles-api/app/services/booking_transition_owner.py` | Single-writer booking/profile transition owner (`tool outcome -> state/profile`) | Backend |
| `truffles-api/app/services/signal_manifest_service.py` | Signal manifest runtime compiler/loader (schema validation + signature cache + version meta) | Backend |
| `truffles-api/app/services/interaction_owner_matrix_service.py` | Cached loader/validator for the machine-readable interaction owner matrix | Backend |
| `truffles-api/app/services/owner_resolver.py` | Pure owner-row resolver that matches runtime turns against matrix rows and emits row/evidence decisions | Backend |
| `truffles-api/app/services/appointment_reminder_service.py` | Appointment reminder/follow-up jobs + outbox enqueue | Backend |
| `truffles-api/app/services/metrics_daily_service.py` | Daily metrics snapshot (metrics_daily) | Backend |
| `truffles-api/app/services/marketing/service.py` | Marketing Pro lifecycle/audience/preflight/execute/retry logic | Backend |
| `truffles-api/app/models/alert_event.py` | DB model for alert events (analytics) | Backend |
| `truffles-api/app/models/console_confirmation.py` | DB model for confirmation requests (Console) | Backend |
| `truffles-api/app/models/console_consultant_verification_finding.py` | DB model for owner/admin consultant verification findings and remediation state | Backend |
| `truffles-api/app/models/console_consultant_verification_session.py` | DB model for owner/admin consultant verification sessions | Backend |
| `truffles-api/app/models/console_consultant_verification_turn.py` | DB model for persisted owner/admin consultant verification transcript turns | Backend |
| `truffles-api/app/models/knowledge_version.py` | DB model for immutable draft/published knowledge artifacts; legacy `sync_*` fields remain as compatibility aliases for activation progress | Backend |
| `truffles-api/app/models/knowledge_activation_job.py` | DB model for knowledge live-activation attempts (`queued/running/ready/failed/stuck`) and retry/error observability | Backend |
| `truffles-api/app/models/console_macro.py` | DB model for Inbox macros (Console) | Backend |
| `truffles-api/app/models/marketing_campaign.py` | Marketing campaign model (status/approval/preflight fields) | Backend |
| `truffles-api/app/models/marketing_campaign_recipient.py` | Materialized audience snapshot per campaign | Backend |
| `truffles-api/app/models/marketing_delivery_event.py` | Marketing delivery timeline/audit events | Backend |
| `truffles-api/app/models/marketing_consent.py` | Marketing consent state (`opt_in/opt_out`) | Backend |
| `truffles-api/app/models/marketing_suppression.py` | Manual/automatic suppression registry | Backend |
| `truffles-api/app/models/outbox_status_event.py` | DB model for outbox status events (analytics) | Backend |
| `truffles-api/app/models/tenants_fleet_prewarm_job.py` | Durable prewarm dispatch queue model for tenants fleet cache rebuild | Backend |
| `truffles-api/app/knowledge_gateway_app.py` | Отдельный app для Knowledge Gateway | Backend |
| `truffles-api/app/provider_gateway_app.py` | Отдельный app для Provider Gateway | Backend |
| `truffles-api/app/inbox_service_app.py` | Отдельный app для Inbox Service | Backend |
| `truffles-api/app/decision_core_app.py` | Отдельный app для Decision Core | Backend |
| `truffles-api/app/outbox_service_app.py` | Отдельный app для Outbox Service | Backend |
| `truffles-api/app/knowledge_activation_service_app.py` | Отдельный app для Knowledge Activation Service | Backend |
| `truffles-api/app/routers/inbox_service.py` | Router для Inbox Service | Backend |
| `truffles-api/app/routers/decision_core.py` | Router для Decision Core | Backend |
| `truffles-api/app/routers/outbox_service.py` | Router для Outbox Service | Backend |
| `truffles-api/app/routers/knowledge_activation_service.py` | Router для Knowledge Activation Service | Backend |
| `truffles-api/app/workers/knowledge_activation.py` | Dedicated worker for direct `knowledge_activation_jobs` claiming / processing / stuck detection | Backend |
| `truffles-api/migrations/015_add_inbox_events.sql` | Migration: inbox_events (durable inbox store) | Backend/OPS |
| `truffles-api/migrations/016_add_console_confirmations.sql` | Migration: console_confirmations (destructive safeguards) | Backend/OPS |
| `truffles-api/migrations/017_add_console_macros.sql` | Migration: console_macros (Inbox быстрые ответы) | Backend/OPS |
| `truffles-api/migrations/018_add_learning_consent_pack_candidates.sql` | Migration: learning consent + anonymization/retention + pack candidates | Backend/OPS |
| `truffles-api/migrations/019_add_handover_trigger_types.sql` | Migration: expand handovers.trigger_type allowed values | Backend/OPS |
| `truffles-api/migrations/020_add_handover_meta.sql` | Migration: handovers meta snapshot + trigger_message_id | Backend/OPS |
| `truffles-api/migrations/021_add_outbox_status_events.sql` | Migration: outbox_status_events (status history) | Backend/OPS |
| `truffles-api/migrations/022_add_alert_events.sql` | Migration: alert_events (no_response, etc.) | Backend/OPS |
| `truffles-api/migrations/034_marketing_pro_v1.sql` | Migration: Marketing Pro v1 schema (campaign state + audience/suppression/delivery events) | Backend/OPS |
| `truffles-api/migrations/041_add_tenants_fleet_prewarm_jobs.sql` | Migration: durable tenants fleet prewarm dispatch queue | Backend/OPS |
| `truffles-api/migrations/059_add_knowledge_version_sync_status.sql` | Migration: knowledge version sync-status fields (`pending/ready/failed`) plus safe-mode backfill for truthful publish/sync UX | Backend/OPS |
| `truffles-api/scripts/console_e2e_seed.py` | Seed для стабильных console‑e2e данных | Backend/QA |
| `console-web/` | Console UI (Next.js, Dockerfile) | Frontend |
| `console-web/src/app/insights/page.tsx` | Insights/Analytics page (read-only daily metrics) | Frontend |
| `console-web/src/app/marketing/page.tsx` | Marketing Pro lifecycle UI (preview/approval/preflight/execute) | Frontend |
| `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationWorkspace.tsx` | Thin composition shell for consultant verification owner/admin lanes | Frontend |
| `console-web/src/app/business/consultant-verification/_hooks/useConsultantVerificationWorkspaceState.ts` | Page-local query/mutation/view-model orchestration for consultant verification workspace | Frontend |
| `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationTeamToolsPanel.tsx` | Secondary team-tools disclosure for consultant verification (`recent sessions`, `compare`, `findings`) | Frontend |
| `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationOwnerSetupLane.tsx` | Left owner lane for consultant verification (`new session`, source/mode controls, scenario library) | Frontend |
| `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationTranscriptLane.tsx` | Middle transcript/composer lane for consultant verification | Frontend |
| `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationReviewLane.tsx` | Right review lane for consultant verification (`explainer`, summary, team tools) | Frontend |
| `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationComparePanel.tsx` | Owner/Admin consultant verification live-vs-draft compare panel and readiness scorecard | Frontend |
| `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationFindingsPanel.tsx` | Owner/Admin consultant verification findings list, status updates, and draft retest actions | Frontend |
| `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationScenarioLibrary.tsx` | Owner/Admin consultant verification scenario catalog cards and quick-run actions | Frontend |
| `console-web/src/app/business/consultant-verification/_components/ConsultantVerificationSessionSummaryPanel.tsx` | Owner/Admin consultant verification session summary and replay controls | Frontend |
| `console-web/src/app/knowledge/_components/KnowledgePackInspectorPanel.tsx` | Support-only Client Pack inspector panel used inside `Knowledge` disclosure | Frontend |
| `console-web/src/app/knowledge/_components/KnowledgePlatformAdminFleetPanel.tsx` | Platform-admin fleet context panel extracted from `Knowledge` route shell | Frontend |
| `console-web/src/app/knowledge/_components/KnowledgeBranchReadinessPanel.tsx` | Branch readiness/sync/patch panel extracted from `Knowledge` route shell | Frontend |
| `console-web/src/app/knowledge/_components/KnowledgeStudioFlow.tsx` | Main owner flow shell for `Knowledge` stepper + stage panels | Frontend |
| `console-web/src/app/knowledge/_components/KnowledgeRollbackConfirmDialog.tsx` | Rollback confirmation dialog extracted from `Knowledge` page | Frontend |
| `console-web/src/app/knowledge/_components/KnowledgeLearningCandidatesPanel.tsx` | Support-only learning-candidates panel used inside `Knowledge` disclosure | Frontend |
| `console-web/src/app/knowledge/_hooks/useKnowledgeStudioState.ts` | Page-local query/mutation/view-model orchestration for `Knowledge` studio route | Frontend |
| `console-web/src/app/business/consultant-verification/_lib/presentation.ts` | Owner-facing verdict/explanation presentation helpers for consultant verification | Frontend |
| `console-web/src/components/TenantsScopedErrorSummary.tsx` | Scoped error summary для Tenants workspace зон | Frontend |
| `console-web/src/components/TenantsSensitiveIdCell.tsx` | Mask/reveal/copy ячейка чувствительного `instance_id` с audit hook | Frontend |
| `console-web/src/components/TenantsQuickCreatePanel.tsx` | Вынесенный quick-create блок Tenants (компания/клиент/филиал) с явными label-id для a11y | Frontend |
| `console-web/src/components/TenantsOperationalKpiPanel.tsx` | Вынесенная панель операционных KPI/alert hooks/weekly snapshots для Tenants (platform_admin) | Frontend |
| `console-web/src/components/ConsoleOwnerScopeGate.tsx` | Shared owner branch-selection gate reused by `Knowledge` and `Проверка консультанта` | Frontend |
| `console-web/src/components/ConsoleSupportDisclosure.tsx` | Shared progressive-disclosure wrapper for secondary owner/admin tools | Frontend |
| `console-web/src/app/tenants/use-tenants-scope-derived-state.ts` | Derived scope/state hook для `/tenants` (context names/maps/filter options) | Frontend |
| `console-web/src/app/tenants/tenants-page-helpers.ts` | Shared helpers/types/formatters for Tenants page (lifecycle audit, branch patch/snapshot, scope/date labels) | Frontend |
| `console-web/src/app/tenants/use-tenants-action-queue.ts` | Hook для action-queue orchestration и archive predicate в `/tenants` | Frontend |
| `console-web/src/app/tenants/use-tenants-operational-model.ts` | Hook для вычисления Tenants operational KPI/drilldown/alert/report модели | Frontend |
| `console-web/e2e/` | Playwright smoke/login/setup тесты (storageState) | Frontend/QA |
| `console-web/e2e/support/keycloak-auth.ts` | Shared Keycloak auth helper for Playwright `login/smoke/inspect_case` live lanes | Frontend/QA |
| `console-web/e2e/calendar-operator.spec.ts` | Dedicated deterministic Calendar operator acceptance lane: booking creation, blocked states, follow-up completion, and medium-width layout proof | Frontend/QA |
| `console-web/e2e/tenants-a11y.spec.ts` | Live Playwright + Axe evidence для Tenants (desktop/mobile) | Frontend/QA |
| `console-web/eslint.config.js` | ESLint flat config для console-web | Frontend |
| `console-web/.env.e2e.example` | Шаблон env для console‑e2e | Frontend/QA |
| `console-web/public/brand/` | Бренд‑ассеты консоли (логотипы) | Frontend |
| `console-web/src/app/api/calendar/callback/route.ts` | Console API proxy for Google Calendar OAuth callback | Frontend |
| `console-web/src/app/api/console-client-events/route.ts` | Bounded console-web telemetry route for selection-gate/session-expiry client events, logging only the allowed event family | Frontend |
| `docs/CONSOLE_GUIDE.md` | Guide по Console (API, тесты, дебаг) | Frontend/Backend |
| `docs/CONSOLE_AUDIT/` | Полная инвентаризация Console (ролевая карта + страницы + код/интеграции) | Frontend/Backend/Architect |
| `docs/CONSOLE_AUDIT/pages/insights.md` | Audit page: Insights/Analytics | Frontend/Architect |
| `docs/CONSOLE_AUDIT/pages/marketing.md` | Audit page: Marketing lifecycle + audience/preflight | Frontend/Architect |
| `docs/CONSOLE_AUDIT/UX_BACKLOG.md` | UX backlog (bugs/UX debt) по реализованной Console | Frontend/Backend/Architect |
| `docs/system_forensics/` | Repo-backed forensic memory for consultant-core architecture/state/control-path analysis | Architect/Brain/Hands |
| `docs/system_forensics/INDEX.md` | Index of hotspot analyses, ledgers, and final synthesis | Architect/Brain/Hands |
| `docs/system_forensics/WORK_METHOD.md` | Forensic method: FACT/INFERENCE/UNKNOWN discipline and update protocol | Architect/Brain/Hands |
| `docs/system_forensics/TEMPLATE_FILE_ANALYSIS.md` | Template for per-file forensic hotspot analysis | Architect/Brain/Hands |
| `docs/system_forensics/files/` | Deep per-file forensic analyses for consultant-core hotspots | Architect/Brain/Hands |
| `docs/system_forensics/files/app_core_consultant_runtime.md` | First deep hotspot analysis: active runtime orchestration owner | Architect/Brain/Hands |
| `docs/system_forensics/files/app_core_dialog_state_service.md` | Second deep hotspot analysis: continuity/state megaservice and truth-carrier reconciliation | Architect/Brain/Hands |
| `docs/system_forensics/files/app_services_intent_service.md` | Third deep hotspot analysis: active owner gateway, context assembly, and legacy semantic helper co-location | Architect/Brain/Hands |
| `docs/system_forensics/files/app_core_turn_executor.md` | Fourth deep hotspot analysis: downstream execution, boundary artifacts, and post-owner semantic reconstruction | Architect/Brain/Hands |
| `docs/system_forensics/files/app_core_turn_planner.md` | Fifth deep hotspot analysis: planner decision shaping, owner-input/output adaptation, and typed policy decision carriers | Architect/Brain/Hands |
| `docs/system_forensics/files/app_core_booking_prompt_owner.md` | Sixth deep hotspot analysis: booking-prompt owner classification and alternate booking recovery lane audit | Architect/Brain/Hands |
| `docs/system_forensics/files/app_services_reasoning_core.md` | Seventh deep hotspot analysis: reasoning-core compatibility shim, boundary helpers, and delegation residue | Architect/Brain/Hands |
| `docs/system_forensics/files/app_routers_webhook_decision.md` | Eighth deep hotspot analysis: webhook decision megafile, compatibility symbol warehouse, and frozen router residue | Architect/Brain/Hands |
| `docs/system_forensics/files/app_routers_webhook_legacy.md` | Ninth deep hotspot analysis: `_legacy.py` compatibility import bus, frozen namespace fanout, and cyclic adapter residue | Architect/Brain/Hands |
| `docs/system_forensics/files/app_routers_webhook_context_manager.md` | Tenth deep hotspot analysis: context-manager state bridge, canonical-dialog-state reconciliation, and legacy continuity coupling | Architect/Brain/Hands |
| `docs/system_forensics/files/app_routers_webhook_response.md` | Eleventh deep hotspot analysis: response-stage orchestration, fallback subsystem, and user-visible compatibility side effects | Architect/Brain/Hands |
| `docs/system_forensics/files/app_routers_webhook_booking.md` | Twelfth deep hotspot analysis: booking-domain orchestration, prompt/confirmation loops, and booking-side commit/escalation behavior | Architect/Brain/Hands |
| `docs/system_forensics/files/app_routers_webhook_info.md` | Thirteenth deep hotspot analysis: info-domain orchestration, truth-fallback behavior, and info-side carryover/escalation behavior | Architect/Brain/Hands |
| `docs/system_forensics/files/app_routers_webhook_pending.md` | Fourteenth deep hotspot analysis: pending/manager-active continuity transport, handover routing, and Telegram-forwarding behavior | Architect/Brain/Hands |
| `docs/system_forensics/files/app_routers_webhook_policy.md` | Fifteenth deep hotspot analysis: policy helper warehouse, law-gate/policy-pack routing, and policy-side escalation behavior | Architect/Brain/Hands |
| `docs/system_forensics/files/app_routers_webhook_guards.md` | Sixteenth deep hotspot analysis: guard/mute/human-lock/clarify subsystem and guard-side routing residue | Architect/Brain/Hands |
| `docs/system_forensics/files/app_routers_webhook_dedup.md` | Seventeenth deep hotspot analysis: dedup/debounce preflight subsystem and shadowed inbound-owner residue | Architect/Brain/Hands |
| `docs/system_forensics/files/app_webhook.md` | Eighteenth deep hotspot analysis: unmounted legacy webhook wrapper, stale shadow helper warehouse, and wrapper contract drift | Architect/Brain/Hands |
| `docs/system_forensics/files/app_main.md` | Nineteenth deep hotspot analysis: main FastAPI composition root and mounted-router evidence | Architect/Brain/Hands |
| `docs/system_forensics/files/app_routers_webhook_init.md` | Twentieth deep hotspot analysis: narrowed webhook-package export contract and remaining public surface | Architect/Brain/Hands |
| `docs/system_forensics/files/tests_test_message_endpoint.md` | Twenty-first deep hotspot analysis: mixed active-ingress and legacy-wrapper/_legacy contract warehouse | Architect/Brain/Hands |
| `docs/system_forensics/files/tests_test_webhook_dedup.md` | Twenty-second deep hotspot analysis: dedup package-surface vs extracted-module contract split | Architect/Brain/Hands |
| `docs/system_forensics/files/tests_test_webhook_response.md` | Twenty-third deep hotspot analysis: response package-surface vs extracted-module contract split | Architect/Brain/Hands |
| `docs/system_forensics/files/tests_test_webhook_booking.md` | Twenty-fourth deep hotspot analysis: booking package-surface vs extracted-module contract split | Architect/Brain/Hands |
| `docs/system_forensics/files/tests_test_booking_chaos_dialogs.md` | Twenty-fifth deep hotspot analysis: explicit narrowed-package split guard for legacy handler exports | Architect/Brain/Hands |
| `docs/system_forensics/files/app_routers_outbox_service.md` | Twenty-sixth deep hotspot analysis: dedicated outbox-worker endpoint and live `_process_outbox_rows` package-export caller chain | Architect/Brain/Hands |
| `docs/system_forensics/files/app_routers_webhook_outbox.md` | Twenty-seventh deep hotspot analysis: real outbox transport-helper implementation and wrapper/export seam | Architect/Brain/Hands |
| `docs/system_forensics/files/tests_test_outbox_service_app.md` | Twenty-eighth deep hotspot analysis: dedicated outbox-service contract and package-export pin | Architect/Brain/Hands |
| `docs/system_forensics/files/tests_test_provider_gateway_integration.md` | Twenty-ninth deep hotspot analysis: direct outbox-helper/provider integration contract coverage | Architect/Brain/Hands |
| `docs/system_forensics/files/app_outbox_service_app.md` | Thirtieth deep hotspot analysis: dedicated outbox-service FastAPI composition root and deployment surface | Architect/Brain/Hands |
| `docs/system_forensics/files/app_routers_admin.md` | Thirty-first deep hotspot analysis: mounted admin router and duplicated outbox-entrypoint orchestration | Architect/Brain/Hands |
| `docs/system_forensics/files/tests_test_admin_legacy_auth.md` | Thirty-second deep hotspot analysis: mounted admin auth coverage and omitted live outbox route | Architect/Brain/Hands |
| `docs/system_forensics/files/tests_test_outbox_transport_degraded.md` | Thirty-third deep hotspot analysis: direct outbox transport-degradation helper contract | Architect/Brain/Hands |
| `docs/system_forensics/files/app_workers_outbox.md` | Thirty-fourth deep hotspot analysis: standalone outbox worker loop and live package-seam caller | Architect/Brain/Hands |
| `docs/system_forensics/files/app_routers_console.md` | Thirty-fifth deep hotspot analysis: mounted console ops-job outbox execute caller | Architect/Brain/Hands |
| `docs/system_forensics/ledgers/` | Cross-cut ledgers for control paths, semantic ownership, truth carriers, and cutover blockers | Architect/Brain/Hands |
| `docs/system_forensics/final/` | Final synthesized system analysis built from file analyses and ledgers | Architect/Brain/Hands |
| `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md` | Accumulating whole-system synthesis and guide for future exact work | Architect/Brain/Hands |
| `docs/system_forensics/final/RESEARCH_BRIEF.md` | External research contract for scalable target architecture and migration thinking | Architect/Brain/Hands |
| `docs/system_forensics/final/RESEARCH_SOURCE_PACK.md` | Prioritized research reading pack across forensic corpus and external framing sources | Architect/Brain/Hands |
| `docs/system_forensics/final/RESEARCH_OUTPUT_SCHEMA.md` | Required schema for external research deliverables and decision-ready recommendations | Architect/Brain/Hands |
| `docs/system_forensics/final/EXTERNAL_RESEARCH_PROMPT.md` | Ready-to-send prompt for external architecture research based on the forensic corpus | Architect/Brain/Hands |
| `docs/system_forensics/final/TARGET_DECISION.md` | Canonical accepted target-architecture decision for consultant-core execution | Architect/Brain/Hands |
| `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` | Ordered finite workstream program derived from forensic and external research | Architect/Brain/Hands |
| `docs/system_forensics/final/SEMANTIC_DECISION_V1.md` | Contract for the single hot-path semantic owner artifact | Architect/Brain/Hands |
| `docs/system_forensics/final/BINDING_PLAN_V1.md` | Contract for deterministic binding between semantic decision and execution | Architect/Brain/Hands |
| `docs/system_forensics/final/TURN_JOURNAL_V1.md` | Contract for append-only canonical turn journal | Architect/Brain/Hands |
| `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md` | Contract for the single primary canonical conversation projection | Architect/Brain/Hands |
| `docs/system_forensics/final/NEXT_AGENT_FULL_PROMPT.md` | Full zero-context execution prompt for the next implementation agent | Architect/Brain/Hands |
| `docs/runbooks/CHAOS_SIM.md` | Chaos-sim runbook (human-like диалоги, evaluator, артефакты) | QA/OPS/Brain |
| `docs/runbooks/DIALOG_REPORT.md` | Dialog-report runbook (one-command анализ диалогов) | QA/OPS/Brain |
| `docs/runbooks/BOOKING_CONFIRM_VERIFY.md` | Booking confirm verification runbook | QA/OPS/Brain |
| `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md` | Deploy/canary/rollback runbook for dedicated Knowledge Activation transport | Brain/Architect/OPS |
| `docs/runbooks/INBOX_CALENDAR_WAVE4_RELEASE.md` | Wave4 release runbook for Inbox/Calendar (`canary -> go/no-go -> rollback`) | Brain/Architect/OPS |
| `docs/runbooks/INBOX_SEMANTIC_WAVE22_VALIDATION.md` | Wave22 semantic validation runbook for Inbox manager/admin/history/booking matrix | Brain/Architect/QA |
| `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-semantic-decision-hot-path-a922.md` | Workstream 1 / Family 1 bounded Task Package for `SemanticDecisionV1` hot-path cutover and post-owner mutation guard | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-state-writer-owner-read-cut-a922.md` | Workstream 1 / Family 2 bounded Task Package for state-writer canonical owner-read cut and execution/existing semantic authority reduction on the canaried path | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-executor-semantic-output-constriction-a922.md` | Workstream 1 / Family 3 bounded Task Package for narrowing executor canaried output to operational enrichment only | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-planner-synthetic-authority-cut-a922.md` | Workstream 1 / Family 4 bounded Task Package for removing planner-core general synthetic semantic minting and guarding the canaried runtime path | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-owner-adjacent-shadow-cut-a922.md` | Workstream 1 / Family 5 bounded Task Package for making canaried owner-adjacent semantic compatibility carriers shadow-only | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-inbox-calendar-ux-reconstruction-closeout-a1.md` | Closeout Task Package for Inbox/Calendar wave4 release discipline (`flag rollback + live lane evidence + runbook`) | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-console-e2e-live-auth-hardening-a1.md` | Follow-up Task Package for live no-mocks auth/case inspection hardening after wave4 closeout | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-console-e2e-auth-helper-unification-a1.md` | Follow-up Task Package for shared auth helper unification in `login/smoke/inspect_case` Playwright specs | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-console-e2e-auth-helper-rollout-a1.md` | Follow-up Task Package for rollout of shared auth helper into the remaining Playwright specs | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave5-a1.md` | Wave5 Task Package for action-driven SLA contract in Inbox (`backend contract -> frontend surfaces`) | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave6-a1.md` | Wave6 Task Package for bounded single-case Inbox actions (`reassign/snooze/reopen`) before bulk scope | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave6-partb-a1.md` | Wave6 Part B Task Package for backend-first bulk/supervisor Inbox actions (`bulk reassign/snooze` -> queue selection UI) | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-a1.md` | Wave7 Task Package for backend action-macro contract in Inbox (`structured macro action + execute endpoint`) | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave7-partb-a1.md` | Wave7 Part B Task Package for macro UI builder/apply flow in Inbox workspace | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-a1.md` | Wave8 Task Package for unified inbox+bookings workspace shell (`Part A`) with embedded case-linked bookings panel | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave8-partb-a1.md` | Wave8 Part B Task Package for context/panel preservation between inbox workspace and full calendar route | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-a1.md` | Wave9 Part A Task Package for supervisor/admin queue governance in Inbox (`role-aware views + visible fields`, no new route) | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave9-partb-a1.md` | Wave9 Part B Task Package for server-backed owner/unassigned governance in Inbox (`assignee filter + queue assignee endpoint`, no new route) | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-a1.md` | Wave10 Part A Task Package for factual assignee workload signals in Inbox reassignment surfaces (`load counts in reassign selects`, no fake availability) | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave10-partb-a1.md` | Wave10 Part B Task Package for one-click recommended routing in current reassignment surfaces (`recommendation CTA`, no hidden automation) | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-closeout-review-a1.md` | Closeout-review Task Package for final ТЗ coverage classification and merge-go/no-go decision after Waves 1-10 | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave11-a1.md` | Wave11 Task Package for post-merge live hardening: reopen-safe sync semantics + inbox left-rail usability reconstruction | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-a1.md` | Wave12 Task Package for server-owned policy-based routing automation on existing reassignment surfaces (`least_open_cases`, single-case + bulk) | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave12-live-validation-a1.md` | Post-merge live-validation Task Package for proving Wave12 policy-routing mutation path on real backend without mocks | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave13-a1.md` | Wave13 Task Package for server-owned business status contract and badge-noise reduction in inbox queue/header surfaces | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave14-a1.md` | Wave14 Task Package for server-owned inbox queue-view semantics instead of local predicates over partial pages | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-a1.md` | Wave15 Task Package for operator-safe action feedback: remove raw sync reason leakage and separate business outcome from secondary sync warnings | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave15-live-validation-a1.md` | Post-merge live-validation Task Package for proving Wave15 feedback semantics on real backend without mocks | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-06-inbox-calendar-ux-reconstruction-wave16-a1.md` | Wave16 Task Package for full redesign of overloaded inbox action surfaces and left queue rail | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave17-a1.md` | Wave17 Task Package for separating inbox filter contract into queue mode, owner scope, advanced refinements, and presentation prefs | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave17-closeout-a1.md` | Wave17 closeout review Task Package for deciding merge-go and whether any saved-views follow-up is actually required | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave18-a1.md` | Wave18 Task Package for fixing inbox filter-state correctness via explicit contract, precedence rules, and deterministic validation | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave19-a1.md` | Wave19 Task Package for semantic decomposition of the full bot->case->manager->booking->history operator chain | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave20-a1.md` | Wave20 Task Package for inbox panel IA reconstruction with explicit open/closed/all modes and history/archive access | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave21-a1.md` | Wave21 Task Package for cross-surface semantic integration between bot-origin cases and calendar bookings | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-a1.md` | Wave22 Task Package for forbidden-state matrix, deterministic acceptance, and live closeout of the new inbox semantic model | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave22-live-proof-a1.md` | Wave22 live-proof closure Task Package for explicit safe-case validation and blocker classification | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave23-a1.md` | Wave23 Task Package for post-closeout defect clustering and the queue-state-first maturity sequence for Inbox/Calendar | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave24-a1.md` | Wave24 Task Package for server-owned `Queue State Canon` across Inbox/Calendar before saved views, presets, and shareable URLs | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave25-a1.md` | Wave25 Task Package for personal saved views on top of the shared inbox/calendar queue-state canon | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave26-a1.md` | Wave26 Task Package for managed team presets on the shared inbox/calendar saved-view object with branch/role-targeted defaults | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave27-a1.md` | Wave27 Task Package for shareable inbox/calendar queue URLs via explicit params plus optional `view_id` on the same queue-state/saved-view canon | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-07-inbox-calendar-ux-reconstruction-wave28-a1.md` | Wave28 Task Package for supervisor-grade booking governance (`follow-up owner`, `due`, `history`) on top of the calendar queue-state/share-URL canon | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave29-a1.md` | Wave29 Task Package for explainable richer routing v1 (`follow_up_sla_balance`) on top of explicit booking governance and queue-state canon | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave30-a1.md` | Wave30 Task Package for server-owned assignee routing profiles (`available/paused/follow_up_only` + optional capacity) before any skill/presence-aware routing | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave31-a1.md` | Wave31 planning Task Package to decide whether any routing v2/capability-input layer is justified after Wave30 or whether the product should stop at routing profiles | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave32-a1.md` | Wave32 Task Package for deep Inbox/Calendar UX+logic audit after Wave30, locking surface-decomposition and operator-proof work before any routing v2 discussion | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave33-a1.md` | Wave33 Task Package for Inbox first-screen decomposition: keep only triage controls inline and move saved views/filters/view/bulk flows into secondary surfaces | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave34-a1.md` | Wave34 Task Package for Calendar first-screen decomposition: keep queue triage primary and move filters/saved views/governance/scheduling into secondary surfaces | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave35-a1.md` | Wave35 Task Package for deterministic operator workflow/layout proof across rebuilt Inbox/Calendar secondary surfaces and medium-width layouts | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave36-a1.md` | Wave36 Task Package for full Calendar operator-grade rebuild: plain-language copy, sanitized follow-up ownership, guided booking composer, inline validation, visual inspections, and misuse-proof testing | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-08-inbox-calendar-ux-reconstruction-wave37-a1.md` | Wave37 Task Package for Calendar acceptance recovery after merged Wave36: focused booking entry, service-first time discovery, intuitive language, hard guardrails, and full operator proof | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-09-inbox-calendar-ux-reconstruction-wave38-a1.md` | Wave38 Task Package for post-merge Calendar hardening: deterministic filters, natural phone input, booking edit/reschedule/cancel lifecycle, and full operator proof | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-09-inbox-calendar-ux-reconstruction-wave39-a1.md` | Wave39 Task Package for Calendar action-safety envelope: server-owned action contract, fail-closed lifecycle, explicit state machines, exhaustive proof, and post-merge replay | Brain/Architect |

| `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-program-a920.md` | Program Task Package for owner-facing consultant verification and trust-under-pressure surface in `Business` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave1-a920.md` | Wave1 Task Package for owner consultant verification entrypoint, IA foundation, and service-boundary contract | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave2-a920.md` | Wave2 Task Package for safe simulation session kernel and no-side-effect consultant verification API | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave3-a920.md` | Wave3 Task Package for owner-readable chat workspace, verdicts, and explanation panels | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave4-a920.md` | Wave4 Task Package for scenario library, stress presets, replay, and session summary | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave5-a920.md` | Wave5 Task Package for weak-spot capture, failure-family grouping, and remediation status loop | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-wave6-a920.md` | Wave6 Task Package for `live vs draft` compare, finding retest, and readiness gate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-13-owner-consultant-verification-closeout-a920.md` | Closeout Task Package for deterministic proof, canary rollout, and post-merge monitoring of consultant verification | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-14-owner-consultant-verification-knowledge-safety-program-a921.md` | Remediation program Task Package for safe Knowledge authoring, truthful draft/live verification, and owner-safe validation/publish messaging | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-verification-branch-publish-flow-a3.md` | Task Package for inline branch repair on consultant verification and truthful publish/sync semantics with retry-sync | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-owner-knowledge-stabilization-reset-a4.md` | Stabilization-reset Task Package for async knowledge sync, bounded owner states, and owner-surface overload containment | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-console-knowledge-sync-state-unification-a4.md` | RCA-backed Task Package for unifying owner-facing sync-state truth after async publish/retry/rollback mutations | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-console-owner-scope-gate-unification-a5.md` | Task Package for extracting one shared owner scope-gate across `Knowledge` and `Проверка консультанта` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-message-preflight-compat-a922.md` | Bounded Task Package for `/message` compatibility with no-conversation new-core preflight/degrade outcomes | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-sender-branch-ignore-slice-a922.md` | Bounded Task Package for moving active branch sender ignore ownership from legacy preflight into `reasoning_core` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-duplicate-message-preflight-slice-a922.md` | Bounded Task Package for moving preexisting duplicate `message_id` skip ownership into `reasoning_core` without changing legacy write-side dedup | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-remote-branch-phone-ignore-slice-a922.md` | Bounded Task Package for moving same-client branch-phone ignore ownership into `reasoning_core` on eligible non-secret paths | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-tenant-context-guard-slice-a922.md` | Bounded Task Package for moving tenant-context invalid/mismatch rejects into `reasoning_core` on eligible non-secret paths | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-missing-remote-jid-slice-a922.md` | Bounded Task Package for moving `missing_remote_jid` reject ownership into `reasoning_core` on eligible non-secret paths | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-missing-tenant-context-slice-a922.md` | Bounded Task Package for moving `missing_tenant_context` reject ownership into `reasoning_core` on eligible non-secret paths | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-proof-path-ast-blackbox-slice-a922.md` | Bounded Task Package for removing AST-derived proof authority from `test_booking_quality_response_guard.py` and extending proof guard coverage | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-proof-helper-extraction-slice-a922.md` | Bounded Task Package for moving expectation/scenario-contract helpers out of proof-only `ops/diagnose.py` into a shared service module | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-booking-scenario-expectation-helper-slice-a922.md` | Bounded Task Package for moving booking-scenario expectation merge helpers out of `scripts/booking_dialog_scenarios.py` into the shared llm-quality contracts module | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-proof-followup-rewrite-helper-slice-a922.md` | Bounded Task Package for moving orphan/check-booking/reschedule followup rewrite helpers out of `scripts/booking_dialog_scenarios.py` into the shared llm-quality contracts module | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-secret-safe-preflight-cutover-a922.md` | Bounded Task Package for making wrapped `/webhook` ingress secret-safe from `reasoning_core` by reusing the legacy preflight bridge before any local early exits | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-preflight-cache-bridge-a922.md` | Bounded Task Package for reusing cached wrapped-ingress preflight payload across the frozen duplicate non-secret preflight call without editing `decision.py` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-runtime-context-loader-bridge-a922.md` | Bounded Task Package for moving the initial wrapped-ingress runtime capability/truth loader pass into `reasoning_core` via branch-aware context-local overrides | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-intent-primitives-bridge-a922.md` | Bounded Task Package for moving the first lexical intent-routing primitive pass into `reasoning_core` through request-scoped semantic overrides | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-domain-router-bridge-a922.md` | Bounded Task Package for moving the first domain-router classification pass into `reasoning_core` through request-scoped semantic overrides | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-protective-lexical-bridge-a922.md` | Bounded Task Package for moving `opt_out` and `frustration` lexical guard ownership into `reasoning_core` through the existing request-scoped semantic override bridge | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-confirmation-refusal-bridge-a922.md` | Bounded Task Package for moving confirmation and refusal lexical-response ownership into wrapped ingress through the existing request-scoped signal override bridge | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-ingress-conversation-snapshot-bridge-a922.md` | Bounded Task Package for loading a read-only active conversation snapshot in `reasoning_core` before semantic bridge entry so manager-active turns stop priming bot-reply overrides | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-slot-normalization-helper-slice-a922.md` | Bounded Task Package for extracting slot/time/partial-date normalize helpers from proof-only `booking_dialog_scenarios.py` into shared llm-quality contracts | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-post-coverage-rewrite-excision-a922.md` | Bounded Task Package for moving post-coverage orphan-repair orchestration out of proof-only `booking_dialog_scenarios.py` into shared llm-quality contracts | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-pending-question-contract-helper-slice-a922.md` | Bounded Task Package for moving pure pending-question contract progression helpers out of proof-only `booking_dialog_scenarios.py` into shared llm-quality contracts | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-question-contract-writer-bridge-a922.md` | Bounded Task Package for moving expected-reply/question-contract continuity write shaping out of `context_manager.py` into `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-question-writer-bridge-a922.md` | Bounded Task Package for moving session-memory question bookkeeping write shaping out of `session_memory.py` into `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-normalization-bridge-a922.md` | Bounded Task Package for moving session-memory payload normalization and validation out of `session_memory.py` into `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-canonical-referent-bridge-a922.md` | Bounded Task Package for moving canonical dialog-state referent set/project/prune shaping out of `context_manager.py` into `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-freshness-bridge-a922.md` | Bounded Task Package for moving session-memory freshness stamping and expiry evaluation out of `session_memory.py` into `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-ancillary-context-carrier-writer-bridge-a922.md` | Bounded Task Package for moving remaining confirmation/ASR/style/memory top-level context-carrier write/delete semantics out of `context_manager.py` into `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-carryover-manager-writer-bridge-a922.md` | Bounded Task Package for moving manager-level class/service/consult carryover write/delete semantics out of `context_manager.py` into `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-session-memory-carryover-reset-bridge-a922.md` | Bounded Task Package for moving carryover-family reset delete semantics out of `_reset_session_memory(...)` in `session_memory.py` into `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-booking-verification-not-found-owner-cutover-a922.md` | Bounded Task Package for making frozen `decision.py` unreachable for the deterministic `calendar.get_booking` `not_found` reply path via the existing `reasoning_core` owner cutover | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-portfolio-not-found-owner-cutover-a922.md` | Bounded Task Package for making frozen `decision.py` unreachable for the deterministic `catalog.portfolio` `not_found` reply path via the existing safe catalog owner cutover | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-master-specialist-followup-slice-a922.md` | Bounded Task Package for moving master/specialist followup detection and expectation helpers out of proof-only `booking_dialog_scenarios.py` into shared llm-quality contracts | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-controller-route-bridge-a922.md` | Bounded Task Package for priming reset-safe greeting and strong out-of-domain controller-route overrides from `reasoning_core` before the frozen delegate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-policy-handoff-override-bridge-a922.md` | Bounded Task Package for priming reset-safe explicit-manager-request `route_llm_policy_core(...)` handoff overrides from `reasoning_core` before the frozen delegate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-catalog-fact-owner-cutover-a922.md` | Bounded Task Package for making frozen `decision.py` unreachable for safe read-only catalog fact turns by letting `reasoning_core` directly realize existing `services_overview`, `location`, and `portfolio` policy overrides | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-service-query-fact-owner-cutover-a922.md` | Bounded Task Package for making frozen `decision.py` unreachable for grounded safe pricing and duration `catalog.service_query` fact turns via `reasoning_core` direct realization | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-master-query-fact-owner-cutover-a922.md` | Bounded Task Package for making frozen `decision.py` unreachable for grounded safe master-service-match `master_query` fact turns via `reasoning_core` direct realization | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-booking-verification-owner-cutover-a922.md` | Bounded Task Package for making frozen `decision.py` unreachable for the safe read-only `calendar.get_booking` ok-path via `reasoning_core` direct realization | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-style-reference-policy-override-bridge-a922.md` | Bounded Task Package for priming reset-safe text-only style-reference `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-booking-verification-policy-override-bridge-a922.md` | Bounded Task Package for priming reset-safe booking-verification `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-services-overview-policy-override-bridge-a922.md` | Bounded Task Package for priming reset-safe services-overview `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-location-parking-policy-override-bridge-a922.md` | Bounded Task Package for priming richer reset-safe location/parking `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-hours-policy-override-bridge-a922.md` | Bounded Task Package for priming richer reset-safe hours `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-pricing-policy-override-bridge-a922.md` | Bounded Task Package for priming richer reset-safe grounded pricing `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-duration-policy-override-bridge-a922.md` | Bounded Task Package for priming richer reset-safe grounded duration `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-promotions-policy-override-bridge-a922.md` | Bounded Task Package for priming reset-safe generic promotions `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-promotions-rules-policy-override-bridge-a922.md` | Bounded Task Package for priming reset-safe promotions-rules `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-contact-policy-override-bridge-a922.md` | Bounded Task Package for priming reset-safe explicit contact `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-master-query-policy-override-bridge-a922.md` | Bounded Task Package for priming reset-safe grounded `master_query` `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-master-query-collect-override-bridge-a922.md` | Bounded Task Package for priming reset-safe service-missing `master_query` collect `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-pricing-service-clarify-policy-override-bridge-a922.md` | Bounded Task Package for priming reset-safe service-missing `pricing` collect `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate when no active service referent exists | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-duration-service-clarify-policy-override-bridge-a922.md` | Bounded Task Package for priming reset-safe service-missing `duration` collect `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate when no active service referent exists | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-bookability-time-collect-policy-override-bridge-a922.md` | Bounded Task Package for priming reset-safe active-service-gated `booking` time-collect `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate when active booking lacks temporal scope | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-time-availability-followup-bridge-a922.md` | Bounded Task Package for priming reset-safe active-name specific-time availability followup `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate under active name-resume state | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-deictic-time-availability-followup-bridge-a922.md` | Bounded Task Package for priming reset-safe active-name deictic-time availability followup `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate under active name-resume state with an exact-time snapshot anchor | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-deictic-day-availability-followup-bridge-a922.md` | Bounded Task Package for priming reset-safe active-name deictic-day availability followup `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate under active name-resume state with an exact-time snapshot anchor | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-relative-date-availability-followup-bridge-a922.md` | Bounded Task Package for priming reset-safe active-name relative-date availability followup `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate under active name-resume state with an exact-time snapshot anchor | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-active-name-relative-daypart-availability-followup-bridge-a922.md` | Bounded Task Package for priming reset-safe active-name relative-date plus daypart availability followup `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate under active name-resume state with an exact-time snapshot anchor | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-specialist-date-range-followup-bridge-a922.md` | Bounded Task Package for priming reset-safe specialist-availability date-range followup `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate under active booking/service context | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-grounded-specialist-transition-bridge-a922.md` | Bounded Task Package for priming reset-safe grounded specialist-availability transition `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate under active booking/service/datetime context | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-service-choice-specialist-weekend-followup-bridge-a922.md` | Bounded Task Package for priming reset-safe service-choice specialist weekend followup `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate under reply-slot service context with grounded service text | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-service-choice-specialist-weekday-followup-bridge-a922.md` | Bounded Task Package for priming reset-safe service-choice specialist weekday followup `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate under reply-slot service context with grounded service text | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-service-choice-specialist-day-followup-bridge-a922.md` | Bounded Task Package for priming reset-safe service-choice specialist day-only followup `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate under reply-slot service context with grounded service text and pure day tokens | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-service-choice-specialist-daypart-followup-bridge-a922.md` | Bounded Task Package for priming reset-safe service-choice specialist daypart followup `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate under reply-slot service context with grounded service text and pure day+daypart tokens | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-service-choice-specialist-exact-time-followup-bridge-a922.md` | Bounded Task Package for priming reset-safe service-choice specialist exact-time followup `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate under reply-slot service context with grounded service text and pure day+time tokens | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-semantic-bridge-growth-guard-a922.md` | Corrective Task Package for freezing further semantic bridge growth in generic ingress hotspots via an AST-based architecture guard and machine-readable hotspot snapshot | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-execution-strategy-lock-a922.md` | Corrective Task Package for locking the approved execution strategy into source-of-truth, generated agent packet, and session-start bootstrap | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-turn-planner-safe-info-owner-cutover-a922.md` | Bounded Task Package for the first real owner-replacement cutover: `turn_planner` + `reasoning_core` directly own safe info-fact replies for `contact`, `hours`, `promotions`, and `promotions_rules` before frozen delegate | Brain/Architect |
| `docs/SEMANTIC_BRIDGE_GUARD.yaml` | Machine-readable hotspot snapshot for guarded semantic bridge families in generic ingress files | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-portfolio-policy-override-bridge-a922.md` | Bounded Task Package for priming reset-safe explicit `portfolio` `route_llm_policy_core(...)` overrides from `reasoning_core` before the frozen delegate | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-management-stateful-helper-slice-a922.md` | Bounded Task Package for finishing the last management/stateful proof helper extraction and collapsing `BookingScenarioPostCoverageRepairCallbacks` to config-only | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-booking-progress-helper-slice-a922.md` | Bounded Task Package for moving booking-progress expectation helpers out of proof-only `booking_dialog_scenarios.py` into shared llm-quality contracts | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-session-memory-projection-slice-a922.md` | Bounded Task Package for routing legacy `session_memory.interaction_state` projection through `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-expected-reply-projection-slice-a922.md` | Bounded Task Package for routing legacy `expected_reply_*` projection through `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-pending-resume-projection-slice-a922.md` | Bounded Task Package for routing legacy `pending_resume` snapshot/restore through `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-canonical-dialog-state-bridge-slice-a922.md` | Bounded Task Package for routing canonical dialog state normalization plus `pending_question_contract`/`interaction_state` bridging through `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-reentry-contract-bridge-slice-a922.md` | Bounded Task Package for routing `re_entry_required` continuity semantics through `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-confirmation-bridge-slice-a922.md` | Bounded Task Package for routing handover/reengage/ASR confirmation continuity semantics through `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-expiring-carrier-bridge-slice-a922.md` | Bounded Task Package for routing `asr_inflight` and `style_reference_pending` continuity semantics through `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-memory-carrier-bridge-slice-a922.md` | Bounded Task Package for routing `memory_profile` and `memory_pending` continuity semantics through `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-class-carryover-canonical-bridge-slice-a922.md` | Bounded Task Package for routing `class_carryover` through a canonical dialog-state mirror in `DialogStateService` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-service-and-consult-carryover-bridge-slice-a922.md` | Bounded Task Package for routing `service_carryover` and `consult_context` fallback shaping through `DialogStateService` while preserving canonical-priority semantics | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-low-confidence-retry-bridge-slice-a922.md` | Bounded Task Package for routing `low_confidence_retry_count` shaping through `DialogStateService` while keeping `retry_offered_at` orchestration unchanged | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-compact-summary-bridge-slice-a922.md` | Bounded Task Package for routing `compact_summary` text/payload shaping through `DialogStateService` while preserving legacy payload shape | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-clarify-attempt-bridge-slice-a922.md` | Bounded Task Package for routing `clarify_attempts` payload shaping through `DialogStateService` while preserving clarify-limit behavior | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-intent-queue-bridge-slice-a922.md` | Bounded Task Package for routing `intent_queue` payload shaping through `DialogStateService` while preserving queue ordering, dedupe, and prompt compatibility | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-owner-convergence-implementation-a922.md` | Corrective implementation Task Package for converging the handover/escalation family into one dedicated non-frozen owner surface instead of continuing seam farming across `reasoning_core.py`, `state_service.py`, and `escalation_service.py` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-state-service-handover-helper-collapse-implementation-a922.md` | Corrective implementation Task Package for deleting the residual handover helper cluster from `state_service.py` after owner convergence so the family no longer depends on a mixed helper host | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-frozen-compat-seam-reduction-a922.md` | Corrective implementation Task Package for deleting the external `_legacy -> decision.py` handover compatibility seam so frozen callers bypass the owner surface middle layer | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-escalation-supporting-helper-closure-a922.md` | Corrective implementation Task Package for deleting the residual owner-specific helper seam from `escalation_service.py` so handover support stays outside the mixed legacy module | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-frozen-read-notify-seam-reduction-a922.md` | Corrective implementation Task Package for deleting the bounded frozen handover read/notify relay so `decision.py` binds directly to the owner surface | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-frozen-internal-self-use-classification-a922.md` | Strict classification Task Package for deciding whether the remaining frozen handover self-use wrappers are still live authority or only compatibility residue | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-owner-boundary-application-family-convergence-a922.md` | Corrective implementation Task Package for deleting the duplicated frozen timeout owner-boundary resolve/derive/apply seam by converging that family into `timeout_owner_boundary_service.py` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-policy-validation-boundary-family-convergence-a922.md` | Corrective implementation Task Package for deleting the frozen policy-validation clarify/collect/guidance family by converging it into one non-frozen boundary owner surface | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-degrade-retry-boundary-family-convergence-a922.md` | Corrective implementation Task Package for deleting the duplicated frozen timeout-degrade retry/clarify/handoff family by converging it into one non-frozen boundary owner surface | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-nonbooking-recovery-boundary-family-convergence-a922.md` | Corrective implementation Task Package for deleting the frozen timeout non-booking recovery reply family by converging it into one non-frozen boundary owner surface | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-booking-specialist-boundary-family-convergence-a922.md` | Corrective implementation Task Package for deleting the frozen timeout booking specialist followup / master-info-interrupt family by converging it into one non-frozen boundary owner surface | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-invalid-schema-specialist-boundary-family-convergence-a922.md` | Corrective implementation Task Package for deleting the frozen invalid-schema specialist-followup family by parameterizing the existing non-frozen specialist boundary owner surface | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-invalid-schema-service-grounded-booking-boundary-family-convergence-a922.md` | Corrective implementation Task Package for deleting the frozen invalid-schema service-grounded booking family by reusing the existing non-frozen contract-validation boundary owner surface | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-pending-slot-question-boundary-family-convergence-a922.md` | Corrective implementation Task Package for deleting the frozen timeout pending-slot-question reply family by reusing the existing non-frozen timeout-degrade boundary owner surface | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-active-name-time-followup-boundary-family-convergence-a922.md` | Corrective implementation Task Package for deleting the frozen timeout active-name time-followup family by converging it into one narrow non-frozen continuity-heavy boundary owner surface | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-policy-core-guard-orchestration-package-a922.md` | Package-level implementation Task Package for deleting the remaining frozen degraded-guard orchestration family by converging it into one dedicated non-frozen guard-boundary owner surface | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-continuity-broader-collapse-package-a922.md` | Package-level implementation Task Package for deleting the residual pending-resume / reset / session-memory continuity family by converging it into `DialogStateService` plus one bounded non-frozen coordinator | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-continuity-broader-collapse-targeted-frozen-waiver-decision-a922.md` | Decision Task Package for proving the continuity package is blocked by narrow frozen pending callsites and locking the exact waiver scope needed for truthful package closure | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-continuity-broader-collapse-targeted-frozen-waiver-implementation-a922.md` | Runtime implementation Task Package for deleting the broader pending/session-memory continuity authority under the exact targeted frozen waiver without moving transport ownership into a new hotspot | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-public-entrypoint-materialization-contract-package-a922.md` | Package-level implementation Task Package for converging the split public-entrypoint materialization family into one shared router-boundary contract surface and retiring legacy eager conversation materialization | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-debounce-buffer-owner-convergence-package-a922.md` | Package-level implementation Task Package for converging the split debounce / buffer / duplicate-message family into the existing non-frozen dedup owner surface and deleting the shadow duplicate probe split | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-proof-black-box-completion-package-a922.md` | Package-level implementation Task Package for converging the remaining proof-path scenario rewrite / expect-repair authority into `llm_quality_contracts.py` and reducing the proof lane to generator-plus-observer boundaries | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-package-a922.md` | Package-level implementation Task Package for deleting the beauty-only platform-evidence seam by converging final closure onto one bounded canary plus matrix plus open-world artifact bundle across the required profiles | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-runtime-target-materialization-package-a922.md` | Package-level implementation Task Package for converging the multi-pack acceptance GAP onto one truthful runtime target materialization family inside the existing platform-admin provisioning/catalog owners | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md` | Package-level re-entry Task Package for the final multi-pack acceptance bundle after truthful `clinic_pack/main` and `generic/main` target materialization | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-demo-salon-noncanonical-lock-failure-family-package-a922.md` | Package-level unblock Task Package for deleting the surviving `demo_salon` non-canonical guarded-lock blocker family before multi-pack acceptance re-entry resumes | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-acceptance-preflight-blocker-package-a922.md` | Package-level blocker Task Package for deleting or truthfully localizing the surviving acceptance-preflight family before any fresh guarded `demo_salon` lock can start | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-acceptance-preflight-l2-transport-blocker-package-a922.md` | Package-level blocker Task Package for deleting or truthfully localizing the surviving non-acceptance `L2` transport / observability family before acceptance preflight can resume | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-acceptance-preflight-l2-expectation-conflict-failure-family-package-a922.md` | Package-level blocker Task Package for deleting or truthfully localizing the surviving completed-run `L2` expectation / judge conflict family before acceptance preflight can reuse a semantically valid `go_to_full` row | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-post-observer-runtime-failure-family-package-a922.md` | Package-level blocker Task Package for locking the surviving completed-run `r14` work to one A -> B -> C runtime reconciliation bundle (`handover_reuse_adapter_drift`, `branch_missing_contract_ownership`, `active_booking_continuity_precedence`) before any new `L2` rerun | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-family-package-a922.md` | Package-level blocker Task Package for locking the surviving `r17` runtime exception to the frozen `booking.py` handover-reuse caller family before any new `L2` rerun | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-targeted-frozen-waiver-decision-a922.md` | Decision Task Package for proving the frozen booking handover-reuse family now needs an exact waiver scope and for invalidating the unwaived runtime attempt as non-progress | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-targeted-frozen-waiver-implementation-a922.md` | Exact-scope targeted frozen-waiver implementation Task Package for deleting the surviving frozen `booking.py` handover-reuse caller drift and validating it with one fresh non-acceptance `L2` rerun | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-preflight-clear-state-contamination-family-package-a922.md` | Package-level blocker Task Package for deleting or truthfully localizing the surviving `r23` reset-before-dialog contamination family before any fresh `L2` rerun can count as canonical evidence | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-authority-closure-plan-a922.md` | Planning Task Package for switching the primary story from proof-path residuals to final live `/webhook` ingress/coordinator owner closure so `semantic_owner`, `continuity_owner`, and `boundary_owner` can converge truthfully | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-decision-a922.md` | Decision Task Package for proving the final ingress/coordinator closure path is now blocked by exact frozen `decision.py` authority and for locking the narrowest admissible waiver scope before runtime work resumes | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-implementation-a922.md` | Exact-scope targeted frozen-waiver implementation Task Package for deleting at least one remaining live ingress/coordinator authority seam from the rooted `decision.py` families without widening beyond the declared waiver scope | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-decision-a922.md` | Decision Task Package for stopping final-ingress seam farming as the main story and locking the next move to one broader owner-replacement bundle over the remaining live `reasoning_core -> decision.py` hotspot | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-owner-replacement-implementation-a922.md` | Implementation Task Package for executing the first bounded broader owner-replacement slice in `reasoning_core` so at least one old live final-ingress seam dies before fallback reaches frozen `decision.py` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-owner-surface-decision-a922.md` | Decision Task Package for stopping the broader-owner implementation bundle once the strongest residual proves non-cuttable under current owner surfaces and for locking the next move to one generic tool-reply owner-surface implementation in existing non-frozen owner files | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-owner-surface-implementation-a922.md` | Implementation Task Package for materializing one reusable generic tool-reply owner surface in `turn_executor.py` and deleting the direct frozen decision/state/payload authority on the surviving tool-reply contour | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-guard-finalize-owner-surface-implementation-a922.md` | Implementation Task Package for materializing one reusable generic tool-reply guard/finalize owner surface in `reasoning_core.py` and deleting the direct frozen guard/finalize entry authority on the surviving tool-reply contour | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-generic-tool-reply-guard-finalize-post-audit-a922.md` | Post-cut audit Task Package for proving whether the remaining `_maybe_apply_fact_guard(...)` authority is still an exact tool-reply residual or already a broader mixed fact-guard family that needs a new decision block | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-decision-a922.md` | Decision Task Package for locking the exact rooted broader fact-guard family, admissible owner destinations, and explicit `booking.py` deferred debt after the post-audit proved the exact tool-reply ladder is saturated | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-targeted-frozen-waiver-decision-a922.md` | Decision Task Package for proving the non-frozen broader fact-guard implementation move is blocked, locking the exact frozen `decision.py` waiver scope, and keeping `booking.py` as explicit deferred debt | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-targeted-frozen-waiver-implementation-a922.md` | Exact-scope targeted frozen-waiver implementation Task Package for deleting the old mixed broader fact-guard authority body in frozen `decision.py` while preserving the injected callable contract for direct and deferred consumers | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fact-guard-family-post-waiver-audit-a922.md` | Post-waiver audit Task Package for proving the surviving fact-guard callback is thin-only and for locking the next move to the broader `reasoning_core -> decision_router` fallback ingress family | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-decision-a922.md` | Decision Task Package for defining the exact broader `public_entrypoint_contract -> reasoning_core -> decision_router` fallback-ingress family, locking admissible owner destinations, and keeping frozen downstream debt explicit before runtime resumes | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-implementation-a922.md` | Implementation Task Package for executing one broader runtime bundle over the rooted `public_entrypoint_contract -> reasoning_core -> decision_router` fallback-ingress family so at least one old fallback-owned frozen residual seam dies before fallback | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-broader-fallback-ingress-family-post-implementation-audit-a922.md` | Audit Task Package for recording which broader fallback-ingress contour actually died, which rooted residual families still remain live, and whether runtime work can continue under the same rooted family without wrapper growth | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922.md` | Doc-only prep Task Package for switching the active consultant-core block from runtime demolition to acceptance-evidence preparation after main-path closure and for locking the next move to one bounded evidence bundle | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-bundle-a922.md` | Bounded implementation Task Package for classifying surfaced `r79` and repairing the shared promo interrupt contract before guarded canary re-entry | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-demo-salon-main-canary-preflight-proof-gap-a922.md` | Proof-gap audit Task Package for freezing the refreshed `r9 -> r12` preflight evidence chain, closing the stale turn-10 scenario blocker, and forcing truthful classification of the remaining advisory turns before new runtime code | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-decision-a922.md` | Decision Task Package for locking turn 9 exact-time progression as the next bounded runtime family, constraining the admissible implementation lane, and keeping turn 12 as deferred oracle debt until rerun | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-implementation-a922.md` | Implementation Task Package for landing the bounded turn 9 exact-time progression fix in non-frozen runtime, preserving deterministic reschedule contracts, and handing off the next move to guarded replay | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md` | Evidence Task Package for one fresh comparable post-fix canary replay that truthfully closes the turn-9 freshness dispute and surfaces the surviving downstream blocker | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-oracle-conflict-proof-decision-a922.md` | Decision Task Package for classifying truthful `r19` semantic-invalid residue into one bounded oracle family rooted in `ops/diagnose.py` before any new runtime or scenario change | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-proof-implementation-a922.md` | Implementation Task Package for aligning `ops/diagnose.py` judge suppression and HQ1 blocking with contract-first `r19` truth before the next replay | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-canary-replay-a922.md` | Closure Task Package for one fresh guarded replay on the locked demo-salon canary after the bounded `r19` oracle-parity fix | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-reentry-bundle-a922.md` | Implementation Task Package for the fresh post-`r20` acceptance re-entry bundle, attempting canonical acceptance lock and truthfully localizing the next blocker if the chain stops before closure | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-decision-a922.md` | Decision Task Package for locking fresh turn 13 name progression as the next bounded runtime family after fresh replay closes turn 9 and turn 12 | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md` | Implementation Task Package for bounded non-frozen turn 13 explicit-name progression repair before guarded replay | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-canary-replay-a922.md` | Replay Task Package for truthful post-fix canary rerun after the bounded turn 13 name progression repair | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-decision-a922.md` | Decision Task Package for locking fresh turn 11 check-booking reference continuity as the next bounded runtime family after truthful replay `r16` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md` | Implementation Task Package for bounded non-frozen turn 11 check-booking reference continuity repair before guarded replay | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-canary-replay-a922.md` | Closure Task Package for truthful guarded replay `r17`, proving the turn-11 repair and classifying the next surviving canary family | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn8-booking-interrupt-exact-time-progression-runtime-implementation-a922.md` | Implementation Task Package for the bounded turn-8 booking-interrupt exact-time progression repair before fresh guarded replay | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md` | Implementation Task Package for materializing the post-`r20` go-to-full evidence pack and retrying one guarded acceptance lock | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-decision-a922.md` | Decision Task Package for classifying the fresh seed-`19` generated multi-seed booking/check-booking info divergence surfaced during acceptance evidence assembly | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-implementation-a922.md` | Implementation Task Package for the bounded seed-`19` booking/check-booking interruption runtime family, deferring direct side owners and restoring explicit hours/promo continuity before replay | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md` | Closure Task Package for the first truthful exact replay on the original seed-`19` blocker scenarios after the bounded runtime repair | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md` | Decision Task Package for classifying exact replay `r4` as a bounded confirm-hook proof/tool-evidence parity family before any new runtime move | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md` | Implementation Task Package for the bounded `r4` confirm-hook proof parity repair in `ops/diagnose.py` before fresh exact replay | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md` | Closure Task Package for the first fresh exact replay after the bounded `r4` confirm-hook proof repair, restoring infra truth before runtime reclassification | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-decision-a922.md` | Decision Task Package for classifying fresh replay `r5` as a bounded post-verification exact-time reschedule runtime continuity family | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md` | Implementation Task Package for the bounded seed-`19` post-verification exact-time reschedule runtime repair before fresh exact replay | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r6-allowlist-safe-preflight-fallback-proof-implementation-a922.md` | Implementation Task Package for the bounded `r6` replay fallback proof repair so contaminated preflight stays on allowlist-safe JIDs while outbox is enabled | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-decision-a922.md` | Decision Task Package for classifying the fresh `r7` preflight stop as a bounded runtime simulation-transport family on the executable explicit-handoff owner | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-implementation-a922.md` | Implementation Task Package for the bounded seed-`19` session-reset simulation transport repair on the executable explicit-handoff owner before fresh exact replay | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-canary-replay-a922.md` | Closure Task Package for the first fresh exact replay after the bounded session-reset simulation transport repair, including stale-artifact hygiene before truthful classification | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-decision-a922.md` | Decision Task Package for classifying fresh replay `r11` as a bounded runtime family where pending-ack preflight clear is intercepted by the live greeting owner | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-implementation-a922.md` | Implementation Task Package for the bounded seed-`19` pending-ack greeting-intercept runtime repair on the executable later greeting owner before fresh exact replay | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-canary-replay-a922.md` | Closure Task Package for the first fresh exact replay after the bounded pending-ack greeting-owner repair, proving whether preflight clear now reaches turn execution | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-runtime-decision-a922.md` | Decision Task Package for classifying fresh replay `r12` as a bounded runtime family where pending-ack preflight clear is intercepted by the live explicit-handoff owner | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-runtime-implementation-a922.md` | Implementation Task Package for the bounded seed-`19` pending-ack explicit-handoff runtime repair on the executable later handoff owner before fresh exact replay | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-canary-replay-a922.md` | Closure Task Package for the first fresh exact replay after the bounded pending-ack explicit-handoff defer repair, including strict exclusion of invalid `r13` before truthful classification | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-decision-a922.md` | Decision Task Package for classifying fresh replay `r14` as a bounded runtime family where pending-ack preflight clear falls through to the terminal unresolved response path | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-implementation-a922.md` | Implementation Task Package for the bounded seed-`19` pending-ack terminal-unresolved runtime repair that reuses the existing pending continuity contract before fresh exact replay | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-runtime-decision-a922.md` | Decision Task Package for classifying fresh replay `r25` as a bounded runtime family where post-cancel rebooking keeps stale `pending` continuity after a valid collect reply | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-runtime-implementation-a922.md` | Implementation Task Package for the bounded seed-`19` post-cancel rebooking continuity repair that restores `bot_active` before fresh exact replay | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-canary-replay-a922.md` | Closure Task Package for truthful fresh replay after the bounded post-cancel rebooking continuity repair, including exclusion of stale non-canonical `r26` / `r27` / `r28` artifacts | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r29-initial-booking-handoff-regression-runtime-decision-a922.md` | Decision Task Package for classifying fresh replay `r29` as a bounded runtime regression where the initial booking request escalates through explicit handoff instead of `booking_prompt` collect | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r29-initial-booking-handoff-regression-runtime-implementation-a922.md` | Implementation Task Package for the bounded seed-`19` initial-booking timeout repair that restores `booking_prompt` collect on the executable later owner path before fresh replay | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r39-dialog-preflight-fallback-cycle-proof-decision-a922.md` | Decision Task Package for classifying non-canonical replay `r39` as a replay-isolation proof family where fallback-JID rotation revisits contaminated candidates | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r39-dialog-preflight-fallback-cycle-proof-implementation-a922.md` | Implementation Task Package for the bounded proof-tooling repair that persists contaminated fallback JIDs and unblocks replay isolation before the next truthful blocker | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-turn-outcome-targeted-frozen-waiver-implementation-a922.md` | Exact-scope targeted frozen-waiver implementation Task Package for deleting the direct frozen tool-reply `TurnOutcome` authority in `decision.py` via `TurnPlanner` + `TurnExecutor` without widening the ingress slice | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-guard-send-trace-orchestration-family-package-a922.md` | Package-level blocker Task Package for deleting or truthfully localizing the surviving frozen tool-reply guard/send/trace/meta orchestration authority on the same ingress contour after typed turn-outcome cutover | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-policy-payload-interaction-owner-family-package-a922.md` | Package-level blocker Task Package for deleting or truthfully localizing the surviving frozen tool-reply policy-payload / interaction-owner semantic authority on the same ingress contour after guard/send/trace cutover | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-artifact-sidecar-payload-family-package-a922.md` | Package-level blocker Task Package for deleting or truthfully localizing the surviving frozen tool-reply artifact / sidecar payload authority on the same ingress contour after the policy-payload cutover | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-tool-reply-guard-finalize-invocation-family-package-a922.md` | Package-level blocker Task Package for deleting or truthfully localizing the surviving frozen tool-reply finalizer / guard invocation authority on the same ingress contour after the artifact-sidecar cutover | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-master-residual-ledger-stop-line-audit-a922.md` | Stop-the-line audit Task Package for publishing one ordered master residual ledger and package backlog after the boundary micro-cut phase | Brain/Architect |
| `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md` | Session log for the consultant-core governance lock / runtime cutover worktree (`a922`) | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-console-selection-gate-observability-a1.md` | Task Package for bounded selection-gate/session-expiry telemetry and controlled verification after the hotfix moved to monitoring | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-23-console-selection-gate-stabilization-a1.md` | Task Package for stabilizing multi-company selection gate after auth/session drift without regressing explicit logout cleanup | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-knowledge-release-model-stoploss-a30.md` | P0 stop-loss Task Package for separating consultant-verification preview readiness from live activation status and pinning session truth snapshots | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-knowledge-release-model-correction-p1-a30.md` | Follow-up P1 Task Package for `active_version_id` and dedicated activation-job release model correction | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-knowledge-activation-observability-p2-a30.md` | Follow-up P2 Task Package for activation-stage/heartbeat observability and owner/admin active-vs-candidate disclosure | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-knowledge-activation-transport-p3-a30.md` | Follow-up P3 Task Package for dedicated activation worker/service transport over direct `knowledge_activation_jobs` claims | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-15-knowledge-activation-admin-observability-p4-a30.md` | Follow-up P4 Task Package for platform-admin/operator activation health, retry, and alert surfaces on top of the dedicated activation transport | Brain/Architect |
| `docs/SESSIONS/SESSION-2026-03-14-owner-consultant-verification-wave2-a920.md` | Session log for Wave2 safe simulation kernel implementation | Brain/Architect |
| `docs/SESSIONS/SESSION-2026-03-14-owner-consultant-verification-wave3-a920.md` | Session log for Wave3 owner-readable chat workspace implementation | Brain/Architect |
| `docs/SESSIONS/SESSION-2026-03-14-owner-consultant-verification-wave4-a920.md` | Session log for Wave4 scenario library, replay, and session summary implementation | Brain/Architect |
| `docs/SESSIONS/SESSION-2026-03-14-owner-consultant-verification-wave5-a920.md` | Session log for Wave5 findings/remediation loop implementation | Brain/Architect |
| `docs/SESSIONS/SESSION-2026-03-14-owner-consultant-verification-wave6-a920.md` | Session log for Wave6 live-vs-draft compare and publish readiness implementation | Brain/Architect |
| `docs/SESSIONS/SESSION-2026-03-14-owner-consultant-verification-knowledge-safety-program-a921.md` | Session log for the Knowledge safety remediation program behind owner consultant verification | Brain/Architect |
| `docs/SESSIONS/SESSION-2026-03-15-consultant-verification-branch-publish-flow-a3.md` | Session log for inline branch repair and truthful publish/sync semantics on owner surfaces | Brain/Architect |
| `docs/SESSIONS/SESSION-2026-03-15-owner-knowledge-stabilization-reset-a4.md` | Session log for the async knowledge sync + owner-surface stabilization reset block | Brain/Architect |
| `docs/SESSIONS/SESSION-2026-03-15-console-knowledge-sync-state-unification-a4.md` | Session log for the sync-state truth unification block after async knowledge mutations | Brain/Architect |
| `docs/SESSIONS/SESSION-2026-03-15-console-owner-scope-gate-unification-a5.md` | Session log for the shared owner scope-gate extraction block | Brain/Architect |
| `docs/SESSIONS/SESSION-2026-03-23-console-selection-gate-observability-a1.md` | Session log for the bounded monitoring/verification block on selection-gate and auth-session drift telemetry | Brain/Architect |
| `docs/SESSIONS/SESSION-2026-03-23-console-selection-gate-stabilization-a1.md` | Session log for the selection-gate stabilization block after auth-refresh scope drift resurfaced on `console.truffles.kz` | Brain/Architect |
| `docs/SESSIONS/SESSION-2026-03-15-knowledge-release-model-stoploss-a30.md` | Session log for the knowledge release-model stop-loss program through P3 dedicated activation transport | Brain/Architect |
| `truffles-api/migrations/060_add_knowledge_release_activation_jobs.sql` | Migration adding `branches.active_knowledge_version_id` and `knowledge_activation_jobs` for the corrected knowledge release model | Backend |
| `truffles-api/migrations/061_add_knowledge_activation_job_stage_fields.sql` | Migration adding `knowledge_activation_jobs.current_stage` for activation progress disclosure (`queued -> syncing_branch_docs -> applying_client_config -> switching_active_pointer -> finalizing`) | Backend |
| `console-web/src/lib/console-scope-gate.ts` | Shared scope-apply helper that writes Console context storage and keeps dependent queries coherent after branch changes | Frontend |
| `console-web/src/lib/console-client-events.ts` | Shared bounded telemetry helper for selection-gate/session-expiry console-web events with `keepalive` + `sendBeacon` fallback | Frontend |
| `console-web/src/lib/calendar-action-registry.ts` | Canonical Calendar action registry and role/status/action scenario matrix used by booking cards, action panel, and deterministic operator proof | Frontend |
| `truffles-api/app/services/calendar_action_contract.py` | Server-owned Calendar booking action contract builder for `allowed_actions` / `blocked_actions` and machine-readable blocked reasons | Backend |
| `truffles-api/app/logging_config.py` | Shared Prometheus counters/helpers, now including Calendar action-family observability for denied/version-conflict/double-submit/filter/follow-up events | Backend |
| `POST /calendar/operator-events` (`truffles-api/app/routers/calendar.py`) | Bounded Calendar operator-event endpoint for filter apply/reset and double-submit replay telemetry tied to audit evidence and failure-family counters | Backend |
| `console-web/src/app/calendar/_lib/useCalendarFiltersMachine.ts` | Local Calendar filters machine for explicit `draft -> applied` queue state transitions and dirty-state resets | Frontend |
| `console-web/src/app/calendar/_lib/useBookingComposerMachine.ts` | Local Calendar booking-composer machine with dependent resets, baseline restore, and dirty-close guardrails | Frontend |
| `console-web/src/app/calendar/_lib/useBookingActionPanelMachine.ts` | Local Calendar booking-action-panel machine for open/close state, cancel draft, and pending lifecycle targets | Frontend |
| `console-web/src/app/calendar/_lib/useBookingFollowUpMachine.ts` | Local Calendar follow-up machine for no-show/governance drafts and pending mutation targets | Frontend |
| `docs/runbooks/EXECUTION_CYCLE.md` | Единый рабочий цикл: что делать после каждого run/session/phase | Все роли |
| `docs/runbooks/ZERO_CONTEXT_BLOCK_DELIVERY.md` | Контракт автономной разработки блоков для агентов с нулевым контекстом | Все роли |
| `ops/console_tenants_perf_long_run.py` | Reproducible authenticated long-run perf lane for Tenants (`portfolio/cockpit/branches` + snapshot gate) | QA/OPS/Brain |
| `scripts/check_console_audit_governance.py` | Deterministic fail-closed checker for `CANON_VS_IMPLEMENTED` + `UX_BACKLOG` consistency (duplicate IDs/gap tags) | QA/OPS/Brain |
| `truffles-api/app/services/console_router_utils.py` | Shared pure helpers for Console router env/query normalization (`parse_env_*`, query rebuild, list dedupe) | Backend |
| `truffles-api/app/services/console_control_tower_utils.py` | Shared pure helper layer for Control Tower action/migration contracts (priority/reasons/wave/detail builders) | Backend |
| `truffles-api/app/services/console_control_tower_program.py` | Shared orchestration/program composition layer for Control Tower action-center and migration-program responses | Backend |
| `truffles-api/app/services/console_branch_changes.py` | Shared branch-change snapshot/diff/record/update-request helper layer extracted from Console router | Backend |
| `truffles-api/app/services/console_fleet_state.py` | Shared fleet lifecycle/payment/service state resolver layer extracted from Console router | Backend |
| `truffles-api/app/services/console_membership_state.py` | Shared membership/role assignment lifecycle guard layer extracted from Console router | Backend |
| `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md` | Weekly control-loop runbook для Platform Admin (snapshot -> backlog -> checks) | Brain/Architect |
| `docs/runbooks/OWNER_ADMIN_POSTMERGE_24H.md` | Post-merge control-loop runbook для Owner/Admin (`T+0/T+24`) | Brain/Architect |
| `truffles-api/tests/test_check_console_audit_governance.py` | Deterministic tests for console audit governance checker | QA/Backend |
| `truffles-api/tests/test_console_router_utils.py` | Deterministic tests for extracted Console router helper module | QA/Backend |
| `truffles-api/tests/test_console_control_tower_utils.py` | Deterministic tests for extracted Control Tower helper module | QA/Backend |
| `truffles-api/tests/test_console_control_tower_program.py` | Deterministic tests for extracted Control Tower orchestration/program module | QA/Backend |
| `truffles-api/tests/test_console_fleet_state.py` | Deterministic tests for extracted fleet state resolver module | QA/Backend |
| `truffles-api/tests/test_console_membership_state.py` | Deterministic tests for extracted membership/role state guard module | QA/Backend |
| `console-web/src/components/provisioning-wizard-utils.ts` | Extracted pure helper functions for `ProvisioningWizard` (JSON parse, status labels/classes, capability normalization) | Frontend |
| `console-web/src/components/provisioning-wizard-domain.ts` | Extracted provisioning domain lexicon (`WIZARD_STEPS`, field guides, formatters, fallback presets) for `ProvisioningWizard` | Frontend |
| `console-web/src/components/provisioning-wizard-derived.ts` | Extracted derived-state builders for `ProvisioningWizard` (step status/timeline/readiness items) | Frontend |
| `console-web/src/components/provisioning-wizard-shell-panels.tsx` | Extracted controlled shell panels for `ProvisioningWizard` (error summary, mode switch, execution hub) | Frontend |
| `console-web/src/components/provisioning-wizard-json-payloads.ts` | Extracted JSON payload builders/loaders for `ProvisioningWizard` (`billing_info`, `working_hours`, `booking_settings`) | Frontend |
| `console-web/src/components/provisioning-wizard-state.ts` | Extracted state lifecycle/bootstrap/hydration helpers for `ProvisioningWizard` | Frontend |
| `console-web/src/components/provisioning-wizard-branch-actions.ts` | Extracted branch action payload builders for `ProvisioningWizard` (`create/update/save instance/telegram/knowledge/booking`) | Frontend |
| `console-web/src/components/provisioning-wizard-account-actions.ts` | Extracted account action payload builders for `ProvisioningWizard` (`create company/client/agent`) | Frontend |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-operations-governance-closeout-a705.md` | Artifact report: UVC audit governance closeout (`UVC-UX-OPERATIONS-GOVERNANCE-CLOSEOUT-A705`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-03-uvc-tech-debt-decomposition-wave1-a705.md` | Artifact report: wave1 structural decomposition for `UX-11`/`UX-12` + merge-red fix | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave2-a705.md` | Artifact report: wave2 structural decomposition for `UX-11`/`UX-12` (control-tower + provisioning domain extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave3-a705.md` | Artifact report: wave3 structural decomposition for `UX-11`/`UX-12` (control-tower orchestration + provisioning derived-state extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-08-inbox-calendar-ux-logic-audit-a1.md` | Artifact report: deep UX/logic audit for Inbox/Calendar after Waves24-30, with surface decomposition and operator-proof plan (`UX-34`/`UX-35`/`UX-36`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closeout-a705.md` | Artifact report: closeout decision for `UX-11`/`UX-12` after merged wave1/2/3 (`Open (Mitigated wave3)` + Wave4 contract) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave4-a705.md` | Artifact report: wave4 structural decomposition for `UX-11`/`UX-12` (onboarding readiness backend slice + provisioning readiness panel extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-final-close-a705.md` | Artifact report: final-close decision after wave4 merge (`Open (Mitigated wave4; residual accepted, wave5 required)`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave5-a705.md` | Artifact report: wave5 structural decomposition for `UX-11`/`UX-12` (router param-validation extraction + wizard shell panel extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review-a705.md` | Artifact report: closure-review decision after wave5 merge (`Open (Mitigated wave5; wave6 required)`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave6-a705.md` | Artifact report: wave6 structural decomposition for `UX-11`/`UX-12` (fleet-state backend extraction + provisioning JSON payload extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review2-a705.md` | Artifact report: closure-review2 decision after wave6 merge (`Open (Mitigated wave6; wave7 required)`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave7-a705.md` | Artifact report: wave7 structural decomposition for `UX-11`/`UX-12` (membership-state backend extraction + wizard state lifecycle extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-final-review3-a705.md` | Artifact report: final-review3 merged-main decision after wave7 (`Open (Mitigated wave7; wave8 required)`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave8-a705.md` | Artifact report: wave8 structural decomposition for `UX-11`/`UX-12` (go-live backend governance extraction + wizard JSON sync extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review4-a705.md` | Artifact report: closure-review4 merged-main decision after wave8 (`Open (Mitigated wave8; wave9 required)`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave9-a705.md` | Artifact report: wave9 structural decomposition for `UX-11`/`UX-12` (branch-change backend extraction + provisioning branch-action extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review5-a705.md` | Artifact report: closure-review5 merged-main decision after wave9 (`Open (Mitigated wave9; wave10 required)`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave10-a705.md` | Artifact report: wave10 structural decomposition for `UX-11`/`UX-12` (branch-change normalization extraction + provisioning account-action extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review6-a705.md` | Artifact report: closure-review6 merged-main decision after wave10 (`Open (Mitigated wave10; wave11 required)`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave11-a705.md` | Artifact report: wave11 structural decomposition for `UX-11`/`UX-12` (branch-change context/rollback extraction + provisioning autopilot extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review7-a705.md` | Artifact report: closure-review7 merged-main decision after wave11 (`Open (Mitigated wave11; wave12 required)`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave12-a705.md` | Artifact report: wave12 structural decomposition for `UX-11`/`UX-12` (branch-change prepare/validation extraction + provisioning autopilot run-state extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-closure-review8-a705.md` | Artifact report: closure-review8 merged-main decision after wave12 (`Open (Mitigated wave12; wave13 required)`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave13-a705.md` | Artifact report: wave13 structural decomposition for `UX-11`/`UX-12` (branch-change list response extraction + provisioning autopilot success-sync extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-closure-review9-a705.md` | Artifact report: closure-review9 merged-main decision after wave13 (`Open (Mitigated wave13; wave14 required)`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-wave14-a705.md` | Artifact report: wave14 structural decomposition for `UX-11`/`UX-12` (branch-change validate/publish-failed state extraction + provisioning branch-mutation orchestration extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-closure-review10-a705.md` | Artifact report: closure-review10 merged-main decision after wave14 (`Open (Mitigated wave14; wave15 required)`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-wave15-a705.md` | Artifact report: wave15 structural decomposition for `UX-11`/`UX-12` (branch-change publish/rollback runtime-state extraction + provisioning go-live payload validation extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-closure-review11-a705.md` | Artifact report: closure-review11 merged-main decision after wave15 (`Open (Mitigated wave15; wave16 required)`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-wave16-a705.md` | Artifact report: wave16 structural decomposition for `UX-11`/`UX-12` (branch-change publish-success state extraction + provisioning go-live mutation submit-flow extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-closure-review12-a705.md` | Artifact report: closure-review12 merged-main decision after wave16 (`Open (Mitigated wave16; wave17 required)`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-wave17-a705.md` | Artifact report: wave17 structural decomposition for `UX-11`/`UX-12` (branch-change rollback normalization extraction + provisioning go-live submit-orchestration extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-closure-review13-a705.md` | Artifact report: closure-review13 merged-main decision after wave17 (`Open (Mitigated wave17; wave18 required)`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-wave18-a705.md` | Artifact report: wave18 structural decomposition for `UX-11`/`UX-12` (branch-change response assembly extraction + provisioning branch-mutation submit-flow extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-closure-review14-a705.md` | Artifact report: closure-review14 merged-main decision after wave18 (`Open (Mitigated wave18; wave19 required)`) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-wave19-a705.md` | Artifact report: wave19 structural decomposition for `UX-11`/`UX-12` (branch-change context resolver extraction + wizard reset-state extraction) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-closure-review15-a705.md` | Artifact report: closure-review15 binary DoD decision after wave19 (`Open (Mitigated wave19; wave20 required)` with failed-criteria map) | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-wave20-a705.md` | Artifact report: wave20 bounded backend extraction (control-tower drift/readiness board orchestration) closing criterion `C1` (`console.py` threshold) and locking closure-review16 | Brain/Architect |
| `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-closure-review16-a705.md` | Artifact report: closure-review16 merged-main binary DoD decision after wave20 (`UX-11/UX-12 = Fixed`, wave21 not opened) | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave4-a705.md` | Follow-up Task Package for next decomposition wave after closeout residual confirmation | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-final-close-a705.md` | Final-close Task Package for post-wave4 deterministic status decision and residual contract | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave5-a705.md` | Next bounded wave Task Package for residual `UX-11/UX-12` decomposition after final-close merge | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review-a705.md` | Closure-review Task Package for post-wave5 merged-main decision and wave6 contract lock | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave6-a705.md` | Next bounded decomposition Task Package after closure-review for residual `UX-11/UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review2-a705.md` | Follow-up closure-review Task Package after wave6 merge to decide `Fixed` vs `Open` for `UX-11/UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave7-a705.md` | Next bounded decomposition Task Package after closure-review2 for residual `UX-11/UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-final-review3-a705.md` | Final review Task Package after wave7 to decide `Fixed` vs `Open + wave8` for `UX-11/UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave8-a705.md` | Next bounded decomposition Task Package after final-review3 residual decision for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review4-a705.md` | Closure-review Task Package after wave8 merge to decide `Fixed` vs `Open + wave9` for `UX-11/UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave9-a705.md` | Next bounded decomposition Task Package after closure-review4 residual decision for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review5-a705.md` | Closure-review Task Package after wave9 merge to decide `Fixed` vs `Open + wave10` for `UX-11/UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave10-a705.md` | Next bounded decomposition Task Package after closure-review5 residual decision for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review6-a705.md` | Closure-review Task Package after wave10 merge to decide `Fixed` vs `Open + wave11` for `UX-11/UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave11-a705.md` | Next bounded decomposition Task Package after closure-review6 residual decision for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review7-a705.md` | Closure-review Task Package after wave11 merge to decide `Fixed` vs `Open + wave12` for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave12-a705.md` | Next bounded decomposition Task Package after closure-review7 residual decision for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review8-a705.md` | Closure-review Task Package after wave12 merge to decide `Fixed` vs `Open + wave13` for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave13-a705.md` | Next bounded decomposition Task Package after closure-review8 residual decision for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review9-a705.md` | Closure-review Task Package after wave13 merge to decide `Fixed` vs `Open + wave14` for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-wave14-a705.md` | Next bounded decomposition Task Package after closure-review9 residual decision for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review10-a705.md` | Closure-review Task Package after wave14 merge to decide `Fixed` vs `Open + wave15` for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-wave15-a705.md` | Next bounded decomposition Task Package after closure-review10 residual decision for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review11-a705.md` | Closure-review Task Package after wave15 merge to decide `Fixed` vs `Open + wave16` for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-wave16-a705.md` | Next bounded decomposition Task Package after closure-review11 residual decision for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review12-a705.md` | Closure-review Task Package after wave16 merge to decide `Fixed` vs `Open + wave17` for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-wave17-a705.md` | Next bounded decomposition Task Package after closure-review12 residual decision for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review13-a705.md` | Closure-review Task Package after wave17 merge to decide `Fixed` vs `Open + wave18` for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-wave18-a705.md` | Next bounded decomposition Task Package after closure-review13 residual decision for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review14-a705.md` | Closure-review Task Package after wave18 merge to decide `Fixed` vs `Open + wave19` for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-wave19-a705.md` | Next bounded decomposition Task Package after closure-review14 residual decision for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review15-a705.md` | Closure-review Task Package after wave19 merge to decide `Fixed` vs `Open + wave20` for `UX-11`/`UX-12` | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-wave20-a705.md` | Next bounded decomposition Task Package after closure-review15 failed criterion `C1` (`console.py` threshold) | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review16-a705.md` | Closure-review Task Package after wave20 merge to decide `Fixed` vs `Open + wave21` for `UX-11`/`UX-12` | Brain/Architect |
| `SPECS/CONTROL_PLANE.md` | Канон: Console как Control Plane (роли, IA, онбординг, capabilities) | Архитектор/Frontend |
| `SPECS/INBOX_HUMAN_LOCK.md` | ТЗ: manual messaging + human lock в «Заявках» | Архитектор/Backend/Frontend |
| `docs/CONSULTANT_CODEMAP.md` | Код‑карта консультанта (decision pipeline, блоки, влияние на поведение) | Backend/Architect |
| `docs/REPORTS/` | Отчёты по прогонам/изменениям | Brain/Architect |
| `docs/REPORTS/2026-03-30-consultant-core-consolidation-freeze-inventory-a922.md` | Report: three-checkout freeze manifests + inventory + consolidation base selection | Brain/Architect |
| `docs/REPORTS/2026-03-30-consultant-core-consolidation-doc-conflict-resolution-a922.md` | Report: low-risk doc conflict source picks for consolidation worktree | Brain/Architect |
| `docs/REPORTS/2026-03-30-consultant-core-consolidation-code-conflict-shortlist-a922.md` | Report: P0/P1/P2 shortlist for remaining consultant-core code/test conflicts | Brain/Architect |
| `docs/REPORTS/2026-03-30-consultant-core-consolidation-code-source-resolution-a922.md` | Report: authoritative source picks for remaining code/test conflict set in consolidation worktree | Brain/Architect |
| `docs/REPORTS/2026-01-24-consult-quality.md` | Отчёт: consult quality + chaos‑sim | Brain/Architect |
| `docs/REPORTS/2026-02-20-tenants-a11y-evidence-a201.md` | Отчёт: live e2e+axe evidence для Tenants (platform_admin) | Brain/Architect |
| `docs/REPORTS/2026-02-20-tenants-v3-redesign-plan.md` | Отчёт: Tenants V3 redesign baseline + Wave3 backfill verification + Wave4/5 progress | Brain/Architect |
| `docs/REPORTS/2026-01-25-control-plane-provisioning.png` | Скрин: Provisioning Wizard (Settings) | Brain/Architect |
| `docs/REPORTS/2026-01-26-control-plane-inbox.png` | Скрин: Inbox 3‑pane (Phase 5) | Brain/Architect |
| `docs/REPORTS/2026-01-27-control-plane-review.md` | Отчёт: Control Plane UX/RBAC/safety review | Brain/Architect |
| `docs/REPORTS/2026-01-30-inbox-ux-standard.md` | Отчёт: Inbox UX standard (analysis + variants) | Brain/Architect |
| `docs/REPORTS/2026-01-30-inbox-ux-v2.md` | Отчёт: Inbox UX v2 + макросы | Brain/Architect |
| `docs/REPORTS/2026-01-31-console-media-infra-telegram.md` | Report: Console media infra + Telegram touchpoints | Brain/Architect |
| `docs/REPORTS/2026-02-01-pack-compiler-implementation.md` | Report: Pack compiler implementation evidence + chaos-sim summary | Brain/Architect |
| `docs/REPORTS/2026-02-08-enterprise-fleet-program.md` | Report: Enterprise fleet operating model + 5-PR execution plan | Brain/Architect |
| `docs/REPORTS/2026-02-15-platform-admin-baseline-v2.md` | Report: Platform Admin runtime/code baseline + control-loop wave results | Brain/Architect |
| `docs/REPORTS/2026-02-15-platform-admin-baseline-v3.md` | Report: Platform Admin wave 1+2 follow-up (outbox guard + inline validation recovery) | Brain/Architect |
| `docs/REPORTS/2026-02-15-owner-admin-wave5-control-hardening-v1.md` | Report: Owner/Admin wave-5 (control hardening + rollback + decomposition start) | Brain/Architect |
| `docs/REPORTS/2026-02-15-owner-admin-wave6-automation-v1.md` | Report: Owner/Admin wave-6 (automation wrapper + goal-mode + publish preflight gate) | Brain/Architect |
| `docs/REPORTS/2026-02-15-owner-admin-wave7-fact-os-v1.md` | Report: Owner/Admin wave-7 (fact contract layer + server-driven owner operations) | Brain/Architect |
| `docs/REPORTS/2026-02-15-owner-admin-wave8-incident-control-v1.md` | Report: Owner/Admin + Platform Admin wave-8 (incident control loop + safe remediation actions) | Brain/Architect |
| `docs/REPORTS/2026-02-16-owner-admin-wave9-subscription-contract-v1.md` | Report: Owner/Admin wave-9 (subscription contract = plan + fact + action) | Brain/Architect |
| `docs/REPORTS/2026-02-16-owner-admin-wave10-subscription-truth-v1.md` | Report: Owner/Admin wave-10 (subscription truth mode: fail-closed contract + diagnostics) | Brain/Architect |
| `docs/REPORTS/2026-02-17-console-postmerge-acceptance-p95-wave123-v1.md` | Report: Post-merge acceptance + p95 timing audit (platform_admin/owner_admin) with nav reliability findings | Brain/Architect |
| `docs/REPORTS/2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md` | Report: session-scoped zero-context gate isolation for UCPV1 track | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md` | Report: exact remaining consultant-core owner families, hotspot clusters, package order, and no-go shortcuts after the timeout active-name time-followup cutover | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-closure-a922.md` | Report: evidence-first GAP for the final multi-pack acceptance closure bundle, proving missing runtime targets for `clinic_or_dental` and `generic_service` block truthful platform closure | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-runtime-target-materialization-a922.md` | Report: implementation evidence for truthful `clinic_pack/main` and `generic/main` runtime targets, closing the repo-dir-only non-beauty target-materialization seam before final acceptance re-entry | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-reentry-a922.md` | Report: evidence-first GAP for the multi-pack acceptance re-entry bundle, proving a stale non-canonical `demo_salon` lock blocks new guarded canary, matrix, and closure evidence | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-18-consultant-core-acceptance-preflight-blocker-a922.md` | Report: implementation GAP for the acceptance-preflight unblock bundle, proving the hardcode-core blocker seam is closed while truthful `go_to_full` still stops at the narrower L2 transport / observability family under `TEST_MODE` | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-18-consultant-core-acceptance-preflight-l2-transport-blocker-a922.md` | Report: implementation GAP for the bounded L2 transport blocker bundle, proving the old synthetic unique-JID seam is dead, billing is acceptable in the unpaid dev lane, and the remaining blocker is the completed-run expectation / judge conflict family from `r11` | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922.md` | Report: doc-only acceptance-evidence prep for post-runtime consultant-core closure, freezing the latest non-canonical canary facts and switching canon from demolition to proof/oracle-first blocker classification | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-bundle-a922.md` | Report: bounded promo-interrupt contract repair that reclassifies `r79` as a runtime core bug and records deterministic evidence before guarded canary re-entry | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-21-consultant-core-demo-salon-main-canary-preflight-proof-gap-a922.md` | Report: refreshed canary-preflight evidence proving turn-10 was stale oracle drift while turns 9/12 remain advisory proof debt to classify before runtime changes | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-decision-a922.md` | Report: bounded turn-9 runtime-family decision proving exact-time progression is the next real runtime blocker while turn 12 stays deferred oracle debt until rerun | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-implementation-a922.md` | Report: bounded turn-9 runtime implementation proving exact-time progression now grounds booking datetime in non-frozen runtime while turn 12 stays deferred until replay | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md` | Report: refreshed canary replay proving turn 9 is fixed on the fresh runtime, turn 12 no longer blocks, and turn 13 is the new surfaced family | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-decision-a922.md` | Report: bounded turn-13 runtime-family decision proving explicit name fill now becomes the next real blocker after fresh replay closes turn 9 and turn 12 | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md` | Report: bounded turn-13 runtime implementation for semantic explicit-name progression before guarded replay | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-canary-replay-a922.md` | Report: truthful post-fix canary replay showing fresh `r16` and invalid pre-run artifacts for the turn-13 lane | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-decision-a922.md` | Report: bounded turn-11 runtime-family decision proving check-booking reference continuity is now the first surviving blocker on fresh replay `r16` | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md` | Report: bounded turn-11 runtime implementation repairing repeated check-booking reference continuity before guarded replay | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-canary-replay-a922.md` | Report: truthful guarded replay `r17` proving turn-11 repair, re-entering turn 13, and surfacing the next canary family at turn 8 | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn8-booking-interrupt-exact-time-progression-runtime-implementation-a922.md` | Report: bounded turn-8 booking-interrupt exact-time progression repair landed locally with focused deterministic proof before replay | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-contract-aligned-oracle-canary-replay-a922.md` | Report: fresh guarded replay `r20` proving the bounded `r19` oracle-parity family is green on the locked demo-salon canary surface | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-reentry-bundle-a922.md` | Report: first post-`r20` acceptance re-entry attempt, proving the chain now stops at missing `go_to_full` evidence-pack materialization rather than runtime/demo-salon canary debt | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md` | Report: truthful execution of the post-`r20` go-to-full evidence-pack family, proving seed `7` is green while fresh seed `19` stops the lane on semantic divergence before checklist assembly | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-decision-a922.md` | Report: decision evidence proving the fresh seed-`19` blocker is a bounded runtime-semantic family on active booking/check-booking info interruption, not a checklist-only or pack-data gap | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-implementation-a922.md` | Report: bounded implementation evidence for the seed-`19` booking/check-booking interruption runtime family before truthful replay on generated coverage | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md` | Report: replay evidence for the first exact post-fix seed-`19` run, proving the next blocker is infra/tool-evidence `confirm_hook_missing` rather than immediate runtime reclassification | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md` | Report: decision evidence proving exact replay `r4` is blocked by confirm-hook proof parity in `ops/diagnose.py`, not by a new runtime or transport family | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md` | Report: bounded implementation evidence for the `r4` confirm-hook proof parity repair in `ops/diagnose.py` before fresh exact replay | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md` | Report: fresh exact replay evidence proving the old `confirm_hook_missing` blocker is closed and runtime reclassification is now admissible on seed `19` | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-decision-a922.md` | Report: decision evidence proving fresh replay `r5` now surfaces a bounded post-verification exact-time reschedule runtime continuity bug at dialog `1`, turn `13` | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md` | Report: bounded implementation evidence for the seed-`19` post-verification exact-time reschedule runtime repair before fresh exact replay | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r6-allowlist-safe-preflight-fallback-proof-implementation-a922.md` | Report: bounded proof-only replay fallback repair showing the old non-allowlist transport blocker is closed before fresh replay reclassification | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-decision-a922.md` | Report: bounded runtime decision proving the next blocker is simulation transport on the executable explicit-handoff owner, not more replay fallback drift | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-implementation-a922.md` | Report: bounded implementation evidence for repairing simulation-safe transport on the executable explicit-handoff owner before fresh exact replay | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-canary-replay-a922.md` | Report: fresh exact replay evidence proving the old provider-transport blocker is no longer first and recording stale-artifact hygiene for `r10` | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-decision-a922.md` | Report: bounded runtime decision proving fresh replay `r11` now fails on pending-ack interception by the live greeting owner during session-reset clear | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-implementation-a922.md` | Report: bounded implementation evidence for repairing pending-ack interception on the executable later greeting owner before fresh exact replay | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-canary-replay-a922.md` | Report: fresh exact replay evidence proving the old greeting-owner blocker is no longer first and that fresh replay `r12` surfaced a different preflight-clear family | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-runtime-decision-a922.md` | Report: bounded runtime decision proving fresh replay `r12` now fails on pending-ack interception by the live explicit-handoff owner during session-reset clear | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-runtime-implementation-a922.md` | Report: bounded implementation evidence for repairing pending-ack interception on the executable later explicit-handoff owner before fresh exact replay | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-canary-replay-a922.md` | Report: fresh exact replay evidence proving the old explicit-handoff blocker is no longer first and that fresh replay `r14` surfaced a different preflight-clear family | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-decision-a922.md` | Report: bounded runtime decision proving fresh replay `r14` now fails on pending-ack falling through to the terminal unresolved response path during session-reset clear | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-implementation-a922.md` | Report: bounded implementation evidence for repairing pending-ack terminal-unresolved fallback by reusing the existing pending continuity contract before fresh exact replay | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-runtime-decision-a922.md` | Report: bounded runtime decision proving fresh replay `r25` now fails because post-cancel rebooking keeps `pending` continuity after an otherwise valid collect reply | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-runtime-implementation-a922.md` | Report: bounded implementation evidence for restoring `bot_active` on the executable post-cancel rebooking collect owner path before fresh exact replay | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-canary-replay-a922.md` | Report: truthful fresh replay evidence after the post-cancel rebooking repair, explicitly excluding stale/non-canonical `r26` / `r27` / `r28` attempts before classifying the new blocker | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r29-initial-booking-handoff-regression-runtime-decision-a922.md` | Report: bounded runtime decision proving fresh replay `r29` now regresses on the initial booking turn via explicit handoff / terminal unresolved instead of `booking_prompt` collect | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r29-initial-booking-handoff-regression-runtime-implementation-a922.md` | Report: bounded implementation evidence for repairing initial-booking policy-timeout fallback so the executable later owner returns to `booking_prompt` collect before fresh replay | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r39-dialog-preflight-fallback-cycle-proof-decision-a922.md` | Report: bounded proof decision proving replay `r39` is blocked by fallback-JID isolation cycling rather than a new runtime turn failure | Brain/Architect |
| `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r39-dialog-preflight-fallback-cycle-proof-implementation-a922.md` | Report: bounded proof implementation evidence showing replay fallback-JID bookkeeping no longer stalls before dialog progression | Brain/Architect |
| `docs/REPORTS/REPORT_TEMPLATE_ZERO_CONTEXT.md` | Шаблон отчёта для zero-context block delivery | Brain/Architect/Hands |
| `docs/TASK_PACKAGES/` | Task Packages (scope/DoD/checks/evidence) | Brain/Architect |
| `docs/TASK_PACKAGES/TP_TEMPLATE_ZERO_CONTEXT.md` | Шаблон Task Package для zero-context block delivery | Brain/Architect/Hands |
| `docs/TASK_PACKAGES/TP-2026-01-23-chaos-consult-quality-v1.md` | Task Package: chaos-sim + consult quality (multi-intent, safe advice) | Brain/Architect |

**Активные Task Packages:**
- `docs/TASK_PACKAGES/TP-2026-03-09-p1.6o60a-remaining-closure-architecture-verdict-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-09-p1.6o60b-remaining-closure-owner-matrix-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o62-timeout-ask-about-requested-slot-booking-limit-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o63-active-name-time-availability-followup-owner-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o64-timeout-mixed-date-availability-governance-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o65-invalid-schema-specialist-followup-truth-gate-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o66-policy-core-named-specialist-followup-owner-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o67-ambiguous-time-fill-scenario-governance-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-program-closeout-steady-loop-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-e2f-firebreak-semantic-contract-closure-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-e2e-firebreak-canonical-lock-replay-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-e2d-acceptance-process-unblock-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-e2c-canonical-replay-canary-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-e2b-lexicon-resolver-hardening-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-e2a-interrupt-arbitration-owner-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-03-e1-llm-first-firebreak-action-router-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-wave7-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-final-review3-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-dedup-intent-map-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-03-uvc-ux-tech-debt-decomposition-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-s2-s3-signal-compiler-and-gate-v2-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-s0-s1-signal-manifest-and-hardcode-gate-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-s4-cross-domain-contract-suite-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-multi-seed-drift-gate-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-chain-controller-bootstrap-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-contract-test-migration-master-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-contract-test-migration-semantic-service-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-core-dehardcoding-sweep-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-process-integrity-signal-program-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-p4-expected-reply-full-closure-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-p5b-distributed-retrieval-backend-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-p9-contract-oracle-full-closure-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-p12-cross-domain-hardening-full-closure-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-p13-canary-rollback-full-closure-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-02-p14-evidence-state-handoff-full-closure-a1.md`
- `docs/TASK_PACKAGES/TP-2026-02-27-research-gates-rollout-a900.md`
- `docs/TASK_PACKAGES/TP-2026-02-24-universal-control-plane-v1-sanitize-gates-a500.md`
- `docs/TASK_PACKAGES/TP-2026-02-22-outreach-auto-case-a200.md`
- `docs/TASK_PACKAGES/TP-2026-02-16-owner-admin-wave10-subscription-truth-a88.md`
- `docs/TASK_PACKAGES/TP-2026-02-15-owner-admin-wave7-fact-os-a1.md`
- `docs/TASK_PACKAGES/TP-2026-02-05-llm-quality-runner.md`
- `docs/TASK_PACKAGES/TP-2026-02-04-llm-policy-core-dec.md`
- `docs/TASK_PACKAGES/TP-2026-02-04-llm-policy-core-impl.md`
- `docs/TASK_PACKAGES/TP-2026-02-02-vertical-pack-canon.md`
- `docs/TASK_PACKAGES/TP-2026-02-02-tp-batch-create.md`
- `docs/TASK_PACKAGES/TP-2026-02-02-vertical-pack-kit.md`
- `docs/TASK_PACKAGES/TP-2026-02-02-minimum-data-safe-mode.md`
- `docs/TASK_PACKAGES/TP-2026-02-02-learning-consent-pack-candidates.md`
- `docs/TASK_PACKAGES/TP-2026-02-03-booking-full-cycle-gcal.md`
- `docs/TASK_PACKAGES/TP-2026-02-03-calendar-oauth-callback.md`
- `docs/TASK_PACKAGES/TP-2026-02-03-outbox-calendar-sync-trace-guard.md`
- `docs/TASK_PACKAGES/TP-2026-02-03-console-merge-verify.md`
- `docs/TASK_PACKAGES/TP-2026-02-03-console-redeploy-verify.md`
- `docs/TASK_PACKAGES/TP-2026-02-03-console-settings-typefix.md`
- `docs/TASK_PACKAGES/TP-2026-02-02-console-provisioning-ux.md`
- `docs/TASK_PACKAGES/TP-2026-02-02-console-calendar-past-dates.md`
- `docs/TASK_PACKAGES/TP-2026-02-02-console-pr-cleanup.md`
- `docs/TASK_PACKAGES/TP-2026-02-03-calendar-provider-dec.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-session-governance.md`
- `docs/TASK_PACKAGES/TP-2026-01-23-console-telegram-p0.md`
- `docs/TASK_PACKAGES/TP-2026-01-23-console-telegram-verify-test.md`
- `docs/TASK_PACKAGES/TP-2026-01-23-console-telegram-ui.md`
- `docs/TASK_PACKAGES/TP-2026-01-23-console-telegram-ci-fix.md`
- `docs/TASK_PACKAGES/TP-2026-01-23-console-telegram-schemathesis-unexclude.md`
- `docs/TASK_PACKAGES/TP-2026-01-23-telegram-onboarding-link.md`
- `docs/TASK_PACKAGES/TP-2026-01-23-telegram-linking-sync.md`
- `docs/TASK_PACKAGES/TP-2026-01-23-telegram-protocol-docs.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-calendar-dec-phase0.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-calendar-data-model-phase1.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-calendar-db-rollout-phase1.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-calendar-local-provider-phase2.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-calendar-backfill-phase3.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-calendar-bot-integration-phase4.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-control-plane-canon.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-knowledge-studio-dec.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-control-plane-phase1.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-control-plane-phase2.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-control-plane-phase2-capabilities.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-control-plane-phase2-provisioning.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-control-plane-phase2-ui.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-trace-booking-commit.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-consultant-chatgpt-like.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-slot-lock-booking-confirm.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-console-telegram-sync-fixes.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-inbox-health-search.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-consult-quality-core-v1.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-ops-outbox-delivery.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-telegram-desktop-link-fix.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-console-e2e-live-ci-fix.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-control-plane-verify.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-human-dialog-tests.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-prod-gonogo-dec.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-console-web-build-fix.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-console-e2e-team.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-console-web-deploy-team.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-control-plane-phase3-knowledge-studio.md`
- `docs/TASK_PACKAGES/TP-2026-01-26-control-plane-phase3-knowledge-backend.md`
- `docs/TASK_PACKAGES/TP-2026-01-26-control-plane-phase5-inbox-ui.md`
- `docs/TASK_PACKAGES/TP-2026-01-26-control-plane-rbac-matrix.md`
- `docs/TASK_PACKAGES/TP-2026-01-26-control-plane-onboarding-state-machine.md`
- `docs/TASK_PACKAGES/TP-2026-01-26-control-plane-destructive-safeguards.md`
- `docs/TASK_PACKAGES/TP-2026-01-26-provider-gateway-architecture.md`
- `docs/TASK_PACKAGES/TP-2026-01-26-provider-contracts-v1.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-provider-gateway-inbound-shadow.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-provider-gateway-outbound-shadow.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-provider-gateway-media-pipeline.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-provider-gateway-inbox-event.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-provider-gateway-service.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-inbox-service-shadow.md`
- `docs/TASK_PACKAGES/TP-2026-01-28-decision-core-shadow.md`
- `docs/TASK_PACKAGES/TP-2026-01-28-outbox-service-shadow.md`
- `docs/TASK_PACKAGES/TP-2026-01-28-provider-gateway-integration-tests.md`
- `docs/TASK_PACKAGES/TP-2026-01-28-qdrant-branch-backfill-ca13.md`
- `docs/TASK_PACKAGES/TP-2026-01-28-decision-meta-branch-id.md`
- `docs/TASK_PACKAGES/TP-2026-01-29-ci-ruff-ca06.md`
- `docs/TASK_PACKAGES/TP-2026-01-29-dialog-report-tool.md`
- `docs/TASK_PACKAGES/TP-2026-01-29-p0-behavior-fixes.md`
- `docs/TASK_PACKAGES/TP-2026-01-30-chaos-oracle.md`
- `docs/TASK_PACKAGES/TP-2026-01-30-console-build-info-wiring.md`
- `docs/TASK_PACKAGES/TP-2026-01-30-console-web-deploy-inbox-ux-v3.md`
- `docs/TASK_PACKAGES/TP-2026-01-30-inbox-ux-v2-macros.md`
- `docs/TASK_PACKAGES/TP-2026-01-30-inbox-ux-v3.md`
- `docs/TASK_PACKAGES/TP-2026-01-30-inbox-macros-fix.md`
- `docs/TASK_PACKAGES/TP-2026-01-30-inbox-queue-adaptive.md`
- `docs/TASK_PACKAGES/TP-2026-01-30-inbox-queue-adaptive-ci-fix.md`
- `docs/TASK_PACKAGES/TP-2026-01-30-inbox-ux-v3-fix.md`
- `docs/TASK_PACKAGES/TP-2026-01-30-console-sidebar-toggle-deploy.md`
- `docs/TASK_PACKAGES/TP-2026-01-30-console-sidebar-toggle.md`
- `docs/TASK_PACKAGES/TP-2026-01-30-unified-reasoning-core-dec.md`
- `docs/TASK_PACKAGES/TP-2026-01-31-llm-pack-ref-only.md`
- `docs/TASK_PACKAGES/TP-2026-01-31-ruff-intent-import-order.md`
- `docs/TASK_PACKAGES/TP-2026-01-31-llm-wording-clarify.md`
- `docs/TASK_PACKAGES/TP-2026-01-31-signal-snapshot-evidence.md`
- `docs/TASK_PACKAGES/TP-2026-01-31-chaos-golden-coverage.md`
- `docs/TASK_PACKAGES/TP-2026-01-31-golden-eval-chaos-sim.md`
- `docs/TASK_PACKAGES/TP-2026-02-01-scn-multiturn-eval.md`
- `docs/TASK_PACKAGES/TP-2026-02-01-pack-lexicons-pack-only.md`
- `docs/TASK_PACKAGES/TP-2026-02-01-pack-compiler-dsl.md`
- `docs/TASK_PACKAGES/TP-2026-02-01-pack-compiler-docs.md`
- `docs/TASK_PACKAGES/TP-2026-02-01-pack-compiler-implementation.md`
- `docs/TASK_PACKAGES/TP-2026-02-04-metrics-daily-auto.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-knowledge-snapshot-gateway-shadow.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-knowledge-snapshot-consumer-shadow.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-knowledge-snapshot-consult-cutover.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-knowledge-gateway-service.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-control-plane-docs-selection-runbooks.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-control-plane-phase4-ui.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-console-contract-knowledge-unexclude.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-console-build-info.md`
- `docs/TASK_PACKAGES/TP-2026-01-26-consult-agnostic-implementation.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-chaos-live-e2e.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-sim-time-override.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-thanks-typo-smalltalk.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-chaos-sim-resilience.md`
- `docs/TASK_PACKAGES/TP-2026-01-25-prod-deploy-guard.md`
- `docs/TASK_PACKAGES/TP-2026-01-26-consult-agnostic-dod.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-control-plane-company-selection.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-console-ux-selection.md`
- `docs/TASK_PACKAGES/TP-2026-01-27-console-contract-stabilization.md`
- `docs/TASK_PACKAGES/TP-2026-01-29-livecheck-ca03-ca06.md`
- `docs/TASK_PACKAGES/TP-2026-01-29-livecheck-ca03-ca06.md`
- `docs/TASK_PACKAGES/TP-2026-02-02-hybrid-llm-plan-dec.md`
- `docs/TASK_PACKAGES/TP-2026-02-02-hybrid-llm-plan-implementation.md`

---

## OWNERS (кто обновляет)

| Артефакт | Ответственный |
|----------|----------------|
| `STATE.md` | Brain или Top Architect (до merge для core/поведенческих изменений + финальный шаг сессии) |
| `SPECS/*` (кроме `SPECS/ACTIVE_LEARNING_PLAN.md`) | Top Architect |
| `docs/TECH_STATUS.md` | QA/OPS (после прогонов) |
| `docs/SELLING_TRUTHS.md` | Top Architect / Brain |
| `STRUCTURE.md` | Brain |

---

## КАНОН-КАРТА (что считать истиной)

- Процесс/роли: `AGENTS.md`, `docs/SESSION_START_PROMPT.txt`.
- Статус/evidence: `STATE.md` (единственный источник фактов с проверкой).
- Бизнес-ограничения: `STRATEGY/REQUIREMENTS.md`.
- Тарифы/обещания: `STRATEGY/PRODUCT.md` + `docs/SELLING_TRUTHS.md` (claim/proof/boundary).
- Контракты Console API: `contracts/console_api/*` (OpenAPI + ошибки).
- Console guide: `docs/CONSOLE_GUIDE.md` (tests/debug/flows).
- Поведение/архитектура: `SPECS/*` (кроме `SPECS/ACTIVE_LEARNING_PLAN.md`; ключевые: `CONSULTANT.md`, `ESCALATION.md`, `ARCHITECTURE.md`).
- Процесс/инструменты (entrypoint): `SPECS/SYSTEM_REFERENCE.md` → section "Start Here — Process Map".
- План/приоритеты: `STRATEGY/TECH_ROADMAP.md`.
- Операционные SOP: `SPECS/SYSTEM_REFERENCE.md` (deploy/knowledge update) + `TECH.md` + `docs/runbooks/*`.
- Решения/GAP: `docs/IMPERIUM_DECISIONS.yaml`, `docs/IMPERIUM_GAPS.yaml`.
- Outbox payload contract: `contracts/events/outbox.webhook_payload.v1.jsonschema`.
- Runtime pack: `truffles-api/app/knowledge/demo_salon/*`; RAG docs: `knowledge/demo_salon/*`.
- Canonical non-salon reference packs (deterministic cross-domain): `truffles-api/app/knowledge/clinic_pack/*`, `truffles-api/app/knowledge/dental_pack/*`.
- Generic pack scaffold (CI/tests): `truffles-api/app/knowledge/generic/*`; RAG docs: `knowledge/generic/*`.
- Derived/статусы: `docs/TECH_STATUS.md`, `SUMMARY.md`, `docs/IMPERIUM_CONTEXT.yaml` (не канон).

---

## КАНОН-FREEZE (как не допустить дрейфа)

- **Норма** живет только в owner-doc из канон-карты; derived-доки не вводят новых правил.
- **Статус/evidence** — только `STATE.md` (и `docs/TECH_STATUS.md`).
- **Обещания наружу** — только `STRATEGY/PRODUCT.md` + `docs/SELLING_TRUTHS.md`.
- **Правка**: меняем owner-doc → проверяем derived → при изменении обещаний/статуса синхронизируем соответствующий owner-doc.
- **Быстрая проверка перед merge**:
  - `rg "СТАТУС РЕАЛИЗАЦИИ|ТЕКУЩИЙ СТАТУС|Где мы сейчас" SPECS STRATEGY docs`
  - `rg "24/7|SLA|минут|refund|бесплат" STRATEGY/PRODUCT.md docs/SELLING_TRUTHS.md`

---

## ЖЕЛЕЗНЫЙ ПРОЦЕСС СЕССИИ (ОБЯЗАТЕЛЕН ВСЕГДА)

**Правило:** если шаг не выполнен — стоп, не продолжать.

1) **Старт:** открыть `STRUCTURE.md` (карта) и `STATE.md` (факты). Проверить, что в `STATE.md` есть краткий **NOW (1 экран)**: фокус, активные CA‑ID/Task Packages, следующие 3 шага, блокеры, последняя evidence‑дата. Если нет — стоп и запросить у Brain или Top Architect обновление.
2) **Owner‑doc:** выбрать единственный owner‑doc для задачи; если не найден — задать вопрос и зафиксировать GAP.
3) **Куда писать:**
   - Норма/инвариант → owner‑doc в `SPECS/*` или `STRATEGY/*`.
   - Статус/evidence → только `STATE.md` (и `docs/TECH_STATUS.md` как derived).
   - Обещания/позиционирование → `STRATEGY/PRODUCT.md` + `docs/SELLING_TRUTHS.md`.
4) **PLAN vs LIVE:** если нет evidence — помечаем как PLAN, не выдаём как факт.
5) **Перед merge:** выполнить `rg`‑проверки из Canon‑Freeze и сверить `git diff --stat`.

---

## ДОК-СТАТУСЫ (CANON / DERIVED / ARCHIVE)

**CANON (истина, спорить нельзя):**
- `STATE.md` — доказательства и текущий статус.
- `STRATEGY/VISION.md` — ДНК/принципы/зачем.
- `STRATEGY/REQUIREMENTS.md` — бизнес‑ограничения.
- `STRATEGY/PRODUCT.md` + `docs/SELLING_TRUTHS.md` — тарифы и внешние обещания.
- `STRATEGY/TECH_ROADMAP.md` — приоритеты и фазы.
- `SPECS/*` (кроме `SPECS/ACTIVE_LEARNING_PLAN.md`) — поведение/архитектура (норматив).
- `docs/SESSION_START_PROMPT.txt` — протокол старта.
- `docs/IMPERIUM_DECISIONS.yaml`, `docs/IMPERIUM_GAPS.yaml` — решения и GAP.
- `docs/runbooks/*` — операционные runbooks (outbox/sentinel/incidents).
- `docs/runbooks/DIALOG_REPORT.md` — dialog-report (таймлайн + решения + outbox + media/ASR).
- `docs/runbooks/TRACE_BUNDLE.md` — bundle диагностика (trace/meta/outbox latency).
- `truffles-api/app/knowledge/<client_slug>/*` — runtime pack (truth/policy/eval).
- `knowledge/<client_slug>/*` — канон RAG‑контента клиента.
- `truffles-api/app/knowledge/generic/*` — generic pack scaffold (CI/tests, no niche).
- `knowledge/generic/*` — generic RAG docs (CI/tests).

**DERIVED (рабочие копии/сводки; не источник истины):**
- `SUMMARY.md`, `docs/IMPERIUM_CONTEXT.yaml`, `docs/TECH_STATUS.md`.
- `Business/*` — бизнес‑документы (sales/legal/onboarding); внешние обещания — только из `STRATEGY/PRODUCT.md` и `docs/SELLING_TRUTHS.md`.
- `prompts/*`, `context/intents/*` — реализации, должны соответствовать `SPECS/*`.

**TEMPLATE/ARCHIVE (не канон, не редактировать как истину):**
- `knowledge/*.md` (в корне) — шаблоны, не участвуют в рантайме.
- `SPECS/ACTIVE_LEARNING_PLAN.md` — архивный план, не канон.
- `ops/templates/*` — шаблоны для заполнения.
- `ops/demo_salon/*` — legacy копии.
- `ops/demo_salon_docs/*` — derived копии для синка/фоллбэка.

---
## ВЕТКИ / TOUCH-LIST

- Правила: не редактировать параллельно один и тот же файл в разных ветках/терминалах; merge только после CI green.
| Branch | Scope | Touch-list (основные файлы/папки) |
|--------|-------|-----------------------------------|
| `dev` | webhook + services | `truffles-api/app/routers/webhook/`, `truffles-api/app/services/*` |
| `data` | eval + facts | `truffles-api/app/knowledge/demo_salon/EVAL.yaml`, `truffles-api/app/knowledge/demo_salon/EVAL_GOLDEN.yaml`, `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml` |
| `docs` | specs + состояния | `SPECS/*`, `STATE.md`, `STRUCTURE.md`, `AGENTS.md` |
| `ops` | CI + deploy | `.github/workflows/*`, `TECH.md`, `/home/zhan/truffles-main/scripts/restart_release.sh`, `/home/zhan/truffles-main/scripts/restart_knowledge_activation_service.sh`, `truffles-api/scripts/knowledge_activation_release_guard.py`, `ops/knowledge_activation_closeout.py`, infra compose (не в этом репо) |

---

## БЫСТРЫЙ ВХОД (если нужно быстро вкатиться)

| Файл | Зачем читать |
|------|--------------|
| `STATE.md` | Базовые факты, текущие блокеры, следующий шаг |
| `STRATEGY/VISION.md` | ДНК и принципы (North Star) |
| `STRATEGY/REQUIREMENTS.md` | Бизнес‑ограничения и DoD |
| `STRATEGY/TECH_ROADMAP.md` | Канон тех‑развития и приоритеты |
| `SPECS/CONSULTANT.md` | Поведение бота (info/consult/booking) |
| `SPECS/ESCALATION.md` | Эскалация, статусы, SLA‑поведение |
| `SPECS/ARCHITECTURE.md` | Рантайм‑архитектура и Decision Graph |
| `SPECS/CONTROL_PLANE.md` | Канон консоли как Control Plane (UX/роли/онбординг) |
| `SPECS/VERTICAL_PACK_KIT.md` | Minimum Data Contract + SAFE_MODE readiness |
| `docs/SESSION_START_PROMPT.txt` | Минимальный протокол старта и проверки фактов |
| `TECH.md` | Доступы, команды, где что работает |
| `truffles-api/app/routers/webhook/` | Входящие WhatsApp (direct + legacy). Модули: `_legacy.py`, `booking.py`, `branch_selection.py`, `context_manager.py`, `decision.py`, `dedup.py`, `guards.py`, `http.py`, `info.py`, `media.py`, `outbox.py`, `parsing.py`, `pending.py`, `policy.py`, `response.py`, `router_sla.py`, `secrets.py`, `session_memory.py`, `shield.py`, `trace.py`. |
| `truffles-api/app/routers/telegram_webhook.py` | Telegram сообщения/кнопки менеджеров |

---

## КОД-КАРТА (entrypoints → pipeline → data)

**Entry points:**
| Узел | Назначение |
|------|------------|
| `truffles-api/app/main.py` | Инициализация приложения |
| `truffles-api/app/routers/webhook/` | Входящие WhatsApp (основной pipeline) |
| `truffles-api/app/routers/telegram_webhook.py` | Менеджерский UI и handoff |
| `truffles-api/app/routers/admin.py` | Админ‑эндпойнты |
| `truffles-api/app/routers/message.py` | Legacy direct‑вход |
| `truffles-api/app/routers/public_entrypoint_contract.py` | Shared public-entrypoint materialization contract surface |

**Pipeline (WhatsApp):**
| Узел | Назначение |
|------|------------|
| `truffles-api/app/routers/webhook/decision.py` | Оркестрация стадий |
| `truffles-api/app/routers/webhook/guards.py`, `shield.py`, `policy.py` | Гейты/безопасность |
| `truffles-api/app/routers/webhook/info.py`, `booking.py`, `pending.py`, `response.py` | Доменные потоки |
| `truffles-api/app/routers/webhook/trace.py`, `outbox.py`, `context_manager.py`, `session_memory.py` | Trace/outbox/memory |

**Services (ядро):**
| Узел | Назначение |
|------|------------|
| `truffles-api/app/services/state_service.py`, `state_machine.py` | Статусы/переходы |
| `truffles-api/app/services/policy_core_guard_orchestration_service.py` | Dedicated non-frozen owner surface for the residual degraded-guard safe-reply / handoff / hold / completed-booking / degraded-collect orchestration family | Backend/Architect |
| `truffles-api/app/services/escalation_service.py`, `manager_message_service.py`, `reminder_service.py` | Эскалация/SLA |
| `truffles-api/app/services/agent_link_service.py` | Telegram linking tokens |
| `truffles-api/app/services/knowledge_service.py`, `pack_runtime_service.py`, `demo_salon_knowledge.py`, `intent_service.py`, `ai_service.py` | Facts/Intent/LLM (`demo_salon_knowledge.py` остаётся adapter-совместимостью) |
| `truffles-api/app/services/outbox_service.py`, `alert_service.py`, `health_service.py` | Надежность/алерты |
| `truffles-api/app/services/console_idempotency.py` | Идемпотентность мутаций Console API |

**Данные и контракты:**
| Узел | Назначение |
|------|------------|
| `truffles-api/app/schemas/*` | Pydantic‑контракты |
| `truffles-api/app/models/*` | Модели БД |
| `truffles-api/app/models/console_idempotency.py` | Idempotency keys для Console API |
| `truffles-api/migrations/*.sql` | SQL миграции для app‑схемы |
| `truffles-api/migrations/006_add_outbox_audit_branch_id.sql` | branch_id для audit/outbox + backfill |
| `truffles-api/migrations/007_backfill_conversations_branch_id.sql` | backfill conversations.branch_id из instanceId |
| `truffles-api/migrations/008_add_agent_link_tokens.sql` | linking tokens для Telegram |
| `truffles-api/app/knowledge/<client_slug>/*` | Truth/policy/eval packs |
| `knowledge/<client_slug>/*` | Канон RAG‑контента |
| `truffles-api/app/knowledge/generic/*` | Generic pack scaffold (CI/tests) |
| `truffles-api/app/knowledge/generic/SYSTEM_LEXICONS.yaml` | System language lexicons (shared) |
| `truffles-api/app/knowledge/generic/SIGNAL_MANIFEST.yaml` | Declarative signal patterns/tokens/layout map for signal services |
| `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml` | Machine-readable owner matrix artifact for active pending-question rows |
| `knowledge/generic/*` | Generic RAG docs (CI/tests) |

---

## .github/ — CI/CD

| Файл | Назначение |
|------|------------|

---

## TESTS

- `truffles-api/tests/test_console_telegram_helpers.py` — Console↔Telegram helper tests.
- `truffles-api/tests/test_console_telegram_connector.py` — Console↔Telegram verify/test helpers.
| `.github/workflows/ci.yml` | GitHub Actions: ruff + pytest + build/push GHCR + deploy (optional) |

---

## SPECS/ — Спецификации (как должно работать)

| Файл | Содержание | Когда читать |
|------|------------|--------------|
| `ESCALATION.md` | Эскалация, напоминания, мьют, метрики | Работа с handovers, Telegram |
| `ACTIVE_LEARNING.md` | Автообучение на ответах менеджеров | Модерация, Qdrant |
| `CONSULTANT.md` | Поведение бота, 9 правил, границы | Промпт, LLM, ответы |
| `ARCHITECTURE.md` | Техническая архитектура, стек, потоки | Новые компоненты |
| `VERTICAL_PACK_KIT.md` | Minimum Data Contract + SAFE_MODE readiness | Онбординг/качество данных |
| `INFRASTRUCTURE.md` | Инфраструктура, безопасность, CI/CD, тесты | DevOps, качество |
| `MULTI_TENANT.md` | Мультитенантность, онбординг | Новый заказчик |
| `SYSTEM_REFERENCE.md` | Системные референсы (интеграции/точки правды) | При аудите/интеграциях |

**Архитектор:** Читать перед проектированием.
**Кодер:** Читать раздел по задаче.

---

## STRATEGY/ — Стратегия (бизнес, продукт)

| Файл | Содержание | Когда читать |
|------|------------|--------------|
| `REQUIREMENTS.md` | Требования Жанбола (закон) | Архитектор: каждую сессию |
| `TECH_ROADMAP.md` | Технический план | Архитектор: планирование |
| `PRODUCT.md` | Тарифы, roadmap продукта | При вопросах о ценах |
| `MARKET.md` | Исследования, метрики, ниши | При вопросах о рынке |
| `VISION.md` | ДНК/принципы (North Star) | Редко |

---

## docs/ — Контекст проекта

| Файл | Содержание |
|------|------------|
| `IMPERIUM_CONTEXT.yaml` | Единый контекст проекта (факты + evidence) |
| `IMPERIUM_DECISIONS.yaml` | CEO-level решения (policy) |
| `IMPERIUM_GAPS.yaml` | Критические пробелы и MVP фиксы |
| `SESSION_START_PROMPT.txt` | Стартовый промпт для новых сессий |
| `TECH_STATUS.md` | Тех‑статус (OK/PARTIAL/BROKEN + evidence) |
| `SELLING_TRUTHS.md` | Честные продающие утверждения (claim/proof/boundary) |

---

## truffles-api/ — Код (Python API)

```
truffles-api/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── webhook.py           # LEGACY: unused; kept for backward compatibility (use routers/webhook/)
│   ├── routers/
│   │   ├── webhook/             # POST /webhook/{client_slug} (direct), POST /webhook (legacy wrapper) — входящие WhatsApp
│   │   ├── telegram_webhook.py  # POST /telegram-webhook — сообщения/кнопки менеджеров
│   │   ├── admin.py             # /admin/* (health/heal/prompt/settings/version)
│   │   ├── alerts.py            # /alerts/test — проверка алертов (токен)
│   │   ├── reminders.py         # /reminders/* — cron напоминаний
│   │   ├── callback.py          # /callback — legacy
│   │   └── message.py           # /message — legacy/manual, не основной путь
│   ├── webhook.py           # LEGACY (unused); do not edit
│   ├── services/
│   │   ├── ai_service.py            # LLM + RAG thresholds + guardrails
│   │   ├── alert_service.py         # Telegram alerts (errors/warnings)
│   │   ├── pack_runtime_service.py  # Neutral runtime facade (delegates to demo adapter)
│   │   ├── demo_salon_knowledge.py  # Truth/policy/phrases для demo_salon
│   │   ├── message_service.py        # save_message + generate_bot_response
│   │   ├── intent_service.py         # Классификация интентов
│   │   ├── knowledge_service.py      # Qdrant RAG поиск + embeddings
│   │   ├── state_machine.py          # ConversationState enum
│   │   ├── state_service.py          # Атомарные переходы + handover create/resolve
│   │   ├── policy_core_guard_orchestration_service.py # Guard-boundary owner for degraded safe reply/handoff/hold/completion/collect
│   │   ├── escalation_service.py     # Telegram уведомления + кнопки
│   │   ├── manager_message_service.py# Ответ менеджера → клиент + auto-learning (owner)
│   │   ├── reminder_service.py       # Напоминания по open handovers
│   │   ├── outbox_service.py         # Outbox enqueue/claim/status
│   │   ├── health_service.py         # self-heal инвариантов
│   │   ├── telegram_service.py       # Telegram API wrapper
│   │   ├── chatflow_service.py       # Отправка сообщений в WhatsApp (ChatFlow)
│   │   └── learning_service.py       # Qdrant upsert по ответам owner
│   ├── knowledge/
│   │   └── demo_salon/          # Канон truth/policy/eval pack (Phase 0)
│   ├── models/              # SQLAlchemy модели
│   │   ├── agent.py              # Роли агентов (owner/admin/manager/support)
│   │   ├── agent_identity.py     # Идентичности агентов (telegram/email)
│   │   ├── learned_response.py   # Очередь обучения (pending/approved)
│   │   ├── outbox_message.py     # Outbox таблица (ACK-first)
│   ├── schemas/             # Pydantic схемы
│   └── database.py          # Database connection
├── tests/                   # Pytest тесты
├── docker-compose.yml       # Локальный запуск (на проде НЕ используется)
└── requirements.txt         # Зависимости
```

**Кодер:** Основное место работы.

---

## knowledge/ — База знаний бота

| Файл | Содержание |
|------|------------|
| `faq.md` | Частые вопросы и ответы |
| `objections.md` | Возражения и ответы |
| `cases.md` | Кейсы успеха |
| `examples.md` | Примеры диалогов (как отвечать) |
| `slang.md` | Сленг СНГ (оплата, "ноготочки") |
| `README.md` | Описание формата |
| `demo_salon/` | Канон KB для Qdrant (demo salon docs) |

**Используется:** RAG поиск, промпт.

---

## context/intents/ — Примеры интентов

16 файлов с примерами фраз для каждого интента:
- `pricing.txt` — "сколько стоит?"
- `human_request.txt` — "позовите менеджера"
- `complaint.txt` — "не работает"
- и т.д.

**Используется:** Intent classification.

---

## prompts/ — Промпты

| Файл | Назначение |
|------|------------|
| `system_prompt_v1.md` | Текущий системный промпт бота |
| `intent_classifier.md` | Промпт для классификации |
| `summarizer.md` | Промпт для суммаризации |
| `llm_plan.md` | Промпт Hybrid LLM plan |
| `llm_policy_core.md` | Промпт LLM policy core |

---

## ops/ — Операционные скрипты

**90% МУСОР** — одноразовые скрипты (старая архитектура).

**Полезное:**
| Файл | Назначение |
|------|------------|
| `monitor.sh` | Мониторинг сервера |
| `health_check.py` | Проверка здоровья системы |
| `onboard_client.py` | План (файла нет). Реальный онбординг: `sync_client.py` + `SPECS/MULTI_TENANT.md` |
| `update_prompt.py` | Обновление промпта через API |
| `metrics_daily_snapshot.sql` | Снимок дневных метрик (SLA/LLM/эскалации) |
| `ops/results/booking_quality.json` | Baseline метрик LLM booking quality runner | QA/OPS/Brain |
| `knowledge_backlog_top.sql` | Топ‑вопросы knowledge backlog (последние 7 дней) |
| `sync_client.py` | Синк/валидация client_pack в Qdrant |
| `migrations/` | SQL миграции |
| `k6/` | k6 load/soak сценарии (Console gates) |
| `templates/` | Шаблоны (промпты, FAQ) |
| `LESSONS_LEARNED.md` | Уроки из отладки |

Миграции:
- `ops/migrations/009_add_conversation_context.sql` — JSONB `conversations.context` для диалогового контекста/слотов.
- `ops/migrations/011_add_webhook_secret.sql` — `client_settings.webhook_secret` для защиты /webhook.
- `ops/migrations/012_add_outbox_messages.sql` — Outbox для ACK-first обработки.
- `ops/migrations/013_add_agents_and_learning_queue.sql` — роли/идентичности + очередь обучения + branch_id.
- `ops/migrations/014_add_branch_routing_settings.sql` — настройки branch routing + auto-approve ролей.
- `ops/migrations/015_add_metrics_daily.sql` — дневные метрики (SLA/LLM/эскалации).
- `ops/migrations/016_add_asr_metrics.sql` — метрики ASR (fail rate + totals).
- `ops/migrations/017_add_knowledge_backlog.sql` — backlog пропусков (low_confidence/out_of_domain/llm_timeout/clarify).
- `ops/migrations/018_add_outbox_meta.sql` — JSONB meta в `outbox_messages` для таймингов/метаданных.
- `ops/migrations/019_add_metrics_analytics_daily.sql` — KPI‑метрики аналитики (truth-first).

**Старые скрипты:** `.archive/ops_old/` — не в git.

---

## Business/ — Бизнес документы

| Папка | Содержание |
|-------|------------|
| `Legal/` | Договоры, NDA, политика обработки данных, согласие на обработку, SLA, акт, политика возврата, AI disclosure, ограничение ответственности, счет-шаблон |
| `Sales/` | Бриф клиента, скрипты, billing rules (`Sales/BILLING_COUNTING.md`) |
| `Onboarding/` | Чеклист запуска, инструкция клиента |
| `Support/` | Регламент техподдержки |

**Не для кода.**

---

## .archive/ — Архив

Старые документы, исследования. Не трогать, но можно смотреть для контекста.

---

## .factory/droids/ — Droid'ы

| Файл | Роль |
|------|------|
| `truffles-architect.md` | Архитектор — проектирует |
| `truffles-coder.md` | Кодер — реализует |
| `truffles-ops.md` | DevOps — инфраструктура |

---

## tests/ — Тесты

| Файл | Что тестирует |
|------|---------------|
| `truffles-api/tests/test_cases.json` | Тестовые сценарии диалогов |
| `truffles-api/tests/test_console_rbac.py` | Unit: Console RBAC matrix guards |
| `truffles-api/tests/test_console_telegram_connector.py` | Unit: Console Telegram verify/test helpers |
| `truffles-api/tests/test_console_telegram_helpers.py` | Unit: Console Telegram trail helpers |
| `truffles-api/tests/test_webhook_booking.py` | Unit: expected_reply_type и booking slot validators |
| `truffles-api/tests/test_webhook_dedup.py` | Unit: webhook buffer/dedup helpers |
| `truffles-api/tests/test_webhook_response.py` | Unit: CTA и quiet hours helpers |
| `truffles-api/tests/test_reasoning_core.py` | Unit: Reasoning Core contract/wiring |
| `truffles-api/tests/test_minimum_data_contract.py` | Unit: Minimum Data Contract validator |
| `truffles-api/tests/test_safe_mode_gate.py` | Unit: Minimum Data safe-mode gate |
| `truffles-api/tests/test_admin_health.py` | Unit: Admin health minimum-data readiness |
| `truffles-api/tests/test_pack_compiler.py` | Unit: pack compiler artifacts + checksum |
| `truffles-api/tests/test_cross_domain_signal_contract_suite.py` | Unit: cross-domain info/booking/tool_registry contract on two non-salon runtime packs |
| `truffles-api/tests/architecture/` | Deterministic architecture guard tests (legacy freeze, continuity writer, proof blackbox, packet consistency) | QA/Backend/Architect |
| `truffles-api/tests/test_interaction_owner_matrix_contract.py` | Unit: schema/artifact contract for machine-readable interaction owner matrix |
| `truffles-api/tests/test_owner_resolver.py` | Unit: resolver-driven row matching for the executable interaction owner slice |
| `truffles-api/tests/test_consultant_core_runtime_contracts.py` | Unit: runtime contract schemas + typed consultant core scaffolding |
| `truffles-api/tests/test_policy_dsl.py` | Unit: policy DSL schema validation |
| `truffles-api/tests/test_knowledge_registry_chunking.py` | Unit: Qdrant pack chunking by size |

---

# НАЧАЛО СЕССИИ

## Архитектор (терминал 1)

```bash
droid --droid truffles-architect
```

**Читать:**
1. `STATE.md` — состояние, план, что дальше
2. `AGENTS.md` — принципы
3. `STRUCTURE.md` — где что лежит
4. `SPECS/*` — по необходимости

**Вопрос себе:** Что в плане? Что конкретно нужно сделать?

---

## Кодер (терминал 2)

```bash
droid --droid truffles-coder
```

**Читать:**
1. `STRUCTURE.md` — где код
2. `TECH.md` — команды, доступы
3. Задачу от архитектора

**Вопрос себе:** Понял ли я задачу? Какие файлы трогать?

---

## Жанбол

**Читать при необходимости:**
- `HOW_TO_WORK.md` — как работать с droid'ами
- `STATE.md` — что сейчас, какой план

---

# ГДЕ ИСКАТЬ ОТВЕТЫ

| Вопрос | Где искать |
|--------|------------|
| Как должна работать эскалация? | `SPECS/ESCALATION.md` |
| Какие тарифы? | `STRATEGY/PRODUCT.md` |
| Как подключить заказчика? | `SPECS/MULTI_TENANT.md` |
| Какие команды на сервере? | `TECH.md` |
| Как тестировать live‑check и CA‑audit? | `SPECS/SYSTEM_REFERENCE.md` (Live‑check SOP), `STRATEGY/TECH_ROADMAP.md` (CA‑plan) |
| Как бот должен отвечать? | `SPECS/CONSULTANT.md`, `knowledge/examples.md` |
| Какие интенты есть? | `context/intents/` |
| Какой код за что отвечает? | `SPECS/ARCHITECTURE.md` |
| Что было сделано? | `CHANGELOG.md` |
| Требования Жанбола? | `STRATEGY/REQUIREMENTS.md` |
| Метрики, исследования? | `STRATEGY/MARKET.md` |

---

# МУСОР (можно удалить)

```
ops/check_*.py        # ~100 файлов — одноразовая отладка
ops/fix_*.py          # ~50 файлов — одноразовые фиксы
ops/add_*.py          # ~20 файлов — добавление нод
ops/get_*.py          # ~10 файлов — отладка
ops/*.sql             # Большинство — одноразовые запросы
ops/*.sh              # По умолчанию одноразовое; canonical keep-скрипты перечислены ниже
```

**Сохранить из ops/:**
- `monitor.sh`
- `start_bge_m3.sh`
- `backup_postgres.sh`
- `backup_qdrant.sh`
- `health_check.py`
- `sync_client.py`
- `manual_sync_demo.py`
- `migrations/`
- `templates/`
- `LESSONS_LEARNED.md`
- `README.md`

---

*Создано: 2025-12-10*

- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o68-invalid-schema-service-grounded-booking-owner-a1.md` — bounded child TP for `r93/M17`, covering invalid-schema service-grounded degraded-booking recovery.
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o69-time-window-slot-constraint-collect-owner-a1.md` — bounded child TP for `r94/M18`, covering declarative time-window slot-constraint recovery under active `time` collect.
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o70-invalid-schema-booking-request-specialist-followup-a1.md` — bounded child TP for `r95/M19`, covering invalid-schema named-specialist booking-request follow-up recovery.
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o71-check-booking-stale-service-choice-governance-a1.md` — bounded child TP for `r96/M20`, covering stale `check_booking/service_choice` governance cleanup.
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o72-active-name-deictic-time-availability-owner-a1.md` — bounded child TP for `r101/M21`, covering active-name deictic requested-slot follow-up ownership after explicit time grounding.
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o73-question-like-daypart-exact-time-fill-owner-a1.md` — bounded child TP for `r102/M22`, covering question-like daypart phrasing that still carries an explicit exact-time fill under active `time` collect.
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o74-active-name-named-specialist-followup-owner-a1.md` — bounded child TP for `r103/M23`, covering declarative named-specialist follow-up under active `name` collect after grounded time.
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o75-active-time-consult-topic-shift-service-choice-owner-a1.md` — bounded child TP for `r104/M24`, covering standalone consult/service-topic shift that must clear stale booking `time` resume.
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o76-initial-timeout-requested-slot-owner-a1.md` — bounded child TP for `r105/M25`, covering first-time requested-slot timeout fallback under active `time` collect that must preserve `ask_about_requested_slot(time)` evidence.
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o77-active-time-daypart-preference-info-signal-false-positive-a1.md` — bounded child TP for `r106/M26`, covering matched active-time daypart-preference turns that must not leak `hours` / `duration` info-class signals.
- `docs/TASK_PACKAGES/TP-2026-03-11-p1.6o78-booking-confirm-pricing-interrupt-service-choice-drift-a1.md` — bounded child TP for `r112/M27`, covering pricing interrupts under booking time confirmation that must preserve grounded service and `expected_reply_type=time` instead of reopening `service_choice`.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o79-executable-interaction-core-redesign-reset-a1.md` — doc-only forensic reset TP that freezes the reactive child chain as mined evidence corpus and makes executable interaction core the default next closure path.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o80-base-canon-interaction-model-sync-a1.md` — doc-only canon-sync TP that promotes interaction target / relation / owner / degrade / forbidden-compression semantics into the base requirements/spec/runbook canon before any runtime migration.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o81-machine-readable-owner-matrix-a1.md` — contract-artifact TP that publishes versioned schema + generic YAML artifact for the remaining interaction owner matrix before persisted-state/runtime migration.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o82-persisted-interaction-state-a1.md` — bounded runtime-state TP that makes `interaction_state` first-class in canonical dialog state + `session_memory` before resolver extraction.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o83-owner-resolver-m27-vertical-slice-a1.md` — bounded runtime TP that adds matrix runtime fields + cached loader + pure resolver and migrates `M27` through the first resolver-driven vertical slice before proof admission.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o84-m27-proof-lane-and-next-row-admission-a1.md` — proof-lane TP that revalidates the deterministic `M27` slice, runs one fresh guarded `dev L2`, records the invalid preflight attempt truthfully, and admits the next surfaced row after `M27` clears.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o85-slot-compare-explicit-time-fill-scenario-governance-a1.md` — bounded scenario-governance TP that normalizes explicit exact-time `slot_compare` turns to canonical `time -> name` expectations before the next proof lane.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o86-post-m28-proof-lane-a1.md` — proof-lane TP that verifies `M28` is gone on a fresh guarded `dev L2`, audits away the invalid first attempt, and admits the next surfaced row after `M28` clears.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o87-booking-tag-requested-slot-governance-a1.md` — bounded scenario-governance TP that targets booking-tag requested-slot questions which should canonicalize back to `ask_about_requested_slot(time)` under active `time` collect.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o88-post-m29-proof-lane-a1.md` — proof-lane TP that verifies `M29` is gone on one fresh guarded `dev L2` after deterministic closure and truthfully admits the next surfaced row, if any.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o89-slot-constraint-generic-free-slot-question-governance-a1.md` — bounded scenario-governance TP that retags generic free-slot questions out of `slot_constraint` and back to `ask_about_requested_slot(time)` under active `time` collect.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o90-post-m30-proof-lane-a1.md` — proof-lane TP that verifies `M30` is gone on one fresh guarded `dev L2` after deterministic closure and truthfully admits the next surfaced row, if any.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o91-invalid-schema-booking-request-specialist-catalog-match-a1.md` — bounded child TP that re-closes reopened `M19` by recovering named-specialist booking-request follow-up from branch catalog before secondary hint fallback.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o92-post-m19-reclosure-proof-lane-a1.md` — proof-lane TP that verifies reopened `M19` is gone on one fresh guarded `dev L2` after deterministic re-closure and truthfully admits the next surfaced row, if any.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o93-generic-specialist-choice-followup-owner-a1.md` — bounded child TP for `r117/M31`, covering generic specialist-choice success-path owner preservation under active `time` collect.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o94-post-m31-proof-lane-a1.md` — proof-lane TP that verifies `M31` is gone on one fresh guarded `dev L2` after deterministic closure and truthfully admits the next surfaced row, if any.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o95-active-name-deictic-day-availability-followup-owner-a1.md` — bounded child TP for `r118/M32`, covering active-name deictic day/date requested-slot follow-up owner preservation and scenario normalization.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o96-post-m32-proof-lane-a1.md` — proof-lane TP that verifies `M32` is gone on one fresh guarded `dev L2` after deterministic closure and truthfully admits the next surfaced row, if any.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o97-active-name-service-info-interrupt-owner-a1.md` — bounded child TP for `r119/M33`, extending the executable owner-matrix path so factual `catalog.service_query` side-questions under active `name` resume preserve the requested-slot owner contract.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o98-post-m33-proof-lane-a1.md` — proof-lane TP that verifies `M33` is gone on one fresh guarded `dev L2` after deterministic closure and truthfully admits the next surfaced row, if any.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o99-active-name-timeout-specialist-choice-followup-a1.md` — bounded child TP for `r120/M34`, covering question-like named-specialist choice under active `name` collect that still loses timeout specialist-followup ownership and stale `service_choice` expectations.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o100-post-m34-proof-lane-a1.md` — proof-lane TP that verifies `M34` is gone on one fresh guarded `dev L2` after deterministic closure and truthfully admits the next surfaced row, if any.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o101-slot-compare-generic-free-slot-question-governance-a1.md` — bounded scenario-governance TP for `r121/M35`, retagging generic free-slot `slot_compare` questions back to canonical `ask_about_requested_slot(time)` under active `time` collect.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o102-post-m35-proof-lane-a1.md` — proof-lane TP that verifies `M35` is gone on one fresh guarded `dev L2` after deterministic closure and truthfully admits the next surfaced row, if any.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o103-grounded-partial-date-daypart-fill-governance-a1.md` — bounded scenario-governance TP for `r122/M36`, normalizing grounded partial-date daypart availability follow-ups from stale `mixed_fill_plus_question/time` to canonical `time -> name`.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o104-post-m36-proof-lane-a1.md` — proof-lane TP that verifies `M36` is gone on one fresh guarded `dev L2` after deterministic closure and truthfully admits the next surfaced row, if any.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o105-timeout-active-booking-name-fill-followup-a1.md` — bounded runtime TP for `r123/M37`, keeping explicit booking slot fill inside timeout-degraded active-booking follow-up instead of `pack_fact_fallback`.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o106-post-m37-proof-lane-a1.md` — proof-lane TP that verifies `M37` is gone on one fresh guarded `dev L2` after deterministic closure and truthfully admits the next surfaced row, if any.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o107-active-time-timeout-generic-specialist-choice-followup-a1.md` — bounded runtime TP for `r124/M38`, routing timeout-degraded generic specialist-change turns under active `time` collect through the specialist-target interrupt while keeping the explicit `time` follow-up prompt.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o108-post-m38-proof-lane-a1.md` — proof-lane TP that verifies `M38` is gone on one fresh guarded `dev L2` after deterministic closure and truthfully admits the next surfaced row, if any.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o109-active-time-services-overview-interrupt-owner-a1.md` — bounded runtime TP for `r125/M39`, promoting grounded service-info side questions under active `time` collect into the existing `catalog.service_query` interrupt path before stale collect prompt emission.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o110-post-m39-proof-lane-a1.md` — fresh proof-lane TP after deterministic `M39` closure; requires one fingerprint-verified guarded `dev L2` and truthful admission of the next family.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o111-active-time-partial-date-fill-timeout-degraded-collect-governance-a1.md` — bounded scenario-governance TP for `r126/M40`, aligning pure partial-date fills under active `time` collect to canonical `time -> name` after grounded `datetime`.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o112-post-m40-proof-lane-a1.md` — fresh proof-lane TP after deterministic `M40` closure; requires one fingerprint-verified guarded `dev L2` and truthful admission of the next family.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o113-openai-preflight-transport-dedupe-timeout-alignment-a1.md` — bounded infra/tooling TP that removes repeated OpenAI preflight false-negatives by deduping identical `llm`/`judge` transport probes and respecting the configured timeout budget.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o114-active-time-time-preference-timeout-guidance-owner-a1.md` — bounded runtime TP for `r127/M41`, keeping generic time-preference statements under active `time` collect inside `booking_slot_guidance` instead of `truth_gate service_duration`.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o115-post-m41-proof-lane-a1.md` — fresh proof-lane TP after deterministic `M41` closure; requires one fingerprint-verified guarded `dev L2` and truthful admission of the next family.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o116-active-name-deictic-time-occupancy-followup-governance-a1.md` — bounded scenario-governance TP that re-closes reopened `M21` for deictic occupancy wording like `А если это время занято?` under active `name` resume.
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o117-post-m21-reclosure-proof-lane-a1.md` — fresh proof-lane TP after deterministic re-closure of reopened `M21`; requires one fingerprint-verified guarded `dev L2` and truthful admission of the next family.
- `docs/TASK_PACKAGES/TP-2026-03-13-p1.6o118-class-level-closure-process-reset-a1.md` — worktree-level process reset TP that keeps `P1.6o117` as the immediate proof gate but moves the remaining work onto class-level triage and structural follow-up tracks.
- `docs/TASK_PACKAGES/TP-2026-03-13-p1.6o119-timeout-degrade-owner-boundary-first-slice-a1.md` — first structural `Track C` TP that targets shared timeout/degrade owner-boundary precedence before degraded info/fact fallback on matched booking-collect turns.
- `docs/TASK_PACKAGES/TP-2026-03-13-p1.6o120-post-track-c-proof-lane-a1.md` — post-`Track C` proof-lane TP that refreshes a fingerprint-verified live runtime and truthfully checks whether timeout/degrade is still the first surfaced class.
- `docs/TASK_PACKAGES/TP-2026-03-13-p1.6o121-booking-slot-guidance-scenario-convergence-first-slice-a1.md` — first structural `Track A` TP that makes scenario/oracle derive active booking slot-guidance expectations from canonical runtime interaction semantics instead of stale `slot_compare` generator knowledge.
- `docs/TASK_PACKAGES/TP-2026-03-13-p1.6o122-post-track-a-proof-lane-a1.md` — post-`Track A` proof-lane TP that verifies the covered slot-guidance family is no longer first fail and truthfully surfaces the next remaining class on a fingerprint-verified live runtime.
- `docs/TASK_PACKAGES/TP-2026-03-13-p1.6o123-active-service-choice-service-info-progress-scenario-convergence-a1.md` — bounded runtime-first continuity TP that emits explicit `catalog_service_booking_progress` for service-grounded factual interrupts under active booking continuity and syncs oracle only on that same bounded contour.
- `docs/TASK_PACKAGES/TP-2026-03-13-p1.6o124-post-service-info-progress-proof-lane-a1.md` — post-`P1.6o123` proof-lane TP that verifies the covered service-info continuity family is no longer first fail on a fingerprint-verified live runtime and truthfully classifies the next remaining class.
- `docs/TASK_PACKAGES/TP-2026-03-13-p1.6o125-proof-lane-tool-evidence-fail-fast-validity-a1.md` — bounded proof-validity TP that makes strict `tool_evidence` bind to observed booking-tool opportunity/evidence in the executed prefix instead of unexecuted booking tails after fail-fast proof stops.
- `docs/TASK_PACKAGES/TP-2026-03-13-p1.6o126-post-tool-evidence-proof-lane-a1.md` — post-`P1.6o125` proof-lane TP that reruns one fresh fingerprint-verified guarded `dev L2` after the tool-evidence validity closure and truthfully classifies the next remaining class on admissible proof evidence.
- `docs/TASK_PACKAGES/TP-2026-03-13-p1.6o127-pending-handoff-resume-boundary-first-slice-a1.md` — bounded runtime-owner TP that preserves booking follow-up continuity across pending/handoff soft-pass and transport-degraded re-entry so factual booking-side interrupts do not erase the active booking question contract.
- `docs/TASK_PACKAGES/TP-2026-03-13-p1.6o128-post-pending-handoff-resume-proof-lane-a1.md` — post-`P1.6o127` proof-lane TP that truthfully proves the pending/handoff runtime-owner family is displaced and routes the next remaining class from fresh admissible evidence.
- `docs/TASK_PACKAGES/TP-2026-03-13-p1.6o129-active-time-named-specialist-followup-scenario-convergence-a1.md` — bounded `Track A` scenario-governance TP that converges active-time named specialist preference availability turns onto generalized specialist-followup expectations without path-specific owner duplication.
- `docs/TASK_PACKAGES/TP-2026-03-13-p1.6o130-post-active-time-named-specialist-followup-proof-lane-a1.md` — post-`P1.6o129` proof-lane TP that reruns one fresh fingerprint-verified guarded `dev L2` after the named specialist followup `Track A` closure and truthfully classifies the next remaining class on admissible proof evidence.
- `docs/TASK_PACKAGES/TP-2026-03-13-p1.6o134-audited-infra-non-canonical-lock-retry-admission-a1.md` — bounded proof-process TP that restores admissible unchanged-fingerprint lock retry only for audited infra-invalid non-canonical locks with invalid run integrity after runtime recovery outside repo code.

- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-decision-a922.md` — doc-only terminal convergence TP that selects `finish_mode`, locks the final `reasoning_core -> decision.py` transport seam as the remaining structural blocker, and redirects the next move to one terminal convergence bundle.

- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-bundle-a922.md` — implementation TP that locks the final live `reasoning_core -> decision.py` transport fallback plus continuity-guard drift into one bounded terminal convergence bundle under `finish_mode`.

- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-broader-residual-family-decision-a922.md` — doc-only decision TP that records the truthful `GAP` on the narrower terminal bundle and locks the broader residual family as the next admissible rooted target.
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-broader-residual-family-bundle-a922.md` — implementation TP for bounded runtime cuts inside the locked broader residual family; current landed cuts include the policy-core rescue / payload-normalization bypass, the bounded timeout-degraded `services_overview` info-fallback bypass, the bounded timeout-degraded active-name time-availability followup bypass, and the bounded timeout-degraded specialist-followup snapshot-drift bypasses before fallback.
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-broader-residual-family-post-implementation-audit-a922.md` — doc-only audit TP that records the latest bounded broader-residual-family seam death, classifies the surviving broader frozen residual family, and locks whether the next move stays inside the same rooted family.
- `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-prep-a922.md` — doc-only prep TP that switches the active consultant-core block from runtime demolition to acceptance-evidence preparation, freezes the latest non-canonical canary facts, and locks the next move to one bounded evidence bundle instead of another runtime slice.
- `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-evidence-bundle-a922.md` — bounded implementation TP that classifies surfaced `r79` as a shared promo interrupt contract bug, repairs the shared info-intent resolver, and prepares truthful guarded canary re-entry.
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-final-ingress-coordinator-terminal-closure-acceptance-reentry-bundle-a922.md` — fresh implementation TP for the post-`r20` acceptance re-entry bundle, proving the first remaining blocker is `go_to_full` evidence-pack materialization rather than another demo-salon runtime family.

- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-debug-cadence-reset-and-shadow-def-guard-a922.md` — meta-level implementation TP that resets consultant-core residual debugging to family-first cadence, adds explicit forensic continuation ergonomics, and locks current shadowed top-level def debt in `reasoning_core.py`.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-debug-cadence-reset-and-shadow-def-guard-a922.md` — artifact report for the cadence-reset / shadow-def-guard block, including structural hotspot evidence and the preserved next move back to turn-11 runtime work.
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md` — implementation TP for the bounded non-frozen turn-11 check-booking reference continuity repair, including snapshot-grounding normalization and focused deterministic regression before guarded replay.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md` — artifact report for the bounded turn-11 runtime implementation, focused regression results, and the handoff to guarded replay.
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-canary-replay-a922.md` — closure TP for truthful guarded replay `r17`, including strict audit and fresh canary classification after the turn-11 repair.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-canary-replay-a922.md` — replay report for `r17`, proving turn-11 and turn-13 closure on fresh evidence while surfacing the next turn-8 runtime family and remaining proof debt.
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn8-booking-interrupt-exact-time-progression-runtime-implementation-a922.md` — implementation TP for the bounded turn-8 booking-interrupt exact-time progression repair in the live later duplicate booking-prompt owner.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn8-booking-interrupt-exact-time-progression-runtime-implementation-a922.md` — implementation report for the turn-8 repair, including focused deterministic proof and the replay handoff.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-final-acceptance-go-to-full-evidence-pack-family-a922.md` — evidence-pack report for the post-`r20` acceptance lane, including fresh `L1`, green seed `7`, and the seed-`19` semantic stop condition before checklist assembly.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-decision-a922.md` — decision report classifying the fresh seed-`19` generated multi-seed blocker as a bounded runtime-semantic family and deferring advisory proof debt.
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-implementation-a922.md` — implementation TP for the bounded seed-`19` runtime family, deferring direct side owners and restoring explicit hours/promo interruption continuity before replay.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-runtime-implementation-a922.md` — implementation report for the seed-`19` repair, including focused deterministic proof and the replay handoff.
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md` — replay TP for the first exact post-fix seed-`19` run against the original blocker scenarios.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-generated-booking-info-divergence-canary-replay-a922.md` — replay report proving the next blocker is infra/tool-evidence `confirm_hook_missing` before any new runtime move.
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md` — decision TP for locking exact replay `r4` to a bounded confirm-hook proof/tool-evidence parity family before any new runtime move.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-proof-decision-a922.md` — decision report proving `r4` is blocked by confirm-hook parity in `ops/diagnose.py` and handing off the bounded proof implementation lane.
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md` — implementation TP for repairing the bounded `r4` confirm-hook proof parity family inside `ops/diagnose.py`.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-contract-aligned-confirm-hook-proof-implementation-a922.md` — implementation report for the `r4` confirm-hook parity repair, including deterministic proof and replay handoff.
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md` — replay TP for the first fresh exact replay after the bounded `r4` confirm-hook proof repair.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r4-confirm-hook-canary-replay-a922.md` — replay report proving the old `confirm_hook_missing` blocker is closed and runtime reclassification is now admissible on seed `19`.
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-decision-a922.md` — decision TP for locking fresh replay `r5` to a bounded post-verification exact-time reschedule runtime continuity family.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-decision-a922.md` — decision report proving `r5` now surfaces a real runtime continuity bug at dialog `1`, turn `13` after proof parity closure.
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md` — implementation TP for the bounded seed-`19` post-verification exact-time reschedule runtime repair before fresh exact replay.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md` — implementation report for the seed-`19` post-verification exact-time reschedule runtime repair, including focused deterministic proof and replay handoff.
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r6-allowlist-safe-preflight-fallback-proof-implementation-a922.md` — implementation TP for the bounded `r6` replay fallback proof repair so contaminated preflight stays on allowlist-safe JIDs.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r6-allowlist-safe-preflight-fallback-proof-implementation-a922.md` — implementation report proving the old non-allowlist fallback blocker is closed before fresh replay reclassification.
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-decision-a922.md` — decision TP for classifying the fresh `r7` preflight stop as a bounded runtime simulation-transport family.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-decision-a922.md` — decision report proving the next blocker is the executable explicit-handoff owner simulation transport seam, not more replay fallback drift.
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-implementation-a922.md` — implementation TP for the bounded seed-`19` simulation transport repair on the executable explicit-handoff owner.
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-runtime-implementation-a922.md` — implementation report proving the live explicit-handoff owner now honors simulation-safe transport before fresh exact replay.
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-canary-replay-a922.md` — replay TP for the first fresh exact replay after the bounded simulation transport repair, including stale `r10` artifact hygiene.
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r7-session-reset-simulation-transport-canary-replay-a922.md` — replay report proving the old provider-transport blocker is no longer first and that fresh replay `r11` surfaced a different preflight-clear family.
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-decision-a922.md` — decision TP for classifying fresh replay `r11` as a bounded pending-ack greeting-intercept runtime family.
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-decision-a922.md` — decision report proving the live greeting owner now blocks pending-clear during session-reset preflight.
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-implementation-a922.md` — implementation TP for the bounded seed-`19` pending-ack greeting-intercept runtime repair on the executable later greeting owner.
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-runtime-implementation-a922.md` — implementation report proving the live greeting owner now defers pending-ack traffic during session-reset clear before fresh exact replay.
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-canary-replay-a922.md` — replay TP for the first fresh exact replay after the bounded pending-ack greeting-owner repair.
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r11-session-reset-pending-ack-greeting-intercept-canary-replay-a922.md` — replay report proving the old greeting-owner blocker is no longer first and that fresh replay `r12` surfaced a different preflight-clear family.
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-runtime-decision-a922.md` — decision TP for classifying fresh replay `r12` as a bounded pending-ack explicit-handoff runtime family.
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-runtime-decision-a922.md` — decision report proving the live explicit-handoff owner now blocks pending-clear during session-reset preflight.
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-runtime-implementation-a922.md` — implementation TP for the bounded seed-`19` pending-ack explicit-handoff runtime repair on the executable later explicit-handoff owner.
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-runtime-implementation-a922.md` — implementation report proving the live explicit-handoff owner now defers pending-ack traffic during session-reset clear before fresh exact replay.
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-canary-replay-a922.md` — replay TP for the first fresh exact replay after the bounded pending-ack explicit-handoff repair, with invalid `r13` explicitly excluded before truthful closure.
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r12-session-reset-pending-ack-explicit-handoff-intercept-canary-replay-a922.md` — replay report proving the old explicit-handoff blocker is no longer first and that fresh replay `r14` surfaced terminal unresolved fallback instead.
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-decision-a922.md` — decision TP for classifying fresh replay `r14` as a bounded pending-ack terminal-unresolved runtime family.
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-implementation-a922.md` — implementation TP for the bounded seed-`19` pending-ack terminal-unresolved runtime repair that reuses the existing pending continuity contract.
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-decision-a922.md` — decision report proving the runtime now falls through to terminal unresolved fallback during session-reset preflight clear.
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-runtime-implementation-a922.md` — implementation report proving the live owner chain now routes pending-ack traffic through the pending continuity contract before terminal fallback.
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-post-cancel-rebooking-continuity-handoff-info-authority-reset-closure-replay-a922.md` — closure replay report for fresh `r52`, proving the prior structural block stayed deterministic-only and surfacing the exact booking reentry / promotions continuity family on live runtime.
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-reentry-booking-prompt-authority-decision-a922.md` — delete-first decision TP that maps the `r52` family into one exact authority-reset block for booking reentry and service-grounded promotions continuity.
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-reentry-booking-prompt-authority-reset-structural-implementation-a922.md` — implementation TP for moving booking reentry authority to `booking_prompt_owner` and centralizing tool-reply continuity sync on the artifact fast path.
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-reentry-booking-prompt-authority-reset-structural-implementation-a922.md` — implementation report proving the touched booking reentry / promotions continuity seams are deleted or unreachable before the next closure replay.
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-tool-protocol-execution-projection-a922.md` — implementation TP for eliminating the active tool semantic dialect by making `referents` canonical across `policy-core -> schema -> executor -> tool projection -> runtime trace/meta`, while demoting legacy `tool_args.*` to execution-shadow only.
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-pack-grounding-projection-a922.md` — implementation TP for eliminating the active pack/grounding semantic dialect by making pack runtime emit canonical grounding across `pack -> executor -> runtime continuity/state -> trace/meta`, while demoting `resolver_contract` / `resolver_candidates` / `slot_candidates` to compatibility-only projections.
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-projection-reduction-a922.md` — implementation TP for reducing the active question-projection dialect by making `pending_question_contract` canonical across typed runtime continuity, policy-core memory, pending-resume snapshots, and runtime trace/meta, while demoting `expected_reply_*` and `last_question_type` to derived compatibility projections.
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-compatibility-question-readers-reduction-a922.md` — implementation TP for reducing the remaining reasoning/frozen bootstrap question-reader dialect by making canonical context `pending_question_contract` outrank top-level `expected_reply_*` in reasoning-core and frozen webhook expected-reply handling.
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-session-memory-observability-projection-a922.md` — implementation TP for reducing the remaining session-memory observability dialect by making shared trace/reset snapshots emit canonical `pending_question_contract` when present, while retaining `last_question_type` only as fallback for purely legacy memory payloads.
- `docs/TASK_PACKAGES/TP-2026-03-25-consultant-core-canonical-question-evidence-closure-a922.md` — implementation TP for closing the remaining frozen webhook/proof observability tail by making question evidence and llm-quality proof helpers consume canonical `pending_question_contract` before legacy `expected_reply_*` projections, and by adding one bounded end-to-end closure proof across semantic contract, question contract, and trace/meta.

- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-owner-output-singularity-cut-a922.md` — Workstream 1 family: remove mixed owner output and force canonical `SemanticDecisionV1` intake/consumption on hot-path owner-adjacent consumers.
