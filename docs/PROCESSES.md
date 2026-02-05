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

**Inputs (from Owner/BA)**
- Company name
- Branch name
- Phone number
- `instanceId` (from ChatFlow)
- Optional: manager contact (telegram_id / phone)

**Mandatory branch data (required before go-live)**
- Address + hours
- Services + pricing
- Service durations (estimates or per-service duration notes)
- Policies (refund/reschedule/medical/payment) + guest rules
- Required disclaimers (medical constraints, "price from" variability, results expectations)
- RU/KZ variants declared for user-facing text (at least `ru` + `kk` in languages)
- Master full names (schedule slots later via CRM/calendar integration)
  - Enforced via knowledge pack validation + Go/No-Go gate (required fields).

**Process**
1. Provision tenant + branch records.
2. Map `branches.instance_id = instanceId` and `phone = number`.
3. Validate uniqueness: one phone and one instanceId per branch.
4. Load and validate branch data pack; index knowledge by `knowledge_tag`.
5. Generate webhook URL and send it back for ChatFlow configuration.
6. Live-check using an external sender number (not connected to any instance).
7. Go-live + monitoring (outbox, SLA, delivery, loops).

**Blocking rules (no-go)**
- Missing mandatory branch data -> block go-live (safe mode only with explicit approval).
- Unknown `instanceId` -> block inbound and alert.
- Phone connected to multiple instances -> stop (loop risk).

**Safe mode (explicit approval only)**
- Allowed outcomes: `FACT`, `COLLECT`, `HANDOFF` only.
- `FACT` is allowed only for verified pack facts; no inference or booking commit.

**Example**
Company: "Mira Salon"

Branches:
- "Mira Salon - Zhandosova" -> phone `+7 701 111 1111`, instanceId `INST_AAA`
- "Mira Salon - Zharokova" -> phone `+7 701 222 2222`, instanceId `INST_BBB`
- "Mira Salon - Timiryazeva" -> phone `+7 701 333 3333`, instanceId `INST_CCC`

Generated webhooks:
- `https://api.truffles.kz/webhook/mira_salon?webhook_secret=...&instanceId=INST_AAA`
- `https://api.truffles.kz/webhook/mira_salon?webhook_secret=...&instanceId=INST_BBB`
- `https://api.truffles.kz/webhook/mira_salon?webhook_secret=...&instanceId=INST_CCC`

**Policy**
- If a company has multiple branches but only one phone, strict isolation is not supported.
- Require one phone per branch to onboard.

### 2.5 Control Plane Go/No-Go (Ready for Live Customers)

**Rule (DEC-014):** Live customers allowed only after Control Plane Go/No-Go checklist is satisfied and evidence recorded in `STATE.md`.

#### 2.5.1 Простые определения
- **Control Plane** — web console и процессы управления (provisioning, onboarding gates, knowledge publish, audit) — см. `SPECS/CONTROL_PLANE.md`.
- **Go/No-Go** — формальное решение "можно/нельзя запускать живого клиента" на основе чек-листа; без evidence в `STATE.md` это No-Go.
- **Онбординг клиента** — подготовка данных и технастроек до go-live: branch/instance/phone, знания, handover (см. раздел 2.4 и `Business/Sales/Чеклист_подключения_клиента.md`).
- **Техподдержка после онбординга** — обработка обращений после go-live: каналы, сроки, эскалации. Поток handover описан в разделах 2.2-2.3; регламент поддержки отсутствует как отдельный документ (см. `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`).
- **Договор** — юридическая база оказания услуг (предмет, оплата, ответственность, SLA/поддержка, обработка данных). В репо есть шаблон `Business/Legal/ДОГОВОР.md` (DERIVED; не канон до утверждения/подписания).
- **Юридическая готовность** — наличие обязательных документов в финальном виде и готовых к подписанию/исполнению (см. `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`).

#### 2.5.2 Go/No-Go checklist (Control Plane)

**A. Юридическая и бизнес-готовность (No-Go без этого)**
- Договор на услуги, NDA, счет на оплату, политика обработки данных — финальные/согласованные версии; в `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md` отмечены как критичные и отсутствующие.
- Шаблоны `Business/Legal/*.md` помечены DERIVED и не считаются каноническими до утверждения/подписания.
- Если есть правила биллинга, зафиксировать каноническую версию (сейчас `Business/Sales/BILLING_COUNTING.md` = DRAFT).

**B. Онбординг и данные клиента**
- Созданы tenant+branch; `branches.instance_id` и `phone` заполнены и уникальны (см. раздел 2.4).
- Обязательные данные branch-pack заполнены и валидированы (address/hours/services/pricing/durations/policies/disclaimers/ru/kk) — см. раздел 2.4.
- Webhook URL создан и передан в ChatFlow; inbound проверен внешним номером (см. раздел 2.4).

**C. Control Plane и Knowledge**
- Provisioning/onboarding шаги проходят через консоль и/или API, порядок шагов соблюден (см. `SPECS/CONTROL_PLANE.md`).
- Knowledge publish защищен: validate → publish → audit/rollback; ошибки ведут к safe mode (см. `SPECS/CONTROL_PLANE.md`).
- Console build info подтвержден в `STATE.md` (DEC-014).

**D. Runtime-готовность**
- Trace/meta/outbox live-check выполнен; evidence в `STATE.md` (DEC-014).
- CI/deploy зеленый и соответствует текущему коду (DEC-014).

**E. Поддержка после go-live**
- Канал эскалации настроен (Telegram/Console handover) и проверен (см. разделы 2.2-2.3).
- Есть согласованный регламент поддержки (в `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md` сейчас отмечен как отсутствующий).

**Decision**
- Любой пропуск в A-D → **No-Go**. Возможен только safe mode по правилам раздела 2.4 и с явным одобрением.

#### 2.5.3 Где описаны процессы (и чего нет)

**Описано в репо**
- Onboarding flow (канон): раздел 2.4.
- Escalation + manager response: разделы 2.2-2.3.
- Control Plane onboarding + go/no-go gate: `SPECS/CONTROL_PLANE.md`.
- Бриф/чеклист подключения (внутренние, DERIVED): `Business/Sales/Бриф_клиента.md`, `Business/Sales/Чеклист_подключения_клиента.md`.

**Не описано или не готово (по `Business/ДОКУМЕНТЫ_АРСЕНАЛ.md`)**
- Критичные документы до старта: договор, NDA, счет, политика обработки данных — не в финальном/подписанном виде.
- Регламент техподдержки, чеклист запуска, инструкция для клиента — отсутствуют как финальные документы.

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
