# Page: Business

Route
- `/business`

UI entry points
- `console-web/src/app/business/page.tsx`

Roles
- Read: `platform_admin`, `owner`, `admin`.

Purpose
- Owner/Admin one-screen business status: delivery risk, unresolved cases, response speed, and top actions.

Sections
- Header: generated timestamp + manual refresh.
- Business status card:
  - status chip (`healthy|degraded|unhealthy`),
  - plain-language status label.
- KPI cards:
  - outbox backlog + failed 24h,
  - unresolved cases (`pending` + `active`),
  - response speed (`first_response_p90_seconds`) + oldest unresolved age.
- Action queue:
  - prioritized actions with severity (`critical|warn|info`) and route CTA.

API endpoints used
- `GET /console/v1/me`
- `GET /console/v1/business/summary`

Backend handlers
- `truffles-api/app/routers/console.py`:
  - `get_business_summary`

Data sources
- `outbox_messages` (backlog, failed 24h).
- `handovers` (+ `conversations` when branch scope is restricted).
- `metrics_analytics_daily` (latest `first_response_p90_seconds`).

Related code
- UI: `console-web/src/app/business/page.tsx`
- Shell/nav: `console-web/src/components/ConsoleShell.tsx`
- RBAC: `console-web/src/lib/api-client.ts`, `truffles-api/app/services/console_auth.py`
