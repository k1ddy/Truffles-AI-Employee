# CONTROL PLANE — Консоль как управляющая плоскость

**Статус:** CANON  
**Owner:** Top Architect  
**Обновлено:** 2026-01-24  
**Scope:** Web‑Console как Control Plane, роли/RBAC, IA, онбординг, capabilities, Knowledge Studio, Team/Calendar, Inbox UX, API границы, фазы работ.  
**Out of scope:** реализация, миграции БД, UI‑макеты, доказательства.  
**Links:** `STATE.md`, `docs/IMPERIUM_DECISIONS.yaml`, `SPECS/ESCALATION.md`, `SPECS/MULTI_TENANT.md`, `docs/CONSOLE_GUIDE.md`, `STRATEGY/TECH_ROADMAP.md`, `STRATEGY/REQUIREMENTS.md`.

---

## 1) North Star

**Console = панель управления бизнес‑ассистентом**, а не просто “список заявок”.
- **Web‑first:** Web Console — основной профессиональный интерфейс. Telegram — paging/fallback.
- **Truth‑first:** факты/правила — в каноне и данных; UI только управляет ими.
- **Fail‑closed:** без валидного tenant‑контекста действия невозможны.

---

## 2) Роли и RBAC (минимально‑достаточная модель)

Роль‑модель строится поверх org‑scope memberships и tenant context (см. `SPECS/MULTI_TENANT.md`).

**Платформа (Truffles):**
- **Platform Admin** — управление тенантами и модулями, доступ к Ops по всей системе (runtime роль `platform_admin`, cross‑tenant, selection gate обязателен).
- **Platform Support** — диагностика/помощь, read‑only в provisioning (без create/update).

**Клиент (бизнес):**
- **Owner** — полный доступ (знания, команда, интеграции, заявки, настройки).
- **Admin** — всё, кроме коммерческих/плановых настроек.
- **Manager** — заявки, календарь, ограниченные операционные настройки (branch‑scoped, `branch_id` обязателен).
- **Specialist/Master** — только календарь/слоты (опционально).
- **Viewer/Analyst** — read‑only (опционально).

**Принцип:** UI и навигация режутся по роли, чтобы не было шума.

**Runtime roles (impl):**
- В коде реально используются: `platform_admin`, `owner`, `admin`, `manager`, `support`
  (см. `truffles-api/app/services/console_auth.py`).
- Platform Support — концепт уровня доступа; фактически доступ задаётся
  membership‑scope + роль support.
- Specialist/Viewer пока не реализованы в RBAC.

**RBAC matrix (runtime, enforced in API/UI):**

| Раздел | Read | Write |
|--------|------|-------|
| Inbox (Cases) | platform_admin/owner/admin/manager/support | platform_admin/owner/admin/manager |
| Knowledge | platform_admin/owner/admin/manager | platform_admin/owner/admin |
| Team | platform_admin/owner/admin | platform_admin/owner/admin |
| Calendar | platform_admin/owner/admin/manager | platform_admin/owner/admin/manager |
| Settings | platform_admin/owner/admin | platform_admin/owner/admin |
| Ops | platform_admin/owner/admin/support | platform_admin/owner/admin |
| Audit | platform_admin/owner/admin/support | — |
| Provisioning (`/console/v1/admin/*`) | platform_admin/owner/admin/support (read) | platform_admin/owner/admin |

Примечания:
- Support = read‑only для Ops/Provisioning; write‑операции доступны только platform_admin/owner/admin.
- Team/Settings скрыты для manager/support; read‑only команда не предоставляется.

---

## 3) Tenant‑контекст и UX выбора (обязательный канон)

См. `SPECS/MULTI_TENANT.md`.

- Контекст **Company → Client → Branch** всегда виден.
- Selector показывается только при наличии выбора.
- При `company_selection_required` / `selection_required` / `branch_selection_required` — блокирующее состояние.
- При нескольких компаниях `X-Company-Id` обязателен (fail‑closed).
- Ошибки понятны: “Выберите компанию/клиента/филиал”, “Нет доступа”.

**Implementation note (2026‑01‑27):**
- UI показывает Company как `company_id` (без имени и без выбора), selection gate есть только для client/branch.
- Детальный план Company→Client→Branch selection закреплён в `docs/CONSOLE_GUIDE.md`.

---

## 4) Информационная архитектура (IA)

**Owner/Admin:**
1) Inbox  2) Calendar  3) Knowledge  4) Team  5) Integrations  6) Settings  7) Audit  8) Insights (опционально)

**Manager:** Inbox, Calendar, read‑only Knowledge, Team directory.

**Platform Admin:** Tenants, Inbox (support), Ops, Audit, Integrations registry.

---

## 5) Онбординг и Provisioning (owner/admin с platform‑scope)

