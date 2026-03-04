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
| `contracts/` | Канон контрактов (Console API, ошибки) | Архитектор/Frontend |
| `contracts/console_api/schemathesis.toml` | Seed/overrides для Schemathesis contract smoke | Backend/QA |
| `contracts/events/` | Контракты событий (outbox) | Архитектор/Backend |
| `contracts/tenancy/tenant_context.v1.jsonschema` | Канон tenant_context (company/client/branch) | Архитектор/Backend |
| `contracts/capabilities/capabilities.v1.jsonschema` | Канон capabilities (channels/providers/features) | Архитектор/Backend |
| `contracts/consult/consult_playbook.v1.jsonschema` | Канон схемы consult playbooks (domain‑agnostic) | Архитектор/Backend |
| `contracts/consult/consult_controller_output.v1.jsonschema` | Канон контракта consult LLM‑контроллера | Архитектор/Backend |
| `contracts/llm/` | Контракты LLM outputs (router + answer_interpreter) | Архитектор/Backend |
| `contracts/llm/dialogue_controller_output.v1.jsonschema` | Контракт LLM‑контроллера (router) | Архитектор/Backend |
| `contracts/llm/answer_interpreter_output.v1.jsonschema` | Контракт LLM answer_interpreter | Архитектор/Backend |
| `contracts/llm/llm_plan_output.v1.jsonschema` | Контракт Hybrid LLM plan | Архитектор/Backend |
| `contracts/llm/llm_policy_core_output.v1.jsonschema` | Контракт LLM policy core | Архитектор/Backend |
| `contracts/packs/` | Pack-compiler artifacts (signal graph, indexes) | Архитектор/Backend |
| `contracts/packs/signal_graph.v1.jsonschema` | Канон сигнального графа (anchors/lexicons) | Архитектор/Backend |
| `contracts/packs/signal_manifest.v1.jsonschema` | Канон signal manifest (regex/tokens/layout map) для signal-layer | Архитектор/Backend |
| `contracts/policy/` | Policy DSL bundles | Архитектор/Backend |
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
| `scripts/restart_workers.sh` | Перезапуск контейнеров воркеров (outbox/sentinel) | OPS |
| `scripts/restart_api.sh` | Канонический деплой API (migration gate + version verify) | OPS |
| `scripts/restart_release.sh` | Канонический release API+workers (digest + parity + migration gate) | OPS |
| `scripts/check_migration_governance.py` | Governance check для SQL миграций (naming/frozen ops migrations) | Backend/OPS |
| `scripts/session_start.sh` | Создать worktree/branch и session log (agent suffix обязателен) | Все роли |
| `scripts/session_check.sh` | Проверка сессии перед commit/push | Все роли |
| `scripts/zero_context_gate.sh` | Проверка полноты TP+Report для zero-context блока | Brain/Architect/Hands |
| `scripts/session_end.sh` | Закрытие сессии + index обновление | Все роли |
| `scripts/session_resume.sh` | Возобновить активную сессию после compaction (по умолчанию SESSION_AGENT) | Все роли |
| `scripts/session_index_rebuild.sh` | Пересобрать `docs/SESSION_INDEX.md` из `docs/SESSIONS/*` | Brain/Architect |
| `scripts/session_audit.sh` | Аудит сессий (статусы/сироты) | Brain/Architect |
| `scripts/session_gate.sh` | Gate для doc-only и session log | Brain/Architect |
| `scripts/install_hooks.sh` | Установка обязательных hooks | Все роли |
| `scripts/test_api_container.sh` | Контейнерный pytest (drift‑safe, sanitized env) | Backend/QA |
| `scripts/booking_confirm_verify.sh` | Runbook скрипт: booking confirm verification + evidence | QA/OPS/Brain |
| `scripts/booking_dialog_scenarios.py` | Генератор booking‑диалогов (10–15 ходов, перебивки, медиа‑шаблоны) | QA/OPS |
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
| `ops/shadow_replay.py` | Shadow replay report (decision_meta/trace comparison) | QA/OPS/Brain |
| `ops/backfill_branch_rag.py` | Backfill Qdrant branch metadata from published knowledge | OPS/Brain |
| `ops/keycloak-theme/` | Тема Keycloak (CSS + лого) для брендинга auth | OPS/Frontend |
| `truffles-api/` | Backend API + workers | Backend |
| `truffles-api/docker-compose.test.yml` | Test‑compose overrides (test containers, no prod env) | Backend/QA |
| `truffles-api/scripts/apply_sql_migrations.py` | SQL migration runner (`schema_migrations` + checksum guard) | Backend/OPS |
| `truffles-api/app/services/onboarding_state.py` | Server-side onboarding state machine (Console) | Backend |
| `truffles-api/app/services/console_confirmations.py` | Confirmation safeguards for destructive Console actions | Backend |
| `truffles-api/app/services/console_owner_admin.py` | Owner/Admin business helpers extracted from `console.py` | Backend |
| `truffles-api/app/services/console_knowledge_preflight.py` | Knowledge publish preflight helpers (`draft_hash`, recent validate gate) | Backend |
| `truffles-api/app/services/capabilities_runtime.py` | Runtime capabilities context (client_capabilities → decision/booking) | Backend |
| `truffles-api/app/services/knowledge_runtime.py` | Runtime published pack truth (knowledge_versions → demo_salon resolver) | Backend |
| `truffles-api/app/services/reasoning_core.py` | Unified Reasoning Core API (signals -> gates -> actions -> compose -> trace) | Backend/Architect |
| `truffles-api/app/services/pack_compiler_service.py` | Pack compiler (compiled artifacts, hashing, schema validation) | Backend/Architect |
| `truffles-api/app/services/learned_response_service.py` | Auto-ingest + approval wiring for learned responses | Backend |
| `truffles-api/app/services/calendar_sync_service.py` | Calendar provider sync via outbox + cursors + busy blocks | Backend |
| `truffles-api/app/services/tool_registry_service.py` | Tool registry executor (calendar/catalog) for LLM plan | Backend |
| `truffles-api/app/services/pack_query_backend_service.py` | Distributed pack-query backend adapter contract (runtime_local/shadow/primary) | Backend |
| `truffles-api/app/services/info_signal_service.py` | Info/lexicon signal helpers (routing-neutral) | Backend |
| `truffles-api/app/services/booking_signal_service.py` | Booking/date/time signal helpers (manifest-backed regex/tokens + lexicon) | Backend |
| `truffles-api/app/services/signal_manifest_service.py` | Signal manifest runtime compiler/loader (schema validation + signature cache + version meta) | Backend |
| `truffles-api/app/services/appointment_reminder_service.py` | Appointment reminder/follow-up jobs + outbox enqueue | Backend |
| `truffles-api/app/services/metrics_daily_service.py` | Daily metrics snapshot (metrics_daily) | Backend |
| `truffles-api/app/services/marketing/service.py` | Marketing Pro lifecycle/audience/preflight/execute/retry logic | Backend |
| `truffles-api/app/models/alert_event.py` | DB model for alert events (analytics) | Backend |
| `truffles-api/app/models/console_confirmation.py` | DB model for confirmation requests (Console) | Backend |
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
| `truffles-api/app/routers/inbox_service.py` | Router для Inbox Service | Backend |
| `truffles-api/app/routers/decision_core.py` | Router для Decision Core | Backend |
| `truffles-api/app/routers/outbox_service.py` | Router для Outbox Service | Backend |
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
| `truffles-api/scripts/console_e2e_seed.py` | Seed для стабильных console‑e2e данных | Backend/QA |
| `console-web/` | Console UI (Next.js, Dockerfile) | Frontend |
| `console-web/src/app/insights/page.tsx` | Insights/Analytics page (read-only daily metrics) | Frontend |
| `console-web/src/app/marketing/page.tsx` | Marketing Pro lifecycle UI (preview/approval/preflight/execute) | Frontend |
| `console-web/src/components/TenantsScopedErrorSummary.tsx` | Scoped error summary для Tenants workspace зон | Frontend |
| `console-web/src/components/TenantsSensitiveIdCell.tsx` | Mask/reveal/copy ячейка чувствительного `instance_id` с audit hook | Frontend |
| `console-web/src/components/TenantsQuickCreatePanel.tsx` | Вынесенный quick-create блок Tenants (компания/клиент/филиал) с явными label-id для a11y | Frontend |
| `console-web/src/components/TenantsOperationalKpiPanel.tsx` | Вынесенная панель операционных KPI/alert hooks/weekly snapshots для Tenants (platform_admin) | Frontend |
| `console-web/src/app/tenants/use-tenants-scope-derived-state.ts` | Derived scope/state hook для `/tenants` (context names/maps/filter options) | Frontend |
| `console-web/src/app/tenants/tenants-page-helpers.ts` | Shared helpers/types/formatters for Tenants page (lifecycle audit, branch patch/snapshot, scope/date labels) | Frontend |
| `console-web/src/app/tenants/use-tenants-action-queue.ts` | Hook для action-queue orchestration и archive predicate в `/tenants` | Frontend |
| `console-web/src/app/tenants/use-tenants-operational-model.ts` | Hook для вычисления Tenants operational KPI/drilldown/alert/report модели | Frontend |
| `console-web/e2e/` | Playwright smoke/login/setup тесты (storageState) | Frontend/QA |
| `console-web/e2e/tenants-a11y.spec.ts` | Live Playwright + Axe evidence для Tenants (desktop/mobile) | Frontend/QA |
| `console-web/eslint.config.js` | ESLint flat config для console-web | Frontend |
| `console-web/.env.e2e.example` | Шаблон env для console‑e2e | Frontend/QA |
| `console-web/public/brand/` | Бренд‑ассеты консоли (логотипы) | Frontend |
| `console-web/src/app/api/calendar/callback/route.ts` | Console API proxy for Google Calendar OAuth callback | Frontend |
| `docs/CONSOLE_GUIDE.md` | Guide по Console (API, тесты, дебаг) | Frontend/Backend |
| `docs/CONSOLE_AUDIT/` | Полная инвентаризация Console (ролевая карта + страницы + код/интеграции) | Frontend/Backend/Architect |
| `docs/CONSOLE_AUDIT/pages/insights.md` | Audit page: Insights/Analytics | Frontend/Architect |
| `docs/CONSOLE_AUDIT/pages/marketing.md` | Audit page: Marketing lifecycle + audience/preflight | Frontend/Architect |
| `docs/CONSOLE_AUDIT/UX_BACKLOG.md` | UX backlog (bugs/UX debt) по реализованной Console | Frontend/Backend/Architect |
| `docs/runbooks/CHAOS_SIM.md` | Chaos-sim runbook (human-like диалоги, evaluator, артефакты) | QA/OPS/Brain |
| `docs/runbooks/DIALOG_REPORT.md` | Dialog-report runbook (one-command анализ диалогов) | QA/OPS/Brain |
| `docs/runbooks/BOOKING_CONFIRM_VERIFY.md` | Booking confirm verification runbook | QA/OPS/Brain |
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
| `SPECS/CONTROL_PLANE.md` | Канон: Console как Control Plane (роли, IA, онбординг, capabilities) | Архитектор/Frontend |
| `SPECS/INBOX_HUMAN_LOCK.md` | ТЗ: manual messaging + human lock в «Заявках» | Архитектор/Backend/Frontend |
| `docs/CONSULTANT_CODEMAP.md` | Код‑карта консультанта (decision pipeline, блоки, влияние на поведение) | Backend/Architect |
| `docs/REPORTS/` | Отчёты по прогонам/изменениям | Brain/Architect |
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
| `docs/REPORTS/REPORT_TEMPLATE_ZERO_CONTEXT.md` | Шаблон отчёта для zero-context block delivery | Brain/Architect/Hands |
| `docs/TASK_PACKAGES/` | Task Packages (scope/DoD/checks/evidence) | Brain/Architect |
| `docs/TASK_PACKAGES/TP_TEMPLATE_ZERO_CONTEXT.md` | Шаблон Task Package для zero-context block delivery | Brain/Architect/Hands |
| `docs/TASK_PACKAGES/TP-2026-01-23-chaos-consult-quality-v1.md` | Task Package: chaos-sim + consult quality (multi-intent, safe advice) | Brain/Architect |

**Активные Task Packages:**
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
| `ops` | CI + deploy | `.github/workflows/*`, `TECH.md`, `/home/zhan/truffles-main/scripts/restart_release.sh`, infra compose (не в этом репо) |

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
ops/*.sh              # Кроме monitor.sh — одноразовое
```

**Сохранить из ops/:**
- `monitor.sh`
- `health_check.py`
- `sync_client.py`
- `manual_sync_demo.py`
- `migrations/`
- `templates/`
- `LESSONS_LEARNED.md`
- `README.md`

---

*Создано: 2025-12-10*
