# TP-2026-01-24 — Control Plane Phase 2A (Capabilities model + admin API)

- **Название/цель:** реализовать модель capabilities (DB + контракт) и admin API для чтения/обновления capabilities.
- **Canon refs:** `SPECS/CONTROL_PLANE.md`, `docs/IMPERIUM_DECISIONS.yaml` (DEC‑015),
  `SPECS/MULTI_TENANT.md`, `docs/CONSOLE_GUIDE.md`, `STRATEGY/REQUIREMENTS.md`, `STATE.md`.

## Invariant
- Никаких изменений в существующих endpoint‑контрактах и поведении core.
- Fail‑closed по tenant‑контексту сохраняется.
- Никаких новых продуктовых обещаний вне канона.

## Scope
- DB таблица `client_capabilities` + индексы.
- Контракт `contracts/capabilities/capabilities.v1.jsonschema`.
- Pydantic‑валидация payload и merge client + branch overrides.
- Console API: `GET/PATCH /console/v1/admin/capabilities`.
- Обновление OpenAPI и generated types.

## Out of scope
- Provisioning Wizard и создание компаний/клиентов/филиалов.
- UI экраны и навигация Phase 2.
- Knowledge Studio (Phase 3).

## Touch-list
- `truffles-api/migrations/012_add_client_capabilities.sql`
- `truffles-api/app/models/client_capability.py`
- `truffles-api/app/models/__init__.py`
- `truffles-api/app/services/capabilities_service.py`
- `truffles-api/app/schemas/capabilities.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `contracts/capabilities/capabilities.v1.jsonschema`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/types/api.generated.ts`
- `SPECS/MULTI_TENANT.md`
- `docs/CONSOLE_GUIDE.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Добавить контракт capabilities (jsonschema) и модель таблицы.
2) Реализовать валидатор + merge logic (client + branch overrides).
3) Добавить `GET/PATCH /console/v1/admin/capabilities` с audit.
4) Обновить OpenAPI и `console-web` generated types.
5) Синхронизировать канон‑доки (Multi‑Tenant/Console Guide) и `STRUCTURE`/`STATE`.

## DoD
- Таблица `client_capabilities` создана миграцией и покрыта индексами.
- API возвращает effective capabilities и принимает PATCH с валидацией.
- Контракт capabilities зафиксирован в `contracts/`.
- OpenAPI и generated types обновлены.
- Док‑синк выполнен; `STATE.md` содержит PLAN/FACT с evidence.

## Checks
- `python3 -m compileall truffles-api/app/services truffles-api/app/schemas truffles-api/app/routers/console.py`
- `npm --prefix console-web run generate:api`

## Evidence
- CI run URL + commit hash + ссылки на изменённые доки.

## Rollback
- Откатить миграцию и связанные API/док‑изменения.

## No-go
- Изменения в core‑пайплайне, knowledge‑packs, или runtime данных.

## Риски/блокеры
- Нет отдельной роли Platform Admin → временно используем текущий RBAC (support/owner/admin).
- Требуется согласование обязательных полей branch для Go/No‑Go (вне scope).

## Branch / Worktree / Merge
- Branch: `feat/control-plane-phase2-capabilities`
- Worktree: `/home/zhan/worktrees/control-plane-phase2-capabilities`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
