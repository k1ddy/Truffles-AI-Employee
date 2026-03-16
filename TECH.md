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

## Перед SSH: проверка окружения

Если `pwd` = `/home/zhan/truffles-main` и public IP совпадает с IP выше — ты уже на проде, SSH не нужен.

Быстрая проверка:
```bash
hostname; whoami; pwd; curl -s https://ifconfig.me
```

---

## Docker контейнеры

| Имя | Образ | Назначение |
|-----|-------|------------|
| truffles-api | truffles-api_truffles-api | Python API (FastAPI) |
| truffles-outbox | truffles-api_truffles-api | Outbox worker (ACK-first delivery) |
| truffles-outbox-service | truffles-api_truffles-api | Outbox service (shadow) |
| truffles-sentinel | truffles-api_truffles-api | Sentinel worker (health/self-heal) |
| truffles-knowledge-gateway | truffles-api_truffles-api | Knowledge snapshot gateway (shadow) |
| truffles_postgres_1 | postgres:15-alpine | PostgreSQL |
| truffles_redis_1 | redis:7-alpine | Redis |
| truffles_qdrant_1 | qdrant/qdrant:latest | Vector DB |
| bge-m3 | text-embeddings-inference | Embeddings |
| truffles-traefik | traefik:v2.11 | Reverse proxy |

**Важно:** Инфраструктура разделена: `traefik/website` → `/home/zhan/infrastructure/docker-compose.yml`, core stack → `/home/zhan/infrastructure/docker-compose.truffles.yml` (env: `/home/zhan/infrastructure/.env`). Прод релиз выполняется через `/home/zhan/truffles-main/scripts/restart_release.sh` (внутри вызывает `restart_api.sh` + `restart_workers.sh`, а при `RESTART_KNOWLEDGE_ACTIVATION_SERVICE=1` ещё и `restart_knowledge_activation_service.sh` + activation canary guard). В `/home/zhan/truffles-main/docker-compose.yml` — заглушка (не использовать). Ранее был кейс ошибки `KeyError: 'ContainerConfig'` на `up/build`.

---

## База данных

| Параметр | Значение |
|----------|----------|
| Контейнер | truffles_postgres_1 |
| База | chatbot |
| Пользователь | ${DB_USER} |
| Пароль | ${DB_POSTGRESDB_PASSWORD} |

**Где брать креды:** на проде источник истины — `/home/zhan/infrastructure/.env` (переменные `DB_POSTGRESDB_USER`, `DB_POSTGRESDB_PASSWORD`).  
В `truffles-api/.env` `DB_USER` может отсутствовать — используйте значения из infra env.

### Подключение
```bash
# Из SSH
docker exec -it truffles_postgres_1 psql -U "$DB_USER" -d chatbot

# Запрос
docker exec truffles_postgres_1 psql -U "$DB_USER" -d chatbot -c 'SELECT ...'
```

### Таблицы (ключевые)
- clients, companies, branches — орг‑структура/тенант
- agents, agent_memberships — роли доступа в консоли
- client_settings — настройки клиента
- users, conversations, messages — ядро диалогов
- handovers — заявки на менеджера
- outbox_messages — ACK‑first доставка
- audit_events — аудит действий консоли
- console_idempotency_keys — идемпотентность console API
- metrics_daily — агрегированные метрики

Полный список таблиц и дата актуализации — `docs/IMPERIUM_CONTEXT.yaml`.

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
- `GET /admin/metrics` — чтение дневных метрик (admin token)
- `POST /admin/metrics/snapshot` — запуск snapshot метрик (admin token)
- `POST /admin/media/cleanup` — TTL‑очистка `/home/zhan/truffles-media` (admin token)
- `POST /reminders/process` — обработка напоминаний

### Knowledge Gateway (shadow, internal)
- URL: `http://127.0.0.1:8010`
- `GET /health` — статус сервиса
- `POST /knowledge/snapshot` — выдача snapshot (требует `KNOWLEDGE_SNAPSHOT_ENABLED=1`)

### Outbox Service (shadow, internal)
- URL: `http://127.0.0.1:8014`
- `GET /health` — статус сервиса
- `POST /outbox/process` — обработка outbox (требует `OUTBOX_SERVICE_ENABLED=1`)

