# TP-2026-02-22-universal-control-plane-v1-phase1-a500

## Название/цель
Universal Control Plane v1 / Phase 1: зафиксировать governance bootstrap и закрыть первый обязательный контрактный разрыв — write/update capabilities в prod допускается только для роли `platform_admin`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/MULTI_TENANT.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-master-a500.md`

## Invariant
- Tenant/RBAC fail-closed.
- Никакой деградации safety/policy/runtime контрактов консультанта.
- Любое capability write-action auditable.

## Scope
- API governance: `PATCH /console/v1/admin/capabilities` -> only `platform_admin`.
- Tests: explicit access-denied for non-platform roles + platform_admin happy-path coverage.
- Canon sync note in Control Plane spec (capabilities write restriction).
- Phase-1 FACT/GAP report.

## Out of scope
- Полный RBAC rework для всех provisioning endpoints.
- Новые capability schema versions.
- Runtime business behavior changes.

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_admin_provisioning.py`
- `SPECS/CONTROL_PLANE.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase1-a500.md`

## Plan (1..N)
1. FACT baseline and contract delta фиксация для capabilities write governance.
2. Backend RBAC change for capabilities patch endpoint.
3. Add/update tests for denied/allowed roles.
4. Update canon text in `SPECS/CONTROL_PLANE.md`.
5. Run targeted checks and produce Phase-1 report.

## DoD
- Non-platform role cannot patch capabilities (`ACCESS_DENIED`).
- Platform admin can patch capabilities path with no regression in existing flow.
- Control plane spec отражает новый governance rule.
- Tests green for touched scope.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/tests/test_console_admin_provisioning.py`
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py -k "capabilities"`
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py`

## Evidence
- Test outputs + code diff.
- Phase report with FACT/GAP and residual risks.

## Rollback
- Revert phase commit.

## No-go
- Не ослаблять права platform_admin на другие critical endpoints.
- Не добавлять owner/admin backdoor для capabilities write.

## Branch / Worktree / Base
- Branch: `feat/2026-02-22-universal-control-plane-v1-a500`
- Worktree: `/home/zhan/worktrees/2026-02-22-universal-control-plane-v1-a500`
- Base: `origin/main`

## Fitness functions impacted
- P1-10 env contract/fail-fast (RBAC gate fail-closed)
- P2-14 task package gate
- P2-15 local-first validation gate

## Risks
- Existing operator привычка owner/admin менять capabilities (изменение поведения API).
- Spec/code drift, если не синхронизировать канон.
