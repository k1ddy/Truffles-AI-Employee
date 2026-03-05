# Web Console UX Backlog (Platform Admin + Owner/Admin focus)

Scope
- Platform Admin operating surface in Console Plane (`Tenants`, `Integrations`, `Company Workspace`, control-plane e2e).
- Owner/Admin business control surface (`Insights`, `Ops`, `Settings`, `Audit`) for non-technical operators.
- Fact-only: each item references runtime/code evidence.

Evidence sources
- `docs/REPORTS/2026-02-15-platform-admin-baseline-v2.md`
- `docs/REPORTS/2026-02-15-platform-admin-baseline-v3.md`
- `docs/REPORTS/2026-02-16-console-plane-perf-baseline-v1.md`
- `docs/REPORTS/2026-02-15-owner-admin-business-control-plane-v1.md`
- `docs/REPORTS/2026-02-15-owner-admin-wave2-data-trust-team-v1.md`
- `docs/REPORTS/2026-02-15-owner-admin-wave3-simple-settings-v1.md`
- `docs/REPORTS/2026-02-15-owner-admin-wave4-action-loop-v1.md`
- `docs/REPORTS/2026-02-15-owner-admin-wave5-control-hardening-v1.md`
- `docs/REPORTS/2026-02-15-owner-admin-wave6-automation-v1.md`
- `docs/REPORTS/2026-02-15-owner-admin-wave7-fact-os-v1.md`
- `docs/REPORTS/2026-02-16-owner-admin-ux-simplify-v1.md`
- `Business/Sales/BILLING_COUNTING.md`
- `docs/CONSOLE_AUDIT/roles/owner.md`
- `docs/CONSOLE_AUDIT/roles/admin.md`
- `docs/CONSOLE_AUDIT/pages/insights.md`
- `docs/CONSOLE_AUDIT/pages/ops.md`
- `docs/CONSOLE_AUDIT/pages/business-data-trust.md`
- `docs/CONSOLE_AUDIT/pages/business-team-performance.md`
- `console-web/e2e/smoke.spec.ts`
- `console-web/e2e/platform-admin.spec.ts`
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/components/ProvisioningWizard.tsx`
- `truffles-api/app/routers/console.py`

## Priority backlog

| ID | Priority | Area | Problem | Impact | Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- |
| UX-08 | P0 | Runtime health | Console health had unstable windows with elevated outbox pressure; recovery loop was reactive. | Platform Admin sees degradation late and spends extra time on manual triage. | `curl https://console.truffles.kz/api/health/full` (`2026-02-15T08:06:10Z`) + `ops/console_platform_admin_kpi_snapshot.py` guard output in `docs/REPORTS/2026-02-15-platform-admin-baseline-v3.md` + health path cache/timeout mitigation in `truffles-api/app/main.py` (`/admin/health/check`). | Mitigated (guard + health cache), Open |
| UX-26 | P0 | Cases list latency | `/console/v1/cases` DB hot-path relied on weak single-column indexes, producing high p95 and visible slow loading in Inbox. | Managers/owners see delayed case list refresh and perceive UI as hanging even when backend is healthy. | `docs/REPORTS/2026-02-16-console-plane-perf-baseline-v1.md` (`combined p95 305.228ms -> 51.712ms`, `-83.1%`) + migration `truffles-api/migrations/030_add_console_cases_hotpath_indexes.sql`. | Mitigated (DB wave), Open |
| UX-09 | P0 | QA reliability | Platform Admin-critical e2e tests were concentrated inside `smoke.spec.ts`, causing noisy failures and slower triage. | High false triage cost for core admin regressions. | Baseline: `smoke.spec.ts` 1451 lines before split. | Fixed |
| UX-10 | P1 | Error clarity | Validation and operator-input errors used toast-only on `tenants` and `company-workspace`; context recovery was not persistent on screen. | Slow incident handling and repeated user actions. | `reportValidationError` + inline summary in `console-web/src/app/tenants/page.tsx`, `console-web/src/app/company-workspace/page.tsx`; snapshot `toast.error` entries reduced to helper-only (`1/1`) in `docs/REPORTS/2026-02-15-platform-admin-baseline-v3.md`. | Fixed |
| UX-11 | P1 | API maintainability | `console.py` remains an overgrown router with mixed concerns. | Slow onboarding and high regression probability for Platform Admin APIs. | Wave13 execution reduced router orchestration (`console.py=24354`) with deterministic lane green (`35 passed` + `branch_change 15 passed`); closure-review9 contract locked for merged-main decision. References: `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave13-a705.md`, `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review9-a705.md`. | Open (Mitigated wave13; closure-review9 required) |
| UX-12 | P1 | Provisioning UX complexity | `ProvisioningWizard.tsx` remains a large multi-domain component. | Hard to ship safe improvements fast across onboarding paths. | Wave13 execution reduced wizard orchestration (`ProvisioningWizard.tsx=4351`) with deterministic lane green (`35 passed` + `branch_change 15 passed` + targeted e2e `2 passed`); closure-review9 contract locked for merged-main decision. References: `docs/CONSOLE_AUDIT/artifacts/2026-03-04-uvc-tech-debt-decomposition-wave13-a705.md`, `docs/TASK_PACKAGES/TP-2026-03-04-uvc-ux-tech-debt-decomposition-closure-review9-a705.md`. | Open (Mitigated wave13; closure-review9 required) |
| UX-13 | P2 | Governance loop | No standard weekly control-loop runbook existed for Platform Admin KPI snapshots and anti-drift artifacts. | Inconsistent evidence quality between sessions. | New runbook and script introduced in this wave. | Fixed |
| UX-14 | P0 | Owner billing transparency | Owner/Admin lacked dedicated UI for plan/quota/usage and evidence drill-down. | High dispute risk and low trust in subscription charges. | `console-web/src/app/subscription/page.tsx`, `truffles-api/app/routers/console.py` (`/subscription/summary`), `Business/Sales/BILLING_COUNTING.md`. | Fixed |
| UX-15 | P0 | Owner incident clarity | Runtime health risk was visible only in technical framing; owner path lacked business-language incident guidance. | Business owners discovered service degradation too late. | `console-web/src/components/ConsoleShell.tsx` (owner/admin incident text), `truffles-api/app/routers/console.py` (`/business/summary`). | Fixed |
| UX-16 | P1 | Data trust and manager accountability | Owner/Admin lacked dedicated control surfaces for data-governance status and manager performance accountability. | Hard to answer client trust questions and improve team outcomes. | `console-web/src/app/business/data-trust/page.tsx`, `console-web/src/app/business/team-performance/page.tsx`, `truffles-api/app/routers/console.py` (`/business/data-trust`, `/business/team-performance`), `docs/REPORTS/2026-02-15-owner-admin-wave2-data-trust-team-v1.md`. | Fixed |
| UX-17 | P0 | Simple settings and explainability | Owner/Admin lacked simple SLA controls and could not understand how timing settings affect lead loss/escalation. | Wrong settings stayed unnoticed; high risk of missed leads and trust issues. | `console-web/src/app/settings/page.tsx` (simple settings + explainability), `truffles-api/app/routers/console.py` (`PATCH /settings` fix), `console-web/e2e/owner-admin-business.spec.ts`, `docs/REPORTS/2026-02-15-owner-admin-wave3-simple-settings-v1.md`. | Fixed |
| UX-18 | P0 | Action loop closure | Team KPI had diagnosis but no direct remediation action; settings default still overloaded by technical blocks; subscription lacked next-charge + alert semantics. | Owner/Admin saw issues but could not act quickly, causing slower recovery and billing ambiguity. | `console-web/src/app/business/team-performance/page.tsx`, `console-web/src/app/settings/page.tsx`, `console-web/src/app/subscription/page.tsx`, `truffles-api/app/schemas/console.py`, `truffles-api/app/routers/console.py`, `docs/REPORTS/2026-02-15-owner-admin-wave4-action-loop-v1.md`. | Fixed |
| UX-19 | P1 | Remediation rollback + impact loop | Quick profile applied instantly but had no guided rollback and no standard impact baseline/replay snapshots for owner/admin. | Operators could not safely revert configuration and could not prove post-merge effect after 24h. | `console-web/src/app/business/team-performance/page.tsx` (`team-performance-quick-profile-rollback*`), `ops/console_owner_admin_kpi_snapshot.py`, `docs/runbooks/OWNER_ADMIN_POSTMERGE_24H.md`, `docs/REPORTS/2026-02-15-owner-admin-wave5-control-hardening-v1.md`. | Fixed |
| UX-20 | P1 | API maintainability (owner/admin slice) | Owner/admin business helpers were still embedded in `console.py` and slowed safe iteration. | Higher regression risk and slower onboarding for owner/admin API changes. | `truffles-api/app/services/console_owner_admin.py`, `truffles-api/app/routers/console.py`, `truffles-api/tests/test_console_owner_business.py`. | Mitigated (wave-5 start), Open |
| UX-21 | P1 | Manual control-loop overhead | Post-merge owner/admin loop still required manual command choreography and inconsistent artifact naming. | Hard to scale governance across many clients and releases. | `ops/owner_admin_control_loop.py`, `docs/runbooks/OWNER_ADMIN_POSTMERGE_24H.md`. | Fixed |
| UX-22 | P1 | Goal-to-action gap in settings | Owners still had to interpret technical presets instead of choosing business outcomes directly. | Slower decisions and higher configuration mistakes for non-technical operators. | `console-web/src/app/settings/page.tsx` (`settings-goal-mode`). | Fixed |
| UX-23 | P1 | Publish safety enforcement gap | Knowledge publish could bypass explicit preflight discipline at backend level. | Higher risk of accidental publish without recent validation of the same draft. | `truffles-api/app/services/console_knowledge_preflight.py`, `truffles-api/app/routers/console.py`, `console-web/src/app/knowledge/page.tsx`, `truffles-api/tests/test_console_knowledge_preflight.py`. | Fixed |
| UX-24 | P0 | Owner KPI fact integrity | KPI cards on owner/admin pages lacked machine-readable fact provenance (`source/as_of/scope/sample`). | Users could not distinguish factual vs. estimated/missing numbers, hurting trust in business decisions. | `truffles-api/app/schemas/console.py`, `truffles-api/app/routers/console.py`, `console-web/src/app/business/page.tsx`, `console-web/src/app/subscription/page.tsx`, `console-web/src/app/business/data-trust/page.tsx`, `console-web/src/app/business/team-performance/page.tsx`. | Fixed |
| UX-25 | P1 | Settings/Team action loop still client-driven | Goal actions and quick profile relied on client-side presets without durable server operation/rollback/impact contract. | Hard to scale changes safely across many owners and impossible to audit/rollback consistently. | `truffles-api/app/routers/console.py` (`/business/operations/owner-mode/*`), `console-web/src/app/settings/page.tsx`, `console-web/src/app/business/team-performance/page.tsx`, `contracts/console_api/openapi.v1.yaml`, `console-web/e2e/owner-admin-business.spec.ts`. | Fixed |
| UX-28 | P0 | Inbox refresh cost + polling pressure | Queue refresh paid heavy SQL price (`list + total_count`) and Inbox performed high-frequency background polling (`case/messages`) with full cache invalidation on context switch. | Operators perceive lag/freeze while queue/chat updates under degraded runtime. | `docs/REPORTS/2026-02-16-console-plane-perf-baseline-v1.md`, `truffles-api/app/routers/console.py` (`list_cases` count-path + client-scoped subqueries), `console-web/src/hooks/useCaseData.ts`, `console-web/src/components/CaseList.tsx`, `console-web/src/components/ConsoleShell.tsx`. | Mitigated |
| UX-27 | P0 | Owner/Admin cognitive overload | Owner/Admin saw technical-heavy left menu and unclear first action path despite business role goals. | Slower onboarding, wrong clicks, and lower trust in Console as business tool. | `console-web/src/components/ConsoleShell.tsx` (business-first nav mode + advanced toggle), `console-web/src/app/business/page.tsx` (`business-today-plan`), `console-web/src/app/settings/page.tsx` (business-language copy), `console-web/e2e/owner-admin-business.spec.ts`, `docs/REPORTS/2026-02-16-owner-admin-ux-simplify-v1.md`. | Fixed |

