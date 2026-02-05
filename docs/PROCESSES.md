# Truffles Platform — Process Contracts

## Overview

This document defines the **contracts** between all actors in the system: processes, humans, logic modules, interfaces, and external services.

---

## 1. Actors & Responsibilities

| Actor | Type | Responsibility | Communicates With |
|-------|------|----------------|-------------------|
| **Client (End User)** | Human | Send messages via WhatsApp/Telegram | ChatFlow, Telegram Bot |
| **Manager** | Human | Handle escalations, respond in Telegram | Telegram Group, Console UI |
| **Owner** | Human | Approve responses, configure settings | Console UI, Telegram |
| **Bot (Truffles)** | System | Auto-respond, classify, escalate | All |
| **ChatFlow** | External | WhatsApp gateway | Webhook API |
| **Telegram Bot API** | External | Manager notifications | Telegram Webhook |
| **Qdrant** | External | Vector search for RAG | Knowledge Service |
| **PostgreSQL** | External | Persistent storage | All modules |
| **OpenAI / LLM** | External | Intent classification, response gen | AI Service |

---

## 2. Process Contracts

### 2.1 Inbound Message Flow (WhatsApp → Bot)

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│  WhatsApp   │───▶│   ChatFlow   │───▶│  /webhook   │───▶│   Outbox    │
│   Client    │    │   Gateway    │    │  (enqueue)  │    │   Worker    │
└─────────────┘    └──────────────┘    └─────────────┘    └──────┬──────┘
                                                                  │
                   ┌──────────────────────────────────────────────┘
                   ▼
            ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
            │  Pipeline   │───▶│ Decision    │───▶│  Response   │
            │  Stages     │    │ Engine      │    │  Sender     │
            └─────────────┘    └─────────────┘    └─────────────┘
```

**Contract: ChatFlow → Webhook**
```python
# Input (ChatFlow webhook payload)
{
    "client_slug": str,           # Required
    "body": {
        "messageType": "text" | "image" | "audio" | "document",
        "message": str,           # Required for text
        "metadata": {
            "remoteJid": str,     # Required: WhatsApp JID
            "messageId": str,     # Required: dedup key
            "timestamp": int,     # Unix timestamp
            "instanceId": str,    # Required: branch routing key (must match branches.instance_id)
        }
    }
}

# Output (HTTP response)
{
    "success": bool,
    "message": str,
    "conversation_id": UUID | None
}
```

**Contract Notes**
- `metadata.instanceId` is the canonical branch routing key.
- If `instanceId` does not match any active branch, inbound must be blocked and alerted.

---

### 2.2 Escalation Flow (Bot → Manager)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Low       │───▶│  Handover   │───▶│  Telegram   │───▶│  Manager    │
│ Confidence  │    │  Created    │    │  Notified   │    │  Takes      │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

**Contract: Escalation → Telegram**
```python
# Handover record
{
    "id": UUID,
    "conversation_id": UUID,
    "status": "pending" | "active" | "resolved",
    "trigger_type": "intent" | "low_confidence" | "shield",
    "telegram_message_id": int | None,
}

# Telegram message sent
{
    "chat_id": str,                     # Branch telegram group
    "message_thread_id": int | None,    # User topic
    "text": str,                        # User message + context
    "reply_markup": InlineKeyboard,     # [Беру] [Решено]
}
```

---

### 2.3 Manager Response Flow (Telegram → Client)

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Manager    │───▶│  Telegram   │───▶│  Manager    │───▶│  ChatFlow   │
│  Replies    │    │  Webhook    │    │  Service    │    │  → Client   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

**Contract: Telegram Webhook → Manager Service**
```python
# Input (Telegram update)
{
    "message": {
        "message_thread_id": int,       # User topic
        "from": {"id": int},            # Manager telegram_id
        "text": str,                    # Reply text
        "chat": {"id": int},            # Group chat
    }
}

# Action
1. Resolve conversation by topic_id
2. Find active handover
3. Send via ChatFlow to client
4. Update handover status
5. If owner → auto-approve for learning
```

---

### 2.3.1 Console ↔ Telegram Sync (Target, Web-first)

**Purpose:** Console is the control plane; Telegram is paging/fallback. Actions must be consistent.

**Contract: Console take → Telegram + Client**
```python
# Input (Console API)
POST /console/v1/cases/{case_id}/take

