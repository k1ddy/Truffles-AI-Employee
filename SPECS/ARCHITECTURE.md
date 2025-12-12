# АРХИТЕКТУРА TRUFFLES

**Источник правды по технической архитектуре системы.**
**Создано:** 2025-12-06
**Обновлено:** 2025-12-10

---

## СТАТУС

| Компонент | Статус |
|-----------|--------|
| Python API (FastAPI) | ✅ РАБОТАЕТ |
| n8n (только роутинг) | ✅ РАБОТАЕТ |
| PostgreSQL | ✅ РАБОТАЕТ |
| Qdrant (RAG) | ✅ РАБОТАЕТ |
| BGE-M3 (Embeddings) | ✅ РАБОТАЕТ |
| Redis | ✅ РАБОТАЕТ (для n8n) |
| Telegram интеграция | ✅ РАБОТАЕТ |
| WhatsApp интеграция | ✅ РАБОТАЕТ (через ChatFlow) |

---

# ЧАСТЬ 1: ОБЗОР СИСТЕМЫ

## Высокоуровневая архитектура

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────────┐
│    WhatsApp     │────▶│      n8n        │────▶│      Python API         │
│   (ChatFlow)    │◀────│   (роутинг)     │◀────│    (вся логика)         │
└─────────────────┘     └─────────────────┘     └───────────┬─────────────┘
                                                            │
┌─────────────────┐                                         │
│    Telegram     │─────────────────────────────────────────┤
│  (менеджеры)    │◀────────────────────────────────────────┤
└─────────────────┘                                         │
                                                            │
                        ┌───────────────────────────────────┼───────────────┐
                        │                                   │               │
                        ▼                                   ▼               ▼
                ┌───────────────┐                   ┌───────────────┐ ┌───────────┐
                │  PostgreSQL   │                   │    Qdrant     │ │  BGE-M3   │
                │  (состояния)  │                   │    (RAG)      │ │(embeddings)│
                └───────────────┘                   └───────────────┘ └───────────┘
