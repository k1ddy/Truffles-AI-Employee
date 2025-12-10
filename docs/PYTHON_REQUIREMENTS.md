# ТРЕБОВАНИЯ К PYTHON СЕРВИСУ

**Читай это перед написанием кода.**

---

## ЦЕЛЬ

Надёжный, тестируемый, масштабируемый сервис который:
1. Не падает от одной ошибки
2. Логирует всё для дебага
3. Имеет тесты на каждый критический путь
4. Можно развивать без страха сломать

---

## ПРИНЦИПЫ

### 1. Каждый внешний вызов — в try/catch

```python
# ПЛОХО
response = openai.chat.completions.create(...)
return response.choices[0].message.content

# ХОРОШО
try:
    response = openai.chat.completions.create(...)
    return response.choices[0].message.content
except openai.APIError as e:
    logger.error(f"OpenAI API error: {e}")
    return None
except Exception as e:
    logger.error(f"Unexpected error in AI: {e}")
    return None
```

### 2. Fallback на каждом уровне

```python
# Если AI не ответил — fallback
ai_response = generate_ai_response(message)
if ai_response is None:
    ai_response = "Извините, произошла техническая ошибка. Передаю менеджеру."
    escalate(conversation_id, reason="ai_error")
```

### 3. Логирование везде

```python
import logging

logger = logging.getLogger(__name__)

# Уровни:
logger.debug("Детали для дебага")      # Не в проде
logger.info("Важные события")          # Новое сообщение, ответ отправлен
logger.warning("Подозрительное")       # Retry, timeout
logger.error("Ошибка")                 # Exception
logger.critical("Система сломана")     # БД недоступна
```

### 4. Structured logging

```python
logger.info("Message processed", extra={
    "conversation_id": str(conversation_id),
    "phone": phone,
    "intent": intent,
    "response_time_ms": response_time
})
```

---

## АРХИТЕКТУРА СЕРВИСА

```
truffles-api/
├── app/
│   ├── main.py              # FastAPI app, endpoints
│   ├── config.py            # Настройки из env
│   ├── dependencies.py      # DB session, etc
│   │
│   ├── models/              # SQLAlchemy модели
│   │   ├── __init__.py
│   │   ├── company.py
│   │   ├── client.py
│   │   ├── branch.py
│   │   ├── user.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   └── handover.py
│   │
│   ├── schemas/             # Pydantic schemas (request/response)
│   │   ├── __init__.py
│   │   ├── message.py
│   │   ├── callback.py
│   │   └── telegram.py
│   │
│   ├── services/            # Бизнес-логика
│   │   ├── __init__.py
│   │   ├── message_service.py      # Обработка входящих
│   │   ├── ai_service.py           # OpenAI + промпты
│   │   ├── qdrant_service.py       # Knowledge base
│   │   ├── stt_service.py          # ElevenLabs STT
│   │   ├── buffer_service.py       # Redis буфер
│   │   ├── intent_service.py       # Классификация
│   │   ├── escalation_service.py   # Создание handover
│   │   ├── telegram_service.py     # Отправка в Telegram
│   │   ├── whatsapp_service.py     # Отправка в WhatsApp
│   │   └── state_machine.py        # Переходы состояний
│   │
│   ├── routers/             # API endpoints
│   │   ├── __init__.py
│   │   ├── webhook.py              # POST /webhook/{client_slug}
│   │   ├── telegram_webhook.py     # POST /telegram-webhook
│   │   ├── health.py               # GET /health
│   │   └── debug.py                # GET /debug/{phone}
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py              # Настройка логирования
│       └── errors.py               # Custom exceptions
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Fixtures
│   ├── test_message_flow.py        # Полный flow
│   ├── test_escalation.py          # Эскалация
│   ├── test_telegram.py            # Telegram callbacks
│   ├── test_ai.py                  # AI с mocks
│   └── test_error_handling.py      # Error cases
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── pytest.ini
```

---

## ENDPOINTS

### POST /webhook/{client_slug}

Входящее сообщение от WhatsApp.

**Request:**
```json
{
  "messageType": "text",
  "message": "Привет",
  "metadata": {
    "sender": "Zh.",
    "timestamp": 1764911619,
    "messageId": "3F1D0B6CB1B912F5CFC7",
    "remoteJid": "77015705555@s.whatsapp.net"
  },
  "mediaData": null
}
```

