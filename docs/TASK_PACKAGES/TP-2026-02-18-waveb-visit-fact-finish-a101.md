# TP-2026-02-18-waveb-visit-fact-finish-a101

- Название/цель: Закрыть P0 Visit Fact Finish по филиалам без усложнения UX: один операционный контракт + idempotent follow-up с доказуемым фактом закрытия и опциональной связью на новую запись.
- Canon refs: `AGENTS.md`, `STATE.md`, `STRUCTURE.md`, `STRATEGY/REQUIREMENTS.md`, `docs/CONSOLE_AUDIT/pages/calendar.md`.
- CA_ID: N/A.

## Invariant
- Не добавлять новые вкладки/экраны.
- Сохранять простой цикл в Calendar: `Запланировано -> Пришел | Не пришел -> Follow-up закрыт`.
- Не менять модель ролей (owner/admin/manager/viewer).

## Scope
- One-page операционный контракт (`роль -> действие -> факт -> KPI`) зафиксировать в `docs/CONSOLE_AUDIT/pages/calendar.md`.
- Сделать `no_show_followup` идемпотентным в API (повторный запрос не создает дубликаты audit rows).
- Добавить в факт follow-up: `closed_at`, `closed_by`, `result` (`contacted|rebooked`), `rebooked_appointment_id` (опционально).
- Расширить booking response полями follow-up state и показать это в текущем UI карточки `Записи`.

## Out of scope
- Reminder OPS control-plane.
- Marketing/campaign контуры.
- Полная миграция legacy booking statuses в БД.

## Touch-list
- `truffles-api/app/routers/calendar.py`
- `truffles-api/tests/test_calendar_noshow_followup_router.py`
- `truffles-api/tests/test_console_openapi_calendar_contract.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/app/calendar/page.tsx`
- `docs/CONSOLE_AUDIT/pages/calendar.md`

## Plan
1. Зафиксировать one-page операционный контракт в audit doc.
2. Реализовать idempotent follow-up и расширенный follow-up fact в backend + contract.
3. Обновить Calendar UI под follow-up state без усложнения основного потока.
4. Прогнать targeted tests/checks и подготовить PR evidence.

## DoD
- Повторное закрытие no-show follow-up не создает дубликаты audit rows.
- Booking response возвращает follow-up state (`done/result/closed_at/closed_by/rebook link`).
- UI карточки `NO_SHOW` показывает ясный итог follow-up.
- One-page контракт добавлен и соответствует текущему поведению.

## Checks
- `pytest -q truffles-api/tests/test_calendar_noshow_followup_router.py`
- `pytest -q truffles-api/tests/test_console_openapi_calendar_contract.py`
- `ruff check truffles-api/app/routers/calendar.py truffles-api/tests/test_calendar_noshow_followup_router.py truffles-api/tests/test_console_openapi_calendar_contract.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run lint -- --file src/app/calendar/page.tsx`

## Evidence
- PR diff по touch-list.
- Outputs pytest/ruff/openapi/lint.
- Описание UX изменения на карточке записи (`NO_SHOW`).

## Rollback
- Revert PR commit(s) целиком.

## No-go
- Не добавлять тех-операции в менеджерский UX.
- Не добавлять новые роли и экраны.
- Не менять unrelated core behavior.

## Риски/блокеры
- Локально может отсутствовать frontend toolchain (`next/typescript`) для lint/tsc.
- Возможны параллельные конфликты в `calendar.py`/`openapi.v1.yaml`.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-18-waveb-visit-fact-finish-a101`
- Worktree: `/home/zhan/worktrees/2026-02-18-waveb-visit-fact-finish-a101`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: Brain/Top Architect после merge
