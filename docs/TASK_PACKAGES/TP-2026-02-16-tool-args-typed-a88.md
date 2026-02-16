# TP-2026-02-16-tool-args-typed-a88

- Название/цель: Завершить отдельный системный блок "typed per-tool contracts" без усложнений: единая строгая валидация `tool_args` для policy/schema и runtime tool registry, плюс контрактные регрессии.
- Canon refs: `AGENTS.md` (one-issue flow, local-first), `STATE.md` (remaining systemic item: typed tool args contracts), `SPECS/SYSTEM_REFERENCE.md`.

## Invariant
- Не менять продуктовый контракт `FACT/COLLECT/HANDOFF`.
- Не ослаблять policy/law/safety gates.
- Не добавлять нишевые хардкоды и лексиконные костыли.

## Scope
- Укрепить `validate_tool_args_shape` как единый per-tool typed gate.
- Применить этот gate в runtime (`tool_registry_service`) до исполнения инструмента.
- Добавить контрактные тесты для policy/schema и runtime на невалидные typed args.

## Out of scope
- Иерархическая память.
- Timeout retry/fallback orchestration.
- Новый verifier orchestration stage.

## Touch-list
- `truffles-api/app/schemas/intent.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/tests/test_llm_policy_core.py`
- `truffles-api/tests/test_booking_appointments.py`
- `docs/TASK_PACKAGES/TP-2026-02-16-tool-args-typed-a88.md`
- `docs/SESSIONS/SESSION-2026-02-16-tool-args-typed-a88.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Уточнить schema-level typed contract (`validate_tool_args_shape`) и включить post-validate для `LlmPlanOutput`.
2. Подключить schema contract в runtime `tool_registry_service` с совместимым mapping ошибок.
3. Добавить/обновить контрактные тесты.
4. Прогнать целевые и регрессионные тесты; подготовить PR.

## DoD
- `validate_tool_args_shape` строго валидирует типы по tool action и отклоняет невалидные `tool_args`.
- `execute_tool_action` отклоняет невалидные typed args до runtime side effects.
- Есть регрессионные тесты для policy/schema и runtime.
- `test_message_endpoint.py` не имеет регрессий.

## Checks
- `pytest -q truffles-api/tests/test_llm_policy_core.py`
- `pytest -q truffles-api/tests/test_booking_appointments.py -k "invalid_args_contract_for_book_slot or invalid_args_contract_for_get_booking or invalid_args_contract_for_catalog_location"`
- `pytest -q truffles-api/tests/test_message_endpoint.py`
- `python3 -m py_compile truffles-api/app/schemas/intent.py truffles-api/app/services/tool_registry_service.py`

## Evidence
- Локальные pytest прогоны и py_compile из раздела Checks.

## Rollback
- `git revert COMMIT_SHA` для отката изменений TP.

## No-go
- Не менять `decision.py`/pipeline-ветки вне typed contract задачи.
- Не трогать replay scenarios/baseline.

## Risks/блокеры
- Разъезд error taxonomy между schema и runtime.
- Слишком жёсткая типизация может сломать существующие permissive flows; держим обратную совместимость error-кодов.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-16-tool-args-typed-a88`
- Worktree: `/home/zhan/worktrees/2026-02-16-verifier-timeout-kernel-a88`
- Base ref: `origin/main`
- Merge policy: PR -> `main` после green checks.
- Cleanup: Brain/Top Architect after merge.
