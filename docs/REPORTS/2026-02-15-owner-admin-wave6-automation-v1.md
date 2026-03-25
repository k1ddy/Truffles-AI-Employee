# Owner/Admin Wave-6 Report (Automation + Goal Mode + Knowledge Preflight)

Date
- 2026-02-15

Goal
- Закрыть следующий слой масштабируемости owner/admin control-plane без усложнения UX:
  1. automation wrapper для post-merge control-loop,
  2. goal-first управление настройками в терминах бизнес-результата,
  3. backend safety gate для knowledge publish (validate-first дисциплина).

Delivered
- Control-loop automation:
  - добавлен `ops/owner_admin_control_loop.py`.
  - режимы `--mode t0|t24` запускают snapshot + optional gate + brief + log в единый run-dir.
  - для `t24` поддержан `--baseline` и auto-resolve последнего `t0` snapshot.
- Settings goal-mode:
  - в `console-web/src/app/settings/page.tsx` добавлен блок `settings-goal-mode` с кнопками бизнес-целей:
    - `capture_leads`,
    - `stable_quality`,
    - `team_protection`.
  - цель применяет соответствующий preset и сразу сохраняет SLA-настройки (`PATCH /settings`) с явным toast outcome.
  - smoke suite расширен проверками `settings-goal-mode` и `settings-goal-capture_leads`.
- Knowledge preflight gate:
  - добавлен сервис `truffles-api/app/services/console_knowledge_preflight.py` (`draft_hash`, validate payload builder, recent preflight lookup).
  - `POST /knowledge/validate` теперь пишет `draft_hash` в audit payload.
  - `POST /knowledge/publish` по умолчанию требует свежий matching validate-preflight; иначе `409 KNOWLEDGE_PREFLIGHT_REQUIRED`.
  - request schema расширена полем `skip_preflight_check` (default `false`) для controlled override.
  - frontend knowledge publish обрабатывает `KNOWLEDGE_PREFLIGHT_REQUIRED` и переводит user flow на шаг Validate.

Validation
- Backend:
  - `python3 -m py_compile ops/owner_admin_control_loop.py truffles-api/app/services/console_knowledge_preflight.py` -> OK.
  - `ruff check truffles-api/app/routers/console.py truffles-api/app/services/console_knowledge_preflight.py truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_knowledge_preflight.py` -> OK.
  - `pytest -q truffles-api/tests/test_console_owner_business.py truffles-api/tests/test_console_knowledge_preflight.py truffles-api/tests/test_console_rbac.py` -> `62 passed`.
- Frontend:
  - `npm --prefix console-web run lint` -> OK.
  - `npm --prefix console-web run build` -> OK.
  - `npm --prefix console-web run test:e2e:smoke -- --list` -> owner/admin smoke surfaces listed, including settings goal-mode checks.

Runtime Evidence
- Automation wrapper (`t0`):
  - command: `python3 ops/owner_admin_control_loop.py --mode t0 --client-slug demo_salon --run-id owner-admin-wave6-t0 --print-json`
  - artifacts:
    - `/tmp/owner_admin_control_loop/owner-admin-wave6-t0/demo_salon_t0.json`
    - `/tmp/owner_admin_control_loop/owner-admin-wave6-t0/demo_salon_t0_gate.json`
    - `/tmp/owner_admin_control_loop/owner-admin-wave6-t0/demo_salon_t0_brief.md`
    - `/tmp/owner_admin_control_loop/owner-admin-wave6-t0/demo_salon_t0.log`
  - facts: `guard_status=critical`, `outbox_backlog=1679`, gate exit `2`.
- Automation wrapper (`t24` replay against t0 baseline):
  - command: `python3 ops/owner_admin_control_loop.py --mode t24 --client-slug demo_salon --run-id owner-admin-wave6-t24 --baseline /tmp/owner_admin_control_loop/owner-admin-wave6-t0/demo_salon_t0.json --print-json`
  - artifacts:
    - `/tmp/owner_admin_control_loop/owner-admin-wave6-t24/demo_salon_t24.json`
    - `/tmp/owner_admin_control_loop/owner-admin-wave6-t24/demo_salon_t24_gate.json`
    - `/tmp/owner_admin_control_loop/owner-admin-wave6-t24/demo_salon_t24_brief.md`
    - `/tmp/owner_admin_control_loop/owner-admin-wave6-t24/demo_salon_t24.log`
  - facts: `impact.summary=mixed_or_stable`, `guard_status=critical`, gate exit `2`.

Result
- Owner/Admin surface moved from manual operator playbook to repeatable semi-automation with stable artifacts.
- Settings now support business-goal-first action model without introducing new complex wizard flow.
- Knowledge publish now enforces validate-first discipline at backend contract level, reducing accidental unsafe publish.
- Runtime bottleneck remains operational (outbox backlog critical), now captured by automated gate evidence on both phases.
