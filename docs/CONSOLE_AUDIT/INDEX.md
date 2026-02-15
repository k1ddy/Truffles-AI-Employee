# Web Console Audit (implemented UI)

Scope
- Implementation-backed inventory of the Web Console (UI + API + data flows).
- Only implemented behavior is documented; canon/plan items are excluded.

Sources (code-backed)
- UI shell + nav: `console-web/src/components/ConsoleShell.tsx`
- Pages: `console-web/src/app/*/page.tsx`, `console-web/src/components/*`
- Console API: `truffles-api/app/routers/console.py`
- Calendar API: `truffles-api/app/routers/calendar.py`
- Auth/RBAC: `console-web/src/lib/api-client.ts`, `truffles-api/app/services/console_auth.py`
- Proxy/auth: `console-web/src/app/api/proxy/[...path]/route.ts`, `console-web/src/lib/auth.ts`

How to use
- Start with Roles to see navigation and access per role.
- Use Pages for UI element-level behavior and endpoints.
- Use System notes for cross-component flows (WhatsApp/Telegram/outbox/knowledge).
- Use Canon vs Implemented for gap tracking against Control Plane canon.

Comparison
- `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`

Reports
- `docs/REPORTS/2026-02-01-console-web-fact-audit.md`
- `docs/REPORTS/2026-02-15-platform-admin-baseline-v1.md`

Backlog
- `docs/CONSOLE_AUDIT/UX_BACKLOG.md`

Roles
- `docs/CONSOLE_AUDIT/roles/platform_admin.md`
- `docs/CONSOLE_AUDIT/roles/owner.md`
- `docs/CONSOLE_AUDIT/roles/admin.md`
- `docs/CONSOLE_AUDIT/roles/manager.md`
- `docs/CONSOLE_AUDIT/roles/support.md`

Pages
- `docs/CONSOLE_AUDIT/pages/global-shell.md`
- `docs/CONSOLE_AUDIT/pages/inbox.md`
- `docs/CONSOLE_AUDIT/pages/case-detail.md`
- `docs/CONSOLE_AUDIT/pages/calendar.md`
- `docs/CONSOLE_AUDIT/pages/knowledge.md`
- `docs/CONSOLE_AUDIT/pages/team.md`
- `docs/CONSOLE_AUDIT/pages/settings.md`
- `docs/CONSOLE_AUDIT/pages/audit.md`
- `docs/CONSOLE_AUDIT/pages/ops.md`
- `docs/CONSOLE_AUDIT/pages/insights.md`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/CONSOLE_AUDIT/pages/integrations.md`
- `docs/CONSOLE_AUDIT/pages/company-workspace.md`

System
- `docs/CONSOLE_AUDIT/system/auth-and-proxy.md`
- `docs/CONSOLE_AUDIT/system/integrations-and-data.md`

Maintenance
- Update the relevant role/page doc when UI text, actions, or endpoints change.
- Add new pages to the Pages list and link to code in the new doc.
