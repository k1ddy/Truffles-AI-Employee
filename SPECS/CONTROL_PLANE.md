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
- **Platform Admin** — управление тенантами и модулями, доступ к Ops по всей системе.
- **Platform Support** — диагностика/помощь, read‑only в provisioning (без create/update).

**Клиент (бизнес):**
- **Owner** — полный доступ (знания, команда, интеграции, заявки, настройки).
- **Admin** — всё, кроме коммерческих/плановых настроек.
- **Manager** — заявки, календарь, ограниченные операционные настройки (branch‑scoped, `branch_id` обязателен).
- **Specialist/Master** — только календарь/слоты (опционально).
- **Viewer/Analyst** — read‑only (опционально).

**Принцип:** UI и навигация режутся по роли, чтобы не было шума.

---

## 3) Tenant‑контекст и UX выбора (обязательный канон)

См. `SPECS/MULTI_TENANT.md`.

- Контекст **Company → Client → Branch** всегда виден.
- Selector показывается только при наличии выбора.
- При `selection_required` / `branch_selection_required` — блокирующее состояние.
- Ошибки понятны: “Выберите клиента/филиал”, “Нет доступа”.

---

## 4) Информационная архитектура (IA)

**Owner/Admin:**
1) Inbox  2) Calendar  3) Knowledge  4) Team  5) Integrations  6) Settings  7) Audit  8) Insights (опционально)

**Manager:** Inbox, Calendar, read‑only Knowledge, Team directory.

**Platform Admin:** Tenants, Inbox (support), Ops, Audit, Integrations registry.

---

## 5) Онбординг и Provisioning (Platform Admin)

**Provisioning flow (Web‑first)** как стандарт:
1) Create Branch (Draft): name, slug, timezone (default ok), остальное optional (`is_active=false` без `instance_id`).
2) Integrations: `instance_id` (WA) → включаем WhatsApp‑channel.
3) Team: владельцы/админы (доступ в Console).
4) Telegram: связка бота → `telegram_chat_id` → включаем Telegram‑capability.
5) Knowledge: `knowledge_tag` / branch‑pack → publish.
6) Booking: `working_hours` / `booking_settings` / specialists → включаем booking‑capability.
7) Go/No‑Go: проверяем только поля, нужные для включённых capabilities.

**Go/No‑Go gate:** обязательные поля проверяются по включённым capabilities; без `instance_id` ветка остаётся draft.

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

## 9) Inbox UX (без шума, с прогрессивным раскрытием)

**3‑pane:** sidebar / list / details.

**List:** имя/телефон, превью, последняя активность, филиал, NEW/LIVE/⚠️.

**Details (cards):**
- по умолчанию: timeline + quick actions + health
- раскрываемые: Context, Explain, Trace, Telegram trail

**Quick Replies:** системные и клиентские макросы, клики вставки.

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
