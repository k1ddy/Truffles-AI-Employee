# TP-2026-02-09 PR-3A Onboarding Go-Live Gate (a20)

## Название/цель
Сделать `go_no_go` в Console реальным release-gate для branch: без explicit go-live approval (или валидного waiver с TTL) branch нельзя активировать.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: onboarding state machine уже есть, но go-live gate остаётся advisory)
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/SYSTEM_REFERENCE.md`

## Invariant
- Tenant isolation и текущие RBAC-права не ослабляются.
- Onboarding step-order (`ONBOARDING_STEP_REQUIRED`) остается рабочим и совместимым.
- Активация branch fail-closed: при сомнении gate блокирует go-live.

## Scope
- Backend:
  - ввести явный branch go-live gate state + audit metadata;
  - добавить admin actions для approve/reject/waive (с TTL);
  - запретить `is_active=true` без `approved` или active waiver;
  - вернуть в API/contract диагностические причины блокировки.
- Console UI:
  - показать gate state в provisioning (`Go/No-Go`) и действия approve/reject/waive.
- Tests:
  - unit/API tests на gate enforcement + waiver TTL + guardrails.

## Out of scope
- Полный коммерческий policy engine (`payment_overdue` orchestration для всех операций).
- Массовый onboarding conveyor redesign (intake/provision/publish end-to-end).
- Legacy `/admin/*` cutover.

## Touch-list
- `truffles-api/migrations/028_add_branch_go_live_gate.sql`
- `truffles-api/app/models/branch.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_access_admin_pr2.py`
- `truffles-api/tests/test_console_onboarding_state.py`
- `contracts/console_api/openapi.v1.yaml`
- `console-web/src/lib/api-client.ts`
- `console-web/src/components/ProvisioningWizard.tsx`
- `docs/TASK_PACKAGES/TP-2026-02-09-pr3a-onboarding-golive-gate-a20.md`
- `docs/SESSIONS/SESSION-2026-02-09-pr3a-onboarding-golive-gate-a20.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Добавить DB/model поля go-live gate и helper-логику проверки (approved/waiver active).
2. Добавить backend API actions: `approve`, `reject`, `waive` с reason/TTL и audit events.
3. Встроить fail-closed check в branch activation path (`/admin/branches/{id}` update + create/autopilot where relevant).
4. Расширить OpenAPI + api-client + provisioning UI для просмотра и управления gate status.
5. Добавить targeted tests и прогнать checks.

## DoD
- Branch activation без approval/active waiver даёт deterministic error (409) с машиночитаемым кодом.
- В Console provisioning видно текущий gate state и кто/когда принял решение.
- Waiver работает только до срока TTL, после истечения gate снова блокирует activation.
- Все новые API задокументированы в OpenAPI и доступны в api-client.
- Тесты на enforcement/waiver проходят.

## Checks
- `cd truffles-api && pytest tests/test_console_access_admin_pr2.py -q`
- `cd truffles-api && pytest tests/test_console_onboarding_state.py -q`
- `cd truffles-api && pytest tests/test_console_tenants_list.py -q`
- `npm --prefix console-web run lint`
- `SESSION_AGENT=a20 scripts/session_check.sh`

## Evidence
- `git status -sb`
- `git diff --stat`
- pytest/lint outputs
- PR URL + CI run URL
- (при изменениях поведения/core) запись в `STATE.md` делает Brain/Top Architect до merge

## Rollback
- Revert PR commit(s) целиком.
- При необходимости rollback migration отдельным SQL (drop added columns / constraints) через согласованный deploy window.

## No-go
- Не разрешать silent auto-approve без audit.
- Не добавлять обходы gate через UI-only проверки.
- Не менять legacy `/admin/*` поведение в этом PR.

## Риски/блокеры
- Риск: заблокируем текущие активные операции у уже живых branch при неинициализированном gate.
- Митигация: безопасный backfill defaults для существующих active branch + explicit test на backward compatibility.

## Branch/Worktree
- Branch: `feat/2026-02-09-pr3a-onboarding-golive-gate-a20`
- Worktree: `/home/zhan/worktrees/2026-02-09-pr3a-onboarding-golive-gate-a20`
- Base ref: `origin/main`
- Merge policy: merge commit via PR (no rebase)
- Cleanup: после merge удалить worktree/branch

## Fitness Functions impacted
- P2-14 (`PR Task Package gate`): соблюдается через TP + session artifacts.
- P2-12 (`No orchestration in entrypoints`): сложная логика gate выносится в helper/service, роутер тонкий.
- P1-10 (`env contract / fail-fast`): не ломаем health/runtime safety; новые проверки deterministic.
