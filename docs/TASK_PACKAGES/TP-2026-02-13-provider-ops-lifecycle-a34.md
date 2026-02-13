# TP-2026-02-13-provider-ops-lifecycle-a34

- Название/цель: Закрыть операционные риски Console Plane для ручного ChatFlow lifecycle: (1) убрать backend-bypass через go-live waiver, (2) вынести provider-binding lifecycle в Integrations API/UI, (3) расширить onboarding autopilot входом `provider_binding`.
- Canon refs:
  - `AGENTS.md`
  - `STATE.md` NOW/GAP: onboarding/provisioning automation + Console-first support
  - `SPECS/SYSTEM_REFERENCE.md`
  - `STRATEGY/REQUIREMENTS.md`

## Invariant
- Не ослаблять existing GO/NO-GO/scorecard gating.
- Не ломать multi-tenant/RBAC доступы.
- Не ломать existing webhook secret contract (`instance_id -> webhook_secret`).

## Scope
- Добавить scorecard enforcement в `go-live/waive` backend path.
- Расширить integrations статус полями provider lifecycle (`provider_binding`, expiry/rebind signals).
- Добавить `provider_binding` в autopilot request/flow и сохранить в onboarding contract.
- Обновить OpenAPI + generated web types + целевые тесты.

## Out of scope
- ChatFlow API automation/polling.
- Фоновый scheduler/cron мониторинга billing expiry.
- Изменение runtime webhook business logic вне указанных точек.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/services/onboarding_contract_service.py` (если потребуется merge/serialization адаптация)
- `truffles-api/tests/test_console_access_admin_pr2.py`
- `truffles-api/tests/test_console_integrations_registry.py`
- `truffles-api/tests/test_console_admin_provisioning.py` (при необходимости)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/app/integrations/page.tsx`
- `console-web/src/components/ProvisioningWizard.tsx` (autopilot form binding fields)
- `console-web/src/types/api.generated.ts`

## Plan
1. Enforce scorecard in `go-live/waive` (fail-closed like approve/autopilot).
2. Add provider-binding lifecycle fields into integrations backend response + serializer.
3. Add UI rendering for new integrations lifecycle fields and statuses.
4. Extend autopilot request schema/API/UI for `provider_binding` and persist into onboarding contract.
5. Update OpenAPI and regenerate frontend API types.
6. Add/adjust backend tests (waive gate, integrations fields, autopilot binding write).

## DoD
- `go-live/waive` returns `GO_LIVE_GATE_REQUIRED` on scorecard fail.
- Integrations page shows provider-binding lifecycle data (`provider`, `webhook_status`, `paid_until`, derived expiry state/rebind marker).
- Autopilot can accept and persist `provider_binding` without manual post-patch.
- Targeted tests green; OpenAPI/types in sync.

## Checks
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py`
- `pytest -q truffles-api/tests/test_console_integrations_registry.py`
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py`
- `npm --prefix console-web run generate:api`
- `npm --prefix console-web run lint -- --file src/app/integrations/page.tsx --file src/components/ProvisioningWizard.tsx`

## Evidence
- `git diff --stat`
- Команды checks + результаты
- Новые/обновлённые тесты на waiver hard-stop + integrations lifecycle + autopilot provider_binding
- Session log + index update

## Rollback
- `git revert SHA`
- Если нужен быстрый rollback поведения: убрать новые checks/fields в `go-live/waive` и integrations serializer отдельным revert-коммитом.

## No-go
- Не добавлять role-based обход scorecard кроме явного архитектурного решения.
- Не писать fake lifecycle статусы без contract source.
- Не менять unrelated booking/runtime flows.

## Branch / Worktree
- Branch: `feat/2026-02-13-provider-ops-lifecycle-a34`
- Worktree: `/home/zhan/worktrees/2026-02-13-provider-ops-lifecycle-a34`
- Base ref: `origin/main`
- Merge policy: merge only (no rebase)
- Cleanup: Brain/Top Architect после merge

## Риски/блокеры
- Возможен UI/contract дрейф, если не обновить generated types после OpenAPI.
- Расширение Integrations response требует аккуратной backward compatibility полей/labels.
