# Report: Owner/Admin Business Control Plane Deep Analysis v1

Date
- 2026-02-15

Scope
- Business-first audit for `owner/admin` users with low platform maturity.
- Focus: simple company settings, subscription transparency, data trust, manager visibility, and day-to-day control clarity.
- This report documents current implementation facts and proposes a prioritized operating model.

Method
- Internal fact baseline (code + docs + runtime snapshot).
- Gap mapping by critical owner/admin jobs-to-be-done.
- External heuristics from primary sources (OECD, GOV.UK Service Standard, Google SRE, Google HEART).

## 1) Baseline facts (implementation + runtime)

Runtime snapshot (`2026-02-15T08:23:42Z`)
- `GET https://console.truffles.kz/api/health/full` -> `status=unhealthy`, `outbox.pending=1647`, `outbox.failed=711`, api version `9c7e3e5e`.
- `GET https://api.truffles.kz/admin/version` -> build `2026-02-15T08:00:00Z`, commit `9c7e3e5e36098fd2661b7846a90e7c3a1c61e06c`.

Owner/Admin current surface (`FACT`)
- Navigation for owner/admin: `Inbox`, `Calendar`, `Knowledge`, `Team`, `Ops`, `Audit`, `Insights`, `Settings`.
- No dedicated owner-facing route for `Subscription/Billing`, `Invoices`, `Data Governance`, or `Business Health` as a single pane.
- Source: `docs/CONSOLE_AUDIT/roles/owner.md`, `docs/CONSOLE_AUDIT/roles/admin.md`, `console-web/src/components/ConsoleShell.tsx`.

Transparency baseline (`FACT`)
- Billing counting rules exist as internal canonical doc (outbox-based evidence model), but not as explicit owner-facing UI contract.
- Source: `Business/Sales/BILLING_COUNTING.md`.
- Insights page exposes operational KPI tiles and trends, but not subscription/quota/invoice accountability per business owner.
- Source: `docs/CONSOLE_AUDIT/pages/insights.md`.
- Audit page exposes event feed (`time/event/actor/entity/details`) but no owner-oriented explanation layer (“why charged/why escalated/what changed in settings”).
- Source: `docs/CONSOLE_AUDIT/pages/audit.md`.

Complexity baseline (`FACT`)
- Critical owner/admin workflows still pass through large components (`ProvisioningWizard`, `console.py`) and can remain cognitively heavy for non-technical users.
- Source: `docs/CONSOLE_AUDIT/UX_BACKLOG.md`, `docs/REPORTS/2026-02-15-platform-admin-baseline-v2.md`.

## 2) Owner/Admin job map

Primary business jobs (`INFERENCE` from implementation + support/onboarding docs)
1. Understand business status in <60 seconds (is bot healthy, are leads handled, any urgent risk).
2. Understand money impact (plan, usage, remaining quota, upcoming invoice, overage risk).
3. Trust data handling (what data is stored, where used, who accessed it, retention/export paths).
4. Control team outcomes (manager response speed, unresolved handoffs, coverage gaps).
5. Change only simple high-impact settings without fear (hours, services, policies, escalation channel).

Evidence base
- Current docs for onboarding/support and selling boundaries: `Business/Onboarding/Инструкция_клиента.md`, `Business/Support/Регламент_техподдержки.md`, `STRATEGY/PRODUCT.md`, `docs/SELLING_TRUTHS.md`.

## 3) Severity-ordered problem map

### P0-1: Incident visibility is not owner-native
What (`FACT`)
- Health is currently unhealthy with growing outbox backlog; incident understanding requires moving across `Ops`, details tables, and technical terms.

Impact (`INFERENCE`)
- Owners discover risk late and cannot quickly answer “are client messages safe right now?”.

### P0-2: Commercial transparency gap (subscription/accountability)
What (`FACT`)
- No owner-facing page that consolidates plan, quota, billable usage, overage forecast, invoice status, and dispute evidence.
- Billing logic exists internally (`BILLING_COUNTING`) but is not surfaced as a guided owner workflow.

Impact (`INFERENCE`)
- Disputes and distrust increase when costs rise without clear self-serve evidence.

### P1-1: Data trust gap
What (`FACT`)
- Owner can view audit feed, but there is no plain-language data governance screen (stored fields, retention, access trail, export/delete requests status).

Impact (`INFERENCE`)
- Non-technical owners struggle to assess privacy/compliance posture.

### P1-2: Manager accountability gap
What (`FACT`)
- Metrics exist (`Insights`, handover fields in data model), but owner lacks a focused manager-performance cockpit with actionable recommendations.

Impact (`INFERENCE`)
- Hard to improve response discipline and prove service quality to business.

