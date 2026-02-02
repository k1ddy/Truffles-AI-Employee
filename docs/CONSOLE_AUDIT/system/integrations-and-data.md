# System: Integrations and data flows (implemented)

Inbox take/resolve
- UI actions: `POST /console/v1/cases/{id}/take|resolve`.
- Backend: `truffles-api/app/routers/console.py` (`take_case`, `resolve_case`).
- Uses `state_service` to change handover state.
- Side effects:
  - Audit events (`record_audit_event`).
  - Telegram sync (`_sync_telegram_after_take|close`).
  - Client notify (`notify_client_manager_status`).

Manager message (text)
- UI: `POST /console/v1/conversations/{id}/messages`.
- Backend: `send_manager_message`.
- Side effects:
  - Create `messages` row with `role=manager`.
  - Send to WhatsApp via `chatflow_service.send_bot_response`.
  - Telegram echo to topic (if present).

Manager message (media)
- UI: `POST /console/v1/conversations/{id}/messages/media` (multipart).
- Backend: `send_manager_media` → `process_console_media_upload`.
- Side effects:
  - Store media + create message metadata (`message_metadata.media`).
  - Send to WhatsApp; echo to Telegram when possible.
  - Video is blocked at UI and backend.

Knowledge publish
- UI: `POST /console/v1/knowledge/publish`.
- Backend: `publish_version`, `sync_qdrant_from_pack`.
- Side effects: pack compile + publish, Qdrant sync, audit.

Outbox ops
- UI: `GET /console/v1/ops/outbox`, `POST /console/v1/ops/outbox/retry`.
- Backend: reads/writes `outbox_messages` with status normalization.

Calendar
- UI: `GET /calendar/specialists`, `GET /calendar/slots`, `POST /calendar/bookings`.
- Backend: `SchedulingService` (appointments) + specialist/services models.

Primary data tables
- Cases: `handovers`, `conversations`, `messages`, `users`.
- Inbox macros: `console_macros`.
- Settings: `client_settings`, `branches`.
- Provisioning: `companies`, `clients`, `branches`, `agents`, `agent_identities`.
- Knowledge: `knowledge_versions`.
- Ops: `outbox_messages`, `metrics_daily`.
- Calendar: `specialists`, `appointments`, `appointment_services`, `appointment_sync_state`.