### Knowledge Activation Service (shadow, internal)
- URL: `http://127.0.0.1:8015`
- `GET /health` — статус сервиса
- `POST /knowledge-activation/process` — direct processing of `knowledge_activation_jobs` (требует `KNOWLEDGE_ACTIVATION_SERVICE_ENABLED=1`)

### Provider Gateway (shadow, internal)
- URL: `http://127.0.0.1:8011`
- `GET /health` — статус сервиса
- `POST /provider/inbound` — входящие от провайдера (требует `PROVIDER_GATEWAY_INBOUND_ENABLED=1`)
- `POST /provider/status` — статус доставки (требует `PROVIDER_GATEWAY_STATUS_ENABLED=1`)

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
- `OUTBOX_SERVICE_ENABLED` — включает `POST /outbox/process` (shadow сервис).
- `KNOWLEDGE_ACTIVATION_HEALTH_QUEUED_WARNING` / `KNOWLEDGE_ACTIVATION_HEALTH_QUEUED_CRITICAL` — пороги для queued activation jobs в health/alerts/metrics.
- `KNOWLEDGE_ACTIVATION_HEALTH_FAILED_24H_WARNING` / `KNOWLEDGE_ACTIVATION_HEALTH_FAILED_24H_CRITICAL` — пороги для failed|stuck activation jobs за 24ч.
- `KNOWLEDGE_ACTIVATION_HEALTH_STUCK_WARNING` / `KNOWLEDGE_ACTIVATION_HEALTH_STUCK_CRITICAL` — пороги для stuck activation jobs.
- `KNOWLEDGE_ACTIVATION_HEALTH_OLDEST_QUEUED_WARNING_SECONDS` / `KNOWLEDGE_ACTIVATION_HEALTH_OLDEST_QUEUED_CRITICAL_SECONDS` — пороги возраста старейшей queued activation job.
- `OUTBOX_SERVICE_TOKEN` — токен для outbox service (header `X-Outbox-Service-Token`).
- `WEBHOOK_PIPELINE_BUDGET_MS` — бюджет (мс) для /webhook пайплайна (LLM/RAG gating) (default: 7000).
- `CONSOLE_IDEMPOTENCY_TTL_SECONDS` — TTL незавершённых console idempotency ключей (default: 600).
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
- `PROVIDER_GATEWAY_INBOUND_ENABLED` — включает `POST /provider/inbound` (global).
- `PROVIDER_GATEWAY_INBOX_ENABLED` — пишет `inbox_events` для provider inbound.
- `PROVIDER_GATEWAY_INBOX_REQUIRED` — если `1`, inbound отвечает ошибкой при сбое записи `inbox_events`.
- `PROVIDER_GATEWAY_STATUS_ENABLED` — включает `POST /provider/status`.
- `PROVIDER_GATEWAY_OUTBOUND_ENABLED` — отправка outbox через Provider Gateway (global; требует `PROVIDER_GATEWAY_OUTBOUND_URL`).
- `PROVIDER_GATEWAY_OUTBOUND_URL` — URL provider gateway outbound endpoint.
- `PROVIDER_GATEWAY_STATUS_CALLBACK_URL` — callback URL для статусов отправки.
- `PROVIDER_GATEWAY_TOKEN` — токен для inbound/outbound/status.
- `INBOX_SERVICE_ENABLED` — включает `POST /inbox/event` (shadow inbox service).
- `INBOX_SERVICE_TOKEN` — токен для inbox service (header `X-Inbox-Service-Token`).
- `DECISION_CORE_ENABLED` — включает `POST /decision/handle` (shadow decision core).
- `DECISION_CORE_TOKEN` — токен для decision core (header `X-Decision-Core-Token`).
- `QDRANT_COLLECTION` — коллекция Qdrant (default: truffles_knowledge; при `TEST_MODE=1` и пустом env → truffles_knowledge_ci).
- `KNOWLEDGE_SNAPSHOT_ENABLED` — включает `/knowledge/snapshot` (gateway service).
- `KNOWLEDGE_SNAPSHOT_TOKEN` — токен для gateway snapshot (header `X-Knowledge-Snapshot-Token`).
- `KNOWLEDGE_SNAPSHOT_TTL_SECONDS` — TTL snapshot (сек).
- `KNOWLEDGE_SNAPSHOT_HMAC_KEY` — HMAC‑секрет подписи snapshot.
- `KNOWLEDGE_SNAPSHOT_KEY_ID` — key id для подписи snapshot (optional).
- `KNOWLEDGE_SNAPSHOT_CONSUMER_ENABLED` — включает shadow-consumer для consult snapshot (default: false).
- `KNOWLEDGE_SNAPSHOT_CONSULT_MODE` — режим consult snapshot: `shadow|fallback|strict` (default: shadow).
- `KNOWLEDGE_SNAPSHOT_CONSULT_ALLOWLIST` — список `client_slug` для canary/cutover (через запятую).
- `BOOKING_CONFIRM_ENABLED` — включить LLM-first slot_extract + booking_confirm (default: false).
- `BOOKING_CONFIRM_CONFIDENCE_THRESHOLD` — порог уверенности для подтверждения слота (default: 0.9).
- `CALENDAR_TOKEN_ENC_KEY` — ключ pgcrypto для шифрования OAuth токенов календаря (обязателен после включения sync).
- `CALENDAR_SYNC_INBOUND_ENABLED` — включает расписание inbound sync через outbox (default: true).
- `CALENDAR_SYNC_INBOUND_INTERVAL_SECONDS` — минимальный интервал inbound sync на branch (default: max(60, `CALENDAR_SYNC_STALE_SECONDS`/2), либо 300 при `CALENDAR_SYNC_STALE_SECONDS=0`).
- `CALENDAR_SYNC_STALE_SECONDS` — порог staleness для health gate (default: 900).
- `CALENDAR_SYNC_LOOKBACK_DAYS` — глубина lookback для inbound sync (default: 14).
- `CALENDAR_SYNC_LOOKAHEAD_DAYS` — глубина lookahead для inbound sync (default: 60).
- `METRICS_DAILY_AUTO_ENABLED` — включает ежедневный snapshot metrics_daily (default: false).
- `METRICS_DAILY_RUN_HOUR_UTC` — час запуска (UTC) для snapshot (default: 1).
- `METRICS_DAILY_RUN_MINUTE_UTC` — минута запуска (UTC) для snapshot (default: 5).
- `METRICS_DAILY_TARGET_OFFSET_DAYS` — на сколько дней назад считать (default: 1).
- `METRICS_DAILY_STATUS_ALLOWLIST` — allowlist `client.status` (default: active, `all` = без фильтра).
- `METRICS_DAILY_RETRY_SECONDS` — backoff при ошибке snapshot (сек, default: 600).
- `METRICS_DAILY_RETRY_MAX` — максимум повторов snapshot за день (default: 3).
- `METRICS_DAILY_BACKFILL_MAX_DAYS` — лимит backfill дней для `/admin/metrics/snapshot` (default: 31).
- `AUDIO_TRANSCRIPTION_ENABLED` — включить транскрибацию коротких голосовых (default: false).
- `AUDIO_TRANSCRIPTION_MAX_MB` — максимум размера голосового для транскрипции (default: 2).
- `AUDIO_TRANSCRIPTION_MODEL` — модель транскрипции (default: whisper-1).
- `AUDIO_TRANSCRIPTION_LANGUAGE` — язык транскрипции (например: ru).

