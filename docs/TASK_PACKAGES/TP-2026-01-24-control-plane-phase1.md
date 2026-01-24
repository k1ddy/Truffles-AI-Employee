# TP-2026-01-24 — Control Plane Phase 1 (Layout + Context + Roles)

- **Название/цель:** внедрить Phase 1 UX каркас: sidebar + top context bar, role‑based navigation, и fail‑closed tenant selection в Console UI.
- **Canon refs:** `SPECS/CONTROL_PLANE.md`, `SPECS/MULTI_TENANT.md`, `SPECS/ESCALATION.md`, `docs/CONSOLE_GUIDE.md`, `STRATEGY/REQUIREMENTS.md`, `STATE.md`.

## Invariant
- Никаких изменений в backend API/контрактах.
- Fail‑closed при отсутствии `X-Client-Id`/`X-Branch-Id`.
- Никаких “догадок” о tenant‑контексте.

## Scope
- Новая оболочка Layout (sidebar + top context bar).
- Ролевая навигация (owner/admin/manager/support).
- Tenant selection UI (client/branch) с хранением в localStorage.
- Обработка `selection_required`/`branch_selection_required` из `/console/v1/me`.

## Out of scope
- Provisioning, Knowledge Studio, Team, Integrations UI.
- Любые изменения backend/DB.
- 3‑pane Inbox (Phase 5).

## Touch-list
- `console-web/src/app/layout.tsx`
- `console-web/src/app/page.tsx`
- `console-web/src/app/globals.css`
- `console-web/src/components/*` (новые: Sidebar, ContextBar, TenantSelector)
- `console-web/src/lib/api.ts`
- `console-web/src/lib/api-client.ts`
- `docs/CONSOLE_GUIDE.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-control-plane-phase1.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Добавить общий Layout (sidebar + header + content slot) для всех страниц.
2) Реализовать Context Bar: отображение Company/Client/Branch + селекторы при 2+.
3) Подключить `/console/v1/me` и локальное хранение выбранных client/branch.
4) Реализовать role‑based menu (owner/admin/manager/support).
5) Обновить docs/CONSOLE_GUIDE.md (контекст‑бар и правила selection).

## DoD
- Контекст всегда виден, selector только при выборе.
- При `selection_required`/`branch_selection_required` UI блокирует контент и требует выбор.
- Меню отражает роль (`agent.role`).
- Вызовы API уходят с `X-Client-Id`/`X-Branch-Id` после выбора.

## Checks
- `npm --prefix console-web run lint` (если зависимости установлены)

## Evidence
- Скриншоты UI + описание поведения (manual) + запись в `STATE.md`.

## Rollback
- Откатить UI‑изменения и вернуть текущую шапку.

## No-go
- Изменения API контрактов или backend поведения.

## Риски/блокеры
- Отсутствие данных `/console/v1/me` на стенде; fallback‑режимы должны быть аккуратны.

## Branch / Worktree / Merge
- Branch: `docs/control-plane-2026-01-24`
- Worktree: `/home/zhan/worktrees/control-plane-docs`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
