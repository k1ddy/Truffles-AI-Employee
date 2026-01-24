# TP-2026-01-24 — Calendar Scheduling Data Model + Migrations (Phase 1)

- **Название/цель:** заложить SoT‑модель расписания (appointments/blocks/sync/reminders/visits) и безопасное хранение токенов (pgcrypto), без включения логики в runtime.
- **Canon refs:** `docs/IMPERIUM_DECISIONS.yaml` (DEC‑013), `SPECS/ARCHITECTURE.md`, `SPECS/MULTI_TENANT.md`, `STRATEGY/REQUIREMENTS.md`, `CalendarIntegration.md`, `CalendarIntegration1.md`, `contracts/integrations/calendar_port.v1.md`.

## Invariant
- SoT по записям — Postgres; внешние календари не источник правды.
- Без live‑провайдера доступности — только `collect_preferences`, без обещаний слотов.
- Branch isolation: календарь/токены/настройки строго по `branch_id`.
- Данные бизнеса (мастера, часы, услуги/буферы) — только из БД/онбординга, без хардкода.
- Синхронизация провайдеров — только через outbox.

## Scope
- Миграции БД: `appointments`, `appointment_services`, `appointment_sync_states`, `calendar_blocks`,
  `calendar_connections`, `calendar_sync_cursors`, `reminder_jobs`, `visits`, `appointment_audit`,
  `services`, `specialist_services`.
- Колонки `branches.timezone/working_hours/booking_settings`.
- pgcrypto + encrypted columns для `google_calendar_tokens`.
- SQLAlchemy модели под новые таблицы.
- Update Google Calendar token handling to use encrypted columns (fail‑closed).

## Out of scope
- Запуск sync воркеров и провайдеров (Google inbound/outbound).
- Перевод Console UI на новую модель.
- Интеграция bot‑booking в pipeline.

## Touch-list
- `truffles-api/migrations/009_add_calendar_scheduling.sql`
- `truffles-api/app/models/branch.py`
- `truffles-api/app/models/google_calendar_token.py`
- `truffles-api/app/services/google_calendar_service.py`
- `truffles-api/app/models/appointment*.py`
- `truffles-api/app/models/calendar_*.py`
- `truffles-api/app/models/reminder_job.py`
- `truffles-api/app/models/visit.py`
- `truffles-api/app/models/service*.py`
- `docs/TASK_PACKAGES/TP-2026-01-24-calendar-data-model-phase1.md`
- `STRUCTURE.md`, `STATE.md`

## Plan
1) Добавить миграцию с таблицами и ограничениями (exclusion constraint).
2) Добавить модели SQLAlchemy для новых сущностей.
3) Включить pgcrypto и перейти на encrypted токены (fallback на plaintext, fail‑closed без ключа).
4) Зафиксировать Task Package в `STATE.md` и `STRUCTURE.md`.

## DoD
- Миграция добавлена и содержит все таблицы/индексы/constraints.
- Модели соответствуют схемам.
- Google Calendar tokens пишутся/читаются через pgcrypto (с защитой при отсутствии ключа).
- `STATE.md` обновлён как PLAN (без evidence).

## Checks
- `python -m compileall truffles-api/app/models truffles-api/app/services/google_calendar_service.py`
- `rg -n "calendar|appointment|reminder" truffles-api/migrations/009_add_calendar_scheduling.sql`

## Evidence
- Логи compileall (local) + ссылки на diff.

## Rollback
- Откат миграции и моделей.

## No-go
- Любая логика в `_legacy.py` или входных роутерах.
- Прямые вызовы внешнего календаря из request‑path.

## Риски/блокеры
- Нужен ключ `CALENDAR_TOKEN_ENC_KEY` для полноценного шифрования.
- Дальше потребуется backfill/миграция данных из legacy `bookings`.

## Branch / Worktree / Merge
- Branch: `feat/calendar-data-model-2026-01-24`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
