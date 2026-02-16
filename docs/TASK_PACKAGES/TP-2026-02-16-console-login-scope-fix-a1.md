# TP-2026-02-16-console-login-scope-fix-a1

- Название/цель: восстановить вход в Console (`console.truffles.kz`) для Platform Admin, убрав неразрешенный scope `offline_access` из дефолтной конфигурации Keycloak и оставив его только как опциональную настройку через env.
- Canon refs: `AGENTS.md`, `STATE.md` (NOW: manager inbox bundle добавил `offline_access` в default scope), `docs/SESSION_START_PROMPT.txt`.
- Invariant: логин через Keycloak должен работать для существующих учетных записей без изменения ролей/прав.
- Scope: default scope для Keycloak в `console-web` + guard, который удаляет `offline_access` без явного разрешения (`KEYCLOAK_ALLOW_OFFLINE_ACCESS=1`).
- Out of scope: правки Keycloak/infra, любые изменения RBAC, UX-изменения, e2e/Playwright.
- Touch-list (файлы/таблицы): `console-web/src/lib/auth.ts`, `STATE.md`.
- Plan:
  1. Обновить default scope в `console-web/src/lib/auth.ts`: убрать `offline_access`, оставить `openid profile email` и поддержку `KEYCLOAK_SCOPE` как override.
  2. Добавить guard: `offline_access` пропускается только если `KEYCLOAK_ALLOW_OFFLINE_ACCESS=1`, иначе удаляется и логируется предупреждение.
  3. Прогнать целевой lint для файла.
  4. Обновить `STATE.md` с фактом локальной правки и статусом deploy (если без прод‑evidence).
  5. Commit + push + PR.
- DoD:
  - `offline_access` отсутствует в default scope и не ломает конфигурацию провайдера.
  - `KEYCLOAK_SCOPE` продолжает работать как override.
  - Без `KEYCLOAK_ALLOW_OFFLINE_ACCESS=1` `offline_access` всегда отфильтрован.
  - Локальный lint без ошибок.
- Checks:
  - `npm --prefix console-web run lint -- --file src/lib/auth.ts`
  - `./scripts/session_check.sh`
- Evidence:
  - diff + lint output; запись в `STATE.md` (DONE local + deploy pending).
- Rollback:
  - revert commit или задать `KEYCLOAK_SCOPE` обратно с `offline_access` при необходимости.
- No-go:
  - Не менять Keycloak server/client настройки.
  - Не трогать RBAC/permissions.
  - Не добавлять новые UI/UX изменения.
- Риски/блокеры:
  - Если Keycloak клиент действительно требует `offline_access`, это нужно включить через `KEYCLOAK_SCOPE` на env стороне.
- Branch + Worktree path + Base ref + Merge policy + Cleanup:
- Branch: `feat/2026-02-16-console-login-scope-fix-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-16-console-login-scope-a1`
  - Base ref: `origin/main`
  - Merge policy: PR -> main (non‑rebase)
  - Cleanup: удалить worktree/branch после merge
