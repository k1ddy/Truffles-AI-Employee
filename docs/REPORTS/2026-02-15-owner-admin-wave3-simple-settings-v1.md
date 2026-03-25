# Owner/Admin Wave-3 Implementation Report (Simple Settings + Explainability)

Date
- 2026-02-15

Scope
- Complete owner/admin control loop after Wave-2 by adding:
  - simple SLA settings surface in business language,
  - explainability guidance for non-technical owners/admins,
  - backend correctness fix for `PATCH /console/v1/settings`,
  - dedicated owner/admin e2e smoke coverage,
  - live-check evidence with trace/meta.

Delivered
- Backend fix for `PATCH /console/v1/settings`:
  - request fields now map to persisted model columns:
    - `reminder_1_minutes` -> `client_settings.reminder_timeout_1`
    - `reminder_2_minutes` -> `client_settings.reminder_timeout_2`
    - `escalation_timeout_minutes` -> `client_settings.auto_close_timeout`
  - added range and order validation:
    - `reminder_1_minutes`: 5-60
    - `reminder_2_minutes`: 30-180
    - `escalation_timeout_minutes`: 30-360
    - ordering: `reminder_1 < reminder_2 < escalation_timeout`
- Backend deterministic tests:
  - mapping correctness test,
  - invalid range/order tests.
- Frontend Wave-3 settings UX:
  - simple profile presets (`Быстрый сервис`, `Сбалансированный`, `Бережный к команде`),
  - manual inputs for reminder1/reminder2/escalation,
  - save action via `PATCH /console/v1/settings`,
  - explainability block with business impact wording.
- Owner/admin e2e smoke suite extension:
  - new test for simple settings + explainability surface.

Live-check evidence
- Suite run:
  - `TEST_MODE=1 python3 ops/diagnose.py livecheck-auto --suite ca10-outbox --client-slug demo_salon --base-url http://localhost:8000 --noise none --reset-before-suite --poll-timeout 30 --timeout 20`
- Result highlights:
  - `conversation_id=d9d1d29d-e082-4c04-8c38-bb68093013f2`
  - `message_id=LC-DEDUP-20260215-093909-5a48bffa`
  - `outbox_count=1`, `outbox_status=PENDING`
- Explain evidence:
  - `python3 ops/diagnose.py explain --client-slug demo_salon --message-id LC-DEDUP-20260215-093909-5a48bffa --minutes 60 --limit 1`
  - `decision_meta.action=escalate`, `decision_meta.intent=reschedule`, `decision_meta.source=policy_pack`
  - `decision_trace` includes `policy_gate:escalate`
  - `outbox_latest.status=PENDING`
- Log artifacts:
  - `/tmp/livecheck_owner_wave2_20260215-143909.log`
  - `/tmp/livecheck_owner_wave2_explain_LC-DEDUP-20260215-093909-5a48bffa.log`

Contracts and touched files
- Backend:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/tests/test_console_owner_business.py`
- Frontend:
  - `console-web/src/app/settings/page.tsx`
  - `console-web/e2e/owner-admin-business.spec.ts`
- Docs:
  - `docs/CONSOLE_AUDIT/pages/settings.md`
  - `docs/CONSOLE_AUDIT/UX_BACKLOG.md`

Validation
- `ruff check truffles-api/app/routers/console.py truffles-api/tests/test_console_owner_business.py`
- `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_rbac.py` -> `52 passed`
- `npm --prefix console-web run lint` -> no ESLint warnings/errors
- `npm --prefix console-web run test:e2e:smoke -- --list` -> includes new owner/admin Wave-3 smoke test

Result
- Owner/Admin now has a practical “configure-and-understand” loop in Console Plane:
  - can set key SLA timers without technical knowledge,
  - can understand business impact before applying settings,
  - can trust that saved values are persisted into runtime-effective fields.
