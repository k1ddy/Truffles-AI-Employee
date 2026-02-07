# TP-2026-02-07 Legacy Admin Security Hardening (a15)

## Название/цель
Закрыть уязвимый legacy `/admin/*` perimeter: убрать анонимный доступ к sensitive/mutating endpoints (`prompt/settings/heal`) без поломки существующих CI/runbook, где используются `/admin/health` и `/admin/version`.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW + GAP по консоли/legacy split)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `TECH.md`

## Invariant
- Не ломаем production diagnostics контур: `/admin/health` и `/admin/version` остаются доступными как минимум для текущих CI/runbook.
- Не ослабляем существующую защиту endpoints, где уже есть `X-Admin-Token`.
- Любой mutating/sensitive legacy endpoint должен требовать валидный `X-Admin-Token`.

## Scope
- Legacy router `truffles-api/app/routers/admin.py`:
  - ввести защиту `X-Admin-Token` для `prompt/settings/heal` (read/write mutating + sensitive read).
  - оставить совместимость для `/admin/health` и `/admin/version`.
- Добавить/обновить unit tests на auth guard для legacy admin endpoints.

## Out of scope
- Перенос legacy `/admin/*` в `/console/v1/*`.
- Рефактор бизнес-логики endpoints.
- RBAC/OIDC для legacy `/admin/*`.
- Изменение deployment/runbook политики.

## Touch-list
- `truffles-api/app/routers/admin.py`
- `truffles-api/tests/test_admin_legacy_auth.py` (new)
- (опционально, если понадобится) `TECH.md`/`SPECS/SYSTEM_REFERENCE.md` для заметки о token requirement

## Plan
1. Зафиксировать текущих consumers `/admin/*` (CI/scripts/docs) и определить safe allowlist.
2. Внести guard в `admin.py` для target endpoints (`prompt/settings/heal`) через `X-Admin-Token`.
3. Добавить unit tests: unauthorized -> 401, authorized -> non-401 for guarded routes, and compatibility for open routes (`health/version`).
4. Прогнать локальные тесты в контейнере (`scripts/test_api_container.sh` с таргетными тестами).
5. Подготовить diff/evidence и handoff.

## DoD
- `GET/PUT /admin/prompt/{client_slug}` требуют `X-Admin-Token`.
- `GET/PUT /admin/settings/{client_slug}` требуют `X-Admin-Token`.
- `POST /admin/heal` требует `X-Admin-Token`.
- `/admin/health` и `/admin/version` не сломаны.
- Есть тесты, покрывающие новый guard.

## Checks
- `PYTEST_ARGS=/app/tests/test_admin_legacy_auth.py scripts/test_api_container.sh`
- (при необходимости) `PYTEST_ARGS=/app/tests/test_outbox_service_app.py scripts/test_api_container.sh`

## Evidence
- Логи запуска таргетных тестов (`/tmp/pytest_admin_legacy_auth_*.txt`).
- `git diff --stat` + ссылки на измененные файлы.
- Итоговый статус checks (pass/fail + причина).

## Rollback
- Откатить изменения в `truffles-api/app/routers/admin.py` и тестах одним revert-коммитом ветки.

## No-go
- Не трогать `/admin/health` и `/admin/version` до явной миграции consumers.
- Не менять контракт Console API в этой задаче.
- Не добавлять обходы/feature flags, ослабляющие guard.

## Риски/блокеры
- Возможны скрытые внешние consumers `prompt/settings` без токена; после merge потребуется короткая проверка runtime логов на 401 всплеск.
