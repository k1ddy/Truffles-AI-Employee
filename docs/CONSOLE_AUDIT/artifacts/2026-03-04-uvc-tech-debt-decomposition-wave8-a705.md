# UVC Tech Debt Decomposition Wave8 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE8-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-04`

Goal
- Continue bounded decomposition after final-review3 without runtime behavior changes.
- Reduce monolith blast-radius for `UX-11`/`UX-12` by extracting one backend go-live governance slice and one frontend JSON sync slice.

What changed
- Backend (`UX-11`): moved go-live normalization/waiver/gate logic from `truffles-api/app/routers/console.py` into `truffles-api/app/services/console_onboarding_readiness.py`:
  - `normalize_branch_go_live_state`
  - `normalize_go_live_waiver_ttl_hours`
  - `coerce_utc_datetime`
  - `is_branch_go_live_waiver_active`
  - `is_branch_go_live_allowed`
  - `ensure_branch_go_live_gate`
- Backend tests: extended deterministic module coverage in `truffles-api/tests/test_console_onboarding_readiness.py`.
- Frontend (`UX-12`): extracted billing/working-hours/booking-settings JSON build/load helpers into `console-web/src/components/provisioning-wizard-state.ts`:
  - `buildBillingInfoJsonFromFields` / `loadBillingInfoFieldsFromJson`
  - `buildWorkingHoursJsonFromFields` / `loadWorkingHoursFieldsFromJson`
  - `buildBookingSettingsJsonFromFields` / `loadBookingSettingsFieldsFromJson`
- Frontend wiring: rewired `console-web/src/components/ProvisioningWizard.tsx` to use extracted helpers.

LOC impact
- `truffles-api/app/routers/console.py`: `24606 -> 24554` (`-52`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4544 -> 4552` (`+8`)

Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> `24554`, `4552`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_onboarding_readiness.py truffles-api/tests/test_console_onboarding_readiness.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py` -> `35 passed`
- `ruff check truffles-api/app/routers/console.py truffles-api/app/services/console_onboarding_readiness.py truffles-api/tests/test_console_onboarding_readiness.py` -> `pass`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-state.ts --file e2e/platform-admin.spec.ts` -> `No ESLint warnings or errors`
- `cd console-web && npm run build` -> `pass`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "Platform Admin Navigation|Platform Admin Tenants|Platform Admin Integrations|deep-link from Tenants action queue to Workspace execute"` -> `26 passed`

Residual
- `UX-11`/`UX-12` remain open with reduced blast-radius; closure decision deferred to `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW4-A705` on merged-main evidence.
