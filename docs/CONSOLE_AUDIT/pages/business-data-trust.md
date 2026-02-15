# Page: Business Data Trust

Route
- `/business/data-trust`

UI entry points
- `console-web/src/app/business/data-trust/page.tsx`

Roles
- Read: `platform_admin`, `owner`, `admin` (`business:read`).

Purpose
- Owner/Admin view of data reliability: quality-metric completeness, knowledge freshness, audit incident pressure, and business actions.

Sections
- Header: update timestamp, metrics date, refresh CTA.
- Status card:
  - `healthy|degraded|unhealthy` with plain-language label,
  - scope warning when analytics are branch-limited.
- KPI cards:
  - `first_response_missing_total`,
  - `escalation_meta_missing_total`,
  - `intent_missing_total`,
  - `knowledge_stale_hours` + last published timestamp.
- Audit cards:
  - total audit events for 24h,
  - critical audit events for 24h (`failed|blocked|rejected`).
- Action queue:
  - prioritized business actions (`critical|warn|info`) with direct CTA to `knowledge|audit|insights|business`.

API endpoints used
- `GET /console/v1/me`
- `GET /console/v1/business/data-trust`

Backend handlers
- `truffles-api/app/routers/console.py`:
  - `get_business_data_trust`

Data sources
- `metrics_analytics_daily` (latest quality completeness fields when scope allows client-wide metrics).
- `knowledge_versions` (latest published knowledge freshness).
- `audit_events` (24h volume + critical event patterns).

Related code
- UI: `console-web/src/app/business/data-trust/page.tsx`
- API: `console-web/src/lib/api-client.ts`
- Router: `truffles-api/app/routers/console.py`
