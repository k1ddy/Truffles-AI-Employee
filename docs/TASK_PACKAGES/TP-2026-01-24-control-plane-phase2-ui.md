# TP-2026-01-24 — Control Plane Phase 2 UI (Provisioning Wizard)

- **Название/цель:** реализовать UI‑wizard Provisioning в Console (flow + gating + content) поверх admin API.
- **Canon refs:** `SPECS/CONTROL_PLANE.md`, `SPECS/MULTI_TENANT.md`, `docs/CONSOLE_GUIDE.md`,
  `STRATEGY/REQUIREMENTS.md`, `STATE.md`, `contracts/console_api/openapi.v1.yaml`.

## Invariant
- Никаких изменений backend API/контрактов.
- Fail‑closed: без tenant‑контекста никаких действий.
- RBAC: provisioning write только owner/admin.

## Scope
- Новый UI‑flow Provisioning Wizard (steps 1–7 из `SPECS/CONTROL_PLANE.md`).
- Создание Company/Client/Branch/Agent через `/console/v1/admin/*`.
- Gating по capability‑зависимым полям (instance_id, telegram_chat_id, knowledge_tag, working_hours).
- Контент шагов: inputs, helper‑тексты, состояния ошибок/blocked.

## Out of scope
- Knowledge Studio UI (Phase 3).
- Team/Calendar UI (Phase 4).
- Любые изменения backend/DB.

## Touch-list
- `console-web/src/app/*`
- `console-web/src/components/*`
- `console-web/src/lib/*`
- `console-web/src/types/api.generated.ts`
- `docs/CONSOLE_GUIDE.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-control-plane-phase2-ui.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Описать UX flow и шаги wizard (branch draft → integrations → team → telegram → knowledge → booking → go/no‑go).
2) Реализовать базовый layout + stepper + формы по шагам.
3) Подключить admin API (create company/client/branch/agent, update branch).
4) Реализовать gating: блокировать переход при отсутствии required‑полей для активных capabilities.
5) Обновить `docs/CONSOLE_GUIDE.md` и `STATE.md` с evidence.

## DoD
- Wizard доступен только owner/admin.
- Create Branch (draft) работает без `instance_id`; activation требует `instance_id`.
- Шаги показывают статус и требуемые поля; go/no‑go блокирует publish при missing‑полях.
- Ошибки API отображаются в UI, без silent‑fail.

## Checks
- `npm --prefix console-web run lint` (если зависимости установлены)

## Evidence
- Скриншоты UI + краткое описание поведения (manual) + запись в `STATE.md`.

## Rollback
- Откатить UI‑изменения через обратный merge.

## No-go
- Изменения backend/DB.

## Риски/блокеры
- Нет достаточных данных/доступов для реального provisioning на стенде.

## Branch / Worktree / Merge
- Branch: `feat/control-plane-phase2-ui`
- Worktree: `/home/zhan/worktrees/control-plane-phase2-ui`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
