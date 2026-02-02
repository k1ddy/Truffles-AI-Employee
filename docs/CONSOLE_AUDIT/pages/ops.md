# Page: Ops (System status)

Route
- `/ops`

UI entry points
- `console-web/src/components/OpsPage.tsx`

Roles
- Read: platform_admin, owner, admin, support.
- Write (outbox retry, telegram verify/test): platform_admin, owner, admin.

Sections
- Overall health (version + status badge).
- Daily metrics (cases by status, avg resolution hours).
- Components (database, redis).
- Telegram health card (webhook, error rate, pending, last success).
- Outbox queue (failed/pending/processing/all with counts + retry actions).

Actions
- Auto refresh: health/telegram/outbox every 30s, metrics every 60s.
- Refresh health (manual "Обновить").
- Telegram verify/test (client scope, role-gated).
- Outbox retry (all failed or single item).
- Outbox filters: Failed / Pending / Processing / All chips with counts.
- Outbox table columns: status, attempts, channel, message preview, error, updated, retry action.

API endpoints used
- Health: `GET /console/v1/health`.
- Metrics: `GET /console/v1/metrics/daily`.
- Telegram health: `GET /console/v1/telegram/health`.
- Telegram verify/test: `POST /console/v1/telegram/verify|test`.
- Outbox list: `GET /console/v1/ops/outbox`.
- Outbox retry: `POST /console/v1/ops/outbox/retry`.

Backend handlers
- `truffles-api/app/routers/console.py`:
  - `get_health`, `get_metrics_daily`, `get_telegram_health`.
  - `list_outbox`, `retry_outbox`.

Data sources
- `outbox_messages` (queue status, counts).
- `metrics_daily` (daily counts).

Related code
- UI: `console-web/src/components/OpsPage.tsx`.
- Backend: `truffles-api/app/routers/console.py`.
