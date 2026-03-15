# Console Guide (Logic + Dev)

**Scope:** Console UI, Console API, auth, tenancy, and how console flows map to core system processes.  
**Out of scope:** Core decision pipeline (see `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`).

---

## 1) Components and Data Flow

**Console UI (Next.js)**  
`console-web/` renders pages and calls the API through a server proxy.

**Auth (Keycloak + NextAuth)**  
Keycloak issues JWT; NextAuth stores session; API validates JWT signature and maps `sub` to agent.

**Console API (FastAPI)**  
`/console/v1/*` endpoints read/write **core DB** tables with tenant scoping
(DB: `chatbot` via `DATABASE_URL` in `truffles-api`).

**Proxy Route**  
`console-web/src/app/api/proxy/[...path]/route.ts` forwards requests to `NEXT_PUBLIC_API_URL` with Bearer token.

**Flow (happy path):**
1. User logs in at `auth.truffles.kz` (Keycloak).
2. NextAuth stores `accessToken` in session.
3. UI calls `/api/proxy/*`.
4. Proxy calls `https://api.truffles.kz/console/v1/*`.
5. Console API validates JWT and loads `ConsoleAuthContext`.
6. Handovers/Bookings/Settings rendered per tenant.

---

## 2) Tenancy and RBAC (Critical)

**Key:** один OIDC login может соответствовать нескольким `client_id`.  
Console uses `agent_identities` to map OIDC `sub` → `agents` → `client_id`.

**Company selection (если компаний несколько):**
- `/console/v1/me` возвращает `companies[]` и `company_selection_required`.

**Client selection (если клиентов несколько):**
- `/console/v1/me` возвращает `clients[]` и `selection_required`.
- API требует заголовок `X-Client-Id`, если клиентов > 1.
- UI хранит выбор в `localStorage` (`console:client_id`) и очищает на logout.

**Branch selection (если филиалов несколько или роль branch‑scoped):**
- `/console/v1/me` возвращает `branches[]` и `branch_selection_required`.
- API требует заголовок `X-Branch-Id`, если филиалов > 1 и доступ ограничен филиалами.
- UI хранит выбор в `localStorage` (`console:branch_id`) и очищает на logout.
**Access scope is enforced here:**
`truffles-api/app/services/console_auth.py` → `get_console_context()`

**Current implementation (code‑backed):**
- Context Bar рендерится в `console-web/src/components/ConsoleShell.tsx` и показывает Company/Client/Branch
  (company name при наличии, иначе краткий id).
- Gate основан на `/console/v1/me` (`company_selection_required`/`selection_required`/`branch_selection_required`);
  выбор хранится в `console:company_id` / `console:client_id` / `console:branch_id` и триггерит refetch.
- Если `branch_selection_required=false`, UI позволяет “Все филиалы” (пустой `branch_id`) в селекте.
- Заголовки `X-Company-Id` / `X-Client-Id` / `X-Branch-Id` прокидываются в API через proxy.
- `/console/v1/me` формируется в `truffles-api/app/routers/console.py`, контекст — в `console_auth.py`.

Rules:
- `sub` must exist in `agent_identities` (channel=`oidc`).
- Agent must be `is_active`.
- All queries filter by `context.client.id`.
- If multiple companies → `X-Company-Id` is mandatory.
- If multiple clients → `X-Client-Id` is mandatory (внутри выбранной компании).
- Non‑admin/owner users are restricted to their branch.
- Provisioning: role=manager requires `branch_id` (branch‑scoped access only).
- Если один `sub` связан с несколькими клиентами → API вернёт
  `CLIENT_SELECTION_REQUIRED` (нужен `X-Client-Id`) либо надо убрать дубликаты.

**Tenant UX contract (short):**
- Контекст (Company / Client / Branch) всегда виден в UI.
- Selector показывается только если есть выбор (2+).
- Ошибки должны быть объяснимы: “Выберите компанию/клиента/филиал”.
- Fail‑closed: без валидного контекста запросы не выполняются.

**Phase 1 UI contract (Control Plane):**
- Верхний Context Bar показывает Company/Client/Branch.
- При `company_selection_required` / `selection_required` / `branch_selection_required` UI блокирует контент и требует выбор.
- Выбор хранится в localStorage (`console:company_id`, `console:client_id`, `console:branch_id`) и передаётся в
  `X-Company-Id` / `X-Client-Id` / `X-Branch-Id`.
- Навигация в сайдбаре режется по роли (owner/admin/manager/support).

**Phase 2 UI contract (Provisioning + Capabilities):**
- UI location: `Settings → Provisioning Wizard` (owner/admin write; support read‑only, остальные без доступа).
- Wizard режимы разделены явно:
  - `Автопроцесс (Recommended)` для single-operator потока.
  - `Ручной по шагам` для детальной донастройки и диагностики.
