# Report: Platform Admin Baseline v1 (Console Plane)

Date
- 2026-02-15

Scope
- Platform Admin control surface in Web Console (`tenants`, `integrations`, `company-workspace`, `ops`, `settings`, `audit`).
- Objective: identify current bottlenecks, UX friction, and management complexity for multi-company operations.

Method
- Canon + implementation review: `STATE.md`, `docs/CONSOLE_AUDIT/*`, `console-web/src/*`, `truffles-api/app/routers/console.py`.
- Runtime snapshot: public health/version endpoints.
- Complexity metrics: LOC + error-surface density in key files.
- External control-plane heuristics for decision framing (links below).

---

## 1) Snapshot (facts)

Runtime health (UTC `2026-02-15T02:43:55Z`)
- `GET https://console.truffles.kz/api/health/full`
- Result: `status=unhealthy`, `outbox.pending=1601`, `outbox.failed=613`, api version `03e3cb1a`.

Prod version
- `GET https://api.truffles.kz/admin/version`
- Result: `git_commit=03e3cb1a35f15769390c37a6a720b76cf1b1c8e3`, build time `2026-02-14T11:59:04Z`.

Complexity hotspots (LOC)
- `truffles-api/app/routers/console.py`: `12066`
- `console-web/src/components/ProvisioningWizard.tsx`: `4894`
- `console-web/src/app/tenants/page.tsx`: `3769`
- `console-web/src/app/integrations/page.tsx`: `1817`
- `console-web/src/app/company-workspace/page.tsx`: `1416`
- `console-web/e2e/smoke.spec.ts`: `1549`

Error surface density (`toast.error` count)
- `console-web/src/components/ProvisioningWizard.tsx`: `59`
- `console-web/src/app/tenants/page.tsx`: `37`
- `console-web/src/app/company-workspace/page.tsx`: `17`

---

## 2) Findings (severity-ordered)

### P0-1: Operational risk visibility gap
What
- Platform health is already `unhealthy` with high outbox backlog, but Platform Admin navigation has no persistent high-severity incident banner with SLA risk and direct guided runbook actions.

Impact
- Slow first response to delivery incidents and higher probability of delayed customer-facing messages.

Evidence
- `https://console.truffles.kz/api/health/full` snapshot above.
- `console-web/src/components/OpsPage.tsx`
- `console-web/src/components/ConsoleShell.tsx`

### P1-1: High UX friction in long admin flows
What
- Tenants/provisioning flows rely heavily on transient toasts for validation and failure handling.

Impact
- Errors are easy to miss during multi-step operations, causing retries and operator uncertainty.

Evidence
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/components/ProvisioningWizard.tsx`

### P1-2: Context logic duplicated across pages
What
- `company/client/branch` localStorage keys and context synchronization are repeated in multiple pages.

Impact
- Inconsistent behavior risk and higher bugfix cost.

Evidence
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/app/integrations/page.tsx`
- `console-web/src/app/company-workspace/page.tsx`

### P1-3: Maintainability risk (monolith files)
What
- Platform Admin surfaces are concentrated in very large single files.

Impact
- High regression probability, slower reviews, expensive onboarding of new contributors.

Evidence
- LOC metrics listed above.

### P2-1: QA fragility from smoke concentration
What
- Critical path e2e checks are concentrated in one large `smoke.spec.ts`.

Impact
- Harder triage and slower reliable feedback for Platform Admin regressions.

Evidence
- `console-web/e2e/smoke.spec.ts`

---

## 3) Journey heatmap (Platform Admin)

| Journey | Current state | Primary pain |
| --- | --- | --- |
| Fleet triage (`/integrations`) | Good read model + workspace CTA | Incident severity is not globally surfaced |
| Branch execute (`/company-workspace`) | Strong action model (`dry_run/execute`) | Context and failures are still toast-heavy |
| Tenant lifecycle (`/tenants`) | Powerful but overloaded page | High cognitive load + long form state |
| Onboarding/go-live (`ProvisioningWizard`) | Contract-aware and feature-rich | Too much logic in one component |
| Ops monitoring (`/ops`) | Functional queue and jobs UI | No top-level P0 alert visibility in shell |

---

## 4) 30-day improvement plan (result-oriented)

### Wave 1 (48-72h) - Stop-risk
1. Add global incident banner in `ConsoleShell` driven by `/health` risk thresholds (`outbox.pending`, `failed`, stale age).
2. Add persistent inline error summary blocks in `company-workspace` and `tenants` (not toast-only).
3. Publish runbook links from incident banner to relevant actions (`/ops`, `/company-workspace`).

Acceptance
- P0 incident visible from any route in <= 5s after page load.
- At least one persistent inline error state per critical flow.

### Wave 2 (Week 1) - UX control
1. Extract shared context hook/service (`useConsoleContextScope`) for all platform pages.
2. Split `tenants` into feature modules (scope panel, lifecycle center, branch editor, KPI panel).
3. Split `ProvisioningWizard` state/actions from presentation.

Acceptance
- No direct localStorage key handling outside shared context module.
- Each extracted module <= 600 LOC target.

### Wave 3 (Weeks 2-4) - Reliability and QA
1. Split e2e smoke into route-focused suites (`platform-admin-integrations`, `platform-admin-workspace`, `platform-admin-tenants`).
2. Add deterministic API contract checks for incident-triggering signals.
3. Track weekly operational KPIs and regressions in one baseline dashboard artifact.

Acceptance
- Platform Admin critical e2e failures isolate by suite in one run.
- Weekly KPI snapshot generated and reviewed (trend, not point-in-time only).

---

## 5) KPI contract for baseline tracking

Reliability
- `outbox_pending`
- `outbox_failed`
- `outbox_failed / (sent + failed)` ratio
- `time_to_incident_visibility` (health breach -> banner shown)

UX
- `time_to_context_ready` (login -> valid company/client/branch context)
- `task_success_rate` for branch lifecycle actions
- `retry_per_task` for onboarding/go-live operations

Engineering
- max LOC per platform-admin module
- `toast-only` error count trend
- e2e suite duration and flaky test count

---

## 6) Immediate actions already completed in this baseline pass

1. Added missing Console Audit pages for active platform routes:
   - `docs/CONSOLE_AUDIT/pages/integrations.md`
   - `docs/CONSOLE_AUDIT/pages/company-workspace.md`
2. Updated Console Audit index and canon comparison to include these routes.
3. Refreshed UX backlog with active `P0/P1/P2` items for Platform Admin.

---

## External references used (control-plane heuristics)

- Azure Architecture Center, control planes in multitenant solutions:
  - https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/overview-control-planes
- AWS Well-Architected SaaS Lens:
  - https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/welcome.html
- Google SRE Book (monitoring / reliability signals):
  - https://sre.google/sre-book/monitoring-distributed-systems/
- Nielsen Norman Group, usability heuristics:
  - https://www.nngroup.com/articles/ten-usability-heuristics/
