# Console Guide (Logic + Dev)

**Scope:** Console UI, Console API, auth, tenancy, and how console flows map to core system processes.  
**Out of scope:** Core decision pipeline (see `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`).

---

## 1) Components and Data Flow

**Console UI (Next.js)**  
`console-web/` renders pages and calls the API through a server proxy.

**Auth (Keycloak + NextAuth)**  
Keycloak issues JWT; NextAuth stores session; API validates JWT signature and maps `sub` to agent.

**Console API (FastAPI)**  
`/console/v1/*` endpoints read/write **core DB** tables with tenant scoping
(DB: `chatbot` via `DATABASE_URL` in `truffles-api`).

**Proxy Route**  
`console-web/src/app/api/proxy/[...path]/route.ts` forwards requests to `NEXT_PUBLIC_API_URL` with Bearer token.

**Flow (happy path):**
1. User logs in at `auth.truffles.kz` (Keycloak).
2. NextAuth stores `accessToken` in session.
3. UI calls `/api/proxy/*`.
4. Proxy calls `https://api.truffles.kz/console/v1/*`.
5. Console API validates JWT and loads `ConsoleAuthContext`.
6. Handovers/Bookings/Settings rendered per tenant.

---

## 2) Tenancy and RBAC (Critical)

**Key:** один OIDC login может соответствовать нескольким `client_id`.  
Console uses `agent_identities` to map OIDC `sub` → `agents` → `client_id`.

**Client selection (если клиентов несколько):**
- `/console/v1/me` возвращает `clients[]` и `selection_required`.
- API требует заголовок `X-Client-Id`, если клиентов > 1.
- UI хранит выбор в `localStorage` (`console:client_id`) и очищает на logout.

**Branch selection (если филиалов несколько или роль branch‑scoped):**
- `/console/v1/me` возвращает `branches[]` и `branch_selection_required`.
- API требует заголовок `X-Branch-Id`, если филиалов > 1 и доступ ограничен филиалами.
- UI хранит выбор в `localStorage` (`console:branch_id`) и очищает на logout.
**Access scope is enforced here:**
`truffles-api/app/services/console_auth.py` → `get_console_context()`

**Note (current limitation):**
Org-level access реализован частично: есть `agent_memberships` и RBAC, но company/branch selection в UI
ограничен выбором клиента. Полная модель Company → Client → Branch — по DEC-011.

Rules:
- `sub` must exist in `agent_identities` (channel=`oidc`).
- Agent must be `is_active`.
- All queries filter by `context.client.id`.
- If multiple clients → `X-Client-Id` is mandatory.
- Non‑admin/owner users are restricted to their branch.
- Если один `sub` связан с несколькими клиентами → API вернёт
  `CLIENT_SELECTION_REQUIRED` (нужен `X-Client-Id`) либо надо убрать дубликаты.

**Tenant UX contract (short):**
- Контекст (Company / Client / Branch) всегда виден в UI.
- Selector показывается только если есть выбор (2+).
- Ошибки должны быть объяснимы: “Выберите клиента/филиал”.
- Fail‑closed: без валидного контекста запросы не выполняются.

**Common symptom:** “Only 1–2 cases shown / no slots.”  
Usually means the admin is mapped to the wrong `client_id` or the wrong client was selected.

**Tables used:**
- `agent_identities` (OIDC identity mapping)
- `agents` (role, client, optional branch)
- `agent_memberships` (org‑scope RBAC: company/client/branch)
- `clients`, `branches` (tenant scope)
- `handovers`, `conversations`, `users` (cases)
- `specialists`, `bookings` (calendar)
- `audit_events` (audit tab)

---

## 3) Console Pages → API Endpoints

**Cases (Заявки)**
- UI: `console-web/src/components/CaseList.tsx`
- API: `GET /console/v1/cases`
- Data: `handovers` + `conversations` + `users`
- Paging: cursor = `handover.created_at`

**Case view**
- UI: `console-web/src/app/cases/[id]/page.tsx`
- API: `GET /console/v1/cases/{id}`, `POST /take`, `POST /resolve`

