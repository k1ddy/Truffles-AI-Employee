# Web Console UX Backlog (Platform Admin + Owner/Admin focus)

Scope
- Platform Admin operating surface in Console Plane (`Tenants`, `Integrations`, `Company Workspace`, control-plane e2e).
- Owner/Admin business control surface (`Insights`, `Ops`, `Settings`, `Audit`) for non-technical operators.
- Fact-only: each item references runtime/code evidence.

Evidence sources
- `docs/REPORTS/2026-02-15-platform-admin-baseline-v2.md`
- `docs/REPORTS/2026-02-15-platform-admin-baseline-v3.md`
- `docs/REPORTS/2026-02-15-owner-admin-business-control-plane-v1.md`
- `Business/Sales/BILLING_COUNTING.md`
- `docs/CONSOLE_AUDIT/roles/owner.md`
- `docs/CONSOLE_AUDIT/roles/admin.md`
- `docs/CONSOLE_AUDIT/pages/insights.md`
- `docs/CONSOLE_AUDIT/pages/ops.md`
- `console-web/e2e/smoke.spec.ts`
- `console-web/e2e/platform-admin.spec.ts`
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/components/ProvisioningWizard.tsx`
- `truffles-api/app/routers/console.py`

## Priority backlog

| ID | Priority | Area | Problem | Impact | Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| UX-08 | P0 | Runtime health | Console health stays `unhealthy`; outbox backlog remains high (`pending=1653`, `failed=679`) for Platform Admin observation windows. | Platform Admin sees degradation but recovery remains reactive. | `curl https://console.truffles.kz/api/health/full` (`2026-02-15T08:06:10Z`) + `ops/console_platform_admin_kpi_snapshot.py` guard output in `docs/REPORTS/2026-02-15-platform-admin-baseline-v3.md`. | Mitigated (guard added), Open |
| UX-09 | P0 | QA reliability | Platform Admin-critical e2e tests were concentrated inside `smoke.spec.ts`, causing noisy failures and slower triage. | High false triage cost for core admin regressions. | Baseline: `smoke.spec.ts` 1451 lines before split. | Fixed |
| UX-10 | P1 | Error clarity | Validation and operator-input errors used toast-only on `tenants` and `company-workspace`; context recovery was not persistent on screen. | Slow incident handling and repeated user actions. | `reportValidationError` + inline summary in `console-web/src/app/tenants/page.tsx`, `console-web/src/app/company-workspace/page.tsx`; snapshot `toast.error` entries reduced to helper-only (`1/1`) in `docs/REPORTS/2026-02-15-platform-admin-baseline-v3.md`. | Fixed |
| UX-11 | P1 | API maintainability | `console.py` remains a 12k+ LOC router with mixed concerns. | Slow onboarding and high regression probability for Platform Admin APIs. | LOC snapshot in baseline report (`truffles-api/app/routers/console.py`: 12066). | Open |
| UX-12 | P1 | Provisioning UX complexity | `ProvisioningWizard.tsx` remains a 4.9k LOC multi-domain component. | Hard to ship safe improvements fast across onboarding paths. | LOC snapshot in baseline report (`console-web/src/components/ProvisioningWizard.tsx`: 4945). | Open |
| UX-13 | P2 | Governance loop | No standard weekly control-loop runbook existed for Platform Admin KPI snapshots and anti-drift artifacts. | Inconsistent evidence quality between sessions. | New runbook and script introduced in this wave. | Fixed |
| UX-14 | P0 | Owner billing transparency | Owner/Admin lacked dedicated UI for plan/quota/usage and evidence drill-down. | High dispute risk and low trust in subscription charges. | `console-web/src/app/subscription/page.tsx`, `truffles-api/app/routers/console.py` (`/subscription/summary`), `Business/Sales/BILLING_COUNTING.md`. | Fixed |
| UX-15 | P0 | Owner incident clarity | Runtime health risk was visible only in technical framing; owner path lacked business-language incident guidance. | Business owners discovered service degradation too late. | `console-web/src/components/ConsoleShell.tsx` (owner/admin incident text), `truffles-api/app/routers/console.py` (`/business/summary`). | Fixed |
| UX-16 | P1 | Data trust and manager accountability | Owner/Admin lacks a dedicated control surface for data-governance status and manager performance accountability. | Hard to answer client trust questions and improve team outcomes. | `docs/CONSOLE_AUDIT/pages/audit.md`, `docs/CONSOLE_AUDIT/pages/insights.md`, `docs/REPORTS/2026-02-15-owner-admin-business-control-plane-v1.md`. | Open |

## 30-day execution waves

1. Wave A (P0): stabilize runtime recovery loop for outbox backlog and expose alert thresholds in Platform Admin runbook.
2. Wave B (P0/P1): keep Platform Admin e2e isolated (`platform-admin.spec.ts`) and add CI lane-level ownership.
3. Wave C (P1): reduce error-surface entropy in `tenants` and `company-workspace` (contextual inline errors, not only toasts).
4. Wave D (P1): start router/component decomposition (`console.py`, `ProvisioningWizard.tsx`) with contract tests guarding behavior.
5. Wave E (P0/P1): ship owner/admin business control layer (`Business Home`, `Subscription`, `Data & Trust`, `Team Performance`).

## This wave delivery (2026-02-15)

- Moved Platform Admin smoke scenarios into dedicated `console-web/e2e/platform-admin.spec.ts`.
- Reduced `console-web/e2e/smoke.spec.ts` from 1451 to 1146 lines.
- Added repeatable KPI snapshot tool: `ops/console_platform_admin_kpi_snapshot.py`.
- Added weekly operating runbook: `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`.
- Added owner/admin route `Business` (`/business`) with risk-aware action queue.
- Added owner/admin route `Subscription` (`/subscription`) with quota/usage/projection + evidence rows.
- Added owner/admin-friendly incident banner copy in `ConsoleShell`.
- Added outbox guard thresholds and fail-fast gate (`--fail-on-breach`, `--fail-level`).
- Replaced toast-only validation flows with `reportValidationError` (toast + inline summary) for `tenants` and `company-workspace`.
