# TP-2026-01-26 — Control Plane RBAC matrix + enforcement

- **Название/цель:** зафиксировать матрицу прав (role × section × read/write) и обеспечить единообразное enforcement в API и UI для Console.
- **Invariant:** strict tenant isolation (company/client/branch); fail-closed по контексту; без расширения прав по умолчанию.
- **Scope:** документирование RBAC-матрицы, серверные проверки прав на console endpoints, UI gating в навигации/действиях, тесты на доступы.
- **Out of scope:** изменения core/LLM pipeline, миграции БД, бизнес-логика вне Console, дизайн/редизайн UI.
- **Touch-list (ожидаемо):**
  - `SPECS/CONTROL_PLANE.md` (RBAC matrix + принцип доступа)
  - `docs/CONSOLE_GUIDE.md` (role runbooks + доступы)
- `truffles-api/app/services/console_auth.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/calendar.py`
- `truffles-api/app/schemas/console.py` (если нужны новые поля)
- `truffles-api/tests/test_console_auth_access.py`
- `truffles-api/tests/test_console_rbac.py` (новые тесты)
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/app/*` (ограничение действий по роли)
- `console-web/src/lib/api-client.ts` (RBAC helpers для UI, error code updates)
- `contracts/console_api/openapi.v1.yaml` (если меняются ошибки/ответы)
- **Plan:**
  1) Снять фактические права из кода (console_auth + console routes) и зафиксировать RBAC‑матрицу в `SPECS/CONTROL_PLANE.md`.
  2) Ввести единые helper‑guards для console endpoints (role × action) и привести маршруты к матрице.
  3) Обновить UI gating: навигация + кнопки/CTA для write‑действий по роли (read‑only поведение).
  4) Добавить тесты на RBAC (минимум 1 тест на каждый раздел: Inbox/Knowledge/Team/Calendar/Settings/Ops).
  5) Обновить runbooks по ролям в `docs/CONSOLE_GUIDE.md` и синхронизировать контракты/ошибки.
- **DoD:**
  - RBAC матрица опубликована и не противоречит коду.
  - API возвращает 403 для запрещённых действий по роли (owner/admin/manager/support).
  - UI не показывает write‑действия для read‑only ролей; подтверждено тестами.
  - Тесты RBAC покрывают ключевые разделы и проходят.
- **Checks:**
  - `pytest -q truffles-api/tests/test_console_auth_access.py truffles-api/tests/test_console_rbac.py`
  - `npm --prefix console-web run lint`
  - при изменении контрактов: `npm --prefix console-web run generate:api`
- **Evidence:** CI run URL + тест‑вывод; обновление `STATE.md` с PR/CI evidence.
- **Rollback:** `git revert` PR; вернуть guards и UI gating к прежнему состоянию.
- **No-go:** не менять `docs/CONSULTANT_CODEMAP.md`; не расширять доступы без явного решения/DEC.
- **Риски/блокеры:** несоответствие ожиданий по ролям (нужна финальная матрица от Owner/Brain); возможные скрытые зависимости UI от админ‑доступа.
- **Branch / Worktree:**
  - Branch: `docs/control-plane-rbac-matrix`
  - Worktree: `/home/zhan/worktrees/control-plane-rbac-matrix`
  - Base ref: `origin/main`
  - Merge policy: merge commit (no rebase)
  - Cleanup: удалить ветку и worktree после merge (Brain)
