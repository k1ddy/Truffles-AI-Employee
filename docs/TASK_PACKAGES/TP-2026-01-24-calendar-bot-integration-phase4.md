# TP-2026-01-24 — Bot booking → appointments integration (Phase 4)

- **Название/цель:** подключить booking‑flow бота к SoT `appointments` без хардкода и без обещаний слотов при отсутствии live‑провайдера.
- **Canon refs:** `SPECS/CONSULTANT.md`, `SPECS/ARCHITECTURE.md`, `SPECS/MULTI_TENANT.md`, `docs/IMPERIUM_DECISIONS.yaml` (DEC‑013).

## Invariant
- SoT по записям — Postgres; внешние календари не источник правды.
- Fail‑closed: без live‑провайдера — только `collect_preferences`.
- Branch isolation: appointment всегда с `branch_id`.
- Никакой логики в `_legacy.py`.

## Scope
- Интеграция booking‑flow с `appointments` через `SchedulingService`.
- Поведение по `booking_mode`:
  - `collect_preferences`: создаём `appointments` со статусом `PENDING_CONFIRMATION`, source `bot`.
  - `confirm_slots`: пока нет live‑provider — остаёмся в `collect_preferences` (no‑go на слоты).
- Запись `appointment_audit` + trace/meta для booking‑commit.
- Отправка карточки менеджеру (Telegram) и статуса клиенту (WhatsApp) через существующие каналы.

## Out of scope
- Google/CRM live‑availability.
- Новые Telegram UI для бронирований.
- Изменения в console‑workflow.

## Touch-list
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/services/appointment_service.py`
- `truffles-api/app/services/escalation_service.py` (handover, уведомления)
- `truffles-api/app/routers/webhook/trace.py`
- `truffles-api/tests/*` (новые unit/contract tests)
- `docs/TASK_PACKAGES/TP-2026-01-24-calendar-bot-integration-phase4.md`

## Plan
1) Выделить точку commit: когда booking‑slots собраны и booking‑prompt завершён.
2) Проверить `booking_mode`/`availability_provider` (branch/client) и создать appointment (PENDING_CONFIRMATION).
3) Записать audit/trace/meta (appointment_id, status, branch_id).
4) Уведомить менеджера и клиента (как в текущем booking‑handover).
5) Добавить unit‑тесты на создание appointment.

## DoD
- При завершённом booking‑flow создаётся appointment в БД.
- `decision_meta` содержит `appointment_id` и статус.
- Без live‑provider бот не предлагает слоты (collect‑only).

## Checks
- `pytest -q truffles-api/tests/test_booking_appointments.py` (new)
- `python3 -m compileall truffles-api/app/routers/webhook/booking.py truffles-api/app/services/appointment_service.py`

## Evidence
- Логи тестов + SQL записи appointment; запись в `STATE.md`.

## Rollback
- Откат PR.

## No-go
- Прямые вызовы внешних календарей в request‑path.
- Любые изменения `_legacy.py`.

## Риски/блокеры
- Нужна связка branch_id в booking‑context (если branch неизвестен → escalate).
- Потребуется согласовать, где хранить appointment_id в context.

## Branch / Worktree / Merge
- Branch: `feat/calendar-bot-integration-2026-01-24`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR + CI green, no rebase
- Cleanup: удалить ветку после merge