- Single-operator mode: `Settings → Provisioning Wizard → Single-Operator Autopilot`.
- Required input for autopilot:
  - `phone` (maps to `branches.phone`)
  - `instance_id` (maps to `branches.instance_id`)
  - `client_data_text` or `client_data_json` (source for intake normalization)
  - `purchased_services` (at least one)
  - `company_id` or `company_name`
  - `client_id` or `client_slug`
  - `branch_name` (required when creating a new branch; optional when `branch_id` is provided)
- Optional input for autopilot:
  - `branch_slug`, `timezone`, `domain_slug`, `payment_status` (editable by `platform_admin`)
- Webhook secret is generated automatically from `instance_id`.
- Autopilot API: `POST /console/v1/admin/onboarding/autopilot`.
- Webhook secret API: `GET /console/v1/admin/webhook-secret?branch_id=...`.
- Autopilot output: created/linked `company|client|branch`, saved `capabilities + onboarding_contract`,
  intake draft payload, `missing_fields`, `missing_questions`, `go_no_go_missing`.
- Field links/constraints:
  - `1 phone = 1 branch` within client scope (unique branch phone)
  - `1 instance_id = 1 branch` within client scope (unique branch instance)
  - `webhook_secret` is persisted in `branches.webhook_secret` and derived from `instance_id`
- Fool-proof guards currently enforced:
  - UI blocks autopilot run while required inputs are missing.
  - API rejects invalid activation (`instance_id` required for active branch).
  - API onboarding state machine blocks out-of-order step transition (`ONBOARDING_STEP_REQUIRED`).
  - Destructive branch changes require confirmation (`confirmation_id` flow).
- Provisioning flow: Create Branch (Draft) → Integrations (`instance_id`) → Team → Telegram (`telegram_chat_id`)
  → Knowledge (`knowledge_tag` / branch‑pack) → Booking (`working_hours` / `booking_settings` / specialists) → Go/No‑Go.
- Manual Integrations gate: для WhatsApp обязательны оба поля `instance_id` и `phone`; иначе шаг не считается завершенным.
- Go/No‑Go gate: проверяем только поля, нужные для включённых capabilities; без `instance_id` ветка остаётся draft.
- Server‑side onboarding: `/console/v1/onboarding/status` и `/console/v1/onboarding/advance`, порядок шагов enforced API.
- Ошибка порядка: `ONBOARDING_STEP_REQUIRED` (409) с `required_step/current_step/missing`.
- Capabilities UI: tri‑state редактор (inherit/enable/disable), effective‑view (client + branch overrides),
  сохранение в `/console/v1/admin/capabilities` с `schema_version` и audit.
- API provisioning: `POST /console/v1/admin/companies|clients|branches|agents`,
  `PATCH /console/v1/admin/branches/{branch_id}`.
- Destructive change guard: branch deactivation / instance_id removal требуют подтверждения
  (`POST /console/v1/confirmations` с action=`branch_deactivate` → `confirmation_id`).
- API capabilities: `GET/PATCH /console/v1/admin/capabilities` (client через `X-Client-Id`, branch через `branch_id`).
- Schema: `contracts/capabilities/capabilities.v1.jsonschema`.
- Fail‑closed: без явного tenant‑контекста действия недоступны.

**Phase 2 delivery notes (implemented, 2026-02-06):**
- Added single-operator autopilot endpoint: `POST /console/v1/admin/onboarding/autopilot`.
- Added onboarding contract API (`GET/PATCH /console/v1/admin/onboarding-contract`) with purchased-services payload and payment status guard (`platform_admin` only).
- Added reference pack API (`GET /console/v1/admin/reference-packs`, `PUT /console/v1/admin/reference-packs/{domain_slug}`) for niche gate.
- Added deterministic webhook secret flow: `GET /console/v1/admin/webhook-secret?branch_id=...`, secret stored in `branches.webhook_secret` and derived from `instance_id`.
- Added explicit wizard mode split in UI (`Автопроцесс` vs `Ручной по шагам`) with field-contract help blocks.
- Added WhatsApp integration guard: both `phone` and `instance_id` are required in manual Integrations step and in onboarding state checks.
- Added Go/No-Go mismatch diagnostics (`capability_mismatch:*`) from onboarding contract vs effective capabilities.
- Added build diagnostics in Settings header (`NEXT_PUBLIC_BUILD_SHA`, `NEXT_PUBLIC_BUILD_TIME`) to detect stale deploys quickly.

