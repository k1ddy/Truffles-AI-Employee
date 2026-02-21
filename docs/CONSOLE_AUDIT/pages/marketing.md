# Page: Marketing

Routes
- `/marketing`

UI entry points
- `console-web/src/app/marketing/page.tsx`
- `console-web/src/lib/api-client.ts`

Roles
- Read: `platform_admin`, `owner`, `admin`.
- Write: `platform_admin`, `owner`, `admin`.

Layout
- Left panel: campaign creation + campaign list.
- Right panel: selected campaign lifecycle controls + preflight + audience + diagnostics.

Campaign create
- Fields: `name`, `segment_code`, `message_text`, `branch_id`.
- Segment choices:
  - `reactivation_30_120`
  - `no_show_recovery_14d`
  - `engaged_no_booking_7d`
- Action: `Создать кампанию`.

Campaign lifecycle controls
- Preview:
  - `sample_limit` input.
  - Action: `Preview аудитории`.
- Approval:
  - Optional audit reason.
  - Actions: `На ревью`, `Approve`, `Pause`, `Resume`.
- Execute:
  - `max_recipients` input.
  - Action: `Refresh preflight`.
  - Action: `Confirm & Execute` (enabled only for `approved|scheduled` + valid preflight).
- Retry:
  - Action: `Retry failed`.

Preflight panel
- Displays:
  - `preflight_valid`
  - `outbox_health_status`
  - `audience_total`
  - `eligible_count`
  - `suppressed_count`
  - `blocked_reasons`
- Blocked reasons are rendered as explicit badges; execute remains disabled when preflight is invalid.

Audience panel
- Controls:
  - `include_suppressed` toggle.
  - `limit` input.
  - `Reload audience` action.
- Table columns:
  - `recipient_jid` + `segment_code`
  - `conversation_id` / `user_id`
  - `reason_codes`
  - `suppression_reasons` / eligible marker

Diagnostics panel
- Counters: `total`, `queued`, `sent`, `failed`, `replied`.
- Failed sample list: recipient/conversation, outbox status, last error.

API endpoints used (Console API)
- `GET /console/v1/admin/marketing/campaigns`
- `POST /console/v1/admin/marketing/campaigns`
- `POST /console/v1/admin/marketing/campaigns/{campaign_id}/preview`
- `GET /console/v1/admin/marketing/campaigns/{campaign_id}/audience`
- `POST /console/v1/admin/marketing/campaigns/{campaign_id}/request-approval`
- `POST /console/v1/admin/marketing/campaigns/{campaign_id}/approve`
- `GET /console/v1/admin/marketing/campaigns/{campaign_id}/preflight`
- `POST /console/v1/admin/marketing/campaigns/{campaign_id}/pause`
- `POST /console/v1/admin/marketing/campaigns/{campaign_id}/resume`
- `POST /console/v1/admin/marketing/campaigns/{campaign_id}/execute`
- `GET /console/v1/admin/marketing/campaigns/{campaign_id}/diagnostics`
- `POST /console/v1/admin/marketing/campaigns/{campaign_id}/retry-failed`

Backend handlers
- `truffles-api/app/routers/console.py`:
  - `list_marketing_campaigns`
  - `create_marketing_campaign`
  - `preview_marketing_campaign`
  - `get_marketing_campaign_audience`
  - `request_marketing_campaign_approval`
  - `approve_marketing_campaign`
  - `get_marketing_campaign_preflight`
  - `pause_marketing_campaign`
  - `resume_marketing_campaign`
  - `execute_marketing_campaign`
  - `get_marketing_campaign_diagnostics`
  - `retry_failed_marketing_campaign_deliveries`

Business logic
- `truffles-api/app/services/marketing/service.py`:
  - audience materialization by segment rules
  - suppression/consent/frequency/permanent-failure filtering
  - preflight generation
  - lifecycle transitions
  - execute and retry safety paths

Data sources
- `marketing_campaigns`
- `marketing_campaign_recipients`
- `marketing_campaign_deliveries`
- `marketing_delivery_events`
- `marketing_consents`
- `marketing_suppressions`
- `outbox_messages`
- `conversations`, `users`, `appointments`
