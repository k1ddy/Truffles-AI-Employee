# UVC Tech Debt Decomposition Wave4 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE4-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-04`

Goal
- Execute the next bounded decomposition stage for `UX-11`/`UX-12` after closeout.
- Keep runtime behavior, control-tower contracts, and UVC UX ownership unchanged.

What changed
- Backend (`UX-11`): extracted onboarding readiness hard-gate helper slice from `truffles-api/app/routers/console.py` into `truffles-api/app/services/console_onboarding_readiness.py` and rewired router call-sites.
- Added deterministic backend tests for extracted readiness slice: `truffles-api/tests/test_console_onboarding_readiness.py`.
- Frontend (`UX-12`): extracted readiness timeline + scorecard rendering slice from `console-web/src/components/ProvisioningWizard.tsx` into `console-web/src/components/provisioning-wizard-readiness-panel.tsx` and rewired `ProvisioningWizard.tsx`.

LOC impact
- `truffles-api/app/routers/console.py`: `24920 -> 24888` (`-32`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4819 -> 4742` (`-77`)

Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_onboarding_readiness.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_control_tower_program.py` -> `7 passed`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-readiness-panel.tsx --file src/components/provisioning-wizard-derived.ts --file src/components/provisioning-wizard-utils.ts` -> `No ESLint warnings or errors`
- `cd console-web && npm run build` -> `pass`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"` -> `26 passed`
- `SESSION_AGENT=a705 scripts/session_check.sh` -> `Session OK`

Residual
- `UX-11`/`UX-12` remain open with reduced blast radius; final closure decision is deferred to `UVC-UX-TECH-DEBT-DECOMPOSITION-FINAL-CLOSE-A705` after wave4 merge evidence is synced on `main`.