**Flow:**
1. Parse & validate
2. Дедупликация (проверить message_id в Redis)
3. Если audio → STT
4. Buffer (если первое — ждать, если нет — добавить и выйти)
5. Check handover → если active → Forward to Topic → EXIT
6. Check muted → если muted → EXIT
7. Classify intent
8. Если human_request/frustration → Escalate → EXIT
9. Generate AI response
10. Send to WhatsApp
11. Save to DB

**Response:** `{"status": "ok"}`

### POST /telegram-webhook

Входящее от Telegram (кнопки и сообщения).

**Request:** Telegram Update object

**Flow для callback_query:**
1. Parse callback_data (action_handoverId)
2. Get bot_token by chat_id
3. Switch by action:
   - take → UPDATE handover SET status='active'
   - resolve → UPDATE handover SET status='resolved', Unmute bot, Unpin
   - skip → статистика
4. Answer callback
5. Update buttons

**Flow для message:**
1. Найти conversation по topic_id
2. Найти active handover
3. Send to WhatsApp
4. Save message (role='manager')
5. Confirm "✅ Доставлено"

### GET /health

```json
{"status": "ok", "db": "ok", "redis": "ok", "qdrant": "ok"}
```

### GET /debug/{phone}

Для дебага — показать состояние клиента.

```json
{
  "phone": "77015705555",
  "conversation": {
    "id": "uuid",
    "state": "pending",
    "bot_status": "muted",
    "bot_muted_until": "2025-12-09T15:30:00Z"
  },
  "active_handover": {
    "id": "uuid",
    "status": "active",
    "assigned_to": "Жанбол"
  },
  "recent_messages": [...]
}
```

---

## ERROR HANDLING

### Уровни ошибок

| Уровень | Пример | Действие |
|---------|--------|----------|
| Recoverable | OpenAI timeout | Retry 1 раз, потом fallback |
| Graceful | Qdrant недоступен | Ответить без knowledge base |
| Critical | DB недоступна | Return 503, alert |

### Fallback responses

```python
FALLBACK_RESPONSES = {
    "ai_error": "Извините, произошла ошибка. Передаю менеджеру.",
    "no_knowledge": "К сожалению, не нашёл информацию. Уточню у коллег.",
    "telegram_error": "Не удалось отправить в Telegram. Попробуем позже.",
    "whatsapp_error": "Не удалось отправить сообщение."
}
```

### Retry policy

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def call_openai(messages):
    return openai.chat.completions.create(...)
```

### Error logging

```python
try:
    result = external_service.call()
except Exception as e:
    logger.error(
        f"Service call failed",
        extra={
            "service": "openai",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "conversation_id": conversation_id
        },
        exc_info=True  # Включить traceback
    )
    raise
```

---

## ТЕСТИРОВАНИЕ

### Что тестировать

| Категория | Тесты |
|-----------|-------|
| Happy path | Сообщение → AI ответ → WhatsApp |
| Escalation | human_request → handover создан → Telegram |
| Callbacks | take → status='active', buttons updated |
| Manager reply | Telegram message → WhatsApp |
| Errors | OpenAI down → fallback response |
| Edge cases | Empty message, long message, special chars |

### Fixtures

```python
# conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db_session():
    # In-memory SQLite для тестов
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def mock_openai(mocker):
    return mocker.patch("app.services.ai_service.openai")

@pytest.fixture
def mock_telegram(mocker):
    return mocker.patch("app.services.telegram_service.requests")
```

### Пример теста

```python
def test_message_creates_response(db_session, mock_openai, mock_telegram):
    # Arrange
    mock_openai.chat.completions.create.return_value = MockResponse(
        content="Привет! Чем могу помочь?"
    )
    
    # Act
    result = process_message(
        db=db_session,
        client_slug="truffles",
        phone="77015705555",
        message="Привет"
    )
    
    # Assert
    assert result.response is not None
    assert "Привет" in result.response
    mock_openai.chat.completions.create.assert_called_once()
