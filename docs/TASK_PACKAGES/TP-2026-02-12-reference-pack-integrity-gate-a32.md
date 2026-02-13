# TP-2026-02-12 Reference Pack Integrity Gate v2 (a32)

## Название/цель
Добавить fail-closed integrity gate для reference packs: проверка не только наличия, но и целостности (schema version, обязательные metadata поля, checksum), и включить этот gate в onboarding scorecard/autopilot/go-live.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: цель ускоренного onboarding + fail-closed go/no-go)
- `SPECS/SYSTEM_REFERENCE.md`
- `SPECS/ARCHITECTURE.md`

## Invariant
- Go-live/activation остаются fail-closed.
- Multi-tenant безопасность и текущие RBAC/tenant gates не ослабляются.
- Existing active reference packs без integrity metadata не должны silently считаться готовыми.

## Scope
- Ввести integrity contract v2 для reference pack metadata.
- Проверять integrity в `build_onboarding_inputs` / scorecard.
- Пробросить детальные missing-коды в go/no-go.
- Обновить/добавить backend tests.

## Out of scope
- Полный редизайн UI onboarding.
- Массовая миграция всех старых reference packs в БД.
- Перевод CI/runbooks на console-first (следующий этап).

## Touch-list
- `truffles-api/app/services/onboarding_state.py`
- `truffles-api/app/routers/console.py` (если потребуется only for surfaced missing details)
- `truffles-api/tests/test_console_onboarding_state.py`
- `truffles-api/tests/test_console_access_admin_pr2.py` (если потребуется)
- `truffles-api/tests/test_console_onboarding_contract_api.py` (если потребуется)

## Plan
1. Формализовать integrity signals (schema/version/metadata/checksum).
2. Встроить проверку в onboarding inputs + go/no-go missing.
3. Убедиться, что autopilot/go-live автоматически блокируются через scorecard fail.
4. Добавить тесты на pass/fail кейсы integrity.
5. Прогнать таргетные pytest suites.

## DoD
- `reference_pack` считается готовым только при integrity pass (не только status=active).
- `onboarding scorecard` возвращает fail и детальные missing-коды при integrity нарушении.
- `autopilot activate`/`go-live approve` блокируются этим fail-closed контуром без обходов.
- Таргетные тесты зеленые.

## Checks
- `pytest -q truffles-api/tests/test_console_onboarding_state.py`
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "scorecard or go_live or autopilot"`
- `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py`

## Evidence
- Логи pytest прогонов.
- Diff по `onboarding_state` + scorecard missing codes.
- Session log + index обновления.

## Rollback
- `git revert SHA`

## No-go
- Не переводить gate в warning-only.
- Не добавлять demo-specific хардкоды.
- Не менять unrelated onboarding/business логику.

## Риски/блокеры
- Старые reference packs без metadata будут fail до апдейта данных (ожидаемо и целевое поведение fail-closed).
