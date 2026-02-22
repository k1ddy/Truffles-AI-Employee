# Page: Marketing

Routes
- `/marketing`

UI entry points
- `console-web/src/app/marketing/page.tsx`
- `console-web/src/lib/api-client.ts`

Roles
- Read: `platform_admin`, `owner`, `admin`.
- Write: `platform_admin`, `owner`, `admin`.

Owner-first concept
- Маркетинг строится вокруг бизнес-цели (возврат, no-show recovery, интерес без записи).
- У каждого сегмента есть human-readable описание, формула и редактируемые параметры.
- Preview/Audience показывают не только коды, но и объяснения причин inclusion/suppression.

Segment catalog (new)
- Endpoint: `GET /console/v1/admin/marketing/segments`.
- Returns for each segment:
  - `label`, `short_label`, `description`, `summary`
  - `defaults`
  - `editable_fields` (`int`/`bool`, min/max/step).

Campaign create/update
- Create request:
  - `branch_id`, `name`, `message_text`, `segment_code`, `segment_params`, `audience_mode`.
- Update request:
  - `name`, `message_text`, `segment_code`, `segment_params`, `reason`.
- Validation:
  - `segment_params` валидируются на backend по выбранному `segment_code`.
  - unsupported keys/ranges -> `INVALID_PARAM`.
- Effect:
  - при update preview/audience snapshot сбрасывается и требует fresh preview.

Preview / Preflight / Audience
- Preview response now includes:
  - `segment_params`, `segment_summary`, `funnel`.
- Preflight response now includes:
  - `segment_params`, `segment_summary`, `blocked_reasons`, provider billing block signals.
- Audience recipient now includes:
  - `reason_codes` + `reason_hints`
  - `suppression_reasons` + `suppression_hints`.

Business meaning of segments
- `reactivation_30_120`:
  - клиенты без будущей записи, чей последний визит в окне `min_days_since_last_visit..max_days_since_last_visit`.
- `no_show_recovery_14d`:
  - клиенты с минимум `min_no_show_count` no-show в окне `no_show_window_days`, без будущей записи.
- `engaged_no_booking_7d`:
  - клиенты с engagement сигналами услуг/цен за `engagement_window_days`, без будущей записи.

How owners edit filters
- На форме кампании (create/edit) рендерятся поля `editable_fields` из segment catalog.
- Int-поля ограничены min/max.
- Bool-поля задаются чекбоксом.
- Сохранённые значения уходят в `segment_params` и используются в materialize preview.

Provider billing block behavior
- Если `provider_billing_blocked=true`, execute остаётся заблокирован.
- UI показывает явный блокер и указывает, что разблокировка возможна только после оплаты у провайдера.

API endpoints used
- `GET /console/v1/admin/marketing/segments`
- `GET /console/v1/admin/marketing/campaigns`
- `POST /console/v1/admin/marketing/campaigns`
- `PATCH /console/v1/admin/marketing/campaigns/{campaign_id}`
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
- `truffles-api/app/routers/console.py`
  - `get_marketing_segments_catalog`
  - campaign lifecycle handlers.
- `truffles-api/app/services/marketing/service.py`
  - segment params normalization/catalog/explainers
  - audience materialization using effective params
  - preflight and execute guards.

Data sources
- `marketing_campaigns`
- `marketing_campaign_recipients`
- `marketing_campaign_deliveries`
- `marketing_delivery_events`
- `marketing_consents`
- `marketing_suppressions`
- `outbox_messages`
- `conversations`, `users`, `appointments`
