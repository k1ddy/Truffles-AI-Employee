# TP-2026-01-24 — Calendar backfill (Phase 3)

- **Название/цель:** перенести legacy `bookings` в `appointments` и зашифровать существующие Google токены.
- **Canon refs:** `docs/IMPERIUM_DECISIONS.yaml` (DEC‑013), `TECH.md`, `SPECS/ARCHITECTURE.md`.

## Invariant
- SoT по записям — Postgres; внешний календарь не источник правды.
- Branch isolation обязательна.
- Никаких destructive операций на legacy таблицах.

## Scope
- Backfill `appointments` + `appointment_services` + `appointment_sync_states` из `bookings`.
- Backfill `google_calendar_tokens` в encrypted поля.

## Out of scope
- Удаление legacy `bookings`.
- Любые изменения runtime.

## Touch-list
- `truffles-api/migrations/010_backfill_appointments_from_bookings.sql`
- `TECH.md` (инструкции уже добавлены)
- `/home/zhan/truffles-main/truffles-api/.env`

## Plan
1) Создать SQL backfill файл (idempotent).
2) Выполнить backfill на БД.
3) Проверить счетчики (appointments vs bookings).
4) Выполнить backfill токенов (pgcrypto).

## DoD
- `appointments` и `appointment_services` заполнены из `bookings`.
- `appointment_sync_states` создан для `google_event_id`.
- `google_calendar_tokens.access_token_enc` заполнен (если был plaintext).

## Checks
- `SELECT COUNT(*) FROM appointments;`
- `SELECT COUNT(*) FROM bookings;`
- `SELECT COUNT(*) FROM google_calendar_tokens WHERE access_token_enc IS NULL AND access_token IS NOT NULL;`

## Evidence
- SQL output + запись в `STATE.md`.

## Rollback
- Отмена не требуется (additive). При проблеме — отключить использование новых таблиц.

## No-go
- Удаление `bookings` или данных.
- Любые изменения `_legacy.py`.

## Риски/блокеры
- Отсутствие `branch_id` у части `bookings` (нужна fallback логика).
- Требуется `CALENDAR_TOKEN_ENC_KEY`.

## Branch / Worktree / Merge
- Branch: `ops/calendar-backfill-2026-01-24`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
