# TP-2026-02-08 Branch Account Factory + RBAC Admin (PR-2, a17)

## Название/цель
Реализовать PR-2 программы Enterprise Fleet: стандартизированное создание branch-аккаунтов и полный lifecycle memberships/access в Console для Platform Admin без SQL/manual костылей.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: завершен PR-1 Fleet Core, следующий шаг PR-2)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/MULTI_TENANT.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `docs/REPORTS/2026-02-08-enterprise-fleet-program.md`

## Invariant
- Tenant isolation fail-closed: no cross-tenant data/access leakage.
- Existing platform_admin and current `/console/v1/me` auth contract не ломаются.
- Existing branch/client archive-restore semantics from PR-1 остаются совместимыми.
- Все mutating access операции пишут audit event с actor/entity/reason/context.

## Scope
- Backend API:
  - Branch Account Factory endpoint: branch creation + template account bootstrap.
  - Membership admin API: list/create/update/deactivate/reactivate memberships with explicit scope (`company|client|branch`).
  - User access lifecycle API: enable/disable agent, re-scope membership, OIDC rebind (guarded).
- Validation/guards:
  - duplicate OIDC external_id guard (hard fail).
  - cross-tenant and scope conflict guards.
  - confirmation reason for destructive access changes.
- Frontend Console:
  - Tenants/Team admin UI для account factory и membership lifecycle actions.
- Contracts/typing:
  - update `contracts/console_api/openapi.v1.yaml` and generated TS types.
- Tests:
  - unit/API tests for guards + negative cross-tenant access (`403`).

## Out of scope
- Onboarding conveyor/go-live gate (PR-3).
- Bulk Jobs and runbook lift (PR-4).
- Legacy `/admin/*` deprecation/cutover (PR-5).
- Billing/contract automation changes (commercial policy matrix).

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_auth.py`
- `truffles-api/app/services/audit_service.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/models/agent.py`
- `truffles-api/app/models/agent_membership.py`
- `truffles-api/tests/test_console_rbac.py`
- `truffles-api/tests/test_console_admin_provisioning.py`
- `truffles-api/tests/test_console_tenants_list.py`
- `truffles-api/tests/test_console_access_admin_pr2.py` (new)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/types/api.generated.ts`
- `console-web/src/lib/api-client.ts`
- `console-web/src/app/team/page.tsx`
- `console-web/src/app/tenants/page.tsx`
- `docs/SESSIONS/SESSION-2026-02-08-branch-account-factory-rbac-pr2-a17.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Зафиксировать API contract для membership/access lifecycle (request/response/errors).
2. Реализовать backend handlers + guards + audit events.
3. Добавить/обновить backend tests (positive + cross-tenant negative + duplicate OIDC).
4. Обновить OpenAPI и frontend types/client.
5. Добавить Console UI flows для account factory и membership actions.
6. Прогнать checks, собрать evidence, открыть PR-2.

## DoD
- Platform Admin может создать branch с шаблонным набором аккаунтов/roles из Console.
- Platform Admin может выполнять membership CRUD + enable/disable + re-scope + OIDC rebind из Console.
- Cross-tenant попытки блокируются (`403`) и покрыты тестами.
- Duplicate OIDC external_id блокируется fail-closed.
- OpenAPI и generated frontend types синхронизированы.

## Checks
- `scripts/session_check.sh`
- `pytest -q truffles-api/tests/test_console_rbac.py truffles-api/tests/test_console_admin_provisioning.py truffles-api/tests/test_console_access_admin_pr2.py`
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `cd console-web && npx openapi-typescript ../contracts/console_api/openapi.v1.yaml -o src/types/api.generated.ts`
- `cd console-web && npm run lint`
- `cd console-web && npm run build`

## Evidence
- `git status -sb`
- `git diff --stat`
- test/lint/build outputs
- CI run URL
- PR URL

## Rollback
- Revert PR-2 commit range целиком.

## No-go
- Не добавлять прямой SQL/manual override path в UI/API.
- Не ослаблять auth checks через fallback role logic.
- Не смешивать PR-2 с PR-3/PR-4 scope.

## Риски/блокеры
- Риск: пересечение существующего provisioning flow и нового account factory.
  - Митигация: сохранить backward-compatible endpoint behavior + explicit feature path.
- Риск: сложность memberships migration for existing agents.
  - Митигация: fail-closed validation + explicit migration-safe defaults + tests on legacy rows.
- Риск: UI complexity для Platform Admin.
  - Митигация: staged UI (factory first, advanced membership actions next panel) без ломки текущих страниц.

## Branch/worktree policy
- Branch: `feat/2026-02-08-branch-account-factory-rbac-pr2-a17`
- Worktree: `/home/zhan/worktrees/2026-02-08-branch-account-factory-rbac-pr2-a17`
- Base ref: `origin/main`
- Merge policy: PR to `main` only, no rebase
- Cleanup: after merge remove branch + worktree via `session_end`/Brain cleanup