---

## Console Web + Keycloak (Control Plane)

**Домены:**
- `https://console.truffles.kz` — Console UI
- `https://auth.truffles.kz` — Keycloak (OIDC)

**Где живёт конфигурация:**
- `docker-compose.console.yml` — Keycloak + console‑postgres + console‑redis (Traefik routing).
- `truffles-api/docker-compose.yml` — сервис `console-web` (Traefik routing).
- `console-web/.env.local` — `NEXTAUTH_URL`, `KEYCLOAK_ISSUER`, `NEXT_PUBLIC_API_URL`.
- `truffles-api/docker-compose.yml` — `CONSOLE_OIDC_JWKS_URL`, `CONSOLE_OIDC_ISSUER`, `CONSOLE_OIDC_AUDIENCE`.

**Данные и источники:**
- Console API читает/пишет **core DB** (`DATABASE_URL` в `truffles-api`, контейнер `truffles_postgres_1`, БД `chatbot`).
- `console-postgres` в `docker-compose.console.yml` сейчас не используется Console API (резерв под будущие нужды).

**Secrets (локально, не в git):**
- `/home/zhan/secrets/console-contract.env` → `CONSOLE_API_TOKEN` для Schemathesis/k6.
- `/home/zhan/secrets/console-e2e.env` → креды Playwright.

