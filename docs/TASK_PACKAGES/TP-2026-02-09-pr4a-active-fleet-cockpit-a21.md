# TP-2026-02-09 PR-4A Active Fleet Cockpit (a21)

## Название/цель
Добавить в Console Platform Admin-экран "Risk & Attention" для уже активных клиентов: единый список клиентов с операционными рисками (integration drift/stale inbound/outbox failures/pending handovers) и рекомендуемыми действиями.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: Enterprise fleet PR-1/PR-2/PR-3 merged; active fleet операционный cockpit не закрыт)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/CONTROL_PLANE.md`
- `docs/REPORTS/2026-02-08-enterprise-fleet-program.md` (PR-4 Active Fleet Ops)

## Invariant
- Tenant isolation и RBAC не ослабляются (endpoint только для `platform_admin`).
- Не меняем runtime webhook/decision/outbox pipeline и не трогаем `_legacy.py`.
- Не ломаем существующие `/admin/clients`, `/admin/integrations`, `/ops/jobs` контуры.

## Scope
- Backend:
  - новый read endpoint `GET /console/v1/admin/fleet/attention`.
  - агрегирование риск-сигналов по активным клиентам на основе текущих таблиц/сервисов:
    - branch integration status (error/warn + stale inbound),
    - outbox `FAILED` за 24ч,
    - pending/active handovers,
    - текущий fleet service_state/lifecycle context.
  - score/level + reasons + suggested_actions в ответе API.
- Frontend:
  - добавить в `Tenants` блок "Risk & Attention" с summary и top-list клиентов (по score).
- Contracts/tests:
  - обновить OpenAPI + generated API types.
  - добавить unit tests на backend логику и endpoint поведение.

## Out of scope
- Bulk execute/canary workflows (PR-4B).
- Draft->validate->publish->rollback для данных клиента (PR-4C).
- Любые DB migrations для новых таблиц.
- Изменения legacy `/admin/*`.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_fleet_attention.py` (new)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/app/tenants/page.tsx`
- `console-web/src/types/api.generated.ts`

## Plan
1. Добавить backend schemas + helper aggregation logic для fleet attention.
2. Реализовать `GET /admin/fleet/attention` с platform_admin guard и фильтрами (`limit`, `stale_after_minutes`, `include_low`).
3. Покрыть backend unit tests (score/reasons + filtering + permission guard).
4. Обновить OpenAPI и regenerate frontend API types.
5. Добавить UI блок в `Tenants` (summary + top risk clients + reasons/actions).
6. Прогнать checks, собрать evidence и обновить session log.

## DoD
- Platform Admin видит в Console список активных клиентов с операционными рисками и приоритетом.
- Ответ endpoint содержит: summary, client-level score/level, причины и suggested actions.
- UI отображает этот блок и данные совпадают с API.
- OpenAPI/types синхронизированы.
- Есть backend тесты для нового контура.

## Checks
- `PYTEST_ARGS='/app/tests/test_console_fleet_attention.py /app/tests/test_console_tenants_list.py /app/tests/test_console_integrations_registry.py' scripts/test_api_container.sh`
- `python3 scripts/generate_openapi.py --check`
- `cd console-web && npm run generate:api`
- `cd console-web && npm run lint`
- `scripts/session_check.sh`

## Evidence
- `git status -sb`
- `git diff --stat`
- Логи checks (pytest/openapi/lint)
- Ссылка на session log `docs/SESSIONS/SESSION-2026-02-09-pr4a-active-fleet-cockpit-a21.md`
- (для merge) CI run URL

## Rollback
- Revert commit с `fleet/attention` endpoint + UI block + contract/type updates.
- Временно использовать существующие `Tenants + Integrations + Ops` экраны без cockpit.

## No-go
- Не добавлять SRE actions (deploy/restart/migrations) в Console.
- Не вводить cross-tenant обходы или ослабление RBAC.
- Не добавлять новые таблицы/миграции без отдельного TP.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-09-pr4a-active-fleet-cockpit-a21`
- Worktree: `/home/zhan/worktrees/2026-02-09-pr4a-active-fleet-cockpit-a21`
- Base ref: `origin/main`
- Merge policy: merge commit via PR (no rebase)
- Cleanup: после merge удалить worktree + branch

## Риски/блокеры
- Риск ложных тревог (noise):
  - Митигация: явные thresholds + score model + `include_low` фильтр.
- Риск тяжелых запросов на большой fleet:
  - Митигация: агрегирование в батчах SQL, limit/top list, без N+1 на client loop.
- Риск несоответствия UI и API контрактов:
  - Митигация: openapi/type generation + backend tests.
