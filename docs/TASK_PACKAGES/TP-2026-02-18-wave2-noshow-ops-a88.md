# TP-2026-02-18-wave2-noshow-ops-a88

- Название/цель: Упростить операционный контроль филиалов после Wave 1: показать причину неявок через reminders и дать менеджеру один явный follow-up контур без финансовых метрик.
- Canon refs: `AGENTS.md`, `STATE.md` NOW/GAP, `SPECS/CONTROL_PLANE.md`, `SPECS/ARCHITECTURE.md`, `TECH.md`, `docs/CONSOLE_AUDIT/pages/calendar.md`, `docs/CONSOLE_AUDIT/pages/business.md`.
- CA_ID: N/A.

## Invariant
- Модель визита остаётся простой: только `COMPLETED` (`Пришел`) и `NO_SHOW` (`Не пришел`).
- Напоминания остаются outbox-first и tenant/branch scoped.
- Без финансовых KPI и без новых сложных статусов визита.

## Scope
- Добавить в Business summary операционные показатели reminders/no-show follow-up:
  - `reminder_delivery_failures_today`
  - `no_show_followup_pending`
- Добавить в Calendar для `NO_SHOW` явный action `Связаться / перезаписать` (операционный follow-up, без изменения статуса визита).
- Добавить backend endpoint для фиксации follow-up по `NO_SHOW` в audit trail.
- Обновить OpenAPI/типы/доки и тесты.

## Out of scope
- Revenue/ROI/денежная атрибуция.
- Маркетинговые кампании/сегменты.
- Новые промежуточные статусы визита.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/calendar.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/models/appointment_audit.py` (только при необходимости нового action payload)
- `truffles-api/tests/test_console_owner_business.py`
- `truffles-api/tests/test_booking_appointments.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/app/business/page.tsx`
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/lib/api-client.ts`
- `docs/CONSOLE_AUDIT/pages/business.md`
- `docs/CONSOLE_AUDIT/pages/calendar.md`

## Plan
1. Зафиксировать API-контракт для follow-up action по `NO_SHOW` и новых KPI в business summary.
2. Реализовать backend вычисление KPI reminders/follow-up и endpoint фиксации follow-up.
3. Добавить UI action в calendar + KPI блок в business.
4. Обновить OpenAPI/type contracts.
5. Прогнать targeted tests и frontend checks.

## DoD
- В `Business` видны `reminder_delivery_failures_today` и `no_show_followup_pending`.
- В `Calendar` у записи `NO_SHOW` есть понятное действие follow-up.
- Follow-up фиксируется в backend/audit и доступен для диагностики.
- Контракт/доки/тесты синхронизированы.

## Checks
- `pytest -q truffles-api/tests/test_console_owner_business.py`
- `pytest -q truffles-api/tests/test_booking_appointments.py`
- `pytest -q truffles-api/tests/test_console_openapi_calendar_contract.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run lint -- --file src/app/calendar/page.tsx --file src/app/business/page.tsx --file src/lib/api-client.ts`
- `npx --prefix console-web tsc --noEmit --incremental false -p console-web/tsconfig.json`

## Evidence
- PR diff для touch-list
- pytest/lint/tsc outputs
- API contract diff (`contracts/console_api/openapi.v1.yaml`)
- `docs/CONSOLE_AUDIT` updates

## Rollback
- Revert PR commit(s).
- Отключить UI follow-up action и endpoint обработчик.

## No-go
- Не добавлять новые визит-статусы.
- Не добавлять денежные KPI.
- Не смешивать follow-up с маркетинговыми рассылками.

## Риски/блокеры
- Грязный canonical root с несвязанными изменениями.
- Возможные конфликты с параллельными ветками по `calendar/console.py`.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-18-wave2-noshow-ops-a88`
- Worktree: `/home/zhan/worktrees/2026-02-18-wave2-noshow-ops-a88`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: Brain/Top Architect после merge