**Provisioning flow (Web‑first)** как стандарт:
1) Create Branch (Draft): name, slug, timezone (default ok), остальное optional (`is_active=false` без `instance_id`).
2) Integrations: `instance_id` (WA) → включаем WhatsApp‑channel.
3) Team: владельцы/админы (доступ в Console).
4) Telegram: связка бота → `telegram_chat_id` → включаем Telegram‑capability.
5) Knowledge: `knowledge_tag` / branch‑pack → publish.
6) Booking: `working_hours` / `booking_settings` / specialists → включаем booking‑capability.
7) Go/No‑Go: проверяем только поля, нужные для включённых capabilities.

**Go/No‑Go gate:** обязательные поля проверяются по включённым capabilities; без `instance_id` ветка остаётся draft.

**Server‑side onboarding state machine (branch‑scoped):**
- Шаги: `branch_draft → integrations → team → telegram → knowledge → booking → go_no_go`.
- Проверка порядка выполняется на API (не только UI).
- API:
  - `GET /console/v1/onboarding/status?branch_id=...`
  - `POST /console/v1/onboarding/advance`
- Ошибка порядка: `ONBOARDING_STEP_REQUIRED` (409), с `required_step/current_step`.

**Destructive safeguards (console):**
- Любые разрушительные действия требуют подтверждения (reason + TTL).
- API: `POST /console/v1/confirmations` → `confirmation_id`.
- Примеры: knowledge rollback (`action=knowledge_rollback`), branch deactivate / instance disconnect (`action=branch_deactivate`).

---

## 6) Capabilities (модули клиента)

### 6.1 Решение (профессиональный вариант)

**Отдельная сущность capabilities** с валидируемым JSON‑контрактом.

Предлагаемый каркас:
- Таблица `client_capabilities`:
  - `id`, `client_id`, `branch_id` (nullable), `scope` (client|branch)
  - `payload_json` (JSONB, schema‑validated)
  - `schema_version`, `status` (active|disabled)
  - `created_by`, `created_at`, `updated_at`
- **Effective capabilities** = merge client‑level + branch‑level overrides.
- Контракт: `contracts/capabilities/capabilities.v1.jsonschema`.

**Минимальный payload:**
- `channels`: whatsapp/telegram/instagram
- `providers`: availability_provider, crm_provider, calendar_provider
- `features`: booking_mode, knowledge_upload, analytics, auto_learn

**Почему так:** масштабируется без постоянных миграций, позволяет точечные overrides.

---

## 7) Knowledge Studio (структурные знания + безопасный publish)

### 7.1 Источник истины и генерация pack

**Источник истины — структурный knowledge‑draft в БД.**
Pack‑файл — **генерируемый артефакт** при publish, а не редактируемый вручную.

**Pipeline:** Draft → Validate → Preview Diff → Publish → Sync → Active.

### 7.2 Риск‑митигирующие правила

- **Fail‑closed:** publish запрещён при schema‑ошибках/mandatory‑дырках.
- **Warnings требуют подтверждения** (явный ack).
- **Двухшаговое подтверждение** для деструктивных изменений (удаления/обнуления цен).
- **Audit log** на каждый шаг.
- **Rollback** к любой предыдущей версии (1‑клик), с записью причины.
- **Safe‑mode**: при конфликте или невалидности — ассистент уходит в HANDOFF, не фантазирует.

### 7.3 Версионирование

Рекомендованная модель:
- `knowledge_versions` с полями `status` (draft/published/archived), `payload_json`, `pack_yaml`, `checksum`, `published_at`, `published_by`, `source_version_id`.
- Хранить N последних published версий + полный audit trail.

### 7.4 Интеграция с текущим SOP

- `ops/sync_client.py` расширяется режимом **source=registry** (DB‑pack).
- Qdrant sync запускается только из опубликованной версии.
- Runtime обязан читать **published** версию (DB‑loader + file fallback до миграции).

---

## 8) Team & Calendar

**Team → Users**
- Список пользователей, роли, доступные филиалы, инвайты/disable.
- Telegram linking токены — в “Advanced”.

**Team → Specialists**
- Мастера, услуги (из каталога), рабочие часы, привязка календаря.

**Принцип:** каталог услуг живёт в Knowledge; мастер выбирает услуги из каталога.

---

## 9) Inbox UX standard (операторский режим)

**Цель:** быстрый разбор заявок без шума. Приоритет: **Action → Chat → Context → Diagnostics**.

### 9.1 Layout (responsive)
- **Desktop:** 2‑pane по умолчанию — Queue (list) + Chat; **Details** справа по toggle, чат остаётся основным.
- **Tablet:** 2‑pane — Queue / Chat + Details drawer.
- **Mobile:** single column; **Details** раскрываются из чата по кнопке.