**Calendar (Записи)**
- UI: `console-web/src/app/calendar/page.tsx`
- API: `/calendar/specialists`, `/calendar/slots`, `/calendar/bookings`
- Data: `specialists`, `bookings`

**Settings**
- UI: `console-web/src/app/settings/page.tsx`
- API: `GET/PATCH /console/v1/settings`

**Audit**
- UI: `console-web/src/app/audit/page.tsx`
- API: `GET /console/v1/audit`

**Ops**
- UI: `console-web/src/components/OpsPage.tsx`
- API: `GET /console/v1/health`, `/console/v1/metrics/daily`, `/console/v1/telegram/health`

---

## 3.1 Telegram integration (Console)

**Purpose:** Telegram is paging/fallback; Console remains the source of truth for workflow, RBAC, and audit.

**Backend (Console API + core mapping):**
- Health: `GET /console/v1/telegram/health` (Console API).
- Verify: `POST /console/v1/telegram/verify` (owner/admin).
- Test: `POST /console/v1/telegram/test` (owner/admin).
- Agent linking: `GET /console/v1/agents` + `POST /console/v1/agents/{id}/telegram/link`.
- Case trail: `GET /console/v1/cases/{id}` returns `telegram_trail`.
- Case actions: `POST /console/v1/cases/{id}/take|resolve|return` return `sync` status.
- Branch routing: `GET /console/v1/settings` returns `branches[].telegram_chat_id` + `branches[].instance_id`.

**UI locations:**
- Settings → Telegram connector: client-scope Verify/Test.
- Settings → Branches: per-branch Verify/Test (requires `telegram_chat_id`).
- Ops → Telegram card: client-scope Verify/Test (owner/admin).

**Data sources (core DB):**
- `branches.telegram_chat_id`, `branches.instance_id` (routing + UI display).
- `client_settings.telegram_bot_token`, `client_settings.telegram_chat_id` (bot config + legacy fallback).
- `conversations.telegram_topic_id` (topic per user).
- `handovers.telegram_message_id`, `handovers.notified_at` (delivery evidence).
- `agent_identities` (channel=telegram) + `agent_link_tokens` (linking tokens).

**Trail mapping (Console API):**
- `message_id` → `handovers.telegram_message_id`
- `topic_id` → `conversations.telegram_topic_id`
- `chat_id` → `branches.telegram_chat_id` (fallback to `client_settings.telegram_chat_id`)
- `delivery_status` → `sent` when message_id present, otherwise `pending`
- `delivered_at` → `handovers.notified_at` (if present)
- `telegram_link` → `https://t.me/c/<internal_id>/<message_id>` when `chat_id` is `-100...`
  - если есть `topic_id` → добавляем `?thread=<topic_id>` для открытия нужного топика.
  - `internal_id` = `chat_id` without `-100` prefix; if not numeric, link is omitted.

**Health mapping (Console API):**
- `webhook_alive` via Telegram `getWebhookInfo` for `telegram_bot_token`.
- `pending_messages` = `pending_update_count` from Telegram webhook info.
- `last_error_at`/`last_error_message` from Telegram webhook info.
- `error_rate_24h` = 0.0 (no persisted telemetry yet; recorded as gap in STATE).
- `status` = `degraded` только если ошибка свежая (последние 24ч) или есть pending messages.

**Onboarding checklist (Telegram + Console, P0)**

**Что нужно от бизнес‑владельца (входные данные):**
- Список филиалов + телефоны + `instanceId` из ChatFlow.
- Telegram‑группа на каждый филиал (supergroup), **topics включены**.
- Бот добавлен админом в каждую группу.
- Список менеджеров и их роли (owner/admin/manager), кто работает через Telegram.

**Шаги онбординга (один раз на клиента):**
1) Создать `client`, `branches`, `agents`.
2) Заполнить `branches.instance_id` (ChatFlow) и `branches.telegram_chat_id` (TG group id `-100...`).
3) Заполнить `client_settings.telegram_bot_token`.
4) Настроить ChatFlow webhook: `/webhook/{client_slug}?webhook_secret=...`.
5) Настроить Telegram webhook: `https://api.truffles.kz/telegram-webhook`.
6) В Console → Settings → Team: подключить Telegram для каждого менеджера (token → `/start <token>`).
7) В Console → Settings/Ops: Verify/Test (client + branch scope).

