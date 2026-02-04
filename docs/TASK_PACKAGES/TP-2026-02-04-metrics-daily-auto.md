# TP-2026-02-04-metrics-daily-auto

- Название/цель: Автоматизировать ежедневный snapshot metrics_daily (без ручного запуска SQL), с безопасным расписанием.
- Canon refs: `STATE.md` (GAP: metrics_daily snapshot automation), `ops/metrics_daily_snapshot.sql`, `TECH.md` (cron/outbox), `SPECS/ARCHITECTURE.md` (outbox/cron).
- Invariant:
  - UI остаётся read-only и читает предагрегат (metrics_daily), без тяжёлых запросов.
  - Снимок идемпотентен по (client_id, metric_date).
  - Outbox/cron воркеры не блокируются длительными задачами.
- Scope:
  - Сервис расчёта daily snapshot для всех активных клиентов.
  - Автозапуск по расписанию (worker/cron) с env‑тумблером.
  - Админ‑ручной запуск/бэкофил для проверки.
  - Документация (TECH.md/runbook).
- Out of scope:
  - Новые метрики/изменение формул.
  - Billing/оплата.
  - UI‑изменения.
- Touch-list:
  - `truffles-api/app/services/metrics_daily_service.py` (new)
  - `truffles-api/app/routers/admin.py`
  - `truffles-api/app/workers/outbox.py`
  - `TECH.md`
  - `STRUCTURE.md`
  - `STATE.md`
- Plan:
  1. Добавить сервис snapshot (SQL через `text`, idempotent insert/update).
  2. Добавить admin endpoint для ручного запуска/бэкофила.
  3. Встроить расписание в worker (daily, env‑toggled).
  4. Обновить документацию/cron‑инструкции.
  5. Проверки/waiver + evidence.
- DoD:
  - Daily snapshot запускается автоматически (при enabled).
  - Есть ручной admin‑запуск и логирование ошибок.
  - Документация обновлена.
  - Есть test waiver (Postgres‑only SQL) или тест.
- Checks:
  - Test waiver: Postgres‑specific SQL, локальные/CI тесты не добавляем; проверка через admin endpoint + SQL выборка.
- Evidence:
  - Логи admin‑запуска или SQL‑выборка metrics_daily (дата/клиент).
  - Запись в `STATE.md` (Brain/Architect) перед merge.
- Rollback:
  - Реверт коммита.
- No-go:
  - Тяжёлые запросы в UI.
  - Изменение формул метрик без отдельного решения.
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-04-metrics-daily-auto-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-04-metrics-daily-auto-a6`
  - Base ref: `origin/main`
  - Merge policy: merge-only
  - Cleanup: удалить worktree/branch после merge
