# TP-2026-02-03-booking-confirm-full-verify

- Название/цель: Полная верификация подтверждения записи (client → consultant → manager) с контейнерными тестами, live-check и SQL evidence.
- Canon refs: `STATE.md` (PLAN booking full-cycle), `SPECS/CONSULTANT.md`, `SPECS/SYSTEM_REFERENCE.md`, `SPECS/ARCHITECTURE.md`, `SPECS/MULTI_TENANT.md`, `TECH.md`.
- Invariant:
  - Никаких изменений поведения/кода/pack данных; только проверки и evidence.
  - Trace/meta и outbox idempotency не нарушаются.
  - `confirm_slots` работает только при provider_ready + fresh staleness gate.
- Scope:
  - Preflight проверки health + minimum_data_contract + provider health/staleness.
  - Контейнерные тесты booking + calendar sync.
  - Live-check suites: CA05 booking, CA05 booking-commit, CA12 booking-full (client→consultant→manager), опционально CA10 outbox.
  - SQL проверки: appointments, appointment_audit, appointment_sync_states, calendar_sync_cursors, outbox_messages, messages.metadata.
  - Сбор evidence в `/tmp` и запись в `STATE.md`.
- Out of scope:
  - Любые код/pack изменения, миграции, настройка OAuth/провайдеров, чистка БД, деплой.
- Touch-list (files/tables):
  - `docs/TASK_PACKAGES/TP-2026-02-03-booking-confirm-full-verify.md`
  - `docs/SESSIONS/SESSION-2026-02-03-booking-confirm-full-verify-a6.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - Таблицы: `branches`, `calendar_connections`, `google_calendar_tokens`, `calendar_sync_cursors`,
    `appointments`, `appointment_audit`, `appointment_sync_states`, `calendar_blocks`,
    `messages`, `conversations`, `outbox_messages`, `message_dedup`.
- Plan:
  1) Preflight: `/admin/version` + `/admin/health`; SQL по minimum_data_contract и booking_settings; provider health/staleness по `calendar_*` + `google_calendar_tokens`.
  2) Контейнерные тесты booking + calendar sync (anti-drift).
  3) Live-check suites CA05/CA05-commit/CA12 (+ CA10 опционально) с allowlist, `TEST_MODE=1`.
  4) SQL проверка статусов записи/синхронизации/trace-meta/outbox.
  5) Сбор evidence в `/tmp` + обновление `STATE.md`.
- DoD:
  - Все контейнерные тесты green.
  - Live-check CA05/CA05-commit/CA12 проходит, decision_meta/trace присутствуют.
  - `appointments` в ожидаемом статусе; `appointment_sync_states` присутствуют; outbox не FAILED.
  - Evidence сохранены и отражены в `STATE.md` (Brain/Top Architect).
- Checks:
  - `scripts/test_api_container.sh -- pytest -q /app/tests/test_booking_appointments.py`
  - `scripts/test_api_container.sh -- pytest -q /app/tests/test_webhook_booking.py`
  - `scripts/test_api_container.sh -- pytest -q /app/tests/test_calendar_provider_sync.py`
  - `scripts/test_api_container.sh -- pytest -q /app/tests/test_message_endpoint.py -k "booking"`
  - `scripts/test_api_container.sh -- python3 -m compileall /app/app/services /app/app/routers`
  - `scripts/test_api_container.sh -- ruff check /app/app /app/tests`
  - `python3 ops/diagnose.py livecheck-auto --suite ca05-booking --client-slug demo_salon --base-url http://localhost:8000 --noise none`
  - `python3 ops/diagnose.py livecheck-auto --suite ca05-booking-commit --client-slug demo_salon --base-url http://localhost:8000 --noise none`
  - `python3 ops/diagnose.py livecheck-auto --suite ca12-booking-full --client-slug demo_salon --base-url http://localhost:8000 --noise none`
  - `python3 ops/diagnose.py livecheck-auto --suite ca10-outbox --client-slug demo_salon --base-url http://localhost:8000 --noise none` (опционально)
- Evidence:
  - Логи тестов в `/tmp/pytest_*`.
  - Live-check jsonl + `ops/diagnose.py emit-evidence`.
  - SQL dumps по appointments/outbox/trace/meta.
  - Запись в `STATE.md` с ссылками на evidence.
- Rollback: не требуется (код не меняем); при сбое — фиксируем GAP/BLOCKED.
- No-go:
  - pytest внутри прод-контейнера; `docker cp`/`-v` hacks.
  - bypass allowlist/TEST_MODE; ручная чистка БД/trace.
  - изменения в packs/коде/конфиге.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-03-booking-confirm-full-verify-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-03-booking-confirm-full-verify-a6`
  - Base: `origin/main`
  - Merge: doc-only fast-forward to `main` (без PR)
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: нет allowlist/outbound, provider token отсутствует/expired, staleness gate stale, minimum_data_contract not ready.
