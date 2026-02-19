# 2026-02-19 Onboarding Any-Niche Step123 (A131)

## Scope

- TP: `docs/TASK_PACKAGES/TP-2026-02-19-onboarding-any-niche-step123-a131.md`
- Branch: `feat/2026-02-19-onboarding-any-niche-step123-a131`
- Worktree: `/home/zhan/worktrees/2026-02-19-onboarding-any-niche-step123-a131`
- Goal: close items `1/2/3` from end-to-end onboarding plan:
  - `1` Ops acceptance C to PASS.
  - `2` hard-gate rollout completion (shadow/canary/enforced behavior).
  - `3` blueprint contract completion (`required_fields_profile`, `readiness_weights`).

## Implementation

### 2) Hard-gate rollout completion

- Added canary branch enforcement via env:
  - `ONBOARDING_READINESS_HARD_GATE_CANARY_BRANCH_IDS`
- Added per-branch enforcement resolver:
  - `_is_readiness_hard_gate_enforced_for_branch(...)`
- Applied per-branch enforcement in:
  - readiness kernel serialization (`shadow_hard_gate.enforced`)
  - go-live blocking logic (`_require_branch_scorecard_ready`)
- Added tests for:
  - shadow behavior when hard-gate disabled
  - enforced behavior with global hard-gate
  - enforced behavior for canary-only branch

### 3) Blueprint contract completion

- Extended blueprint model with:
  - `required_fields_profile` (`fields`, `checksum`) from domain contract
  - `readiness_weights` per domain
- Added schema/API serialization for new fields.
- Synced frontend API types.
- Synced OpenAPI schema:
  - `OnboardingBlueprintRequiredFieldsProfile`
  - new required fields on `OnboardingBlueprint`.
- Added focused tests for blueprint contract invariants.

### 1) Ops acceptance C to PASS

- Added valid production-grade fixture:
  - `ops/fixtures/onboarding_pack_quality_beauty_valid.yaml`
- Remediation executed:
  - `onboarding-fleet-remediate --sync-reference-pack-integrity --apply --json`
- Pre-check evidence (expected fail before remediation):
  - active branch blocked by:
    - `reference_pack_required_fields`
    - `reference_pack_required_fields_checksum`
- Post-remediation checks PASS:
  - `onboarding-fleet-check --fail-on-active-missing --json` exit `0`
  - `onboarding-quality-smoke --domains beauty,clinic,legal,ecom --fail-on-regression --json` exit `0`
  - `onboarding-pack-quality --domain-slug beauty --require-booking auto --client-data-text-file ops/fixtures/onboarding_pack_quality_beauty_valid.yaml --json` exit `0`

## Evidence

- Raw artifacts: `/tmp/onboarding_any_niche_step123_a131/`
- Key files:
  - `/tmp/onboarding_any_niche_step123_a131/onboarding_fleet_check_pre.json`
  - `/tmp/onboarding_any_niche_step123_a131/onboarding_fleet_remediate.json`
  - `/tmp/onboarding_any_niche_step123_a131/onboarding_fleet_check_post.json`
  - `/tmp/onboarding_any_niche_step123_a131/onboarding_quality_smoke.json`
  - `/tmp/onboarding_any_niche_step123_a131/onboarding_pack_quality.json`
  - `/tmp/onboarding_any_niche_step123_a131/onboarding_pack_quality_summary.json`

## Validation

- `python3 -m py_compile ...` -> `0`
- `ruff check ...` -> `0`
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "hard_gate or onboarding_blueprints"` -> `0`
- `pytest -q truffles-api/tests/test_onboarding_blueprints.py` -> `0`
- `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py` -> `0`
- `python3 truffles-api/scripts/generate_openapi.py --check` -> `0`
- `python3 ops/diagnose.py onboarding-fleet-check --fail-on-active-missing --json` -> pre `1`, post `0`
- `python3 ops/diagnose.py onboarding-quality-smoke --domains beauty,clinic,legal,ecom --fail-on-regression --json` -> `0`
- `python3 ops/diagnose.py onboarding-pack-quality --domain-slug beauty --require-booking auto --client-data-text-file ops/fixtures/onboarding_pack_quality_beauty_valid.yaml --save-summary /tmp/onboarding_any_niche_step123_a131/onboarding_pack_quality_summary.json --json` -> `0`

## Verdict

- Item `1`: PASS
- Item `2`: PASS
- Item `3`: PASS
- TP result: PASS
