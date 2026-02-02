# Task Package: Merge origin/main into local main (sync)

- Название/цель: Синхронизировать локальный `main` с `origin/main` после новых изменений, сохраняя doc-only коммит по console web fix TPs.
- Canon refs: `docs/REPORTS/2026-02-01-console-web-fact-audit.md`, `docs/TASK_PACKAGES/TP-2026-02-02-console-web-fix-tps.md`.
- Invariant: Без функциональных изменений; только merge `origin/main` и разрешение конфликтов в документах.
- Scope: Merge `origin/main` в текущий `main` через рабочую ветку; разрешить конфликт в `docs/SESSION_INDEX.md` при необходимости.
- Out of scope: Любые правки кода/логики/данных кроме автоматического merge.
- Touch-list: `docs/SESSION_INDEX.md`, `docs/SESSIONS/SESSION-2026-02-02-merge-origin-main-a4.md`, `docs/TASK_PACKAGES/TP-2026-02-02-merge-origin-main.md`, merge-результат `origin/main`.
- Plan:
  1) Зафиксировать Task Package + session log в ветке merge.
  2) Выполнить `git merge origin/main`.
  3) Разрешить конфликт `docs/SESSION_INDEX.md` с сохранением обеих сторон.
  4) Commit merge и fast-forward `main`.
  5) Push `main` в `origin`.
- DoD:
  - Merge commit создан и содержит resolved `docs/SESSION_INDEX.md`.
  - `main` fast-forwarded до merge commit.
  - `git push origin main` выполнен без ошибок.
  - В `docs/SESSION_INDEX.md` и `docs/SESSIONS/*` есть запись о сессии.
- Checks: `git status -sb`, `git diff --name-only --diff-filter=U`.
- Evidence: merge commit hash + `git show --stat` (фиксируется в итоговом отчете).
- Rollback: `git revert -m 1 MERGE_COMMIT_SHA` при необходимости отката синка.
- No-go: Не менять функциональность и код вручную; не трогать БД/конфиги.
- Branch: `feat/2026-02-02-merge-origin-main-a4`
- Worktree path: `/home/zhan/worktrees/2026-02-02-merge-origin-main-a4`
- Base ref: `main`
- Merge policy: merge `origin/main` в рабочую ветку, затем fast-forward `main`.
- Cleanup: удалить ветку/worktree после успешного пуша.
