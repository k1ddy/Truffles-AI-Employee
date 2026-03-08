# UVC Tech Debt Decomposition Wave5 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE5-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-04`

Goal
- Continue bounded decomposition after final-close without runtime behavior change.
- Reduce monolith blast-radius for `UX-11`/`UX-12` using reusable backend/frontend slices.

What changed
- Backend (`UX-11`): extracted query validation helpers (`reject_unknown_query_params`, `validate_limit`, `parse_uuid_param`, `parse_bool_param`) into `truffles-api/app/services/console_router_utils.py` and rewired router wrappers in `truffles-api/app/routers/console.py`.
- Backend tests: extended `truffles-api/tests/test_console_router_utils.py` with deterministic coverage for new extracted helpers.
- Frontend (`UX-12`): extracted wizard shell blocks (`error summary`, `mode panel`, `execution hub`) from `ProvisioningWizard.tsx` into `console-web/src/components/provisioning-wizard-shell-panels.tsx` as controlled components.

LOC impact
- `truffles-api/app/routers/console.py`: `24888 -> 24881` (`-7`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4742 -> 4679` (`-63`)

Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_router_utils.py truffles-api/tests/test_console_router_utils.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py truffles-api/tests/test_console_onboarding_readiness.py` -> `16 passed`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-shell-panels.tsx --file src/components/provisioning-wizard-readiness-panel.tsx --file src/components/provisioning-wizard-derived.ts --file src/components/provisioning-wizard-utils.ts` -> `No ESLint warnings or errors`
- `cd console-web && npm run build` -> `pass`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"` -> `26 passed`
- `SESSION_AGENT=a705 scripts/session_check.sh` -> `Session OK`

Residual
- `UX-11`/`UX-12` remain open with reduced blast-radius; closure decision deferred to `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW-A705` after wave5 merge evidence on `main`.
