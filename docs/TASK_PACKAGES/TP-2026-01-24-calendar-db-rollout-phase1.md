# TP-2026-01-24 — Calendar DB rollout (Phase 1 apply)

- **Название/цель:** применить миграцию календарной схемы на БД и включить `CALENDAR_TOKEN_ENC_KEY` (pgcrypto).
- **Canon refs:** `docs/IMPERIUM_DECISIONS.yaml` (DEC‑013), `TECH.md`, `SPECS/ARCHITECTURE.md`, `STRATEGY/REQUIREMENTS.md`.

## Invariant
- SoT по записям — Postgres; внешние календари не источник правды.
- Branch isolation: календарь/токены/настройки строго по `branch_id`.
- Никаких slot‑обещаний без live‑провайдера.
- Никаких “ручных правок” БД ради evidence.

## Scope
- Применить `truffles-api/migrations/009_add_calendar_scheduling.sql` в prod БД.
- Сгенерировать и добавить `CALENDAR_TOKEN_ENC_KEY` в `/home/zhan/truffles-main/truffles-api/.env`.
- Перезапустить API контейнер, чтобы env подхватился.

## Out of scope
- Backfill данных из legacy `bookings`.
- Кодовые изменения и UI.

## Touch-list
- `/home/zhan/truffles-main/truffles-api/migrations/009_add_calendar_scheduling.sql`
- `/home/zhan/truffles-main/truffles-api/.env`
- `/home/zhan/restart_api.sh`

## Plan
1) Проверить окружение (prod check).
2) Применить миграцию.
3) Сгенерировать ключ и добавить в `.env`.
4) Перезапустить API контейнер.
5) Проверить наличие таблиц.

## DoD
- Миграция успешно применена (SQL output).
- `CALENDAR_TOKEN_ENC_KEY` установлен.
- `\\dt appointments` и `\\dt calendar_blocks` доступны.

## Checks
- `docker exec -i truffles_postgres_1 psql -U "$DB_POSTGRESDB_USER" -d chatbot -c "\\dt appointments"`
- `docker exec -i truffles_postgres_1 psql -U "$DB_POSTGRESDB_USER" -d chatbot -c "\\dt calendar_blocks"`

## Evidence
- SQL output + команда restart API (log).
- Запись в `STATE.md`.

## Rollback
- Откат не требуется (DDL additive). При критике — выключить feature‑использование.

## No-go
- Прямые изменения runtime/бот‑логики.
- Любые destructive SQL.

## Риски/блокеры
- Нужен доступ к `/home/zhan/infrastructure/.env` для кредов БД.
- Перезапуск API = короткий простой.

## Branch / Worktree / Merge
- Branch: `ops/calendar-db-rollout-2026-01-24`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
