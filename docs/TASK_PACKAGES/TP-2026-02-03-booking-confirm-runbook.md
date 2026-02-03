# TP-2026-02-03-booking-confirm-runbook

- Название/цель: Добавить runbook и безопасный скрипт для быстрых проверок booking confirm (confirm_slots + provider readiness) с единым сбором evidence.
- Canon refs: `STATE.md` (booking confirm verification), `STRUCTURE.md`, `TECH.md`, `docs/runbooks/DIALOG_REPORT.md`, `ops/diagnose.py`.
- Invariant:
  - Не менять поведение booking/trace/outbox.
  - Скрипт не должен мутировать БД без явного opt-in.
  - Не чистить БД/trace ради evidence.
- Scope:
  - Runbook: `docs/runbooks/BOOKING_CONFIRM_VERIFY.md` (preflight, steps, evidence, failure modes).
  - Script: `scripts/booking_confirm_verify.sh` (preflight + optional apply + livecheck + evidence).
  - Обновить `STRUCTURE.md` и `STATE.md`.
  - Обновить session log.
- Out of scope:
  - Изменение валидатора outbox или логики booking/confirm.
  - Новые ops/diagnose subcommands.
  - Реальные OAuth токены/провайдерная интеграция.
- Touch-list (files):
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
  - `scripts/booking_confirm_verify.sh`
  - `STRUCTURE.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-02-03-booking-confirm-full-verify-a6.md`
  - `docs/TASK_PACKAGES/TP-2026-02-03-booking-confirm-runbook.md`
- Plan:
  1) Создать Task Package и обновить session log.
  2) Добавить runbook с шагами, командами и evidence.
  3) Добавить скрипт с dry-run и явным apply для DB изменений.
  4) Обновить `STRUCTURE.md` + `STATE.md`.
  5) Проверить `bash -n` для скрипта.
- DoD:
  - Runbook покрывает preflight, livecheck, SQL evidence и типовые фейлы.
  - Скрипт работает в dry-run, требует opt-in для DB изменений, фиксирует evidence в /tmp.
  - `STRUCTURE.md` и `STATE.md` отражают новый runbook/скрипт.
- Checks:
  - `bash -n scripts/booking_confirm_verify.sh`
- Evidence:
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
  - `scripts/booking_confirm_verify.sh`
- Rollback:
  - Удалить runbook/скрипт и записи в `STRUCTURE.md`/`STATE.md`.
- No-go:
  - Запуск скрипта на проде без явного opt-in.
  - Изменение бизнес-логики booking.
- Branch/worktree/base/merge/cleanup:
  - Branch: `feat/2026-02-03-booking-confirm-full-verify-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-03-booking-confirm-full-verify-a6`
  - Base: `origin/main`
  - Merge: PR required (core repo changes)
  - Cleanup: `scripts/session_end.sh --status done` + remove worktree/branch
- Риски/блокеры:
  - Разные окружения (DB имя/юзер, контейнерные имена).
  - Отсутствие allowlist JIDs или TEST_MODE.
