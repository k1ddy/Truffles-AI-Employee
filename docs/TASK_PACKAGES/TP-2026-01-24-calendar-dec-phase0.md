# TP-2026-01-24 — Calendar Scheduling DEC + Specs (Phase 0)

- **Название/цель:** зафиксировать решение по календарю (SoT, конфликт‑политика, branch‑scope, mixed confirmation) и синхронизировать канон‑доки для дальнейшей реализации без хардкода.
- **Canon refs:** `docs/IMPERIUM_DECISIONS.yaml`, `SPECS/ARCHITECTURE.md`, `SPECS/MULTI_TENANT.md`, `STRATEGY/REQUIREMENTS.md`, `CalendarIntegration.md`, `CalendarIntegration1.md`, `contracts/integrations/calendar_port.v1.md`.

## Invariant
- SoT по записям — Postgres; внешние календари не источник правды.
- Без live‑провайдера доступности — только `collect_preferences`, без обещаний слотов.
- Branch isolation: токены/календарь/настройки/доступы строго по `branch_id`.
- Никаких хардкодов: мастера/часы/услуги/буферы — только данные.
- Синхронизация с провайдерами через outbox; request‑path не блокируем.

## Scope
- DEC по календарю: SoT + конфликт‑политика + mixed confirmation per‑branch + per‑branch calendar + pgcrypto.
- Обновить `SPECS/ARCHITECTURE.md` и `SPECS/MULTI_TENANT.md` под решения.
- Зафиксировать точки расширения (provider‑порт, outbox, audit).

## Out of scope
- Код, миграции БД, UI/Console изменения.
- OAuth flow, sync workers, reminders.

## Touch-list
- `docs/IMPERIUM_DECISIONS.yaml`
- `SPECS/ARCHITECTURE.md`
- `SPECS/MULTI_TENANT.md`
- `docs/TASK_PACKAGES/TP-2026-01-24-calendar-dec-phase0.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Зафиксировать DEC‑013 в `docs/IMPERIUM_DECISIONS.yaml`.
2) Обновить архитектурный канон (SoT, outbox‑sync, branch‑scope, data‑driven).
3) Обновить multi‑tenant правила (branch overrides для booking/confirmation/timezone).
4) Зафиксировать Task Package и запись в `STATE.md`.

## DoD
- DEC‑013 зафиксирован в `docs/IMPERIUM_DECISIONS.yaml`.
- `SPECS/ARCHITECTURE.md` и `SPECS/MULTI_TENANT.md` отражают канон.
- Task Package добавлен, `STRUCTURE.md` и `STATE.md` обновлены.

## Checks
- `rg -n "Scheduling core|calendar" SPECS/ARCHITECTURE.md SPECS/MULTI_TENANT.md docs/IMPERIUM_DECISIONS.yaml`

## Evidence
- Ссылки на изменения в `STATE.md` (PLAN).

## Rollback
- Откатить doc‑изменения.

## No-go
- Любые изменения в коде/БД/консоли до следующего Task Package.

## Риски/блокеры
- DEC должен согласовать owner (Жанбол).
- Дальнейшие фазы требуют схемы данных и миграций.

## Branch / Worktree / Merge
- Branch: `docs/calendar-dec-2026-01-24`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
