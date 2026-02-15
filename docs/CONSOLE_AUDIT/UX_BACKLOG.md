# Web Console UX Backlog (Platform Admin focus)

Scope
- Platform Admin operating surface in Console Plane (`Tenants`, `Integrations`, `Company Workspace`, control-plane e2e).
- Fact-only: each item references runtime/code evidence.

Evidence sources
- `docs/REPORTS/2026-02-15-platform-admin-baseline-v2.md`
- `console-web/e2e/smoke.spec.ts`
- `console-web/e2e/platform-admin.spec.ts`
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/components/ProvisioningWizard.tsx`
- `truffles-api/app/routers/console.py`

## Priority backlog

| ID | Priority | Area | Problem | Impact | Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| UX-08 | P0 | Runtime health | Console health stays `unhealthy`; outbox backlog remains high (`pending=1639`, `failed=676`) for Platform Admin observation windows. | Platform Admin sees degradation but recovery remains reactive. | `curl https://console.truffles.kz/api/health/full` (2026-02-15) in `docs/REPORTS/2026-02-15-platform-admin-baseline-v2.md`. | Open |
| UX-09 | P0 | QA reliability | Platform Admin-critical e2e tests were concentrated inside `smoke.spec.ts`, causing noisy failures and slower triage. | High false triage cost for core admin regressions. | Baseline: `smoke.spec.ts` 1451 lines before split. | Fixed |
| UX-10 | P1 | Error clarity | Error feedback is still toast-heavy on `tenants` and `company-workspace`; operators lose contextual recovery hints. | Slow incident handling and repeated user actions. | `toast.error` count snapshot in baseline report (`tenants`: 23, `company-workspace`: 8). | Open |
| UX-11 | P1 | API maintainability | `console.py` remains a 12k+ LOC router with mixed concerns. | Slow onboarding and high regression probability for Platform Admin APIs. | LOC snapshot in baseline report (`truffles-api/app/routers/console.py`: 12066). | Open |
| UX-12 | P1 | Provisioning UX complexity | `ProvisioningWizard.tsx` remains a 4.9k LOC multi-domain component. | Hard to ship safe improvements fast across onboarding paths. | LOC snapshot in baseline report (`console-web/src/components/ProvisioningWizard.tsx`: 4945). | Open |
| UX-13 | P2 | Governance loop | No standard weekly control-loop runbook existed for Platform Admin KPI snapshots and anti-drift artifacts. | Inconsistent evidence quality between sessions. | New runbook and script introduced in this wave. | Fixed |

## 30-day execution waves

1. Wave A (P0): stabilize runtime recovery loop for outbox backlog and expose alert thresholds in Platform Admin runbook.
2. Wave B (P0/P1): keep Platform Admin e2e isolated (`platform-admin.spec.ts`) and add CI lane-level ownership.
3. Wave C (P1): reduce error-surface entropy in `tenants` and `company-workspace` (contextual inline errors, not only toasts).
4. Wave D (P1): start router/component decomposition (`console.py`, `ProvisioningWizard.tsx`) with contract tests guarding behavior.

## This wave delivery (2026-02-15)

- Moved Platform Admin smoke scenarios into dedicated `console-web/e2e/platform-admin.spec.ts`.
- Reduced `console-web/e2e/smoke.spec.ts` from 1451 to 1146 lines.
- Added repeatable KPI snapshot tool: `ops/console_platform_admin_kpi_snapshot.py`.
- Added weekly operating runbook: `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`.
