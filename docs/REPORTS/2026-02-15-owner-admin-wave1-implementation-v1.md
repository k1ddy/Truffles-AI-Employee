# Report: Owner/Admin Wave-1 Implementation v1

Date
- 2026-02-15

Scope
- Implement Wave-1 owner/admin control layer from `TP-2026-02-15-owner-admin-wave1-business-home-a1`.
- Deliverables:
  - backend read-model endpoints for business/subscription;
  - frontend routes (`/business`, `/subscription`);
  - owner/admin plain-language incident banner in global shell.

## Delivered

Backend
- Added RBAC sections `business` and `subscription` (read for `platform_admin/owner/admin`).
  - `truffles-api/app/services/console_auth.py`
- Added response schemas:
  - `ConsoleBusinessSummaryResponse`
  - `ConsoleSubscriptionSummaryResponse`
  - `ConsoleBusinessActionItem`
  - `ConsoleSubscriptionEvidenceItem`
  - `truffles-api/app/schemas/console.py`
- Added endpoints:
  - `GET /console/v1/business/summary`
  - `GET /console/v1/subscription/summary`
  - `truffles-api/app/routers/console.py`

Frontend
- Added nav/RBAC sections:
  - `business`, `subscription`
  - `console-web/src/lib/api-client.ts`
- Added API client methods:
  - `businessApi.getSummary()`
  - `businessApi.getSubscriptionSummary()`
  - `console-web/src/lib/api-client.ts`
- Added pages:
  - `console-web/src/app/business/page.tsx`
  - `console-web/src/app/subscription/page.tsx`
- Updated global incident banner:
  - owner/admin copy switched to business-language framing;
  - Workspace CTA shown only if role has `tenants:read`;
  - `console-web/src/components/ConsoleShell.tsx`

Docs / audit sync
- Added:
  - `docs/CONSOLE_AUDIT/pages/business.md`
  - `docs/CONSOLE_AUDIT/pages/subscription.md`
- Updated:
  - `docs/CONSOLE_AUDIT/pages/global-shell.md`
  - `docs/CONSOLE_AUDIT/roles/owner.md`
  - `docs/CONSOLE_AUDIT/roles/admin.md`
  - `docs/CONSOLE_AUDIT/INDEX.md`
  - `docs/CONSOLE_AUDIT/CANON_VS_IMPLEMENTED.md`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`

## Validation

Backend checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/app/services/console_auth.py`
- `pytest -q truffles-api/tests/test_console_rbac.py truffles-api/tests/test_console_owner_business.py`
  - Result: `45 passed`.

Frontend checks
- `npm --prefix console-web ci`
- `npm --prefix console-web run lint`
  - Result: no ESLint warnings/errors.
- `npm --prefix console-web run build`
  - Result: successful production build; routes include `/business` and `/subscription`.

## Residual risks
- Subscription quota metadata depends on `companies.billing_info` / `clients.config.billing`; if quota is absent, UI shows usage but quota remains unknown.
- Business summary thresholds are heuristic and should be tuned with production trend evidence.
