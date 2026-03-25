# TP-2026-02-10 SSO Provisioning Env Alias Compatibility (a26)

## Название/цель
Устранить runtime блокер `SSO provisioning is not configured`, если окружение содержит `KEYCLOAK_USERNAME/KEYCLOAK_PASSWORD` вместо `CONSOLE_KEYCLOAK_*`, и улучшить диагностику отсутствующих env.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW/GAP: Team SSO provisioning incident after build `0a52cb1`)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONTROL_PLANE.md`

## Invariant
- SSO provisioning не ослабляет tenant isolation и branch scope.
- Ошибки интеграции остаются fail-fast и прозрачными.
- API контракт `create_agent` не меняется.

## Scope
- Backend resolver SSO admin env в `console.py`.
- Unit tests для env fallback и error details.

## Out of scope
- UI/UX редизайн Team.
- RBAC/branch membership политика.
- Keycloak infra/deploy secrets management.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_access_admin_pr2.py`

## Plan
1. Добавить fallback `KEYCLOAK_USERNAME/KEYCLOAK_PASSWORD` в `_resolve_keycloak_admin_config`.
2. Расширить `details` при `INTEGRATION_UNAVAILABLE` alias-подсказками.
3. Добавить unit tests для fallback и missing-credentials diagnostics.
4. Прогнать targeted pytest.
5. Открыть PR и отдать evidence.

## DoD
- При наличии `KEYCLOAK_ISSUER + KEYCLOAK_USERNAME + KEYCLOAK_PASSWORD` resolver возвращает валидный config.
- При отсутствии admin credentials ошибка содержит `missing` и alias hints.
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py` проходит.

## Checks
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py`

## Evidence
- `git diff --stat`
- pytest output
- PR URL

## Rollback
- Revert commit с изменениями в touch-list.

## No-go
- Не менять `_legacy.py`.
- Не менять booking/decision pipeline.
- Не вводить hardcode credential значений.

## Риски/блокеры
- Если в runtime отсутствуют любые админ-креды Keycloak, provisioning останется недоступным (ожидаемо).