## 30-day execution waves

1. Wave A (P0): stabilize runtime recovery loop for outbox backlog and expose alert thresholds in Platform Admin runbook.
2. Wave B (P0/P1): keep Platform Admin e2e isolated (`platform-admin.spec.ts`) and add CI lane-level ownership.
3. Wave C (P1): reduce error-surface entropy in `tenants` and `company-workspace` (contextual inline errors, not only toasts).
4. Wave D (P1): start router/component decomposition (`console.py`, `ProvisioningWizard.tsx`) with contract tests guarding behavior.
5. Wave E (P0/P1): ship owner/admin business control layer (`Business Home`, `Subscription`, `Data & Trust`, `Team Performance`).
6. Wave F (P0/P1): enforce owner/admin fact contract + server-driven owner operations with rollback/impact evidence.

## This wave delivery (2026-02-15)

- Moved Platform Admin smoke scenarios into dedicated `console-web/e2e/platform-admin.spec.ts`.
- Reduced `console-web/e2e/smoke.spec.ts` from 1451 to 1146 lines.
- Added repeatable KPI snapshot tool: `ops/console_platform_admin_kpi_snapshot.py`.
- Added weekly operating runbook: `docs/runbooks/PLATFORM_ADMIN_CONTROL_LOOP.md`.
- Added owner/admin route `Business` (`/business`) with risk-aware action queue.
- Added owner/admin route `Subscription` (`/subscription`) with quota/usage/projection + evidence rows.
- Added owner/admin-friendly incident banner copy in `ConsoleShell`.
- Added owner/admin route `Data Trust` (`/business/data-trust`) with quality gaps, knowledge freshness, and audit pressure.
- Added owner/admin route `Team Performance` (`/business/team-performance`) with stale queue pressure and manager accountability table.
- Added owner/admin `Settings` Wave-3 simple controls with explainability and fixed `PATCH /settings` persistence mapping.
- Added Wave-4 owner/admin action-loop:
  - Team KPI quick profile apply (`5/30/60`) with confirm,
  - Settings onboarding-lite default + `Расширенные` для технических блоков,
  - Subscription v2 alerts (`80/100`), next billing date, projected overage semantics.
