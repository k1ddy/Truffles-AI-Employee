# TP-2026-02-03-booking-full-cycle-gcal

- Название/цель: Полный цикл записи (слоты → бронь → подтверждение/перенос/отмена → статус) + Google Calendar provider sync по DEC-013, с инструментами для консультанта (tool-first).
- Canon refs: `docs/IMPERIUM_DECISIONS.yaml` (DEC-013/DEC-020/DEC-021), `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`, `contracts/integrations/calendar_port.v1.md`, `STRATEGY/REQUIREMENTS.md`, `STATE.md` (PLAN).
- Invariant: SoT остаётся в Postgres; провайдер — только projection+busy; tool-first и pack-only факты; safe-mode при недостатке данных; outbox idempotency; trace/meta обязательны.
- Scope:
  - Инструменты консультанта: `calendar.list_slots`, `calendar.book_slot`, `calendar.get_booking`, `calendar.reschedule`, `calendar.cancel` + валидатор аргументов/состояния.
  - Availability: слоты считаются по `appointments` + `calendar_blocks` + рабочим часам; при подтверждении — безопасная деградация при staleness.
  - Google Calendar sync: outbound по outbox (create/update/cancel), inbound busy → `calendar_blocks`, `calendar_sync_cursors`, `appointment_sync_states`.
  - Booking info: сервис/мастер/длительность/цена/адрес/гео/портфолио только из packs/tools (без фактов в коде).
  - Appointment reminders + post-visit follow-ups через `reminder_jobs` и outbox (правила из pack/policy).
- Out of scope: UI/UX в Console, платежи/скидки, CRM/BI, multi-provider (кроме Google Calendar), двухсторонний апдейт appointments из провайдера.
- Touch-list:
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/booking.py`
  - `truffles-api/app/routers/webhook/outbox.py`
  - `truffles-api/app/routers/calendar.py`
  - `truffles-api/app/services/appointment_service.py`
  - `truffles-api/app/services/google_calendar_service.py`
  - `truffles-api/app/services/calendar_sync_service.py` (new)
  - `truffles-api/app/models/*calendar*`, `truffles-api/app/models/appointment_sync_state.py`
  - `truffles-api/app/models/reminder_job.py`
  - `contracts/integrations/calendar_port.v1.md`
  - `contracts/events/outbox.webhook_payload.v1.jsonschema`
  - `SPECS/ARCHITECTURE.md`, `SPECS/CONSULTANT.md`
  - `STATE.md`, `STRUCTURE.md`
- Plan:
  1) Зафиксировать tool contracts + allowlist и обновить спеки (calendar_port + ARCHITECTURE/CONSULTANT).
  2) Реализовать outbound sync (outbox events) и обновление `appointment_sync_states`.
  3) Реализовать inbound busy sync → `calendar_blocks` + staleness gate для `confirm_slots`.
  4) Встроить tool-first booking в decision pipeline (list/book/get/reschedule/cancel).
  5) Добавить reminder_jobs + отправку outbox по правилам pack/policy.
  6) Тесты + evidence; обновить `STATE.md` (PLAN→DONE/GAP).
- DoD:
  - `confirm_slots` работает только при provider_ready; при staleness → `collect_preferences`.
  - Запись/перенос/отмена создают outbox sync события; `appointment_sync_states` обновлены.
  - Inbound busy синхронизация пополняет `calendar_blocks` и влияет на слоты.
  - Tool-actions отражаются в decision_trace/meta (tool_used, tool_decision, tool_args).
  - Reminders/follow-ups создаются как `reminder_jobs`, отправка через outbox.
  - Тесты green и evidence собраны.
- Checks:
  - `pytest -q truffles-api/tests/test_booking_appointments.py`
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k "booking"`
  - `pytest -q truffles-api/tests/test_calendar_provider_sync.py` (new)
  - `pytest -q truffles-api/tests/test_reminder_jobs.py` (new)
- Evidence:
  - CI run URL + логи тестов.
  - SQL: `calendar_blocks`, `appointment_sync_states`, `calendar_sync_cursors`, `reminder_jobs`.
  - decision_trace/meta фрагменты с tool_action и outbox_id.
- Rollback: revert commit; `booking_mode=collect_preferences`; отключить provider sync event type.
- No-go: прямые вызовы провайдера в request-path; подтверждение слота при staleness; LLM факты/слоты без tool/pack.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-03-booking-full-cycle-gcal-a1`
  - Worktree: `/home/zhan/worktrees/2026-02-03-booking-full-cycle-gcal-a1`
  - Base: `origin/main`
  - Merge: PR → `main` (code)
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: OAuth токены/доступы Google, неполные pack данные (services/prices/durations), таймзоны, SLA outbox backlog.
