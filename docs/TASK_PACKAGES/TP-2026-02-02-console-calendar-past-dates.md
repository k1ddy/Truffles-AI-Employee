# TP-2026-02-02-console-calendar-past-dates

- Название/цель: Добавить в Calendar переключатель "Показывать прошлые даты" и снять ограничение min для даты.
- Canon refs: `STATE.md` (UX backlog), `docs/CONSOLE_AUDIT/UX_BACKLOG.md` (UX-02).
- Invariant:
  - Никаких изменений API/DB.
  - Создание записей и текущая логика календаря не меняются.
  - Без неожиданных файлов в diff.
- Scope:
  - UI‑переключатель для прошлых дат.
  - Если переключатель выключен, дата не может быть раньше сегодня.
  - Обновить UX backlog + STATE + сессионные доки.
- Out of scope:
  - Любые изменения Provisioning Wizard.
  - Новые фичи календаря кроме переключателя.
- Touch-list:
  - `console-web/src/app/calendar/page.tsx`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`
  - `docs/TASK_PACKAGES/TP-2026-02-02-console-calendar-past-dates.md`
  - `docs/SESSIONS/SESSION-2026-02-02-console-calendar-past-dates-a5.md`
  - `docs/SESSION_INDEX.md`
  - `STRUCTURE.md`
  - `STATE.md`
- Plan:
  1. Добавить toggle "Показывать прошлые даты" в фильтры календаря.
  2. Обновить backlog/STATE/сессионные доки.
  3. Прогнать lint и открыть PR.
- DoD:
  - Переключатель доступен; при включении можно выбрать прошлые даты.
  - При выключении и выбранной прошлой дате UI возвращает дату на сегодня.
  - CI зелёный.
- Checks:
  - `npm --prefix console-web run lint`
  - CI on PR.
- Evidence:
  - CI run URL.
  - Локальный lint лог (если запускался).
- Rollback:
  - Реверт коммита или отключение переключателя.
- No-go:
  - Изменения API/DB.
  - Новые тесты без необходимости; тест‑waiver: UI‑переключатель без отдельного теста, полагаемся на lint + CI e2e.
- Риски/блокеры:
  - Возможна несинхронизация выбранной даты при выключении переключателя — устраняем reset на сегодня.
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-02-console-calendar-past-dates-a5`
  - Worktree: `/home/zhan/worktrees/2026-02-02-console-calendar-past-dates-a5`
  - Base ref: `origin/main`
  - Merge policy: merge-only
  - Cleanup: удалить worktree/branch после merge
