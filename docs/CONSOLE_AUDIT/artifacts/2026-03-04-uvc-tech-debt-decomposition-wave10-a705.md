# UVC Tech Debt Decomposition Wave10 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE10-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-04`

Goal
- Continue bounded decomposition after closure-review5 without runtime behavior changes.
- Further reduce monolith blast-radius for `UX-11`/`UX-12` by extracting one backend branch-change normalization slice and one frontend account-action slice.

What changed
- Backend (`UX-11`): extracted branch-change normalization orchestration from `truffles-api/app/routers/console.py` to `truffles-api/app/services/console_branch_changes.py`:
  - `normalize_branch_change_patch`
- Backend wiring: router now delegates `_normalize_branch_change_patch(...)` to service function with pre-bound validators/guards, preserving existing messages and gate checks.
- Frontend (`UX-12`): extracted account/action payload builders from `console-web/src/components/ProvisioningWizard.tsx` into `console-web/src/components/provisioning-wizard-account-actions.ts`:
  - `buildCreateCompanyPayload`
  - `buildCreateClientPayload`
  - `buildCreateAgentPayload`
- Frontend wiring: `handleCreateCompany`, `handleCreateClient`, `handleCreateAgent` now delegate payload building/validation to extracted module.

LOC impact
- `truffles-api/app/routers/console.py`: `24493 -> 24366` (`-127`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4452 -> 4423` (`-29`)

Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> `24366`, `4423`
- `python3 -m py_compile truffles-api/app/services/console_branch_changes.py truffles-api/app/routers/console.py truffles-api/tests/test_console_branch_changes.py` -> `pass`
- `ruff check truffles-api/app/services/console_branch_changes.py truffles-api/app/routers/console.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py` -> `35 passed`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"` -> `10 passed, 23 deselected`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-account-actions.ts --file src/components/provisioning-wizard-branch-actions.ts --file e2e/platform-admin.spec.ts` -> `No ESLint warnings or errors`
- `cd console-web && npm run build` -> `pass`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "show actionable provisioning guidance for quick-create server errors|deep-link from Tenants action queue to Workspace execute"` -> `2 passed`
- `scripts/session_check.sh` -> `Session OK`

Residual
- `UX-11`/`UX-12` remain open with reduced blast-radius; closure decision deferred to `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW6-A705` on merged-main evidence.
