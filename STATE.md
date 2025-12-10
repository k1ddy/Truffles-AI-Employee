# Truffles — Состояние проекта

**Обновлено: 2025-12-09**

---

## Архитектура (текущая)

```
WhatsApp → n8n (роутинг) → Python API (вся логика) → PostgreSQL
                ↓
Telegram callbacks → Python API (api.truffles.kz/telegram-webhook)
```

**n8n = только роутинг, без бизнес-логики.**

---

## Что работает

### Python сервис (truffles-api)

| Функция | Статус | Описание |
|---------|--------|----------|
| Intent Classification | ✅ | LLM (gpt-4o-mini), 7 интентов |
| Эскалация в Telegram | ✅ | Топик + кнопки + pin |
| Callback обработка | ✅ | take/resolve/skip в Python |
| Forward to Topic | ✅ | Сообщения клиента → менеджеру |
| Менеджер → Клиент | ✅ | Telegram → WhatsApp |
| Мьют логика | ✅ | 1й нет=30мин, 2й=24ч |
| State Machine | ✅ | bot_active/pending/manager_active |
| Тесты | ✅ | 62 теста (pytest) |

### Интенты
- `human_request` → эскалация
- `frustration` → эскалация
- `rejection` → мьют
- `question` → ответ бота
- `greeting`, `thanks`, `other` → ответ бота

### State Machine
```
bot_active      — бот отвечает
pending         — заявка создана, бот отвечает + forward
manager_active  — менеджер взял, бот молчит
```

---

## Инфраструктура

| Что | Значение |
|-----|----------|
| Сервер | 5.188.241.234:222 (SSH) |
| Python API | https://api.truffles.kz |
| n8n | https://n8n.truffles.kz |
| Telegram webhook | api.truffles.kz/telegram-webhook |
| Bot token | 8249719610:AAGdyGmYTM9xnD5NojlsrIA36tbDcZFnpNk |

### Docker контейнеры
- truffles-api (FastAPI)
- postgres (chatbot)
- n8n
- qdrant
- redis
- traefik (роутинг)

---

## Структура кода

```
truffles-api/app/
├── main.py
├── config.py
├── database.py
├── models/           # 8 моделей
├── schemas/          # 4 схемы
├── services/
│   ├── ai_service.py
│   ├── intent_service.py
│   ├── escalation_service.py
│   ├── telegram_service.py
│   ├── manager_message_service.py
│   ├── message_service.py
│   └── state_machine.py
└── routers/
    ├── webhook.py           # POST /webhook
    └── telegram_webhook.py  # POST /telegram-webhook
```

---

## Доступы

### SSH
```
ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234
```

### PostgreSQL
```
Host: postgres (Docker) или localhost:5432
DB: chatbot
User: n8n
Password: Iddqd777!
```

### n8n API
```
URL: https://n8n.truffles.kz
Key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## TODO

| Приоритет | Задача |
|-----------|--------|
| 🔴 High | Напоминания о незакрытых заявках (cron) |
| 🟡 Medium | История переписки в заявке для менеджера |
| 🟡 Medium | Автоприветствие менеджера |
| 🟢 Low | "Менеджер уже занимается" при повторном вопросе |
| 🟢 Low | Деактивировать n8n workflow 9_Telegram_Callback |

---

## Аналитика (данные собираются)

- `handovers.resolved_by_name` — кто решил
- `handovers.resolved_at` — когда решил
- `handovers.first_response_at` — время первого ответа
- `handovers.assigned_to_name` — кто взял

---

## Документы

| Файл | Что содержит |
|------|--------------|
| docs/PYTHON_REQUIREMENTS.md | Требования к коду, error handling |
| docs/N8N_ESCALATION_ARCHITECTURE.md | Полный flow эскалации |
| docs/SCHEMA.md | Схема БД |
| AGENTS.md | Роли, принципы работы |

---

## Чего НЕ делать

- Не добавлять логику в n8n workflows
- Не фиксить старые workflows — они deprecated
- Не спрашивать "что делать" — читай этот файл и TODO
