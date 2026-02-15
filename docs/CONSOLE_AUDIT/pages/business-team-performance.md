# Page: Business Team Performance

Route
- `/business/team-performance`

UI entry points
- `console-web/src/app/business/team-performance/page.tsx`

Roles
- Read: `platform_admin`, `owner`, `admin` (`business:read`).

Purpose
- Owner/Admin team-accountability view: open workload, stale queue pressure, manager response velocity, and load-balancing actions.

Sections
- Header: update timestamp, metrics date, refresh CTA.
- Status card:
  - `healthy|degraded|unhealthy` with plain-language label,
  - scope warning for branch-limited KPI context.
- KPI cards:
  - `unresolved_cases`,
  - `unresolved_older_than_60m`,
  - `manager_median_response_seconds`,
  - `first_response_p90_seconds`.
- Manager table:
  - manager label,
  - unresolved/pending/active counts,
  - oldest unresolved age,
  - average first response for last 30 days.
- Action queue:
  - prioritized actions (`critical|warn|info`) with CTA to `inbox|team|insights`.

API endpoints used
- `GET /console/v1/me`
- `GET /console/v1/business/team-performance`

Backend handlers
- `truffles-api/app/routers/console.py`:
  - `get_business_team_performance`

Data sources
- `handovers` + `conversations` branch scope filters (workload and stale queue).
- `metrics_analytics_daily` (latest manager-level responsiveness metrics where scope allows).

Related code
- UI: `console-web/src/app/business/team-performance/page.tsx`
- API: `console-web/src/lib/api-client.ts`
- Router: `truffles-api/app/routers/console.py`
