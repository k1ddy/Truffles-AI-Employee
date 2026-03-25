# Task Package: Console Web fix Task Packages (doc-only)

- Название/цель: Сформировать отдельные Task Packages для устранения найденных багов/UX-отклонений в Web Console (по факту аудита).
- Canon refs: `docs/REPORTS/2026-02-01-console-web-fact-audit.md`, `STATE.md` (DONE: Web Console fact audit).
- Invariant: Только документы; без изменений кода/поведения/данных.
- Scope: Создать набор Task Packages по каждому найденному issue; обновить session log + index.
- Out of scope: Любые изменения в `console-web`/`truffles-api`, тесты, запуск CI.
- Touch-list: `docs/TASK_PACKAGES/TP-2026-02-02-console-web-fix-*.md`, `docs/SESSIONS/SESSION-2026-02-02-console-web-fix-tps-a4.md`, `docs/SESSION_INDEX.md`.
- Plan:
  1) Создать session log и добавить запись в `docs/SESSION_INDEX.md`.
  2) Сформировать Task Packages для 5 найденных багов/UX-отклонений.
  3) Проверить отсутствие плейсхолдеров.
  4) Закрыть сессию и закоммитить doc-only изменения.
- DoD:
  - 5 Task Packages созданы и ссылаются на фактические findings.
  - Session log + index обновлены и статус `done`.
  - Коммит doc-only готов к push.
- Checks: `git status -sb`, optional scan for placeholder markers in `docs/TASK_PACKAGES`.
- Evidence: hash коммита + `git show --stat`.
- Rollback: `git revert COMMIT_SHA` при необходимости отката.
- No-go: Не менять код/поведение; не править БД/конфиги.
- Branch: `feat/2026-02-02-console-web-fix-tps-a4`
- Worktree path: `/home/zhan/worktrees/2026-02-02-console-web-fix-tps-a4`
- Base ref: `main`
- Merge policy: fast-forward в `main` после push.
- Cleanup: удалить ветку/worktree после merge.
