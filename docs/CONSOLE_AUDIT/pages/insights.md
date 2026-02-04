# Page: Insights (Analytics)

Route
- `/insights`

UI entry points
- `console-web/src/app/insights/page.tsx`

Roles
- Read: platform_admin, owner, admin.

Sections
- Message volume (client inbound, bot replies).
- Daily metrics summary (total/pending/active/resolved, average resolution time).
- KPI tiles (truth-first: bot-closed, time saved estimate, booking conversion, first response p50/p90, after-hours coverage, escalation quality, losses/risks, top intents).
- KPI trends (7-day sparkline series).
- Date picker with refresh.

Actions
- Select date (daily slice).
- Refresh metrics.

API endpoints used
- Metrics: `GET /console/v1/metrics/daily` (optional `date=YYYY-MM-DD`).

Backend handlers
- `truffles-api/app/routers/console.py`:
  - `get_metrics_daily`.

Data sources
- `metrics_daily` (pre-aggregated message volume).
- `handovers`, `conversations` (daily case metrics).

Related code
- UI: `console-web/src/app/insights/page.tsx`.
- Backend: `truffles-api/app/routers/console.py`.
