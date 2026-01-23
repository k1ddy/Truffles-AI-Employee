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

**Key:** One login = one `client_id`.  
Console uses `agent_identities` to map OIDC `sub` → `agents` → `client_id`.

**Access scope is enforced here:**
`truffles-api/app/services/console_auth.py` → `get_console_context()`

**Note (current limitation):**
Org-level access is not implemented yet. Company-level selection (company/client/branch) is planned per DEC-011
and requires membership/RBAC changes.

Rules:
- `sub` must exist in `agent_identities` (channel=`oidc`).
- Agent must be `is_active`.
- All queries filter by `context.client.id`.
- Non‑admin/owner users are restricted to their branch.
- Если один `sub` связан с несколькими клиентами → API вернёт
  `CLIENT_SELECTION_REQUIRED` (нужен `X-Client-Id`) либо надо убрать дубликаты.

**Common symptom:** “Only 1–2 cases shown / no slots.”  
Usually means the admin is mapped to the wrong `client_id`.

**Tables used:**
- `agent_identities` (OIDC identity mapping)
- `agents` (role, client, optional branch)
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

**Where to run:** `docs/DEV_SETUP.md` (Console tests section).

---

## 7) Debug & Troubleshooting

**403 ACCESS_DENIED**
- Check `agent_identities` mapping for `sub`.
- Verify `agents.is_active = true`.

**400 CLIENT_SELECTION_REQUIRED**
- Один `sub` связан с несколькими клиентами/агентами.
- Решение: оставить одну связку `agent_identities` для нужного клиента
  или добавить `X-Client-Id` в запросы.

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
- `TECH.md` — console env + deploy commands.
- `docs/PROCESSES.md` — contract map and core flows.
- `contracts/console_api/*` — API contract source of truth.
