# TP-2026-02-18-wave2-reminder-control-plane-a88

- Название/цель: Построить Console-first контур управления appointment reminders (очередь, причины провалов, retry), чтобы менеджеры/владельцы видели и контролировали доставку напоминаний.
- Canon refs: `AGENTS.md`, `STATE.md` NOW/GAP, `SPECS/CONTROL_PLANE.md` (Ops/roles/fail-closed), `SPECS/ARCHITECTURE.md` (outbox-first/idempotency/evidence), `TECH.md` (outbox/reminder env contract), `truffles-api/app/services/appointment_reminder_service.py`.
- CA_ID: N/A.

## Invariant
- Напоминания отправляются только через outbox, без прямых provider bypass.
- Consent и tenant-scope остаются обязательными.
- Существующие booking create/cancel/reminder scheduling не регрессируют.

## Scope
- API в Console:
  - список reminder jobs (status/template/run_at/last_error/scope filters),
  - безопасный retry для `FAILED/PENDING` (role-gated, confirmation на массовые операции),
  - диагностические агрегаты (ошибки, возраст, SLA задержки).
- UI:
  - reminder diagnostics panel в `Ops` (или отдельная reminder page в Console),
  - фильтры по client/branch/template/status и action `retry`.
- Observability:
  - четкая связь reminder-job -> outbox row -> delivery status.

## Out of scope
- Маркетинговые кампании и сегментация.
- Изменение текста reminder templates/контентной стратегии.
- Редизайн всего `Ops` раздела.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/services/appointment_reminder_service.py`
- `truffles-api/app/routers/outbox_service.py` (только при необходимости observability hooks)
- `truffles-api/tests/test_reminder_jobs.py`
- `truffles-api/tests/test_console_rbac.py`
- `truffles-api/tests/test_console_owner_business.py` (если затронут owner ops contract)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/components/OpsPage.tsx` (или новый `console-web/src/app/ops/reminders/page.tsx`)
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `docs/CONSOLE_AUDIT/pages/ops.md`
- `STATE.md`

## Plan
1. Зафиксировать API contract reminder management (list/summary/retry) с role/confirmation rules.
2. Реализовать backend list + retry + error taxonomy в console router/service.
3. Добавить UI панель/экран с фильтрами и безопасным retry flow.
4. Обновить OpenAPI/typegen и RBAC проверки.
5. Прогнать deterministic tests и зафиксировать SQL/ops evidence.

## DoD
- Owner/Admin/Platform Admin видят reminder queue и причины провалов по scope.
- Retry из Console работает безопасно и отражается в статусах.
- Есть связная диагностика: reminder job -> outbox -> delivery.
- OpenAPI/types/UI синхронизированы; RBAC fail-closed соблюден.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/appointment_reminder_service.py`
- `pytest -q truffles-api/tests/test_reminder_jobs.py`
- `pytest -q truffles-api/tests/test_console_rbac.py`
- `pytest -q truffles-api/tests/test_console_owner_business.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run generate:api`
- `npm --prefix console-web run lint`
- `npm --prefix console-web run build`

## Evidence
- API contract diff (`contracts/console_api/openapi.v1.yaml`)
- pytest + lint/build outputs
- SQL evidence:
  - reminder jobs by status/error/age,
  - outbox linkage for retried jobs
- UI evidence (ops panel with reminder diagnostics + retry flow)
- `docs/REPORTS/2026-02-18-wave2-reminder-control-plane-a88.md`
- `STATE.md` FACT/GAP update

## Rollback
- Revert PR commit(s).
- Отключить reminder retry UI/action (feature flag) при инциденте.
- Вернуться к текущему background-only reminder процессу.

## No-go
- Нельзя выполнять массовый retry без confirmation flow.
- Нельзя скрывать/терять `last_error` в диагностике.
- Нельзя обходить consent/tenant checks ради "успешных" цифр.

## Риски/блокеры
- Runtime backlog в outbox может искажать эффект reminder retry.
- Provider degradation может давать ложные повторные FAIL без root-cause fix.
- Без ясного error taxonomy операторы будут "стрелять retry вслепую".

## Branch / Worktree / Merge
- Branch: `feat/2026-02-18-wave2-reminder-control-plane-a88`
- Worktree: `/home/zhan/worktrees/2026-02-18-wave2-reminder-control-plane-a88`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: Brain/Top Architect после merge
