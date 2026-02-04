# TP-2026-02-04-analytics-message-metrics

- Название/цель: Добавить корректные метрики "сообщений от клиентов" и "ответов бота" в Analytics, без нагрузки на запросы.
- Canon refs: `SPECS/ARCHITECTURE.md` (outbox/trace/meta), `SPECS/CONTROL_PLANE.md` (Insights), `ops/metrics_daily_snapshot.sql`, `docs/CONSOLE_GUIDE.md`.
- Invariant:
  - Поведение диалогов/эскалации не меняется.
  - Метрики считаются из предагрегата (metrics_daily), без тяжёлых запросов в UI.
  - RBAC fail-closed.
- Scope:
  - Источники метрик: inbound (role=user) и bot replies (assistant, source=bot).
  - Явное source‑tagging для bot/system/reminder сообщений.
  - Расширение metrics_daily + snapshot SQL.
  - Экспорт метрик через Console API + отображение в Insights.
  - Бизнес‑документ: правила подсчета сообщений для биллинга + доказательства.
- Out of scope:
  - Реалтайм/стриминговая аналитика.
  - Новые канальные/филиальные разрезы (channel/branch) — отдельной задачей.
  - Любые изменения core‑логики принятия решений.
- Touch-list:
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/routers/webhook/response.py`
  - `truffles-api/app/routers/webhook/guards.py`
  - `truffles-api/app/services/reminder_service.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/app/routers/admin.py`
  - `ops/metrics_daily_snapshot.sql`
  - `console-web/src/app/insights/page.tsx`
  - `docs/CONSOLE_AUDIT/pages/insights.md`
  - `Business/Sales/BILLING_COUNTING.md`
  - `STRUCTURE.md`
  - `STATE.md`
- Plan:
  1. Зафиксировать определения метрик (inbound/bot replies) и source‑tagging.
  2. Добавить source=bot/system/reminder в сохранение сообщений.
  3. Расширить metrics_daily snapshot (колонки + расчёт).
  4. Экспортировать метрики в Console API и отобразить в Insights.
  5. Lint/tests + evidence.
- DoD:
  - В Analytics отображаются: inbound messages, bot replies.
  - Метрики берутся из metrics_daily; нет тяжёлых запросов в UI.
  - source‑tagging есть у bot/system/reminder сообщений.
  - Бизнес‑документ по биллингу создан и привязан в STRUCTURE/STATE.
  - Lint зелёный.
- Checks:
  - `npm --prefix console-web run lint`
  - Test waiver: без нового e2e (нет фикстур под Insights).
- Evidence:
  - Логи линта в `/tmp/*`.
  - SQL/скрин из `/admin/metrics` или snapshot output (если доступно).
  - Запись в `STATE.md` (Brain/Architect) перед merge.
- Rollback:
  - Реверт коммита.
- No-go:
  - Любые тяжёлые агрегации на каждый UI‑запрос.
  - Подмена поведения pipeline.
- Риски/блокеры:
  - Исторические данные без source‑tagging могут требовать backfill.
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-04-analytics-message-metrics-a6`
  - Worktree: `/home/zhan/worktrees/2026-02-04-analytics-message-metrics-a6`
  - Base ref: `origin/main`
  - Merge policy: merge-only
  - Cleanup: удалить worktree/branch после merge
