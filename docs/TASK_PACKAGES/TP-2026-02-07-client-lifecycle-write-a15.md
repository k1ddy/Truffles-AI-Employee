# TP-2026-02-07 Client Lifecycle Write Semantics (a15)

## Название/цель
Ввести явные lifecycle actions для клиентов (`archive/restore`) в Console Admin, убрать свободное изменение client status через patch-form и обеспечить безопасный архив через prechecks + audit reason.

## Canon refs
- `AGENTS.md`
- `STATE.md` (GAP: lifecycle write semantics / split admin surface)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`
- `TECH.md`

## Invariant
- Lifecycle клиента меняется только через явные actions, а не через свободный текст `status`.
- Архивирование не допускается при активных зависимостях (агенты/мембершипы/филиалы).
- Все lifecycle действия пишут audit trail с reason.
- Read semantics (`active/archived/all`) и `/me` active-by-default поведение не деградируют.

## Scope
- Backend (`/console/v1/admin/*`):
  - добавить `POST /admin/clients/{client_id}/archive`
  - добавить `POST /admin/clients/{client_id}/restore`
  - ввести request body с обязательным `reason`
  - prechecks для archive (active agents/memberships/branches)
  - side-effects: `status`, `deleted_at`, `updated_at`
  - audit events для success/block/fail states
  - запрет lifecycle-изменений через `PATCH /admin/clients/{client_id}`.
- Frontend (`Tenants`):
  - убрать free-text поле `status` из client editor
  - добавить Archive/Restore actions c reason+confirmation
  - проброс новых API вызовов.

## Out of scope
- Полный перенос legacy `/admin/*` в `/console/v1/*`.
- Массовый рефактор auth/RBAC/memberships.
- Integrations registry/drift guard.
- SRE surface (deploy/restart/migrations orchestration in UI).

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/models/client.py`
- `truffles-api/migrations/025_add_clients_deleted_at.sql` (если нужно для отсутствующей колонки)
- `truffles-api/tests/test_console_admin_provisioning.py`
- `truffles-api/tests/test_console_tenants_list.py` (только если потребуется коррекция ожиданий)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/types/api.generated.ts`

## Plan
1. Добавить backend schemas + endpoints archive/restore и helper prechecks.
2. В `PATCH /admin/clients/{id}` запретить изменение `status`.
3. Добавить/обновить backend tests для archive/restore/precheck/status-guard.
4. Обновить Tenants UI/API client: убрать status input, добавить lifecycle action flow.
5. Обновить OpenAPI и regenerate frontend types.
6. Прогнать target checks (backend + frontend), собрать evidence.

## DoD
- `archive/restore` доступны как отдельные действия и требуют reason.
- Archive блокируется при активных агент/мембершип/branch зависимостях с прозрачной ошибкой.
- `PATCH /admin/clients/{id}` больше не принимает lifecycle-изменения.
- UI не даёт свободно редактировать `status`, а использует явные Archive/Restore.
- OpenAPI/types синхронизированы.
- Есть тесты на lifecycle actions и guard.

## Checks
- `PYTEST_ARGS='/app/tests/test_console_admin_provisioning.py /app/tests/test_console_tenants_list.py' scripts/test_api_container.sh`
- `python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint`

## Evidence
- `git diff --stat` + список измененных файлов.
- Логи target checks (pytest/openapi/lint).
- PR checks summary (core-eval допускается красным по текущему правилу).

## Rollback
- Revert-коммит изменений в router/schema/model/ui/types.
- При необходимости временно вернуть lifecycle-изменения через старый patch путь.

## No-go
- Не менять поведение `/admin/health`/`/admin/version` в legacy.
- Не добавлять orchestration в entrypoints/`_legacy.py`.
- Не делать broad refactor вне P0-B scope.

## Риски/блокеры
- Возможны внешние consumers `PATCH /admin/clients` со `status`; для них будет controlled break (INVALID_PARAM).
- Если `clients.deleted_at` отсутствует в отдельных окружениях, нужен migration apply перед deploy.