```

## Принцип разделения

| Компонент | Ответственность |
|-----------|-----------------|
| **n8n** | Только роутинг: принять webhook → вызвать API → отправить ответ |
| **Python API** | Вся бизнес-логика: состояния, AI, эскалация, напоминания |
| **PostgreSQL** | Персистентность: пользователи, диалоги, сообщения, заявки |
| **Qdrant** | Семантический поиск: база знаний, RAG |
| **BGE-M3** | Векторизация текста для RAG |

---

# ЧАСТЬ 2: СТЕК ТЕХНОЛОГИЙ

## Почему такой выбор

### Python + FastAPI

| Альтернатива | Почему не подошла |
|--------------|-------------------|
| Вся логика в n8n | Нетестируемо, сложно дебажить, JSON hell |
| Node.js | Python лучше для ML/AI интеграций |
| Django | Overkill для API, FastAPI быстрее |

**Выбор:** FastAPI — асинхронный, быстрый, автодокументация, типизация.

### PostgreSQL

| Альтернатива | Почему не подошла |
|--------------|-------------------|
| MongoDB | Нужны транзакции, связи между таблицами |
| SQLite | Не масштабируется |
| MySQL | PostgreSQL мощнее (JSONB, arrays) |

**Выбор:** PostgreSQL — надёжный, JSONB для гибких полей, проверенный.

### Qdrant (Vector DB)

| Альтернатива | Почему не подошла |
|--------------|-------------------|
| Pinecone | Cloud-only, дорого, данные не в Казахстане |
| Weaviate | Сложнее настраивать |
| pgvector | Медленнее на больших объёмах |
| Chroma | Менее зрелый |

**Выбор:** Qdrant — self-hosted, быстрый, простой API, активно развивается.

### BGE-M3 (Embeddings)

| Альтернатива | Почему не подошла |
|--------------|-------------------|
| OpenAI embeddings | Платно, данные уходят в облако |
| sentence-transformers | Хуже качество на русском |
| E5 | BGE-M3 лучше для мультиязычности |

**Выбор:** BGE-M3 — бесплатный, self-hosted, отличное качество на русском/казахском.

### n8n (Orchestration)

| Альтернатива | Почему не подошла |
|--------------|-------------------|
| Чистый код | Долго писать интеграции |
| Zapier | Cloud-only, дорого |
| Make | Ограничения кастомизации |

**Выбор:** n8n — self-hosted, визуальный, но используем только для роутинга (не для логики).

---

# ЧАСТЬ 3: КОМПОНЕНТЫ СИСТЕМЫ

## Python API (truffles-api)

### Структура

```
truffles-api/
├── app/
│   ├── main.py                 # FastAPI приложение
│   ├── config.py               # Конфигурация
│   ├── database.py             # SQLAlchemy подключение
│   │
│   ├── models/                 # ORM модели
│   │   ├── client.py           # Клиенты (компании)
│   │   ├── client_settings.py  # Настройки клиента
│   │   ├── user.py             # Пользователи (телефоны)
│   │   ├── conversation.py     # Диалоги
│   │   ├── message.py          # Сообщения
│   │   ├── handover.py         # Заявки на менеджера
│   │   └── prompt.py           # Промпты для AI
│   │
│   ├── routers/                # API endpoints
│   │   ├── message.py          # POST /message — входящие сообщения
│   │   ├── callback.py         # POST /callback — действия менеджера
│   │   ├── telegram_webhook.py # POST /telegram-webhook — Telegram
│   │   ├── reminders.py        # POST /reminders/process — напоминания
│   │   └── webhook.py          # POST /webhook — от n8n
│   │
│   ├── services/               # Бизнес-логика
│   │   ├── state_machine.py    # Состояния диалога
│   │   ├── intent_service.py   # Классификация намерений
│   │   ├── ai_service.py       # Генерация ответов (LLM)
│   │   ├── knowledge_service.py# RAG поиск
│   │   ├── escalation_service.py # Эскалация
│   │   ├── reminder_service.py # Напоминания
│   │   ├── telegram_service.py # Отправка в Telegram
│   │   ├── chatflow_service.py # Отправка в WhatsApp
│   │   ├── message_service.py  # Работа с сообщениями
│   │   ├── conversation_service.py # Работа с диалогами
│   │   ├── callback_service.py # Обработка callback
│   │   └── manager_message_service.py # Ответы менеджеров
│   │
│   ├── schemas/                # Pydantic схемы
│   │   ├── message.py
│   │   ├── callback.py
│   │   ├── telegram.py
│   │   └── reminder.py
│   │
│   └── llm/                    # LLM провайдеры
│       ├── base.py
│       └── openai_provider.py
│
├── migrations/                 # SQL миграции
├── tests/                      # Тесты
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

### Endpoints

| Endpoint | Метод | Назначение |
|----------|-------|------------|
| `/message` | POST | Обработка входящего сообщения от клиента |
| `/callback` | POST | Действия менеджера (take/resolve/skip/return) |
| `/telegram-webhook` | POST | Webhook от Telegram (кнопки, сообщения менеджеров) |
| `/reminders/process` | POST | Обработка и отправка напоминаний |
| `/health` | GET | Проверка здоровья сервиса |
| `/db-check` | GET | Проверка подключения к БД |

### State Machine

```
┌─────────────────────────────────────────────────────────────┐
│                    СОСТОЯНИЯ ДИАЛОГА                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  bot_active ◄──────────────────────────────────────────┐    │
│      │                                                 │    │
│      │ should_escalate(intent)                         │    │
│      ▼                                                 │    │
│   pending ─────────────────────────────────────────┐   │    │
│      │                                             │   │    │
│      │ manager [Беру]                              │   │    │
│      ▼                                             │   │    │
│  manager_active ───────────────────────────────────┼───┘    │
│                        manager [Решено]            │        │
│                                                    │        │
└────────────────────────────────────────────────────┘        │
```

**Файл:** `services/state_machine.py`

```python
class ConversationState(str, Enum):
    BOT_ACTIVE = "bot_active"
    PENDING = "pending"
    MANAGER_ACTIVE = "manager_active"

VALID_TRANSITIONS = {
    ConversationState.BOT_ACTIVE: [ConversationState.PENDING],
    ConversationState.PENDING: [ConversationState.BOT_ACTIVE, ConversationState.MANAGER_ACTIVE],
    ConversationState.MANAGER_ACTIVE: [ConversationState.BOT_ACTIVE],
}
```

---

## n8n (роутинг)

### Активные workflows

