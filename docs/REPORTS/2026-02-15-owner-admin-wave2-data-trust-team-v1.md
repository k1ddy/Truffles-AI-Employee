# Owner/Admin Wave-2 Implementation Report (Data Trust + Team Performance)

Date
- 2026-02-15

Scope
- Extend owner/admin control layer after Wave-1 (`Business`, `Subscription`).
- Close UX-16: data-governance visibility + manager accountability in business language.

Delivered
- New backend read-model endpoints:
  - `GET /console/v1/business/data-trust`
  - `GET /console/v1/business/team-performance`
- New frontend routes:
  - `/business/data-trust`
  - `/business/team-performance`
- Extended owner/admin navigation in `ConsoleShell`:
  - `Данные` and `Команда KPI`.
- Added Wave-2 shortcuts on `/business` page.

What owner/admin can do now
- Data Trust:
  - see quality-metric completeness gaps,
  - track knowledge freshness,
  - inspect 24h critical audit pressure,
  - follow prioritized recovery actions.
- Team Performance:
  - see open/stale queue pressure,
  - monitor manager response KPIs,
  - compare manager load and oldest unresolved cases,
  - execute actionable load-balancing steps.

Contracts and evidence
- Router: `truffles-api/app/routers/console.py`
- Schemas: `truffles-api/app/schemas/console.py`
- OpenAPI: `contracts/console_api/openapi.v1.yaml`
- API client/types: `console-web/src/lib/api-client.ts`, `console-web/src/types/api.generated.ts`
- UI pages:
  - `console-web/src/app/business/data-trust/page.tsx`
  - `console-web/src/app/business/team-performance/page.tsx`

Validation
- `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/schemas/console.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run generate:api`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`

Result
- UX-16 is no longer a discovery gap: owner/admin now has dedicated control surfaces for data trust and team accountability.
- Wave-2 keeps read-only governance posture and preserves existing tenancy/RBAC constraints.
