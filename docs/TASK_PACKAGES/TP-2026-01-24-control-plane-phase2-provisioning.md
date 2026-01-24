# TP-2026-01-24 — Control Plane Phase 2B (Provisioning API)

- **Название/цель:** реализовать admin API для создания/обновления Company/Client/Branch/Agent и поддержать поэтапный onboarding.
- **Canon refs:** `SPECS/CONTROL_PLANE.md`, `SPECS/MULTI_TENANT.md`, `docs/CONSOLE_GUIDE.md`,
  `STRATEGY/REQUIREMENTS.md`, `STATE.md`.

## Invariant
- Не менять core‑пайплайн и контракты decision.
- Fail‑closed сохраняется: без `instance_id` активный WA‑канал запрещён.
- Никаких внешних обещаний вне канона.

## Scope
- Admin endpoints: `POST /console/v1/admin/companies|clients|branches|agents`.
- Branch update endpoint: `PATCH /console/v1/admin/branches/{branch_id}`.
- Разрешить draft‑branch: `branches.instance_id` nullable.
- Валидации для поэтапного onboarding (активировать branch без `instance_id` нельзя).
- RBAC: provisioning write только owner/admin; роль manager требует `branch_id`.
- OpenAPI + generated types.

## Out of scope
- UI Provisioning Wizard.
- Knowledge Studio (Phase 3).
- Автогенерация OIDC пользователей/ролей.

## Touch-list
- `truffles-api/migrations/013_allow_branches_instance_id_null.sql`
- `truffles-api/app/models/branch.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/types/api.generated.ts`
- `SPECS/CONTROL_PLANE.md`
- `docs/CONSOLE_GUIDE.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-control-plane-phase2-provisioning.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Добавить миграцию и модель‑синк для draft‑branch (`instance_id` nullable).
2) Реализовать admin endpoints (create + branch update) с RBAC gate.
3) Зафиксировать этапы onboarding и gate‑правила в канон‑доках.
4) Обновить OpenAPI и сгенерировать типы.
5) Обновить `STATE.md` и `STRUCTURE.md`.

## DoD
- Draft‑branch создаётся без `instance_id`, но активировать без него нельзя.
- Endpoint‑набор доступен только owner/admin/support (platform admin).
- OpenAPI и generated types синхронизированы.
- `STATE.md` отражает PLAN/FACT с evidence после CI.

## Checks
- `python3 -m compileall truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/app/models/branch.py`
- `npm --prefix console-web run generate:api`

## Evidence
- CI run URL + commit hash.

## Rollback
- Откатить миграцию и API‑изменения через обратный merge.

## No-go
- Любые изменения в decision‑пайплайне и runtime‑packs.

## Риски/блокеры
- Нужна ручная привязка OIDC subject (вне scope).

## Branch / Worktree / Merge
- Branch: `feat/control-plane-phase2-provisioning`
- Worktree: `/home/zhan/worktrees/control-plane-phase2-provisioning`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
