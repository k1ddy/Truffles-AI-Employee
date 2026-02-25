# TP-2026-02-22-universal-control-plane-v1-phase2-slice2-impl1-a500

## Название/цель
Universal Control Plane v1 / Phase 2 slice 2 (implementation wave 1): зафиксировать platform-admin-only доступ к governance catalogs (`onboarding blueprints`, `reference packs list`) с тестовым покрытием.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `SPECS/CONTROL_PLANE.md`
- `SPECS/MULTI_TENANT.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/TASK_PACKAGES/TP-2026-02-22-universal-control-plane-v1-phase2-slice2-a500.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase2-slice2-analysis-a500.md`

## Invariant
- Governance catalog endpoints не должны быть writable/readable вне platform-admin policy.
- Existing platform-admin happy-path для blueprints/reference packs не должен деградировать.

## Scope
- Add explicit `_require_platform_admin(context)` to:
  - `GET /admin/onboarding-blueprints`
  - `GET /admin/reference-packs`
- Add deny tests for owner role.
- Canon sync for new governance boundary.

## Out of scope
- Остальные slice 2 endpoints (`webhook-secret`, `onboarding-contract`, identity, branch workflows).

## Touch-list
- `truffles-api/app/routers/console.py`
- `truffles-api/tests/test_console_onboarding_contract_api.py`
- `SPECS/CONTROL_PLANE.md`
- `docs/REPORTS/2026-02-22-universal-control-plane-v1-phase2-slice2-impl1-a500.md`

## Plan (1..N)
1. Apply platform-admin hard gate to two governance catalog read endpoints.
2. Add deterministic deny tests for non-platform roles.
3. Run targeted and regression checks.
4. Update phase docs and canon notes.

## DoD
- Owner/admin cannot read onboarding blueprints and reference pack catalog through `/admin/*`.
- Platform-admin tests for these endpoints remain green.
- Canon reflects governance-catalog platform-only rule.

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/tests/test_console_onboarding_contract_api.py`
- `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py`
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "list_onboarding_blueprints"`
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py`

## Evidence
- Diff + test outputs + phase report.

## Rollback
- Revert implementation wave commit.

## No-go
- Не расширять scope в сторону runtime decision logic.
- Не ослаблять already-locked platform-admin boundaries from Phase 1/2 slice 1.

## Branch / Worktree / Base
- Branch: `feat/2026-02-22-universal-control-plane-v1-a500`
- Worktree: `/home/zhan/worktrees/2026-02-22-universal-control-plane-v1-a500`
- Base: `origin/main`
