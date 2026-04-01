# TP-2026-03-18-consultant-core-multi-pack-acceptance-package-a922

## Goal
Delete the last beauty-only platform-evidence seam and converge final consultant-core closure onto one bounded machine-readable acceptance bundle: `demo_salon` remains canary-only for guarded acceptance, while platform evidence must come from one cross-profile `llm-quality-matrix` plus one `llm-quality-open-world-closure` artifact covering `beauty`, `clinic_or_dental`, and `generic_service` without reopening proof rewrite ownership.

## Canon refs
- `STATE.md` NOW: consultant core `proof_black_box_completion` runtime family convergence
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-proof-black-box-completion-package-a922.md`
- `docs/_generated/AGENT_PACKET.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after the acceptance bundle or truthful `GAP` is published with machine-readable evidence
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.pytest.org pytest parametrize generate test ids matrix combinations`
- **Date/time (local):** `2026-03-18` (earlier in-session before TP authoring; exact minute was not retained after the interrupted handoff)
- **Sources opened (from this query):**
  - `https://docs.pytest.org/en/stable/example/parametrize.html`
  - `https://docs.pytest.org/en/stable/how-to/parametrize.html`
- **Source quality:**
  - high-signal / primary source: official `pytest` documentation
- **Found ready-made solutions:**
  - stable parametrized ids are the right way to express matrix coverage without cloning bespoke test bodies
  - parametrized combinations should stay declarative and machine-readable so each row remains attributable and replayable
- **Decision:** `reuse`
  - reuse the existing cross-profile matrix and closure machinery already implemented in `ops/diagnose.py` instead of inventing a new acceptance harness
  - reuse `scripts/llm_quality_guarded.sh` only for the `demo_salon` canary acceptance lane and keep cross-profile proof in `llm-quality-matrix` plus `llm-quality-open-world-closure`
  - if a tiny deterministic validator/report check is needed, prefer extending an existing test or artifact gate with stable row ids rather than building another runner
- **Rejected options:**
  - new per-profile acceptance wrapper: rejected because `ops/diagnose.py` already owns matrix + closure artifacts
  - beauty-only guarded acceptance as platform closure: rejected because canon explicitly requires `beauty`, `clinic_or_dental`, and `generic_service`
  - ad-hoc narrative summary without machine-readable closure artifact: rejected because `P6` closure is blocked without `llm-quality-open-world-closure`

## Root cause (mandatory)
- **Symptom:** consultant-core runtime/proof convergence is materially done, but platform closure is still blocked because there is no single accepted evidence bundle proving required profile coverage across `beauty`, `clinic_or_dental`, and `generic_service`.
- **Minimal reproduction:**
  - `find truffles-api/app/knowledge -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort && rg -n "platform_evidence_requirement|required_profiles|multi_pack_acceptance|llm-quality-matrix|llm-quality-open-world-closure|cross_domain_contract" docs/SOURCE_OF_TRUTH.yaml docs/ACTIVE_PROGRAM.md docs/runbooks/BOOKING_CONFIRM_VERIFY.md ops/diagnose.py`
