# TECH — Технические данные

**Проверено: 2025-12-23**

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
| bge-m3 | text-embeddings-inference | Embeddings |
| truffles-traefik | traefik:v2.11 | Reverse proxy |

**Важно:** Инфраструктура разделена: `traefik/website` → `/home/zhan/infrastructure/docker-compose.yml`, core stack → `/home/zhan/infrastructure/docker-compose.truffles.yml` (env: `/home/zhan/infrastructure/.env`). API в проде деплоится через `/home/zhan/restart_api.sh`. В `/home/zhan/truffles-main/docker-compose.yml` — заглушка (не использовать). Ранее был кейс ошибки `KeyError: 'ContainerConfig'` на `up/build`.

---

## База данных

| Параметр | Значение |
|----------|----------|
| Контейнер | truffles_postgres_1 |
| База | chatbot |
| Пользователь | ${DB_USER} |
| Пароль | ${DB_POSTGRESDB_PASSWORD} |

### Подключение
```bash
# Из SSH
docker exec -it truffles_postgres_1 psql -U "$DB_USER" -d chatbot

# Запрос
docker exec truffles_postgres_1 psql -U "$DB_USER" -d chatbot -c 'SELECT ...'
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
| demo_salon | <CLIENT_ID> | -1003412216010 |

---

## API

| URL | Назначение |
|-----|------------|
| https://api.truffles.kz | Python API |

### Endpoints
- `POST /webhook/{client_slug}` — входящие сообщения от ChatFlow (прямой путь, preferred)
- `POST /webhook` — входящие сообщения (legacy wrapper)
- `POST /telegram-webhook` — callbacks от Telegram
- `GET /health` — проверка здоровья
- `GET /admin/health` — health/self-heal метрики
- `POST /admin/outbox/process` — обработка ACK-first очереди (admin token)
- `POST /reminders/process` — обработка напоминаний

**WhatsApp Webhook URL (ChatFlow):**
`https://api.truffles.kz/webhook/{client_slug}?webhook_secret=<SECRET>`

### Переменные окружения (API)
- `NO_RESPONSE_ALERT_MINUTES` — порог минут для алерта “вход есть — ответа нет” (default: 3).
- `OUTBOX_COALESCE_SECONDS` — тишина перед склейкой сообщений в outbox (default: 8).
- `OUTBOX_PROCESS_LIMIT` — лимит сообщений на один запуск `/admin/outbox/process` (default: 10).
- `OUTBOX_MAX_ATTEMPTS` — максимум попыток outbox перед статусом FAILED (default: 5).
- `OUTBOX_RETRY_BACKOFF_SECONDS` — базовый backoff (сек) для повторов outbox (default: 2).
- `ALERTS_ADMIN_TOKEN` — токен для admin/outbox эндпойнтов.
- `CHATFLOW_RETRY_ATTEMPTS` — количество попыток отправки в ChatFlow (default: 3).
- `CHATFLOW_RETRY_BACKOFF_SECONDS` — базовый backoff (сек) для ChatFlow (default: 0.5).

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

### Деплой API (prod)
```bash
# CI build/push → pull image
ssh -p 222 zhan@5.188.241.234 "IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main PULL_IMAGE=1 bash ~/restart_api.sh"

# Локальная сборка (fallback)
ssh -p 222 zhan@5.188.241.234 "docker build -t truffles-api_truffles-api /home/zhan/truffles-main/truffles-api"
ssh -p 222 zhan@5.188.241.234 "bash ~/restart_api.sh"
```
`restart_api.sh` поддерживает `IMAGE_NAME` и `PULL_IMAGE=1`.

### Перезапуск API (без обновления кода)
```bash
ssh -p 222 zhan@5.188.241.234 "bash ~/restart_api.sh"
```

### Запрос к БД
```bash
ssh -p 222 zhan@5.188.241.234 "docker exec truffles_postgres_1 psql -U \"$DB_USER\" -d chatbot -c 'SELECT * FROM clients'"
```

### Qdrant
```bash
ssh -p 222 zhan@5.188.241.234 "curl -s -H 'api-key: ${QDRANT_API_KEY}' 'http://localhost:6333/collections'"
```

---

## Outbox (ACK-first)

- Входящие сообщения только кладутся в outbox (`/webhook*`), обработка идёт отдельным воркером.
- Планировщик: `/etc/cron.d/truffles-outbox` (каждую минуту вызывает `POST /admin/outbox/process`).
- При ошибке отправки outbox планирует повтор с backoff (next_attempt_at) до `OUTBOX_MAX_ATTEMPTS`.
- Ручной запуск (на сервере):
```bash
TOKEN=$(/usr/bin/docker exec truffles-api /bin/sh -lc 'echo "$ALERTS_ADMIN_TOKEN"')
curl -fsS -X POST http://localhost:8000/admin/outbox/process -H "X-Admin-Token: $TOKEN"
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
UPDATE client_settings SET owner_telegram_id = '@ent3rprise' WHERE client_id = '<CLIENT_ID>';
```
