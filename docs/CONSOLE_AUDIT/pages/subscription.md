# Page: Subscription

Route
- `/subscription`

UI entry points
- `console-web/src/app/subscription/page.tsx`

Roles
- Read: `platform_admin`, `owner`, `admin`.

Purpose
- Owner/Admin transparent subscription view: contract terms, payment status, usage meters, actionable next steps, and billable evidence rows.

Sections
- Header: billing period + next billing date + refresh.
- KPI cards:
  - plan/contract/source,
  - monthly quota + currency,
  - billable messages + remaining quota,
  - projected month total + quota usage.
- Contract & payment:
  - payment status from onboarding contract,
  - explicit default baseline (`Starter`, `1000` messages, `1` WhatsApp),
  - source tagging for plan/payment fields.
- Meters:
  - per-meter view (`messages/channels/add-ons`) with `included/used/remaining/status/source`,
  - statuses: `ok|warning|limit_reached|over_limit|not_included|included_not_configured|unknown`.
- Recommended actions:
  - server-driven `recommended_actions` for owner/admin (`critical|warn|info`) with direct CTA.
- Alert band:
  - `quota_alert_level` (`normal|warning_80|limit_100`),
  - human-readable `quota_alert_message`,
  - explicit overage rule from canon (`overage = max(0, billable - quota)`).
- Usage bar:
  - `usage_percent`,
  - `over_quota` state.
- Forecast v2:
  - projected remaining quota,
  - projected overage messages,
  - next billing date.
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
- `client_onboarding_contracts` for payment status + purchased channels/features.
- `client_capabilities` + active branch settings for configured add-on/channel usage facts.

Related code
- UI: `console-web/src/app/subscription/page.tsx`
- Shell/nav: `console-web/src/components/ConsoleShell.tsx`
- RBAC: `console-web/src/lib/api-client.ts`, `truffles-api/app/services/console_auth.py`
