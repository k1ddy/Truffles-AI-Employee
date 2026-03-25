# UVC Tech Debt Decomposition Wave6 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE6-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-04`

Goal
- Continue bounded decomposition after closure-review without runtime behavior change.
- Reduce monolith blast-radius for `UX-11`/`UX-12` via one backend and one frontend extraction slice.

What changed
- Backend (`UX-11`): extracted fleet lifecycle/payment/service state resolver layer from `truffles-api/app/routers/console.py` into `truffles-api/app/services/console_fleet_state.py` and rewired router call-sites/imports.
- Backend tests: added deterministic module tests `truffles-api/tests/test_console_fleet_state.py`.
- Frontend (`UX-12`): extracted provisioning JSON payload/build/read logic (`billing_info`, `working_hours`, `booking_settings`) from `console-web/src/components/ProvisioningWizard.tsx` into `console-web/src/components/provisioning-wizard-json-payloads.ts` and rewired handlers.

LOC impact
- `truffles-api/app/routers/console.py`: `24897 -> 24743` (`-154`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4679 -> 4617` (`-62`)

Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> `24743`, `4617`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_fleet_state.py truffles-api/tests/test_console_fleet_state.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py` -> `24 passed`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-json-payloads.ts --file src/components/provisioning-wizard-shell-panels.tsx --file src/components/provisioning-wizard-readiness-panel.tsx --file src/components/provisioning-wizard-derived.ts --file src/components/provisioning-wizard-utils.ts` -> `No ESLint warnings or errors`
- `cd console-web && npm run build` -> `pass`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"` -> `26 passed`
- `SESSION_AGENT=a705 scripts/session_check.sh` -> `Session OK`

Residual
- `UX-11`/`UX-12` remain open with reduced blast-radius; closure decision deferred to `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW2-A705` after wave6 merge evidence on `main`.
