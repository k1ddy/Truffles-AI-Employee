# UVC Tech Debt Decomposition Wave17 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE17-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-05`

Goal
- Continue bounded decomposition after closure-review12 without runtime behavior drift.
- Reduce orchestration concentration for `UX-11/UX-12` by delegating rollback normalization and go-live submit orchestration into helper/service modules.

What changed
- Backend (`UX-11`): extracted rollback payload normalization wrapper into `truffles-api/app/services/console_branch_changes.py`:
  - `prepare_branch_change_rollback_payload`
- Backend wiring:
  - `truffles-api/app/routers/console.py` (`rollback_branch_change`) now delegates rollback normalization try/except/error mapping to `prepare_branch_change_rollback_payload`.
- Backend tests:
  - Extended deterministic service coverage in `truffles-api/tests/test_console_branch_changes.py`:
    - `test_prepare_branch_change_rollback_payload_normalizes_patch`
    - `test_prepare_branch_change_rollback_payload_maps_validation_error`
- Frontend (`UX-12`): extracted go-live submit orchestration into `console-web/src/components/provisioning-wizard-branch-actions.ts`:
  - `submitGoLiveDecisionMutation`
  - `submitGoLiveWaiverMutation`
- Frontend wiring:
  - `console-web/src/components/ProvisioningWizard.tsx` now uses `submitGoLiveDecisionMutation` for approve/reject and `submitGoLiveWaiverMutation` for waiver; validation copy and branch-gate behavior are preserved.

LOC impact
- `truffles-api/app/routers/console.py`: `24380 -> 24381` (`+1`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4338 -> 4325` (`-13`)
- Note: wave17 keeps fail-closed quality focus on ownership transfer and deterministic parity; closure decision remains in closure-review13.

Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> `24381`, `4325`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py` -> `35 passed`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"` -> `25 passed, 23 deselected`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-branch-actions.ts --file e2e/platform-admin.spec.ts` -> `No ESLint warnings or errors`
- `cd console-web && npm run build` -> `pass`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "show actionable provisioning guidance for quick-create server errors|deep-link from Tenants action queue to Workspace execute"` -> `2 passed`
- `SESSION_AGENT=a705 scripts/session_check.sh` -> `Session OK`

Residual
- `UX-11`/`UX-12` remain fail-closed until merged-main closure decision in `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW13-A705`.
