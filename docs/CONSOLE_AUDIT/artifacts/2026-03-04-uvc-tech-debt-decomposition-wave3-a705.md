# UVC Tech Debt Decomposition Wave3 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE3-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-04`

Goal
- Close Wave3 structural decomposition for `UX-11`/`UX-12` with behavior-preserving extraction only.
- Keep existing UVC UX ownership, endpoints, and UI contracts unchanged.

What changed
- Backend (`UX-11`): extracted control-tower orchestration/program composition from `console.py` into `truffles-api/app/services/console_control_tower_program.py` and rewired router handlers.
- Added deterministic backend tests for extracted orchestration module: `truffles-api/tests/test_console_control_tower_program.py`.
- Frontend (`UX-12`): extracted `ProvisioningWizard` derived-state builders (`step state/status`, `timeline`, `readiness`) into `console-web/src/components/provisioning-wizard-derived.ts` and rewired `ProvisioningWizard.tsx`.

LOC impact
- `truffles-api/app/routers/console.py`: `25143 -> 24920` (`-223`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4911 -> 4819` (`-92`)

Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_control_tower_program.py truffles-api/tests/test_console_control_tower_program.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_control_tower_program.py` -> `3 passed`
- `pytest -q truffles-api/tests/test_console_owner_business.py -k "control_tower_issue_counts or migration_wave_detail_filters_actions_and_counts or migration_program_aggregates_wave_gates"` -> `3 passed, 56 deselected`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-derived.ts --file e2e/platform-admin.spec.ts` -> `No ESLint warnings or errors`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"` -> `26 passed`
- `SESSION_AGENT=a705 scripts/session_check.sh` -> `Session OK`

Residual
- `UX-11` and `UX-12` remain open until closeout block confirms final target state (`Open -> Fixed` vs explicit deferred residual) and syncs final decision in canon docs.
