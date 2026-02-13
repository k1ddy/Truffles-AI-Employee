# TP-2026-02-13-company-workspace-ux-a36

- Название/цель: Сделать Console Plane реально управляемым для platform admin: единый Company Workspace, typed UX для provider ops (без prompt), и мастер быстрого создания company/client/branch.
- Canon refs:
  - `AGENTS.md`
  - `STATE.md` NOW/GAP: Console onboarding/support + provider lifecycle operational control
  - `SPECS/SYSTEM_REFERENCE.md`
  - `STRATEGY/REQUIREMENTS.md`
  - `TECH.md`

## Invariant
- Не ослаблять RBAC (`platform_admin` для tenants/integrations write-контуров).
- Не ломать provider binding hard-stop / onboarding scorecard gates.
- Не ломать `instance_id -> webhook_secret` контракт.
- Не добавлять mutate-операции provider ops без confirmation.

## Scope
- Добавить dedicated `Company Workspace` страницу в console-web с фокусом на platform admin ops.
- Перевести integrations provider actions с `window.prompt` на typed modal/forms UX.
- Добавить в tenants явный мастер создания company/client/branch с валидацией и безопасным контекстным переключением.
- Сохранить/использовать существующие backend endpoints; при необходимости расширить только UX-safe API bindings.
- Обновить/добавить frontend tests (где применимо) и прогнать обязательные проверки.

## Out of scope
- ChatFlow-side provisioning automation (создание instance/webhook на стороне ChatFlow API).
- Глубокий redesign всей Console.
- Изменения runtime LLM/booking logic.

## Touch-list
- `console-web/src/app/integrations/page.tsx`
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/components/ConsoleShell.tsx`
- `console-web/src/app/company-workspace/page.tsx` (new)
- `console-web/src/lib/api-client.ts` (если потребуется)
- `console-web/src/types/api.generated.ts` (если потребуется)
- `truffles-api/tests/test_console_*.py` (только если потребуется backend contract touch)
- `docs/SESSIONS/SESSION-2026-02-13-company-workspace-ux-a36.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Session bootstrap и факт-проверка текущего UX кода.
2. Реализовать typed provider ops action modal + confirmation flow в Integrations.
3. Реализовать master create flow (company/client/branch) в Tenants.
4. Добавить Company Workspace page и navigation entry.
5. Прогнать проверки и собрать evidence.

## DoD
- В Integrations нет `window.prompt` для provider ops execute-потока.
- Platform admin может запускать provider actions через форму с валидируемыми полями.
- В Tenants есть явный create workflow для company/client/branch.
- Есть отдельный Company Workspace экран с понятным action-oriented UX.
- Frontend lint/type checks и целевые backend/frontend проверки зелёные.

## Checks
- `pytest -q truffles-api/tests/test_console_integrations_registry.py`
- `pytest -q truffles-api/tests/test_console_*.py`
- `python3 truffles-api/scripts/generate_openapi.py --check` (если контракты тронуты)
- `npm --prefix console-web run generate:api` (если OpenAPI менялся)
- `npm --prefix console-web run lint -- --file src/app/integrations/page.tsx --file src/app/tenants/page.tsx --file src/app/company-workspace/page.tsx --file src/components/ConsoleShell.tsx`

## Evidence
- `git status -sb`
- `git diff --stat`
- outputs check-команд
- session log + index update

## Rollback
- `git revert COMMIT_SHA`

## No-go
- Не внедрять временные bypass UX/security checks.
- Не удалять existing gating/confirmation mechanisms.
- Не делать broad refactor вне Touch-list.

## Branch / Worktree
- Branch: `feat/2026-02-13-company-workspace-ux-a36`
- Worktree: `/home/zhan/worktrees/2026-02-13-company-workspace-ux-a36`
- Base ref: `origin/main`
- Merge policy: merge only (no rebase)
- Cleanup: Brain/Top Architect после merge

## Риски/блокеры
- Большой frontend файл (`tenants/page.tsx`) — риск регрессии UX/state.
- Нужен аккуратный state management для modal/form flows без дублирования логики.
- Верификация удобства требует согласованности между Tenants/Integrations/Workspace.
