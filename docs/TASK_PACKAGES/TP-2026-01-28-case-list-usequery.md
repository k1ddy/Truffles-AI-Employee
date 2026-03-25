# TP-2026-01-28-case-list-usequery

- Название/цель: Исправить отсутствующий импорт `useQuery` в `CaseList`, чтобы убрать runtime/TS ошибку и стабилизировать lint.
- Canon refs: `AGENTS.md`, `docs/SESSION_START_PROMPT.txt`, `STATE.md` (GAP: missing import in `CaseList`).
- Invariant: Поведение UI не меняется; только исправление импорта.
- Scope: `console-web/src/components/CaseList.tsx`.
- Out of scope: Любые изменения фильтров/логики/дизайна CaseList и других компонентов.
- Touch-list (файлы):
  - `console-web/src/components/CaseList.tsx`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-01-28-case-list-usequery-a2.md`
  - `docs/SESSION_INDEX.md`
- Plan:
  1) Добавить импорт `useQuery`.
  2) Запустить lint.
  3) Зафиксировать evidence и обновить `STATE.md`.
- DoD:
  - Импорт добавлен, линтер проходит.
  - `STATE.md` обновлён с evidence.
- Checks:
  - `npm --prefix console-web run lint`
- Evidence:
  - Вывод lint, указание в `STATE.md`.
- Rollback:
  - `git revert COMMIT_SHA`.
- No-go:
  - Линтер не проходит или затронуты другие файлы вне scope.
- Риски/блокеры:
  - Отсутствие `node_modules` (нужен `npm --prefix console-web install`).
- Branch + Worktree + Base ref + Merge policy + Cleanup:
  - Branch: `feat/2026-01-28-case-list-usequery-a2`
  - Worktree: `/home/zhan/worktrees/2026-01-28-case-list-usequery-a2`
  - Base ref: `origin/main`
  - Merge policy: merge в `main` (Top Architect)
  - Cleanup: удалить ветку и worktree после merge
