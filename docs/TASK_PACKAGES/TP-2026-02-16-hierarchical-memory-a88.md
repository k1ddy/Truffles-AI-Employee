# TP-2026-02-16-hierarchical-memory-a88

- Название/цель: Минимально внедрить hierarchical memory для runtime ответа: short-term history + compact summary из старых turn'ов вместо жёсткого окна только последних N сообщений.
- Canon refs: `AGENTS.md` (one-issue flow), `STATE.md` (remaining systemic: hierarchical memory), `SPECS/SYSTEM_REFERENCE.md`.

## Invariant
- Не менять контракт `FACT/COLLECT/HANDOFF`.
- Не менять policy/law gates.
- Не использовать LLM для summary на этом шаге (детерминированный и дешёвый слой).

## Scope
- `truffles-api/app/services/ai_service.py`: расширить `get_conversation_history` с bounded summary блока старых сообщений.
- `truffles-api/tests/test_ai_service.py`: покрыть контракты summary-injection.

## Out of scope
- Перестройка memory profile/session memory в `decision.py`.
- Векторная long-term memory.

## Touch-list
- `truffles-api/app/services/ai_service.py`
- `truffles-api/tests/test_ai_service.py`
- `docs/TASK_PACKAGES/TP-2026-02-16-hierarchical-memory-a88.md`
- `docs/SESSIONS/SESSION-2026-02-16-hierarchical-memory-a88.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Добавить deterministic helper для compact summary старых сообщений.
2. Обновить `get_conversation_history`: recent tail + optional summary prefix.
3. Добавить unit-тесты на summary контракт.
4. Прогнать `test_ai_service.py` + compile.

## DoD
- При длинном диалоге в history появляется bounded summary старых turn'ов.
- При коротком диалоге поведение без изменений.
- Тесты зелёные.

## Checks
- `pytest -q truffles-api/tests/test_ai_service.py`
- `python3 -m py_compile truffles-api/app/services/ai_service.py`

## Evidence
- Выводы pytest + py_compile.

## Rollback
- `git revert COMMIT_SHA`.

## No-go
- Не трогать `decision.py` и policy-core orchestration.
- Не добавлять новые внешние зависимости.

## Risks/блокеры
- Слишком длинный summary может раздувать prompt; ограничиваем lines/chars.
- Неверная роль summary в history; фиксируем единый формат и тестами.

## Branch / Worktree / Merge policy / Cleanup
- Branch: `feat/2026-02-16-hierarchical-memory-a88`
- Worktree: `/home/zhan/worktrees/2026-02-16-wave123-a88`
- Base ref: `origin/main`
- Merge policy: PR -> `main` после green checks.
- Cleanup: Brain/Top Architect after merge.