| ID | Название | Назначение |
|----|----------|------------|
| 1_Webhook | Webhook | Принять от ChatFlow → POST /message → отправить ответ |
| Knowledge Sync | Knowledge Sync | Google Docs → Qdrant (ручной запуск) |

### 1_Webhook — как работает

```
WhatsApp (ChatFlow) отправляет webhook
        ↓
n8n 1_Webhook принимает
        ↓
HTTP Request: POST https://api.truffles.kz/message
  Body: { client_id, remote_jid, content, channel }
        ↓
Получает ответ: { bot_response, state, intent }
        ↓
IF bot_response exists:
  HTTP Request: POST ChatFlow API (отправить в WhatsApp)
```

**Почему через n8n, а не напрямую:**
- ChatFlow отправляет webhook на один URL
- n8n умеет парсить разные форматы
- Легко добавить другие каналы (Telegram bot, Instagram)

---

## PostgreSQL

### Схема базы данных

> **ВАЖНО:** Полная иерархия и конечное видение описаны в `SPECS/MULTI_TENANT.md`

```
┌─────────────┐
│  companies  │ (биллинг, юр. лицо) — СУЩЕСТВУЕТ, НЕ ИСПОЛЬЗУЕТСЯ
│             │
│ id (PK)     │
│ name        │
│ billing_info│
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│   clients   │────▶│ client_settings │     │   prompts   │
│             │     │                 │     │             │
│ id (PK)     │     │ client_id (FK)  │     │ client_id   │
│ company_id  │     │ telegram_chat_id│     │ name        │
│ name        │     │ telegram_bot_token    │ text        │
│ status      │     │ reminder_timeout_1    │ is_active   │
└──────┬──────┘     │ mute_duration_*  │     └─────────────┘
       │            └─────────────────┘
       │
       ├────────────────────────────────┐
       ▼                                ▼
┌─────────────┐                  ┌─────────────┐
│  branches   │ ⚠️ НЕ ПОДКЛЮЧЕН  │    users    │
│             │                  │             │
│ id (PK)     │                  │ id (PK)     │
│ client_id   │                  │ phone       │
│ instance_id │ (WhatsApp)       │ name        │
│ telegram_   │                  │ metadata    │
│ chat_id     │                  └──────┬──────┘
│ knowledge_  │                         │
│ tag         │                         ▼
└─────────────┘                  ┌─────────────────┐     ┌─────────────┐
                                 │  conversations  │────▶│  messages   │
                                 │                 │     │             │
                                 │ id (PK)         │     │ id (PK)     │
                                 │ user_id (FK)    │     │ conv_id (FK)│
                                 │ client_id       │     │ role        │
                                 │ state           │     │ content     │
                                 │ bot_muted_until │     │ created_at  │
                                 │ telegram_topic_id     └─────────────┘
                                 └────────┬────────┘
                                          │
                                          ▼
                                 ┌─────────────────┐
                                 │    handovers    │
                                 │                 │
                                 │ id (PK)         │
                                 │ conversation_id │
                                 │ status          │
                                 │ trigger_type    │
                                 │ user_message    │
                                 │ manager_response│
                                 │ assigned_to     │
                                 │ reminder_*_sent │
                                 └─────────────────┘
```

### ПЛАН: Подключение Branch

После реализации (см. STATE.md):
- `conversations.branch_id` вместо `client_id`
- Роутинг по `branch.instance_id`
- Telegram credentials из `branch.telegram_chat_id`
- RAG по `branch.knowledge_tag`

### Ключевые таблицы

**companies** — юр. лица (биллинг) — НЕ ИСПОЛЬЗУЕТСЯ
```sql
id           UUID PRIMARY KEY
name         TEXT            -- "ТОО Truffles"
billing_info JSONB           -- информация для оплаты
```

**clients** — бренды/продукты
```sql
id          UUID PRIMARY KEY
name        TEXT            -- "Салон Мира"
slug        TEXT UNIQUE     -- "demo_salon"
status      TEXT            -- active, suspended
config      JSONB           -- дополнительные настройки
```

**client_settings** — настройки эскалации и мьюта
```sql
client_id                   UUID PRIMARY KEY
telegram_chat_id            TEXT    -- ID группы в Telegram
telegram_bot_token          TEXT    -- токен бота
owner_telegram_id           TEXT    -- @username владельца
reminder_timeout_1          INT     -- 30 (минут)
reminder_timeout_2          INT     -- 60 (минут)
mute_duration_first_minutes INT     -- 30
mute_duration_second_hours  INT     -- 24
enable_reminders            BOOLEAN -- true
enable_owner_escalation     BOOLEAN -- true
```

