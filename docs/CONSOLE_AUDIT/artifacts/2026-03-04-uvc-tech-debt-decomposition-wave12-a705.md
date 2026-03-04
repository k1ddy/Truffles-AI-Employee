# UVC Tech Debt Decomposition Wave12 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE12-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-04`

Goal
- Continue bounded decomposition after closure-review7 without runtime behavior changes.
- Reduce `UX-11`/`UX-12` blast-radius by moving repeated branch-change orchestration into service layer and extracting autopilot run-state helpers.

What changed
- Backend (`UX-11`): extracted branch-change prepare/validation orchestration from router into `truffles-api/app/services/console_branch_changes.py`:
  - `prepare_branch_change_payload`
- Backend wiring:
  - `truffles-api/app/routers/console.py` now uses shared `_BRANCH_CHANGE_NORMALIZATION_KWARGS` and delegates `draft/validate/publish` payload preparation to service helper.
  - rollback path now reuses the same shared normalization kwargs with `normalize_branch_change_patch` service API.
- Frontend (`UX-12`): extracted autopilot run-state/action helpers from `ProvisioningWizard` into `console-web/src/components/provisioning-wizard-autopilot.ts`:
  - `toggleAutopilotServiceSelection`
  - `buildAutopilotRunState`
  - `buildAutopilotRunValidationError`
- Frontend wiring: `ProvisioningWizard` now delegates autopilot run-eligibility and validation message composition to extracted helpers while preserving existing UX copy and actions.
- Tests:
  - moved branch-change helper assertions to service-level APIs in `truffles-api/tests/test_console_branch_changes.py`.
  - added deterministic coverage for no-op diff detection via `prepare_branch_change_payload`.

LOC impact
- `truffles-api/app/routers/console.py`: `24365 -> 24351` (`-14`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4365 -> 4365` (`0`)

Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> `24351`, `4365`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py` -> `35 passed`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"` -> `13 passed, 23 deselected`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-autopilot.ts --file e2e/platform-admin.spec.ts` -> `No ESLint warnings or errors`
- `cd console-web && npm run build` -> `pass`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "show actionable provisioning guidance for quick-create server errors|deep-link from Tenants action queue to Workspace execute"` -> `2 passed`
- `SESSION_AGENT=a705 scripts/session_check.sh` -> pending final canon sync in this block

Residual
- `UX-11`/`UX-12` remain fail-closed until merged-main closure decision in `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW8-A705`.
