# TP-2026-02-18-waveA-operational-contract-calendar-a100

- Название/цель: Зафиксировать простой операционный цикл филиала в текущем экране `Записи` без новых вкладок: `Запланировано -> Пришел | Не пришел -> Follow-up закрыт`.
- Canon refs: `AGENTS.md`, `STATE.md` NOW/GAP (calendar UX confusion), `STRUCTURE.md`, `STRATEGY/REQUIREMENTS.md`, `SPECS/CONTROL_PLANE.md`, `SPECS/SYSTEM_REFERENCE.md`.
- CA_ID: N/A.

## Invariant
- Не добавлять новые роли/вкладки/workflow экраны.
- Не ломать create/cancel/status update контур в calendar API.
- Не менять domain specialist сущность (мастер расписания).

## Scope
- Упростить отображение статусов записи в UI (`pending_confirmation/confirmed/...` => `Запланировано`; `completed` => `Пришел`; `no_show` => `Не пришел`).
- Добавить явный флаг `no_show_followup_done` в booking response (API), вычисляемый по `appointment_audit.action=no_show_followup`.
- В `calendar/page.tsx` показать состояние follow-up как закрытое после фиксации и не предлагать повторное действие как основное.
- Обновить contract/schema и backend tests для нового поля.

## Out of scope
- Маркетинг/campaign/promo flow.
- Напоминания OPS runbooks и provider-level retry UI.
- Полная миграция legacy статусов в БД.

## Touch-list
- `truffles-api/app/routers/calendar.py`
- `truffles-api/tests/test_calendar_noshow_followup_router.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/app/calendar/page.tsx`
- `console-web/src/utils/labels.ts`

## Plan
1. Добавить `no_show_followup_done` в booking response и вычисление через `appointment_audit`.
2. Обновить UI `Записи`: единые простые статусы и follow-up closed state.
3. Обновить тесты/контракт и прогнать targeted checks.

## DoD
- Менеджер не видит неоднозначное `ожидает подтверждения`; видит `Запланировано`.
- Для `NO_SHOW` после фиксации follow-up запись помечается как `follow-up закрыт`.
- API и тесты подтверждают корректность `no_show_followup_done`.

## Checks
- `pytest -q truffles-api/tests/test_calendar_noshow_followup_router.py`
- `pytest -q truffles-api/tests/test_console_openapi_calendar_contract.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `ruff check truffles-api/app/routers/calendar.py truffles-api/tests/test_calendar_noshow_followup_router.py`
- `npm --prefix console-web run lint -- --file src/app/calendar/page.tsx --file src/utils/labels.ts`

## Evidence
- PR diff по touch-list.
- Outputs pytest/openapi/ruff/lint.
- Скрин или описание calendar cards до/после (статусы + follow-up closed).

## Rollback
- Revert PR commit(s).

## No-go
- Не вводить новые роли (`specialist/support/marketer`) в пользовательский контур.
- Не добавлять новые вкладки навигации.
- Не добавлять технические OPS действия в менеджерский UX.

## Риски/блокеры
- Возможные пересечения с параллельными правками `calendar.py` и `openapi`.
- Локально может отсутствовать `next` для lint фронта.

## Branch / Worktree / Merge
- Branch: `feat/2026-02-18-waveA-operational-contract-calendar-a100`
- Worktree: `/home/zhan/worktrees/2026-02-18-waveA-operational-contract-calendar-a100`
- Base ref: `origin/main`
- Merge policy: merge-only (no rebase)
- Cleanup: Brain/Top Architect после merge
