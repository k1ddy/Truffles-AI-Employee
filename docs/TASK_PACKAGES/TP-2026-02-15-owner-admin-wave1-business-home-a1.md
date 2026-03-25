# TP-2026-02-15-owner-admin-wave1-business-home-a1

- Название/цель: Реализовать Wave-1 owner/admin control layer: `Business Home` (статус + приоритеты), `Subscription & Billing` (прозрачность плана/квоты/usage), и owner-friendly incident clarity в shell.
- Canon refs: `SPECS/CONTROL_PLANE.md`, `STRATEGY/REQUIREMENTS.md`, `STRATEGY/PRODUCT.md`, `docs/SELLING_TRUTHS.md`, `Business/Sales/BILLING_COUNTING.md`, `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (UX-14/UX-15), `docs/REPORTS/2026-02-15-owner-admin-business-control-plane-v1.md`.

## Invariant
- Не нарушать текущие RBAC и tenancy gates (`company/client/branch selection_required`).
- Не добавлять новые коммерческие обещания, выходящие за `PRODUCT`/`SELLING_TRUTHS`.
- Не менять биллинг-формулу: только owner-facing прозрачность на существующих правилах.

## Scope
- Owner/Admin UI route `Business Home` с 3 блоками: health summary, business summary, top actions.
- Owner/Admin UI route `Subscription` с текущим plan/quota usage и drill-down evidence.
- Global owner/admin incident banner (business-language + CTA в `Ops`).

## Out of scope
- Изменение тарифов/контрактов.
- Новые provider integrations.
- Billing engine rewrite.

## Touch-list
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/app/business/page.tsx` (new)
- `console-web/src/app/subscription/page.tsx` (new)
- `console-web/src/lib/api-client.ts`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_*.py` (targeted)
- `console-web/e2e/platform-admin.spec.ts` or new owner-admin suite
- `docs/CONSOLE_AUDIT/pages/business.md` (new)
- `docs/CONSOLE_AUDIT/pages/subscription.md` (new)

## Plan
1. Define API read-model contracts for owner/admin business and subscription cards.
2. Add backend endpoints (read-only) with RBAC + tenancy gates.
3. Implement frontend pages + shell navigation for owner/admin.
4. Add global incident banner logic (threshold-driven) for owner/admin routes.
5. Add deterministic API tests and route e2e checks.
6. Update Console Audit docs and backlog statuses.

## DoD
- Owner/Admin sees `Business Home` and `Subscription` in navigation.
- Incident banner appears on owner/admin pages when health threshold breached.
- Subscription page displays quota usage + billable evidence table based on existing billing rules.
- All new endpoints are covered by RBAC/tenancy tests.

## Checks
- `pytest -q truffles-api/tests/test_console_rbac.py truffles-api/tests/test_console_ops_outbox.py`
- `pytest -q truffles-api/tests/test_console_metrics_daily.py` (or equivalent owner KPI suite)
- `npm --prefix console-web run lint`
- `npm --prefix console-web run test:e2e -- e2e/platform-admin.spec.ts` (plus owner/admin route checks)

## Evidence
- API contract snippets + screenshots for owner/admin routes.
- Runtime snapshot with triggered incident banner path.
- Test outputs + CI run URL.

## Rollback
- Revert commits touching `business/subscription` routes and shell nav changes.

## No-go
- No hidden fallback that bypasses RBAC.
- No hardcoded tenant/client IDs.
- No billing computation divergence from `BILLING_COUNTING.md`.

## Risks/блокеры
- Existing `console.py` size may slow safe endpoint additions.
- Owner-facing billing evidence may need pagination and privacy redaction guardrails.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-15-owner-admin-business-audit-a1` (or dedicated implementation branch)
- Worktree: `/home/zhan/worktrees/2026-02-15-owner-admin-business-audit-a1` (analysis) + dedicated implementation worktree by Brain decision
- Base ref: `origin/main`
- Merge policy: PR with API + UI + e2e evidence
- Cleanup: Brain/Top Architect after merge
