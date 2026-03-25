# TP-2026-02-03-calendar-oauth-callback

- Название/цель: Поднять Google Calendar OAuth callback на домене Console и получить реальные токены для provider sync (demo_salon/branch_b).
- Canon refs: `STATE.md` (GAP calendar sync outbound failed), `SPECS/SYSTEM_REFERENCE.md`, `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`.
- Invariant:
  - Не менять booking/trace поведение.
  - OAuth токены не коммитятся в репозиторий.
  - Outbox календаря остаётся SoT=DB (provider только проекция).
- Scope:
  - Добавить proxy‑route `/api/calendar/callback` в console‑web.
  - Настроить `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI` в env для API.
  - Пройти OAuth для demo_salon/branch_b и записать токены в `google_calendar_tokens`.
  - Повторить booking confirm live-check и проверить calendar sync outbox.
- Out of scope:
  - Изменения OAuth клиента в Google Console.
  - UI/UX в Console.
  - Миграции/схемы.
- Touch-list (files/tables):
  - `console-web/src/app/api/calendar/callback/route.ts`
  - `docs/TASK_PACKAGES/TP-2026-02-03-calendar-oauth-callback.md`
  - `docs/SESSIONS/SESSION-2026-02-03-booking-confirm-full-verify-a6.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - Таблицы: `google_calendar_tokens`, `calendar_connections`, `calendar_sync_cursors`, `outbox_messages`
- Plan:
  1) Добавить console‑web callback route, rebuild console‑web контейнер.
  2) Настроить env для `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI` и перезапустить `truffles-api`.
  3) Пройти OAuth (auth URL) и убедиться, что токены записаны в БД.
  4) Прогнать `scripts/booking_confirm_verify.sh` и проверить outbox calendar sync.
  5) Зафиксировать evidence и обновить `STATE.md`.
- DoD:
  - В `google_calendar_tokens` лежат реальные токены (не test_*), `expires_at` валиден.
  - Booking confirm live-check проходит, calendar sync outbox не FAILED.
  - Evidence сохранены в `/tmp/booking-confirm-<stamp>` и отражены в `STATE.md`.
- Checks:
  - `docker compose -f truffles-api/docker-compose.yml build console-web`
  - `docker compose -f truffles-api/docker-compose.yml up -d --force-recreate console-web`
  - `scripts/booking_confirm_verify.sh --client-slug demo_salon --branch-slug branch_b --apply --cancel-appointments`
- Evidence:
  - `/tmp/booking-confirm-<stamp>` (livecheck jsonl + SQL)
  - SQL: `google_calendar_tokens`, `outbox_messages` calendar sync
- Rollback:
  - Откатить изменения console‑web route и перезапустить контейнер.
  - Удалить тестовые токены из БД (только при необходимости, через согласованный SQL).
- No-go:
  - Коммитить client_secret/токены.
  - Менять OAuth scopes без DEC.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-03-booking-confirm-full-verify-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-03-booking-confirm-full-verify-a6`
  - Base: `origin/main`
  - Merge: PR
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры: нужен интерактивный OAuth (человек), redirect URI должен совпадать с Google Console.
