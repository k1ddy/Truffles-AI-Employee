# 2026-02-19 Onboarding Hard-Gate Rollout (A131)

## Scope

- Plan step: `1` (rollout acceptance for onboarding hard-gate).
- Branch: `feat/2026-02-19-onboarding-any-niche-step123-a131`
- Worktree: `/home/zhan/worktrees/2026-02-19-onboarding-any-niche-step123-a131`

## Implementation

- Added rollout diagnostics command:
  - `python3 ops/diagnose.py onboarding-hard-gate-rollout ...`
- Command projects go-live blocking for modes:
  - `actual`
  - `shadow`
  - `canary`
  - `enforced`
- Added rollout projection fields in fleet rows:
  - `readiness_status`
  - `readiness_blocker_codes`
  - `hard_gate_blockers`
  - `hard_gate_enforced`
  - `projected_status`
  - `projected_blockers`
- Added deterministic helper tests for rollout mode evaluation and projection.

## Validation

- `python3 -m py_compile ops/diagnose.py` -> `0`
- `ruff check ops/diagnose.py truffles-api/tests/test_diagnose_onboarding_fleet.py truffles-api/tests/test_console_openapi_calendar_contract.py truffles-api/tests/test_console_openapi_ops_reminder_contract.py` -> `0`
- `pytest -q truffles-api/tests/test_diagnose_onboarding_fleet.py` -> `18 passed`
- `pytest -q truffles-api/tests/test_console_openapi_calendar_contract.py truffles-api/tests/test_console_openapi_ops_reminder_contract.py` -> `7 passed`
- `python3 truffles-api/scripts/generate_openapi.py --check` -> `0`

## Rollout Evidence

Artifacts:
- `/tmp/onboarding_hard_gate_rollout_a131/actual.json`
- `/tmp/onboarding_hard_gate_rollout_a131/shadow.json`
- `/tmp/onboarding_hard_gate_rollout_a131/canary.json`
- `/tmp/onboarding_hard_gate_rollout_a131/enforced.json`

Snapshot facts (`demo_salon/main`, branch `b7f75692-951e-421a-aae6-f5db97394799`):
- `actual`: `active_blocked=0`
- `shadow`: `active_blocked=0`
- `canary` (input canary includes `main`): `active_blocked=1`, `projected_status=blocked_hard_gate`
- `enforced`: `active_blocked=1`, `projected_status=blocked_hard_gate`
- hard-gate blockers observed: `delivery:failed_24h_critical`, `traffic:whatsapp_capability_mismatch`

## Result

- Step `1` rollout acceptance tooling is operational and evidence-backed.
- Shadow mode keeps branch pass.
- Canary/enforced modes deterministically surface blockers before full rollout.
