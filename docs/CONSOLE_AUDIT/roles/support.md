# Role: support

Scope
- Implemented UI access for support (read-only troubleshooting).
- Source: `console-web/src/lib/api-client.ts`, `console-web/src/components/ConsoleShell.tsx`.

Navigation (sidebar + mobile)
- Заявки (`/`)
- Статус (`/ops`)
- Журнал (`/audit`)

Access summary (RBAC)
- Inbox: read-only (no take/resolve/send). Diagnostics tab is visible.
- Ops: read-only (no outbox retry).
- Audit: read-only.
- Calendar/Knowledge/Team/Settings/Tenants: no access.

Selection gates
- Context selection gates (company/client/branch) are enforced by `/console/v1/me`.

Key UI actions
- Inbox
  - View case details, decision trace, and Telegram trail (Diagnostics tab).
  - Cannot take/resolve or send messages.
- Ops
  - View health/metrics/telegram status/outbox; retry disabled.

Code references
- RBAC: `console-web/src/lib/api-client.ts`, `truffles-api/app/services/console_auth.py`.
- Navigation + gates: `console-web/src/components/ConsoleShell.tsx`.
