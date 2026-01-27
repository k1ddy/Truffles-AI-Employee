# TP-2026-01-27 — Close GAP: platform_admin Inbox AccessDenied (docs-only)

- **Название/цель:** закрыть GAP в `STATE.md` с evidence: admin/admin (role `platform_admin`) видит Inbox без AccessDenied.
- **Canon refs:** `STATE.md`, `SPECS/CONTROL_PLANE.md`, `STRATEGY/REQUIREMENTS.md`.
- **Invariant:** только docs; без изменений кода/деплоя/прав доступа; fail‑closed сохраняется.
- **Scope:** обновить `STATE.md` и сессионные документы (session log + index).
- **Out of scope:** любые изменения в `console-web`/backend, деплой, тесты.
- **Touch-list:**
  - `STATE.md`
  - `docs/TASK_PACKAGES/TP-2026-01-27-platform-admin-ui-rbac.md`
  - `docs/SESSIONS/SESSION-2026-01-27-platform-admin-ui-rbac-a2.md`
  - `docs/SESSION_INDEX.md`
- **Plan:**
  1) Проверить наличие evidence файла (скрин Inbox).
  2) Обновить `STATE.md` (GAP → DONE) с ссылкой на evidence.
  3) Обновить session log + `docs/SESSION_INDEX.md` (status=done).
  4) `scripts/session_check.sh`, commit, push.
- **DoD:**
  - GAP закрыт в `STATE.md` с evidence.
  - Сессионные документы обновлены и отмечены как done.
- **Checks:** `scripts/session_check.sh`
- **Evidence:** `/home/zhan/screenshots/console-admin-deny-2026-01-27T11-29-06-656Z/01-home.png`, `/tmp/admin_admin_me.json`.
- **Rollback:** revert commit.
- **No-go:** любые кодовые/деплой изменения.
- **Branch / Worktree:**
  - Branch: `feat/2026-01-27-platform-admin-ui-rbac-a2`
  - Worktree: `/home/zhan/worktrees/2026-01-27-platform-admin-ui-rbac-a2`
  - Base ref: `origin/main`
  - Merge policy: PR (no rebase)
  - Cleanup: удалить ветку/ворктри после merge