**Why this was done (for future improvements):**
- To remove onboarding ambiguity for a single platform operator and make required inputs explicit before API calls.
- To enforce fail-closed launch policy: incomplete or contract-mismatched setups stay blocked at Go/No-Go.
- To keep multi-branch setups deterministic (`phone` + `instance_id` uniqueness and secret isolation per branch).
- To make post-release debugging measurable (build stamp shown in UI).

**Regression checks to keep in CI:**
- `truffles-api/tests/test_console_onboarding_state.py`
- `truffles-api/tests/test_console_onboarding_contract_api.py`
- `truffles-api/tests/test_onboarding_contract_service.py`
- `truffles-api/tests/test_onboarding_intake_service.py`

**Phase 3 UI contract (Knowledge Studio):**
- UI location: `Knowledge` (owner/admin write; manager read‑only).
- Flow: Draft → Validate → Preview Diff → Publish → History → Rollback.
- Publish gate: ошибки блокируют publish; warnings требуют явного подтверждения.
- Fail‑closed: без tenant‑контекста действия недоступны.

**Company → Client → Branch selection (UI + API, implemented)**
- `/console/v1/me` возвращает `companies[]`, `company_selection_required`, `selected_company_id`;
  у client доступен `company_name`.
- UI хранит `console:company_id` и фильтрует `clients[]` по выбранной компании;
  селект Company в `ConsoleShell` и gate — первый шаг перед client/branch.
- Заголовок `X-Company-Id` прокидывается в API через `console-web/src/lib/api-client.ts`
  и `/api/proxy/*`.
- E2E учитывает `company-select`/`context-company-select` и `E2E_COMPANY_ID`.

**Common symptom:** “Only 1–2 cases shown / no slots.”  
Usually means the admin is mapped to the wrong `client_id` or the wrong client was selected.

**Tables used:**
- `agent_identities` (OIDC identity mapping)
- `agents` (role, client, optional branch)
- `agent_memberships` (org‑scope RBAC: company/client/branch)
- `clients`, `branches` (tenant scope)
- `handovers`, `conversations`, `users` (cases)
- `specialists`, `bookings` (calendar)
- `audit_events` (audit tab)

### 2.1 Enterprise Fleet management surface (current vs missing)

**Already in Console (code-backed):**
- Tenant registry CRUD: `companies|clients|branches|agents` (`/console/v1/admin/*`).
- Lifecycle read filters for tenants: `lifecycle=active|archived|all` in clients/branches list.
- Client lifecycle actions: `POST /console/v1/admin/clients/{client_id}/archive|restore` with reason/prechecks/audit.
- Integrations registry: `GET /console/v1/admin/integrations` with drift diagnostics.
- Onboarding control: status/advance, autopilot, onboarding contract, capabilities, reference packs.

**Still missing for fleet-scale operations:**
- Membership admin completeness: update/re-scope/disable/enable memberships and identity rebind as first-class UI/API.
- Runbook-to-Console jobs coverage for `sync_client` and branch RAG backfill (today they remain script-first).
- Full migration off legacy `/admin/*` consumers (CI/runbooks still depend on compatibility endpoints).
- Commercial lifecycle model beyond `billing_info` + onboarding `payment_status` (no invoice/subscription surface).

**Execution source of truth:**
- `docs/REPORTS/2026-02-08-enterprise-fleet-program.md` (PR-1..PR-5 plan, risks, owner manual checks).

---

## 3) Console Pages → API Endpoints

**Cases (Заявки)**
- UI: `console-web/src/components/InboxView.tsx` (3‑pane: list → dialog → details)
- List: `console-web/src/components/CaseList.tsx` (compact)
- Conversation: `console-web/src/components/CaseConversation.tsx` + `console-web/src/components/ChatInterface.tsx`
- Details cards: `console-web/src/components/CaseDetailsPanel.tsx` (Context/Explain/Trace/Telegram)
- Quick Replies: `console-web/src/components/InboxMacros.tsx`
- API: `GET /console/v1/cases`
- Data: `handovers` + `conversations` + `users`
- Paging: cursor зависит от `sort_by` (по умолчанию `last_activity`).
- Filters: `status` (`open` = `pending` + `active`), `branch_id`, `assigned_to_me`, `q`, `phone`,
  `has_delivery_error`, `has_pending_outbox`, `sort_by`.
- UI default: `status=open` (открытые заявки); “Все статусы” показывает закрытые.
- Health: `last_inbound_at`, `last_outbound_at`, `last_activity_at`, `last_message_preview`, `needs_reply`, `has_delivery_error`, `has_pending_outbox`.
- RBAC: owner/admin/manager/support read; owner/admin/manager write (take/resolve/send).

