# TP-2026-02-08 Membership RBAC UI Completeness (PR-2b, a17)

## Название/цель
Довести PR-2 до операционно полезного уровня для подключенных бизнесов: добавить в Console Team UI создание учеток (owner/admin/manager/support/specialist/viewer) и полноценное управление memberships (list/create/update activate/deactivate/re-scope) без SQL/CLI.

## Canon refs
- `AGENTS.md`
- `STATE.md` (NOW: merged PR-1/PR-2/PR-2.5)
- `STRUCTURE.md`
- `SPECS/CONTROL_PLANE.md` (PR-3 roadmap block, RBAC completeness)
- `docs/REPORTS/2026-02-08-enterprise-fleet-program.md` (PR-3 Membership/RBAC completeness intent)

## Invariant
- Tenant isolation и access checks не ослабляются.
- Team page остается доступной только ролям с `team.read`; write-операции только при `team.write`.
- Backend behavior/API contracts не меняются (только использование уже существующих endpoint'ов).

## Scope
- Frontend (`/team`):
  - Add section for account creation (`/admin/agents`) with client/branch-aware role constraints.
  - Add memberships section (`/admin/memberships`) with list + filters + create + update (`role/scope/is_active/reason`).
  - Add quick activate/deactivate for memberships via `patchMembership` with reason.
- Reuse existing API client methods (`adminApi.createAgent/listMemberships/createMembership/patchMembership`).

## Out of scope
- Новый backend endpoint для bulk create.
- Onboarding conveyor/go-live gate.
- Jobs/bulk fleet ops.

## Touch-list
- `console-web/src/app/team/page.tsx`
- `docs/TASK_PACKAGES/TP-2026-02-08-membership-rbac-ui-pr2b-a17.md`
- `docs/SESSIONS/SESSION-2026-02-08-membership-rbac-ui-pr2b-a17.md`
- `docs/SESSION_INDEX.md`

## Plan
1. Add account create form in Team users tab using existing `/admin/agents`.
2. Add memberships query table + create/update flows using `/admin/memberships` endpoints.
3. Wire state guards (reason required for destructive changes), role/scope UX validation.
4. Run frontend checks (`lint`, `build`) and session checks.

## DoD
- Platform/owner/admin can create user accounts from Team UI without switching to provisioning wizard.
- Memberships are visible and editable (role/scope/active) in Team UI with audit reasons.
- No TypeScript/lint regressions in console-web.

## Checks
- `cd console-web && npm run lint`
- `cd console-web && npm run build`
- `SESSION_AGENT=a17 scripts/session_check.sh`

## Evidence
- `git status -sb`
- `git diff --stat`
- check outputs (lint/build/session_check)
- PR URL

## Rollback
- Revert PR-2b commit.

## No-go
- Не менять backend роуты/схемы в этом PR.
- Не обходить reason-поля для destructive membership updates.
- Не вводить cross-tenant shortcuts в UI.

## Риски/блокеры
- Риск: UX перегрузится большим количеством контролов.
- Митигация: сделать секции компактными (Create Account / Memberships) и безопасные defaults.

## Branch/Worktree
- Branch: `feat/2026-02-08-membership-rbac-ui-pr2b-a17`
- Worktree: `/home/zhan/worktrees/2026-02-08-membership-rbac-ui-pr2b-a17`
- Base ref: `origin/main`
- Merge policy: merge commit через PR (без rebase)
- Cleanup: после merge удалить branch/worktree через Brain/Top Architect

## Fitness Functions impacted
- P2-14 (`PR Task Package gate`): соблюдается через TP + session artifacts.
- P0/P1 core pipeline fitness functions не затрагиваются (UI-only scope).
