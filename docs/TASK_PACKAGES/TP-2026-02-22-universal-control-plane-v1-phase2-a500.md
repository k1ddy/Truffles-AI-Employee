# TP-2026-02-22-universal-control-plane-v1-phase2-a500

## Название/цель
Universal Control Plane v1 / Phase 2 (slice 1): усилить tenant/RBAC boundary так, чтобы tenant-hierarchy write операции (`company/client lifecycle`) выполнялись только ролью `platform_admin`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/MULTI_TENANT.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase1-a500.md`

## Invariant
- Tenant isolation fail-closed.
- Никакой деградации существующих branch-scoped provisioning flow.
- Все write операции в tenant hierarchy остаются auditable.

## Scope
- API hardening: `create/update company`, `create/update/archive/restore client` -> platform_admin-only.
- Add deterministic tests proving deny for non-platform roles.
- Canon sync for tenant hierarchy write governance.
- Phase 2 slice report with FACT/GAP and risks.

## Out of scope
- Полный RBAC rework всех `/admin/*` endpoints.
- Изменение branch-level onboarding/branch change flows.
- Runtime decision-core behavior.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_admin_provisioning.py`
- `SPECS/CONTROL_PLANE.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase2-a500.md`

## Plan (1..N)
1. Analysis gate baseline: map `/admin/*` role guards for tenant hierarchy endpoints.
2. Add platform-admin hard gate to company/client hierarchy write handlers.
3. Add/adjust deterministic tests for non-platform denial and platform-admin success preservation.
4. Canon sync in Control Plane spec.
5. Run checks and publish phase report.

## DoD
- Owner/admin cannot execute tenant hierarchy write actions.
- Platform-admin happy path for existing provisioning tests remains green.
- Canon explicitly documents tenant hierarchy write restrictions.
- Touched test suite passes.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/tests/test_console_admin_provisioning.py`
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py -k "platform_admin or capabilities or tenant"`
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py`

## Evidence
- Diff in `console.py`, provisioning tests, and spec update.
- Phase 2 report with command outputs.

## Rollback
- Revert phase commit.

## No-go
- Не ослаблять platform_admin ограничения для tenant hierarchy.
- Не трогать core runtime routing/decision behavior.

## Branch / Worktree / Base
- Branch: `feat/2026-02-22-universal-control-plane-v1-a500`
- Worktree: `/home/zhan/worktrees/2026-02-22-universal-control-plane-v1-a500`
- Base: `origin/main`

## Fitness functions impacted
- P1-10 env contract/fail-fast (RBAC fail-closed discipline).
- P2-14 task package gate.
- P2-15 local-first validation gate.

## Risks
- Некоторые owner/admin operational сценарии могли полагаться на client hierarchy write через старую модель; это намеренно ограничено в пользу platform control plane.
