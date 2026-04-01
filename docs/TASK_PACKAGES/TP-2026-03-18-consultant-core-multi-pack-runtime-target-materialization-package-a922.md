# TP-2026-03-18-consultant-core-multi-pack-runtime-target-materialization-package-a922

## Goal
Delete the repo-dir-only runtime-target assumption exposed by the multi-pack acceptance GAP and converge target materialization onto one existing platform-admin provisioning family so `clinic_or_dental` and `generic_service` become truthful runtime-accessible client/branch targets before the final acceptance bundle is retried.

## Canon refs
- `STATE.md` NOW: consultant core `multi_pack_acceptance` closure bundle GAP
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-closure-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/onboarding_blueprints.py`
- `truffles-api/app/services/knowledge_validation.py`
- `truffles-api/app/services/reference_pack_integrity.py`
- `docs/_generated/AGENT_PACKET.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after the implementation block either materializes truthful non-beauty runtime targets with integrity evidence or stops with a narrower truthful `GAP`
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `sqlalchemy insert on conflict postgresql upsert official docs`
- **Date/time (local):** `2026-03-18` (earlier in-session before TP authoring; exact minute was not retained after the interrupted handoff)
- **Sources opened (from this query):**
  - `https://docs.sqlalchemy.org/20/dialects/postgresql.html`
- **Source quality:**
  - high-signal / primary source: official SQLAlchemy PostgreSQL dialect documentation
- **Found ready-made solutions:**
  - SQLAlchemy already supports bounded PostgreSQL upsert through dialect-native `insert(...).on_conflict_do_update(...)` and `on_conflict_do_nothing(...)`
  - if a single provisioning helper needs idempotent seed behavior, it should stay inside one existing owner family instead of raw `psql` or ad-hoc SQL strings
- **Decision:** `reuse/integrate`
  - reuse the existing platform-admin provisioning owners first: `run_onboarding_autopilot(...)`, `upsert_reference_pack(...)`, and `upsert_domain_catalog(...)`
  - if implementation proves one small idempotent helper is still needed inside that owner family, use the official SQLAlchemy upsert pattern there rather than direct DB surgery
- **Rejected options:**
  - raw `psql` bootstrap commands as the primary implementation path: rejected because they would create a second materialization authority outside the console provisioning family
  - acceptance-side client substitution: rejected because deleted / empty clients already proved that fake targets contaminate closure evidence
  - a new standalone bootstrap script before exhausting the existing console provisioning family: rejected because the repo already has the required owner surfaces

## Root cause (mandatory)
- **Symptom:** final consultant-core closure is blocked because `beauty` has a truthful runtime target (`demo_salon`), but `clinic_or_dental` and `generic_service` do not.
- **Minimal reproduction:**
  - `find truffles-api/app/knowledge -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort && rg -n "clinic_or_dental|generic_service|required_profiles" docs/SOURCE_OF_TRUTH.yaml docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-closure-a922.md && rg -n "run_onboarding_autopilot|list_onboarding_blueprints|upsert_reference_pack|upsert_domain_catalog|_DOMAIN_DEFAULT_BOOKING_REQUIRED|_DOMAIN_EXTRA_REQUIRED_FIELDS|_DEFAULT_CLIENT_SLUG = \"generic\"" truffles-api/app/routers/console.py truffles-api/app/services/onboarding_blueprints.py truffles-api/app/services/knowledge_validation.py truffles-api/app/services/pack_runtime_neutral_adapter.py`
- **Evidence:**
  - `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-closure-a922.md` proves `demo_salon` is the only truthful active runtime target and that `clinic_pack`, `dental_pack`, and `generic` are repo directories rather than runtime client slugs
  - `truffles-api/app/routers/console.py` already owns client / branch / reference-pack / domain-catalog provisioning through `run_onboarding_autopilot(...)`, `upsert_reference_pack(...)`, and `upsert_domain_catalog(...)`
  - `truffles-api/app/services/onboarding_blueprints.py` exposes first-class blueprints for `beauty`, `clinic`, `legal`, and `ecom`, but no explicit `generic` blueprint
  - `truffles-api/app/services/knowledge_validation.py` still defaults unknown domains to the beauty fail-closed required-field profile, so `generic_service` cannot be materialized truthfully through the current provisioning path
  - `truffles-api/app/services/pack_runtime_neutral_adapter.py` already treats `generic` as the runtime-neutral fallback client slug, so runtime fallback and provisioning/domain ownership are currently out of sync