# Actions (must be atomic)
1) state_service.manager_take()  # pending -> manager_active
2) audit: case_taken (actor=agent_id)
3) Telegram:
   - edit handover card buttons -> [Решено]
   - post to topic: "Менеджер подключился"
4) WhatsApp:
   - send template: manager_connected (from client settings/pack)

# Output
{ "success": true, "case_id": UUID, "sync": {"telegram":"sent|failed","client_notify":"sent|failed"} }
```

**Contract: Console resolve/return → Telegram + Client**
```python
# Input
POST /console/v1/cases/{case_id}/resolve
POST /console/v1/cases/{case_id}/return

# Actions
1) state_service.manager_resolve()  # manager_active/pending -> bot_active
2) audit: case_resolved/case_returned
3) Telegram:
   - remove buttons, unpin card
   - post to topic: "Бот снова отвечает"
4) WhatsApp:
   - send template: manager_disconnected (from client settings/pack)
```

---

### 2.3.2 Agent ↔ Telegram Linking (Target)

**Goal:** enforce RBAC and correct audit attribution.

**Flow:**
1) Console UI issues a short token (server-side only).
2) Agent sends `/start <token>` to the bot.
3) Server creates `agent_identities` row (`channel="telegram"`, `external_id=from_user.id`).
4) Console shows “Connected” + username.

**Rule:** take/resolve in Telegram is allowed only for linked agents.

---

### 2.3.3 Manager Quick Replies (Target)

**Goal:** reduce time-to-first-response without hardcoding text.

**Contract:**
- Templates live in client data (`client_settings` or pack).
- Telegram shows quick buttons; click inserts text, manager can edit.
- Saved messages still go through `manager_message_service`.

---

### 2.3.4 Noise Control Rules (Target)

- Branch routing: one group per branch, one topic per client.
- Quiet hours per branch/role (Console settings).
- Event filters (handover created, SLA reminder, client replied while manager_active).
- Dedup and rate-limit for Telegram sends.

---

### 2.3.5 Unified Inbox + Case Health (Target)

**Purpose:** единое понимание “что происходит с заявкой” и где теряются сообщения (Console ↔ Telegram ↔ WhatsApp).

**Contract (target, to encode in OpenAPI + DB/queries):**
- Все inbound/outbound сообщения пишутся в `messages` с `message_metadata.source`:
  - `source="whatsapp"` (inbound/outbound)
  - `source="telegram"` (manager replies)
  - `source="console"` (web replies)
- На уровне кейса вычисляются агрегаты:
- `last_inbound_at`, `last_outbound_at`
- `last_message_preview` (snippet)
- `last_activity_channel` (`whatsapp|telegram|console`)
- `needs_reply` (last inbound > last outbound)
- `unread_count` (сообщения после `agent_last_viewed_at`) — **Phase 2** после трекинга просмотра
- `has_delivery_error`, `has_pending_outbox`
- `health` (ok/degraded/error) + `health_reason`
- Inbox сортируется по `last_inbound_at desc` (самые “живые” сверху).
- В UI:
  - бейдж `NEW` (unread_count > 0)
  - бейдж `LIVE` (inbound < N минут)
  - бейдж `⚠️` при `has_delivery_error` или `has_pending_outbox`.

**Inbox filters (target):**
- `q` (поиск по телефону/имени/ID)
- `phone` (normalized)
- `status`, `branch_id`, `assigned_to_me`
- `has_unread`, `has_delivery_error`
- `last_activity_since`

---

### 2.3.6 Execution Plan (for next sessions)

**P0**
1) Agent↔Telegram linking (tokens, webhook handler, Console UI, audit).
2) Console take/resolve sync to Telegram + WhatsApp notifications.
3) Audit events for telegram_delivery and manager_connect/disconnect.

**P1**
1) Quick replies (templates + UI buttons).
2) Notification rules (quiet hours + event filters).

**P2**
1) On-call routing and personal delivery.
2) Topic reset tool (if topic deleted).

---

### 2.4 Onboarding Flow (Client + Branch)

**Goal**
- 1 phone = 1 branch (strict isolation).
- Inbound replies must always come from the same phone and use branch-only data.
- Launch is allowed only in full mode after all gates are green.

**Inputs (from Owner/BA)**
- Signed legal package + payment confirmation.
- Company name, client, branch.
- Phone number.
- `instanceId` (from ChatFlow).
- Client-level `webhook_secret` (token).
- Optional: manager contact (`telegram_id` / phone).

**Mandatory branch data (100% required before go-live)**
- Address + hours.
- Services + pricing.
- Service durations (estimates or per-service duration notes).
- Policies (refund/reschedule/medical/payment) + guest rules.
- Required disclaimers (medical constraints, "price from" variability, results expectations).
- RU/KZ variants declared for user-facing text (at least `ru` + `kk` in languages).
- Master full names and calendar setup source.
- Enforced via knowledge pack validation + Go/No-Go gate (required fields).

**Step-by-step contract (0..8)**
0. **Niche Reference (mandatory):** for each niche create/update reference pack first. Without reference pack, onboarding is blocked.
1. **Intake:** collect client input from file/form and map into canonical niche fields.
2. **Normalization:** semantic mapping + autofill from context; if fields are missing, launch COLLECT questions until full completion.
3. **Hard validation (100%):** validate mandatory fields (address/hours/services+prices/durations/policies/disclaimers/RU+KK/contacts). If not 100%, launch is blocked.
4. **Provisioning (auto path):** create company/client/branch, bind `phone + instance_id + webhook_secret`, enforce uniqueness (`1 phone = 1 branch`, unique `instance_id`).
5. **Owner manual steps (explicit):** configure WhatsApp in ChatFlow and provide `instanceId/token/phone`; fill branch calendar; confirm payment manually.
6. **Knowledge publish (auto path):** `generate pack -> validate -> publish -> sync`; run test dialog for `FACT/COLLECT/HANDOFF` and verify trace/outbox.
7. **Go-Live decision:** allow launch only when all four are true: data=100%, payment confirmed, WA configured, calendar filled.
8. **Support and changes:** every data change goes through the same pipeline (`intake -> normalize -> validate -> publish`); escalations via Telegram/Console.

**Blocking rules (hard no-go)**
- Missing mandatory data (any field from the required set) -> no launch.
- Unknown `instanceId` -> block inbound and alert.
- Phone connected to multiple instances -> stop (loop risk).
- Payment not confirmed or calendar not configured -> no launch.

**Policy**
- If a company has multiple branches but only one phone, strict isolation is not supported.
- Launch in safe mode is forbidden. Safe mode may exist only as runtime protection, not as onboarding completion.

### 2.5 Control Plane Go/No-Go (Ready for Live Customers)

**Rule (DEC-014):** Live customers allowed only after Control Plane Go/No-Go checklist is satisfied and evidence recorded in `STATE.md`.

#### 2.5.1 Простые определения
- **Control Plane** — web console и процессы управления (provisioning, onboarding gates, knowledge publish, audit) — см. `SPECS/CONTROL_PLANE.md`.
- **Go/No-Go** — формальное решение "можно/нельзя запускать живого клиента" на основе чек-листа; без evidence в `STATE.md` это No-Go.
- **Онбординг клиента** — подготовка данных и технастроек до go-live: branch/instance/phone, знания, handover (см. раздел 2.4 и `Business/Sales/Чеклист_подключения_клиента.md`).
- **Техподдержка после онбординга** — обработка обращений после go-live: каналы, сроки, эскалации. Поток handover описан в разделах 2.2-2.3; регламент поддержки — template `Business/Support/Регламент_техподдержки.md`.
- **Договор** — юридическая база оказания услуг (предмет, оплата, ответственность, SLA/поддержка, обработка данных и приложения). В репо есть template `Business/Legal/ДОГОВОР.md`.
- **Юридическая готовность** — наличие обязательных документов в финальном виде и готовых к подписанию/исполнению (см. `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`).

#### 2.5.2 Go/No-Go checklist (Control Plane)

**A. Юридическая и бизнес-готовность (No-Go без этого)**
- Договор на услуги, NDA, счет на оплату, политика обработки данных — template готов; требуется заполнение под клиента и подписание.
- Согласие на обработку данных, ограничение ответственности, политика возврата, акт приёма-передачи, SLA — отдельные документы/приложения при наличии соответствующих условий в тарифе (сейчас Draft (DERIVED)).
- Правила биллинга канонизированы: `Business/Sales/BILLING_COUNTING.md`.

**B. Онбординг и данные клиента**
- Для ниши есть актуальный reference pack (шаг 0 из раздела 2.4).
- Созданы company/client/branch; `branches.instance_id` и `phone` заполнены и уникальны (см. раздел 2.4).
- Обязательные данные branch-pack заполнены и валидированы на 100% (address/hours/services/pricing/durations/policies/disclaimers/ru/kk/contacts) — см. раздел 2.4.
- `webhook_secret` задан на уровне клиента, webhook URL передан в ChatFlow, inbound проверен внешним номером (см. раздел 2.4).

**C. Control Plane и Knowledge**
- Provisioning/onboarding шаги проходят через консоль и/или API, порядок шагов соблюден (см. `SPECS/CONTROL_PLANE.md`).
- Knowledge publish защищен: validate -> publish -> audit/rollback; после publish есть проверка `FACT/COLLECT/HANDOFF` + trace/outbox.
- Console build info подтвержден в `STATE.md` (DEC-014).

**D. Runtime-готовность**
- Trace/meta/outbox live-check выполнен; evidence в `STATE.md` (DEC-014).
- CI/deploy зеленый и соответствует текущему коду (DEC-014).

**E. Поддержка после go-live**
- Канал эскалации настроен (Telegram/Console handover) и проверен (см. разделы 2.2-2.3).
- Регламент поддержки готов как template; финализация под клиента обязательна.
- Операционный поток изменений данных после запуска использует тот же pipeline из раздела 2.4 (без обходов).

**Decision**
- Любой пропуск в A-E -> **No-Go**.
- Запуск в safe mode как замена Go-Live не допускается.

#### 2.5.3 Где описаны процессы (и чего нет)

**Описано в репо**
- Onboarding flow (канон): раздел 2.4.
- Escalation + manager response: разделы 2.2-2.3.
- Control Plane onboarding + go/no-go gate: `SPECS/CONTROL_PLANE.md`.
- Бриф/чеклист подключения (внутренние, DERIVED): `Business/Sales/Бриф_клиента.md`, `Business/Sales/Чеклист_подключения_клиента.md`.

**Не описано или не готово (по `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`)**
- Отдельные документы в статусе Draft (DERIVED): согласие на обработку данных, ограничение ответственности, политика возврата, акт приёма-передачи, SLA, disclosure об автоматизированных ответах.

### 2.6 End-to-End Contract: signed docs -> onboarding -> support

**Цель:** фиксировать единый операционный путь от подписания документов до регулярной поддержки, без ручных обходов запуска.

**Источники истины (факты по коду/докам):**
- Onboarding state machine: `truffles-api/app/services/onboarding_state.py`.
- Provisioning/admin API: `truffles-api/app/routers/console.py` (`/console/v1/admin/companies|clients|branches|agents`).
- Calendar/specialists API: `truffles-api/app/routers/calendar.py` (`/console/v1/specialists|slots|bookings`).
- OIDC auth mapping: `truffles-api/app/services/console_auth.py`.
- User auto-create on inbound: `truffles-api/app/services/conversation_service.py`.
- Entity models: `truffles-api/app/models/agent.py`, `truffles-api/app/models/agent_membership.py`, `truffles-api/app/models/agent_identity.py`, `truffles-api/app/models/specialist.py`, `truffles-api/app/models/user.py`.
- Console context model: `SPECS/CONTROL_PLANE.md`, `docs/CONSOLE_GUIDE.md`.
- Onboarding SOP and webhook/instance contracts: `SPECS/SYSTEM_REFERENCE.md`.

#### 2.6.1 Stage-by-stage responsibilities (0..8)

**Этап 0 — Niche Reference**
- Truffles (Owner): утвердить эталонный reference pack для ниши до intake.
- Клиент (Owner/Admin): подтвердить, что бизнес-процесс соответствует выбранной нише.
- Выход: reference pack существует и назначен клиенту.

**Этап 1-3 — Intake -> Normalize -> Validate (100%)**
- Truffles (Owner): собрать данные, привести к канону, закрыть все missing fields до 100%.
- Клиент (Owner/Admin): предоставить факты по адресу/часам/услугам/ценам/длительностям/политикам/дисклеймерам/RU+KK/контактам.
- Выход: валидный branch pack без пробелов.

**Этап 4-5 — Provisioning + manual owner actions**
- Truffles (Owner): создать company/client/branch, связать `phone + instance_id + webhook_secret`, проверить уникальность.
- Клиент (Owner/Admin): вручную настроить WA в ChatFlow, передать `instanceId/token/phone`, заполнить календарь филиала, подтвердить оплату.
- Выход: технический контур и коммерческий контур готовы.

**Этап 6 — Publish**
- Truffles (Owner): выполнить `generate -> validate -> publish -> sync`, затем onboarding smoke + trace/outbox checks.
- Клиент (Owner/Admin): подтвердить фактическую корректность опубликованных данных.
- Выход: опубликованный и синхронизированный pack.

**Этап 7 — Go-Live**
- Truffles (Owner): принять решение Go/No-Go по жесткому гейту (данные 100% + оплата + WA + календарь).
- Клиент (Owner/Admin): подтвердить операционную готовность команды.
- Выход: запуск только при полном прохождении гейта.

**Этап 8 — Support and change management**
- Truffles (Owner/Support): вести эскалации через Telegram/Console; любое изменение данных запускать через тот же pipeline (`intake -> normalize -> validate -> publish`).
- Клиент (Owner/Admin/Manager): отправлять изменения только через поддерживаемый процесс, без обходных ручных патчей в runtime.
- Выход: предсказуемые изменения без дрейфа знаний.

#### 2.6.2 Account entities and linkage (runtime contract)

1) **Console staff accounts (owner/admin/manager/support)**
- Identity source: OIDC users (Keycloak realm), seed/example: `ops/keycloak-realm.json`.
- Binding to business: `POST /console/v1/admin/agents` creates `agents` + `agent_memberships`; optional `oidc_subject` creates `agent_identities` with `channel="oidc"`.
- Auth flow: Console reads OIDC `sub`, matches `agent_identities(channel="oidc")`, then resolves access by `agent_memberships` scope (`company/client/branch`).
- Canon fields: `agents.client_id`, `agent_memberships.scope/company_id/client_id/branch_id`.

2) **Working specialists (masters for booking)**
- Stored in `specialists` and linked by `specialists.client_id` + `specialists.branch_id`.
- Used by calendar routes under `/console/v1` (`/specialists`, `/slots`, `/bookings`) and by scheduling logic.

3) **End customers (WhatsApp users)**
- Created automatically on first inbound in `get_or_create_user`.
- Identity key: `users.client_id + users.remote_jid`.

4) **Business hierarchy (company/client/branch)**
- Provisioning API: `POST /console/v1/admin/companies|clients|branches`.
- Console context is always `Company -> Client -> Branch` (`docs/CONSOLE_GUIDE.md`).

#### 2.6.3 Gaps and constraints (current repo)

- Several legal documents remain Draft (DERIVED): see `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`.
- Billing runtime has `company.billing_info` only; there is no invoice/subscription model in core DB.
- Fully automated onboarding orchestrator is still limited; canonical sync path is `ops/sync_client.py` + onboarding state machine.
- Any onboarding flow change must keep Go/No-Go fail-closed and be backed by evidence in `STATE.md`.

#### 2.6.4 Control Plane audit checkpoints

- Provisioning/Onboarding UI parity: `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`.
- Fact audit snapshot: `docs/REPORTS/2026-02-01-console-web-fact-audit.md`.
- RBAC role cards: `docs/CONSOLE_AUDIT/roles/*`.
- UX debt register: `docs/CONSOLE_AUDIT/UX_BACKLOG.md`.
- Any Control Plane behavior change requires a separate Task Package and audit doc updates.

### 2.7 Unified Client Onboarding Runbook (operational, step-by-step)

**Назначение:** единая инструкция запуска клиента от подписания документов до поддержки. Используется Brain/Hands/OPS как исполняемый порядок действий.

**Результат запуска:** клиент считается запущенным только если выполнены шаги 0..8, а Go/No-Go = PASS.

#### 2.7.1 Inputs and artifacts (before step 0)

`Input package` (обязательный):
- Подписанные документы: договор + NDA (если нужен) + политика обработки данных.
- Подтверждение оплаты.
- Ниша клиента и ссылка на reference pack ниши.
- Бриф клиента (факты для pack): адрес, часы, услуги, цены, длительности, политики, дисклеймеры, RU/KK.
- Технические данные: номер WA, `instanceId` из ChatFlow, Telegram chat/group id, список сотрудников бизнеса.

`Artifacts` (что сохраняем):
- IDs: `company_id`, `client_id`, `branch_id`.
- IDs staff: `agent_id`, `agent_membership_id`, `agent_identity_id` (если OIDC linked).
- Validation: список missing fields или отметка `0 missing`.
- Publish evidence: версия knowledge + sync result.
- Live-check evidence: `conversation_id` + `decision_meta/trace` + outbox status.

#### 2.7.2 Steps 0..8 with exact control points

0) **Niche reference gate**
- Проверка: reference pack по нише существует и назначен клиенту.
- Если нет reference pack -> STOP (онбординг не начинается).

1) **Provision business hierarchy (company/client/branch)**
- API:
  - `POST /console/v1/admin/companies`
  - `POST /console/v1/admin/clients`
  - `POST /console/v1/admin/branches`
- Поля branch (минимум): `client_id`, `slug`, `name`, `instance_id` (для active branch), `phone`.
- Контроль:
  - уникальность `slug`, `instance_id`, `phone` в рамках клиента;
  - активный branch запрещен без `instance_id` (`INVALID_PARAM`).

2) **Create Console staff accounts and bind to business**
- Identity source: Keycloak (OIDC user with stable `sub`).
- Binding API: `POST /console/v1/admin/agents`:
  - создаёт `agents`;
  - создаёт `agent_memberships` (`scope=client|branch`);
  - при `oidc_subject` создаёт `agent_identities(channel=\"oidc\")`.
- Правила:
  - `manager`/`specialist` требуют `branch_id`;
  - доступ в Console строится через `agent_identities(channel=oidc, external_id=sub)` + `agent_memberships`.
- Контроль:
  - `GET /console/v1/agents` показывает созданных сотрудников;
  - `GET /console/v1/me` для пользователя возвращает правильный tenant-context.

3) **Configure channel bindings (WA + Telegram + webhook secret)**
- Branch-level:
  - `PATCH /console/v1/admin/branches/{branch_id}` -> `instance_id`, `phone`, `telegram_chat_id`, timezone.
- Client-level:
  - `client_settings.webhook_secret` должен быть установлен.
  - Текущая реализация: отдельного Console endpoint для `webhook_secret` нет, задаётся через DB/ops-процедуру.
- ChatFlow:
  - webhook URL формата `/webhook/{client_slug}?webhook_secret=<secret>&instanceId=<instanceId>`.
- Контроль:
  - unknown `instanceId` блокируется в runtime;
  - один phone не может обслуживать несколько branch в strict isolation.

4) **Prepare required data pack (intake -> normalize -> complete)**
- Обязательные минимальные поля проверяются в `truffles-api/app/services/knowledge_validation.py`.
- Базовый обязательный набор:
  - `client_pack.salon.name`
  - `client_pack.salon.city`
  - `client_pack.salon.address.full`
  - `client_pack.salon.hours.days`
  - `client_pack.salon.hours.open`
  - `client_pack.salon.hours.close`
  - `client_pack.salon.services_summary`
  - `client_pack.salon.communication.languages` (должны включать `ru` и `kk`)
  - `client_pack.services_catalog.services`
  - `client_pack.service_duration_estimates`
  - `client_pack.booking.collect_fields`
  - `client_pack.booking.bot_can_confirm`
  - `client_pack.price_list`
  - `client_pack.guest_policy`
  - `client_pack.safety.medical_note`
  - `client_pack.pricing.price_from_reason`
  - `client_pack.quality.expectations_photo`
  - policy блок: `hard_law`, `payment_info`, `reschedule`, `cancel`, `medical`, `legal`, `complaint`, `discounts`, `guard_topics.refund`
- Контроль:
  - missing fields = 0;
  - если missing > 0 -> возврат в COLLECT и запуск запрещён.

5) **Publish and sync knowledge**
- Pipeline: `validate -> publish -> sync`.
- API:
  - `POST /console/v1/knowledge/validate`
  - `POST /console/v1/knowledge/publish`
  - `GET /console/v1/knowledge/history`
- Контроль:
  - publish успешен;
  - active version существует;
  - warnings/errors обработаны без игнора.

6) **Booking readiness (calendar data)**
- В onboarding state machine для booking обязательны:
  - `working_hours`,
  - `booking_settings`,
  - `specialists` (активный специалист в branch).
- API/данные:
  - `working_hours`/`booking_settings` задаются через branch update;
  - проверка специалистов доступна через `GET /console/v1/specialists`.
- Ограничение текущей реализации:
  - публичного Console endpoint для create/update specialist сейчас нет (только чтение/слоты/bookings в `calendar.py`);
  - заполнение `specialists` делается через согласованный ops-процесс (DB/seed), затем проверяется API.

7) **Advance onboarding state machine + hard Go/No-Go**
- API:
  - `GET /console/v1/onboarding/status?branch_id=<id>`
  - `POST /console/v1/onboarding/advance`
- Порядок шагов:
  - `branch_draft -> integrations -> team -> telegram -> knowledge -> booking -> go_no_go`
- Hard gate PASS (обязателен):
  - data pack 100%;
  - payment confirmed;
  - WA configured (`instance_id` + webhook route);
  - calendar ready (`working_hours` + `booking_settings` + `specialists`).
- Любой missing -> `No-Go`.

8) **Live-check and handover to support**
- Проверка фактического потока:
  - тестовый inbound с allowlist sender;
  - результат содержит `decision_meta/trace`;
  - outbox не в failed.
- Support readiness:
  - Telegram/Console escalation channel проверен;
  - команда знает канал и регламент (`Business/Support/Регламент_техподдержки.md`).
- После запуска любое изменение данных проходит тот же pipeline из шага 4-5.

#### 2.7.3 Account creation scheme (where/how linked)

| Entity | Где создаётся | Как связывается с бизнесом | Где проверять |
|---|---|---|---|
| Console staff (`owner/admin/manager/support`) | Keycloak (OIDC user) + `POST /console/v1/admin/agents` | `agents.client_id`, `agent_memberships(scope/company_id/client_id/branch_id)`, `agent_identities(channel=oidc, external_id=sub)` | `/console/v1/agents`, `/console/v1/me`, таблицы `agents/agent_memberships/agent_identities` |
| Specialists (booking masters) | ops/manual process в `specialists` (до появления write API) | `specialists.client_id + specialists.branch_id` | `GET /console/v1/specialists`, таблица `specialists` |
| End customers (WA users) | auto on first inbound | `users.client_id + users.remote_jid` | таблица `users`, flow `conversation_service.get_or_create_user` |
| Business hierarchy | `POST /console/v1/admin/companies|clients|branches` | `company -> client -> branch` | `/console/v1/me` context, таблицы `companies/clients/branches` |

#### 2.7.4 Stop conditions (mandatory)

- Нет reference pack ниши.
- Нет OIDC mapping для staff (нет `agent_identities(channel=oidc)`).
- Missing required pack fields.
- Не подтверждена оплата.
- Не заполнен booking минимум (`working_hours|booking_settings|specialists`).
- Go/No-Go не PASS.

#### 2.7.5 Ownership

- **Top Architect/Brain:** утверждают канон шагов и DoD.
- **Hands/OPS:** исполняют runbook, собирают evidence.
- **Owner (Жанбол):** финальное решение Go/No-Go и коммерческое подтверждение.

---

## 3. Module Contracts

### 3.1 Result Pattern (all services)

```python
from app.contracts import Result, Ok, Err, IntegrationError

# All external calls return Result[T]
def send_message(...) -> Result[MessageSent]:
    if error:
        return Err(IntegrationError(code="CHATFLOW_ERROR", ...))
    return Ok(MessageSent(remote_jid=jid))
```

### 3.2 Stage Contract (webhook pipeline)

```python
@dataclass
class StageInput:
    conversation: Conversation
    message: Message
    context: dict

@dataclass
class StageOutput:
    decision: Literal["continue", "reply", "escalate", "skip"]
    reply: str | None
    trace: dict

class Stage(Protocol):
    def execute(self, input: StageInput) -> Result[StageOutput]: ...
```

---

## 4. Interface Contracts

### 4.1 Console API → Frontend

| Endpoint | Method | Auth | Response |
|----------|--------|------|----------|
| `/console/v1/me` | GET | Bearer JWT | `ConsoleMeResponse` |
| `/console/v1/cases` | GET | Bearer JWT | `ConsoleCaseListResponse` |
| `/console/v1/cases/{id}` | GET | Bearer JWT | `ConsoleCase` |
| `/console/v1/cases/{id}/take` | POST | Bearer JWT | `ConsoleCaseActionResponse` |
| `/console/v1/cases/{id}/resolve` | POST | Bearer JWT | `ConsoleCaseActionResponse` |
| `/console/v1/settings` | GET/PATCH | Bearer JWT | `ConsoleSettingsResponse` |

**Error Contract:**
```json
{
    "error": {
        "code": "ACCESS_DENIED",
        "message": "...",
        "details": {...}
    }
}
```

### 4.2 External Services

| Service | Base URL | Auth | Timeout | Retry |
|---------|----------|------|---------|-------|
| ChatFlow | `app.chatflow.kz/api/v1` | token param | 30s | 3x backoff |
| Telegram | `api.telegram.org/bot{token}` | URL token | 15s | None |
| Qdrant | `localhost:6333` | api-key header | 10s | None |
| OpenAI | `api.openai.com/v1` | Bearer token | 60s | 2x backoff |

---

## 5. State Machine

### Conversation States

```
                    ┌───────────────┐
                    │  bot_active   │◀──────────────────┐
                    └───────┬───────┘                   │
                            │ escalate                  │
                            ▼                           │
                    ┌───────────────┐                   │
                    │   pending     │───────────────────┤
                    └───────┬───────┘  auto_close       │
                            │ manager_take              │
                            ▼                           │
                    ┌───────────────┐                   │
                    │manager_active │───────────────────┘
                    └───────────────┘  resolve
```

**State Transitions:**
| From | To | Trigger | Actor |
|------|----|---------|-------|
| bot_active | pending | escalate | Bot |
| pending | manager_active | take | Manager |
| pending | bot_active | auto_close (4h) | System |
| manager_active | bot_active | resolve | Manager |

---

## 6. SLAs & Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| Pending SLA | 15 min | Send ping to client |
| Auto-close | 4 hours | Close without response |
| Outbox backlog | > 100 | Alert |
| Escalation rate | > 30% | Review triggers |
| LLM timeout | > 2% | Fallback to safe‑mode (hard‑safety) |

### 6.1 Ops — Outbox Queue & Retry

**Purpose:** увидеть зависшие доставки и безопасно ретраить (WhatsApp/outbox).

**Process:**
1) Ops UI → открыть очередь outbox (pending/processing/failed).
2) Для failed — нажать Retry (bulk или по одному).
3) API переводит статус `FAILED → PENDING`, сбрасывает `next_attempt_at`, пишет audit `outbox_retry`.
4) Worker подхватывает и повторяет доставку; результат виден в статусах.

**Console API:**
- `GET /console/v1/ops/outbox` (filters: status, cursor, limit).
- `POST /console/v1/ops/outbox/retry` (ids[] optional, limit default 100).

---

## 7. Error Codes

| Code | Module | Meaning |
|------|--------|---------|
| `CHATFLOW_TIMEOUT` | chatflow | Request timed out |
| `CHATFLOW_ERROR` | chatflow | Non-200 response |
| `TELEGRAM_RATE_LIMIT` | telegram | 429 response |
| `QDRANT_ERROR` | qdrant | Vector search failed |
| `LLM_TIMEOUT` | ai_service | LLM request timed out |
| `AUTH_REQUIRED` | console | No bearer token |
| `ACCESS_DENIED` | console | Insufficient permissions |
| `INVALID_STATE_TRANSITION` | state | FSM violation |