- **Evidence:**
  - `docs/SOURCE_OF_TRUTH.yaml:58` through `docs/SOURCE_OF_TRUTH.yaml:60` require three profiles: `beauty`, `clinic_or_dental`, `generic_service`
  - `docs/ACTIVE_PROGRAM.md:31` still marks `multi_pack_acceptance` as not started and forbids treating beauty-only evidence as convergence
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md:494` through `docs/runbooks/BOOKING_CONFIRM_VERIFY.md:504` already define the exact closure contract: `llm-quality-matrix` plus `llm-quality-open-world-closure`, with heavy acceptance stress staying on `demo_salon` only
  - `ops/diagnose.py:13261` through `ops/diagnose.py:13337` already expose `llm-quality-matrix` and `llm-quality-open-world-closure`
  - `ops/diagnose.py:14415` through `ops/diagnose.py:14685` already validate machine-readable closure status, including `cross_domain_contract`, per-row validity, judge/run-integrity/threshold gates, and failure-family presence
  - `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md:64` still records `multi_pack_acceptance` as the last open package
- **Five Whys:**
  1. Why is platform closure still open? Because required evidence is still split between a beauty canary acceptance lane and separate cross-profile matrix/closure tooling.
  2. Why is that split a problem? Because it allows beauty-only green or a loose narrative summary to masquerade as final convergence.
  3. Why has that not been closed already? Because earlier packages were correctly focused on deleting runtime/proof authority seams, not on assembling the final platform-evidence bundle.
  4. Why is a new runner not the answer? Because the repo already contains the exact acceptance/matrix/closure commands and gates needed for this bundle.
  5. Why is this package the truthful next move? Because the remaining residual is not another code hotspot; it is the still-live beauty-only platform-evidence seam and the absence of one machine-readable cross-profile closure artifact.
- **Root cause statement:** final consultant-core closure remains blocked because platform-evidence ownership is still split between `demo_salon`-only guarded acceptance and separately available cross-profile matrix/closure tooling, so the repo has no single bounded package that turns those existing owners into one canonical machine-readable multi-pack acceptance bundle.
- **Fix mechanism:**
  - keep `demo_salon` guarded acceptance as canary-only evidence
  - execute one cross-profile `llm-quality-matrix` with contract gates enabled across the three required profiles
  - execute one `llm-quality-open-world-closure` artifact on top of that matrix plus deterministic scenario evidence
  - publish one bounded closure report/canon update only if the artifact is valid; otherwise stop with the exact failure family / reason set and do not patch runtime inside this block

## Invariant
- no beauty-only evidence may count as platform closure
- no quality gate weakening: `judge.enabled`, `infra_valid`, `semantic_valid`, `run_integrity_valid`, `cross_domain_contract`, threshold checks, and failure-family checks remain mandatory
- `scripts/booking_dialog_scenarios.py` and `ops/diagnose.py` must not regain proof rewrite ownership in this package
- no runtime/core code changes count as progress inside the implementation block; if acceptance reveals a product/runtime bug, stop and split a new package from the surfaced failure family
- if required profile coverage cannot be mapped to real runtime-accessible client/branch slugs, stop and publish `GAP` instead of substituting beauty clones or lowering the contract

## Scope
- publish one package-level implementation plan for the final `multi_pack_acceptance` residual
- lock the exact evidence bundle for `demo_salon` canary acceptance plus cross-profile matrix + closure artifact
- define the deterministic inventory step for mapping `beauty`, `clinic_or_dental`, and `generic_service` to real client/branch targets
- define the exact stop conditions and artifact paths for truthful closure vs truthful `GAP`
- allow only docs/report/canon updates in the implementation block unless the block stops and spawns a new failure-family package

## Out of scope
- any new runtime or frozen-file implementation
- reopening `proof_black_box_completion`
- reworking `ops/diagnose.py` into another acceptance runner unless a bounded missing validator is proven
- claiming consultant correctness beyond the required closure artifact contract
- treating `demo_salon` as anything other than the canary acceptance lane

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-closure-a922.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `ops/diagnose.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `scripts/llm_quality_guarded.sh` for the `demo_salon` canary `lock/replay/canary/full` chain
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md` for the canonical guarded acceptance and `P6` closure SOP
  - `ops/diagnose.py llm-quality-matrix` for cross-profile LLM stress and matrix summary generation
  - `ops/diagnose.py llm-quality-open-world-closure` for machine-readable final closure validation
  - existing `summary.json`, `matrix_summary.json`, `failure_families`, and deterministic `scenarios.json` artifacts
  - `truffles-api/tests/architecture/test_arch_guard_packet.py` for canon sync integrity after the TP/closure report is published
- **External reuse:**
  - official `pytest` parametrization guidance from the single mandatory query above, only if a small deterministic artifact validator needs stable matrix row ids
- **Why this reuse mix is truthful:**
  - the repo already has separate owners for canary acceptance, cross-profile matrix, and open-world closure; this package is about assembling them into one canonical bundle, not inventing another layer
  - reusing these surfaces deletes the beauty-only platform-evidence seam instead of moving closure authority into a new wrapper forest or new runner

## Plan
1. Publish and register this package-level TP, then switch canon to it.
2. In the implementation block, inventory the runtime-accessible client/branch mapping for `beauty`, `clinic_or_dental`, and `generic_service`, using existing pack/tenant truth only.
3. Reuse an existing valid `demo_salon` acceptance baseline if one is still canonical; otherwise run one guarded `lock -> replay -> canary/full` chain on `demo_salon` only.
4. Run one cross-profile `llm-quality-matrix` with `cross-domain-contract block` and `scenario-context-contract block` across the mapped profile targets.
5. Run one `llm-quality-open-world-closure` command against the matrix summary plus deterministic scenario evidence and save the machine-readable closure artifact.
6. Publish one bounded report that links the exact artifact paths and states either `valid=true` closure or the exact blocking reasons / failure families.
7. Update canon only if the machine-readable closure artifact is valid; otherwise stop with `GAP` and spin a new failure-family package instead of patching runtime here.

## DoD
- this TP locks one truthful implementation path for `multi_pack_acceptance`
- the next block is explicitly evidence-first and machine-readable, not another runtime/code detour
- the package forbids beauty-only closure, gate weakening, and runtime fixes inside the acceptance block
- canon/session docs point at this package and the next move to implement the closure bundle
- required architecture/session guards pass

## Checks
- `find truffles-api/app/knowledge -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort && rg -n "platform_evidence_requirement|required_profiles|multi_pack_acceptance|llm-quality-matrix|llm-quality-open-world-closure|cross_domain_contract" docs/SOURCE_OF_TRUTH.yaml docs/ACTIVE_PROGRAM.md docs/runbooks/BOOKING_CONFIRM_VERIFY.md ops/diagnose.py`
- `scripts/llm_quality_guarded.sh --help`
- `python3 ops/diagnose.py llm-quality-matrix --help`
- `python3 ops/diagnose.py llm-quality-open-world-closure --help`
- `scripts/llm_quality_guarded.sh --mode lock --run-id booking-lock-a922 --pg-checklist /tmp/booking_quality/pg_checklist-a922.json -- --base-url "$BASE_URL" --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds`
- `scripts/llm_quality_guarded.sh --mode replay --run-id booking-replay-a922 -- --base-url "$BASE_URL" --client-slug demo_salon --scenarios-file /tmp/booking_quality/booking-lock-a922/scenarios.json --baseline-summary /tmp/booking_quality/booking-lock-a922/summary.json --count 10 --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds --fail-on-regression --max-failures 20`
- `scripts/llm_quality_guarded.sh --mode full --run-id booking-full-a922 -- --base-url "$BASE_URL" --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds --fail-on-regression --baseline-summary /tmp/booking_quality/booking-lock-a922/summary.json`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality-matrix --client-slugs "$BEAUTY_CLIENT,$CLINIC_OR_DENTAL_CLIENT,$GENERIC_SERVICE_CLIENT" --branch-slugs "$BEAUTY_BRANCH,$CLINIC_OR_DENTAL_BRANCH,$GENERIC_SERVICE_BRANCH" --run-id-prefix multi-pack-a922 --cross-domain-contract block --scenario-context-contract block -- --base-url "$BASE_URL" --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --quality-lane dev --run-economy-gate block --fail-on-thresholds`
- `python3 ops/diagnose.py llm-quality-open-world-closure --matrix-summary /tmp/booking_quality/multi-pack-a922/matrix_summary.json --deterministic-scenarios /tmp/booking_quality/multi-pack-seed-ru-a922/scenarios.json --deterministic-scenarios /tmp/booking_quality/multi-pack-seed-kk-a922/scenarios.json --deterministic-scenarios /tmp/booking_quality/multi-pack-seed-mixed-a922/scenarios.json --deterministic-scenarios /tmp/booking_quality/multi-pack-seed-translit-a922/scenarios.json --output /tmp/booking_quality/multi-pack-closure-a922.json --pretty`
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
- one bounded closure report in `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-closure-a922.md`
- machine-readable artifacts from the implementation block:
  - `/tmp/booking_quality/booking-lock-a922/summary.json`
  - `/tmp/booking_quality/booking-replay-a922/summary.json`
  - `/tmp/booking_quality/booking-full-a922/summary.json`
  - `/tmp/booking_quality/multi-pack-a922/matrix_summary.json`
  - `/tmp/booking_quality/multi-pack-closure-a922.json`
