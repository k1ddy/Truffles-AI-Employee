# TP-2026-01-24 Trace booking_commit retention + booking livecheck

## Название/цель
Сохранить `booking_commit` в decision_trace при длинных диалогах и добавить livecheck-сценарий, который завершает booking и проверяет appointments/appointment_audit/outbox.

## Invariant
- P0: trace/meta пишутся всегда; critical stages не теряются.
- P0: `_legacy.py` остаётся adapter-only (без оркестрации).
- P0: outbox idempotency и auto-heal не ломаем.

## Scope
- Retention: гарантировать сохранение последнего `booking_commit` в `decision_trace` при `DECISION_TRACE_MAX`.
- Unit test на retention для `booking_commit`.
- Livecheck suite: booking завершение + проверки `appointments`, `appointment_audit`, `decision_trace.booking_commit`, `outbox_messages`.
- CI livecheck: включить новую suite в артефакты/запуск.
- Документация Task Package + отметки в `STRUCTURE.md`/`STATE.md` после evidence.

## Out of scope
- Изменение логики booking/appointment creation.
- Миграции схемы календаря/appointments.
- Исправление CA06 (отложено).

## Touch-list
- `truffles-api/app/routers/webhook/trace.py`
- `truffles-api/tests/test_webhook_trace.py`
- `ops/diagnose.py`
- `.github/workflows/ci.yml`
- `docs/TASK_PACKAGES/TP-2026-01-24-trace-booking-commit.md`
- `STRUCTURE.md`
- `STATE.md`

## Plan
1) Добавить pinned retention для `booking_commit` и unit test.
2) Реализовать livecheck suite для booking commit + DB checks.
3) Подключить suite в CI livecheck (артефакты/список).
4) Запустить локальные тесты; подготовить livecheck/SQL evidence.
5) Обновить `STRUCTURE.md` и `STATE.md` по evidence.

## DoD
- `booking_commit` остаётся в trace даже при `decision_trace` > 40.
- Unit test проходит и фиксирует retention pinned stage.
- Livecheck suite успешно завершает booking и валидирует `appointments`, `appointment_audit`, `booking_commit` trace и outbox.
- CI livecheck включает новый suite; артефакты и evidence сохранены.

## Checks
- `pytest -q truffles-api/tests/test_webhook_trace.py`
- (optional) `pytest -q truffles-api/tests/test_booking_appointments.py`
- Livecheck: `python3 ops/diagnose.py livecheck-auto --suite <new-suite> --remote-jid <allowlist>`

## Evidence
- CI run URL (livecheck artifacts).
- SQL: `appointments`, `appointment_audit`, `outbox_messages` для test marker.
- decision_trace фрагмент с `booking_commit`.
- Запись в `STATE.md` (conv_id, msg_id, trace_id, outbox_id).

## Rollback
- Revert коммит(ы) или убрать suite из CI и вернуть retention логику.

## No-go
- Не трогать `_legacy.py` для оркестрации.
- Не менять booking flow ради тестов.
- Не чистить БД/trace ради evidence.

## Риски/блокеры
- CA06 остаётся в красном; если CI падает из-за CA06 — фикс/skip отдельно.
- Livecheck требует allowlist JID и чистый диалог.

## Branch / Worktree
- Branch: `fix/trace-booking-commit`
- Worktree: `/home/zhan/truffles-main`
- Base ref: `origin/main`
- Merge policy: PR + CI green, без rebase (merge only)
- Cleanup: Brain после merge
