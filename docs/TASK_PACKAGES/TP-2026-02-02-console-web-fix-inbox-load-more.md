# Task Package: Inbox "Load more" should append, not replace

- Название/цель: Исправить пагинацию Inbox, чтобы "Load more" добавлял элементы, а не заменял текущий список.
- Canon refs: `docs/REPORTS/2026-02-01-console-web-fact-audit.md` (Finding 3).
- Invariant: Порядок кейсов сохраняется, без дубликатов; cursor и фильтры работают как раньше.
- Scope: `console-web/src/components/CaseList.tsx` (state управления списком).
- Out of scope: API изменения и другие UX правки.
- Touch-list: `console-web/src/components/CaseList.tsx`.
- Plan:
  1) Ввести накопительный state списка (append по `cursor`).
  2) Дедупликация по case_id при добавлении следующей страницы.
  3) Сохранить корректный `hasMore` и `cursor` при фильтрах.
  4) Добавить тест/проверку поведения загрузки нескольких страниц.
- DoD:
  - После "Load more" предыдущие кейсы остаются в списке.
  - Нет дубликатов и пропусков при смене фильтров.
- Checks:
  - `npm --prefix console-web run lint`
  - Playwright/компонентный тест на пагинацию (добавить при отсутствии).
- Evidence: скринкаст/лог теста + ссылка на тестовый файл.
- Rollback: `git revert COMMIT_SHA`.
- No-go: Не менять API контракт и сортировку.
- Branch: `feat/2026-02-02-console-inbox-load-more`
- Worktree path: `/home/zhan/worktrees/2026-02-02-console-inbox-load-more`
- Base ref: `origin/main`
- Merge policy: merge в `main` после CI.
- Cleanup: удалить ветку/worktree после merge.
- Риски/блокеры: Нужно убедиться, что объединение не ломает виртуализацию списка.
