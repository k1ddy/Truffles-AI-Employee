# Page: Integrations (Fleet control)

Route
- `/integrations`

UI entry points
- `console-web/src/app/integrations/page.tsx`

Roles
- Read/write: `platform_admin` only (`integrations` section in RBAC).

Purpose
- Fleet-first read model for platform operations.
- Fast triage by `company/client/branch` scope.
- Redirect mutable actions to `/company-workspace`.

Main UI sections
- View mode switch:
  - `Обзор` (matrix + KPI + queue).
  - `Сегодня` (focus on current-day operational list).
- Workspace CTA (`Manage in Workspace`) with routing to `/company-workspace`.
- Scope controls (`company/client/branch`, stale threshold, reset/sync/save).
- KPI cards (coverage/readiness/risk style metrics).
- Fleet attention list (priority branches requiring action).
- Provider ops queue (items with direct `Open in Workspace` CTA).
- Branch matrix (card rows with status chips and context).
- Pagination controls (`Load more`) for integrations/provider lifecycle datasets.

Key behavior
- Page is read-oriented: no direct provider execute actions are performed on this route.
- Context scope is persisted to localStorage:
  - `console:company_id`
  - `console:client_id`
  - `console:branch_id`
- Page uses explicit limit guards and shows truncation warning when list cap is hit.

API endpoints used
- `GET /console/v1/me`
- `GET /console/v1/admin/companies`
- `GET /console/v1/admin/clients`
- `GET /console/v1/admin/branches`
- `GET /console/v1/admin/integrations`
- `GET /console/v1/admin/provider-lifecycle`
- `GET /console/v1/admin/memberships`
- `GET /console/v1/admin/fleet/attention`

Backend handlers
- `truffles-api/app/routers/console.py`:
  - `list_integrations`
  - `list_provider_lifecycle`
  - `list_memberships`
  - `list_fleet_attention`

Related code
- UI: `console-web/src/app/integrations/page.tsx`
- Nav/RBAC: `console-web/src/components/ConsoleShell.tsx`, `console-web/src/lib/api-client.ts`
- Types: `console-web/src/types/api.generated.ts`

Related tests
- API: `truffles-api/tests/test_console_integrations_registry.py`
- API: `truffles-api/tests/test_console_fleet_attention.py`
- E2E smoke: `console-web/e2e/smoke.spec.ts` (`Integrations` coverage)
