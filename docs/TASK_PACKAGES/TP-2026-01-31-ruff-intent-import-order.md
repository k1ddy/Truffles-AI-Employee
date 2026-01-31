# TP-2026-01-31-ruff-intent-import-order

- Название/цель: Исправить ruff I001 (import order) в `truffles-api/tests/test_intent.py`, чтобы CI на origin/main был зелёным.
- Canon refs: `AGENTS.md`, `STATE.md` (NOW/PLAN: fix ruff I001 for `test_intent.py`), CI https://github.com/k1ddy/Truffles-AI-Employee/actions/runs/21538671466.
- Invariant: Нет изменений поведения; только порядок импортов в тесте.
- Scope: Перестановка импортов в `truffles-api/tests/test_intent.py`; обновление `STATE.md` и `STRUCTURE.md`.
- Out of scope: Любая бизнес-логика, схемы, промпты, пайплайн.
- Touch-list:
  - `truffles-api/tests/test_intent.py`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/TASK_PACKAGES/TP-2026-01-31-ruff-intent-import-order.md`
  - `docs/SESSIONS/SESSION-2026-01-31-ruff-intent-import-order-a1.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1) Создать сессию + worktree по TP.
  2) Исправить порядок импортов в `test_intent.py`.
  3) Прогнать `ruff` и `pytest` для `test_intent.py`.
  4) Обновить `STATE.md` с evidence.
  5) Коммит + PR + merge после зелёного CI.
- DoD:
  - `ruff` больше не сообщает I001 в `test_intent.py`.
  - `pytest -q truffles-api/tests/test_intent.py` проходит.
  - CI в PR зелёный.
- Checks:
  - `python -m ruff check truffles-api/tests/test_intent.py`
  - `pytest -q truffles-api/tests/test_intent.py`
- Evidence:
  - Локальные выводы `ruff`/`pytest`.
  - Обновление `STATE.md` с evidence + ссылка на CI.
- Rollback: `git revert COMMIT_SHA`.
- No-go: Никаких изменений в core-логике/entrypoints/БД.
- Branch + Worktree + Base ref + Merge policy + Cleanup:
  - Branch: `feat/2026-01-31-ruff-intent-import-order-a1`
  - Worktree: `/home/zhan/worktrees/2026-01-31-ruff-intent-import-order-a1`
  - Base ref: `origin/main`
  - Merge policy: merge (no rebase)
  - Cleanup: удалить ветку + worktree после merge
- Риски/блокеры:
  - Если `ruff` недоступен локально, полагаемся на CI и ручную проверку порядка импортов.
