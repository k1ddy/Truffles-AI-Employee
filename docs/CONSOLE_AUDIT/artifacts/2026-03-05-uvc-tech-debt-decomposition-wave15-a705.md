# UVC Tech Debt Decomposition Wave15 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE15-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-05`

Goal
- Continue bounded decomposition after closure-review10 without runtime behavior drift.
- Reduce orchestration concentration for `UX-11/UX-12` by delegating repeated state-transition and go-live validation logic into service/helper modules.

What changed
- Backend (`UX-11`): extracted remaining branch-change state transition helpers from router to service layer `truffles-api/app/services/console_branch_changes.py`:
  - `apply_branch_change_publish_runtime_error_state`
  - `apply_branch_change_rollback_failed_state`
  - `apply_branch_change_rolled_back_state`
- Backend wiring:
  - `truffles-api/app/routers/console.py` (`publish_branch_change`, `rollback_branch_change`) now delegates publish/rollback failure and rollback-complete state mutation to service helpers.
- Backend tests:
  - Added deterministic service-level coverage in `truffles-api/tests/test_console_branch_changes.py`:
    - `test_apply_branch_change_publish_runtime_error_state_sets_publish_failed`
    - `test_apply_branch_change_rollback_failed_state_sets_error`
    - `test_apply_branch_change_rolled_back_state_sets_snapshot_and_actor`
- Frontend (`UX-12`): extracted go-live decision payload validation from `ProvisioningWizard` into `console-web/src/components/provisioning-wizard-branch-actions.ts`:
  - `buildGoLiveDecisionPayload`
  - `buildGoLiveWaiverPayload`
- Frontend wiring:
  - `ProvisioningWizard` now uses shared go-live payload builders for `approve/reject/waive` actions and preserves existing validation texts/copy.

LOC impact
- `truffles-api/app/routers/console.py`: `24358 -> 24376` (`+18`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4356 -> 4349` (`-7`)
- Note: wave15 keeps fail-closed quality focus on ownership transfer and deterministic parity; closure decision remains in closure-review11.

Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> `24376`, `4349`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py` -> `35 passed`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"` -> `21 passed, 23 deselected`
- `cd truffles-api && ruff check app/routers/console.py app/services/console_branch_changes.py tests/test_console_branch_changes.py` -> `All checks passed`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-branch-actions.ts` -> `No ESLint warnings or errors`
- `cd console-web && npm run build` -> `pass`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "show actionable provisioning guidance for quick-create server errors|deep-link from Tenants action queue to Workspace execute"` -> `2 passed`
- `SESSION_AGENT=a705 scripts/session_check.sh` -> `Session OK`

Residual
- `UX-11`/`UX-12` remain fail-closed until merged-main closure decision in `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW11-A705`.