**branches** — филиалы (⚠️ СУЩЕСТВУЕТ, НЕ ПОДКЛЮЧЕН)
```sql
id               UUID PRIMARY KEY
client_id        UUID REFERENCES clients
slug             TEXT            -- "almaty"
name             TEXT            -- "Филиал Алматы"
instance_id      TEXT            -- WhatsApp instance (ChatFlow)
phone            TEXT            -- +7 777 123 4567
telegram_chat_id TEXT            -- ID группы в Telegram (для эскалации)
knowledge_tag    TEXT            -- тег для RAG фильтрации
is_active        BOOLEAN         -- true
```

**conversations** — диалоги с клиентами
```sql
id                  UUID PRIMARY KEY
client_id           UUID
user_id             UUID REFERENCES users
state               TEXT    -- bot_active, pending, manager_active
bot_muted_until     TIMESTAMP
no_count            INT     -- счётчик отказов
telegram_topic_id   BIGINT  -- ID топика в Telegram
last_message_at     TIMESTAMP
```

**handovers** — заявки на менеджера
```sql
id                  UUID PRIMARY KEY
conversation_id     UUID REFERENCES conversations
status              TEXT    -- pending, active, resolved
trigger_type        TEXT    -- intent, keyword, manual
trigger_value       TEXT    -- human_request, frustration
user_message        TEXT    -- сообщение клиента
manager_response    TEXT    -- ответ менеджера (для автообучения)
assigned_to         TEXT    -- telegram_id менеджера
assigned_to_name    TEXT
telegram_message_id BIGINT  -- ID сообщения с кнопками
reminder_1_sent_at  TIMESTAMP
reminder_2_sent_at  TIMESTAMP
```

---

## Qdrant (Vector Database)

### Конфигурация

| Параметр | Значение |
|----------|----------|
| Host | qdrant:6333 (внутри Docker) |
| Collection | truffles_knowledge |
| Vector size | 1024 (BGE-M3) |
| Distance | Cosine |
| API Key | ${DB_PASSWORD} |

### Структура документа

```json
{
  "id": "uuid",
  "vector": [0.1, 0.2, ...],  // 1024 dimensions
  "payload": {
    "content": "Текст чанка документа",
    "metadata": {
      "client_slug": "truffles",
      "doc_name": "faq.md",
      "source": "document",     // или "learned"
      "updated_at": "2025-12-10"
    }
  }
}
```

### RAG Pipeline

```
Вопрос пользователя
        ↓
BGE-M3: text → vector (1024 dim)
        ↓
Qdrant: поиск по cosine similarity
  - filter: client_slug = X
  - limit: 5
  - score_threshold: 0.5
        ↓
Топ-5 релевантных чанков
        ↓
Форматирование в контекст для LLM
```

**Файл:** `services/knowledge_service.py`

```python
def search_knowledge(query: str, client_slug: str, limit: int = 5):
    embedding = get_embedding(query)  # BGE-M3
    
    response = qdrant.search(
        collection_name="truffles_knowledge",
        query_vector=embedding,
        limit=limit,
        score_threshold=0.5,
        query_filter={
            "must": [
                {"key": "metadata.client_slug", "match": {"value": client_slug}}
            ]
        }
    )
    return response
```

---

## BGE-M3 (Embeddings)

### Конфигурация

| Параметр | Значение |
|----------|----------|
| Модель | BAAI/bge-m3 |
| Размерность | 1024 |
| Сервис | text-embeddings-inference |
| URL | http://bge-m3:80/embed |

### Использование

```python
def get_embedding(text: str) -> List[float]:
    response = httpx.post(
        "http://bge-m3:80/embed",
        json={"inputs": text}
    )
    return response.json()[0]
```

### Почему BGE-M3

1. **Мультиязычность** — русский, казахский, английский
2. **Self-hosted** — данные не уходят в облако
3. **Бесплатно** — нет платы за API
4. **Качество** — один из лучших open-source моделей

---

## LLM (OpenAI)

### Используемые модели