- `STATE.md` entry naming either the deleted beauty-only platform-evidence seam or the exact `GAP` reasons that blocked closure

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Max matrix runs:** `1`
- **Cheap deterministic gates first:** repo inventory + `--help` verification for guarded acceptance, matrix, and closure commands
- **Reuse policy:** reuse a valid existing `demo_salon` lock baseline if canonical; do not rerun expensive beauty canary steps without a new reason
- **Stop condition:** if profile mapping is missing, preflight/judge is invalid, any matrix row fails contract gates, the closure artifact reports reasons, or the only apparent fix is weakening gates or changing runtime code, stop and return to RCA/GAP instead of forcing closure
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** implementation block is evidence-only against the current runtime; no runtime/core code changes are planned in this package
- **Go/no-go signals:**
  - `demo_salon` acceptance lane remains canary-only and green on the required guarded chain
  - `matrix_summary.json` reports `cross_domain_contract.required=true`, `cross_domain_contract.valid=true`, and `all_ok=true`
  - `llm-quality-open-world-closure` returns `valid=true`
  - no unresolved `failure_families`
  - required architecture/session guards pass after canon/report sync
- **Rollback:**
  - revert this block's doc/report/canon changes only
  - do not keep any closure claim if the machine-readable artifact is invalid or missing