**Ожидаемый результат (после онбординга):**
- Эскалация создаёт topic и карточку с кнопками.
- `pending/manager_active` форвардит сообщения клиента в topic (текст/медиа по policy).
- Take/Resolve (Console или Telegram) обновляет Telegram‑карточку и шлёт клиенту системное уведомление.
- Аудит содержит `case_taken/resolved` + `manager_connected/disconnected`.
- В карточке кейса есть две ссылки: `tg://` (Desktop) и `https://t.me` (Web); если Desktop не открывает topic, используйте Web‑ссылку.

**Контракт требований (минимум для работы):**
- `branches.telegram_chat_id` заполнен на каждый филиал.
- `client_settings.telegram_bot_token` задан и webhook установлен.
- Агент связал Telegram через `/start <token>`.
- `POST /console/v1/cases/{id}/take|resolve|return` идёт через `state_service`.

**Where to change code:**
- API endpoint + mapping: `truffles-api/app/routers/console.py`
- Telegram API helper: `truffles-api/app/services/telegram_service.py`
- Linking helpers: `truffles-api/app/services/agent_link_service.py`
- UI Ops card: `console-web/src/components/OpsPage.tsx`
- UI Case trail: `console-web/src/components/CaseView.tsx`
- UI Branch list: `console-web/src/app/settings/page.tsx`
- Console schemas: `truffles-api/app/schemas/console.py`
- Contracts: `contracts/console_api/openapi.v1.yaml`

**Diagnostics (quick):**
- Webhook status: `curl -s -H "Authorization: Bearer $TOKEN" https://api.truffles.kz/console/v1/telegram/health`
- Telegram webhook raw: `curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"`
- Agent linking (token):
  ```bash
  curl -s -X POST -H "Authorization: Bearer $TOKEN" \
    https://api.truffles.kz/console/v1/agents/<agent_id>/telegram/link
  ```
- Link usage: отправить в Telegram боту `/start <token>` (создаст `agent_identity`).
- Verify (client scope):
  ```bash
  curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \\
    https://api.truffles.kz/console/v1/telegram/verify \\
    -d '{"scope":"client"}'
  ```
- Verify (branch scope):
  ```bash
  curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \\
    https://api.truffles.kz/console/v1/telegram/verify \\
    -d '{"scope":"branch","branch_id":"<UUID>"}'
  ```
- Test message (custom text):
  ```bash
  curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \\
    https://api.truffles.kz/console/v1/telegram/test \\
    -d '{"scope":"branch","branch_id":"<UUID>","message":"Truffles test message"}'
  ```

---

## 4) Console Auth & Tokens

**OIDC config (API side)**  
`CONSOLE_OIDC_JWKS_URL`, `CONSOLE_OIDC_ISSUER`, `CONSOLE_OIDC_AUDIENCE`.

**Keycloak realm file**  
`ops/keycloak-realm.json` defines clients + initial users.

**Stable `sub`**  
Set `users[].id` in `ops/keycloak-realm.json` to avoid `sub` changes on re‑create.

---

## 5) Adding New Console Features

**Backend**
1. Add schema in `truffles-api/app/schemas/console.py`.
2. Add endpoint in `truffles-api/app/routers/console.py` or a dedicated router.
3. Enforce tenant scope via `get_console_context`.
4. Add idempotency for mutations: `console_idempotency.py`.
5. Update contract: `contracts/console_api/openapi.v1.yaml`.

**Frontend**
1. Add API call via `/api/proxy/*` (server‑side).
2. Use `useAuthenticatedApi` for client calls.
3. Handle `AUTH_REQUIRED` / `ACCESS_DENIED` errors.
4. Keep UI consistent with `globals.css` tokens.

**Tests**
- Contract: `schemathesis --config-file contracts/console_api/schemathesis.toml run contracts/console_api/openapi.v1.yaml --url https://api.truffles.kz/console/v1`
- E2E (if required): `console-e2e` (Playwright)

---

## 6) Console tests (E2E/CI)

