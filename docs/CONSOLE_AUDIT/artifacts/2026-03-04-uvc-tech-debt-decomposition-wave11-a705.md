# UVC Tech Debt Decomposition Wave11 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE11-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-04`

Goal
- Continue bounded decomposition after closure-review6 without runtime behavior changes.
- Further reduce `UX-11`/`UX-12` blast-radius by extracting one backend branch-change context/rollback slice and one frontend autopilot slice.

What changed
- Backend (`UX-11`): extracted branch-change context query, rollback-patch assembly, and status-filter normalization from router into `truffles-api/app/services/console_branch_changes.py`:
  - `query_branch_changes_for_context`
  - `get_branch_change_for_context`
  - `build_branch_change_rollback_patch`
  - `normalize_branch_change_status_filter`
- Backend wiring: router now delegates list/get/rollback helper logic to service functions while keeping endpoint contracts and error codes unchanged.
- Frontend (`UX-12`): extracted autopilot derived-state + payload assembly from `console-web/src/components/ProvisioningWizard.tsx` into `console-web/src/components/provisioning-wizard-autopilot.ts`:
  - `deriveAutopilotState`
  - `buildRunAutopilotPayload`
- Frontend wiring: manual checks/messages stay in `ProvisioningWizard`, while payload/derived logic is delegated to extracted helper.

LOC impact
- `truffles-api/app/routers/console.py`: `24366 -> 24365` (`-1`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4423 -> 4365` (`-58`)

Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> `24365`, `4365`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py` -> `35 passed`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"` -> `12 passed, 23 deselected`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-account-actions.ts --file src/components/provisioning-wizard-branch-actions.ts --file src/components/provisioning-wizard-autopilot.ts --file e2e/platform-admin.spec.ts` -> `No ESLint warnings or errors`
- `cd console-web && npm run build` -> `pass`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "show actionable provisioning guidance for quick-create server errors|deep-link from Tenants action queue to Workspace execute"` -> `2 passed`
- `SESSION_AGENT=a705 scripts/session_check.sh` -> `Session OK`

Residual
- `UX-11`/`UX-12` status remains fail-closed until merged-main closure decision in `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW7-A705`.
