# Dev Environment Setup — Truffles Platform

> **Цель:** Единый источник истины для запуска dev окружения.

---

## 1. Ports Contract

| Service | Port | Как запустить | Логи |
|---------|------|---------------|------|
| **console-web** | 3000 | `pm2 start ecosystem.config.cjs` | `pm2 logs console-web` |
| **truffles-api** | 8000 | Docker (prod image) | `docker logs truffles-api` |
| **keycloak** | 8080 | Docker | `docker logs keycloak` |
| **PostgreSQL** | 5432 | Docker | `docker logs truffles_postgres_1` |
| **Qdrant** | 6333 | Docker | `docker logs truffles_qdrant_1` |

> ⚠️ **НЕ ИСПОЛЬЗОВАТЬ** порт 8001 для API! Это старый dev порт без логов.

---

## 2. Required Environment Variables

### console-web/.env.local

```bash
# API URL — ТОЛЬКО 8000, не 8001!
NEXT_PUBLIC_API_URL=http://localhost:8000

# OIDC (Keycloak)
CONSOLE_OIDC_JWKS_URL=http://localhost:8080/realms/truffles/protocol/openid-connect/certs
CONSOLE_OIDC_ISSUER=http://localhost:8080/realms/truffles
```

### truffles-api/.env

```bash
# CORS — разрешить frontend
CORS_ALLOW_ORIGINS=http://localhost:3000

# Outbox worker
OUTBOX_WORKER_ENABLED=1

# Test mode (для dev)
TEST_MODE=1
OUTBOUND_ALLOWLIST_JIDS=77015705555@s.whatsapp.net
```

---

## 3. Quick Start

```bash
# 1. Запустить Docker стек
cd /home/zhan/infrastructure
docker compose -f docker-compose.truffles.yml up -d

# 2. Проверить API
curl http://localhost:8000/health
curl http://localhost:8000/admin/health/check

# 3. Запустить console-web
cd /home/zhan/truffles-main/console-web
npm install
pm2 start ecosystem.config.cjs

# 4. Проверить frontend
open http://localhost:3000
```

---

## 4. Troubleshooting

| Симптом | Причина | Решение |
|---------|---------|---------|
| 502 Bad Gateway | API на неправильном порту | Проверить `NEXT_PUBLIC_API_URL=http://localhost:8000` |
| CORS blocked | CORS не настроен | Добавить `CORS_ALLOW_ORIGINS=http://localhost:3000` в API .env |
| "Не удалось загрузить" | API не запущен | `docker logs truffles-api` |
| AUTH_REQUIRED | Нет JWT | Проверить `CONSOLE_OIDC_JWKS_URL` |

---

## 5. E2E Health Check

После запуска проверить всю цепочку:

```bash
# Frontend → API → DB
curl http://localhost:3000/api/health/full
```

Ожидаемый ответ:
```json
{
  "status": "healthy",
  "components": {
    "frontend": "ok",
    "api": {"status": "ok", "port": 8000},
    "database": "connected"
  }
}
```

---

## 6. Console tests (local)

**Креды (не коммитить):**
- E2E‑креды лежат на прод‑хосте: `/home/zhan/secrets/console-e2e.env`.
- В файле должны быть `E2E_USERNAME`, `E2E_PASSWORD`, `KEYCLOAK_CLIENT_SECRET`.
- Contract/k6 env: `/home/zhan/secrets/console-contract.env` (`CONSOLE_API_TOKEN` или Keycloak user creds).
- При ротации обновить файл и уведомить Brain/Owner.
- Шаблон переменных: `console-web/.env.e2e.example`.

**Playwright smoke (read-only):**
`E2E_USE_STORAGE_STATE=1` включает один логин на весь прогон (быстрее и стабильнее).
```bash
cd /home/zhan/truffles-main/console-web

# 1) Подтянуть креды
set -a
. /home/zhan/secrets/console-e2e.env
set +a

# 2) BASE и NEXTAUTH_URL должны совпадать (иначе CSRF)
#    Если в console-web/.env.local указан https://console.truffles.kz — ставим BASE туда же.
PLAYWRIGHT_BASE_URL=http://localhost:3000
NEXTAUTH_URL=$PLAYWRIGHT_BASE_URL

# 3) Настройки Keycloak (secret берём из console-e2e.env)
KEYCLOAK_ISSUER=https://auth.truffles.kz/realms/truffles
KEYCLOAK_CLIENT_ID=console-web

# 4) API base
NEXT_PUBLIC_API_URL=https://api.truffles.kz/console/v1

PLAYWRIGHT_WEB_SERVER=0 \
PLAYWRIGHT_BASE_URL=$PLAYWRIGHT_BASE_URL \
NEXTAUTH_URL=$NEXTAUTH_URL \
KEYCLOAK_ISSUER=$KEYCLOAK_ISSUER \
KEYCLOAK_CLIENT_ID=$KEYCLOAK_CLIENT_ID \
KEYCLOAK_CLIENT_SECRET=$KEYCLOAK_CLIENT_SECRET \
NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
E2E_USE_STORAGE_STATE=1 \
npm run test:e2e:smoke
```

**E2E seed (стабильные данные для тестов):**
> Требует доступ к БД и Keycloak admin. Скрипт идемпотентный, использует стабильные UUID.

```bash
cd /home/zhan/truffles-main/truffles-api
set -a
. .env
set +a

E2E_SEED_ALLOW=1 \
E2E_USERNAME="ci-console" \
KEYCLOAK_ISSUER=https://auth.truffles.kz/realms/truffles \
KEYCLOAK_ADMIN_USERNAME="<admin>" \
KEYCLOAK_ADMIN_PASSWORD="<password>" \
python scripts/console_e2e_seed.py
```

**Примечания:**
- Если уже известен `sub`, можно передать `E2E_SUBJECT` и не обращаться к Keycloak admin.
- Для нестандартного Keycloak: `KEYCLOAK_ADMIN_BASE_URL` и `KEYCLOAK_REALM`.
- `CONSOLE_API_TOKEN` короткоживущий; хранить только в env‑файле, не в репозитории.

**Если что-то пошло не так (частые случаи):**
- Зависло на логине/CSRF: `NEXTAUTH_URL` должен совпадать с `PLAYWRIGHT_BASE_URL` и реальным хостом.
- 401 от Keycloak: `KEYCLOAK_CLIENT_SECRET` не совпадает или был ротирован.
- Пустой UI/таймауты: проверить `NEXT_PUBLIC_API_URL` и health API.
- `CLIENT_SELECTION_REQUIRED`: убедиться, что E2E user привязан к одному client, либо добавить `console:client_id` в storageState.

**Schemathesis contract smoke (GET-only):**
```bash
SCHEMATHESIS_TOKEN="<bearer token>" \
schemathesis --config-file /home/zhan/truffles-main/contracts/console_api/schemathesis.toml run /home/zhan/truffles-main/contracts/console_api/openapi.v1.yaml \
  --url https://api.truffles.kz/console/v1 \
  --include-method=GET \
  --checks all \
  --request-timeout 10 \
  --hypothesis-max-examples=3 \
  --header "Authorization: Bearer ${SCHEMATHESIS_TOKEN}"
```
Seed IDs live in `/home/zhan/truffles-main/contracts/console_api/schemathesis.toml`.

**k6 (manual load smoke):**
```bash
CONSOLE_API_URL=https://api.truffles.kz/console/v1 \
CONSOLE_API_TOKEN="<bearer token>" \
k6 run /home/zhan/truffles-main/ops/k6/console_smoke.js
```

---

*Обновлено: 2026-01-21*
