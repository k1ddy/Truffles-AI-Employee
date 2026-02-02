# Task Package: Fix calendar default date (local timezone)

- Название/цель: Исправить формирование default date в календаре, чтобы не было UTC-сдвига дня.
- Canon refs: `docs/REPORTS/2026-02-01-console-web-fact-audit.md` (Finding 5).
- Invariant: Календарь продолжает открываться на текущей локальной дате.
- Scope: `console-web/src/app/calendar/page.tsx` (formatDate).
- Out of scope: Изменение API, UI-редизайн календаря.
- Touch-list: `console-web/src/app/calendar/page.tsx` (или общий util date при вынесении).
- Plan:
  1) Заменить `toISOString()` на локальное форматирование (`YYYY-MM-DD` из local date).
  2) Добавить Playwright smoke проверку default date (с селектором, который работает на live).
  3) Проверить отображение календаря на границе дня.
- DoD:
  - Default date соответствует локальной дате пользователя.
  - Нет сдвига при UTC offset.
- Checks:
  - `npm --prefix console-web run lint`
  - `npm --prefix console-web run test:e2e:smoke`
- Evidence: лог теста + пример форматирования для локального времени.
- Rollback: `git revert COMMIT_SHA`.
- No-go: Не менять поведение выбора даты пользователем.
- Branch: `feat/2026-02-02-console-calendar-default-date-a4`
- Worktree path: `/home/zhan/worktrees/2026-02-02-console-calendar-default-date-a4`
- Base ref: `origin/main`
- Merge policy: merge в `main` после CI.
- Cleanup: удалить ветку/worktree после merge.
- Риски/блокеры: Требуется согласование тестового фреймворка для console-web.