**Case view**
- UI: `console-web/src/app/cases/[id]/page.tsx` (deep link into Inbox selection)
- API: `GET /console/v1/cases/{id}`, `POST /take`, `POST /resolve`
- Case Health: последние inbound/outbound + delivery flags.

**Calendar (Записи)**
- UI: `console-web/src/app/calendar/page.tsx`
- API: `/calendar/specialists`, `/calendar/slots`, `/calendar/bookings`
- Data: `specialists`, `bookings`
- RBAC: owner/admin/manager read/write.

**Business (Owner/Admin control)**
- UI: `console-web/src/app/business/page.tsx`, `console-web/src/app/business/data-trust/page.tsx`,
  `console-web/src/app/business/team-performance/page.tsx`,
  `console-web/src/app/business/consultant-verification/page.tsx`
- API: `GET /console/v1/business/summary`, `GET /console/v1/business/incidents`,
  `GET /console/v1/business/data-trust`, `GET /console/v1/business/team-performance`,
  `GET /console/v1/business/consultant-verification/overview`,
  `GET /console/v1/business/consultant-verification/sessions`,
  `POST /console/v1/business/consultant-verification/sessions`,
  `GET /console/v1/business/consultant-verification/sessions/{session_id}`,
  `POST /console/v1/business/consultant-verification/sessions/{session_id}/messages`,
  `GET /console/v1/business/consultant-verification/findings`,
  `POST /console/v1/business/consultant-verification/findings`,
  `PATCH /console/v1/business/consultant-verification/findings/{finding_id}`,
  `GET /console/v1/business/consultant-verification/readiness`,
  `POST /console/v1/business/consultant-verification/compare`
- RBAC: `platform_admin`, `owner`, `admin`; the same roles can create sessions and send simulation messages inside the selected tenant scope.
- Consultant verification Wave1/Wave2/Wave3 contract:
  - Route is business-facing, not a dev playground.
  - First screen still shows readiness/gaps/next-wave promise as the default owner entrypoint.
  - Interactive session/findings/compare endpoints fail closed behind the per-client rollout flag; when rollout is disabled the page remains on the overview/readiness surface.
  - If Console branch context is missing, the page now renders an inline branch gate; owner/admin can choose and apply the branch in place instead of being sent to another page.
  - The top scope card shows the selected client/branch plus current knowledge freshness and sync state so the owner can see exactly which branch is being tested.
  - Wave2 adds safe simulation sessions on the real consultant runtime with rollback-only execution, persisted owner/admin transcripts, and explicit preview flags (`would_handoff`, `would_book`, `gap_detected`).
  - Wave3 adds the owner-readable workspace: `как клиент` / `найти слабые места` mode selection, recent sessions, transcript bubbles, verdict chips, source refs, preview-only impact badges, and an optional advanced-details disclosure.
  - Wave4 adds a data-driven scenario catalog sourced from onboarding blueprints, capabilities, and reference packs; session summaries with honest category counts (`answered / clarification / handoff / gap`); and replay actions that always start a fresh simulation session instead of mutating prior evidence.
  - Wave5 adds owner-detected findings: weak answers can be flagged from the explainer panel, clustered into failure families, linked to `knowledge_backlog` / `learning_candidates`, and tracked via statuses (`new / in_review / needs_data / fixed / retested`).
  - Wave6 adds `live vs draft` compare and publish readiness: the same prompt or finding can be rerun against published knowledge and the latest saved draft; the result records a compare audit event, surfaces regressions in owner language, supports finding retest, and becomes a required gate before `Knowledge -> Publish`.
  - Readiness is sync-aware: if the latest published knowledge is still `pending` or `failed`, or the branch is in `knowledge_safe_mode`, the page shows `needs_attention` and keeps the interactive workspace hidden until sync is actually ready.
  - Closeout status on this branch: local deterministic proof, owner/admin compare lane, and screenshot audit are green; one-client canary and post-merge monitoring remain release-only steps after merge/deploy.
  - Simulation turns must never leak real outbound, booking, or handoff side effects into production flows.

**Knowledge (Знания)**
- UI: `console-web/src/app/knowledge/page.tsx`
- API: `GET /console/v1/knowledge/current`, `POST /console/v1/knowledge/validate`,
  `POST /console/v1/knowledge/publish`, `GET /console/v1/knowledge/history`,
  `POST /console/v1/knowledge/rollback`, `POST /console/v1/knowledge/versions/{version_id}/retry-sync`