| Задача | Модель | Почему |
|--------|--------|--------|
| Классификация intent | gpt-4o-mini | Дёшево, быстро, достаточно умно |
| Генерация ответа | gpt-4o-mini | Баланс качества и стоимости |

### Конфигурация

```python
# services/ai_service.py

OPENAI_API_KEY = "sk-proj-..."
DEFAULT_MODEL = "gpt-4o-mini"
TEMPERATURE = 1.0
MAX_TOKENS = 2000
```

### Structured Outputs

Не используем. Простой текстовый ответ.

### Стоимость (оценка)

| Компонент | На 1000 сообщений |
|-----------|-------------------|
| Классификация | ~$0.50 |
| Генерация ответа | ~$1.50 |
| **Итого** | **~$2.00** |

---

# ЧАСТЬ 4: ПОТОКИ ДАННЫХ

## Входящее сообщение от клиента

```
1. WhatsApp клиент отправляет сообщение
        ↓
2. ChatFlow получает, шлёт webhook в n8n
        ↓
3. n8n 1_Webhook:
   - Парсит payload
   - POST /message в Python API
        ↓
4. Python API (message.py):
   - get_or_create_user()
   - get_or_create_conversation()
   - save_message(role="user")
   - Проверка: bot muted?
        ↓
5. intent_service.classify_intent()
   - LLM определяет: human_request? frustration? question?
        ↓
6. IF should_escalate(intent):
   - escalation_service.escalate_conversation()
   - Создать handover
   - Отправить в Telegram
   - bot_response = "Передал менеджеру..."
        ↓
   ELIF is_rejection(intent):
   - Mute бота на 30мин/24ч
   - bot_response = "Хорошо, напишите если понадоблюсь"
        ↓
   ELSE:
   - ai_service.generate_ai_response()
     - get_system_prompt()
     - search_knowledge() (RAG)
     - get_conversation_history()
     - llm.generate()
        ↓
7. save_message(role="assistant", content=bot_response)
        ↓
8. chatflow_service.send_bot_response()
        ↓
9. n8n получает ответ, отправляет в ChatFlow → WhatsApp
```

## Ответ менеджера

```
1. Менеджер пишет в Telegram топик
        ↓
2. Telegram шлёт webhook: POST /telegram-webhook
        ↓
3. telegram_webhook.py:
   - Определить: это кнопка или сообщение?
        ↓
4. IF сообщение:
   - manager_message_service.process_manager_message()
   - Найти handover по topic_id
   - Отправить в WhatsApp клиенту
   - Авто-взять заявку если pending
        ↓
5. IF кнопка [Беру]:
   - handover.status = "active"
   - conversation.state = "manager_active"
   - Обновить кнопки на [Решено]
        ↓
6. IF кнопка [Решено]:
   - handover.status = "resolved"
   - conversation.state = "bot_active"
   - Сбросить mute, no_count
   - Убрать кнопки, unpin
```

## Напоминания

```
1. Cron каждую минуту: curl POST /reminders/process
        ↓
2. reminder_service.get_pending_reminders()
   - Найти handovers со status="pending"
   - Проверить: reminder_1 нужен? (>30 мин)
   - Проверить: reminder_2 нужен? (>60 мин)
        ↓
3. Для каждого напоминания:
   - telegram_service.send_message()
   - mark_reminder_sent()
        ↓
4. Вернуть статистику: sent, failed
```

---

# ЧАСТЬ 5: DOCKER ИНФРАСТРУКТУРА

## Контейнеры

| Контейнер | Образ | Порт | Назначение |
|-----------|-------|------|------------|
| truffles-api | truffles-api | 8000 | Python API |
| truffles_postgres_1 | postgres:15-alpine | 5432 | База данных |
| truffles_qdrant_1 | qdrant/qdrant | 6333 | Vector DB |
| truffles_redis_1 | redis:7-alpine | 6379 | Кэш (для n8n) |
| truffles_n8n_1 | n8nio/n8n | 5678 | Orchestration |
| bge-m3 | text-embeddings-inference | 80 | Embeddings |
| truffles-traefik | traefik:v2.10 | 80,443 | Reverse proxy |

## Docker Compose (упрощённо)

