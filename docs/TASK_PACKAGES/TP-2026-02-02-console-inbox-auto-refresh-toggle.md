# Task Package: Inbox auto-refresh toggle

- Название/цель (1–2 предложения)
  - Добавить индикатор и переключатель автообновления очереди, чтобы пользователь мог контролировать refresh.
- Canon refs (owner‑doc + `STATE.md` NOW/GAP + CA_ID при наличии)
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (UX-03).
  - `docs/CONSOLE_AUDIT/pages/inbox.md`.
- Invariant
  - Поведение фильтров и выбор кейса не меняются; автообновление по умолчанию остаётся включённым.
- Scope
  - UI/logic автообновления в очереди Inbox (CaseList).
- Out of scope
  - Изменения API, SSE/websocket, новый polling backend.
- Touch-list (файлы/таблицы)
  - `console-web/src/components/CaseList.tsx`
  - `docs/CONSOLE_AUDIT/pages/inbox.md`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-02-02-console-inbox-auto-refresh-toggle-a4.md`
- Plan (1..N)
  1) Добавить переключатель автообновления и связать его с `refetchInterval`.
  2) Обновить инвентарь Inbox и UX backlog (статус fixed + evidence).
  3) Обновить `STATE.md` с evidence (PR/CI).
- DoD
  - Пользователь может включать/выключать автообновление.
  - UI явно показывает состояние автообновления.
  - Документация синхронизирована и UX-03 закрыт.
- Checks
  - `npm --prefix console-web run lint`
- Evidence
  - PR + CI run URL.
  - Запись в `STATE.md`.
- Rollback
  - `git revert COMMIT_SHA`
- No-go
  - Не менять формат данных и контракт API.
- Branch / Worktree / Base / Merge / Cleanup
  - Branch: `feat/2026-02-02-console-inbox-auto-refresh-toggle-a4`
  - Worktree: `/home/zhan/worktrees/2026-02-02-console-inbox-auto-refresh-toggle-a4`
  - Base: `origin/main`
  - Merge: PR в `main`
  - Cleanup: удалить worktree/branch после merge
- Риски/блокеры
  - Отсутствие локальных deps для lint (использовать CI как evidence).
