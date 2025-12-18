# TECH — Технические данные

**Проверено: 2025-12-10**

---

## Сервер

| Параметр | Значение |
|----------|----------|
| IP | 5.188.241.234 |
| SSH порт | 222 |
| Пользователь | zhan |
| SSH команда | `ssh -i C:\Users\user\.ssh\id_rsa -p 222 zhan@5.188.241.234` |

---

## Docker контейнеры

| Имя | Образ | Назначение |
|-----|-------|------------|
| truffles-api | truffles-api_truffles-api | Python API (FastAPI) |
| truffles_postgres_1 | postgres:15-alpine | PostgreSQL |
| truffles_redis_1 | redis:7-alpine | Redis |
| truffles_qdrant_1 | qdrant/qdrant:latest | Vector DB |
| truffles_n8n_1 | n8nio/n8n:latest | n8n (роутинг) |
| bge-m3 | text-embeddings-inference | Embeddings |
| truffles-traefik | traefik:v2.10 | Reverse proxy |

---

## База данных

| Параметр | Значение |
|----------|----------|
| Контейнер | truffles_postgres_1 |
| База | chatbot |
| Пользователь | n8n |
| Пароль | ${DB_PASSWORD} |

### Подключение
```bash
# Из SSH
docker exec -it truffles_postgres_1 psql -U n8n -d chatbot

# Запрос
docker exec truffles_postgres_1 psql -U n8n -d chatbot -c 'SELECT ...'
```

### Таблицы (ключевые)
- clients — клиенты (компании)
- client_settings — настройки клиента
- users — пользователи (телефоны)
- conversations — диалоги
- messages — сообщения
- handovers — заявки на менеджера
- prompts — промпты для AI

---

## Клиенты

| name | client_id | telegram_chat_id |
|------|-----------|------------------|
| truffles | 499e4744-5e7f-4a97-8466-56ff2cdcf587 | -1003362579990 |
| demo_salon | c839d5dd-65be-4733-a5d2-72c9f70707f0 | -1003412216010 |

---

## API

| URL | Назначение |
|-----|------------|
| https://api.truffles.kz | Python API |
| https://n8n.truffles.kz | n8n интерфейс |

### Endpoints
- `POST /webhook` — входящие сообщения от n8n
- `POST /telegram-webhook` — callbacks от Telegram
- `GET /health` — проверка здоровья
- `POST /reminders/process` — обработка напоминаний

### Переменные окружения (API)
- `NO_RESPONSE_ALERT_MINUTES` — порог минут для алерта “вход есть — ответа нет” (default: 3).

---

## Telegram

| Клиент | Bot username | Bot token |
|--------|--------------|-----------|
| truffles | @truffles_kz_bot | 8045341599:AAGY... |
| demo_salon | @salon_mira_bot | 8249719610:AAGd... |

Webhook URL: `https://api.truffles.kz/telegram-webhook`

---

## Полезные команды

### Логи API
```bash
ssh -p 222 zhan@5.188.241.234 "docker logs truffles-api --tail 100"
```

### Перезапуск API
```bash
ssh -p 222 zhan@5.188.241.234 "docker restart truffles-api"
```

### Запрос к БД
```bash
ssh -p 222 zhan@5.188.241.234 "docker exec truffles_postgres_1 psql -U n8n -d chatbot -c 'SELECT * FROM clients'"
```

### Qdrant
```bash
ssh -p 222 zhan@5.188.241.234 "curl -s -H 'api-key: ${DB_PASSWORD}' 'http://localhost:6333/collections'"
```

---

## Миграции (ожидают выполнения)

### add_reminder_settings.sql
```sql
ALTER TABLE client_settings 
ADD COLUMN IF NOT EXISTS enable_reminders BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS enable_owner_escalation BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS mute_duration_first_minutes INTEGER DEFAULT 30,
ADD COLUMN IF NOT EXISTS mute_duration_second_hours INTEGER DEFAULT 24;
```

После выполнения — обновить owner_telegram_id:
```sql
UPDATE client_settings SET owner_telegram_id = '@ent3rprise' WHERE client_id = '499e4744-5e7f-4a97-8466-56ff2cdcf587';
```