- **Rollback verification:**
  - `python3 scripts/build_agent_packet.py --check`
  - `python3 scripts/arch_guard.py`
  - `pytest -q truffles-api/tests/architecture`
- **Post-release monitoring window:** first post-closure review only; if a later replay or matrix invalidates the artifact, reopen the program as `BLOCKED` instead of defending the old closure claim

## Rollback
- Revert the docs/report/canon files touched by this block and rerun the required guards.

## No-go
- Do not count `demo_salon`-only green as platform closure.
- Do not weaken `judge`, `cross_domain_contract`, `scenario_context_contract`, threshold, or failure-family gates to make the package pass.
- Do not patch runtime/core behavior inside the acceptance block.
- Do not invent a new matrix runner, wrapper forest, or per-profile harness before exhausting the existing `ops/diagnose.py` and guarded acceptance surfaces.
- Do not reopen proof rewrite authority in `scripts/booking_dialog_scenarios.py` or `ops/diagnose.py`.
- Do not claim consultant correctness or full business-agnostic closure without the machine-readable closure artifact.

## Risks / blockers
- the repo may have knowledge-pack directories for the required profiles but no runtime-accessible client/branch mapping in the target environment; that blocks truthful closure
- a valid beauty canary baseline may be stale or absent, forcing one expensive guarded refresh before cross-profile closure can be evaluated
- matrix runs may surface new failure families; this package must stop and split follow-up work instead of absorbing runtime fixes
- if deterministic scenario evidence for the required language/noise profiles is missing, `llm-quality-open-world-closure` will remain blocked even if the matrix rows are green

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- frozen `decision.py` still exists as broader legacy transport/runtime ingress and is not removed by this package
- consultant-core runtime cutover remains partial overall even if multi-pack acceptance closes
- closure still depends on operational availability of valid client/branch targets for the three required profiles

### Why not in this block
- this package is only for deleting the beauty-only platform-evidence seam and publishing the final multi-pack acceptance artifact
- broader legacy-runtime retirement is a separate architectural concern from platform-evidence closure

### Risk if deferred
- teams can keep over-reading beauty-only evidence as platform convergence
- platform closure remains narrative instead of machine-readable
- future runtime work can proceed without one final evidence contract, making closure claims noisy and reversible

### Linked follow-up Task Package(s)
- if the closure artifact is green: no further ordered consultant-core package remains in the current residual ledger
- if blocked: one new failure-family TP must be authored from the surfaced `matrix_summary.json` / `multi-pack-closure-a922.json` reasons before any runtime change

### Expiry/trigger to stop deferral
- stop deferral immediately if anyone attempts to close the program from beauty-only acceptance, or from a narrative summary without a valid `llm-quality-open-world-closure` artifact

## Next-block contract (mandatory)
### Next block objective
- implement the final `multi_pack_acceptance` evidence bundle: one `demo_salon` canary acceptance chain plus one cross-profile matrix and one machine-readable closure artifact, with no runtime fixes inside the block

### First deterministic check command
- `find truffles-api/app/knowledge -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort && rg -n "platform_evidence_requirement|required_profiles|multi_pack_acceptance|llm-quality-matrix|llm-quality-open-world-closure|cross_domain_contract" docs/SOURCE_OF_TRUTH.yaml docs/ACTIVE_PROGRAM.md docs/runbooks/BOOKING_CONFIRM_VERIFY.md ops/diagnose.py`

### Blocked-by conditions
- inability to map `beauty`, `clinic_or_dental`, and `generic_service` to real runtime-accessible client/branch targets
- any invalid preflight, judge disablement, or missing deterministic scenario evidence required by `llm-quality-open-world-closure`
- any matrix row with unresolved threshold breaches, failure families, scenario-context violations, or run-integrity violations
- any implementation attempt that requires runtime/core code changes or gate weakening to make the package appear green

### Owner role for closure
- Brain / Top Architect
