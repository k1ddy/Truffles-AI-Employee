# Page: Subscription

Route
- `/subscription`

UI entry points
- `console-web/src/app/subscription/page.tsx`

Roles
- Read: `platform_admin`, `owner`, `admin`.

Purpose
- Owner/Admin transparent subscription view: period usage, quota posture, forecast, and billable evidence rows.

Sections
- Header: billing period + refresh.
- KPI cards:
  - plan/contract/source,
  - monthly quota + currency,
  - billable messages + remaining quota,
  - projected month total + quota usage.
- Usage bar:
  - `usage_percent`,
  - `over_quota` state.
- Evidence table:
  - recent billable outbox rows (`created_at`, `outbox_id`, `status`, provider status, inbound id).

API endpoints used
- `GET /console/v1/me`
- `GET /console/v1/subscription/summary`

Backend handlers
- `truffles-api/app/routers/console.py`:
  - `get_subscription_summary`

Data sources
- `outbox_messages` with billable filters from `Business/Sales/BILLING_COUNTING.md`.
- `companies.billing_info` and `clients.config.billing` for plan/quota metadata.

Related code
- UI: `console-web/src/app/subscription/page.tsx`
- Shell/nav: `console-web/src/components/ConsoleShell.tsx`
- RBAC: `console-web/src/lib/api-client.ts`, `truffles-api/app/services/console_auth.py`
