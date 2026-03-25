# TP-2026-02-10 Tenants Platform Admin Fixes (a24)

## Название/цель
Устранить критичные баги и низкую операционную ценность вкладки `Tenants` для роли `platform_admin`: закрыть cross-tenant write дыры, синхронизировать листинги с контекстом и повысить actionability risk-панели.

## Canon refs
- `AGENTS.md`
- `STATE.md` (Tenants / platform_admin scope)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONTROL_PLANE.md`
- `docs/CONSOLE_AUDIT/pages/tenants.md`
- `docs/CONSOLE_AUDIT/roles/platform_admin.md`

## Invariant
- Tenant isolation и RBAC не ослабляются.
- `platform_admin` сохраняет full cross-tenant write; non-platform роли не получают новых обходов.
- Контракты API `/console/v1/admin/*` не ломаются.

## Scope
- Backend hardening в provisioning write endpoints: access checks для company/client/branch lifecycle/update/create flows.
- Тесты на cross-tenant deny matrix для owner/admin контекста.
- Frontend `Tenants`:
  - clients list фильтрация по company context;
  - branches list фильтрация по client context;
  - Risk panel: action buttons для быстрого перехода в `Integrations`/`Inbox`/контекст;
  - улучшение контекстной читаемости и ключевых UI labels;
  - замена ручного `Company ID` input на company selector в client edit.

## Out of scope
- Редизайн всей Console IA.
- Миграции БД.
- Bulk operations и новые backend endpoints.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_admin_provisioning.py`
- `console-web/src/app/tenants/page.tsx`

## Plan
1. Добавить недостающие backend guards на write paths.
2. Добавить/обновить backend тесты на `ACCESS_DENIED` cross-tenant.
3. Исправить frontend scope filtering в `Tenants`.
4. Добавить action-oriented UX в risk panel и улучшить формы редактирования.
5. Прогнать targeted pytest + frontend lint и подготовить PR.

## DoD
- Любая cross-tenant write попытка non-platform роли отклоняется `ACCESS_DENIED`.
- Tenants clients/branches отображают данные в текущем context scope.
- Risk panel позволяет перейти к операционным действиям из карточки риска.
- Локальные проверки проходят.

## Checks
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py`
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py truffles-api/tests/test_console_tenants_list.py`
- `npm --prefix console-web run lint`

## Evidence
- `git diff --stat`
- Вывод команд checks из текущей сессии
- PR URL

## Rollback
- Revert commit с изменениями в трех файлах touch-list.

## No-go
- Не трогать `_legacy.py`.
- Не менять runtime webhook/decision pipeline.
- Не добавлять обходы `require_console_permission`.

## Риски/блокеры
- Риск UI-регрессий в Tenants из-за большой страницы.
- Митигация: ограниченный diff + lint + targeted backend tests.
