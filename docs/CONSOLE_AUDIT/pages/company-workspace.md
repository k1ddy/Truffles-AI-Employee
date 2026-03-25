# Page: Company Workspace (Platform operations)

Route
- `/company-workspace`

UI entry points
- `console-web/src/app/company-workspace/page.tsx`

Roles
- Read/write: `platform_admin` only (uses `tenants` + `integrations` permissions).

Purpose
- Execution workspace for branch-level operational actions.
- Consolidates provider lifecycle, webhook contract actions, and go-live decisions.
- Works with strict branch scope and explicit operator intent.

Main UI sections
- Status cards (quick operational state snapshot for selected branch).
- Recommended action card:
  - Opens action in `execute` or `dry_run` mode.
  - Supports clear/reset.
  - Shows explicit next-step verify link to `Ops` after execute CTA.
  - Empty recommendation state includes return links to `Tenants` and `Integrations`.
- Today fact block (current-day operational summary for selected scope).
- Scope section (`company/client/branch`) with context save.
- WhatsApp panel:
  - branch phone + `instance_id` patch,
  - webhook secret/URL operations and copy helpers.
- Provider actions section:
  - action list (`start_rebind`, `complete_rebind`, renewal/webhook/reminder, reconcile),
  - execute modal with reason/notes and optional date fields.
- Hard-stop wizard:
  - onboarding scorecard checks,
  - go-live approve/reject/waive with required reason.

Safety controls
- Execute flow supports `dry_run` before mutate.
- Confirmation token flow is used for protected execute actions.
- Required reason fields for sensitive decisions (`go-live`, provider execute actions).
- Branch scope is mandatory for mutable actions.

Key UX behavior
- Long technical values are shortened in UI and support copy-to-clipboard.
- Context is persisted in localStorage:
  - `console:company_id`
  - `console:client_id`
  - `console:branch_id`
- Explicit handling for known API limit validation error (`limit 1..100`).

API endpoints used
- Read:
  - `GET /console/v1/me`
  - `GET /console/v1/admin/clients`
  - `GET /console/v1/admin/branches`
  - `GET /console/v1/admin/integrations`
  - `GET /console/v1/admin/provider-lifecycle`
  - `GET /console/v1/onboarding/scorecard`
- Mutate:
  - `POST /console/v1/confirmations`
  - `POST /console/v1/admin/integrations/{branch_id}/reconcile`
  - `PATCH /console/v1/admin/branches/{id}`
  - `GET /console/v1/admin/webhook-secret`
  - `POST /console/v1/admin/branches/{id}/go-live/approve`
  - `POST /console/v1/admin/branches/{id}/go-live/reject`
  - `POST /console/v1/admin/branches/{id}/go-live/waive`

Backend handlers
- `truffles-api/app/routers/console.py`:
  - integrations reconcile execute path
  - branch patch/go-live decisions
  - webhook secret endpoints
  - onboarding scorecard endpoint

Related code
- UI: `console-web/src/app/company-workspace/page.tsx`
- Nav/RBAC: `console-web/src/components/ConsoleShell.tsx`, `console-web/src/lib/api-client.ts`

Related tests
- API: `truffles-api/tests/test_console_integrations_registry.py`
- API: `truffles-api/tests/test_console_access_admin_pr2.py`
- E2E smoke: `console-web/e2e/smoke.spec.ts` (`/company-workspace` navigation checks)
