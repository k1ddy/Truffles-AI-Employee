# TP-2026-02-13-company-control-plane-v3-a37

## Название/цель
Сделать реально управляемый Console Plane для компаний: контекстно-скоупленные Integrations, единый WhatsApp Control Panel, линейный hard-stop onboarding wizard без ручных обходов.

## Canon refs
- AGENTS.md
- STATE.md (NOW: post-merge UX still fragmented; context flow not operationally closed)
- STRATEGY/REQUIREMENTS.md
- SPECS/CONTROL_PLANE.md
- SPECS/SYSTEM_REFERENCE.md

## Invariant
- Tenant isolation и access checks не ослабляются.
- Provider/renewal/rebind операции остаются confirmation-gated.
- Console остается source-of-truth для onboarding/provider operations.

## Scope
1. Backend: `/admin/integrations` принимает и применяет scope-фильтры `company_id/client_id/branch_id` с fail-closed проверками доступа.
2. Contract + generated API types: добавить новые query параметры в OpenAPI и синхронизировать типы.
3. Frontend Integrations: явные фильтры контекста + синхронизация с текущим console context.
4. Frontend Company Workspace: единый WhatsApp Control Panel для выбранной компании/клиента/филиала.
5. Frontend Onboarding: линейный hard-stop workflow (Create -> WA -> Verify -> Renewal -> Go-live) в виде операционного run-path.
6. Tests: backend unit/integration tests + frontend lint/type checks + targeted e2e updates where feasible.

## Out of scope
- Интеграция с внешним ChatFlow API (автоматическая регистрация/продление на стороне ChatFlow).
- Полный redesign всей визуальной системы Console.
- Изменение роли/прав beyond current RBAC matrix.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_integrations_registry.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `console-web/src/app/integrations/page.tsx`
- `console-web/src/app/company-workspace/page.tsx`
- `console-web/src/app/tenants/page.tsx` (only if needed for route handoff)
- `console-web/e2e/*` (targeted updates if required)
- `docs/SESSIONS/SESSION-2026-02-13-company-control-plane-v3-a37.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Start governed session/worktree and baseline checks.
2. Add backend scoped integrations filters + validation + tests.
3. Update OpenAPI + generate frontend API types.
4. Implement Integrations context filters UI and wiring.
5. Implement Company Workspace WhatsApp Control Panel.
6. Implement linear hard-stop onboarding workflow UI.
7. Run checks, capture evidence, update session log, prepare PR.

## DoD
- Platform admin может ограничить Integrations до company/client/branch и видеть только scoped данные.
- Company Workspace содержит единый WhatsApp Control Panel с обязательными lifecycle действиями в одном потоке.
- Onboarding workflow отображает hard-stop шаги и блокирует go-live без обязательных шагов.
- Нет prompt-based действий в критических provider flows.
- Тесты/линт/контракты для измененного контура проходят.

## Checks
- `pytest -q truffles-api/tests/test_console_integrations_registry.py`
- `pytest -q truffles-api/tests/test_console_*.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run generate:api`
- `npm --prefix console-web run lint -- --file src/app/integrations/page.tsx --file src/app/company-workspace/page.tsx --file src/lib/api-client.ts`
- Optional targeted e2e smoke if required by changed selectors/routes.

## Evidence
- PR link + CI links
- test outputs summary
- affected file refs
- session log update in `docs/SESSIONS/SESSION-2026-02-13-company-control-plane-v3-a37.md`
- `STATE.md` update left to Brain/Top Architect per process

## Rollback
- Revert PR commit(s) and redeploy previous main image.
- Disable new UI path by routing users back to existing `/tenants` and `/integrations` defaults if incident occurs.

## No-go
- Не ослаблять tenant scope/access checks.
- Не добавлять manual DB workaround steps в UX flow.
- Не обходить confirmation guard для execute операций.
- Не трогать unrelated branches/sessions.

## Риски/блокеры
- Existing large frontend files (`tenants`, `ProvisioningWizard`) are complex and regression-prone.
- OpenAPI/type generation drift can break frontend build if contract not synchronized.
- E2E coverage may lag behind new UX flow; must add/adjust minimal critical checks.

## Branch/Worktree
- Branch: `feat/2026-02-13-company-control-plane-v3-a37`
- Worktree path: `/home/zhan/worktrees/2026-02-13-company-control-plane-v3-a37`
- Base ref: `origin/main`
- Merge policy: regular merge (no rebase)
- Cleanup: by Brain/Top Architect after merge
