# TP-2026-02-03-outbox-calendar-sync-trace-guard

- Название/цель: Убрать перезапись decision_meta/decision_trace при ошибках outbox‑событий календаря (internal events), чтобы booking_commit trace сохранялся.
- Canon refs: `STATE.md` (GAP outbox payload guard rejects calendar sync), `SPECS/SYSTEM_REFERENCE.md`, `SPECS/ARCHITECTURE.md`, `docs/runbooks/OUTBOX.md`.
- Invariant:
  - `booking_commit` trace не теряется.
  - Outbox idempotency и обработка whatsapp.send_* не меняются.
  - Calendar sync остаётся enqueued, ошибки остаются в outbox meta/last_error.
- Scope:
  - Изменить обработку ошибок outbox‑событий (calendar sync/unsupported events) так, чтобы они не переписывали decision_meta/trace.
  - Локальная проверка через live‑check booking confirm.
- Out of scope:
  - OAuth/реальные токены календаря.
  - Изменения схем outbox/appointment.
  - Рефакторинг booking/trace pipeline.
- Touch-list (files/tables):
  - `truffles-api/app/routers/webhook/outbox.py`
  - `docs/TASK_PACKAGES/TP-2026-02-03-outbox-calendar-sync-trace-guard.md`
  - `docs/SESSIONS/SESSION-2026-02-03-booking-confirm-full-verify-a6.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `STRUCTURE.md`
- Plan:
  1) Добавить флаг(и) в `_record_outbox_payload_error` для опционального пропуска decision_meta/trace.
  2) Использовать флаги для calendar sync и неподдержанных outbox‑event’ов.
  3) Пересобрать контейнеры и перезапустить `truffles-api`/`truffles-outbox`.
  4) Прогнать `scripts/booking_confirm_verify.sh` (CA05/CA12) и собрать evidence.
  5) Обновить `STATE.md` (закрыть GAP) и сессию.
- DoD:
  - `livecheck-auto` CA05/CA12 проходят, `booking_commit` trace присутствует.
  - decision_meta на booking‑commit сообщении не содержит `outbox_payload_error` для calendar sync.
  - Outbox rows сохраняют `last_error` и meta с contract_error при ошибках event‑payload.
- Checks:
  - `python3 -m compileall truffles-api/app/routers/webhook/outbox.py`
  - `scripts/booking_confirm_verify.sh --client-slug demo_salon --branch-slug branch_b --apply --cancel-appointments`
- Evidence:
  - /tmp/booking-confirm-<stamp> (livecheck jsonl + SQL/trace/meta)
  - Логи compileall.
- Rollback: откатить изменения в `truffles-api/app/routers/webhook/outbox.py`, пересобрать контейнеры.
- No-go:
  - Изменения packs/knowledge.
  - Ручные правки БД вне скрипта.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-03-booking-confirm-full-verify-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-03-booking-confirm-full-verify-a6`
  - Base: `origin/main`
  - Merge: PR (поведенческое изменение)
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: требуется пересборка контейнеров; возможна несовместимость с текущим образом.
