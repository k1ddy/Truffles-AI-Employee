# UVC Tech Debt Decomposition Wave1 (A705)

## Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-03`
- Scope: first bounded extraction wave for `UX-11`/`UX-12` + merge-red e2e fix.

## Baseline
- `truffles-api/app/routers/console.py`: `25418` LOC.
- `console-web/src/components/ProvisioningWizard.tsx`: `5591` LOC.
- Historical merge-red: Playwright deep-link smoke occasionally redirected to `/login` and lost target ops URL.

## Implemented
1. Merge-red fix:
- Updated `console-web/e2e/platform-admin.spec.ts` to preserve and restore `workspace-next-step-ops` deep-link URL after `/login` fallback.

2. UX-12 decomposition wave1:
- Added `console-web/src/components/provisioning-wizard-utils.ts`.
- Moved pure helper functions (JSON parse/stringify, status labels/classes, capability normalization, tri-state formatting) from `ProvisioningWizard.tsx` to the new module.

3. UX-11 decomposition wave1:
- Added `truffles-api/app/services/console_router_utils.py`.
- Moved pure helpers (`request_with_query_params`, `parse_env_bool`, `parse_env_csv_set`, `parse_env_int`, `dedupe_list`) from `console.py`.
- Rewired `console.py` to import these helpers.
- Added deterministic tests `truffles-api/tests/test_console_router_utils.py`.

## Post-change snapshot
- `truffles-api/app/routers/console.py`: `25362` LOC.
- `console-web/src/components/ProvisioningWizard.tsx`: `5332` LOC.

## Checks
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-utils.ts --file e2e/platform-admin.spec.ts` -> pass.
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 npm run test:e2e -- --grep "deep-link from Tenants action queue to Workspace execute"` -> `1 passed`.
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_router_utils.py` -> pass.
- `pytest -q truffles-api/tests/test_console_router_utils.py` -> `5 passed`.

## Residuals
- `UX-11` and `UX-12` remain open as structural debt; current wave only removed pure helper layer.
- Next wave should split domain submodules/components while preserving existing contracts.
