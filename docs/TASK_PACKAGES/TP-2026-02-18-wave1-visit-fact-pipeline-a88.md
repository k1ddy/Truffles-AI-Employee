# TP-2026-02-18-wave1-visit-fact-pipeline-a88

- Название/цель: Добавить факт-пайплайн посещений (check-in/completed/no-show) для филиалов/мастеров/услуг и закрыть бизнес-контракт "кто реально пришел после записи".
- Canon refs: `AGENTS.md`, `STATE.md` NOW/GAP, `SPECS/CONTROL_PLANE.md` (Calendar/roles/fail-closed), `SPECS/ARCHITECTURE.md` (trace/meta/audit discipline), `contracts/console_api/openapi.v1.yaml` (`/calendar/bookings`), `docs/CONSOLE_AUDIT/pages/calendar.md`.
- CA_ID: N/A.

## Invariant
- Существующие create/list/cancel booking flows не деградируют.
- Tenant/RBAC ограничения остаются fail-closed (branch-scoped для manager).
- Все статусные мутации пишут audit evidence.

## Scope
- API: добавить статусные операции для визита (`CHECKED_IN`, `COMPLETED`, `NO_SHOW`) по appointment.
- Data: использовать `visits` как SoT факта визита и связать с `appointments`.
- UI: добавить операторские действия статуса в `Calendar` для manager/owner/admin/platform_admin.
- Diagnostics: обеспечить evidence через `appointment_audit` + `visits`.

## Out of scope
- Маркетинговые кампании/рассылки.
- Финансовая атрибуция визита/выручки.
- Полный редизайн календаря.

## Touch-list
- `truffles-api/app/routers/calendar.py`
- `truffles-api/app/services/appointment_service.py`
- `truffles-api/app/models/visit.py` (при необходимости)
- `truffles-api/app/models/appointment_audit.py`
- `truffles-api/tests/test_booking_appointments.py`
- `truffles-api/tests/test_calendar.py` (если есть/создать)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/utils/labels.ts`
- `docs/CONSOLE_AUDIT/pages/calendar.md`
- `STATE.md`

## Plan
1. Спроектировать API contract: status transition endpoints + response schema.
2. Реализовать backend transitions с валидацией state machine и audit записью.
3. Добавить/обновить `visits` запись как факт статуса визита.
4. Добавить UI-кнопки и guardrails (role-gated + invalid transition hints).
5. Прогнать deterministic tests + e2e smoke для календаря.
6. Зафиксировать evidence (API responses + SQL `appointments/visits/audit` + trace/meta где применимо).

## DoD
- Manager/Owner/Admin/Platform Admin могут зафиксировать `checked_in/completed/no_show` по записи.
- В БД появляется связанный факт в `visits` и audit trail в `appointment_audit`.
- Calendar UI показывает эти статусы и блокирует недопустимые переходы.
- OpenAPI/typed client синхронизированы.

## Checks
- `python3 -m py_compile truffles-api/app/routers/calendar.py truffles-api/app/services/appointment_service.py`
- `pytest -q truffles-api/tests/test_booking_appointments.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k booking`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run lint -- --file src/app/calendar/page.tsx --file src/utils/labels.ts`
- `npm --prefix console-web run build`
- `PLAYWRIGHT_WEB_SERVER=0 PLAYWRIGHT_BASE_URL=https://console.truffles.kz npx playwright test e2e/smoke.spec.ts --project=chromium --no-deps --grep "calendar|booking"`

## Evidence
- API contract diff (`openapi.v1.yaml`)
- test logs (pytest + lint/build + e2e)
- SQL evidence:
  - `appointments.status` changed
  - `visits` row created/updated
  - `appointment_audit` row created with actor/action/status delta
- `docs/REPORTS/2026-02-18-wave1-visit-fact-pipeline-a88.md`
- `STATE.md` FACT/GAP entry

## Rollback
- Revert PR commit(s).
- Disable UI status actions feature flag (if introduced).
- Keep create/list/cancel paths intact.

## No-go
- Нельзя обновлять статус без audit записи.
- Нельзя оставлять `visits` неиспользуемой при включенном UI статусов.
- Нельзя внедрять кросс-филиальные мутации без явного branch scope.

## Риски/блокеры
- Исторические appointments без консистентных статусов потребуют backfill policy.
- Конфликт source-of-truth между `appointments.status` и `visits.status` без четкой transition logic.
- UX-риск: операторы могут ошибаться без confirm/hint при `NO_SHOW`.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-18-wave1-visit-fact-pipeline-a88`
- Worktree: `/home/zhan/worktrees/2026-02-18-wave1-visit-fact-pipeline-a88`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: Brain/Top Architect после merge
