# Console Post-Merge Acceptance + p95 (Wave123)

Date
- 2026-02-17

Scope
- Post-merge acceptance for business-critical Console roles.
- Capture p95 navigation/readiness timings from live Console.

Environment
- Console: `https://console.truffles.kz`
- API: `https://api.truffles.kz`
- Auth state: `console-web/.auth/console.json` (platform_admin)

## 1) Role Acceptance (post-merge)

Platform Admin runtime/control snapshots
- `python3 ops/console_platform_admin_kpi_snapshot.py --pretty --output /tmp/platform_admin_kpi_20260217_postmerge_wave123.json`
- Result: `runtime.guards.outbox.status=critical`
- Facts:
  - `outbox.pending=1983`
  - `outbox.failed=1785`
  - `console health status=unhealthy` (`503`)

Owner/Admin runtime snapshot
- `python3 ops/console_owner_admin_kpi_snapshot.py --client-slug demo_salon --pretty --output /tmp/owner_admin_kpi_20260217_postmerge_wave123_t0.json`
- Result: `kpi.guard.status=critical`
- Fact driver: `outbox_backlog=1983` (other KPI dimensions are `ok`)

Playwright acceptance (platform_admin)
- Partial pass (stable):
  - Incident banner flow: `PASS`
  - Integrations -> Company Workspace navigation: `PASS`
- Full suite result:
  - `2 passed / 6 failed`
  - failing area: all Tenants flows fail in `openTenants()` with URL stuck at `/`
  - command: `PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz npx playwright test e2e/platform-admin.spec.ts --project=chromium --no-deps --reporter=list`

Owner/Admin UI suite
- Blocked by role mismatch in current auth state (`platform_admin`), not owner/admin identity.
- command: `PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz npx playwright test e2e/owner-admin-business.spec.ts --project=chromium --no-deps --reporter=list`
- key failure: `nav-owner-admin-toggle` not visible.

## 2) p95 Utility Timings

Browser timing probe (live console, 12 runs)
- artifact: `/tmp/console_ui_p95_postmerge_wave123_20260217.json`
- metrics:
  - `page_ready_ms`: `p50=58`, `p95=222`, `avg=73`
  - `nav_to_integrations_ms`: `p50=5431`, `p95=7977`, `avg=5859`
  - `nav_back_cases_ms`: `p50=92`, `p95=112`, `avg=94`
- notes:
  - `nav_click_fallbacks_used=12`
  - `context_switch_not_measurable` (current account has single active client context)

Direct route load probe (to isolate page load vs nav click)
- artifact: `/tmp/console_ui_direct_nav_p95_postmerge_wave123_20260217.json`
- metrics:
  - `goto_integrations_ms`: `p50=239`, `p95=1391`, `avg=385`
  - `goto_tenants_ms`: `p50=1419`, `p95=2413`, `avg=1494`
  - `goto_cases_ms`: `p50=859`, `p95=1884`, `avg=843`

Interpretation
- Main UX regression is not pure page rendering time.
- Primary defect is navigation reliability: sidebar click for `Tenants` often becomes no-op, which inflates user-perceived latency and causes repeated clicks.

## Code Changes for Stabilization

Navigation fail-safe
- `console-web/src/components/ConsoleShell.tsx`
- Added fallback in `navigateFromNav`: if client-side route transition does not change pathname within timeout, force hard navigation (`window.location.assign`).

E2E local auth-origin stabilization
- `console-web/e2e/auth.setup.ts`
- `console-web/e2e/login.spec.ts`
- `console-web/e2e/platform-admin.spec.ts`
- `console-web/e2e/owner-admin-business.spec.ts`
- `console-web/e2e/smoke.spec.ts`
- Added origin resolution helper for local base URL to avoid unstable cross-origin sign-in transitions during local acceptance.

## Validation

Build/lint
- `npm --prefix console-web run lint` -> pass
- `npm --prefix console-web run build` -> pass

Targeted smoke (platform_admin)
- `PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz npx playwright test e2e/platform-admin.spec.ts --project=chromium --no-deps --grep "Incident Banner|navigate from Integrations row" --reporter=list` -> `2 passed`