### 9.2 Queue (list)
- **Минимум сигналов:** имя/телефон, превью, последняя активность, SLA, теги “Нужно ответить / На связи / Ошибка”.
- **Дефолт сортировка:** activity; быстрые переключатели “Мои” и “Срочные”.
- **Фильтры:** поиск + статус + assigned; **advanced** скрыт по умолчанию.
- **Branch filter** только при `branch = All` (если глобальный контекст уже выбран — не дублировать).

### 9.3 Chat + actions
- **Action bar:** “Взять”, “Закрыть”, “Передать/Эскалировать” (role‑based).
- **Quick replies:** рядом с композером (chips + раскрываемый список), макросы из БД (персональные/командные).
- **Управление макросами:** настройка из Inbox (RBAC), хранение per‑client/branch/agent.
- **Контекст‑strip:** короткая “Суть запроса” + время последнего inbound над чатом.

### 9.4 Details (Context + Case + Consultant)
- **Default tabs:** Контекст / Заявка / Консультант.
- **Контекст:** контакт клиента, краткая сводка, причина обращения.
- **Заявка:** статус, SLA, канал, последнее inbound/outbound, флаги доставки.
- **Консультант:** assigned manager (имя/роль), статус работы, first_response/resolve (если доступно).

### 9.5 Diagnostics (gated)
- **Отдельный таб:** Explain + Trace + Telegram trail.
- **По умолчанию скрыт** для операторов; доступен support/admin.

### 9.6 Cross‑tab clarity
- Inbox = обработка заявок и ответы. Нет редактирования Knowledge/Team/Settings.
- UI‑тексты операторов — RU; тех. термины только в Diagnostics.

---

## 10) Ops / Status

- **Owner/Admin:** короткий статус OK/Degraded + “что делать”.
- **Platform Admin:** полный Ops (health/metrics/outbox/telegram).

---

## 11) API границы (минимальный набор)

**Provisioning (Platform Admin):**
- `POST /console/v1/admin/companies|clients|branches|agents`
- `PATCH /console/v1/admin/capabilities`

**Knowledge:**
- `GET /console/v1/knowledge/current`
- `POST /console/v1/knowledge/validate`
- `POST /console/v1/knowledge/publish`
- `GET /console/v1/knowledge/history`
- `POST /console/v1/knowledge/rollback`

**Team:**
- `GET/POST/PATCH /console/v1/team/users`
- `GET/POST/PATCH /console/v1/team/specialists`

**Integrations:**
- `GET/PATCH /console/v1/integrations/*`

---

## 12) План работ (фазы)

**Phase 1 — Layout + контекст + роли**
- Sidebar + top context bar
- Role‑based navigation
- Fail‑closed selection_required

**Phase 2 — Provisioning + capabilities**
- Wizard + tenant registry
- Capabilities model + UI
- Go/No‑Go gate

**Phase 3 — Knowledge Studio**
- Template/download → validate → preview → publish
- Versioning + rollback
- Safe‑mode + audit

**Phase 4 — Team + Calendar**
- Users + Specialists
- Services ↔ specialists ↔ slots

**Phase 5 — Inbox UX**
- 3‑pane view
- Explain/Trace cards
- Macros

---

## 13) No‑go (жёсткие ограничения)

- Никаких “догадок” о tenant‑контексте.
- Никакого write‑доступа к runtime контейнеру (без `docker cp`, без `-v`).

---

## 14) Production Go/No‑Go (Live Customers)

**DEC‑014:** живые заказчики допускаются только после выполнения чеклиста и фиксации evidence в `STATE.md`.

**Минимум:**
1) **CI + deploy:** main зелёный, деплой подтверждён; в Settings виден build‑info (SHA/time).
2) **Provisioning Wizard:** виден в `Settings`, draft‑branch без `instance_id` не активируется; Go/No‑Go gate
   проверяет только поля включённых capabilities.
3) **Knowledge safety:** Draft→Validate→Publish→Rollback; publish запрещён при ошибках; safe‑mode при невалидности.
4) **RBAC/tenancy:** selection_required/branch_selection_required работает; manager только с `branch_id`;
   support read‑only в provisioning.
5) **Ops evidence:** decision_meta/trace на каждый inbound; outbox idempotency/auto‑heal; live‑check записан
   (conversation_id, decision_trace, decision_meta, outbox status).
6) **Rollback:** описан и проверяем (UI/knowledge/deploy).
- Никаких хардкодов знаний — только через структурные данные + валидацию.
- Никаких изменений в core‑поведении без Task Package и evidence.

---

## 14) Связь с каноном

- Web‑first и Telegram fallback: `SPECS/ESCALATION.md`.
- Tenant context и RBAC: `SPECS/MULTI_TENANT.md`.
- Console API/UX: `docs/CONSOLE_GUIDE.md`.
- Продуктовые ограничения: `STRATEGY/REQUIREMENTS.md`.
