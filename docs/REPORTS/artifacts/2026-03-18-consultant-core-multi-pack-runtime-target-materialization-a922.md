# 2026-03-18 Consultant Core Multi-Pack Runtime Target Materialization (a922)

## Verdict Summary
- **FACT:** `clinic_pack/main` and `generic/main` now exist as truthful active runtime-accessible targets in the target environment.
- **FACT:** both new targets were materialized through the existing platform-admin provisioning/catalog owner family in `truffles-api/app/routers/console.py`, plus `truffles-api/app/services/onboarding_blueprints.py`, `truffles-api/app/services/knowledge_validation.py`, and `truffles-api/app/services/reference_pack_integrity.py`.
- **FACT:** both new targets pass `python3 ops/diagnose.py integrity-gate --client-slug <slug> --pretty` with `status=PASS`, `infra_valid=true`, and `critical_failures=[]`.
- **FACT:** `clinic` and `generic` now both have active `reference_packs` rows and active `domain_capability_templates` rows.
- **FACT:** `clinic_pack/main` and `generic/main` both have active branches, `go_live_state=approved`, branch webhook secrets present, active specialists, confirmed onboarding contracts, and published knowledge versions.
- **FACT:** `demo_salon` remains the unchanged beauty canary target and still passes `integrity-gate`.
- **FACT:** the old authority seam deleted/unreachable in this block is the repo-dir-only / deleted-client substitute runtime-target seam that previously blocked truthful non-beauty closure.
- **INFERENCE:** the surviving owner family for multi-pack target materialization is now the existing console provisioning/catalog surface, not repo directories, deleted substitute clients, or ad-hoc DB bootstrapping.
- **Recommendation:** close this package, sync canon to the runtime convergence result, and author one bounded acceptance re-entry TP before any expensive matrix / closure rerun.

## Materialized Targets
| Required profile | Truthful runtime target | Domain contract | Runtime state | Verdict |
| --- | --- | --- | --- | --- |
| `beauty` | `demo_salon/main` | existing `beauty` | active before this block; retained unchanged | truthful canary retained |
| `clinic_or_dental` | `clinic_pack/main` | existing `clinic` domain owner path with branch-level runtime capabilities | `client=active`, `branch=active`, `go_live_state=approved`, `specialist=active` | truthful target materialized |
| `generic_service` | `generic/main` | first-class `generic` domain blueprint / validation / reference-pack contract | `client=active`, `branch=active`, `go_live_state=approved`, `specialist=active` | truthful target materialized |

## Owner-Family Proof
- **FACT:** no committed bootstrap helper or raw `psql` owner was introduced.
- **FACT:** the block reused the existing owner family only:
  - `upsert_domain_catalog(...)`
  - `upsert_reference_pack(...)`
  - `create_company(...)`
  - `create_client(...)`
  - `create_branch(...)`
  - `create_agent(...)`
  - `run_onboarding_autopilot(...)`
  - `approve_branch_go_live(...)`
  - `update_branch(...)`
  - `calendar.create_specialist(...)`
- **FACT:** `generic` is now first-class in provisioning/validation/reference-pack ownership via `truffles-api/app/services/onboarding_blueprints.py`, `truffles-api/app/services/knowledge_validation.py`, and `truffles-api/app/services/reference_pack_integrity.py`.
- **INFERENCE:** the old split between runtime-neutral fallback semantics and provisioning/catalog ownership is now materially closed for `generic_service`.

## Integrity Evidence
- **FACT:** `python3 ops/diagnose.py integrity-gate --client-slug demo_salon --pretty` => `PASS` with all eight checks `PASS`.
- **FACT:** `python3 ops/diagnose.py integrity-gate --client-slug clinic_pack --pretty` => `PASS` with all eight checks `PASS`.
- **FACT:** `python3 ops/diagnose.py integrity-gate --client-slug generic --pretty` => `PASS` with all eight checks `PASS`.
- **FACT:** each integrity run returned `OUTBOX_DUPLICATE_IDEMPOTENCY=0`, `OUTBOX_STUCK_PROCESSING=0`, `HANDOVER_OPEN_UNIQUENESS=0`, `CONVERSATION_STATE_CONSISTENCY=0`, `APPOINTMENT_TIME_CONFLICT=0`, `APPOINTMENT_VISIT_CONSISTENCY=0`, `MEMBERSHIP_DUPLICATE_ACTIVE=0`, and `ORPHAN_REFERENCE_CHECK=0`.

