# Role: manager

Scope
- Implemented UI access for manager (branch-scoped operations).
- Source: `console-web/src/lib/api-client.ts`, `console-web/src/components/ConsoleShell.tsx`.

Navigation (sidebar + mobile)
- Заявки (`/`)
- Записи (`/calendar`)
- Знания (`/knowledge`)

Access summary (RBAC)
- Inbox: read/write (take/resolve/send). No Diagnostics tab.
- Calendar: read/write (slots, bookings, create booking).
 - Knowledge: read-only (manager can view, cannot publish/rollback).
- Team/Settings/Ops/Audit/Tenants: no access.

Selection gates
- Branch selection is required when multiple branches are available; UI blocks until a branch is chosen.
- Context selection lives in `ConsoleShell` and is enforced by `/console/v1/me`.

Key UI actions
- Inbox
  - Take/resolve/return-to-bot: `POST /console/v1/cases/{id}/take|resolve|return`.
  - Send messages/media: `POST /console/v1/conversations/{id}/messages` and `/messages/media`.
  - Quick replies/macros: allowed (canWriteInbox true).
  - Message history pagination: `GET /console/v1/cases/{id}/messages?cursor=...&limit=...`.
- Calendar
  - View specialists, slots, and create bookings.

Manager UX specifics
- Queue counter reflects loaded vs total cases from backend (`CaseListResponse.total`).
- Chat shows "Загрузить старые" for long dialogs and keeps scroll position when loading history.
- "Взять/Закрыть/Вернуть боту" actions surface sync warnings when Telegram/client notify fails.
- Delivery risk hints are shown directly in conversation header (`has_delivery_error`, `has_pending_outbox`).

Code references
- RBAC: `console-web/src/lib/api-client.ts`, `truffles-api/app/services/console_auth.py`.
- Navigation + gates: `console-web/src/components/ConsoleShell.tsx`.
