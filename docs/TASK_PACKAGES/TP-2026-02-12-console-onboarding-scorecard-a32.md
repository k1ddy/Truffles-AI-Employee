# TP-2026-02-12 Console Onboarding Scorecard (a32)

## Название/цель
Закрыть три приоритетных пункта для Console-first onboarding: добавить calendar surface в canonical OpenAPI, убрать прямую demo-зависимость из generic runtime adapter и ввести onboarding scorecard как жесткий go-live gate.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/SYSTEM_REFERENCE.md`

## Invariant
- Текущий production behavior для `demo_salon` не ухудшается.
- `GO_LIVE_GATE_REQUIRED` продолжает блокировать активацию до выполнения обязательных условий.
- Contract drift check остается fail-closed.

## Scope
- Обновить `contracts/console_api/openapi.v1.yaml` для calendar/onboarding scorecard.
- Обновить `truffles-api/scripts/generate_openapi.py` чтобы drift-check учитывал `calendar` router.
- Добавить/обновить тесты contract/runtime/onboarding.
- Добавить endpoint `GET /console/v1/onboarding/scorecard`.
- Перевести `approve_branch_go_live` на scorecard-based fail.

## Out of scope
- Полная миграция всех legacy `/admin/*` в CI/runbooks.
- Внедрение `minimum_data_contract.v2` по всем нишам.
- Редизайн UI экрана onboarding.

## Touch-list
- `contracts/console_api/openapi.v1.yaml`
- `truffles-api/scripts/generate_openapi.py`
- `truffles-api/app/services/pack_runtime_generic_adapter.py`
- `truffles-api/app/services/pack_runtime_fallback_adapter.py`
- `truffles-api/app/services/onboarding_state.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `truffles-api/tests/test_pack_runtime_service.py`
- `truffles-api/tests/test_console_onboarding_state.py`
- `truffles-api/tests/test_console_access_admin_pr2.py`

## Plan
1. Добавить calendar paths/schemas в canonical OpenAPI.
2. Включить `calendar.router` в openapi generator check.
3. Вынести generic fallback adapter без прямого импорта `demo_salon_knowledge`.
4. Добавить сервисный scorecard + API schema + endpoint.
5. Заменить go-live prereq check на scorecard readiness.
6. Прогнать contract/tests/linters и зафиксировать evidence.

## DoD
- OpenAPI drift check проходит с calendar endpoints.
- В generic adapter нет прямого импорта `demo_salon_knowledge`.
- `GET /onboarding/scorecard` доступен и возвращает pass/fail.
- `approve_branch_go_live` возвращает `GO_LIVE_GATE_REQUIRED` при `scorecard.ready=false`.
- Таргетные тесты проходят.

## Checks
- `cd truffles-api && python3 scripts/generate_openapi.py --check`
- `ruff check truffles-api/app/services/onboarding_state.py truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/app/services/pack_runtime_generic_adapter.py truffles-api/app/services/pack_runtime_fallback_adapter.py truffles-api/tests/test_console_openapi_calendar_contract.py truffles-api/tests/test_pack_runtime_service.py truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_console_access_admin_pr2.py`
- `pytest -q truffles-api/tests/test_console_openapi_calendar_contract.py truffles-api/tests/test_pack_runtime_service.py truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_console_access_admin_pr2.py`
- `pytest -q truffles-api/tests/test_calendar_specialists_router.py`
- `bash scripts/doc_truth_gate.sh`

## Evidence
- Contract drift check output (`generate_openapi.py --check`).
- Pytest summary для таргетных файлов.
- `doc-truth: OK`.

## Rollback
- `git revert` коммита с этим пакетом изменений.

## No-go
- Не ослаблять go-live gate до warning-only режима.
- Не добавлять demo-only hardcode в generic runtime.
- Не править unrelated бизнес-логику webhook/core routing.

## Риски/блокеры
- `openapi_spec_validator` может отсутствовать локально; canonical проверка делается через `generate_openapi.py --check` и CI job.
