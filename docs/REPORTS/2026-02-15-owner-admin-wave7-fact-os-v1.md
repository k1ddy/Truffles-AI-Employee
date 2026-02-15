# Owner/Admin Wave-7 Report (Fact Contract Layer + Owner Operating System)

Date
- 2026-02-15

Goal
- Закрыть два блока для масштабирования owner/admin control-plane без выдуманных данных:
  1. Fact Contract Layer для KPI (явное происхождение и качество каждого числа).
  2. Owner Operating System как server-driven контур (`preview/apply/rollback/impact`) вместо client-only пресетов.

Delivered
- Fact Contract Layer:
  - Добавлены метаданные фактов `kind/source/as_of/scope/sample_size/note` в owner/admin KPI API:
    - `GET /business/summary`
    - `GET /subscription/summary`
    - `GET /business/data-trust`
    - `GET /business/team-performance`
  - UI owner/admin страниц показывает fact-confidence строку под KPI-картами:
    - `console-web/src/app/business/page.tsx`
    - `console-web/src/app/subscription/page.tsx`
    - `console-web/src/app/business/data-trust/page.tsx`
    - `console-web/src/app/business/team-performance/page.tsx`
  - `GET /health` больше не возвращает фиктивный `redis="connected"`; статус redis теперь fact-based (`connected`/`error`/`unknown`).
- Owner Operating System (server-driven):
  - Добавлены endpoint'ы:
    - `POST /business/operations/owner-mode/preview`
    - `POST /business/operations/owner-mode/apply`
    - `POST /business/operations/owner-mode/rollback`
    - `GET /business/operations/{operation_id}/impact`
  - Реализованы режимы `capture_leads | stable_quality | team_protection`.
  - Применение режима пишет server snapshot + due-at check в audit payload и поддерживает rollback к previous settings.
  - Settings + Team Performance переведены на server-operation flow с impact/rollback действиями.
- Contract/Test coverage:
  - OpenAPI расширен новыми схемами и путями (`MetricFactMeta`, owner operation models + paths).
  - Backend tests расширены для owner operation flows и helpers.
  - Smoke owner/admin suite расширен проверками operation surfaces.

Validation
- Backend:
  - `ruff check truffles-api/app/routers/console.py truffles-api/app/schemas/console.py truffles-api/tests/test_console_owner_business.py` -> OK.
  - `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py` -> `62 passed`.
- Frontend:
  - `npm --prefix console-web run lint` -> OK.
  - `npm --prefix console-web run build` -> OK.
  - `npm --prefix console-web run test:e2e:smoke -- --list` -> owner/admin smoke surfaces listed.

Runtime Evidence
- Owner/Admin control-loop (`T+0`):
  - command: `python3 ops/owner_admin_control_loop.py --mode t0 --client-slug demo_salon --run-id owner-admin-wave7-t0 --print-json`
  - summary artifact: `/tmp/owner_admin_wave7_t0.json`
  - snapshot artifact: `/tmp/owner_admin_control_loop/owner-admin-wave7-t0/demo_salon_t0.json`
  - facts: `guard_status=critical`, `outbox_backlog=1692`, gate exit `2`.
- Owner/Admin control-loop (`T+24` replay vs baseline):
  - command: `python3 ops/owner_admin_control_loop.py --mode t24 --client-slug demo_salon --run-id owner-admin-wave7-t24 --baseline /tmp/owner_admin_control_loop/owner-admin-wave7-t0/demo_salon_t0.json --print-json`
  - summary artifact: `/tmp/owner_admin_wave7_t24.json`
  - snapshot artifact: `/tmp/owner_admin_control_loop/owner-admin-wave7-t24/demo_salon_t24.json`
  - facts: `guard_status=critical`, `impact.summary=mixed_or_stable`, gate exit `2`.
- Owner operation preview/apply payload evidence (local endpoint harness):
  - artifacts:
    - `/tmp/owner_admin_wave7_apply_preview.json`
    - `/tmp/owner_admin_wave7_apply_result.json`
  - verified fields:
    - `mode=capture_leads`,
    - SLA patch `5/30/60`,
    - baseline snapshot present,
    - `metric_meta` present per metric with source/scope/as_of/sample_size,
    - `impact_check_due_at` returned by apply response.

Result
- Owner/Admin pages теперь показывают только объяснимые KPI (с machine-readable provenance), а действия режима SLA переведены в server contract с rollback/impact, пригодный для массового использования.
- Слой прозрачности и управляемости закрыт для Wave-7, но операционный bottleneck остаётся: backlog guard в runtime всё ещё `critical`.
