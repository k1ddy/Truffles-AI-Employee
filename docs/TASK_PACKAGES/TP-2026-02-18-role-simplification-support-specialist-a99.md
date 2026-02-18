# TP-2026-02-18-role-simplification-support-specialist-a99

- Название/цель: Упростить ролевую модель Console для филиалов: исключить `support` и `specialist` из рабочего контура, чтобы остались понятные роли для бизнеса (`owner/admin/manager/viewer`) без лишних сценариев.
- Canon refs: `AGENTS.md`, `STATE.md` NOW/GAP (контекст Wave 1 UX gap), `STRUCTURE.md`, `STRATEGY/REQUIREMENTS.md`, `SPECS/CONTROL_PLANE.md`, `SPECS/SYSTEM_REFERENCE.md`.
- CA_ID: N/A.

## Invariant
- Existing tenant data isolation/RBAC safety не ухудшаются.
- Назначение и редактирование командных ролей остаются audit-friendly и branch-scoped.
- Calendar/booking доменная сущность `specialist` (как мастер в записи) не затрагивается.

## Scope
- Запретить создание/назначение ролей `support` и `specialist` в Console API для tenant team management.
- Убрать `support` и `specialist` из UI-форм role selection (Provisioning/Team-related flows).
- Синхронизировать текст ошибок/валидации и контрактные тесты под новый allowlist ролей.

## Out of scope
- Полная миграция/удаление legacy ролей из БД.
- Изменение platform-level ролей (`platform_admin`).
- Переработка календарной бизнес-логики записи/визитов.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/console_auth.py`
- `truffles-api/app/schemas/console.py` (только если нужно для request allowlist)
- `truffles-api/tests/test_console_rbac.py`
- `truffles-api/tests/test_console_team_management.py`
- `truffles-api/tests/test_console_openapi_contract.py` (или смежные contract tests)
- `contracts/console_api/openapi.v1.yaml` (если меняется request enum)
- `console-web/src/components/ProvisioningWizard.tsx`
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/src/app/team/page.tsx` (если role labels/options там дублируются)

## Plan
1. Зафиксировать серверный allowlist assignable ролей для tenant API и закрыть `support/specialist` в create/update paths.
2. Обновить frontend role options/labels и убрать UI-пути, где пользователь может выбрать deprecated роли.
3. Обновить OpenAPI/types/tests под новый контракт и прогнать targeted checks.

## DoD
- Через Console нельзя создать или назначить `support/specialist` для tenant users.
- В UI нет выбора `support/specialist` в onboarding/team role controls.
- Тесты на team management/RBAC покрывают отклонение deprecated ролей и проходят.

## Checks
- `pytest -q truffles-api/tests/test_console_team_management.py`
- `pytest -q truffles-api/tests/test_console_rbac.py`
- `pytest -q truffles-api/tests/test_console_openapi_contract.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run lint -- --file src/components/ProvisioningWizard.tsx --file src/lib/api-client.ts --file src/components/ConsoleShell.tsx`
- `npx --prefix console-web tsc --noEmit --incremental false -p console-web/tsconfig.json`

## Evidence
- PR diff по touch-list.
- Outputs pytest/openapi/lint/tsc.
- Скрин/описание UI формы с упрощённым набором ролей.

## Rollback
- Revert PR commit(s) целиком.
- Временный rollback-флаг не требуется.

## No-go
- Не добавлять новые роли/иерархии.
- Не смешивать это изменение с маркетингом/campaign функционалом.
- Не менять booking pipeline и visit statuses в этой задаче.

## Риски/блокеры
- Legacy аккаунты с ролями `support/specialist` могут существовать; нужно сохранить безопасное поведение для чтения, но запретить новые назначения.
- Возможные пересечения с параллельными изменениями `console.py` и OpenAPI.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-18-role-simplification-support-specialist-a99`
- Worktree: `/home/zhan/worktrees/2026-02-18-role-simplification-support-specialist-a99`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: Brain/Top Architect после merge
