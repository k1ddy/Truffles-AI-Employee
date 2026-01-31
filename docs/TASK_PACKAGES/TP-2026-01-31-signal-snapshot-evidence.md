# TP-2026-01-31-signal-snapshot-evidence

- Название/цель: Зафиксировать evidence, что Signal Snapshot Layer пишет decision_meta (test run + запись в STATE).
- Canon refs: `AGENTS.md`, `STATE.md`, `SPECS/ARCHITECTURE.md` (Signal Snapshot Layer), DEC-018.
- Invariant: Поведение/код не меняются; только проверка и документация.
- Scope: Локальный запуск теста signal_snapshot + обновление `STATE.md`/session docs.
- Out of scope: Любые изменения логики/пайплайна/LLM/pack-index.
- Touch-list:
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/TASK_PACKAGES/TP-2026-01-31-signal-snapshot-evidence.md`
  - `docs/SESSIONS/SESSION-2026-01-31-signal-snapshot-evidence-a1.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1) Запустить `pytest -q truffles-api/tests/test_message_endpoint.py -k "signal_snapshot"`.
  2) Сохранить вывод в `/tmp/pytest_signal_snapshot_20260131.txt`.
  3) Обновить `STATE.md` (DONE + evidence).
  4) Обновить session log/index и STRUCTURE.
- DoD:
  - Тесты signal_snapshot проходят.
  - `STATE.md` содержит evidence.
- Checks:
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "signal_snapshot"`
- Evidence:
  - `/tmp/pytest_signal_snapshot_20260131.txt`
- Rollback: `git revert COMMIT_SHA`.
- No-go: Никаких изменений кода/поведения.
- Branch + Worktree + Base ref + Merge policy + Cleanup:
  - Branch: `main` (doc-only)
  - Worktree: `/home/zhan/truffles-main`
  - Base ref: `origin/main`
  - Merge policy: fast-forward
  - Cleanup: не требуется
- Риски/блокеры:
  - Если `pytest` недоступен локально, фиксируем как GAP и требуем CI evidence.