## DB Truth
- **FACT:** target DB truth snapshot now contains:
  - active clients: `demo_salon`, `clinic_pack`, `generic`
  - active branches: `demo_salon/main`, `clinic_pack/main`, `generic/main`
  - active reference packs: `beauty`, `clinic`, `generic`
  - active domain capability templates: `clinic`, `generic`
- **FACT:** `clinic_pack/main` runtime contract state:
  - `published_knowledge_version_id=5cde6cee-2193-4c08-95f7-9605d50b620f`
  - `payment_status=confirmed`
  - branch capabilities use `domain_slug=clinic`, `booking_mode=confirm_slots`, `knowledge_upload=true`, `analytics=true`, `whatsapp=false`
  - active specialist `77e9a813-e6b5-4695-bc2b-51b1743a55cf`
- **FACT:** `generic/main` runtime contract state:
  - `published_knowledge_version_id=dab6c495-a8f4-4e27-885c-f0c0117700f3`
  - `payment_status=confirmed`
  - branch capabilities use `domain_slug=generic`, `booking_mode=collect_preferences`, `knowledge_upload=true`, `analytics=true`, `whatsapp=false`
  - active specialist `280a3a2b-89b8-4b3e-88d0-9cfd1efea80b`
- **FACT:** both new main branches have branch-scoped webhook secrets present.

## Deterministic Test Evidence
- **FACT:** `pytest -q truffles-api/tests/test_onboarding_blueprints.py` => `5 passed`
- **FACT:** `pytest -q truffles-api/tests/test_knowledge_validation.py -k "unknown_domain_keeps_fail_closed_profile_for_beauty_fields or domain_legal_skips_booking_required_fields_by_default or domain_generic_requires_booking_but_skips_beauty_specific_fields"` => `3 passed, 11 deselected`
- **FACT:** `pytest -q truffles-api/tests/test_reference_pack_integrity.py` => `5 passed`
- **FACT:** `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py -k "reference_pack or onboarding_autopilot or onboarding_blueprints"` => `6 passed, 7 deselected`
- **FACT:** `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "onboarding_autopilot or onboarding_blueprints"` => `9 passed, 35 deselected`
- **FACT:** `pytest -q truffles-api/tests/test_console_admin_provisioning.py -k "create_client or update_client"` => `8 passed, 15 deselected`

## Residual Debt
- **FACT:** final multi-pack acceptance closure is still not claimed in this block.
- **FACT:** expensive `llm-quality-matrix` / `llm-quality-open-world-closure` reruns were intentionally not started here.
- **FACT:** `run_onboarding_autopilot(...)` reported `knowledge_publish_failed` in its action list for both targets, but DB truth shows published knowledge versions exist for both branches.
- **INFERENCE:** the operator-facing autopilot action ledger likely still over-reports a publish failure after the published row exists; this did not block truthful target materialization, but it remains residual operator-signal debt until acceptance re-entry confirms whether a narrower follow-up package is needed.

## Next Honest Path
1. Author one re-entry TP for final multi-pack acceptance using the new truthful target mapping:
   - `beauty -> demo_salon`
   - `clinic_or_dental -> clinic_pack`
   - `generic_service -> generic`
2. Re-run the bounded canary + matrix + closure bundle only after that re-entry TP locks target selection, lock/replay/full cadence, and stop conditions.
3. If acceptance or closure artifacts fail, publish the next failure family as a new package instead of patching runtime inside the acceptance lane.

## Gap Register
- **GAP:** no final platform closure claim is made in this block.
- **GAP:** the acceptance re-entry package is not authored yet.
