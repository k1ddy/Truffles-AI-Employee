# Page: Business

Route
- `/business`

UI entry points
- `console-web/src/app/business/page.tsx`

Roles
- Read: `platform_admin`, `owner`, `admin`.

Purpose
- Owner/Admin one-screen business status: delivery risk, unresolved cases, response speed, visit outcomes, and top actions.

Sections
- Header: generated timestamp + manual refresh.
- Business status card:
  - status chip (`healthy|degraded|unhealthy`),
  - plain-language status label.
- KPI cards:
  - visits today: planned, arrived, no-show, cancelled, arrival rate.
  - operations today: reminder delivery failures, no-show without manager follow-up.
  - outbox backlog + failed 24h,
  - unresolved cases (`pending` + `active`),
  - response speed (`first_response_p90_seconds`) + oldest unresolved age.
- Action queue:
  - prioritized actions with severity (`critical|warn|info`) and route CTA.
- Wave-2 shortcuts:
  - `Data Trust` (`/business/data-trust`),
  - `Team Performance` (`/business/team-performance`).

API endpoints used
- `GET /console/v1/me`
- `GET /console/v1/business/summary`

Backend handlers
- `truffles-api/app/routers/console.py`:
  - `get_business_summary`

Data sources
- `appointments` (today outcomes: planned/arrived/no-show/cancelled + arrival rate).
- `appointment_audit` (no-show follow-up progress).
- `reminder_jobs` (today reminder delivery failures).
- `outbox_messages` (backlog, failed 24h).
- `handovers` (+ `conversations` when branch scope is restricted).
- `metrics_analytics_daily` (latest `first_response_p90_seconds`).

Related code
- UI: `console-web/src/app/business/page.tsx`
- UI subpages: `console-web/src/app/business/data-trust/page.tsx`, `console-web/src/app/business/team-performance/page.tsx`
- Shell/nav: `console-web/src/components/ConsoleShell.tsx`
- RBAC: `console-web/src/lib/api-client.ts`, `truffles-api/app/services/console_auth.py`
