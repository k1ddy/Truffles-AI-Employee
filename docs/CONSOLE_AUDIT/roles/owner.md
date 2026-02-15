# Role: owner

Scope
- Implemented UI access for owner.
- Source: `console-web/src/lib/api-client.ts`, `console-web/src/components/ConsoleShell.tsx`.

Navigation (sidebar + mobile)
- Заявки (`/`)
- Записи (`/calendar`)
- Знания (`/knowledge`)
- Команда (`/team`)
- Статус (`/ops`)
- Журнал (`/audit`)
- Аналитика (`/insights`)
- Бизнес (`/business`)
- Данные (`/business/data-trust`)
- Команда KPI (`/business/team-performance`)
- Подписка (`/subscription`)
- Настройки (`/settings`)

Access summary (RBAC)
- Inbox: read/write (take/resolve/send, macros, diagnostics).
- Calendar: read/write (slots, bookings, create booking).
- Knowledge: read/write (validate/publish/rollback).
- Team: read/write (users list + Telegram link tokens).
- Settings: read/write (provisioning wizard + Telegram verify/test + bot config view).
- Ops: read/write (outbox retry, telegram verify/test).
- Audit: read-only.
- Insights: read-only (daily metrics).
- Business: read-only (owner/admin business summary + action queue).
- Data Trust: read-only (quality completeness, knowledge freshness, critical audit pressure).
- Team Performance: read-only (stale queue pressure, manager responsiveness, manager workload).
- Subscription: read-only (quota/usage/projection + billable evidence).

Selection gates
- Context selection gates (company/client/branch) are enforced by `/console/v1/me` and surfaced in `ConsoleShell`.
- Knowledge page enforces branch selection when branch context is missing.

Key UI actions
- Inbox
  - Take/resolve case: `POST /console/v1/cases/{id}/take|resolve`.
  - Send messages/media: `POST /console/v1/conversations/{id}/messages` and `/messages/media`.
  - View Diagnostics tab in case details.
- Knowledge
  - Validate/publish/rollback (requires confirmation for rollback).
- Settings
  - Provisioning Wizard (`ProvisioningWizard` with `accessSection="settings"`).
  - Telegram verify/test (client + branch scope).
- Ops
  - Outbox retry (`POST /console/v1/ops/outbox/retry`).
- Business
  - Business summary (`GET /console/v1/business/summary`).
- Data Trust
  - Data trust summary (`GET /console/v1/business/data-trust`).
- Team Performance
  - Team performance summary (`GET /console/v1/business/team-performance`).
- Subscription
  - Subscription summary (`GET /console/v1/subscription/summary`).

Code references
- RBAC: `console-web/src/lib/api-client.ts`, `truffles-api/app/services/console_auth.py`.
- Navigation + gates: `console-web/src/components/ConsoleShell.tsx`.
