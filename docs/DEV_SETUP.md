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

**Playwright smoke (read-only):**
`E2E_USE_STORAGE_STATE=1` включает один логин на весь прогон (быстрее и стабильнее).
```bash
cd /home/zhan/truffles-main/console-web
PLAYWRIGHT_BASE_URL=http://localhost:3000 \
NEXTAUTH_URL=http://localhost:3000 \
KEYCLOAK_ISSUER=https://auth.truffles.kz/realms/truffles \
KEYCLOAK_CLIENT_ID=console-web \
KEYCLOAK_CLIENT_SECRET=console-client-secret \
NEXT_PUBLIC_API_URL=https://api.truffles.kz/console/v1 \
E2E_USE_STORAGE_STATE=1 \
E2E_USERNAME=admin \
E2E_PASSWORD=admin \
npm run test:e2e:smoke
```

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
