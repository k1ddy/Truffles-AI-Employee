# TP-2026-01-27 — Verify admin/admin access denial in Console

- **Название/цель:** воспроизвести и подтвердить ошибку доступа для учетки admin/admin ("Нет доступа" / "Нет доступа к Inbox") и зафиксировать evidence.
- **Canon refs:** `STATE.md`, `docs/CONSOLE_GUIDE.md`, `docs/RUNBOOK.md`, `SPECS/CONTROL_PLANE.md`, `TECH.md`.
- **Invariant:** без правок RBAC, без изменений БД и кода; только проверка и evidence.
- **Scope:** вход в Console под admin/admin, фиксация экрана ошибки, получение `/console/v1/me` и сопоставление роли с матрицей доступа.
- **Out of scope:** любые изменения ролей/скоупов/контрактов; исправления UI/API.
- **Touch-list:** нет файлов приложения; только артефакты `/tmp/*` и `/home/zhan/screenshots/*` + запись в `STATE.md` (GAP/FACT).
- **Plan:**
  1) Создать отдельную сессию через `scripts/session_start.sh --force-new`.
  2) Залогиниться в Console под admin/admin и зафиксировать экран ошибки (скрин).
  3) Получить `/console/v1/me` под этим пользователем и сохранить в `/tmp/admin_admin_me.json`.
  4) Сверить роль/контекст с матрицей в `SPECS/CONTROL_PLANE.md` и зафиксировать результат в `STATE.md`.
- **DoD:** есть скрин ошибки + `/tmp/admin_admin_me.json`; в `STATE.md` добавлен GAP/FACT с evidence.
- **Checks:**
  - `curl` к `/console/v1/me` с токеном Keycloak.
  - (опционально) Playwright скриншот страницы ошибки.
- **Evidence:** скрин ошибки, `/tmp/admin_admin_me.json`, ссылка на `/console/v1/me` результат.
- **Rollback:** не требуется (нет кода/БД).
- **No-go:** правки RBAC/кода, изменения данных БД, временные обходы auth.
- **Риски/блокеры:** нет доступа к админским кредам Keycloak; нестабильный auth redirect; блокировка по selection gate.
- **Branch / Worktree:**
  - Branch: `feat/2026-01-27-admin-login-verify-a2`
  - Worktree: `/home/zhan/worktrees/2026-01-27-admin-login-verify-a2`
  - Base ref: `origin/main`
  - Merge policy: doc-only fast-forward in `main` (без PR)
  - Cleanup: удалить ветку и worktree после записи evidence (Top Architect/Brain)