- RBAC: owner/admin write; manager read-only; support no access.
- Требует branch selection (`X-Branch-Id`).
- Rollback требует подтверждения: `POST /console/v1/confirmations` (action=`knowledge_rollback`) → `confirmation_id`.
- `GET /console/v1/knowledge/current` now returns both knowledge provenance (`published`, saved draft, edit base) and branch sync health (`sync_status`, `sync_error`, `knowledge_safe_mode`).
- Owner sync-state must be derived from `GET /console/v1/knowledge/current`; `console-me` remains scope/context only and must not be treated as the source of truth for sync-safe-mode rendering after publish/retry/rollback.
- `Publish` is now an async owner contract:
  - phase 1: create/publish the knowledge version,
  - phase 2: enqueue branch-local sync on the durable outbox worker (`knowledge.sync`), outside the owner request path.
- A successful publish response now returns `sync_status=pending` and `partial_success=false`; owner copy stays bounded (`Синхронизация выполняется`) instead of surfacing raw timeout text as the primary message.
- `retry-sync` requeues branch-local sync for the current published version; it does not create a new published knowledge version.
- Cross-branch backfill is no longer part of the owner publish/retry click path.
- After `publish`, `retry-sync`, or `rollback`, the frontend must refetch dependent server-state (`console-me`, `knowledge/current`, `knowledge/history`, consultant-verification readiness) so owner UI cannot show stale `safe_mode/timed out` together with fresh `pending`.
- History, current state, rollback, and consultant-verification readiness all treat `sync_status=pending|failed` as blocking for owner verification until sync is actually `ready`.

**Team (Команда)**
- UI: `console-web/src/app/team/page.tsx`
- API: `GET /console/v1/agents` (owner/admin), `GET /calendar/specialists`
- RBAC: owner/admin only (Team UI).
- Data: `agents`, `agent_identities`, `specialists`

**Settings**
- UI: `console-web/src/app/settings/page.tsx`
- API: `GET/PATCH /console/v1/settings`
- RBAC: owner/admin only.
- Build info: Settings header shows `NEXT_PUBLIC_BUILD_SHA` and `NEXT_PUBLIC_BUILD_TIME` for deploy diagnosis.

**Audit**
- UI: `console-web/src/app/audit/page.tsx`
- API: `GET /console/v1/audit`
- RBAC: owner/admin/support (read-only).

**Ops**
- UI: `console-web/src/components/OpsPage.tsx`
- API: `GET /console/v1/health`, `/console/v1/metrics/daily`, `/console/v1/telegram/health`,
  `GET /console/v1/ops/outbox`, `POST /console/v1/ops/outbox/retry`
- RBAC: owner/admin/support read; owner/admin write (retry/verify/test).

**Insights KPI (truth-first)**
- Статусы: `FACT` (полные данные), `EST` (оценка), `NEED` (неполнота данных).
- Закрыты без человека: диалоги с bot‑ответом и без handover за 24ч; “закрыт” = нет нового inbound 24ч после последнего user‑сообщения. `NEED` если окно 24ч не закрыто.
- Экономия времени менеджера: `total_bot_messages * медиана ручного ответа (сек)` — **EST**. Медиана считается по user→первый manager в диалоге.
- Конверсия в запись: `appointments` с `conversation_id` и user‑сообщением ≤24ч до booking / кол‑во inbound‑диалогов. `NEED` если есть bookings без `conversation_id`.
- Время до первого ответа (p50/p90): время от первого user до первого bot/manager; показываем `missing_total` без ответа.
- После‑часов покрытие: user‑сообщения вне `branch.working_hours` (TZ) и bot‑ответ ≤10 мин. `NEED` если нет `timezone`/`working_hours`.
- Качество эскалаций: % handover, где есть слоты service + datetime + контакт (name/phone) в `handovers.meta`. `NEED` при отсутствии snapshot.
- Потери/риски: `outbox_status_events` FAILED + `alert_events` no_response в день; “спасено” = FAILED, но позже SENT (**EST**).
- Топ‑темы и боли: top‑N intents + info_sections из `decision_meta` (детерминированно). `NEED` если отсутствует intent; LLM‑кластеризация помечается как **EST**.
- Тренды KPI: 7‑дневные sparklines на основе `metrics_analytics_daily` (без тяжёлых запросов).

---

## 3.1 Telegram integration (Console)

**Purpose:** Telegram is paging/fallback; Console remains the source of truth for workflow, RBAC, and audit.

**Backend (Console API + core mapping):**
- Health: `GET /console/v1/telegram/health` (Console API).
- Verify: `POST /console/v1/telegram/verify` (owner/admin).
- Test: `POST /console/v1/telegram/test` (owner/admin).
- Agent linking: `GET /console/v1/agents` + `POST /console/v1/agents/{id}/telegram/link` (self‑link allowed for any role; owner/admin can link others).
- Case trail: `GET /console/v1/cases/{id}` returns `telegram_trail`.
- Case actions: `POST /console/v1/cases/{id}/take|resolve|return` return `sync` status.
- Branch routing: `GET /console/v1/settings` returns `branches[].telegram_chat_id` + `branches[].instance_id`.