### P1-3: Settings overload for novice operators
What (`FACT`)
- Settings/provisioning includes advanced structures and large UI state; novice users can still lose context despite recent improvements.

Impact (`INFERENCE`)
- High support dependency and risky misconfiguration.

## 4) Target operating model (Owner/Admin)

Proposed IA extension (`INFERENCE`, implementation-ready)
1. `Business Home` (new default for owner/admin)
- One-screen summary: health, SLA risk, revenue/lead proxies, top 3 actions.
2. `Subscription & Billing`
- Plan, quota usage, projected overage, invoice state, billable evidence drill-down.
3. `Data & Trust`
- What is stored, access timeline, retention windows, export/delete request path.
4. `Team Performance`
- First response, resolution, unresolved handoffs, per-manager workload.
5. `Simple Settings`
- Curated top-10 business controls; advanced config hidden behind explicit toggle.

Interaction principles (`INFERENCE`, backed by external heuristics)
- `Simple-first`: default to concise, non-technical language and action labels.
- `Progressive disclosure`: hide advanced JSON/technical controls unless explicitly requested.
- `Visibility of status`: global critical risk banner with clear next action.
- `Assisted digital`: guided setup and contextual help for low-maturity operators.

## 5) 30/60/90 execution plan

### 0-30 days (P0)
1. Build owner `Business Home` MVP in Console shell.
2. Add `Subscription & Billing` MVP (read-only): plan/quota/usage/forecast + evidence links.
3. Add global incident banner for owner/admin with direct CTA (`Ops` + runbook action).

Acceptance
- Owner can answer in <=60 seconds: system health, billing position, urgent actions.
- Billing disputes can reference self-serve evidence rows (outbox-grounded).

### 31-60 days (P1)
1. Ship `Data & Trust` page with plain-language data contract and access timeline.
2. Ship `Team Performance` page with manager KPIs and backlog risks.
3. Add simple-vs-advanced mode in Settings with safe defaults.

Acceptance
- Reduced support tickets for “where are my data / why this bill / who replied late”.

### 61-90 days (P1/P2)
1. Add guided recommendations engine (“next best admin action”).
2. Add weekly owner digest (business + risk + action summary).
3. Add task success instrumentation and churn-risk flags.

Acceptance
- Measurable improvement in owner activation, retention, and support load.

## 6) KPI contract (owner/admin business outcomes)

North-star metrics
- `owner_time_to_confidence`: login -> owner understands status and next step.
- `billing_dispute_rate`: disputes per 100 active clients.
- `owner_task_success_rate`: successful completion of top business tasks without support.

Operational guardrails
- `incident_visibility_time`: health breach -> owner sees actionable alert.
- `handoff_backlog_age_p90`: unresolved manager handoff aging.
- `settings_error_retry_rate`: repeated failed attempts in settings/provisioning.

Product quality metrics
- HEART mapping:
  - Happiness: owner confidence pulse.
  - Engagement: weekly active owner/admin.
  - Adoption: usage of new business pages.
  - Retention: active owner retention trend.
  - Task success: completion rate for top workflows.

## 7) Experiment matrix (first 6 experiments)

1. Hypothesis: `Business Home` reduces time-to-confidence by >=40%.
2. Hypothesis: billing transparency page reduces dispute rate by >=25%.
3. Hypothesis: global incident banner reduces late incident discovery by >=50%.
4. Hypothesis: simple settings mode reduces failed retries by >=30%.
5. Hypothesis: team performance cockpit improves first response p90 by >=20%.
6. Hypothesis: data trust page reduces “data privacy” support tickets by >=20%.

## 8) External references used

Primary references
- OECD: Digitalisation of SMEs.
  - https://www.oecd.org/en/topics/sub-issues/digitalisation-of-smes.html
- GOV.UK Service Standard.
  - https://www.gov.uk/service-manual/service-standard
- GOV.UK: Assisted digital approach.
  - https://www.gov.uk/government/publications/government-approach-to-assisted-digital/government-approach-to-assisted-digital
- Google SRE book: Monitoring distributed systems.
  - https://sre.google/sre-book/monitoring-distributed-systems/
- HEART framework publication.
  - https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/
- Nielsen heuristic: visibility of system status.
  - https://www.nngroup.com/articles/ten-usability-heuristics/

Inference note
- External sources are used as decision heuristics; all product decisions still require local runtime evidence and canon constraints.

## 9) Immediate recommendation

- Start Wave-1 implementation from this report with one focused Task Package per stream:
  1. `Owner Business Home + Incident Banner`.
  2. `Subscription & Billing Transparency`.
  3. `Simple Settings for novice owners`.