```yaml
version: '3.8'

services:
  truffles-api:
    build: ./truffles-api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://n8n:${DB_PASSWORD}@postgres:5432/chatbot
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - postgres
      - qdrant
      - bge-m3
    restart: unless-stopped

  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=n8n
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=chatbot

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__API_KEY=${DB_PASSWORD}

  bge-m3:
    image: ghcr.io/huggingface/text-embeddings-inference:cpu-1.2
    command: --model-id BAAI/bge-m3
    volumes:
      - bge_cache:/data

  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    volumes:
      - n8n_data:/home/node/.n8n
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true

  traefik:
    image: traefik:v2.10
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./traefik:/etc/traefik

volumes:
  postgres_data:
  qdrant_data:
  bge_cache:
  n8n_data:
```

## Сеть

Все контейнеры в одной Docker network `truffles_default`.

Внутренние DNS:
- `postgres` → PostgreSQL
- `qdrant` → Qdrant
- `bge-m3` → Embeddings
- `truffles-api` → Python API

---

# ЧАСТЬ 6: ПЛАН МАСШТАБИРОВАНИЯ

## Текущее состояние (1-10 клиентов)

- Один сервер в Казахстане
- Все компоненты на одной машине
- Достаточно для старта

## Ближайшее (10-100 клиентов)

### Message Queue

```
Сейчас:
  WhatsApp → n8n → Python API (синхронно)

Нужно:
  WhatsApp → n8n → Redis Queue → Python Worker
```

**Зачем:** Не терять сообщения при пиках нагрузки.

### Connection Pooling

```
Сейчас:
  Каждый запрос = новое подключение к PostgreSQL

Нужно:
  PgBouncer между API и PostgreSQL
```

**Зачем:** Меньше накладных расходов на подключения.

### Кэширование

```python
# Кэшировать в Redis:
- prompts (меняются редко)
- client_settings (меняются редко)
- последние N сообщений (для истории)
```

## Будущее (100-10000 клиентов)

### Horizontal Scaling

```
                    ┌─────────────┐
                    │   Traefik   │
                    │   (LB)      │
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ API Pod 1   │ │ API Pod 2   │ │ API Pod 3   │
    └─────────────┘ └─────────────┘ └─────────────┘
           │               │               │
           └───────────────┼───────────────┘
                           ▼
                    ┌─────────────┐
                    │ PostgreSQL  │
                    │ (Primary)   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ PostgreSQL  │
                    │ (Replica)   │
                    └─────────────┘
```

### Kubernetes

- Helm charts для деплоя
- HPA (Horizontal Pod Autoscaler)
- Отдельные namespace для клиентов (если нужна изоляция)

### Multi-Region

- PostgreSQL с репликацией
- Qdrant cluster
- CDN для статики (если будет веб)

---

# ЧАСТЬ 7: МОНИТОРИНГ И ДИАГНОСТИКА

## Логи

| Компонент | Как смотреть |
|-----------|--------------|
| Python API | `docker logs truffles-api --tail 100` |
| PostgreSQL | `docker logs truffles_postgres_1` |
| n8n | `docker logs truffles_n8n_1` или UI |
| Qdrant | `docker logs truffles_qdrant_1` |

## Health Checks

| Endpoint | Что проверяет |
|----------|---------------|
| `GET /health` | API жив |
| `GET /db-check` | Подключение к PostgreSQL |
| Qdrant: `GET /collections` | Qdrant жив |

## Текущий мониторинг

```bash
# /home/zhan/monitor.sh — запускается по cron каждую минуту
# Проверяет /health, при ошибке шлёт в Telegram
```

## Что добавить (план)

1. **Structured logging** — JSON логи для парсинга
2. **Request ID** — для трейсинга запросов
3. **Prometheus metrics** — latency, errors, throughput
4. **Grafana dashboard** — визуализация
5. **Alertmanager** — алерты по правилам

---

# ЧАСТЬ 8: БЕЗОПАСНОСТЬ

## Текущее состояние

| Аспект | Статус |
|--------|--------|
| HTTPS | ✅ Traefik + Let's Encrypt |
| API Keys | ⚠️ В коде (нужно в env) |
| DB пароли | ⚠️ В docker-compose |
| SSH | ✅ Только по ключу |

## Что нужно сделать

1. **Secrets management** — вынести в .env или Vault
2. **Rate limiting** — защита от DDoS
3. **Input validation** — проверка входных данных
4. **Audit logs** — кто что делал