**Purpose:** catch auth breakage, navigation regressions, and read-only API wiring.

**Defaults:**
- Smoke tests are read-only. Mutating checks require `E2E_ALLOW_MUTATIONS=1`.
- CI uses `E2E_USE_STORAGE_STATE=1` to log in once per run (faster, less flaky).
- Login flow uses NextAuth sign-in to reach Keycloak (more stable than clicking UI).
- Playwright uses storageState via setup project (one login per run).

**Where to run:** `docs/DEV_SETUP.md` (Console tests section).

**Credentials (do not commit):**
- Prod host: `/home/zhan/secrets/console-e2e.env`.
- Contract/k6: `/home/zhan/secrets/console-contract.env`.
- Template: `console-web/.env.e2e.example` (no secrets).
- CI: GitHub Secrets (`CONSOLE_E2E_USERNAME`, `CONSOLE_E2E_PASSWORD`, `CONSOLE_KEYCLOAK_CLIENT_SECRET`).
- `CONSOLE_API_TOKEN` is short-lived; do not store in repo. If used locally, keep only in
  `/home/zhan/secrets/console-contract.env` and rotate.

**Seed (stable E2E data):**
- Script: `truffles-api/scripts/console_e2e_seed.py` (idempotent, stable UUIDs).
- Requires DB + Keycloak admin, gated by `E2E_SEED_ALLOW=1`.
- If `sub` is known, pass `E2E_SUBJECT` to skip Keycloak admin.

**E2E note (multi-client):**
- E2E user should map to **one** client, or storageState must include `console:client_id`.
- Otherwise tests will see `CLIENT_SELECTION_REQUIRED`.

**CONSOLE_API_TOKEN (short-lived):**
- Получать через Keycloak token endpoint; хранить только в env.
```bash
KEYCLOAK_TOKEN_URL="https://auth.truffles.kz/realms/truffles/protocol/openid-connect/token"
curl -s -X POST "$KEYCLOAK_TOKEN_URL" \
  -d "client_id=console-web" \
  -d "client_secret=$CONSOLE_KEYCLOAK_CLIENT_SECRET" \
  -d "grant_type=password" \
  -d "username=$CONSOLE_KEYCLOAK_USERNAME" \
  -d "password=$CONSOLE_KEYCLOAK_PASSWORD" | jq -r '.access_token'
```
---

## 7) Debug & Troubleshooting

**403 ACCESS_DENIED**
- Check `agent_identities` mapping for `sub`.
- Verify `agents.is_active = true`.

**400 CLIENT_SELECTION_REQUIRED**
- Один `sub` связан с несколькими клиентами/агентами.
- `/console/v1/me` вернул `selection_required=true` → выбрать клиента или передать `X-Client-Id`.
- Очистить `localStorage` ключ `console:client_id`, если выбранный клиент удалён.
- Решение: оставить одну связку `agent_identities` для нужного клиента или использовать `X-Client-Id`.

**400 BRANCH_SELECTION_REQUIRED**
- Роль branch‑scoped и доступно несколько филиалов.
- `/console/v1/me` вернул `branch_selection_required=true` → выбрать филиал или передать `X-Branch-Id`.
- Очистить `localStorage` ключ `console:branch_id`, если выбранный филиал удалён.

**502 /api/proxy/**
- `NEXT_PUBLIC_API_URL` не задан или API недоступен.
- Проверить `console-web/.env.local` и доступность `https://api.truffles.kz/console/v1`.

**Empty “Cases”**
- Check `handovers` count by `client_id`.
- Verify admin is mapped to correct tenant.

**Empty “Calendar”**
- Check `specialists` and `bookings` for tenant.

**Slow “Cases”**
- Validate DB indexes on `handovers(client_id, created_at)` and `conversations(branch_id)`.

---

## 8) Related Canon Docs

- `SPECS/MULTI_TENANT.md` — tenant boundaries and branch routing.
- `contracts/tenancy/tenant_context.v1.jsonschema` — canonical tenant context contract.
- `TECH.md` — console env + deploy commands.
- `docs/PROCESSES.md` — contract map and core flows.
- `contracts/console_api/*` — API contract source of truth.
