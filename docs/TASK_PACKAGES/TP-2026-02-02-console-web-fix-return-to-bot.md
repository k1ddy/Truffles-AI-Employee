# Task Package: Fix case return endpoint (return to bot, not resolve)

- Название/цель: Исправить `POST /console/v1/cases/{case_id}/return`, чтобы кейс возвращался боту/в pending без закрытия как resolved.
- Canon refs: `docs/REPORTS/2026-02-01-console-web-fact-audit.md` (Finding 1), `STATE.md` (DONE: Web Console fact audit).
- Invariant: Возврат кейса не должен проставлять resolved/закрытие и не должен ломать существующие действия resolve/take.
- Scope: Логика return endpoint в `truffles-api/app/routers/console.py` + связанные сервисы состояния кейса.
- Out of scope: Изменения UI, изменение схем БД, правки других endpoint.
- Touch-list: `truffles-api/app/routers/console.py`, возможно `truffles-api/app/services/*` (state manager).
- Plan:
  1) Найти текущий вызов `state_manager_resolve` в endpoint `/return`.
  2) Заменить на корректную операцию возврата (если есть `state_manager_return_to_bot`/`state_manager_reopen` — использовать; иначе добавить отдельный метод).
  3) Убедиться, что `resolution_notes`, `resolved_at`, `resolved_by` не выставляются при return.
  4) Добавить/обновить тест на endpoint `/return`.
- DoD:
  - `/console/v1/cases/{id}/return` оставляет кейс в активном/pending состоянии.
  - В ответе кейс не имеет `resolved_at`/`resolution_notes`.
  - Кейс снова виден в очереди бота/не закреплен за менеджером.
- Checks:
  - `pytest -q truffles-api/tests -k "case_return"`
  - при отсутствии теста: добавить новый в `truffles-api/tests`.
- Evidence: логи pytest + JSON ответ `/return` до/после.
- Rollback: `git revert -m 1 MERGE_COMMIT_SHA` или обычный `git revert COMMIT_SHA`.
- No-go: Не менять логику resolve/take, не править БД вручную.
- Branch: `feat/2026-02-02-console-case-return-to-bot`
- Worktree path: `/home/zhan/worktrees/2026-02-02-console-case-return-to-bot`
- Base ref: `origin/main`
- Merge policy: merge в `main` после CI.
- Cleanup: удалить ветку/worktree после merge.
- Риски/блокеры: Нужно подтвердить правильный статус "возврата" в state manager.
