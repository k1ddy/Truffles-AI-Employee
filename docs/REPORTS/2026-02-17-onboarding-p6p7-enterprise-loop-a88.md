# Onboarding P6+P7 Enterprise Loop (2026-02-17)

## Summary

Implemented `P6` + `P7` without replacing existing onboarding flow:

1. `P6` SLA/escalation control loop was added to onboarding scorecard read-model.
2. `P7` operational onboarding pipeline was added as stage-based read-model with blockers/next actions.
3. Console Plane onboarding screen now renders both blocks (`SLA loop` + `Operational pipeline`) alongside existing scorecard/readiness widgets.
4. `ops/diagnose.py onboarding-fleet-*` output was extended with SLA/pipeline signals for operational audits.

## Backend changes

- `truffles-api/app/services/onboarding_state.py`
  - Added `OnboardingSlaControlLoop`, `OnboardingOperationalStage`, `OnboardingOperationalPipeline`.
  - Added SLA threshold resolution from `client_settings` and unresolved handover counters (`pending/warning/breached`).
  - Added provider binding SLA incident detection (`missing/rebind/webhook/billing/renewal/capability alert`).
  - Added operational pipeline assembly (`contract/channel/knowledge/booking/sla/go-live` stages with blockers + next actions).
  - `build_onboarding_scorecard()` now enriches scorecard with `sla_control_loop` and `operational_pipeline`.

- `truffles-api/app/schemas/console.py`
  - Added API schemas:
    - `ConsoleOnboardingSlaControlLoop`
    - `ConsoleOnboardingOperationalStage`
    - `ConsoleOnboardingOperationalPipeline`
  - Extended `ConsoleOnboardingScorecardResponse` with:
    - `sla_control_loop`
    - `operational_pipeline`

- `truffles-api/app/routers/console.py`
  - `_serialize_onboarding_scorecard()` now serializes new P6/P7 payload blocks.

- `ops/diagnose.py`
  - `onboarding-fleet` container report rows now include SLA/pipeline fields.
  - Summary now includes:
    - `active_sla_fail`
    - `active_pipeline_blocked`

## Console Plane changes

- `console-web/src/components/ProvisioningWizard.tsx`
  - Added dedicated UI blocks:
    - `SLA / Escalation Control Loop`
    - `Operational Onboarding Pipeline`
  - Added blocker/action formatting for SLA incidents and pipeline actions.
  - Included new P6/P7 signals in readiness blockers aggregation.

- `console-web/src/app/company-workspace/page.tsx`
  - Added explicit schema typing for options/integration/lifecycle memo values.
  - This removed implicit-any build blockers that surfaced during validation.

## Contract changes

- `contracts/console_api/openapi.v1.yaml`
  - Added schemas:
    - `OnboardingSlaControlLoop`
    - `OnboardingOperationalStage`
    - `OnboardingOperationalPipeline`
  - Extended `OnboardingScorecardResponse` with:
    - `sla_control_loop`
    - `operational_pipeline`

- `console-web/src/types/api.generated.ts`
  - Regenerated from `openapi.v1.yaml`.

## Tests and checks

- `python3 -m py_compile truffles-api/app/services/onboarding_state.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py ops/diagnose.py truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_console_access_admin_pr2.py truffles-api/tests/test_diagnose_onboarding_fleet.py` -> pass
- `ruff check truffles-api/app/services/onboarding_state.py truffles-api/app/schemas/console.py truffles-api/app/routers/console.py ops/diagnose.py truffles-api/tests/test_console_onboarding_state.py truffles-api/tests/test_console_access_admin_pr2.py truffles-api/tests/test_diagnose_onboarding_fleet.py` -> pass
- `pytest -q truffles-api/tests/test_console_onboarding_state.py` -> `22 passed`
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "onboarding_scorecard or onboarding_autopilot"` -> `7 passed, 26 deselected`
- `pytest -q truffles-api/tests/test_diagnose_onboarding_fleet.py` -> `7 passed`
- `python3 truffles-api/scripts/generate_openapi.py --check` -> pass
- `npm --prefix console-web run generate:api` -> pass
- `npm --prefix console-web run lint -- --file src/components/ProvisioningWizard.tsx --file src/app/company-workspace/page.tsx` -> pass
- `npm --prefix console-web run build` -> pass

## Notes

- The session started from `origin/main`; branch is currently behind upstream by later unrelated commits and can be merged with current `origin/main` before final PR merge if needed.