---

# ЧАСТЬ 9: ИЗВЕСТНЫЕ ОГРАНИЧЕНИЯ

| Ограничение | Последствия | Решение |
|-------------|-------------|---------|
| Один сервер | Single point of failure | Резервный сервер |
| Синхронная обработка | Потеря сообщений при пике | Message queue |
| API ключи в коде | Утечка при коммите | .env файлы |
| Нет автобэкапов | Потеря данных | Настроить pg_dump |

---

# ЧАСТЬ 10: ERROR HANDLING И RESILIENCE [ФУНДАМЕНТ]

> *Добавлено 2025-12-11. Архитектурное решение для надёжности системы.*

## Проблема

Сейчас error handling разбросан хаотично. Каждый сервис обрабатывает ошибки по-своему.

## Принцип: Клиент всегда получает ответ

Что бы ни сломалось внутри — клиент должен получить ответ. Либо полезный, либо fallback.

## Решение: Result Pattern

### Базовый класс

**Файл:** `truffles-api/app/services/result.py`

```python
from dataclasses import dataclass
from typing import Optional, TypeVar, Generic

T = TypeVar('T')

@dataclass
class Result(Generic[T]):
    ok: bool
    value: Optional[T] = None
    error: Optional[str] = None
    error_code: Optional[str] = None  # для классификации ошибок
    
    @staticmethod
    def success(value: T) -> 'Result[T]':
        return Result(ok=True, value=value)
    
    @staticmethod
    def failure(error: str, code: str = "unknown") -> 'Result[T]':
        return Result(ok=False, error=error, error_code=code)
    
    def unwrap_or(self, default: T) -> T:
        """Вернуть value или default если ошибка."""
        return self.value if self.ok else default
```

### Использование в сервисах

```python
# ai_service.py
def generate_ai_response(...) -> Result[tuple[str, str]]:
    try:
        # ... логика ...
        return Result.success((response, confidence))
    except Exception as e:
        log_error("ai_service", e)
        return Result.failure(str(e), "ai_error")

# webhook.py
result = generate_ai_response(...)
if result.ok:
    response, confidence = result.value
else:
    response = "Извините, произошла ошибка. Попробуйте позже."
    log_error("webhook", result.error)
```

### Коды ошибок

| Код | Описание | Fallback |
|-----|----------|----------|
| `ai_error` | LLM не ответил | "Ошибка, попробуйте позже" |
| `rag_error` | Qdrant недоступен | Ответить без RAG |
| `escalation_error` | Не удалось эскалировать | Ответить + лог |
| `telegram_error` | Telegram API | Retry через 5 сек |
| `db_error` | PostgreSQL | Ошибка, не сохранять |

## Graceful Degradation

Если компонент X упал — система продолжает работать с ограничениями.

```
┌─────────────────────────────────────────────────────────┐
│                    ВХОДЯЩЕЕ СООБЩЕНИЕ                    │
└─────────────────────────────┬───────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────┐
│  RAG Search                                              │
│  OK → использовать контекст                             │
│  FAIL → ответить без контекста (LLM only)               │
└─────────────────────────────┬───────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────┐
│  LLM Generate                                            │
│  OK → отправить ответ                                   │
│  FAIL → fallback: "Ошибка, попробуйте позже"           │
└─────────────────────────────┬───────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────┐
│  Escalation (если нужна)                                 │
│  OK → создать handover + уведомить                      │
│  FAIL → ответить клиенту + лог (не терять сообщение)   │
└─────────────────────────────┬───────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────┐
│  Send Response (WhatsApp)                                │
│  OK → готово                                            │
│  FAIL → retry 3 раза → лог критической ошибки          │
└─────────────────────────────────────────────────────────┘
```

## Логирование

### Уровни

| Уровень | Когда | Пример |
|---------|-------|--------|
| `DEBUG` | Детали для отладки | RAG score, LLM tokens |
| `INFO` | Нормальные события | Сообщение обработано |
| `WARNING` | Нештатная ситуация, но работаем | RAG упал, ответили без него |
| `ERROR` | Ошибка, нужно внимание | LLM не ответил |
| `CRITICAL` | Система не работает | БД недоступна |

### Формат

```python
import logging

def log_error(service: str, error: Exception, context: dict = None):
    logging.error(f"[{service}] {error}", extra={
        "service": service,
        "error_type": type(error).__name__,
        "context": context or {}
    })
```