- **Five Whys:**
  1. Why is multi-pack closure blocked? Because two required profiles still lack truthful runtime-accessible targets.
  2. Why do those targets not exist? Because repo-local pack directories are not enough; the target environment still needs active client / branch / reference-pack / domain rows.
  3. Why are those rows not materialized through the current owner family? Because the provisioning/catalog path only has explicit first-class domain handling for `beauty`, `clinic`, `legal`, and `ecom`, while `generic` remains runtime-default only.
  4. Why does that mismatch matter? Because acceptance requires real client slugs and branch context, not repo directories or deleted substitute clients.
  5. Why is this package the truthful next move? Because the surfaced failure family is no longer inside consultant runtime/proof ownership; it is now the split target-materialization contract between pack directories, provisioning/catalog owners, and acceptance profile requirements.
- **Root cause statement:** runtime target materialization is fragmented across repo-only pack directories, existing platform-admin provisioning/catalog owners, and a runtime-neutral `generic` fallback that is not yet first-class in the provisioning/validation contract; as a result, `clinic_or_dental` and `generic_service` cannot currently be materialized as truthful active runtime targets.
- **Fix mechanism:**
  - reuse the existing platform-admin provisioning family in `truffles-api/app/routers/console.py`
  - keep `clinic_or_dental` on the existing `clinic` domain owner path unless implementation proves that is impossible
  - add explicit first-class `generic` domain support in the provisioning/validation/reference-pack path instead of relying on unknown-domain beauty fallback
  - prove the resulting targets with integrity-gate and DB truth before re-entering the final acceptance bundle

## Invariant
- no beauty-only or deleted-client substitute may count as `clinic_or_dental` or `generic_service`
- no direct DB surgery, raw `psql` bootstrap, or acceptance-side client aliasing may become the primary materialization owner
- no consultant runtime-core, frozen webhook files, or proof-lane owners may be changed in this package unless a new surfaced failure family forces a separate package
- `demo_salon` remains the existing beauty canary and must not be destabilized by this work
- no new provisioning wrapper forest; the surviving owner family must stay the existing console provisioning/catalog surface

## Scope
- publish one package-level implementation plan for the acceptance-gap failure family `multi_pack_runtime_target_materialization`
- lock the truthful owner family to the existing platform-admin provisioning/catalog surfaces plus their existing support services
- lock the canonical profile mapping strategy:
  - `beauty` stays `demo_salon` / existing active branch
  - `clinic_or_dental` must materialize through the existing `clinic` domain path unless that is disproven during implementation
  - `generic_service` must materialize through explicit `generic` domain support rather than beauty-default fallback
- define the integrity evidence required before the final acceptance bundle may be retried

## Out of scope
- rerunning `implement_multi_pack_acceptance_closure_bundle` in this block
- consultant runtime-core or frozen-file edits
- inventing a separate dental-specific domain owner unless implementation proves the existing `clinic` path cannot truthfully satisfy `clinic_or_dental`
- reopening the proof-path package
- changing `platform_evidence_requirement` or relaxing open-world closure gates

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-runtime-target-materialization-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-runtime-target-materialization-a922.md`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/services/onboarding_blueprints.py`
- `truffles-api/app/services/knowledge_validation.py`
- `truffles-api/app/services/reference_pack_integrity.py`
- `truffles-api/tests/test_onboarding_blueprints.py`
- `truffles-api/tests/test_knowledge_validation.py`
- `truffles-api/tests/test_reference_pack_integrity.py`
- `truffles-api/tests/test_console_onboarding_contract_api.py`
- `truffles-api/tests/test_console_access_admin_pr2.py`
- `truffles-api/tests/test_console_admin_provisioning.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/routers/console.py:run_onboarding_autopilot(...)` for client / branch / onboarding-contract / reference-pack materialization inside the existing owner family
  - `truffles-api/app/routers/console.py:upsert_reference_pack(...)` and `truffles-api/app/routers/console.py:upsert_domain_catalog(...)` for first-class reference-pack and domain-template convergence
  - `truffles-api/app/services/onboarding_blueprints.py` for explicit domain blueprint ownership
  - `truffles-api/app/services/knowledge_validation.py:get_required_fields_for_domain(...)` for canonical per-domain required-field ownership
  - `truffles-api/app/services/reference_pack_integrity.py` for reference-pack schema / checksum ownership
  - `python3 ops/diagnose.py integrity-gate --client-slug ... --pretty` for truthful target proof before acceptance re-entry
  - existing deterministic provisioning tests under `truffles-api/tests/`
- **External reuse:**
  - official SQLAlchemy PostgreSQL upsert guidance from the single mandatory query above, only if one bounded idempotent seed helper is required inside the existing provisioning owner family
- **Why this reuse mix is truthful:**
  - the repo already has one platform-admin family that owns target provisioning, reference-pack integrity, and onboarding catalog state
  - reusing and extending that family deletes the current repo-dir-only / deleted-client substitute seam instead of moving target materialization into ad-hoc SQL, acceptance wrappers, or another helper forest

