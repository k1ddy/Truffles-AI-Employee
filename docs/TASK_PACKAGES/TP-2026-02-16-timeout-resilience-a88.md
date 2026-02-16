# TP-2026-02-16-timeout-resilience-a88

- Название/цель: Усилить timeout-resilience в runtime LLM-ответе (`generate_ai_response`) без изменения продуктового контракта: retry timeout/transient + fallback model + явная telemetry деградации.
- Canon refs: `AGENTS.md` (local-first, one-issue flow), `STATE.md` (remaining systemic: timeout-resilience), `SPECS/SYSTEM_REFERENCE.md`.

## Invariant
- Не менять контракт `FACT/COLLECT/HANDOFF`.
- Не ослаблять policy/law/safety gates.
- Не добавлять нишевые хардкоды.

## Scope
- `truffles-api/app/services/ai_service.py`: retry/fallback для `generate_ai_response`.
- `truffles-api/tests/test_ai_service.py`: контрактные тесты timeout/transient/fallback поведения.

## Out of scope
- Изменения в planner/controller policy-core (`intent_service.py`).
- Иерархическая память.

## Touch-list
- `truffles-api/app/services/ai_service.py`
- `truffles-api/tests/test_ai_service.py`
- `docs/TASK_PACKAGES/TP-2026-02-16-timeout-resilience-a88.md`
- `docs/SESSIONS/SESSION-2026-02-16-timeout-resilience-a88.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Добавить минимальные retry/fallback env-настройки и helper-классификатор transient ошибок.
2. Перевести `generate_ai_response` на bounded retry/fallback flow.
3. Обновить timing_context/метаданные деградации и покрыть тестами.
4. Прогнать целевые тесты.

## DoD
- На timeout делается retry и при необходимости fallback model.
- На transient provider error делается ровно один retry.
- Неуспех после bounded retries деградирует в `low_confidence`, без падения пайплайна.
- Контрактные тесты зелёные.

## Checks
- `pytest -q truffles-api/tests/test_ai_service.py`
- `python3 -m py_compile truffles-api/app/services/ai_service.py`

## Evidence
- Выводы pytest + py_compile.

## Rollback
- `git revert COMMIT_SHA`.

## No-go
- Не менять `decision.py` и policy-core orchestration.
- Не трогать replay scenarios/baseline.

## Risks/блокеры
- Чрезмерный retry может увеличить latency; ограничиваем попытки и timeout window.
- Неправильная классификация transient ошибок; покрываем unit-тестами.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-16-timeout-resilience-a88`
- Worktree: `/home/zhan/worktrees/2026-02-16-wave123-a88`
- Base ref: `origin/main`
- Merge policy: PR -> `main` после green checks.
- Cleanup: Brain/Top Architect after merge.
