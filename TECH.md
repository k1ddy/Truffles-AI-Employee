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
| truffles-outbox | truffles-api_truffles-api | Outbox worker (ACK-first delivery) |
| truffles-sentinel | truffles-api_truffles-api | Sentinel worker (health/self-heal) |
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
- `GET /media/{path}` — выдача локально сохранённого медиа по подписи
- `GET /health` — проверка здоровья
- `GET /admin/health` — health/self-heal метрики
- `POST /admin/outbox/process` — обработка ACK-first очереди (admin token)
- `POST /admin/media/cleanup` — TTL‑очистка `/home/zhan/truffles-media` (admin token)
- `POST /reminders/process` — обработка напоминаний

**WhatsApp Webhook URL (ChatFlow):**
`https://api.truffles.kz/webhook/{client_slug}?webhook_secret=<SECRET>`

**Inbound verification (ChatFlow):**
- Реальный inbound = WA‑сообщение клиента → ChatFlow → `/webhook/{client_slug}`; `send-text` — outbound и не создаёт inbound.
- POST на `/webhook` без WA‑клиента = симуляция (использовать только если DoD это допускает).
- В БД поле называется `messages.metadata` (JSONB), не `message_metadata`.
- `instanceId` в webhook — это routing‑token, который мы задаём в URL/metadata; provider‑ID ChatFlow не используем.

