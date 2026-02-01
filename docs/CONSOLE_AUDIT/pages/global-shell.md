# Page: Global shell, auth, and context

Route / Layout
- All console pages are wrapped by `ConsoleShell` (`console-web/src/components/ConsoleShell.tsx`).
- Public (unauthenticated) view is `PublicLanding` with SSO login button.

Primary UI regions
- Sidebar (desktop): logo, collapse toggle, role label, nav links.
- Header (sticky): Context Bar (Company/Client/Branch) + session status + Login/Logout button.
- Mobile nav: horizontal pill buttons under header (same nav as sidebar).

Navigation items (labels and routes)
- Тенанты (`/tenants`)
- Заявки (`/`)
- Записи (`/calendar`)
- Знания (`/knowledge`)
- Команда (`/team`)
- Статус (`/ops`)
- Журнал (`/audit`)
- Настройки (`/settings`)

Nav visibility rules
- Filtered by role using `canAccessConsole` and `ConsoleRBAC` (`console-web/src/lib/api-client.ts`).
- Active route highlights (exact `/` for inbox, prefix match for others).

Context bar
- Shows Company / Client / Branch and selectors when multiple options exist.
- Uses `authApi.getMe()` to fetch companies/clients/branches (`console-web/src/lib/api-client.ts`).
- Selection writes to localStorage and triggers refetch + cache invalidation:
  - `console:company_id`
  - `console:client_id`
  - `console:branch_id`
- Company selection clears client + branch; client selection clears branch.
- Branch selector includes "Все филиалы" when `branch_selection_required` is false.

Selection gate (blocking state)
- If `/console/v1/me` returns any of:
  - `company_selection_required`
  - `selection_required`
  - `branch_selection_required`
  UI blocks content and shows a required selection card.
- Confirm buttons write selection to localStorage and refetch `/console/v1/me`.

Session controls
- Login via Keycloak (`LoginButton`, `console-web/src/components/LoginButton.tsx`).
- Logout clears localStorage (company/client/branch) and calls `signOut()`.

Content width
- Inbox pages (`/` and `/cases/*`) use a wider max width (`max-w-[1440px]`).
- Other pages use `max-w-6xl`.

API / data interactions
- `/console/v1/me` returns role + tenant context; enforced by `get_console_context` (`truffles-api/app/services/console_auth.py`).
- Headers are set by `console-web/src/lib/api.ts` and proxy route:
  - `X-Company-Id`, `X-Client-Id`, `X-Branch-Id`.

Related components
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/components/LoginButton.tsx`
- `console-web/src/components/AccessDenied.tsx`
