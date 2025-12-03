# Truffles Chatbot Architecture

## Версия: 2.0 (Refactored)
## Дата: 2025-11-29

---

## 1. Высокоуровневая архитектура

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ВХОДЯЩИЕ КАНАЛЫ                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│   WhatsApp          Telegram          Instagram          (Future)           │
│      │                  │                 │                  │              │
│      └──────────────────┴─────────────────┴──────────────────┘              │
│                                   │                                          │
│                                   ▼                                          │
│                         ┌─────────────────┐                                  │
│                         │   1_Webhook     │  ← Redis дедупликация           │
│                         └────────┬────────┘                                  │
│                                  │                                           │
│                                  ▼                                           │
│                    ┌─────────────────────────┐                               │
│                    │  2_Parse/ChannelRouter  │                               │
│                    │  ├─ NormalizeEvent      │                               │
│                    │  ├─ CheckUser (upsert)  │                               │
│                    │  ├─ SaveInboundMessage  │  ← NEW                        │
│                    │  └─ Channel Switch      │                               │
│                    └───────────┬─────────────┘                               │
│                                │                                             │
│              ┌─────────────────┼─────────────────┐                           │
│              ▼                 ▼                 ▼                           │
│     ┌────────────────┐ ┌────────────────┐ ┌────────────────┐                │
│     │ 3_WhatsApp     │ │ 3_Telegram     │ │ 3_Instagram    │                │
│     │   Adapter      │ │   Adapter      │ │   Adapter      │                │
│     └───────┬────────┘ └───────┬────────┘ └───────┬────────┘                │
│             │                  │                  │                          │
│             └──────────────────┴──────────────────┘                          │
│                                │                                             │
│                                ▼                                             │
│                    ┌─────────────────────────┐                               │
│                    │    INTENT CLASSIFIER    │  ← NEW (отдельный workflow)  │
│                    │    (5_ClassifyIntent)   │                               │
│                    └───────────┬─────────────┘                               │
│                                │                                             │
│         ┌──────────┬──────────┼──────────┬──────────┬──────────┐            │
│         ▼          ▼          ▼          ▼          ▼          ▼            │
│    ┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌─────────┐       │
│    │greeting ││question ││ pricing ││complaint││ready_buy││ other   │       │
│    └────┬────┘└────┬────┘└────┬────┘└────┬────┘└────┬────┘└────┬────┘       │
│         │          │          │          │          │          │            │
│         ▼          ▼          ▼          ▼          ▼          ▼            │
│    ┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌─────────┐       │
│    │ Simple  ││   RAG   ││ Pricing ││ Handover││ Handover││Fallback │       │
│    │Response ││ Lookup  ││  Calc   ││  Tool   ││  Tool   ││ + RAG   │       │
│    └────┬────┘└────┬────┘└────┬────┘└────┬────┘└────┬────┘└────┬────┘       │
│         │          │          │          │          │          │            │
│         └──────────┴──────────┴──────────┴──────────┴──────────┘            │
│                                │                                             │
│                                ▼                                             │
│                    ┌─────────────────────────┐                               │
│                    │   RESPONSE GENERATOR    │                               │
│                    │   (6_GenerateResponse)  │                               │
│                    └───────────┬─────────────┘                               │
│                                │                                             │
│                                ▼                                             │
│                    ┌─────────────────────────┐                               │
│                    │  SaveOutboundMessage    │                               │
│                    └───────────┬─────────────┘                               │
│                                │                                             │
│                                ▼                                             │
│                    ┌─────────────────────────┐                               │
│                    │   SEND (per channel)    │                               │
│                    │   WhatsApp / Telegram   │                               │
│                    └─────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Intent Classification

### 2.1. Intents (расширяемый список)

| Intent | Описание | Действие |
|--------|----------|----------|
| `greeting` | Приветствие, "привет", "здравствуйте" | Ответ из prompts таблицы |
| `question_service` | Вопрос о услугах Truffles | RAG lookup → ответ |
| `question_pricing` | Вопрос о ценах, тарифах | RAG + Pricing Calculator |
| `question_technical` | Технический вопрос | RAG lookup |
| `complaint` | Жалоба, негатив | Handover to manager |
| `ready_to_buy` | Готов купить, "хочу заказать" | Handover to manager |
| `request_manager` | Явный запрос менеджера | Handover |
| `off_topic` | Не по теме | Вежливый отказ + redirect |
| `unclear` | Непонятно | Уточняющий вопрос |

### 2.2. Classifier Prompt (для LLM)

```
Classify the user message into one of these intents:
- greeting
- question_service
- question_pricing
- question_technical
- complaint
- ready_to_buy
- request_manager
- off_topic
- unclear

Consider conversation history for context.
Return JSON: {"intent": "...", "confidence": 0.0-1.0, "entities": {...}}
```

---

## 3. Компоненты системы

### 3.1. Workflows

| ID | Name | Описание | Вызывается из |
|----|------|----------|---------------|
| 1 | `1_Webhook` | Входная точка, дедупликация | External (WhatsApp provider) |
| 2 | `2_Parse/ChannelRouter` | Нормализация, CheckUser, роутинг | 1_Webhook |
| 3a | `3_WhatsApp_Adapter` | WhatsApp специфика + отправка | 2_Parse |
| 3b | `3_Telegram_Adapter` | Telegram специфика + отправка | 2_Parse |
| 4 | `4_NormalizeMedia` | Audio→Text (ElevenLabs), Image→Text | 3_* Adapters |
| 5 | `5_ClassifyIntent` | Intent classification | 3_* Adapters |
| 6 | `6_GenerateResponse` | RAG + Response generation | 5_ClassifyIntent |
| 7 | `7_Handover` | Передача менеджеру | 6_GenerateResponse |
| 8 | `cronUpdateDocs` | Обновление RAG из Google Drive | Cron (1 hour) |

