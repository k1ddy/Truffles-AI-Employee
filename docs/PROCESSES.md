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
| LLM timeout | > 2% | Fallback to deterministic |

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