### Переменные окружения (API)
- `NO_RESPONSE_ALERT_MINUTES` — порог минут для алерта “вход есть — ответа нет” (default: 3).
- `OUTBOX_COALESCE_SECONDS` — тишина перед склейкой сообщений в outbox (default: 8).
- `OUTBOX_MAX_WAIT_SECONDS` — максимум ожидания до принудительной обработки outbox (default: 10).
- `OUTBOX_PROCESS_LIMIT` — лимит сообщений на один запуск `/admin/outbox/process` (default: 10).
- `OUTBOX_MAX_ATTEMPTS` — максимум попыток outbox перед статусом FAILED (default: 5).
- `OUTBOX_RETRY_BACKOFF_SECONDS` — базовый backoff (сек) для повторов outbox (default: 2).
- `OUTBOX_STALE_PROCESSING_SECONDS` — через сколько секунд PROCESSING считается зависшим и переходит обратно в очередь (default: 120).
- `ALERTS_ADMIN_TOKEN` — токен для admin/outbox эндпойнтов.
- `CHATFLOW_RETRY_ATTEMPTS` — количество попыток отправки в ChatFlow (default: 3).
- `CHATFLOW_RETRY_BACKOFF_SECONDS` — базовый backoff (сек) для ChatFlow (default: 0.5).
- `CHATFLOW_MEDIA_BASE_URL` — базовый URL ChatFlow media API (default: https://app.chatflow.kz/api/v1).
- `PUBLIC_BASE_URL` — публичный base URL API для signed media (default: http://localhost:8000).
- `MEDIA_SIGNING_SECRET` — секрет подписи для `/media/*` (обязателен в проде).
- `MEDIA_URL_TTL_SECONDS` — TTL подписи для `/media/*` (default: 3600).
- `MEDIA_STORAGE_DIR` — базовый каталог медиа (default: /home/zhan/truffles-media).
- `MEDIA_CLEANUP_TTL_DAYS` — TTL очистки локальных медиа (default: 7).
- `MEDIA_STORAGE_WARN_BYTES` — порог алерта по объёму (default: 5GB).
- `QDRANT_COLLECTION` — коллекция Qdrant (default: truffles_knowledge; при `TEST_MODE=1` и пустом env → truffles_knowledge_ci).
- `AUDIO_TRANSCRIPTION_ENABLED` — включить транскрибацию коротких голосовых (default: false).
- `AUDIO_TRANSCRIPTION_MAX_MB` — максимум размера голосового для транскрипции (default: 2).
- `AUDIO_TRANSCRIPTION_MODEL` — модель транскрипции (default: whisper-1).
- `AUDIO_TRANSCRIPTION_LANGUAGE` — язык транскрипции (например: ru).

---

## Quality toolchain (OSS стандарт)

**Цель:** повторяемые проверки без “самописных” велосипедов.

**Инструменты (принятый стандарт):**
- **Schemathesis** — contract/fuzz по OpenAPI.
- **Hypothesis** — property‑based инварианты логики.
- **k6** — load/soak (контейнер).
- **OpenTelemetry + Prometheus + Grafana + Loki/Tempo** — наблюдаемость.

**Примечание:** интеграция инструментов делается через Task Package и фиксируется evidence в `STATE.md`.

---

## CI / GitHub Actions (как запускать, зачем и когда)

**Источник правды:** `.github/workflows/ci.yml`.

### Когда CI запускается
- **Pull Request → main:** lint + unit + core‑eval (если затронуты L1‑пути). long/asr только при L2‑изменениях или label `run-long`. build/push/deploy/livecheck не выполняются.
- **Push → main:** полный пайплайн (lint/unit/core/long/asr → build-push → deploy → ci-livecheck), если гейты позволяют.
- **workflow_dispatch:** ручной запуск с опциями `run_long` и `run_livecheck`.

### Почему этапы пропускаются (skipped)
**Path filters (changes):**
- L1 включает: `truffles-api/app/**`, `truffles-api/tests/**`, `knowledge/**`, `ops/**`, `.github/workflows/**`.
  - Нет L1‑изменений → `core-eval` skip.
- L2 включает: `truffles-api/app/knowledge/**/EVAL.yaml`, `truffles-api/app/knowledge/**/SALON_TRUTH.yaml`, `truffles-api/tests/test_demo_salon_eval.py`.
  - Нет L2‑изменений → `long-eval` и `asr-eval` skip.
**Doc‑only fast lane:**
- Изменения в `SPECS/**`, `STRATEGY/**`, `docs/**`, `AGENTS.md`, `STRUCTURE.md`, `TECH.md`, `STATE.md` не считаются L1 → `core-eval` skip.
- На main build/deploy/livecheck запускаются только если `deploy_required=true` (код/рантайм), иначе пропускаются.
- Отдельно: правки `STATE.md` не запускают deploy/livecheck и не требуют `core-eval` (если нет других L1 изменений).
 - При doc‑only deploy/ci-livecheck job полностью пропускаются (не просто “skipped” шаги).

**deploy_required (точный список путей):**
- `truffles-api/app/**`
- `truffles-api/requirements.txt`
- `truffles-api/Dockerfile`
- `knowledge/**`

**livecheck_required (точный список путей):**
- `truffles-api/app/**`
- `truffles-api/requirements.txt`
- `truffles-api/Dockerfile`
- `knowledge/**`
- `ops/**`
- `.github/workflows/**`

**Event gate (PR vs main):**
- На PR `build-push`, `deploy`, `ci-livecheck` всегда skip.
- На main эти шаги выполняются только при успешных обязательных джобах (lint/unit/secret-scan + core/long/asr, если они не skipped).

### Как форсировать проверки
- **long/asr:** label `run-long` на PR или `workflow_dispatch` с `run_long=true`.
- **ci-livecheck:** только на `main` и только если `deploy` сработал; на `workflow_dispatch` нужно `run_livecheck=true`.

### CI livecheck параллелизм
- **Матрица групп:** `ci-livecheck` запускается в 4 параллельных группах (`pool-a/b/c/d`), каждая гоняет свой набор suite‑ов.
- **Требование к allowlist:** желательно минимум 4 JID в `OUTBOUND_ALLOWLIST_JIDS`; если меньше — фиксируется `ALLOWLIST_TOO_SHORT` и включается fallback.
- **Артефакты:** на группу отдельные `livecheck-artifacts-<group>` и `livecheck-evidence-<group>.md`.
- **Fallback:** если allowlist < 4, `pool-a` запускает все suite последовательно, `pool-b/c/d` пропускаются.

### Livecheck-only (быстрый rerun без полного CI)
- **Когда:** если `ci-livecheck` красный и нужно проверить фикс без повторного lint/unit/build/deploy.
- **Как запустить:** GitHub → Actions → `Livecheck Only` → Run workflow.
  - `expected_commit` = SHA, который уже задеплоен (если пусто — проверяется только `/admin/version`).
  - `expected_version` = `main` (по умолчанию).
  - `min_allowlist_jids` = 4 (должны быть 4 JID в allowlist для параллели).
- **Что делает:** проверяет `/admin/version`, затем гоняет только livecheck suites (4 параллельных пула).
- **Что НЕ делает:** не запускает lint/unit/core/long/asr и не деплоит.
- **Fallback:** если allowlist меньше `min_allowlist_jids`, запускается один пул (`pool-a`) с полным набором suites.

### Гейты build/deploy/livecheck (важно понимать)
- `build-push` запускается только на `main` или `workflow_dispatch`, и только если lint/unit/secret-scan ok.
- `deploy` внутри себя решает `deployed=true/false` (PR и не‑main → false).
- `ci-livecheck` job всегда виден, но шаги выполняются только если `deploy` прошёл и событие допустимо.

### Concurrency (почему бывают cancelled)
- Для не‑main включён `cancel-in-progress`, поэтому новый PR‑пуш отменяет предыдущие run’ы. Это нормально.

### Быстрый рецепт
- **Док‑изменения без поведения:** PR → проверяем lint/unit; остальные этапы будут skipped — это ожидаемо.
- **Изменение поведения:** merge в main → полный CI + deploy + livecheck.
- **Нужен полный прогон без мержа:** `workflow_dispatch` на `main` с `run_long`/`run_livecheck` (если есть доступ и гейты позволяют).
- **Live‑check sender‑only:** используйте `clean_auto` как отправителя (ChatFlow send‑text) → receiver‑номер салона; если написать на `clean_auto`, ответа не будет. Подробности — `SPECS/SYSTEM_REFERENCE.md` §4.3.

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
ssh -p 222 zhan@5.188.241.234 "IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main PULL_IMAGE=1 REQUIRE_GHCR=1 VERIFY_VERSION=1 EXPECTED_GIT_COMMIT=<sha> EXPECTED_VERSION=main bash ~/restart_api.sh"

# Локальная сборка (fallback)
ssh -p 222 zhan@5.188.241.234 "docker build -t truffles-api_truffles-api /home/zhan/truffles-main/truffles-api"
ssh -p 222 zhan@5.188.241.234 "bash ~/restart_api.sh"
```
`restart_api.sh` поддерживает `IMAGE_NAME`, `PULL_IMAGE=1`, `REQUIRE_GHCR=1`, `VERIFY_VERSION=1`, `EXPECTED_GIT_COMMIT`, `EXPECTED_VERSION`.

### Перезапуск API (без обновления кода)
```bash
ssh -p 222 zhan@5.188.241.234 "bash ~/restart_api.sh"
```
**Важно:** воркеры (`truffles-outbox`, `truffles-sentinel`) запускаются отдельно; `restart_api.sh` их не перезапускает.
```bash
ssh -p 222 zhan@5.188.241.234 "docker restart truffles-outbox truffles-sentinel"
```
Или через скрипт:
```bash
ssh -p 222 zhan@5.188.241.234 "ENV_FILE=/home/zhan/truffles-main/truffles-api/.env bash /home/zhan/truffles-main/scripts/restart_workers.sh"
```

### Запрос к БД
```bash
ssh -p 222 zhan@5.188.241.234 "docker exec truffles_postgres_1 psql -U \"$DB_USER\" -d chatbot -c 'SELECT * FROM clients'"
```

### Qdrant
```bash
ssh -p 222 zhan@5.188.241.234 "curl -s -H 'api-key: ${QDRANT_API_KEY}' 'http://localhost:6333/collections'"
```

### Knowledge update (packs)
- SOP и шаги: `SPECS/SYSTEM_REFERENCE.md` → раздел **4.1 Knowledge update SOP**.
- Важно: использовать `python3`, затем build+restart (без `docker cp`).

---

## Outbox (ACK-first)

- Входящие сообщения только кладутся в outbox (`/webhook*`), обработка идёт отдельным воркером.
- Основной путь: контейнер `truffles-outbox` (loop + backoff).
- Fallback: `/etc/cron.d/truffles-outbox` может вызывать `POST /admin/outbox/process`.
- При ошибке отправки outbox планирует повтор с backoff (next_attempt_at) до `OUTBOX_MAX_ATTEMPTS`.
- Зависшие `PROCESSING` (старше `OUTBOX_STALE_PROCESSING_SECONDS`) переводятся обратно в `PENDING` или в `FAILED` при исчерпании попыток.
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
