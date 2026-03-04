# UVC Tech Debt Decomposition Wave9 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE9-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-04`

Goal
- Continue bounded decomposition after closure-review4 without runtime behavior changes.
- Further reduce monolith blast-radius for `UX-11`/`UX-12` by extracting one backend branch-change slice and one frontend provisioning-action slice.

What changed
- Backend (`UX-11`): moved branch-change helper slice from `truffles-api/app/routers/console.py` into `truffles-api/app/services/console_branch_changes.py`:
  - `BRANCH_CHANGE_MANAGED_FIELDS`
  - `BRANCH_CHANGE_MUTABLE_STATUSES`
  - `snapshot_branch_for_change`
  - `build_branch_change_diff`
  - `serialize_branch_change_record`
  - `build_branch_update_request`
- Backend wiring: router imports extracted helpers under existing private aliases; endpoint behavior unchanged.
- Frontend (`UX-12`): extracted wizard branch-action payload builders into `console-web/src/components/provisioning-wizard-branch-actions.ts`:
  - `buildCreateBranchPayload`
  - `buildUpdateBranchDraftPayload`
  - `buildSaveInstancePayload`
  - `buildSaveTelegramPayload`
  - `buildSaveKnowledgePayload`
  - `buildSaveBookingPayload`
- Frontend wiring: `console-web/src/components/ProvisioningWizard.tsx` handlers now call extracted builders and keep existing validation/error messages.

LOC impact
- `truffles-api/app/routers/console.py`: `24554 -> 24493` (`-61`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4552 -> 4452` (`-100`)

Checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> `24493`, `4452`
- `python3 -m py_compile truffles-api/app/services/console_branch_changes.py truffles-api/app/routers/console.py truffles-api/tests/test_console_branch_changes.py` -> `pass`
- `ruff check truffles-api/app/routers/console.py truffles-api/app/services/console_branch_changes.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py` -> `35 passed`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"` -> `10 passed, 23 deselected`
- `cd console-web && npm run lint -- --file src/components/ProvisioningWizard.tsx --file src/components/provisioning-wizard-branch-actions.ts` -> `No ESLint warnings or errors`
- `cd console-web && npm run build` -> `pass`
- `cd console-web && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3100 E2E_USE_STORAGE_STATE=0 E2E_DETERMINISTIC_AUTH=1 npm run test:e2e -- --grep "show actionable provisioning guidance for quick-create server errors|deep-link from Tenants action queue to Workspace execute"` -> `2 passed`
- `scripts/session_check.sh` -> `Session OK`

PR
- `https://github.com/k1ddy/Truffles-AI-Employee/pull/901`

Residual
- `UX-11`/`UX-12` remain open with reduced blast-radius; closure decision deferred to `UVC-UX-TECH-DEBT-DECOMPOSITION-CLOSURE-REVIEW5-A705` on merged-main evidence.