**Console tenancy (interim):**
- `/console/v1/me` возвращает список `clients` и `selection_required`.
- При нескольких клиентах обязателен `X-Client-Id`.
- UI хранит выбор в `localStorage` (`console:client_id`) и очищает на logout.
- Полный орг‑уровень (Company/Client/Branch) — DEC‑011, в разработке.

**Запуск (docker‑вариант, preferred):**
```bash
docker compose -f /home/zhan/truffles-main/docker-compose.console.yml up -d console-postgres console-redis console-keycloak
GIT_COMMIT=$(git -C /home/zhan/truffles-main rev-parse HEAD) \
BUILD_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  docker compose -f /home/zhan/truffles-main/truffles-api/docker-compose.yml up -d console-web
```

**Console Web restart (build info wired):**
```bash
/home/zhan/truffles-main/scripts/restart_console_web.sh
```

**Legacy (если console‑web ещё на PM2):**
- см. `docs/DEPLOYMENT_RUNBOOK.md` (раздел PM2).

---

## Calendar Scheduling (SoT) — доступы и шаги

**Env (API):**
- Файл: `/home/zhan/truffles-main/truffles-api/.env`
- Обязательно: `CALENDAR_TOKEN_ENC_KEY` (32+ bytes random, хранить как секрет).
- OAuth: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`.

**Миграция схемы (Phase 1):**
```bash
set -a
source /home/zhan/infrastructure/.env
set +a
docker exec -e PGPASSWORD="$DB_POSTGRESDB_PASSWORD" -i truffles_postgres_1 \\
  psql -U "$DB_POSTGRESDB_USER" -d chatbot < /home/zhan/truffles-main/truffles-api/migrations/009_add_calendar_scheduling.sql
```

**Проверка:**
```bash
docker exec -i truffles_postgres_1 psql -U "$DB_POSTGRESDB_USER" -d chatbot -c \"\\dt appointments\"
docker exec -i truffles_postgres_1 psql -U "$DB_POSTGRESDB_USER" -d chatbot -c \"\\dt calendar_blocks\"
```

**Backfill legacy bookings → appointments (Phase 3):**
```bash
set -a
source /home/zhan/infrastructure/.env
set +a
docker exec -e PGPASSWORD="$DB_POSTGRESDB_PASSWORD" -i truffles_postgres_1 \\
  psql -U "$DB_POSTGRESDB_USER" -d chatbot < /home/zhan/truffles-main/truffles-api/migrations/010_backfill_appointments_from_bookings.sql
```

**Backfill tokens (pgcrypto):**
```bash
set -a
source /home/zhan/truffles-main/truffles-api/.env
source /home/zhan/infrastructure/.env
set +a
docker exec -e PGPASSWORD="$DB_POSTGRESDB_PASSWORD" -i truffles_postgres_1 \\
  psql -U "$DB_POSTGRESDB_USER" -d chatbot -v key="$CALENDAR_TOKEN_ENC_KEY" \\
  -c \"UPDATE google_calendar_tokens SET \\
      access_token_enc = pgp_sym_encrypt(access_token, :'key'), \\
      refresh_token_enc = pgp_sym_encrypt(refresh_token, :'key'), \\
      encryption_version = 1, encrypted_at = now() \\
    WHERE access_token_enc IS NULL AND access_token IS NOT NULL;\"