## Plan
1. Publish and register this package-level TP, then switch canon to it.
2. In the implementation block, inventory and freeze the canonical runtime target mapping for all required profiles, keeping `beauty -> demo_salon` unchanged.
3. Materialize one truthful `clinic_or_dental` runtime target through the existing `clinic` domain owner path, reusing existing blueprints/catalog/reference-pack integrity unless that path is disproven.
4. Materialize one truthful `generic_service` runtime target by making `generic` a first-class provisioning/validation/reference-pack domain instead of relying on unknown-domain beauty fallback.
5. Keep all target creation/update authority inside the existing console provisioning/catalog family; if one idempotent helper is still needed, keep it inside that family and use the official SQLAlchemy upsert pattern.
6. Add targeted deterministic coverage for the new domain/materialization contract and prove each new target with integrity-gate plus DB truth.
7. Publish one bounded report that either proves truthful target materialization for the required non-beauty profiles or stops with an exact narrower `GAP`; only then may the acceptance bundle be retried.

## DoD
- this TP locks one truthful implementation path for the surfaced runtime-target-materialization failure family
- the next block must converge target materialization inside the existing platform-admin provisioning family instead of acceptance-side substitution or raw SQL bootstrapping
- the TP explicitly preserves `demo_salon` as the existing beauty canary and forbids counting deleted clients or repo directories as runtime targets
- canon/session docs point at this package and the next move to implement it
- required architecture/session guards pass

## Checks
- `find truffles-api/app/knowledge -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort && rg -n "clinic_or_dental|generic_service|required_profiles" docs/SOURCE_OF_TRUTH.yaml docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-closure-a922.md && rg -n "run_onboarding_autopilot|list_onboarding_blueprints|upsert_reference_pack|upsert_domain_catalog|_DOMAIN_DEFAULT_BOOKING_REQUIRED|_DOMAIN_EXTRA_REQUIRED_FIELDS|_DEFAULT_CLIENT_SLUG = \"generic\"" truffles-api/app/routers/console.py truffles-api/app/services/onboarding_blueprints.py truffles-api/app/services/knowledge_validation.py truffles-api/app/services/pack_runtime_neutral_adapter.py`
- `pytest -q truffles-api/tests/test_onboarding_blueprints.py`
- `pytest -q truffles-api/tests/test_knowledge_validation.py -k "unknown_domain_keeps_fail_closed_profile_for_beauty_fields or domain_legal_skips_booking_required_fields_by_default"`
- `pytest -q truffles-api/tests/test_reference_pack_integrity.py`
- `pytest -q truffles-api/tests/test_console_onboarding_contract_api.py -k "reference_pack or onboarding_autopilot or onboarding_blueprints"`
- `pytest -q truffles-api/tests/test_console_access_admin_pr2.py -k "onboarding_autopilot or onboarding_blueprints"`
- `pytest -q truffles-api/tests/test_console_admin_provisioning.py -k "create_client or update_client"`
- `python3 ops/diagnose.py integrity-gate --client-slug demo_salon --branch-slug main --pretty`
- `python3 ops/diagnose.py integrity-gate --client-slug clinic_pack --branch-slug main --pretty`
- `python3 ops/diagnose.py integrity-gate --client-slug generic --branch-slug main --pretty`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated TP plus canon sync in `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_PROGRAM.md`, `docs/_generated/AGENT_PACKET.md`, and `docs/_generated/AGENT_PACKET.json`
- one bounded implementation report in `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-runtime-target-materialization-a922.md`
- target-materialization evidence from the implementation block:
  - integrity-gate output for the clinic/dental target actually chosen
  - integrity-gate output for the `generic_service` target
  - DB truth for `clients`, `branches`, `reference_packs`, and `domain_capability_templates`
  - targeted pytest outputs for onboarding blueprints, knowledge validation, reference-pack integrity, and console provisioning
