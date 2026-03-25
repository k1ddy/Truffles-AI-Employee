# 2026-02-19 Onboarding Readiness Kernel (a131)

## Scope

- TP: `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-readiness-kernel-a131.md`
- Branch: `feat/2026-02-19-onboarding-readiness-kernel-a131`
- Worktree: `/home/zhan/worktrees/2026-02-19-onboarding-readiness-kernel-a131`

## Delivery

- Added `readiness_kernel` to onboarding scorecard read-model:
  - deterministic blocker codes,
  - next action codes,
  - auto-questions,
  - dimension statuses (`pass`/`warn`/`fail`),
  - shadow hard-gate payload.
- Added feature-flagged hard-gate enforcement in go-live gate path:
  - default remains shadow-only (`ONBOARDING_READINESS_HARD_GATE_ENABLED=false`),
  - hard blocking activates only when flag is enabled.
- Removed duplicate go-live scorecard-check logic by reusing shared gate helper.
- Preserved backward-compatible behavior for tests/mocks when hard-gate is disabled.

## Checks (fact)

- `python3 -m py_compile truffles-api/app/services/onboarding_state.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py`
  - result: pass
- `pytest -q truffles-api/tests/test_console_onboarding_state.py`
  - result: `22 passed`
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "onboarding_scorecard or go_live or require_branch_scorecard"`
  - result: `9 passed, 31 deselected`
- `pytest -q truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_console_access_admin_pr2.py`
  - result: `62 passed`
- `ruff check truffles-api/app/services/onboarding_state.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py truffles-api/tests/test_console_access_admin_pr2.py`
  - result: pass
- `python3 truffles-api/scripts/generate_openapi.py --check`
  - result: pass (`openapi.generated.yaml` regenerated for check, contract drift not detected)

## Behavior contract

- If scorecard is `ready=true` and hard-gate flag is `false`, go-live behavior is unchanged (no new blocking).
- If scorecard is `ready=true` and hard-gate flag is `true`, go-live can be blocked by selected readiness blocker codes.
- `GO_LIVE_GATE_REQUIRED` now carries readiness diagnostic details when readiness kernel is available.