## Инварианты системы

**Инвариант** — правило которое всегда должно быть истинным. Если нарушено — баг.

### Инварианты состояний

| Состояние | Инвариант | Constraint |
|-----------|-----------|------------|
| `bot_active` | topic_id может быть NULL | — |
| `pending` | должен быть handover со status='pending' | FK + CHECK |
| `manager_active` | topic_id NOT NULL, handover status='active' | CHECK |

### SQL Constraints

```sql
-- Добавить в миграцию
ALTER TABLE conversations ADD CONSTRAINT chk_manager_active_has_topic
    CHECK (state != 'manager_active' OR telegram_topic_id IS NOT NULL);

ALTER TABLE conversations ADD CONSTRAINT chk_pending_or_active_has_handover
    CHECK (state = 'bot_active' OR EXISTS (
        SELECT 1 FROM handovers h 
        WHERE h.conversation_id = conversations.id 
        AND h.status IN ('pending', 'active')
    ));
```

### Транзакции при смене состояния

```python
# services/state_service.py

def escalate_to_pending(db: Session, conversation: Conversation, user_message: str) -> Result:
    """Атомарный переход bot_active → pending."""
    try:
        with db.begin_nested():  # savepoint
            # 1. Создать handover
            handover = Handover(
                conversation_id=conversation.id,
                status="pending",
                user_message=user_message
            )
            db.add(handover)
            
            # 2. Создать topic
            topic_id = create_telegram_topic(...)
            if not topic_id:
                raise ValueError("Failed to create topic")
            
            # 3. Обновить conversation
            conversation.state = "pending"
            conversation.telegram_topic_id = topic_id
            
            db.flush()  # проверить constraints
        
        db.commit()
        return Result.success(handover)
        
    except Exception as e:
        db.rollback()
        return Result.failure(str(e), "escalation_failed")
```

### Self-healing (второй уровень защиты)

Если инвариант всё же нарушен — обнаружить и починить:

```python
# services/health_service.py

def check_and_heal_conversations(db: Session) -> dict:
    """Проверить инварианты и починить нарушения."""
    healed = []
    
    # Инвариант 1: manager_active должен иметь topic_id
    broken = db.query(Conversation).filter(
        Conversation.state == "manager_active",
        Conversation.telegram_topic_id == None
    ).all()
    
    for conv in broken:
        conv.state = "bot_active"
        healed.append({"id": conv.id, "issue": "manager_active_no_topic"})
    
    # Инвариант 2: pending/active должен иметь handover
    # ... аналогично
    
    db.commit()
    return {"healed": len(healed), "details": healed}
```

---

## TODO: Шаги реализации

### Фаза 1: Защита от сбоев [P0]

**Шаг 1: Result class**
- Создать `services/result.py`
- Базовый класс с success/failure

**Шаг 2: Применить к ai_service**
- `generate_ai_response` → возвращает `Result`
- Обработать в `webhook.py`

### Фаза 2: Защита от багов [P0]

**Шаг 3: SQL Constraints**
- Добавить CHECK constraints в БД
- Невалидные состояния невозможны на уровне данных

**Шаг 4: Транзакционные переходы**
- `state_service.py` — атомарные переходы состояний
- Либо всё, либо ничего

**Шаг 5: Self-healing job**
- `health_service.py` — проверка инвариантов
- Cron каждые 5 минут

### Фаза 3: Наблюдаемость [P1]

**Шаг 6: Централизованное логирование**
- Настроить logging
- Формат с context

**Шаг 7: Мониторинг**
- Алерты при нарушении инвариантов
- Dashboard здоровья системы

---

## СВЯЗЬ С ДРУГИМИ ДОКУМЕНТАМИ

| Документ | Что там |
|----------|---------|
| `TECH.md` | Доступы, команды, конкретные значения |
| `SPECS/ESCALATION.md` | Логика эскалации |
| `SPECS/CONSULTANT.md` | Поведение бота |
| `SPECS/MULTI_TENANT.md` | Multi-tenant архитектура |
| `STRATEGY/TECH_ROADMAP.md` | План развития |

---

*Создано: 2025-12-06*
*Обновлено: 2025-12-11 — добавлена ЧАСТЬ 10 (Error Handling)*
