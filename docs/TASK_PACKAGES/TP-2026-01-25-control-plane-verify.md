# TP-2026-01-25 — Control Plane UI Verification (Provisioning Wizard)

- **Название/цель:** синхронизировать рабочий worktree с `origin/main`, подтвердить визуально наличие Provisioning Wizard в Settings и зафиксировать evidence в `STATE.md`.
- **Canon refs:** `SPECS/CONTROL_PLANE.md`, `docs/CONSOLE_GUIDE.md`, `STATE.md`, `STRUCTURE.md`.

## Invariant
- Никаких изменений backend/DB/API контрактов.
- CI не запускать (только локальная проверка + скрин).
- Доказательства в `STATE.md` только при наличии подтверждений.

## Scope
- Создать рабочий worktree от `origin/main`.
- Запустить локальный UI и сделать скрин Provisioning Wizard.
- Обновить `STATE.md` evidence для PR #348/#355 (Phase 2/3 UI) при подтверждении в коде и скрине.

## Out of scope
- Любые функциональные изменения UI/Backend.
- Исправления тестов/CI.
- Изменения в `SPECS/*`.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-01-25-control-plane-verify.md`
- `docs/REPORTS/2026-01-25-control-plane-provisioning.png`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1) Зафиксировать наличие Phase 2/3 UI в `origin/main` (кодовые подтверждения).
2) При необходимости временно добавить redirect URI для `http://127.0.0.1:3102/*` в Keycloak client `console-web` (после скрина вернуть исходный список).
3) Локально поднять console-web и сделать скрин Settings с Provisioning Wizard.
4) Записать evidence в `STATE.md` и обновить `STRUCTURE.md`.

## DoD
- Скриншот показывает блок `Provisioning Wizard` в Settings.
- `STATE.md` обновлён с evidence (commit/paths + скрин).
- `STRUCTURE.md` содержит новый TP и файл отчёта.

## Checks
- `npm --prefix console-web install`
- `NEXTAUTH_URL=http://127.0.0.1:3102 NEXT_PUBLIC_API_URL=https://api.truffles.kz/console/v1 npm --prefix console-web run dev -- --hostname 127.0.0.1 --port 3102`
- Playwright login + screenshot (см. Evidence).

## Evidence
- Скриншот: `docs/REPORTS/2026-01-25-control-plane-provisioning.png`.
- Подтверждение в коде: `console-web/src/app/settings/page.tsx`, `console-web/src/app/knowledge/page.tsx` (origin/main).
- Temporary Keycloak redirect update (3102) reverted after capture.

## Rollback
- Откатить коммит с обновлением `STATE.md`/`STRUCTURE.md`/скриншотом.

## No-go
- Любые изменения backend/DB/контрактов.
- Запуск CI.

## Риски/блокеры
- Локальный login зависит от Keycloak (`auth.truffles.kz`) и наличия valid creds.

## Branch / Worktree / Merge
- Branch: `docs/control-plane-verify-2026-01-25`
- Worktree: `/home/zhan/worktrees/control-plane-verify`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase (CI не запускать)
- Cleanup: удалить ветку после merge
