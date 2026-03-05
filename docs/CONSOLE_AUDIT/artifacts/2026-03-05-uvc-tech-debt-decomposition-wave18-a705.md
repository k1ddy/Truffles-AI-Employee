# UVC Tech Debt Decomposition Wave18 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE18-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-05`

Goal
- Continue bounded decomposition after closure-review13 without runtime behavior drift.
- Reduce orchestration concentration for `UX-11/UX-12` by delegating branch-change response assembly and provisioning branch mutation submit-flow into helper boundaries.

What changed
- Backend (`UX-11`): extracted branch-change response assembly helper into `truffles-api/app/services/console_branch_changes.py`:
  - `build_branch_change_response`
- Backend wiring:
  - `truffles-api/app/routers/console.py` now delegates repeated `ConsoleBranchChangeResponse(...)` construction in `get/draft/validate/publish/rollback` handlers to `build_branch_change_response`.
- Backend tests:
  - Extended deterministic service coverage in `truffles-api/tests/test_console_branch_changes.py`:
    - `test_build_branch_change_response_with_branch`
    - `test_build_branch_change_response_without_branch`
- Frontend (`UX-12`): extracted generic branch-mutation submit helper into `console-web/src/components/provisioning-wizard-branch-actions.ts`:
  - `submitBranchMutation`
- Frontend wiring:
  - `console-web/src/components/ProvisioningWizard.tsx` now uses `submitBranchMutation` for:
    - `handleCreateBranch`
    - `handleUpdateBranchDraft`
    - `handleSaveInstance`
    - `handleSaveTelegram`
    - `handleSaveKnowledge`
    - `handleSaveBooking`
  - Removed accidental `clientId` argument in booking-save path while preserving existing mutation payload shape.

LOC impact
- `truffles-api/app/routers/console.py`: `24381 -> 24390` (`+9`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4325 -> 4323` (`-2`)
- Note: wave18 keeps fail-closed focus on ownership transfer + deterministic parity; closure decision remains in closure-review14.

Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> `24390`, `4323`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py` -> `35 passed`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"` -> `27 passed, 23 deselected`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-branch-actions.ts --file e2e/platform-admin.spec.ts` -> `No ESLint warnings or errors`
- `cd console-web && npm run build` -> `pass`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "show actionable provisioning guidance for quick-create server errors|deep-link from Tenants action queue to Workspace execute"` -> `2 passed`
- `SESSION_AGENT=a705 scripts/session_check.sh` -> `Session OK`

Residual
- `UX-11`/`UX-12` remain fail-closed until merged-main closure decision in `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW14-A705`.

