# TP-2026-02-05-console-analytics-kpis

- Название/цель: Добавить truth-first KPI-метрики (8 пунктов) в Insights, с явной маркировкой FACT/ESTIMATE/NEED и доказательствами на основе БД.
- Canon refs: `STATE.md` (GAP: Insights KPI truth-first), `STRATEGY/REQUIREMENTS.md` (аналитика, truth-first), `SPECS/CONTROL_PLANE.md` (Insights), `SPECS/ARCHITECTURE.md` (trace/meta/outbox), `SPECS/ESCALATION.md` (handover), `docs/CONSOLE_GUIDE.md`, `ops/metrics_daily_snapshot.sql`.
- Invariant:
  - Поведение диалогов/эскалации не меняется.
  - Метрики считаются из предагрегата (daily snapshot), без тяжёлых запросов в UI.
  - decision_meta/decision_trace не ломаются; outbox idempotency сохраняется.
  - RBAC fail-closed.
- Scope:
  - БД: handover snapshot (slots) + trigger_message_id; события outbox/alerts; daily analytics snapshot.
  - Backend: агрегация KPI, API выдачи, статусы FACT/ESTIMATE/NEED.
  - Frontend: Insights UI для 8 KPI + подсказки по определению.
  - Trends: 7-дневные тренды KPI из `metrics_analytics_daily` (sparkline-графики).
  - Док: определения метрик и rules-of-truth (short).
- Out of scope:
  - LLM-инсайты/кластеризация.
  - Реалтайм/стриминг.
  - Billing/финансы.
  - Кросс-tenant агрегаты.
  - Полноценный BI-дашборд с произвольными фильтрами.
- Touch-list:
  - Таблицы: `handovers` (meta, trigger_message_id), `outbox_status_events`, `alert_events`, `metrics_analytics_daily` (new), `metrics_daily` (read).
  - `truffles-api/migrations/020_add_handover_meta.sql`
  - `truffles-api/migrations/021_add_outbox_status_events.sql`
  - `truffles-api/migrations/022_add_alert_events.sql`
  - `ops/migrations/019_add_metrics_analytics_daily.sql`
  - `ops/metrics_daily_snapshot.sql`
  - `truffles-api/app/models/handover.py`
  - `truffles-api/app/models/outbox_message.py` (events integration)
  - `truffles-api/app/models/alert_event.py` (new)
  - `truffles-api/app/models/outbox_status_event.py` (new)
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/services/escalation_service.py`
  - `truffles-api/app/services/outbox_service.py`
  - `truffles-api/app/services/reminder_service.py`
  - `truffles-api/app/services/metrics_daily_service.py` (or new analytics service)
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `contracts/console_api/openapi.v1.yaml`
  - `console-web/src/app/insights/page.tsx`
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/types/api.generated.ts`
  - `docs/CONSOLE_GUIDE.md`
  - `STATE.md`
- Plan:
  1. Зафиксировать GAP в `STATE.md` и короткие определения метрик в `docs/CONSOLE_GUIDE.md`.
  2. Добавить DB миграции (handover meta/trigger_message_id, outbox_status_events, alert_events, metrics_analytics_daily).
  3. Записать handover snapshot на эскалации; фиксировать outbox/alert события.
  4. Реализовать daily analytics snapshot (SQL + сервис) и join в `/console/v1/metrics/daily`.
  5. Обновить OpenAPI + типы клиента.
  6. Обновить Insights UI (KPI tiles + FACT/ESTIMATE/NEED + подсказки).
  7. Добавить KPI trends (API series + sparkline-графики в UI).
  8. Тесты/линт + evidence (SQL snapshots, test logs).
- DoD:
  - 8 KPI отображаются в Insights с меткой статуса.
  - KPI берутся из daily snapshot, UI без тяжёлых запросов.
  - Тренды KPI (7 дней) отображаются и основаны на `metrics_analytics_daily`.
  - Handover snapshot и outbox/alert events пишутся.
  - OpenAPI и UI типы синхронизированы.
  - Есть минимум 1 тест.
- Checks:
  - `pytest -q truffles-api/tests/test_console_analytics.py`
  - `npm --prefix console-web run lint`
- Evidence:
  - SQL snapshot output в `/tmp/analytics_daily_snapshot_*.txt`.
  - Логи тестов/линта в `/tmp/*`.
  - Запись в `STATE.md` (Brain/Architect) до merge.
- Rollback:
  - Реверт коммита; при необходимости откат миграций обратным SQL.
- No-go:
  - Тяжёлые агрегации на каждый UI-запрос.
  - Изменения в core-логике принятия решений.
  - Ручная правка БД ради evidence.
- Риски/блокеры:
  - Исторические данные без новых событий будут частично пустыми.
  - Нет гарантии заполненности branch.timezone/working_hours.
- Branch/Worktree/Base/Merge/Cleanup:
  - Branch: `feat/2026-02-05-console-analytics-kpis-a7`
  - Worktree: `/home/zhan/worktrees/2026-02-05-console-analytics-kpis-a7`
  - Base ref: `origin/main`
  - Merge policy: merge-only
  - Cleanup: удалить worktree/branch после merge
