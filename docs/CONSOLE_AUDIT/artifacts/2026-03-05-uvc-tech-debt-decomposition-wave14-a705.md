# UVC Tech Debt Decomposition Wave14 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE14-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-05`

Goal
- Continue bounded decomposition after closure-review9 without runtime behavior drift.
- Reduce orchestration concentration for `UX-11/UX-12` by delegating repeated mutation/state-transition logic into service/helper modules.

What changed
- Backend (`UX-11`): extracted branch-change validation/publish-failed state transitions from router into service layer `truffles-api/app/services/console_branch_changes.py`:
  - `apply_branch_change_validation_result`
  - `apply_branch_change_publish_failed_state`
- Backend wiring:
  - `truffles-api/app/routers/console.py` (`validate_branch_change`, `publish_branch_change`) now delegates state mutation to extracted service helpers.
- Backend tests:
  - Added deterministic service-level coverage in `truffles-api/tests/test_console_branch_changes.py`:
    - `test_apply_branch_change_validation_result_marks_validated`
    - `test_apply_branch_change_validation_result_marks_draft_on_errors`
    - `test_apply_branch_change_publish_failed_state_sets_error_payload`
- Frontend (`UX-12`): extracted repeated branch mutation success/error orchestration from `ProvisioningWizard` into `console-web/src/components/provisioning-wizard-branch-actions.ts`:
  - `syncBranchMutationSuccess`
  - `handleBranchMutationError`
- Frontend wiring:
  - `ProvisioningWizard` now uses shared callbacks (`applyBranchMutationSuccess`, `handleBranchMutationFailure`) for `patch/approve/reject/waive` flows, preserving UX copy and side effects.

LOC impact
- `truffles-api/app/routers/console.py`: `24354 -> 24358` (`+4`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4355 -> 4356` (`+1`)
- Note: wave14 keeps fail-closed quality focus on ownership transfer and deterministic parity; closure decision remains in closure-review10.

Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> `24358`, `4356`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py` -> `35 passed`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"` -> `18 passed, 23 deselected`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-branch-actions.ts` -> `No ESLint warnings or errors`
- `SESSION_AGENT=a705 scripts/session_check.sh` -> `Session OK`

Residual
- `UX-11`/`UX-12` remain fail-closed until merged-main closure decision in `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW10-A705`.
