# TP-2026-01-27 — Platform Admin role + RBAC enforcement (Control Plane)

- **Название/цель:** добавить runtime-роль `platform_admin` (global admin) и обеспечить строгий RBAC enforcement в API/UI без расширения прав остальных ролей.
- **Canon refs:** `STATE.md` (NOW), `SPECS/CONTROL_PLANE.md`, `STRATEGY/REQUIREMENTS.md`, `docs/REPORTS/2026-01-27-control-plane-review.md`.
- **Invariant:** fail-closed tenant контекст; manager остаётся branch-scoped; никаких расширений прав без явного решения.
- **Scope:** runtime роль `platform_admin`, серверный RBAC enforcement, UI gating/навигация по роли, контракт роли в Console API, минимальные тесты доступа.
- **Out of scope:** Tenants UI, Inbox UX cleanups, Knowledge UX changes, Trace/Explain v2, миграции БД.
- **Touch-list (ожидаемо):**
  - `SPECS/CONTROL_PLANE.md` (обновить runtime roles + матрицу доступа)
  - `truffles-api/app/services/console_auth.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/models/agent_membership.py`
  - `truffles-api/app/models/agent.py`
  - `truffles-api/tests/test_console_auth_access.py`
  - `truffles-api/tests/test_console_rbac.py` (расширение)
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/components/ConsoleShell.tsx`
  - `contracts/console_api/openapi.v1.yaml`
- **Plan:**
  1) Зафиксировать роль `platform_admin` в runtime enum/моделях и RBAC матрице.
  2) Обновить серверный RBAC enforcement для `platform_admin` (read/write cross-tenant), сохранить fail-closed.
  3) Обновить UI gating/навигацию по роли (скрыть/показать разделы по матрице).
  4) Обновить контракт Console API (role enum/описания).
  5) Добавить/обновить тесты доступа.
  6) Сохранить evidence и обновить `STATE.md` до merge.
- **DoD:**
  - `/console/v1/me` возвращает `role=platform_admin` для соответствующего аккаунта.
  - `platform_admin` имеет доступ к admin endpoints (read/write), остальные роли без расширения прав.
  - UI навигация соответствует матрице (platform_admin видит только разрешённые разделы).
  - Контракт API обновлён и синхронизирован с реализацией.
  - Тесты доступа проходят; CI зелёный.
- **Checks:**
  - `pytest -q truffles-api/tests/test_console_auth_access.py truffles-api/tests/test_console_rbac.py`
  - `npm --prefix console-web run lint` (или явный waiver в TP, если окружение не готово)
  - при изменении контрактов: `npm --prefix console-web run generate:api`
- **Evidence:**
  - CI run URL + тест-логи
  - curl `/console/v1/me` для platform_admin (role + доступы)
  - скриншот навигации (platform_admin vs manager)
  - запись в `STATE.md` до merge (Brain/Top Architect)
- **Rollback:** `git revert` коммитов + откат role enum/guards/навигации.
- **No-go:** любые изменения в core/LLM pipeline, `_legacy.py`, или расширение прав non-platform ролей.
- **Риски/блокеры:** возможные скрытые зависимости UI от admin-доступа; необходимость завести platform_admin аккаунт/cred (зафиксировать отдельно).
- **Branch / Worktree:**
  - Branch: `feat/2026-01-27-platform-admin-a2`
  - Worktree: `/home/zhan/worktrees/2026-01-27-platform-admin-a2`
  - Base ref: `origin/main`
  - Merge policy: merge commit (no rebase)
  - Cleanup: удалить ветку и worktree после merge (Brain/Top Architect)
