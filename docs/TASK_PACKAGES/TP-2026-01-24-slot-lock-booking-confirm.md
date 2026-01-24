# TP-2026-01-24 — Slot-Lock + Booking Confirm (ChatGPT-like)

## Название/цель
Внедрить slot-lock и booking_confirm в booking-пайплайне с LLM-first slot_extract/validate и трассировкой, без изменения внешних фактов/политик.

## Invariant
- Hard-LAW: мед/жалобы/возвраты/юридические угрозы → только эскалация.
- decision_meta/decision_trace/outbox пишутся на каждый inbound.
- `_legacy.py` остаётся adapter-only.

## Scope
- Slot-lock: booking не сбрасывается на OOD/провокациях, удерживаем expected_reply_type.
- Slot-extract (LLM) + slot-validate (детерминированно) для ответов на слоты.
- Booking_confirm при низкой уверенности (подтверждение слота).
- decision_meta/trace поля: slot_confidence/slot_source/slot_confirmation_required.
- Natural dialog suite (6–10 ходов, шум/перебивки) + проверки appointment/appointment_audit/outbox + booking_commit trace.

## Out of scope
- Calendar sync, CA06, UI изменения.
- Изменения DB схем/миграции.
- Политики/прайс/контент в packs.

## Touch-list
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/trace.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_chaos_dialogs.py`

## Plan
1) Реализация slot_lock + booking_confirm (feature flag, threshold) в booking/decision.
2) Trace/meta: slot_extract/slot_validate/booking_confirm + slot_* поля.
3) Тесты: unit + chaos dialog suite (multi-turn, шум/перебивки).
4) Live-check: appointments/appointment_audit/outbox + booking_commit trace.
5) CI + запись evidence в `STATE.md`.

## DoD
- Slot-lock: booking не паузится на OOD/провокациях, ожидаемый слот сохраняется.
- slot_extract/slot_validate/booking_confirm трассируются; meta поля записаны.
- booking_commit создаёт appointment (если возможно) и пишет audit/outbox.
- Тесты проходят; CI зелёный; есть live-check evidence.

## Checks
- `pytest -q truffles-api/tests/test_webhook_booking.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py`
- CI (GitHub Actions)

## Evidence
- CI run URL
- `ops/diagnose.py livecheck` + `ops/diagnose.py explain`
- SQL: `appointments`, `appointment_audit`, `decision_trace` (booking_confirm/booking_commit), `outbox_messages`
- Запись в `STATE.md` до merge

## Rollback
- Откат PR + деплой предыдущего образа.

## No-go
- Красный CI.
- Нет decision_meta/trace на inbound.
- Любые изменения в `_legacy.py`.
- Хардкод фактов клиента.

## Риски/блокеры
- Низкая уверенность LLM → больше подтверждений (UX балансировать порогом).
- Нужен allowlist JID для live-check.

## Branch/Worktree
- Branch: `feat/slot-lock-booking-confirm`
- Worktree: `/home/zhan/worktrees/slot-lock-booking-confirm`
- Base: `origin/main`
- Merge policy: PR + CI green, merge делает Brain
- Cleanup: удалить ветку + worktree после merge
