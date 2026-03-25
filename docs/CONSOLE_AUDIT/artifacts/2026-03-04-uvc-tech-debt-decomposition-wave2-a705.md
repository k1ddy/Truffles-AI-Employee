# UVC Tech Debt Decomposition Wave2 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE2-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-04`

Goal
- Continue structural decomposition for `UX-11`/`UX-12` with behavior-preserving extraction only.
- Keep existing UVC UX ownership and contracts unchanged.

What changed
- Backend (`UX-11`): extracted control-tower pure helper layer from `console.py` into `truffles-api/app/services/console_control_tower_utils.py` and rewired router imports.
- Frontend (`UX-12`): extracted provisioning domain lexicon/field-guide/formatters from `ProvisioningWizard.tsx` into `console-web/src/components/provisioning-wizard-domain.ts` and rewired component imports.
- Added deterministic backend tests for extracted module: `truffles-api/tests/test_console_control_tower_utils.py`.

LOC impact
- `truffles-api/app/routers/console.py`: `25370 -> 25143` (`-227`)
- `console-web/src/components/ProvisioningWizard.tsx`: `5332 -> 4911` (`-421`)

Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_control_tower_utils.py truffles-api/tests/test_console_control_tower_utils.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_control_tower_utils.py` -> `5 passed`
- `pytest -q truffles-api/tests/test_console_owner_business.py -k "control_tower_issue_counts or migration_wave_detail_filters_actions_and_counts or migration_program_aggregates_wave_gates"` -> `3 passed, 56 deselected`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-domain.ts --file e2e/platform-admin.spec.ts` -> `No ESLint warnings or errors`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"` -> `26 passed`
- `SESSION_AGENT=a705 scripts/session_check.sh` -> `Session OK`

Residual
- `UX-11` and `UX-12` remain open until deep feature-slice extraction (`Wave3`) is completed.
