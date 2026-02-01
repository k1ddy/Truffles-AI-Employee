# Role: platform_admin

Scope
- Implemented UI access for platform_admin (control plane + provisioning).
- Source: `console-web/src/lib/api-client.ts`, `console-web/src/components/ConsoleShell.tsx`.

Navigation (sidebar + mobile)
- Тенанты (`/tenants`)
- Заявки (`/`)
- Записи (`/calendar`)
- Знания (`/knowledge`)
- Команда (`/team`)
- Статус (`/ops`)
- Журнал (`/audit`)
- Настройки (`/settings`)

Access summary (RBAC)
- Inbox: read/write (take/resolve/send, macros, diagnostics).
- Calendar: read/write (slots, bookings, create booking).
- Knowledge: read/write (validate/publish/rollback).
- Team: read/write (users list + Telegram link tokens).
- Settings: read/write (provisioning wizard + Telegram verify/test + bot config view).
- Ops: read/write (outbox retry, telegram verify/test).
- Audit: read-only.
- Tenants: read/write (company/client/branch list + edit + provisioning wizard).

Selection gates
- Context selection gates (company/client/branch) are enforced by `/console/v1/me` and surfaced in `ConsoleShell`.
- If selection is required, UI blocks content until the context is confirmed.

Key UI actions (role-specific behavior)
- Inbox
  - Take/resolve case: `POST /console/v1/cases/{id}/take|resolve`.
  - Send messages/media: `POST /console/v1/conversations/{id}/messages` and `/messages/media`.
  - View Diagnostics tab in case details.
- Settings
  - Provisioning Wizard (`ProvisioningWizard` with `accessSection="settings"`).
  - Telegram verify/test (client + branch scope).
- Tenants
  - Edit company/client/branch; destructive changes require confirmation (`branch_deactivate`).
  - Provisioning Wizard (`accessSection="tenants"`).
- Ops
  - Outbox retry (`POST /console/v1/ops/outbox/retry`).
  - Telegram verify/test (client scope).

Code references
- RBAC: `console-web/src/lib/api-client.ts`, `truffles-api/app/services/console_auth.py`.
- Navigation + gates: `console-web/src/components/ConsoleShell.tsx`.
- Tenants page: `console-web/src/app/tenants/page.tsx`.