**UI locations:**
- Settings → Telegram connector: client-scope Verify/Test.
- Settings → Branches: per-branch Verify/Test (requires `telegram_chat_id`).
- Ops → Telegram card: client-scope Verify/Test (owner/admin).

**Data sources (core DB):**
- `branches.telegram_chat_id`, `branches.instance_id` (routing + UI display).
- `client_settings.telegram_bot_token`, `client_settings.telegram_chat_id` (bot config + legacy fallback).
- `conversations.telegram_topic_id` (topic per user).
- `handovers.telegram_message_id`, `handovers.notified_at` (delivery evidence).
- `agent_identities` (channel=telegram) + `agent_link_tokens` (linking tokens).

**Trail mapping (Console API):**
- `message_id` → `handovers.telegram_message_id`
- `topic_id` → `conversations.telegram_topic_id`
- `chat_id` → `branches.telegram_chat_id` (fallback to `client_settings.telegram_chat_id`)
- `delivery_status` → `sent` when message_id present, otherwise `pending`
- `delivered_at` → `handovers.notified_at` (if present)
- `telegram_link` → `https://t.me/c/<internal_id>/<message_id>` when `chat_id` is `-100...`
  - если есть `topic_id` → добавляем `?thread=<topic_id>` для открытия нужного топика.
  - `internal_id` = `chat_id` without `-100` prefix; if not numeric, link is omitted.

**Health mapping (Console API):**
- `webhook_alive` via Telegram `getWebhookInfo` for `telegram_bot_token`.
- `pending_messages` = `pending_update_count` from Telegram webhook info.
- `last_error_at`/`last_error_message` from Telegram webhook info.
- `error_rate_24h` = 0.0 (no persisted telemetry yet; recorded as gap in STATE).
- `status` = `degraded` только если ошибка свежая (последние 24ч) или есть pending messages.

**Onboarding checklist (Telegram + Console, P0)**

**Что нужно от бизнес‑владельца (входные данные):**
- Список филиалов + телефоны + `instanceId` из ChatFlow.
- Telegram‑группа на каждый филиал (supergroup), **topics включены**.
- Бот добавлен админом в каждую группу.
- Список менеджеров и их роли (owner/admin/manager), кто работает через Telegram.

**Шаги онбординга (один раз на клиента):**
1) Создать `client`, `branches`, `agents`.
2) Заполнить `branches.instance_id` (ChatFlow) и `branches.telegram_chat_id` (TG group id `-100...`).
3) Заполнить `client_settings.telegram_bot_token`.
4) Настроить ChatFlow webhook: `/webhook/{client_slug}?webhook_secret=...`.
5) Настроить Telegram webhook: `https://api.truffles.kz/telegram-webhook`.
6) В Console → Team → Users: подключить Telegram для каждого менеджера (token → `/start <token>`).
7) В Console → Settings/Ops: Verify/Test (client + branch scope).

**Ожидаемый результат (после онбординга):**
- Эскалация создаёт topic и карточку с кнопками.
- `pending/manager_active` форвардит сообщения клиента в topic (текст/медиа по policy).
- Take/Resolve (Console или Telegram) обновляет Telegram‑карточку и шлёт клиенту системное уведомление.
- Аудит содержит `case_taken/resolved` + `manager_connected/disconnected`.
- В карточке кейса есть две ссылки: `tg://` (Desktop) и `https://t.me` (Web); если Desktop не открывает topic, используйте Web‑ссылку.

**Контракт требований (минимум для работы):**
- `branches.telegram_chat_id` заполнен на каждый филиал.
- `client_settings.telegram_bot_token` задан и webhook установлен.
- Агент связал Telegram через `/start <token>`.
- `POST /console/v1/cases/{id}/take|resolve|return` идёт через `state_service`.

**Role runbooks (short)**

**Global admin (platform):**
- Доступ: owner/admin + membership на уровне компании (см. `agent_memberships`), без отдельной platform‑role.
- Создать Company/Client/Branch/Agent в Provisioning Wizard или через `/console/v1/admin/*`.
- Проверить обязательные поля: `instance_id`, `telegram_chat_id`, `knowledge_tag`, `working_hours`, `booking_settings`.
- Связать OIDC `sub` → `agent_identities`; для manager обязателен `branch_id`.
- Go/No‑Go: `/console/v1/knowledge/validate|publish`, `/console/v1/telegram/verify`, /cases take/resolve.