```

### Тест error handling

```python
def test_ai_error_triggers_fallback(db_session, mock_openai):
    # Arrange
    mock_openai.chat.completions.create.side_effect = Exception("API Error")
    
    # Act
    result = process_message(
        db=db_session,
        client_slug="truffles",
        phone="77015705555",
        message="Привет"
    )
    
    # Assert
    assert "ошибка" in result.response.lower()
    # Проверить что создан handover с reason="ai_error"
```

---

## МОНИТОРИНГ

### Health check каждые 5 минут

```python
@app.get("/health")
async def health():
    checks = {
        "db": check_db(),
        "redis": check_redis(),
        "qdrant": check_qdrant()
    }
    
    all_ok = all(v == "ok" for v in checks.values())
    
    if not all_ok:
        logger.critical("Health check failed", extra=checks)
        # Alert в Telegram
        send_alert(f"🔴 Health check failed: {checks}")
    
    return {"status": "ok" if all_ok else "degraded", **checks}
```

### Метрики

```python
# Считать и логировать
metrics = {
    "messages_processed": 0,
    "ai_calls": 0,
    "ai_errors": 0,
    "escalations": 0,
    "avg_response_time_ms": 0
}
```

### Alerts

Отправлять в Telegram Жанболу когда:
- Health check failed
- 5+ ошибок за 5 минут
- Среднее время ответа > 10 сек

---

## КОНФИГУРАЦИЯ

### Environment variables

```bash
# Database
DATABASE_URL=postgresql://n8n:Iddqd777!@postgres:5432/chatbot

# Redis
REDIS_URL=redis://redis:6379/0

# OpenAI
OPENAI_API_KEY=sk-...

# ElevenLabs (STT)
ELEVENLABS_API_KEY=...

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
QDRANT_API_KEY=Iddqd777!

# ChatFlow (WhatsApp)
CHATFLOW_TOKEN=eyJ...
CHATFLOW_URL=https://app.chatflow.kz/api/v1/send-text

# Telegram
TELEGRAM_BOT_TOKEN=8045341599:AAGY1vnqoebErB7Ki5iAqHusgLqf9WwA5m4

# App
DEBUG=false
LOG_LEVEL=INFO
BUFFER_WAIT_SECONDS=5
```

### Config class

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://redis:6379/0"
    openai_api_key: str
    elevenlabs_api_key: str | None = None
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_api_key: str
    chatflow_token: str
    chatflow_url: str = "https://app.chatflow.kz/api/v1/send-text"
    telegram_bot_token: str
    debug: bool = False
    log_level: str = "INFO"
    buffer_wait_seconds: int = 5
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

## CHECKLIST ПЕРЕД ДЕПЛОЕМ

- [ ] Все тесты проходят
- [ ] Логирование настроено
- [ ] Error handling на всех внешних вызовах
- [ ] Fallback responses определены
- [ ] Health check работает
- [ ] Env variables заданы
- [ ] Docker build успешен
- [ ] Подключение к БД работает
- [ ] Подключение к Redis работает
- [ ] Подключение к Qdrant работает
- [ ] OpenAI отвечает
- [ ] Telegram webhook настроен
- [ ] WhatsApp отправка работает

---

## ПРИОРИТЕТ РЕАЛИЗАЦИИ

### Этап 1: Базовый flow (без буфера и STT)
1. POST /webhook/{client_slug} — минимальный flow
2. AI response (OpenAI + промпт из БД)
3. Knowledge base (Qdrant)
4. Send to WhatsApp
5. Error handling + logging
6. Тесты

### Этап 2: Эскалация
1. Check handover early → Forward to Topic
2. Intent classification → escalate
3. Create handover
4. Send to Telegram (создать топик если нет, кнопки, pin)
5. POST /telegram-webhook (callbacks + messages)
6. Тесты

### Этап 3: Buffer и STT
1. Redis buffer
2. ElevenLabs STT
3. Turn detection (эвристики, можно без LLM)
4. Тесты

### Этап 4: Надёжность
1. Health checks
2. Alerts
3. Retry policies
4. Метрики
5. Тесты error cases

---

## ССЫЛКИ

- **Архитектура n8n:** `docs/N8N_ESCALATION_ARCHITECTURE.md`
- **Схема БД:** `docs/SCHEMA.md`
- **План проекта:** `MASTER_PLAN.md`
- **Текущее состояние:** `STATE.md`
