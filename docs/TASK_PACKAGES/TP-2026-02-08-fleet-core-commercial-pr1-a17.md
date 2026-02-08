# TP-2026-02-08 Fleet Core + Commercial State (PR-1, a17)

## Название/цель
Реализовать первый кодовый шаг enterprise программы: единый Fleet Registry с lifecycle/commercial состоянием и KPI-baseline для Platform Admin, включая API + базовый UI в Tenants.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/MULTI_TENANT.md`
- `docs/PROCESSES.md`
- `docs/REPORTS/2026-02-08-enterprise-fleet-program.md`

## Invariant
- Fail-closed tenancy и RBAC не ослабляются.
- Lifecycle write (`archive/restore`) не ломается.
- Legacy `/admin/health|version` поведение не трогаем.
- Никаких изменений webhook/runtime decision logic в этом PR.

## Scope
- Backend: добавить fleet registry endpoint для platform_admin (list + summary KPI), с фильтрами поиска и lifecycle/commercial state.
- Backend: вычисляемые поля на item:
  - `lifecycle_state` (derived + explicit override),
  - `commercial_state` / `payment_status`,
  - `service_state` (ok/degraded/attention),
  - `owner_name`, `next_action`, branch counters.
- Frontend: добавить в Tenants базовый Fleet section (summary + list) и фильтры.
- API contract: обновить OpenAPI и generated frontend types.
- Tests: backend unit tests для fleet registry derivation/filtering.

## Out of scope
- Membership CRUD/re-scope (PR-2).
- Bulk ops/jobs (PR-4).
- Legacy consumer migration/cutover (PR-5).
- Полная новая коммерческая биллинг-модель (invoice/subscription tables).

## Touch-list
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_tenants_list.py`
- `contracts/console_api/openapi.v1.yaml`
- `truffles-api/scripts/generate_openapi.py` (invoke only)
- `console-web/src/lib/api-client.ts`
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/types/api.generated.ts`
- `docs/SESSIONS/SESSION-2026-02-08-fleet-core-commercial-pr1-a17.md`

## Plan
1. Добавить схемы Fleet summary/item/list в console schemas.
2. Добавить backend fleet endpoint + derived-state helpers + filters.
3. Добавить backend unit tests на derivation/filter/search.
4. Реген OpenAPI и frontend API types.
5. Добавить Fleet section в `tenants/page.tsx` с summary/list/filters.
6. Прогнать checks и собрать evidence.

## DoD
- Platform Admin может открыть fleet-реестр и увидеть lifecycle/commercial/service состояние клиентов в одном списке.
- Есть summary KPI baseline по fleet (минимум: total, active, onboarding, archived, degraded, payment_pending, payment_confirmed).
- Фильтры lifecycle/payment/service и поиск работают.
- OpenAPI + generated types синхронизированы.
- Есть backend tests для новых derivation rules.

## Checks
- `scripts/session_check.sh`
- `pytest -q truffles-api/tests/test_console_tenants_list.py truffles-api/tests/test_console_integrations_registry.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `cd console-web && npx openapi-typescript ../contracts/console_api/openapi.v1.yaml -o src/types/api.generated.ts`
- `cd console-web && npm run lint`
- `cd console-web && npm run build`

## Evidence
- `git status -sb`
- `git diff --stat`
- test/lint command outputs
- ссылку на PR

## Rollback
- Revert commit PR-1 целиком.

## No-go
- Не внедрять новый write-path lifecycle вне уже утвержденных archive/restore.
- Не менять контракт selection_required и tenant headers.
- Не добавлять зависимость от ручного SQL для отображения fleet registry.

## Риски/блокеры
- Риск: derived lifecycle неточно отражает business stage.
  - Митигация: explicit override через `company.billing_info.lifecycle_state` + прозрачный `next_action`.
- Риск: тяжелый SQL list.
  - Митигация: лимит + cursor + агрегаты без N+1.
- Риск: UI перегрузится данными.
  - Митигация: компактный summary + paged list + фильтры.
