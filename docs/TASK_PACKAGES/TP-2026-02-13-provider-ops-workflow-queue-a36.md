# TP-2026-02-13-provider-ops-workflow-queue-a36

- Название/цель: Завершить Console-first операционный контур управления ручным ChatFlow lifecycle после merge: (1) фактически подтвердить platform_admin control surface на tenants/integrations в `origin/main`, (2) добавить Provider Ops Workflow actions для `instance_id/webhook/renewal/rebind`, (3) добавить Provider Ops Queue + reminders с обязательным confirmation на mutate-операции.
- Canon refs:
  - `AGENTS.md`
  - `STATE.md` NOW/GAP: Console-first onboarding/support, provider lifecycle manual ops
  - `SPECS/SYSTEM_REFERENCE.md`
  - `STRATEGY/REQUIREMENTS.md`
  - `TECH.md`

## Invariant
- Не ослаблять tenant RBAC (integrations/tenants — platform_admin only).
- Не ослаблять existing go-live/onboarding hard-stop.
- Не ломать `instance_id -> webhook_secret` contract.
- Любая mutating provider-ops операция должна быть audit-traceable и требовать confirmation в execute-mode.

## Scope
- Проверить фактическое покрытие `origin/main` для platform_admin control plane (`/tenants`, `/integrations`, provisioning APIs) и зафиксировать evidence в session log.
- Добавить backend Provider Ops action surface (action-based API) с поддержкой:
  - `start_rebind`
  - `complete_rebind`
  - `renewal_confirmed`
  - `webhook_updated`
- Добавить Provider Ops queue/read endpoint на основе lifecycle/drift сигналов.
- Добавить reminder endpoint и mandatory confirmation на execute-операции.
- Обновить OpenAPI + generated frontend types.
- Добавить UI блок на Integrations для queue/actions/reminder.
- Добавить/обновить тесты (RBAC, API behavior, confirmations, queue selection, UI smoke where applicable).

## Out of scope
- Интеграция с внешним ChatFlow management API (создание/удаление instance/number binding).
- Background scheduler/cron в этом PR (оставляем ручной execute + queue/read).
- Изменение webhook runtime/LLM routing логики.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/tests/test_console_integrations_registry.py`
- `truffles-api/tests/test_console_access_admin_pr2.py`
- `truffles-api/tests/test_console_rbac.py` (если нужно)
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/app/integrations/page.tsx`
- `console-web/src/lib/api-client.ts`
- `console-web/src/types/api.generated.ts`
- `docs/SESSIONS/SESSION-2026-02-13-provider-ops-workflow-a36.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Session bootstrap + fact verification on `origin/main` (platform_admin surfaces, relevant tests).
2. Design & implement provider-ops action API with confirmation-gated execute mode.
3. Implement provider-ops queue/read endpoint and reminder execute endpoint.
4. Wire API contracts + frontend types + Integrations UI panel for actions/queue.
5. Add/update backend/frontend tests for RBAC, confirmations, mutations, queue logic.
6. Run deterministic checks and collect evidence.

## DoD
- Platform admin sees and can operate provider-ops queue/actions from Console Integrations.
- Mutations require confirmation on execute mode and emit audit events.
- Queue lists branches with actionable provider lifecycle risks (`rebind_required`, `expired`, `expiring_soon`, webhook mismatch/drift).
- OpenAPI/types synchronized and targeted tests green.

## Checks
- `pytest -q truffles-api/tests/test_console_integrations_registry.py`
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "integrations or onboarding or provider or confirmation"`
- `pytest -q truffles-api/tests/test_console_*.py`
- `python3 truffles-api/scripts/generate_openapi.py --check`
- `npm --prefix console-web run generate:api`
- `npm --prefix console-web run lint -- --file src/app/integrations/page.tsx --file src/lib/api-client.ts`

## Evidence
- `git status -sb`
- `git diff --stat`
- Check command outputs
- API/contract/UI references with changed files
- Session log + session index updates

## Rollback
- `git revert COMMIT_SHA`
- Быстрый rollback: revert provider-ops endpoints/UI while preserving existing integrations lifecycle read-only surface.

## No-go
- Не добавлять bypass mutate без confirmation.
- Не использовать ChatFlow-side assumptions как auto-fact без подтвержденного input.
- Не трогать unrelated runtime booking/decision flows.

## Branch / Worktree
- Branch: `feat/2026-02-13-provider-ops-workflow-a36`
- Worktree: `/home/zhan/worktrees/2026-02-13-provider-ops-workflow-a36`
- Base ref: `origin/main`
- Merge policy: merge only (no rebase)
- Cleanup: Brain/Top Architect после merge

## Риски/блокеры
- Объем OpenAPI/typegen/UI diff требует строгого контроля контрактов.
- Нужна аккуратная backward compatibility для Integrations UI.
- Возможны существующие локальные незакомиченные файлы в root-worktree; работа только в отдельном session worktree.
