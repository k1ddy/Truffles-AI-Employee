# Task Package: Calendar error UI (user-friendly message)

- Название/цель (1–2 предложения)
  - Заменить raw JSON вывод ошибок календаря на понятное сообщение с optional деталями.
- Canon refs (owner‑doc + `STATE.md` NOW/GAP + CA_ID при наличии)
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (UX-01).
  - `docs/CONSOLE_AUDIT/pages/calendar.md`.
- Invariant
  - Поведение календаря и API вызовов не меняется, только UI отображение ошибки.
- Scope
  - Error block для загрузки специалистов на странице календаря.
- Out of scope
  - Изменения API/логики календаря, ретраи, новые события.
- Touch-list (файлы/таблицы)
  - `console-web/src/app/calendar/page.tsx`
  - `docs/CONSOLE_AUDIT/pages/calendar.md`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-02-02-console-calendar-error-ui-a4.md`
- Plan (1..N)
  1) Заменить raw JSON на user-friendly текст + `details` с техническими данными.
  2) Обновить inventory doc и UX backlog (статус fixed + evidence).
  3) Обновить `STATE.md` с evidence (PR/CI).
- DoD
  - UI показывает понятное сообщение об ошибке и скрытые детали.
  - Документация синхронизирована, статус UX-01 закрыт.
- Checks
  - `npm --prefix console-web run lint`
- Evidence
  - PR + CI run URL.
  - Запись в `STATE.md`.
- Rollback
  - `git revert COMMIT_SHA`
- No-go
  - Не менять API/данные и не добавлять новые зависимости.
- Branch / Worktree / Base / Merge / Cleanup
  - Branch: `feat/2026-02-02-console-calendar-error-ui-a4`
  - Worktree: `/home/zhan/worktrees/2026-02-02-console-calendar-error-ui-a4`
  - Base: `origin/main`
  - Merge: PR в `main`
  - Cleanup: удалить worktree/branch после merge
- Риски/блокеры
  - Отсутствие локальных deps для lint (использовать CI как evidence).
