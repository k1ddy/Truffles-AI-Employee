# UVC Tech Debt Decomposition Wave20 (A705)

Block
- `BLOCK_ID`: `UVC-UX-TECH-DEBT-DECOMPOSITION-WAVE20-A705`
- Parent: `UVC-UX-TECH-DEBT-DECOMPOSITION-A705`
- Date: `2026-03-05`

Goal
- Close failed criterion `C1` from closure-review15 by reducing `truffles-api/app/routers/console.py` to `<=24396` without behavior drift.

What changed
- Backend (`UX-11`): extracted Control Tower drift-board orchestration from router into service boundary:
  - Added `build_admin_control_tower_drift_board_response` in `truffles-api/app/services/console_control_tower_program.py`.
  - Rewired `truffles-api/app/routers/console.py` function `_build_admin_control_tower_drift_board` to delegate to service helper.
- Backend (`UX-11`): extracted Control Tower readiness-board orchestration from router into service boundary:
  - Added `build_admin_control_tower_readiness_board_response` in `truffles-api/app/services/console_control_tower_program.py`.
  - Rewired `truffles-api/app/routers/console.py` function `_build_admin_control_tower_readiness_board` to delegate to service helper.
- Frontend (`UX-12`): no functional changes in this wave (wizard threshold already within closure target).

LOC impact
- `truffles-api/app/routers/console.py`: `24469 -> 24353` (`-116`)
- `console-web/src/components/ProvisioningWizard.tsx`: `4287 -> 4287` (`0`)
- Note: after syncing remote branch updates during wave20, router temporarily increased to `24498`; bounded extraction still closed criterion `C1` (`24353 <= 24396`).

Deterministic checks
- `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx` -> `24353`, `4287`
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/console_control_tower_program.py` -> `pass`
- `pytest -q truffles-api/tests/test_console_onboarding_readiness.py truffles-api/tests/test_console_membership_state.py truffles-api/tests/test_console_fleet_state.py truffles-api/tests/test_console_router_utils.py truffles-api/tests/test_console_control_tower_program.py` -> `35 passed`
- `pytest -q truffles-api/tests/test_console_branch_changes.py truffles-api/tests/test_console_admin_provisioning.py -k "branch_change"` -> `32 passed, 23 deselected`
- `pytest -q truffles-api/tests/test_console_owner_business.py -k "control_tower and (drift_board or readiness_board)"` -> `4 passed, 55 deselected`
- `SESSION_TP_SCOPE_OVERRIDE=UVC_SCOPE_OVERRIDE_A705 SESSION_AGENT=a705 scripts/session_check.sh` -> `Session OK`

Residual
- Wave20 closes closure-review15 failed criterion `C1` in branch evidence.
- Final status decision for `UX-11/UX-12` remains fail-closed until closure-review16 on merged-main evidence.

Next block contract
- Follow-up TP locked: `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review16-a705.md`.
- Next objective: execute binary DoD matrix on merged-main wave20 evidence and decide `Fixed` vs `Open + wave21`.
- First deterministic check: `wc -l truffles-api/app/routers/console.py console-web/src/components/ProvisioningWizard.tsx`.

References
- `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-wave20-a705.md`
- `docs/TASK_PACKAGES/TP-2026-03-05-uvc-ux-tech-debt-decomposition-closure-review16-a705.md`
- `docs/CONSOLE_AUDIT/artifacts/2026-03-05-uvc-tech-debt-decomposition-closure-review15-a705.md`
