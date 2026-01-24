# TP-2026-01-24 — Calendar local provider + scheduling service (Phase 2)

- **Название/цель:** перевести Console calendar на SoT `appointments` и локальный availability (без Google), с data‑driven параметрами (мастера/часы/услуги).
- **Canon refs:** `docs/IMPERIUM_DECISIONS.yaml` (DEC‑013), `SPECS/ARCHITECTURE.md`, `SPECS/MULTI_TENANT.md`, `STRATEGY/REQUIREMENTS.md`, `contracts/integrations/calendar_port.v1.md`.

## Invariant
- SoT по записям — Postgres; внешние календари не источник правды.
- Branch isolation по `branch_id`.
- Никаких slot‑обещаний без live‑провайдера.
- Request‑path не блокируем внешними провайдерами (outbox только async).
- Данные бизнеса (мастера/часы/услуги) — из БД, не хардкод.

## Scope
- Новый `appointment`/`scheduling` service для slots + CRUD appointments.
- Перевести `/console/v1/calendar/*` на новую модель `appointments`.
- Использовать `branch.timezone` + `branch.working_hours` как fallback, `specialist.working_hours` как override.
- Слоты блокируются `appointments` + `calendar_blocks`.
- Обновить UI статусные лейблы под новые статусы (без изменения API контракта).

## Out of scope
- Google OAuth/sync workers.
- Bot booking integration (будет отдельным TP).
- Reminder jobs и WhatsApp шаблоны.

## Touch-list
- `truffles-api/app/routers/calendar.py`
- `truffles-api/app/services/*`
- `truffles-api/app/models/*` (imports)
- `console-web/src/utils/labels.ts`
- `console-web/src/app/calendar/page.tsx`
- `contracts/console_api/openapi.v1.yaml` (если меняем контракт)
- `docs/TASK_PACKAGES/TP-2026-01-24-calendar-local-provider-phase2.md`

## Plan
1) Создать `AppointmentService` (slots + create + list + cancel).
2) Переподключить `calendar.py` на `AppointmentService`.
3) Обновить UI‑лейблы статусов.
4) Проверки (compile + smoke via API, если есть доступ).

## DoD
- Console calendar использует `appointments`, не `bookings`.
- Slots корректно учитывают working hours + blocks.
- Статусы в UI читаемы для новых enum.

## Checks
- `python3 -m compileall truffles-api/app/services truffles-api/app/routers/calendar.py`
- (если доступно) `curl -s https://api.truffles.kz/console/v1/calendar/specialists`
## Test waiver
- DB‑backed slot tests не добавлялись (нужен Postgres + fixtures); ограничились compileall.

## Evidence
- Логи checks + diff; запись в `STATE.md` как PLAN (если без live‑check).

## Rollback
- Откат PR.

## No-go
- Изменения в `_legacy.py`.
- Прямые вызовы внешних календарей в request‑path.

## Риски/блокеры
- Нужен backfill `appointments` для данных в UI.
- В prod может не быть working_hours → требуется fallback.

## Branch / Worktree / Merge
- Branch: `feat/calendar-local-provider-2026-01-24`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