- `STATE.md` entry naming either the deleted repo-dir-only target-materialization seam or the exact narrower `GAP` that blocked implementation

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` acceptance reruns inside this package
- **Max materialization attempts:** `1` truthful clinic/generic materialization attempt before stop-and-RCA
- **Cheap deterministic gates first:** target inventory, blueprint/validation/unit tests, and integrity-gate proof before any acceptance retry
- **Reuse policy:** reuse existing `demo_salon` beauty canary unchanged; do not rerun matrix/closure inside this package
- **Stop condition:** if materialization requires raw DB surgery, consultant runtime changes, a separate dental-only owner family, or acceptance-side substitution, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** platform-admin-only provisioning/catalog rollout; no consultant runtime-core or frozen-file rollout in this package
- **Go/no-go signals:**
  - the chosen `clinic_or_dental` target exists as an active client / branch pair and passes `integrity-gate`
  - the `generic_service` target exists as an active client / branch pair and passes `integrity-gate`
  - required `reference_packs` / `domain_capability_templates` rows exist and pass integrity expectations
  - `demo_salon` remains valid and unchanged as the beauty canary target
- **Rollback:**
  - revert this block's code/doc changes
  - deactivate or remove any wrongly created target rows through the same bounded provisioning/catalog owner family used for creation, not via ad-hoc DB edits
  - do not retry acceptance until the rollbacked state is revalidated
- **Rollback verification:**
  - `python3 ops/diagnose.py integrity-gate --client-slug demo_salon --branch-slug main --pretty`
  - `python3 scripts/build_agent_packet.py --check`
  - `python3 scripts/arch_guard.py`
  - `pytest -q truffles-api/tests/architecture`
- **Post-release monitoring window:** only until the materialization report and integrity evidence are published; if either new target regresses or disappears, reopen the package before any acceptance rerun

## Rollback
- Revert the docs/canon/code files touched by this block and re-run the required guards; if implementation created target rows, remove or deactivate them through the same bounded provisioning/catalog owner path before declaring rollback complete.

## No-go
- Do not count `clinic_pack`, `dental_pack`, or `generic` directory presence as runtime target materialization.
- Do not use deleted / empty clients (`truffles`, `qwer`, `demo_salon_script_test`, or similar) as profile substitutes.
- Do not patch consultant runtime-core, frozen webhook files, or proof owners inside this package.
- Do not build a new bootstrap runner or SQL sidecar before exhausting the existing console provisioning/catalog family.
- Do not let unknown-domain beauty fallback stand in for a truthful `generic_service` contract.
- Do not rerun multi-pack acceptance or closure artifacts until the new targets are proven truthfully materialized.

## Risks / blockers
- `generic_service` likely needs explicit first-class domain support because unknown-domain validation currently falls back to beauty-specific required fields
- `clinic_or_dental` is a profile contract rather than a current domain slug, so the implementation report must make the chosen runtime mapping explicit
- target materialization may require platform-admin write access and target-environment DB/container availability
- if the current provisioning family cannot publish truth-complete runtime packs for clinic/generic without another owner family, the implementation block must stop as `GAP`

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- final multi-pack acceptance closure remains blocked until truthful clinic/generic runtime targets exist and are proven
- `clinic_or_dental` remains a profile alias rather than a first-class domain slug
- `generic` already exists as a runtime-neutral fallback slug, but provisioning/validation/reference-pack ownership is not yet aligned to it

### Why not in this block
- this block only locks the implementation path for the surfaced target-materialization failure family
- the actual target creation, integrity proof, and acceptance retry belong to the next implementation block

### Risk if deferred
- the program remains blocked at the final acceptance step
- teams can keep substituting repo directories or deleted clients for truthful runtime targets
- `generic_service` remains half-owned by runtime fallback and half-unowned by provisioning/catalog contracts

### Linked follow-up Task Package(s)
- implementation of this package
- re-entry into `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-package-a922.md` only after truthful target materialization is proven

### Expiry/trigger to stop deferral
- stop deferral immediately if anyone reruns `llm-quality-matrix` / `llm-quality-open-world-closure` without first proving truthful runtime targets for `clinic_or_dental` and `generic_service`

## Next-block contract (mandatory)
### Next block objective
- implement truthful runtime target materialization for `clinic_or_dental` and `generic_service` inside the existing platform-admin provisioning/catalog family, then prove each target with integrity-gate plus DB truth so the final acceptance bundle can re-enter honestly

### First deterministic check command
- `find truffles-api/app/knowledge -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort && rg -n "clinic_or_dental|generic_service|required_profiles" docs/SOURCE_OF_TRUTH.yaml docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-closure-a922.md && rg -n "run_onboarding_autopilot|list_onboarding_blueprints|upsert_reference_pack|upsert_domain_catalog|_DOMAIN_DEFAULT_BOOKING_REQUIRED|_DOMAIN_EXTRA_REQUIRED_FIELDS|_DEFAULT_CLIENT_SLUG = \"generic\"" truffles-api/app/routers/console.py truffles-api/app/services/onboarding_blueprints.py truffles-api/app/services/knowledge_validation.py truffles-api/app/services/pack_runtime_neutral_adapter.py`

### Blocked-by conditions
- implementation needs raw DB surgery or a new bootstrap owner outside the existing console provisioning/catalog family
- `generic_service` still depends on unknown-domain beauty fallback after the proposed changes
- the chosen `clinic_or_dental` target cannot be materialized through the existing `clinic` domain owner path and would require a broader new runtime/domain package
- platform-admin provisioning or integrity-gate proof cannot run in the target environment

### Owner role for closure
- Brain / Top Architect