- Added Wave-5 owner/admin control hardening:
  - post-merge runbook v2 (`T+0`/`T+24`) with baseline/replay protocol,
  - owner/admin KPI snapshot tool (`ops/console_owner_admin_kpi_snapshot.py`) with impact delta and fail-fast gate,
  - Team KPI guided remediation with one-click rollback to previous SLA values,
  - owner/admin helper extraction start (`console.py` -> `app/services/console_owner_admin.py`).
- Added Wave-6 owner/admin automation and safety layer:
  - orchestration script for control-loop phases (`ops/owner_admin_control_loop.py`),
  - business goal-mode actions in settings (`settings-goal-*`),
  - backend knowledge publish preflight gate (`KNOWLEDGE_PREFLIGHT_REQUIRED`) with draft hash validation.
- Added Wave-7 owner/admin fact + operation contract:
  - KPI fact metadata (`kind/source/as_of/scope/sample_size`) in `business/subscription/data-trust/team-performance` APIs and owner/admin UI cards,
  - server-driven owner mode operations (`preview/apply/rollback/impact`) with audit snapshot and due-at check,
  - smoke coverage refresh for owner/admin operation surfaces (`owner-admin-business.spec.ts`),
  - health API no longer reports hardcoded Redis connected state; returns fact-based `connected/error/unknown`.
- Added outbox guard thresholds and fail-fast gate (`--fail-on-breach`, `--fail-level`).
- Replaced toast-only validation flows with `reportValidationError` (toast + inline summary) for `tenants` and `company-workspace`.
- Added owner/admin business-first UX simplification:
  - default reduced left menu for owner/admin with explicit `Показать расширенное меню` toggle,
  - `/business` now starts with `Что делать сейчас` 3-step action plan,
  - settings primary surface copy translated to plain business language.