### 3.2. База данных (truffles-chat-bot)

| Таблица | Назначение |
|---------|------------|
| `users` | Пользователи (phone, remote_jid, name, etc.) |
| `messages` | История сообщений (user_id, role, content, intent) |
| `prompts` | Шаблоны ответов (greeting, fallback, etc.) |
| `handovers` | Логи передачи менеджеру |
| `faq_items` | FAQ (legacy, можно мигрировать в Qdrant) |
| `scoring_rules` | Правила скоринга лидов |
| `lead_scores` | Оценки лидов |

### 3.3. Внешние сервисы

| Сервис | Назначение | Credentials |
|--------|------------|-------------|
| PostgreSQL | Основная БД | `truffles-chat-bot` |
| Redis | Дедупликация, Chat Memory, кэш | Local |
| Qdrant | Vector DB для RAG | QdrantLocal |
| OpenAI | LLM (gpt-4.1-mini), Embeddings | OpenAi account |
| ElevenLabs | Speech-to-Text | ElevenLabs account |
| Cohere | Reranker для RAG | CohereApi account |
| Google Drive | Хранение документов | Google Drive account |
| ChatFlow.kz | WhatsApp API | Token in workflow |

---

## 4. Конфигурация (для будущей кастомизации)

### 4.1. Что должно быть конфигурируемым

```yaml
# Пример config.yaml (будущее)
channels:
  whatsapp:
    enabled: true
    provider: chatflow.kz
    instance_id: "..."
    token: "..."
  telegram:
    enabled: false
    bot_token: "..."
  instagram:
    enabled: false

llm:
  provider: openai
  model: gpt-4.1-mini
  temperature: 0.7
  
stt:
  provider: elevenlabs  # or openai
  language: auto  # ru, kk, en
  
rag:
  collection: truffles_knowledge
  chunk_size: 500
  chunk_overlap: 50
  top_k: 5
  reranker: cohere
  
intents:
  handover_triggers:
    - complaint
    - ready_to_buy
    - request_manager
  max_unclear_before_handover: 3
```

### 4.2. Prompts из БД

Все промпты должны загружаться из таблицы `prompts`:
- `greeting_initial`
- `clarification_needed`
- `handover_to_manager`
- `fallback_default`
- `intent_classifier` (NEW)
- `response_generator` (NEW)

---

## 5. Data Flow (детально)

### 5.1. Inbound Message

```
1. WhatsApp Provider → POST /webhook/flow
2. 1_Webhook:
   - Extract messageId
   - Redis GET messageId → if exists, SKIP (duplicate)
   - Redis SET messageId (TTL 24h)
   - Call 2_Parse/ChannelRouter

3. 2_Parse/ChannelRouter:
   - NormalizeEvent (unified format)
   - Call CheckUser (upsert to users table)
   - SaveInboundMessage (insert to messages)
   - Switch by channel → WhatsApp Adapter

4. 3_WhatsApp Adapter:
   - If audio → Call 4_NormalizeMedia (STT)
   - Call 5_ClassifyIntent
   - Call 6_GenerateResponse (with intent + RAG)
   - SaveOutboundMessage
   - Send WhatsApp
```

### 5.2. Normalized Event Format

```json
{
  "event": {
    "channel": "whatsapp",
    "user_id": "77015705555",
    "session_id": "77015705555@s.whatsapp.net",
    "message": "Сколько стоит бот?",
    "message_type": "text",
    "attachments": [],
    "locale": "ru",
    "timestamp": 1732889277000,
    "metadata": {
      "messageId": "ABC123",
      "sender": "John",
      "remoteJid": "77015705555@s.whatsapp.net"
    }
  },
  "user": {
    "id": "uuid-...",
    "phone": "77015705555",
    "name": "John"
  }
}
```

---

## 6. TODO / Roadmap

### Phase 1: Core Fix (Current)
- [x] Дедупликация через Redis
- [x] CheckUser интеграция
- [x] SaveInboundMessage
- [x] SaveOutboundMessage
- [ ] Fix audio processing (ElevenLabs)
- [ ] Intent Classifier workflow
- [ ] Simplify Sales Orchestrator

### Phase 2: Quality
- [ ] Prompts из БД (не хардкод)
- [ ] Улучшить RAG (chunking, reranking)
- [ ] Entity extraction (бизнес тип, бюджет)
- [ ] Conversation context в Redis

### Phase 3: Channels
- [ ] Telegram Adapter
- [ ] Instagram Adapter

### Phase 4: Features
- [ ] Обработка документов (PDF, DOCX)
- [ ] Обработка фото (OCR)
- [ ] Kaspi Pay интеграция
- [ ] Lead scoring

### Phase 5: Enterprise
- [ ] Multi-tenant (разные бизнесы)
- [ ] Admin UI для настроек
- [ ] Analytics dashboard

---

## 7. Changelog

| Дата | Изменение |
|------|-----------|
| 2025-11-29 | Initial architecture document |
| 2025-11-29 | Added SaveInboundMessage, SaveOutboundMessage |
| 2025-11-29 | Fixed Channel Switch expression |

