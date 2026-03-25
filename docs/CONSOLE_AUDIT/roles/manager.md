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
- Inbox workspace is sticky for 24h: filters/search/auto-refresh and last selected case are restored per manager scope.
- Inbox auto-opens a case when queue has visible items (saved case first, otherwise first in queue).
- Chat shows "Загрузить более ранние" for long dialogs and keeps scroll position when loading history.
- Case header includes SLA countdown and "Следующая заявка" action for fast queue handling.
- "Взять/Закрыть/Вернуть боту" actions surface sync warnings when Telegram/client notify fails.
- Delivery risk hints are shown directly in conversation header (`has_delivery_error`, `has_pending_outbox`).

Session policy
- Console session for manager path is configured for 24h JWT/session window.
- SessionProvider keepalive refetch runs every 5 minutes to reduce unexpected sign-outs during long shifts.

Code references
- RBAC: `console-web/src/lib/api-client.ts`, `truffles-api/app/services/console_auth.py`.
- Navigation + gates: `console-web/src/components/ConsoleShell.tsx`.
