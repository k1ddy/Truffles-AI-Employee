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
| `contracts/` | Канон контрактов (Console API, ошибки) | Архитектор/Frontend |
| `contracts/console_api/schemathesis.toml` | Seed/overrides для Schemathesis contract smoke | Backend/QA |
| `contracts/events/` | Контракты событий (outbox) | Архитектор/Backend |
| `contracts/tenancy/tenant_context.v1.jsonschema` | Канон tenant_context (company/client/branch) | Архитектор/Backend |
| `contracts/capabilities/capabilities.v1.jsonschema` | Канон capabilities (channels/providers/features) | Архитектор/Backend |
| `contracts/consult/consult_playbook.v1.jsonschema` | Канон схемы consult playbooks (domain‑agnostic) | Архитектор/Backend |
| `contracts/consult/consult_controller_output.v1.jsonschema` | Канон контракта consult LLM‑контроллера | Архитектор/Backend |
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
| `.github/workflows/session-gate.yml` | CI gate: session log + doc-only policy | Brain/Architect |
| `SUMMARY.md` | Сводка текущей инвентаризации и GAP | Архитектор |
| `scripts/restart_workers.sh` | Перезапуск контейнеров воркеров (outbox/sentinel) | OPS |
| `scripts/session_start.sh` | Создать worktree/branch и session log (agent suffix обязателен) | Все роли |
| `scripts/session_check.sh` | Проверка сессии перед commit/push | Все роли |
| `scripts/session_end.sh` | Закрытие сессии + index обновление | Все роли |
| `scripts/session_resume.sh` | Возобновить активную сессию после compaction (по умолчанию SESSION_AGENT) | Все роли |
| `scripts/session_audit.sh` | Аудит сессий (статусы/сироты) | Brain/Architect |
| `scripts/session_gate.sh` | Gate для doc-only и session log | Brain/Architect |
| `scripts/install_hooks.sh` | Установка обязательных hooks | Все роли |
| `scripts/restart_knowledge_gateway.sh` | Перезапуск Knowledge Gateway (shadow) | OPS |
| `scripts/restart_provider_gateway.sh` | Перезапуск Provider Gateway (shadow) | OPS |
| `scripts/restart_inbox_service.sh` | Перезапуск Inbox Service (shadow) | OPS |
| `scripts/restart_decision_core.sh` | Перезапуск Decision Core (shadow) | OPS |
| `docker-compose.yml` | **Заглушка:** инфра‑стек в `/home/zhan/infrastructure/docker-compose*.yml` | DevOps |
| `ops/reset.sql` | **Emergency:** закрыть все open handovers + вернуть `bot_active` | Кодер/OPS |
| `ops/keycloak-theme/` | Тема Keycloak (CSS + лого) для брендинга auth | OPS/Frontend |
| `truffles-api/` | Backend API + workers | Backend |
| `truffles-api/app/services/onboarding_state.py` | Server-side onboarding state machine (Console) | Backend |
| `truffles-api/app/services/console_confirmations.py` | Confirmation safeguards for destructive Console actions | Backend |
| `truffles-api/app/models/console_confirmation.py` | DB model for confirmation requests (Console) | Backend |
| `truffles-api/app/knowledge_gateway_app.py` | Отдельный app для Knowledge Gateway | Backend |
| `truffles-api/app/provider_gateway_app.py` | Отдельный app для Provider Gateway | Backend |
| `truffles-api/app/inbox_service_app.py` | Отдельный app для Inbox Service | Backend |
| `truffles-api/app/decision_core_app.py` | Отдельный app для Decision Core | Backend |
| `truffles-api/app/routers/inbox_service.py` | Router для Inbox Service | Backend |
| `truffles-api/app/routers/decision_core.py` | Router для Decision Core | Backend |
| `truffles-api/migrations/015_add_inbox_events.sql` | Migration: inbox_events (durable inbox store) | Backend/OPS |
| `truffles-api/migrations/016_add_console_confirmations.sql` | Migration: console_confirmations (destructive safeguards) | Backend/OPS |
| `truffles-api/scripts/console_e2e_seed.py` | Seed для стабильных console‑e2e данных | Backend/QA |
| `console-web/` | Console UI (Next.js, Dockerfile) | Frontend |
| `console-web/e2e/` | Playwright smoke/login/setup тесты (storageState) | Frontend/QA |
| `console-web/eslint.config.js` | ESLint flat config для console-web | Frontend |
| `console-web/.env.e2e.example` | Шаблон env для console‑e2e | Frontend/QA |
| `console-web/public/brand/` | Бренд‑ассеты консоли (логотипы) | Frontend |
| `docs/CONSOLE_GUIDE.md` | Guide по Console (API, тесты, дебаг) | Frontend/Backend |
| `docs/runbooks/CHAOS_SIM.md` | Chaos-sim runbook (human-like диалоги, evaluator, артефакты) | QA/OPS/Brain |
| `SPECS/CONTROL_PLANE.md` | Канон: Console как Control Plane (роли, IA, онбординг, capabilities) | Архитектор/Frontend |
| `docs/CONSULTANT_CODEMAP.md` | Код‑карта консультанта (decision pipeline, блоки, влияние на поведение) | Backend/Architect |
| `docs/REPORTS/` | Отчёты по прогонам/изменениям | Brain/Architect |
| `docs/REPORTS/2026-01-24-consult-quality.md` | Отчёт: consult quality + chaos‑sim | Brain/Architect |
| `docs/REPORTS/2026-01-25-control-plane-provisioning.png` | Скрин: Provisioning Wizard (Settings) | Brain/Architect |
| `docs/REPORTS/2026-01-26-control-plane-inbox.png` | Скрин: Inbox 3‑pane (Phase 5) | Brain/Architect |
| `docs/REPORTS/2026-01-27-control-plane-review.md` | Отчёт: Control Plane UX/RBAC/safety review | Brain/Architect |
| `docs/TASK_PACKAGES/` | Task Packages (scope/DoD/checks/evidence) | Brain/Architect |
| `docs/TASK_PACKAGES/TP-2026-01-23-chaos-consult-quality-v1.md` | Task Package: chaos-sim + consult quality (multi-intent, safe advice) | Brain/Architect |

**Активные Task Packages:**
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
| `data` | eval + facts | `truffles-api/app/knowledge/demo_salon/EVAL.yaml`, `truffles-api/app/knowledge/demo_salon/SALON_TRUTH.yaml` |
| `docs` | specs + состояния | `SPECS/*`, `STATE.md`, `STRUCTURE.md`, `AGENTS.md` |
| `ops` | CI + deploy | `.github/workflows/*`, `TECH.md`, `/home/zhan/restart_api.sh`, infra compose (не в этом репо) |

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
| `truffles-api/app/services/knowledge_service.py`, `demo_salon_knowledge.py`, `intent_service.py`, `ai_service.py` | Facts/Intent/LLM |
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

**Старые скрипты:** `.archive/ops_old/` — не в git.

---

## Business/ — Бизнес документы

| Папка | Содержание |
|-------|------------|
| `Legal/` | Договоры, NDA |
| `Sales/` | Бриф клиента, скрипты |

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
