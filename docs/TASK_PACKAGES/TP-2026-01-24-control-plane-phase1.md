# TP-2026-01-24 — Control Plane Phase 1 (Layout + Context + Roles)

- **Название/цель:** внедрить Phase 1 UX каркас: sidebar + top context bar, role‑based navigation, и fail‑closed tenant selection в Console UI.
- **Canon refs:** `SPECS/CONTROL_PLANE.md`, `SPECS/MULTI_TENANT.md`, `SPECS/ESCALATION.md`, `docs/CONSOLE_GUIDE.md`, `STRATEGY/REQUIREMENTS.md`, `STATE.md`.

## Invariant
- Никаких изменений в backend API/контрактах.
- Fail‑closed при отсутствии `X-Client-Id`/`X-Branch-Id`.
- Никаких “догадок” о tenant‑контексте.

## Scope
- Общий Layout (sidebar + header + content slot).
- Context Bar: Company/Client/Branch.
- Ролевая навигация (owner/admin/manager/support).
- Tenant selection UI на основе `/console/v1/me`.

## Out of scope
- Provisioning, Knowledge Studio, Team, Integrations UI.
- Любые изменения backend/DB.
- 3‑pane Inbox (Phase 5).

## Touch-list
- `console-web/src/app/layout.tsx`
- `console-web/src/app/page.tsx`
- `console-web/src/app/providers.tsx`
- `console-web/src/components/ConsoleShell.tsx`
- `docs/CONSOLE_GUIDE.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-control-plane-phase1.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Добавить общий Layout (sidebar + header + content slot).
2) Реализовать Context Bar с клиентом/филиалом.
3) Подключить `/console/v1/me` и хранить выбор в localStorage.
4) Включить role‑based menu.
5) Обновить `docs/CONSOLE_GUIDE.md`.

## DoD
- Контекст всегда виден, selector только при выборе.
- При `selection_required`/`branch_selection_required` UI блокирует контент.
- Меню отражает роль (`agent.role`).
- API запросы уходят с `X-Client-Id`/`X-Branch-Id` после выбора.

## Checks
- `npm --prefix console-web run lint` (если зависимости установлены)

## Evidence
- Скриншоты UI + краткое описание поведения (manual) + запись в `STATE.md`.

## Rollback
- Откатить UI‑изменения и вернуть текущую шапку.

## No-go
- Изменения API контрактов или backend поведения.

## Риски/блокеры
- Отсутствие валидных данных `/console/v1/me` на стенде.

## Branch / Worktree / Merge
- Branch: `feat/control-plane-phase1-ui`
- Worktree: `/home/zhan/worktrees/control-plane-phase1-ui`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
