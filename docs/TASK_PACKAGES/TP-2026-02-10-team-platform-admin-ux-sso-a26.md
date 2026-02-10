# TP-2026-02-10 Team Platform Admin UX + SSO Branch Scope (a26)

## Название/цель
Улучшить вкладку `Team` для роли `platform_admin` в условиях большого числа компаний/филиалов, устранить inconsistencies в branch-scope доступе и добавить создание пользователей по SSO login/password с привязкой к выбранному филиалу.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW/GAP по Console Team и platform_admin UX)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/SYSTEM_REFERENCE.md`

## Invariant
- Tenant/branch isolation не ослабляется.
- Non-platform роли не получают новые обходы доступа.
- `platform_admin` сохраняет глобальное управление без разрушения branch-restricted контрактов.

## Scope
- Backend:
  - закрыть branch access inconsistency для branch-scoped privileged memberships;
  - поддержать `create_agent` с `sso_username`/`sso_password` (Keycloak provisioning -> OIDC binding).
- API contract:
  - обновить OpenAPI/typed-контракты для новых SSO полей.
- Frontend Team:
  - сделать membership/agent UX пригодным для большого масштаба (фильтры, search, context-aware selects);
  - добавить форму создания SSO-пользователя с валидными guardrails;
  - улучшить branch scoping поток для ролей ниже `platform_admin`.

## Out of scope
- Полный редизайн Console IA.
- Миграции БД.
- Новый identity provider кроме текущего Keycloak admin API.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_access_admin_pr2.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/app/team/page.tsx`
- `console-web/src/types/api.generated.ts`

## Plan
1. Исправить backend guard, чтобы branch-restricted privileged роли не обходили branch access.
2. Добавить SSO provisioning в `create_agent` и валидации payload.
3. Обновить OpenAPI + generated frontend types.
4. Улучшить Team UX: поиск/фильтры/контекстные списки/SSO поля.
5. Прогнать targeted backend tests + OpenAPI check + frontend generate/lint/build.
6. Подготовить PR с evidence.

## DoD
- Branch-scoped privileged user не имеет доступа вне разрешенного branch.
- `create_agent` принимает SSO login/password и создает связанного OIDC пользователя.
- Team UI позволяет platform_admin эффективно работать с большим числом компаний/филиалов.
- Контракты API и frontend типы синхронизированы.
- Targeted checks проходят локально.

## Checks
- `pytest -q truffles-api/tests/test_console_cases_helpers.py truffles-api/tests/test_console_access_admin_pr2.py`
- `pytest -q truffles-api/tests/test_console_rbac.py truffles-api/tests/test_console_auth_access.py`
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run generate:api`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`

## Evidence
- `git diff --stat`
- Логи из checks
- PR URL

## Rollback
- Revert commit с изменениями в touch-list.

## No-go
- Не трогать `_legacy.py`.
- Не менять decision pipeline/booking flow.
- Не ослаблять RBAC через implicit privileged bypass.

## Риски/блокеры
- Keycloak admin env может отсутствовать в некоторых окружениях.
- Большой UI diff в `team/page.tsx` повышает риск точечных regressions.
