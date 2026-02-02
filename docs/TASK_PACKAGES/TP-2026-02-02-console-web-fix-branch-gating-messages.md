# Task Package: Enforce branch gating on case messages and manager sends

- Название/цель: Добавить branch-ограничения для чтения сообщений кейса и отправки сообщений менеджером.
- Canon refs: `docs/REPORTS/2026-02-01-console-web-fact-audit.md` (Finding 2), `STATE.md` (DONE: Web Console fact audit).
- Invariant: Branch RBAC должен оставаться строгим; platform_admin остаётся с полным доступом.
- Scope: API endpoints:
  - `GET /console/v1/cases/{case_id}/messages`
  - `POST /console/v1/conversations/{conversation_id}/messages`
  - `POST /console/v1/conversations/{conversation_id}/messages/media`
- Out of scope: UI-изменения, изменения схем БД.
- Touch-list: `truffles-api/app/routers/console.py`, `truffles-api/app/services/console_auth.py` (или аналогичная проверка).
- Plan:
  1) Найти существующую проверку branch доступа (используемую в case detail/list).
  2) Добавить branch check в endpoints сообщений:
     - для case_id: проверка по branch_id кейса.
     - для conversation_id: получение conversation → branch_id → проверка.
  3) Добавить негативный тест (403) для cross-branch доступа.
- DoD:
  - Все три endpoint возвращают 403 для пользователя без доступа к branch.
  - Доступ работает корректно при валидной ветке.
  - Поведение platform_admin не меняется.
- Checks:
  - `pytest -q truffles-api/tests -k "branch_access and messages"`
  - при отсутствии теста: добавить новый.
- Evidence: вывод pytest + пример 403 ответа для cross-branch.
- Rollback: `git revert COMMIT_SHA`.
- No-go: Не ослаблять branch RBAC, не менять схему прав.
- Branch: `feat/2026-02-02-console-branch-gating-messages`
- Worktree path: `/home/zhan/worktrees/2026-02-02-console-branch-gating-messages`
- Base ref: `origin/main`
- Merge policy: merge в `main` после CI.
- Cleanup: удалить ветку/worktree после merge.
- Риски/блокеры: Нужно подтвердить корректный источник branch_id для conversation.
