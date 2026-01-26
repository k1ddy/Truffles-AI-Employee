Title: Control Plane TP‑B — Onboarding state machine (server‑side)
Owner: Top Architect
Date: 2026-01-26

Canon refs:
- SPECS/CONTROL_PLANE.md (Provisioning flow + Go/No‑Go)
- SPECS/MULTI_TENANT.md (tenant context + fail‑closed)
- STRATEGY/REQUIREMENTS.md (quality + safety gates)
- docs/CONSOLE_GUIDE.md (Wizard UI + endpoints)
- STATE.md (Control Plane roadmap)

Dependencies:
- TP‑A RBAC matrix enforcement (PR #383 merged).
- Phase 2 UI Provisioning Wizard (PR #348 merged).
- Company→Client→Branch selection gate (PR #376 merged).

Invariant:
- Fail‑closed tenant context and RBAC gates must remain.
- No changes to core pipeline (webhook/LLM routing).
- No silent enablement of capabilities; only explicit owner/admin actions.

Scope:
- Ввести server‑side state machine онбординга (Branch‑scoped, Web‑first).
- Добавить централизованную проверку последовательности шагов (order enforcement).
- Экспортировать статус онбординга в Console API для Wizard.
- Обновить UI Wizard, чтобы шаги блокировались серверным статусом.
- Тесты на переходы и ошибки “step‑out‑of‑order”.

Out of scope:
- Новые интеграции/каналы.
- Изменения Knowledge pipeline (это TP‑C/DEC‑014 зона).
- Переписывание существующих admin endpoints.

Touch-list (files/tables):
- truffles-api/app/models/branch.py (onboarding_state, timestamps)
- truffles-api/migrations/0xx_onboarding_state.sql
- truffles-api/app/services/onboarding_state.py (state machine + guards)
- truffles-api/app/routers/console.py (provisioning + onboarding endpoints)
- truffles-api/app/schemas/console.py (status/step schemas)
- console-web/src/app/settings/page.tsx (Wizard gating via API)
- console-web/src/lib/api-client.ts (new endpoints)
- contracts/console_api/openapi.v1.yaml (new endpoints/errors)
- truffles-api/tests/test_console_onboarding_state.py (new)
- SPECS/CONTROL_PLANE.md (state machine spec)
- docs/CONSOLE_GUIDE.md (updated flow + errors)
- STATE.md, STRUCTURE.md

Plan:
1) Зафиксировать state machine и шаги (branch‑scoped):
   - branch_draft → integrations → team → telegram → knowledge → booking → go_no_go.
   - Шаги могут быть SKIPPED по capabilities (explicit).
2) Добавить хранение состояния:
   - `branches.onboarding_state` (enum) + `onboarding_updated_at`.
3) Сервис guard‑ов:
   - `can_transition(from, to)` + `validate_prerequisites(step)`.
   - Fail‑closed: если шаг не готов — 409 `ONBOARDING_STEP_REQUIRED`.
4) API:
   - `GET /console/v1/onboarding/status?branch_id=...`
   - `POST /console/v1/onboarding/advance` (owner/admin only).
   - Привязать provisioning endpoints к guards.
5) UI:
   - Wizard читает status; кнопки шага disabled, если step locked.
6) Тесты:
   - позитивные переходы + запрет skip;
   - branch‑scoped manager без шагов → 409.
7) Документация + STATE.

DoD:
- Порядок шагов enforced server‑side (API errors на out‑of‑order).
- Wizard блокирует шаги и показывает причину.
- Тесты на transitions проходят.
- Документация/канон обновлены.

Checks:
- pytest -q truffles-api/tests/test_console_onboarding_state.py
- npm --prefix console-web run lint
- npm --prefix console-web run generate:api (если OpenAPI менялся)

Evidence:
- CI run URL + test output.
- Обновление STATE.md с PR/CI evidence.

Rollback:
- Revert PR + rollback migration.

No-go:
- Не менять core pipeline.
- Не разрешать step‑skip без explicit allowlist.

Branch/Worktree:
- Branch: feat/control-plane-onboarding-state-machine
- Worktree: /home/zhan/worktrees/control-plane-onboarding-state-machine
- Base: origin/main
- Merge policy: PR only, no rebase
- Cleanup: delete branch/worktree after merge
