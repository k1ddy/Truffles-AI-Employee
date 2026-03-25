# 2026-03-18 Consultant Core Multi-Pack Acceptance Closure (a922)

## Verdict Summary
- **FACT:** `implement_multi_pack_acceptance_closure_bundle` is blocked before any expensive acceptance or matrix run.
- **FACT:** `demo_salon` is the only truthful active runtime-accessible target found for the required profile set.
- **FACT:** `clinic_pack`, `dental_pack`, and `generic` exist under `truffles-api/app/knowledge/`, but they are not runtime client slugs in the target environment.
- **FACT:** the repo currently has only one active reference-pack domain row: `beauty`.
- **FACT:** existing historical matrix / closure artifacts in `/tmp/booking_quality` are demo-only or explicitly invalid for final closure.
- **FACT:** no old authority seam became deleted or unreachable in this block.
- **INFERENCE:** the remaining failure family is runtime target materialization for the required non-beauty profiles, not another proof-lane implementation gap.
- **Recommendation:** stop the closure bundle here and author one package TP for runtime target materialization across `clinic_or_dental` and `generic_service` before any new acceptance rerun.

## Runtime Target Inventory
| Required profile | Repo surface | Runtime evidence | Verdict |
| --- | --- | --- | --- |
| `beauty` | `truffles-api/app/knowledge/demo_salon` | `python3 ops/diagnose.py integrity-gate --client-slug demo_salon --pretty` => `PASS`; DB inventory shows `demo_salon` is `active` with `business_type=beauty_salon`, `policy_type=demo_salon`, and branch `main` | truthful target available |
| `clinic_or_dental` | `truffles-api/app/knowledge/clinic_pack`, `truffles-api/app/knowledge/dental_pack` | `python3 ops/diagnose.py integrity-gate --client-slug clinic_pack --pretty` => `client not found`; `python3 ops/diagnose.py integrity-gate --client-slug dental_pack --pretty` => `client not found`; no active clinic/dental reference pack row | blocked |
| `generic_service` | `truffles-api/app/knowledge/generic` | `python3 ops/diagnose.py integrity-gate --client-slug generic --pretty` => `client not found`; no active generic reference pack row | blocked |

## Non-Target Runtime Clients Are Not Valid Substitutes
- **FACT:** `python3 ops/diagnose.py integrity-gate --client-slug truffles --pretty` passes integrity, but DB inventory shows client `truffles` is `deleted` and its config is `{}`.
- **FACT:** `python3 ops/diagnose.py integrity-gate --client-slug qwer --pretty` passes integrity, but DB inventory shows client `qwer` is `deleted` and its config is `{}`.
- **FACT:** `python3 ops/diagnose.py integrity-gate --client-slug demo_salon_script_test --pretty` passes integrity, but DB inventory shows client `demo_salon_script_test` is `deleted` and has no branch.
- **INFERENCE:** these slugs cannot truthfully satisfy `clinic_or_dental` or `generic_service` for platform closure.

## Supporting DB Truth
- **FACT:** client / branch inventory from `docker exec truffles_postgres_1 psql -U n8n -d chatbot ...` shows only one active business client with the required runtime semantics: `demo_salon`.
- **FACT:** `docker exec truffles_postgres_1 psql -U n8n -d chatbot -At -F '\t' -c "SELECT id, domain_slug, title, status FROM reference_packs ORDER BY domain_slug, title;"` returns one active row only: `Reference pack: beauty`.
- **FACT:** `docker exec truffles_postgres_1 psql -U n8n -d chatbot -At -F '\t' -c "SELECT COUNT(*) FROM domain_capability_templates;"` returns `0`.
- **INFERENCE:** repo-local pack directories are ahead of runtime target materialization in the target environment.

## Existing Artifact Inventory
| Artifact | Truth from artifact | Why it does not close the package |
| --- | --- | --- |
| `/tmp/booking_quality/booking-matrix-20260216-a88/matrix_summary.json` | `all_ok=true`; one row only: `demo_salon`; `cross_domain_contract=None`; `failure_families=None` | demo-only; missing cross-domain contract, failure families, branch context, and invariant fields |
| `/tmp/booking_quality/matrix-smoke-a88/matrix_summary.json` | `all_ok=true`; one row only: `demo_salon`; `cross_domain_contract=None` | demo-only smoke; not a valid cross-profile closure artifact |
| `/tmp/booking_quality/p6-closure-probe-20260306-a1/p6_open_world_closure.json` | `valid=false`; reasons include `matrix_cross_domain_not_required`, `matrix_cross_domain_invalid`, `matrix_failure_families_missing`, `matrix_distinct_clients_lt_2:1`, `matrix_branch_context_missing`, `matrix_seed_evidence_missing` | explicitly invalid closure artifact |

## What Was Run In This Block
- **FACT:** completed the package deterministic gate: `find truffles-api/app/knowledge -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort && rg -n "platform_evidence_requirement|required_profiles|multi_pack_acceptance|llm-quality-matrix|llm-quality-open-world-closure|cross_domain_contract" docs/SOURCE_OF_TRUTH.yaml docs/ACTIVE_PROGRAM.md docs/runbooks/BOOKING_CONFIRM_VERIFY.md ops/diagnose.py`.
- **FACT:** completed cheap command-surface checks:
  - `scripts/llm_quality_guarded.sh --help`
  - `python3 ops/diagnose.py llm-quality-matrix --help`
  - `python3 ops/diagnose.py llm-quality-open-world-closure --help`
- **FACT:** completed runtime target validation via `integrity-gate` plus DB inventory queries.
- **FACT:** did not start a new guarded `lock/replay/full`, `llm-quality-matrix`, or `llm-quality-open-world-closure` run because the package hit the TP stop condition earlier: missing truthful runtime targets for two required profiles.

## Blocking Reasons
- **FACT:** the TP's `Blocked-by conditions` explicitly forbid proceeding when `beauty`, `clinic_or_dental`, and `generic_service` cannot be mapped to real runtime-accessible client/branch targets.
- **FACT:** that condition is currently true.
- **INFERENCE:** forcing a beauty-only canary rerun here would create narrative churn, not package closure.
- **INFERENCE:** forcing a matrix run with fake/deleted substitute clients would contaminate the closure evidence instead of satisfying it.

## Next Honest Path
1. Author one package TP for runtime target materialization from this surfaced failure family.
2. Materialize truthful runtime-accessible targets for `clinic_or_dental` and `generic_service` without weakening the `platform_evidence_requirement` contract.
3. Re-enter `implement_multi_pack_acceptance_closure_bundle` only after those targets exist and pass the same integrity gate used here.

## Gap Register
- **GAP:** no truthful runtime-accessible `clinic_or_dental` target exists in the current environment.
- **GAP:** no truthful runtime-accessible `generic_service` target exists in the current environment.
- **GAP:** no already-valid multi-pack matrix / closure artifact exists that can replace those missing targets.
