# TP-2026-02-07 Tenant Lifecycle Read Semantics (a15)

## Название/цель
Исправить lifecycle семантику Console Tenants в read-path: по умолчанию показывать только активные clients/branches, архив и неактивные выдавать только через явные фильтры. Убрать путаницу в Platform Admin контексте без изменения core runtime.

## Canon refs
- `AGENTS.md`
- `STATE.md:218` (TODO automation onboarding/provisioning API/console)
- `SPECS/CONTROL_PLANE.md`
- `contracts/console_api/openapi.v1.yaml`

## Invariant
- Default read-поток в Console показывает только operational active сущности.
- Архив доступен через явный фильтр, без потери наблюдаемости.
- RBAC и destructive safeguards не деградируют.

## Scope
- Добавить lifecycle query params в `/console/v1/admin/clients` и `/console/v1/admin/branches`.
- Сделать default фильтрацию clients/branches на active.
- Применить lifecycle semantics к platform_admin tenant context (`/console/v1/me` data source).
- Обновить OpenAPI и frontend Tenants UI (`Active / Archived / All`).
- Добавить/обновить тесты на новые read-semantics.

## Out of scope
- Новые lifecycle mutation endpoints (`archive/restore`) для client/branch.
- Миграция legacy `/admin/*` в console ops.
- Membership CRUD completeness и integrations registry/drift guard.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_auth.py`
- `truffles-api/app/schemas/console.py` (если потребуется)
- `contracts/console_api/openapi.v1.yaml`
- `truffles-api/tests/test_console_tenants_list.py`
- `truffles-api/tests/test_console_auth_access.py`
- `truffles-api/tests/test_console_admin_provisioning.py`
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`

## Plan
1. Добавить и валидировать lifecycle params в tenants list API.
2. Внедрить default active фильтры в list clients/branches.
3. Выровнять platform_admin auth context (`accessible_clients`, `branches`) под active-by-default.
4. Обновить OpenAPI и сгенерированные web types.
5. Добавить UI toggle `Active / Archived / All` и проброс params.
6. Обновить/добавить backend tests для default/filter веток.
7. Прогнать checks и собрать evidence.

## DoD
- `/console/v1/admin/clients` default -> только `status=active`.
- `/console/v1/admin/branches` default -> только `is_active=true`.
- Явный lifecycle filter возвращает архив/неактивные/все по запросу.
- `/console/v1/me` для platform_admin не смешивает архив в default selectors.
- Tenants UI переключает режим и выдача соответствует API.
- Все целевые тесты и линтеры green.

## Checks
- `cd truffles-api && pytest tests/test_console_tenants_list.py tests/test_console_auth_access.py tests/test_console_admin_provisioning.py -q`
- `cd truffles-api && python scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint`

## Evidence
- Логи pytest/openapi/lint.
- Сниппеты API вызовов (default vs filtered) на локальном окружении.
- Обновление `STATE.md` (поведенческое изменение Console read semantics, до merge).

## Rollback
- Полный revert коммитов этой задачи.

## No-go
- Не трогать webhook/core decision runtime.
- Не менять legacy `/admin/*` в этом TP.
- Не вводить free-text lifecycle semantics в UI/API.

## Branch / Worktree
- Branch: `feat/2026-02-07-tenant-lifecycle-read-a15`
- Worktree: `/home/zhan/worktrees/2026-02-07-tenant-lifecycle-read-a15`
- Base ref: `main`
- Merge policy: no rebase, merge/ff по процессу
- Cleanup: Brain/Top Architect после merge (удаление worktree + branch)

## Риски/блокеры
- Возможная неявная зависимость UI selectors от archived клиентов.
- Риск несовпадения backend/frontend enum параметров без regen типов.
- Нужна аккуратная обратная совместимость query params для текущего UI.