**Owner (client):**
- Управляет знаниями, командой, интеграциями, включением capabilities.
- Workflow: Settings → Provisioning Wizard, Knowledge → Validate/Publish, Team → Users (link Telegram).
- Проверки: Telegram Verify/Test (client/branch), branch selection gate, Go/No‑Go.

**Admin (client):**
- Почти как owner, но без коммерческих/плановых настроек.
- Поддерживает branches/agents/knowledge, следит за Telegram linking и операционными настройками.

**Manager (branch):**
- Branch‑scoped, нужен `branch_id`; доступ: Cases + Calendar, Knowledge read‑only; Team/Settings недоступны.
- Обязательно выбрать филиал (или получить `branch_selection_required`).
- Рабочий цикл: взять заявку → ответить клиенту → resolve/return.

**Where to change code:**
- API endpoint + mapping: `truffles-api/app/routers/console.py`
- Telegram API helper: `truffles-api/app/services/telegram_service.py`
- Linking helpers: `truffles-api/app/services/agent_link_service.py`
- UI Ops card: `console-web/src/components/OpsPage.tsx`
- UI Case trail: `console-web/src/components/CaseView.tsx`
- UI Branch list: `console-web/src/app/settings/page.tsx`
- Console schemas: `truffles-api/app/schemas/console.py`
- Contracts: `contracts/console_api/openapi.v1.yaml`

**Diagnostics (quick):**
- Webhook status: `curl -s -H "Authorization: Bearer $TOKEN" https://api.truffles.kz/console/v1/telegram/health`
- Telegram webhook raw: `curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"`
- Agent linking (token):
  ```bash
  curl -s -X POST -H "Authorization: Bearer $TOKEN" \
    https://api.truffles.kz/console/v1/agents/<agent_id>/telegram/link
  ```
- Link usage: отправить в Telegram боту `/start <token>` (создаст `agent_identity`).
- Verify (client scope):
  ```bash
  curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \\
    https://api.truffles.kz/console/v1/telegram/verify \\
    -d '{"scope":"client"}'
  ```
- Verify (branch scope):
  ```bash
  curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \\
    https://api.truffles.kz/console/v1/telegram/verify \\
    -d '{"scope":"branch","branch_id":"<UUID>"}'
  ```

**Live-check (post-deploy, Console↔Telegram↔WhatsApp):**
1) Inbox: открой `Console → Заявки`, сортировка `Активные` (last_activity). Отправь тестовое сообщение клиенту —
   нужная заявка должна подняться вверх, а в строке показать канал активности.
2) Case View: в карточке проверь `Case Health` (last in/out, NEW/LIVE/⚠️), `Telegram trail` и ссылки:
   - Web: `https://t.me/c/<id>/<message_id>?thread=<topic_id>`
   - Desktop: `tg://privatepost?channel=<internal_id>&post=<message_id>&thread=<topic_id>`
3) Telegram → Console: отправь сообщение из Telegram топика → оно должно появиться в Console (polling ≤ 5s).
4) Console → Telegram: отправь сообщение из Console → оно должно уйти клиенту и отобразиться в Telegram топике (echo).
4.1) Console → Telegram (media): отправь фото/аудио/документ → медиа должно уйти клиенту и отобразиться в Telegram топике (echo). Видео запрещено.
5) Ops: проверь `Console → Ops` (Telegram health + outbox backlog).
- Test message (custom text):
  ```bash
  curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \\
    https://api.truffles.kz/console/v1/telegram/test \\
    -d '{"scope":"branch","branch_id":"<UUID>","message":"Truffles test message"}'
  ```

---

## 4) Console Auth & Tokens

**OIDC config (API side)**  
`CONSOLE_OIDC_JWKS_URL`, `CONSOLE_OIDC_ISSUER`, `CONSOLE_OIDC_AUDIENCE`.

**Keycloak realm file**  
`ops/keycloak-realm.json` defines clients + initial users.

**Stable `sub`**  
Set `users[].id` in `ops/keycloak-realm.json` to avoid `sub` changes on re‑create.

---

## 5) Adding New Console Features

**Backend**
1. Add schema in `truffles-api/app/schemas/console.py`.
2. Add endpoint in `truffles-api/app/routers/console.py` or a dedicated router.
3. Enforce tenant scope via `get_console_context`.
4. Add idempotency for mutations: `console_idempotency.py`.
5. Update contract: `contracts/console_api/openapi.v1.yaml`.

**Frontend**
1. Add API call via `/api/proxy/*` (server‑side).
2. Use `useAuthenticatedApi` for client calls.
3. Handle `AUTH_REQUIRED` / `ACCESS_DENIED` errors.
4. Keep UI consistent with `globals.css` tokens.

