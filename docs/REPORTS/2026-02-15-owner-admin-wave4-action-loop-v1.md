# Owner/Admin Wave-4 Report (Action Loop + Lite UX + Subscription v2)

Date
- 2026-02-15

Goal
- Закрыть сразу 4 приоритета:
  1. post-merge control (runtime evidence),
  2. Team KPI -> прямое действие (quick profile),
  3. onboarding-lite default в Settings,
  4. subscription transparency v2 для владельца.

Delivered
- Team KPI closed-loop (`/business/team-performance`):
  - добавлена CTA "Применить быстрый профиль" (5/30/60),
  - перед применением — confirm,
  - write path только при `settings:write`.
- Settings onboarding-lite (`/settings`):
  - default показывает только бизнес-поля:
    - SLA (1/2 напоминание),
    - эскалация,
    - Telegram,
    - подписка.
  - сложные блоки и provisioning перенесены в `Расширенные`.
  - добавлен блок "Что будет после сохранения" по каждому полю.
- Subscription v2 (`/subscription`):
  - `next_billing_date`,
  - alert-level `normal|warning_80|limit_100`,
  - `quota_alert_message`,
  - прогноз по перерасходу/остатку,
  - явное правило: `overage = max(0, billable - quota)`.
- Backend contract updates:
  - `ConsoleSubscriptionSummaryResponse` расширен полями v2 прозрачности.
  - `get_subscription_summary` считает projection/alerts без изменения billing формулы.

Validation
- Backend:
  - `ruff check truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/tests/test_console_owner_business.py`
  - `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py` -> `54 passed`
- Frontend:
  - `npm --prefix console-web run lint` -> OK
  - `npm --prefix console-web run build` -> OK
  - `npm --prefix console-web run test:e2e:smoke -- --list` -> включает Wave-4 smoke surfaces

Post-merge evidence
- Live-check:
  - `TEST_MODE=1 python3 ops/diagnose.py livecheck-auto --suite ca10-outbox --client-slug demo_salon --base-url http://localhost:8000 --noise none --reset-before-suite --poll-timeout 30 --timeout 20`
  - summary: `message_count=1`, `message_dedup_count=1`, `outbox_count=1`, `outbox_status=PENDING`
  - log: `/tmp/livecheck_owner_wave4_20260215-154354.log`
- Explain:
  - `python3 ops/diagnose.py explain --client-slug demo_salon --message-id LC-DEDUP-20260215-104354-4cbfd75e --minutes 60 --limit 1`
  - key facts:
    - `decision_meta.action=escalate`,
    - `decision_trace` содержит `policy_gate:escalate`,
    - `outbox_latest.status=PENDING`
  - log: `/tmp/livecheck_owner_wave4_explain_LC-DEDUP-20260215-104354-4cbfd75e.log`
- KPI snapshot:
  - `python3 ops/console_platform_admin_kpi_snapshot.py --pretty --output /tmp/owner_admin_wave4_kpi_snapshot_20260215-154458.json`
  - runtime: `outbox.pending=1668`, `outbox.failed=849` (`critical`)
  - artifact: `/tmp/owner_admin_wave4_kpi_snapshot_20260215-154458.json`
- DB KPI sample (demo_salon):
  - `outbox_backlog=1667`, `unresolved_cases=3`, `first_response_p90_seconds=0.03`

Files
- Backend:
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/tests/test_console_owner_business.py`
- Frontend:
  - `console-web/src/lib/api-client.ts`
  - `console-web/src/app/business/team-performance/page.tsx`
  - `console-web/src/app/settings/page.tsx`
  - `console-web/src/app/subscription/page.tsx`
  - `console-web/e2e/smoke.spec.ts`
  - `console-web/e2e/owner-admin-business.spec.ts`

Result
- Owner/Admin получил практический action-loop:
  - видит риск в Team KPI -> может сразу применить быстрый профиль,
  - на Settings не перегружен техдеталями,
  - на Subscription видит дату следующего списания, риск 80/100 и понятный смысл перерасхода.