```

**Fail-closed поведение:**
- Если `CALENDAR_TOKEN_ENC_KEY` не задан, а токены уже зашифрованы — доступ к календарю отключён.

---

## Console API Idempotency (мутации)

- Все мутации `/console/v1/*` должны идти с idempotency‑key в заголовке.
- Ответ сохраняется в `console_idempotency_keys` по ключу `(client_id, idempotency_key, scope)` и переиспользуется.
- Для диагностики: `console_idempotency_keys` + `audit_events` (дубликаты не должны появляться).

---

## Console API Contracts

- Источник истины: `contracts/console_api/openapi.v1.yaml` + `contracts/console_api/errors.v1.json`.
- Генерация: `truffles-api/scripts/generate_openapi.py` (обновлять после изменений в `console` роутерах).
- Любые breaking изменения — через новую версию контракта.

---

## Observability (OTel/Tempo)

**Включение:**
- `OTEL_ENABLED=1`
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4318/v1/traces`
- `OTEL_SERVICE_NAME` — для API (`truffles-api`).
- `OTEL_SERVICE_NAME_OUTBOX` — для outbox worker (`truffles-outbox`).
- `OTEL_SERVICE_NAME_SENTINEL` — для sentinel (`truffles-sentinel`).
- Span attrs: `message_id`/`outbox_id`/`trace_id`/`client_slug`/`conversation_id`/`branch_id`.

**Проверки:**
```bash
curl -fsS http://localhost:3200/ready
curl -fsS http://localhost:3200/metrics | rg -m 1 tempo_distributor_spans_received_total

docker logs truffles-api --tail 5 | rg -i 'otel enabled'
docker logs truffles-outbox --tail 5 | rg -i 'otel enabled'
docker logs truffles-sentinel --tail 5 | rg -i 'otel enabled'
```

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

## Console quality gates (Playwright / Schemathesis / k6)
CI uses GitHub secrets for auth and skips jobs if they are missing:
- `CONSOLE_E2E_USERNAME`, `CONSOLE_E2E_PASSWORD`
- `CONSOLE_KEYCLOAK_TOKEN_URL`, `CONSOLE_KEYCLOAK_CLIENT_ID`, `CONSOLE_KEYCLOAK_CLIENT_SECRET`,
  `CONSOLE_KEYCLOAK_USERNAME`, `CONSOLE_KEYCLOAK_PASSWORD`
- optional: `CONSOLE_API_TOKEN` (bypass Keycloak for contract/k6)

**Playwright (smoke, read-only):**
```bash
cd console-web
PLAYWRIGHT_BASE_URL=http://localhost:3000 \
NEXT_PUBLIC_API_URL=https://api.truffles.kz/console/v1 \
KEYCLOAK_ISSUER=https://auth.truffles.kz/realms/truffles \
KEYCLOAK_CLIENT_ID=console-web \
KEYCLOAK_CLIENT_SECRET=console-client-secret \
NEXTAUTH_URL=http://localhost:3000 \
E2E_USERNAME=admin \
E2E_PASSWORD=admin \
npm run test:e2e:smoke
```

**Playwright (mutating, only staging):**
```bash
cd console-web
E2E_ALLOW_MUTATIONS=1 npm run test:e2e:mutating
```

**Schemathesis (GET-only contract smoke):**
```bash
SCHEMATHESIS_TOKEN="<bearer token>" \
schemathesis --config-file contracts/console_api/schemathesis.toml run contracts/console_api/openapi.v1.yaml \
  --url https://api.truffles.kz/console/v1 \
  --include-method=GET \
  --checks all \
  --request-timeout 10 \
  --hypothesis-max-examples=3 \
  --header "Authorization: Bearer ${SCHEMATHESIS_TOKEN}"
```
**Seed IDs:** `contracts/console_api/schemathesis.toml` contains stable `case_id`/`conversation_id` used in contract
checks. If the IDs go stale, update them with a real handover + conversation from the same client as the
console token.

**k6 (manual load smoke):**
```bash
CONSOLE_API_URL=https://api.truffles.kz/console/v1 \
CONSOLE_API_TOKEN="<bearer token>" \
k6 run ops/k6/console_smoke.js
```
- **Когда запускать:** перед релизом после изменений в Console API/фильтрах/пагинации/индексах; перед подключением крупного клиента; при подозрении на деградацию.
- **Когда обновлять сценарий:** появился новый “горячий” эндпоинт или изменились параметры фильтров; изменились SLO/пороговые значения.
- **Режим:** только read‑only; low VU/iterations; предпочтительно staging.

---

## CI / GitHub Actions (как запускать, зачем и когда)

**Источник правды:** `.github/workflows/ci.yml`.

### Когда CI запускается
- **Pull Request → main:** lint + unit + core‑eval (если затронуты L1‑пути). long/asr только при L2‑изменениях или label `run-long`. build/push/deploy/livecheck не выполняются.
- **Push → main:** полный пайплайн (lint/unit/core/long/asr → build-push → deploy → ci-livecheck), если гейты позволяют.
- **workflow_dispatch:** ручной запуск с опциями `run_long` и `run_livecheck`.

### Console gates
- `console-e2e` (Playwright smoke) — запускается при изменениях в `console-web/**` или CI.
- `console-contract` (Schemathesis GET-only) — запускается при изменениях в `contracts/console_api/**` или console API.
- `console-k6` — ручной запуск через `workflow_dispatch` (input `run_k6=true`).

### Console E2E (локально, чтобы воспроизвести CI)
- Креды: `/home/zhan/secrets/console-e2e.env` (не коммитить).
- Важно: `NEXTAUTH_URL` должен совпадать с `PLAYWRIGHT_BASE_URL` (иначе CSRF).
- Команда и контекст запуска — в `docs/DEV_SETUP.md` (раздел 6).
- Seed данных (идемпотентный) — `truffles-api/scripts/console_e2e_seed.py`.

### Console secrets (источник истины)
- CI secrets: GitHub Actions (`CONSOLE_E2E_USERNAME`, `CONSOLE_E2E_PASSWORD`, `CONSOLE_KEYCLOAK_CLIENT_SECRET`, `CONSOLE_API_TOKEN`).
- Prod host: `/home/zhan/secrets/console-e2e.env` (E2E login + Keycloak client secret).
- Contract/k6: `/home/zhan/secrets/console-contract.env` (token or Keycloak user creds).
- `CONSOLE_API_TOKEN` не хранится в репозитории: получать через Keycloak token endpoint и использовать локально.
- Шаблон переменных: `console-web/.env.e2e.example`.

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
- `truffles-api/migrations/**`
- `truffles-api/scripts/**`
- `truffles-api/requirements.txt`
- `truffles-api/Dockerfile`
- `scripts/restart_api.sh`
- `scripts/restart_workers.sh`
- `scripts/restart_release.sh`
- `scripts/check_migration_governance.py`
- `knowledge/**`

**livecheck_required (точный список путей):**
- `truffles-api/app/**`
- `truffles-api/migrations/**`
- `truffles-api/scripts/**`
- `truffles-api/requirements.txt`
- `truffles-api/Dockerfile`
- `scripts/restart_api.sh`
- `scripts/restart_workers.sh`
- `scripts/restart_release.sh`
- `scripts/check_migration_governance.py`
- `knowledge/**`
- `ops/**`
- `.github/workflows/**`

**Event gate (PR vs main):**
- На PR `build-push`, `deploy`, `ci-livecheck` всегда skip.
- На main эти шаги выполняются только при успешных обязательных джобах (lint/unit/secret-scan + long/asr, если они не skipped).
- `core-eval` остаётся обязательным quality-signal, но не блокирует deploy.

### Как форсировать проверки
- **long/asr:** label `run-long` на PR или `workflow_dispatch` с `run_long=true`.
- **ci-livecheck:** только на `main` и только если `deploy` сработал; на `workflow_dispatch` нужно `run_livecheck=true`.

### Quality validity gates (`ops/diagnose.py llm-quality`)
- **infra_valid** = пройден preflight/infra-контур (включая webhook_secret/branch/env/judge prerequisites).
- **semantic_valid** = нет threshold/regression breach при валидном сравнении.
- Любой run с `infra_valid=false` считается `INVALID`: его нельзя использовать для сравнения качества и для обновления baseline.
- Обновление canonical baseline (`ops/results/booking_quality.json`) допускается только при `infra_valid=true`, `semantic_valid=true`, `judge.enabled=true` (`judge_mode=sample|all`).
- Strict replay (`--scenarios-file`) без judge допускается только как debug (`--allow-judge-off`) и не считается каноническим quality-evidence.

### Validation order (local-first)
- Для core/поведенческих правок порядок проверки фиксированный: `local realism` -> `local deterministic` -> `CI deterministic`.
- `local realism` = реальные LLM‑диалоги (10–15 ходов) + chaos перебивки + tool hooks + booking confirm path.
- Если нет `OPENAI_API_KEY`/judge key для required local realism run, статус задачи = `BLOCKED`.
- CI не является источником финальной поведенческой валидации; CI подтверждает воспроизводимость и ловит базовый drift.

### CI scope (what belongs in CI)
- В CI держим только простые, быстрые и детерминированные проверки, не требующие внешнего LLM.
- Примеры CI-набора: lint, unit, schema/contracts, deterministic replay, smoke на trace/meta contract.
- Сложные LLM+tools+chaos прогоны выполняются локально перед PR и прикладываются как evidence.

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
- `deploy` внутри себя решает `deployed=true/false`; на `main` при `deploy_required=true` silent skip запрещён (job падает).
- `ci-livecheck` job всегда виден, но шаги выполняются только если `deploy.outputs.deployed=true`.

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
# Обновить APP_VERSION (используется в /admin/version и livecheck deploy-verify)
ssh -p 222 zhan@5.188.241.234 "sed -i 's/^APP_VERSION=.*/APP_VERSION=main/' /home/zhan/truffles-main/truffles-api/.env"