**Tests**
- Contract: `schemathesis --config-file contracts/console_api/schemathesis.toml run contracts/console_api/openapi.v1.yaml --url https://api.truffles.kz/console/v1`
- E2E (if required): `console-e2e` (Playwright)

---

## 6) Console tests (E2E/CI)

**Purpose:** catch auth breakage, navigation regressions, and read-only API wiring.

**Defaults:**
- Smoke tests are read-only. Mutating checks require `E2E_ALLOW_MUTATIONS=1`.
- CI uses `E2E_USE_STORAGE_STATE=1` to log in once per run (faster, less flaky).
- Login flow uses NextAuth sign-in to reach Keycloak (more stable than clicking UI).
- Playwright uses storageState via setup project (one login per run).

**Where to run:** `docs/DEV_SETUP.md` (Console tests section).

**Credentials (do not commit):**
- Prod host: `/home/zhan/secrets/console-e2e.env`.
- Contract/k6: `/home/zhan/secrets/console-contract.env`.
- Template: `console-web/.env.e2e.example` (no secrets).
- CI: GitHub Secrets (`CONSOLE_E2E_USERNAME`, `CONSOLE_E2E_PASSWORD`, `CONSOLE_KEYCLOAK_CLIENT_SECRET`).
- `CONSOLE_API_TOKEN` is short-lived; do not store in repo. If used locally, keep only in
  `/home/zhan/secrets/console-contract.env` and rotate.

**Seed (stable E2E data):**
- Script: `truffles-api/scripts/console_e2e_seed.py` (idempotent, stable UUIDs).
- Requires DB + Keycloak admin, gated by `E2E_SEED_ALLOW=1`.
- If `sub` is known, pass `E2E_SUBJECT` to skip Keycloak admin.

**E2E note (multi-client):**
- E2E user should map to **one** client, or storageState must include `console:client_id`.
- Otherwise tests will see `CLIENT_SELECTION_REQUIRED`.

**CONSOLE_API_TOKEN (short-lived):**
- Получать через Keycloak token endpoint; хранить только в env.
```bash
KEYCLOAK_TOKEN_URL="https://auth.truffles.kz/realms/truffles/protocol/openid-connect/token"
curl -s -X POST "$KEYCLOAK_TOKEN_URL" \
  -d "client_id=console-web" \
  -d "client_secret=$CONSOLE_KEYCLOAK_CLIENT_SECRET" \
  -d "grant_type=password" \
  -d "username=$CONSOLE_KEYCLOAK_USERNAME" \
  -d "password=$CONSOLE_KEYCLOAK_PASSWORD" | jq -r '.access_token'
```
---

## 7) Debug & Troubleshooting

**403 ACCESS_DENIED**
- Check `agent_identities` mapping for `sub`.
- Verify `agents.is_active = true`.

**400 CLIENT_SELECTION_REQUIRED**
- Один `sub` связан с несколькими клиентами/агентами.
- `/console/v1/me` вернул `selection_required=true` → выбрать клиента или передать `X-Client-Id`.
- Очистить `localStorage` ключ `console:client_id`, если выбранный клиент удалён.
- Решение: оставить одну связку `agent_identities` для нужного клиента или использовать `X-Client-Id`.

**400 COMPANY_SELECTION_REQUIRED**
- Доступно несколько компаний.
- `/console/v1/me` вернул `company_selection_required=true` → выбрать компанию или передать `X-Company-Id`.
- Очистить `localStorage` ключ `console:company_id`, если выбранная компания удалена.

**400 BRANCH_SELECTION_REQUIRED**
- Роль branch‑scoped и доступно несколько филиалов.
- `/console/v1/me` вернул `branch_selection_required=true` → выбрать филиал или передать `X-Branch-Id`.
- Очистить `localStorage` ключ `console:branch_id`, если выбранный филиал удалён.

**502 /api/proxy/**
- `NEXT_PUBLIC_API_URL` не задан или API недоступен.
- Проверить `console-web/.env.local` и доступность `https://api.truffles.kz/console/v1`.

**Empty “Cases”**
- Check `handovers` count by `client_id`.
- Verify admin is mapped to correct tenant.

**Empty “Calendar”**
- Check `specialists` and `bookings` for tenant.

**Slow “Cases”**
- Validate DB indexes on `handovers(client_id, created_at)` and `conversations(branch_id)`.

---

## 8) Related Canon Docs

- `SPECS/MULTI_TENANT.md` — tenant boundaries and branch routing.
- `contracts/tenancy/tenant_context.v1.jsonschema` — canonical tenant context contract.
- `TECH.md` — console env + deploy commands.
- `docs/PROCESSES.md` — contract map and core flows.
- `contracts/console_api/*` — API contract source of truth.
