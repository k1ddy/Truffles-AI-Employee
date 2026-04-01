# TP-2026-01-24 — Control Plane Phase 2 (Provisioning + Capabilities, plan)

- **Название/цель:** зафиксировать Phase 2 UI contract для Provisioning + Capabilities и подготовить план реализации.
- **Canon refs:** `SPECS/CONTROL_PLANE.md`, `SPECS/MULTI_TENANT.md`, `docs/CONSOLE_GUIDE.md`, `docs/IMPERIUM_DECISIONS.yaml`,
  `STRATEGY/REQUIREMENTS.md`, `STATE.md`.

## Invariant
- Не менять backend/DB и существующие API контракты.
- Fail‑closed по tenant‑контексту сохраняется.
- Никаких новых продуктовых обещаний вне канона.

## Scope
- Добавить Phase 2 UI contract в `docs/CONSOLE_GUIDE.md`.
- Зафиксировать план работ для Provisioning Wizard и Capabilities (UI + API + data).
- Обновить `STRUCTURE.md` и `STATE.md`.

## Out of scope
- Реализация UI/BE/DB для Provisioning/Capabilities.
- Knowledge Studio (Phase 3), Team/Calendar, Inbox UX.

## Touch-list
- `docs/CONSOLE_GUIDE.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-control-plane-phase2.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Добавить Phase 2 UI contract в Console Guide.
2) Зафиксировать границы API и данных для Provisioning + Capabilities.
3) Обновить список активных Task Packages.
4) Отразить PLAN в `STATE.md`.

## DoD
- Phase 2 UI contract добавлен в `docs/CONSOLE_GUIDE.md`.
- Task Package содержит scope/DoD/checks/evidence/risks.
- `STRUCTURE.md` содержит новый Task Package в active list.
- `STATE.md` отражает PLAN без claims о реализации.

## Checks
- `rg -n "Phase 2 UI contract" docs/CONSOLE_GUIDE.md`

## Evidence
- Commit hash + ссылки на изменённые документы.

## Rollback
- Откатить doc‑правки.

## No-go
- Любые изменения в backend, DB или UI‑коде.

## Риски/блокеры
- Не определён полный набор обязательных данных филиала (Go/No‑Go gate).
- API/DB модель provisioning + capabilities пока не реализована.

## Branch / Worktree / Merge
- Branch: `docs/control-plane-phase2-2026-01-24`
- Worktree: `/home/zhan/worktrees/control-plane-phase2-docs`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
