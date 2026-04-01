# UVC Tech Debt Decomposition Wave19 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE19-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-05`

Goal
- Continue bounded decomposition after closure-review14 without runtime behavior drift.
- Reduce orchestration concentration for `UX-11`/`UX-12` by delegating repeated branch-change context resolution and wizard reset-state assembly into helper boundaries.

What changed
- Backend (`UX-11`): extracted branch-change context helper into `truffles-api/app/services/console_branch_changes.py`:
  - `get_branch_for_change_context`
- Backend wiring:
  - `truffles-api/app/routers/console.py` now delegates repeated branch lookup + client-access check in:
    - `validate_branch_change`
    - `publish_branch_change`
    - `rollback_branch_change`
- Backend tests:
  - Extended deterministic service coverage in `truffles-api/tests/test_console_branch_changes.py`:
    - `test_get_branch_for_change_context_requires_access`
    - `test_get_branch_for_change_context_raises_when_branch_missing`
- Frontend (`UX-12`): extracted provisioning reset-state helper into `console-web/src/components/provisioning-wizard-state.ts`:
  - `createProvisioningWizardResetState`
- Frontend wiring:
  - `console-web/src/components/ProvisioningWizard.tsx` now delegates reset assembly to shared helper and resets `branchBootstrap` through the same boundary.

LOC impact
- `truffles-api/app/routers/console.py`: `24390 -> 24396` (`+6`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4323 -> 4296` (`-27`)
- Note: wave19 keeps fail-closed focus on ownership transfer + deterministic parity; closure decision remains in closure-review15.

Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> `24396`, `4296`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py truffles-api/tests/test_console_branch_changes.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py` -> `35 passed`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"` -> `29 passed, 23 deselected`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-branch-actions.ts --file e2e/platform-admin.spec.ts` -> `No ESLint warnings or errors`
- `cd console-web && npm run build` -> `pass`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "show actionable provisioning guidance for quick-create server errors|deep-link from Tenants action queue to Workspace execute"` -> `2 passed`
- `SESSION_AGENT=a705 scripts/session_check.sh` -> `Session OK`

Residual
- `UX-11`/`UX-12` remain fail-closed until merged-main closure decision in `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW15-A705`.
