# Onboarding P4+P5 Unified — Report (2026-02-17)

## Scope

Implemented unified `P4+P5` onboarding kernel:
- `P4`: real intake -> policy-pack compile report.
- `P5`: quality matrix + baseline/replay regression compare.
- Integrated output into Console Plane autopilot response and UI.

## Backend

1. `onboarding_intake_service`:
- Added compile summary (`build_intake_compile_summary`).
- Added quality matrix (`build_intake_pack_quality_summary`).
- Added baseline compare logic (`_compare_quality_baseline`).
- Added critical-missing helper (`build_intake_critical_missing_fields`).

2. `console` schema/router:
- Added intake payload models:
  - `OnboardingIntakeCompile`
  - `OnboardingIntakeQualityDimension`
  - `OnboardingIntakeQualityMatrix`
- `run_onboarding_autopilot` now returns:
  - `intake.compile`
  - `intake.quality_matrix`

3. `ops/diagnose.py`:
- Added new command:
  - `onboarding-pack-quality`
- Supports:
  - `--client-data-text-file/--client-data-json-file`
  - `--baseline-summary`
  - `--fail-on-regression`
  - `--save-summary`
- Output includes:
  - compile summary
  - quality matrix
  - regressions/comparison_blocked

## Contract/UI

1. `contracts/console_api/openapi.v1.yaml`:
- Added schemas for compile + quality matrix.
- Added `compile` and `quality_matrix` fields to `OnboardingAutopilotIntake`.

2. `console-web`:
- Regenerated `src/types/api.generated.ts`.
- Updated `ProvisioningWizard` to render:
  - pack compile status/flags/errors
  - quality matrix status, counts, dimensions, regressions

## Tests

- `pytest -q truffles-api/tests/test_onboarding_intake_service.py` -> `14 passed`
- `pytest -q truffles-api/tests/test_diagnose_onboarding_fleet.py` -> `7 passed`
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "onboarding_autopilot or onboarding_scorecard"` -> `7 passed`
- `pytest -q truffles-api/tests/test_console_onboarding_state.py` -> `21 passed`
- `pytest -q truffles-api/tests/test_minimum_data_contract.py truffles-api/tests/test_safe_mode_gate.py` -> `6 passed`

## Static checks/build

- `python3 -m py_compile truffles-api/app/services/onboarding_intake_service.py truffles-api/app/routers/console.py truffles-api/app/schemas/console.py ops/diagnose.py` -> pass
- `python3 truffles-api/scripts/generate_openapi.py --check` -> pass
- `python3 ops/diagnose.py onboarding-pack-quality --domain-slug beauty --require-booking true --client-data-json-file /tmp/onboarding_pack_quality_payload_p4p5.json --save-summary /tmp/onboarding_pack_quality_p4p5_summary.json --json` -> `status=pass`
- `npm --prefix console-web run generate:api` -> pass
- `npm --prefix console-web run lint -- --file src/components/ProvisioningWizard.tsx` -> pass
- `npm --prefix console-web run build` -> pass

## Notes

- `ruff check ops/diagnose.py` reports pre-existing issues unrelated to this change; functional and contract checks above are green.
