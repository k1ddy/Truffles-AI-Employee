# TP-2026-02-03-booking-confirm-provider-ready

- Название/цель: Включить confirm_slots + provider readiness для demo_salon branch_b (booking_settings + calendar connection/token/cursor) и повторно проверить booking confirm с SQL evidence.
- Canon refs: `STATE.md` (booking confirm verification), `SPECS/VERTICAL_PACK_KIT.md`, `SPECS/ARCHITECTURE.md`, `STRATEGY/REQUIREMENTS.md`, `docs/PROCESSES.md`, `TECH.md`.
- Invariant:
  - Не менять поведение booking/SAFE_MODE/trace/outbox.
  - Не чистить БД/trace ради evidence.
  - Все изменения — только конфиг/данные для тестовой ветки demo_salon branch_b.
- Scope:
  - Обновить `branches.booking_settings` для branch_b: `booking_mode=confirm_slots`, `availability_provider=google_calendar`, `confirmation_policy=client`.
  - Создать/обновить `calendar_connections`, `google_calendar_tokens`, `calendar_sync_cursors` для provider readiness.
  - Проверить provider health/staleness через SQL + service call.
  - Re-run live-check CA05 booking-commit + CA12 booking-full (confirm_slots path).
  - SQL проверки: `appointments` (status=CONFIRMED), `appointment_sync_states` (row exists), `calendar_blocks` unchanged, outbox status, decision_meta/trace.
- Out of scope:
  - Реальный OAuth flow (если GOOGLE_CLIENT_ID/SECRET отсутствуют — фиксируем GAP).
  - Любые кодовые изменения booking logic.
- Touch-list (files/tables):
  - `docs/TASK_PACKAGES/TP-2026-02-03-booking-confirm-provider-ready.md`
  - `docs/SESSIONS/SESSION-2026-02-03-booking-confirm-full-verify-a6.md`
  - `STATE.md`
  - Tables: `branches`, `calendar_connections`, `google_calendar_tokens`, `calendar_sync_cursors`, `appointments`, `appointment_sync_states`, `calendar_blocks`, `messages`, `outbox_messages`.
- Plan:
  1) Preflight: capture current booking_settings + provider health inputs.
  2) Update branch_b booking_settings + insert/update calendar connection/token/cursor.
  3) Verify provider readiness (health check + staleness fresh).
  4) Run live-check CA05 booking-commit + CA12 booking-full (confirm_slots).
  5) SQL evidence for appointments/outbox/trace/meta/sync states.
  6) Update `STATE.md` + session log with evidence and any GAPs.
- DoD:
  - Provider readiness true (token + cursor present, staleness fresh).
  - CA05 booking-commit + CA12 booking-full pass without safe-mode.
  - Appointment status CONFIRMED for new runs, appointment_sync_states row exists.
  - Evidence stored in `/tmp` and recorded in `STATE.md`.
- Checks:
  - `curl -s http://localhost:8000/admin/health`
  - `TEST_MODE=1 python3 ops/diagnose.py livecheck-auto --suite ca05-booking-commit --client-slug demo_salon --base-url http://localhost:8000 --noise none --instance-id <branch_b_instance_id> --reset-before-suite`
  - `TEST_MODE=1 python3 ops/diagnose.py livecheck-auto --suite ca12-booking-full --client-slug demo_salon --base-url http://localhost:8000 --noise none --instance-id <branch_b_instance_id> --reset-before-suite`
- Evidence:
  - SQL dumps for booking_settings, connections/tokens/cursors, appointments, appointment_sync_states, calendar_blocks, outbox, messages.meta.
  - Live-check jsonl + emit-evidence.
  - Provider health output (service call).
- Rollback:
  - Revert branch_b booking_settings to previous JSON.
  - Delete inserted calendar connection/token/cursor rows for branch_b.
- No-go:
  - Удаление данных ради evidence.
  - Изменение core поведения booking/safe-mode.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-03-booking-confirm-full-verify-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-03-booking-confirm-full-verify-a6`
  - Base: `origin/main`
  - Merge: PR required (core repo changes)
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры:
  - GOOGLE_CLIENT_ID/SECRET отсутствуют → OAuth нельзя; календарный токен будет тестовый, sync может падать (фиксировать GAP).
