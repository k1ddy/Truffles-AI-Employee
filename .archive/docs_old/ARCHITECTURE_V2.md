# Архитектура Truffles v2

## Текущая проблема

Бизнес-логика размазана по 10 n8n workflows. Состояния проверяются в разных местах. Костыли (mute, no_count) вместо явной модели.

## Новая архитектура

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│  WhatsApp   │────▶│    n8n      │────▶│  Python Service │
│  Telegram   │◀────│  (роутинг)  │◀────│  (вся логика)   │
└─────────────┘     └─────────────┘     └────────┬────────┘
                                                 │
                                        ┌────────▼────────┐
                                        │   PostgreSQL    │
                                        │   (состояния)   │
                                        └─────────────────┘
```

## n8n — только роутинг

**1_Webhook:**
- Принять сообщение от WhatsApp
- Вызвать Python API: POST /webhook
- Отправить ответ в WhatsApp

**9_Telegram_Callback:**
- ⚠️ DEPRECATED — Telegram webhook теперь идёт напрямую в Python
- URL: https://api.truffles.kz/telegram-webhook

**10_Handover_Monitor:**
- Каждые 5 мин вызвать: GET /reminders
- Отправить напоминания

## Python Service — вся логика

### Endpoints

```
POST /message
  Input: phone, text, channel
  Output: response_text, action (reply/escalate/silent)

POST /callback
  Input: action (take/resolve/skip/return), handover_id, manager_id
  Output: result, next_action

GET /reminders
  Output: list of reminders to send
```

### State Machine

```
ConversationState:
  - bot_active      → бот отвечает
  - pending         → заявка создана, ждём менеджера
  - manager_active  → менеджер взял заявку
```

Переходы:
```
bot_active + "позови менеджера" → pending + создать handover
bot_active + обычное сообщение → bot_active + ответ бота

pending + новое сообщение → pending + переслать менеджеру
pending + [Беру] → manager_active
pending + [Решено] → bot_active

manager_active + новое сообщение → manager_active + переслать менеджеру
manager_active + [Решено] → bot_active
manager_active + [Вернуть боту] → bot_active
```

### Структура кода

```
truffles-service/
├── main.py              # FastAPI app
├── models/
│   ├── conversation.py  # Conversation, ConversationState
│   ├── handover.py      # Handover, HandoverStatus
│   └── message.py       # Message
├── services/
│   ├── state_machine.py # Переходы состояний
│   ├── bot.py           # Генерация ответов (LLM)
│   ├── escalation.py    # Логика эскалаций
│   └── reminder.py      # Логика напоминаний
├── api/
│   ├── message.py       # POST /message
│   ├── callback.py      # POST /callback
│   └── reminder.py      # GET /reminders
└── db/
    └── postgres.py      # SQLAlchemy models
```

## Docker

```yaml
services:
  truffles-api:
    build: ./truffles-service
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - OPENROUTER_API_KEY=...
    depends_on:
      - postgres
```

## Преимущества

1. **Явные состояния** — нет костылей, всё в state machine
2. **Тестируемость** — можно писать unit tests на Python
3. **Отладка** — логи в одном месте, не по 10 workflows
4. **Масштабируемость** — добавить канал = добавить endpoint
5. **Скорость разработки** — фичи добавляются в Python, не в JSON

## План миграции

1. Создать Python сервис с базовыми endpoints
2. Перенести state machine
3. Упростить n8n workflows до роутинга
4. Перенести генерацию ответов (LLM)
5. Перенести логику эскалаций
6. Перенести напоминания
7. Тестирование
8. Удалить старую логику из n8n

## Оценка времени

- День 1: Python сервис + state machine + POST /message
- День 2: POST /callback + GET /reminders + интеграция с n8n
- День 3: Тестирование + доработки

Итого: 2-3 дня
