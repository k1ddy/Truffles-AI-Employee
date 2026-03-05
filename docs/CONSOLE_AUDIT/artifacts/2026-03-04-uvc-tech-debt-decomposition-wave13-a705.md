# UVC Tech Debt Decomposition Wave13 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE13-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-05`

Goal
- Continue bounded decomposition after closure-review8 without runtime behavior drift.
- Reduce `UX-11`/`UX-12` orchestration concentration in existing router/wizard surfaces (no new tabs/routes).

What changed
- Backend (`UX-11`): extracted branch-change list orchestration from `console.py` into service layer `truffles-api/app/services/console_branch_changes.py`:
  - `build_branch_change_list_response`
- Backend wiring:
  - `truffles-api/app/routers/console.py` `list_branch_changes` now delegates pagination/status/cursor response composition to `_build_branch_change_list_response`.
- Backend tests:
  - Added deterministic service-level coverage in `truffles-api/tests/test_console_branch_changes.py`:
    - `test_build_branch_change_list_response_builds_page_and_cursor`
    - `test_build_branch_change_list_response_rejects_invalid_status`
- Frontend (`UX-12`): extracted autopilot success mutation sync orchestration from `ProvisioningWizard` into `console-web/src/components/provisioning-wizard-autopilot.ts`:
  - `syncAutopilotMutationSuccess`
- Frontend wiring:
  - `ProvisioningWizard` now delegates state synchronization on `runAutopilotMutation.onSuccess` to extracted helper, preserving existing UX copy, query invalidation flow, and deep-link behavior.

LOC impact
- `truffles-api/app/routers/console.py`: `24365 -> 24354` (`-11`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4365 -> 4351` (`-14`)

Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> `24354`, `4351`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py` -> `35 passed`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"` -> `15 passed, 23 deselected`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-autopilot.ts --file e2e/platform-admin.spec.ts` -> `No ESLint warnings or errors`
- `cd console-web && npm run build` -> `pass`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "show actionable provisioning guidance for quick-create server errors|deep-link from Tenants action queue to Workspace execute"` -> `2 passed`
- `SESSION_AGENT=a705 scripts/session_check.sh` -> `Session OK`

Residual
- `UX-11`/`UX-12` remain fail-closed until merged-main closure decision in `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW9-A705`.