# CI build/push → pull image (prod standard)
ssh -p 222 zhan@5.188.241.234 "IMAGE_NAME=ghcr.io/k1ddy/truffles-ai-employee:main PULL_IMAGE=1 RUN_MIGRATIONS=1 MIGRATION_BOOTSTRAP_MODE=auto REQUIRE_GHCR=1 VERIFY_VERSION=1 EXPECTED_GIT_COMMIT=<sha> EXPECTED_VERSION=main RESTART_KNOWLEDGE_ACTIVATION_SERVICE=1 KNOWLEDGE_ACTIVATION_SERVICE_ENABLED=1 RUN_KNOWLEDGE_ACTIVATION_CANARY=1 KNOWLEDGE_ACTIVATION_CANARY_OUTPUT=/tmp/knowledge_activation_release_guard.json bash /home/zhan/truffles-main/scripts/restart_release.sh"

# ❌ Запрещено на проде: локальная docker-compose build/run для API
# restart_release.sh по умолчанию использует GHCR и требует GHCR-образ (REQUIRE_GHCR=1).
# По умолчанию RUN_MIGRATIONS=1: SQL миграции применяются до переключения контейнера.
```
`restart_release.sh` поддерживает `IMAGE_NAME`, `PULL_IMAGE=1`, `RUN_MIGRATIONS=1`, `MIGRATION_BOOTSTRAP_MODE=auto|legacy|off`, `REQUIRE_GHCR=1`, `VERIFY_VERSION=1`, `EXPECTED_GIT_COMMIT`, `EXPECTED_VERSION`, `RESTART_KNOWLEDGE_ACTIVATION_SERVICE=1`, `KNOWLEDGE_ACTIVATION_SERVICE_ENABLED=1`, `RUN_KNOWLEDGE_ACTIVATION_CANARY=1`, `KNOWLEDGE_ACTIVATION_CANARY_OUTPUT`, `ACTIVATION_GUARD_PYTHON`.
Он резолвит immutable digest и применяет один image reference к `truffles-api`, `truffles-outbox`, `truffles-sentinel`, а при `RESTART_KNOWLEDGE_ACTIVATION_SERVICE=1` и к `truffles-knowledge-activation-service`, после чего проверяет image parity и может записать `go|no_go` JSON артефакт через `truffles-api/scripts/knowledge_activation_release_guard.py`.
`restart_api.sh` используется внутри release flow и поддерживает `EXPECTED_IMAGE`, `MIGRATION_BOOTSTRAP_MODE`.

Точечный перезапуск только воркеров (если нужно отдельно):
```bash
ssh -p 222 zhan@5.188.241.234 "ENV_FILE=/home/zhan/truffles-main/truffles-api/.env bash /home/zhan/truffles-main/scripts/restart_workers.sh"
```
`restart_workers.sh` теперь поднимает `truffles-outbox`, `truffles-knowledge-activation`, `truffles-sentinel`.

### Knowledge Gateway (shadow)
```bash
ssh -p 222 zhan@5.188.241.234 "ENV_FILE=/home/zhan/truffles-main/truffles-api/.env PULL_IMAGE=1 REQUIRE_GHCR=1 bash /home/zhan/truffles-main/scripts/restart_knowledge_gateway.sh"
ssh -p 222 zhan@5.188.241.234 "curl -s http://127.0.0.1:8010/health"
```

### Provider Gateway (shadow)
```bash
ssh -p 222 zhan@5.188.241.234 "ENV_FILE=/home/zhan/truffles-main/truffles-api/.env PULL_IMAGE=1 REQUIRE_GHCR=1 bash /home/zhan/truffles-main/scripts/restart_provider_gateway.sh"
ssh -p 222 zhan@5.188.241.234 "curl -s http://127.0.0.1:8011/health"
```

### Knowledge Activation Service (shadow)
```bash
ssh -p 222 zhan@5.188.241.234 "ENV_FILE=/home/zhan/truffles-main/truffles-api/.env PULL_IMAGE=1 REQUIRE_GHCR=1 EXPECTED_IMAGE=ghcr.io/k1ddy/truffles-ai-employee:main KNOWLEDGE_ACTIVATION_SERVICE_ENABLED=1 VERIFY_HEALTH=1 bash /home/zhan/truffles-main/scripts/restart_knowledge_activation_service.sh"
ssh -p 222 zhan@5.188.241.234 "curl -s http://127.0.0.1:8015/health"
ssh -p 222 zhan@5.188.241.234 "python3 /home/zhan/truffles-main/truffles-api/scripts/knowledge_activation_release_guard.py --output /tmp/knowledge_activation_release_guard.manual.json --pretty"
```
- P4 observability: `/metrics` now exports `health_check_knowledge_activation_status`, `knowledge_activation_jobs_total{state=*}`, `knowledge_activation_failed_24h_total`, `knowledge_activation_stale_running_total`, and queue-age gauges; `/admin/health/check` + sentinel include `checks.knowledge_activation`.
- P5 rollout safety: `restart_knowledge_activation_service.sh` also supports `VERIFY_URL`, `VERIFY_RETRIES`, and `VERIFY_SLEEP_SECONDS`; canonical deploy/rollback SOP lives in `docs/runbooks/KNOWLEDGE_ACTIVATION_RELEASE.md`.
- P6 closeout: `python3 /home/zhan/truffles-main/ops/knowledge_activation_closeout.py --client-slug <client> --branch-slug <branch> --guard-json /tmp/knowledge_activation_release_guard.json --output /tmp/knowledge_activation_closeout.json --pretty` reuses the P5 artifact and adds tenant preview/live invariants from Postgres truth.
- P9 post-deploy automation: `.github/workflows/ci.yml` now reuses `scripts/knowledge_activation_postdeploy.sh` after deploy; CI always uploads `knowledge-activation-proof` artifacts, and tenant closeout is truthfully marked `skipped` until `KNOWLEDGE_ACTIVATION_CLOSEOUT_CLIENT_SLUG` / `KNOWLEDGE_ACTIVATION_CLOSEOUT_BRANCH_SLUG` (or workflow-dispatch overrides) are configured.

### Перезапуск API (без обновления кода)
```bash
ssh -p 222 zhan@5.188.241.234 "RUN_MIGRATIONS=1 MIGRATION_BOOTSTRAP_MODE=auto RESTART_KNOWLEDGE_ACTIVATION_SERVICE=1 RUN_KNOWLEDGE_ACTIVATION_CANARY=1 bash /home/zhan/truffles-main/scripts/restart_release.sh"
```
По умолчанию перезапуск идёт с GHCR `:main` (REQUIRE_GHCR=1); локальные образы на проде запрещены.
`restart_release.sh` перезапускает API+workers в одном шаге, а при `RESTART_KNOWLEDGE_ACTIVATION_SERVICE=1` включает activation service в тот же parity/canary contract. После deploy финальный go/no-go для одного rollout tenant теперь фиксируется `ops/knowledge_activation_closeout.py` и должен сохранить `knowledge_activation_closeout.json` рядом с P5 guard artifact.

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
