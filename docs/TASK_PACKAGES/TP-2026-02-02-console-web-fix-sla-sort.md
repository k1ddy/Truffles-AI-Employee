# Task Package: SLA sort must be server-side

- Название/цель: Перенести сортировку по SLA на серверную сторону, чтобы сорт работал по всем страницам.
- Canon refs: `docs/REPORTS/2026-02-01-console-web-fact-audit.md` (Finding 4).
- Invariant: Существующие сортировки (activity/created_at) не ломаются.
- Scope: `console-web/src/components/CaseList.tsx` + API сортировки `GET /console/v1/cases`.
- Out of scope: UI редизайн, изменение SLA метрик.
- Touch-list: `console-web/src/components/CaseList.tsx`, `truffles-api/app/routers/console.py` (case list), возможно `truffles-api/app/services/*`.
- Plan:
  1) Проверить поддержку `sort_by=sla` на API; если нет — добавить.
  2) Прокинуть `sort_by=sla` из UI в запрос.
  3) Убрать клиентскую сортировку SLA на текущей странице.
  4) Добавить тест на серверную сортировку (минимум unit/contract).
- DoD:
  - Сортировка SLA работает корректно across pages.
  - UI отображает порядок как приходит с API.
- Checks:
  - `pytest -q truffles-api/tests -k "case_list and sla"`
  - `npm --prefix console-web run lint`
- Evidence: pytest вывод + примеры ответа API с сортировкой.
- Rollback: `git revert COMMIT_SHA`.
- No-go: Не менять значения SLA, только сортировку.
- Branch: `feat/2026-02-02-console-sla-sort`
- Worktree path: `/home/zhan/worktrees/2026-02-02-console-sla-sort`
- Base ref: `origin/main`
- Merge policy: merge в `main` после CI.
- Cleanup: удалить ветку/worktree после merge.
- Риски/блокеры: Нужно согласовать формат поля SLA в API и контракте.
