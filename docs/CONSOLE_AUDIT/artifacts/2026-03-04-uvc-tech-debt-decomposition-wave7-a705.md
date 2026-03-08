# UVC Tech Debt Decomposition Wave7 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE7-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-04`

Goal
- Continue bounded decomposition after closure-review2 without runtime behavior changes.
- Reduce monolith blast-radius for `UX-11`/`UX-12` by extracting one backend and one frontend stateful orchestration slice.

What changed
- Backend (`UX-11`): extracted membership/role state orchestration helpers from `truffles-api/app/routers/console.py` into `truffles-api/app/services/console_membership_state.py` and rewired router imports/call-sites.
- Backend tests: added deterministic module coverage `truffles-api/tests/test_console_membership_state.py`.
- Frontend (`UX-12`): extracted wizard state lifecycle/bootstrap/hydration helpers into `console-web/src/components/provisioning-wizard-state.ts` and rewired `ProvisioningWizard.tsx` effects/initializers.

LOC impact
- `truffles-api/app/routers/console.py`: `24743 -> 24603` (`-140`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4617 -> 4544` (`-73`)

Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> `24603`, `4544`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_membership_state.py truffles-api/tests/test_console_membership_state.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py` -> `30 passed`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-state.ts --file e2e/platform-admin.spec.ts` -> `No ESLint warnings or errors`
- `cd console-web && npm run build` -> `pass`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"` -> `26 passed`

Residual
- `UX-11`/`UX-12` remain open with reduced blast-radius; closure decision deferred to `UVC-UX-TECH-DEBT-DECOMPOSITION-FINAL-REVIEW3-A705` on merged-main evidence.
