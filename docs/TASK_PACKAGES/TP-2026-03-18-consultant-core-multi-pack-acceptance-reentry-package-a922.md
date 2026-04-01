# TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922

## Goal
Delete the stale pre-materialization acceptance-entry seam and converge final consultant-core closure onto one bounded re-entry package that binds actual runtime targets `demo_salon/main`, `clinic_pack/main`, and `generic/main` to one guarded canary lane plus one cross-profile matrix and one machine-readable closure artifact.

## Canon refs
- `STATE.md` NOW: consultant core `multi_pack_runtime_target_materialization` owner convergence
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-runtime-target-materialization-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-package-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-runtime-target-materialization-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/_generated/AGENT_PACKET.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after the re-entry block either publishes a valid machine-readable closure artifact or a truthful `GAP` with exact failure families / reasons
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `pytest parametrize stable ids matrix official docs`
- **Date/time (local):** `2026-03-18T19:30:09+05:00`
- **Sources opened (from this query):**
  - `https://docs.pytest.org/en/stable/example/parametrize.html`
  - `https://docs.pytest.org/en/stable/how-to/parametrize.html`
- **Source quality:**
  - high-signal / primary source: official `pytest` documentation
- **Found ready-made solutions:**
  - stable parametrized ids keep matrix rows attributable and replayable instead of hiding failures inside generic loops
  - reuse of existing matrix surfaces is preferable to cloning bespoke test runners when the row contract already exists
- **Decision:** `reuse`
  - reuse the existing `scripts/llm_quality_guarded.sh`, `ops/diagnose.py llm-quality-matrix`, and `ops/diagnose.py llm-quality-open-world-closure` owners
  - if one tiny deterministic validator needs stable row names, extend an existing guard/test with explicit ids instead of building another acceptance wrapper
- **Rejected options:**
  - new per-profile acceptance runner: rejected because the repo already has the canonical canary + matrix + closure owners
  - beauty-only guarded rerun as final closure: rejected because actual `clinic_pack` and `generic` runtime targets now exist and must participate in closure evidence
  - narrative report without machine-readable closure artifact: rejected because `P6` remains blocked without `llm-quality-open-world-closure`

## Root cause (mandatory)
- **Symptom:** the non-beauty runtime-target blocker is closed, but final consultant-core closure is still not re-entered through one canonical acceptance package that binds the actual target slugs, refreshed canary evidence, deterministic scenario evidence, and one machine-readable closure artifact.
- **Minimal reproduction:**
  - `python3 scripts/quality_artifact_report.py --hours 72 --show-commands && rg -n "demo_salon/main|clinic_pack/main|generic/main|llm-quality-matrix|llm-quality-open-world-closure|lock/replay/canary/full" docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-runtime-target-materialization-a922.md docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- **Evidence:**
  - `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-runtime-target-materialization-a922.md` proves truthful active runtime targets now exist for `beauty`, `clinic_or_dental`, and `generic_service`
  - `python3 scripts/quality_artifact_report.py --hours 72 --show-commands` currently returns only the header row, so there is no recent audited guarded acceptance bundle to reuse as the canonical re-entry baseline
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md:467` through `docs/runbooks/BOOKING_CONFIRM_VERIFY.md:504` already define the exact multi-pack matrix + closure contract and explicitly keep the heavy guarded lane on `demo_salon` only
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md:606` through `docs/runbooks/BOOKING_CONFIRM_VERIFY.md:612` already define the canonical `lock/replay/canary/full` sequence
  - `ops/diagnose.py` already exposes `llm-quality-matrix` and `llm-quality-open-world-closure`; no new runner is missing
- **Five Whys:**
  1. Why is final closure still open after truthful target materialization landed? Because the repo still lacks one current acceptance re-entry package bound to the real target slugs and current artifact state.
  2. Why does that matter? Because without a re-entry contract, teams can drift into stale baseline reuse, beauty-only evidence, or matrix runs that are not tied to the actual closure contract.
  3. Why can't the old acceptance TP be used unchanged? Because it was authored before truthful `clinic_pack/main` and `generic/main` targets existed and before the target-materialization report replaced the old gap.
  4. Why is another acceptance harness not the answer? Because the repo already contains the exact owners for guarded canary runs, multi-pack matrix runs, deterministic scenario generation, and machine-readable closure validation.
  5. Why is this package the truthful next move? Because the remaining residual is now acceptance orchestration and evidence binding, not runtime target materialization or proof-path ownership.
- **Root cause statement:** final consultant-core closure remains blocked because the acceptance lane still lacks one current re-entry package that binds actual runtime targets, refreshed guarded canary evidence, deterministic open-world scenarios, and one machine-readable closure artifact under the existing owners.
- **Fix mechanism:**
  - publish one re-entry TP that locks the actual profile mapping to `demo_salon/main`, `clinic_pack/main`, and `generic/main`
  - require one refreshed guarded `lock -> replay -> canary -> full` chain on `demo_salon` because no recent audited baseline is available
  - require four deterministic scenario artifacts covering `ru`, `kk`, `mixed`, `mixed_translit`, plus `clean/typo`, `canonical/synonym`, and `canonical/variant`
  - run one bounded `llm-quality-matrix` and one `llm-quality-open-world-closure`
  - publish closure only if the machine-readable artifact is valid; otherwise stop with exact reasons/failure families and no runtime fixes inside the block

## Invariant
- no beauty-only evidence may count as final platform closure
- no quality-gate weakening: `judge.enabled`, `infra_valid`, `semantic_valid`, `run_integrity_valid`, `cross_domain_contract`, `scenario_context_contract`, threshold checks, and failure-family checks remain mandatory
- no runtime/core/proof-owner edits count as progress inside the next implementation block; new surfaced failures must become a new package, not inline acceptance-lane patches
- actual runtime targets remain fixed as `beauty -> demo_salon/main`, `clinic_or_dental -> clinic_pack/main`, `generic_service -> generic/main`
- no new acceptance wrapper forest; the surviving owners must stay `scripts/llm_quality_guarded.sh`, `scripts/booking_dialog_scenarios.py`, and `ops/diagnose.py`

## Scope
- publish one package-level TP for truthful acceptance re-entry after runtime target materialization
- lock the actual client/branch mapping for the three required profiles
- lock the guarded canary cadence, deterministic scenario bundle, matrix command, closure command, stop conditions, and evidence paths
- allow only docs/report/canon updates in the implementation block unless the block stops with a truthful `GAP`

## Out of scope
- any new runtime provisioning change
- any consultant runtime-core or frozen-file change
- reopening the proof-path package
- inventing a new acceptance runner or new matrix wrapper
- lowering `platform_evidence_requirement` or `P6` closure gates

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-multi-pack-acceptance-reentry-package-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-runtime-target-materialization-a922.md`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-reentry-a922.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `scripts/booking_dialog_scenarios.py`
- `scripts/llm_quality_guarded.sh`
- `scripts/quality_artifact_report.py`
- `ops/diagnose.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-runtime-target-materialization-a922.md` for the truthful target mapping and integrity evidence
  - `scripts/quality_artifact_report.py` for audited-run inventory before deciding whether a baseline may be reused
  - `scripts/llm_quality_guarded.sh` for the `demo_salon` `lock/replay/canary/full` canary chain
  - `scripts/booking_dialog_scenarios.py` for deterministic open-world `scenarios.json` generation
  - `ops/diagnose.py llm-quality-matrix` for cross-profile LLM stress and `matrix_summary.json`
  - `ops/diagnose.py llm-quality-open-world-closure` for machine-readable closure validation
  - `docs/runbooks/BOOKING_CONFIRM_VERIFY.md` for canonical guarded-run and open-world closure SOP
  - `truffles-api/tests/architecture/test_arch_guard_packet.py` for canon sync verification after TP/report updates
- **External reuse:**
  - official `pytest` parametrization guidance from the single mandatory query above, only if a small deterministic artifact validator needs stable row ids
- **Why this reuse mix is truthful:**
  - the repo already has one canary-runner owner, one deterministic-scenario owner, and one matrix/closure owner
  - reusing those owners deletes the stale pre-materialization acceptance-entry seam instead of moving closure authority into a new wrapper or report-only shortcut

## Plan
1. Publish and register this re-entry TP, then switch canon to it.
2. Freeze the actual profile mapping for the next block: `demo_salon/main`, `clinic_pack/main`, `generic/main`.
3. Re-run the guarded `demo_salon` lane as `lock -> replay -> canary -> full` because no recent audited baseline is available for truthful reuse.
4. Generate four deterministic scenario artifacts covering the required language, surface-noise, semantic-variation, and slot-format profiles.
5. Run one bounded `llm-quality-matrix` across `demo_salon`, `clinic_pack`, and `generic` with `cross-domain-contract block` and `scenario-context-contract block`.
6. Run one `llm-quality-open-world-closure` command against that matrix summary and the deterministic scenario bundle.
7. Publish one bounded report that either proves `valid=true` closure or stops with exact reasons/failure families and a new follow-up package.

## DoD
- this TP locks one truthful acceptance re-entry path after runtime target materialization
- actual target slugs are explicit and no longer inferred from old gap assumptions
- the next block is evidence-only and fail-closed, not a runtime patch block
- canon/session docs point at this package and the next move to implement the re-entry closure bundle
- required architecture/session guards pass

## Checks
- `python3 scripts/quality_artifact_report.py --hours 72 --show-commands && rg -n "demo_salon/main|clinic_pack/main|generic/main|llm-quality-matrix|llm-quality-open-world-closure|lock/replay/canary/full" docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-runtime-target-materialization-a922.md docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `scripts/llm_quality_guarded.sh --help`
- `python3 ops/diagnose.py llm-quality-matrix --help`
- `python3 ops/diagnose.py llm-quality-open-world-closure --help`
- `python3 scripts/booking_dialog_scenarios.py --help`
- `scripts/llm_quality_guarded.sh --mode lock --run-id booking-lock-a922-reentry --pg-checklist /tmp/booking_quality/pg_checklist-a922-reentry.json -- --base-url "$BASE_URL" --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds`
- `scripts/llm_quality_guarded.sh --mode replay --run-id booking-replay-a922-reentry -- --base-url "$BASE_URL" --client-slug demo_salon --scenarios-file /tmp/booking_quality/booking-lock-a922-reentry/scenarios.json --baseline-summary /tmp/booking_quality/booking-lock-a922-reentry/summary.json --count 10 --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds --fail-on-regression --max-failures 20`
- `scripts/llm_quality_guarded.sh --mode canary --run-id booking-canary-a922-reentry -- --base-url "$BASE_URL" --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds --fail-on-regression --baseline-summary /tmp/booking_quality/booking-lock-a922-reentry/summary.json`
- `scripts/llm_quality_guarded.sh --mode full --run-id booking-full-a922-reentry -- --base-url "$BASE_URL" --client-slug demo_salon --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --jid-mode unique --judge-mode all --quality-lane acceptance --run-economy-gate block --fail-on-thresholds --fail-on-regression --baseline-summary /tmp/booking_quality/booking-lock-a922-reentry/summary.json`
- `mkdir -p /tmp/booking_quality/multi-pack-seed-ru-a922-reentry && python3 scripts/booking_dialog_scenarios.py --count 10 --min-turns 10 --max-turns 15 --seed 42 --coverage booking,info,interrupt,handoff --language-profile ru --surface-noise-profile clean --semantic-variation-profile canonical --slot-format-profile canonical --include-media --media-mode text --output /tmp/booking_quality/multi-pack-seed-ru-a922-reentry/scenarios.json`
- `mkdir -p /tmp/booking_quality/multi-pack-seed-kk-a922-reentry && python3 scripts/booking_dialog_scenarios.py --count 10 --min-turns 10 --max-turns 15 --seed 1337 --coverage booking,info,interrupt,handoff --language-profile kk --surface-noise-profile clean --semantic-variation-profile canonical --slot-format-profile canonical --include-media --media-mode text --output /tmp/booking_quality/multi-pack-seed-kk-a922-reentry/scenarios.json`
- `mkdir -p /tmp/booking_quality/multi-pack-seed-mixed-a922-reentry && python3 scripts/booking_dialog_scenarios.py --count 10 --min-turns 10 --max-turns 15 --seed 2026 --coverage booking,info,interrupt,handoff --language-profile mixed --surface-noise-profile typo --semantic-variation-profile synonym --slot-format-profile variant --include-media --media-mode text --output /tmp/booking_quality/multi-pack-seed-mixed-a922-reentry/scenarios.json`
- `mkdir -p /tmp/booking_quality/multi-pack-seed-translit-a922-reentry && python3 scripts/booking_dialog_scenarios.py --count 10 --min-turns 10 --max-turns 15 --seed 9001 --coverage booking,info,interrupt,handoff --language-profile mixed_translit --surface-noise-profile clean --semantic-variation-profile canonical --slot-format-profile canonical --include-media --media-mode text --output /tmp/booking_quality/multi-pack-seed-translit-a922-reentry/scenarios.json`
- `TEST_MODE=1 python3 ops/diagnose.py llm-quality-matrix --client-slugs demo_salon,clinic_pack,generic --branch-slugs main,main,main --run-id-prefix multi-pack-reentry-a922 --cross-domain-contract block --scenario-context-contract block -- --base-url "$BASE_URL" --mode llm --count 10 --min-turns 10 --max-turns 15 --include-media --scenario-coverage booking,info,interrupt,handoff --tool-hooks auto --reset-before-dialog --jid-mode unique --judge-mode all --quality-lane dev --run-economy-gate block --fail-on-thresholds`
- `python3 ops/diagnose.py llm-quality-open-world-closure --matrix-summary /tmp/booking_quality/multi-pack-reentry-a922/matrix_summary.json --deterministic-scenarios /tmp/booking_quality/multi-pack-seed-ru-a922-reentry/scenarios.json --deterministic-scenarios /tmp/booking_quality/multi-pack-seed-kk-a922-reentry/scenarios.json --deterministic-scenarios /tmp/booking_quality/multi-pack-seed-mixed-a922-reentry/scenarios.json --deterministic-scenarios /tmp/booking_quality/multi-pack-seed-translit-a922-reentry/scenarios.json --output /tmp/booking_quality/multi-pack-closure-a922-reentry.json --pretty`
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
- one bounded re-entry report in `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-acceptance-reentry-a922.md`
- runtime target truth reused from `docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-runtime-target-materialization-a922.md` plus `/tmp/a922-target-db-truth.json`
- guarded canary artifacts from the next block:
  - `/tmp/booking_quality/booking-lock-a922-reentry/summary.json`
  - `/tmp/booking_quality/booking-replay-a922-reentry/summary.json`
  - `/tmp/booking_quality/booking-canary-a922-reentry/summary.json`
  - `/tmp/booking_quality/booking-full-a922-reentry/summary.json`
- deterministic scenario artifacts from the next block:
  - `/tmp/booking_quality/multi-pack-seed-ru-a922-reentry/scenarios.json`
  - `/tmp/booking_quality/multi-pack-seed-kk-a922-reentry/scenarios.json`
  - `/tmp/booking_quality/multi-pack-seed-mixed-a922-reentry/scenarios.json`
  - `/tmp/booking_quality/multi-pack-seed-translit-a922-reentry/scenarios.json`
- matrix/closure artifacts from the next block:
  - `/tmp/booking_quality/multi-pack-reentry-a922/matrix_summary.json`
  - `/tmp/booking_quality/multi-pack-closure-a922-reentry.json`
- `STATE.md` entry naming either the deleted stale acceptance-entry seam or the exact `GAP` reasons/failure families that blocked closure

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Max matrix runs:** `1`
- **Max deterministic seed bundle generations:** `1`
- **Cheap deterministic gates first:** quality artifact inventory, command `--help` checks, and target-mapping/report verification before any expensive run
- **Reuse policy:** do not reuse stale or unaudited canary artifacts; because the current 72-hour inventory is empty, refresh the guarded `demo_salon` baseline once in the next block
- **Stop condition:** if any guarded run is invalid, any deterministic scenario artifact is missing required profiles, any matrix row violates contract gates, or the closure artifact returns `valid=false`, stop and publish `GAP` rather than patching runtime or rerunning blindly
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** the next implementation block is evidence-only against the current runtime; no runtime/core rollout is planned
- **Go/no-go signals:**
  - guarded `demo_salon` `lock/replay/canary/full` chain is valid under current gates
  - deterministic scenario bundle covers `ru`, `kk`, `mixed`, `mixed_translit`, plus `clean/typo`, `canonical/synonym`, and `canonical/variant`
  - `matrix_summary.json` reports `cross_domain_contract.required=true`, `cross_domain_contract.valid=true`, and `all_ok=true`
  - `llm-quality-open-world-closure` returns `valid=true`
  - no unresolved `failure_families` or closure `reasons`
- **Rollback:**
  - revert this block's doc/canon changes only
  - do not keep any closure claim if the machine-readable artifact is invalid or missing
- **Rollback verification:**
  - `python3 scripts/build_agent_packet.py --check`
  - `python3 scripts/arch_guard.py`
  - `pytest -q truffles-api/tests/architecture`
- **Post-release monitoring window:** immediate closure review only; any later invalidation reopens the program as `BLOCKED`

## Rollback
- Revert the docs/report/canon files touched by this block and rerun the required guards.

## No-go
- Do not count `demo_salon`-only evidence as final closure.
- Do not skip `clinic_pack` or `generic` in the matrix/closure bundle.
- Do not weaken `judge`, `cross_domain_contract`, `scenario_context_contract`, threshold, or failure-family gates to make re-entry look green.
- Do not patch runtime/core/proof ownership inside the next implementation block.
- Do not invent a new acceptance runner, new matrix wrapper, or report-only shortcut before exhausting existing owners.
- Do not claim consultant correctness or full business-agnostic closure without a valid `llm-quality-open-world-closure` artifact.

## Risks / blockers
- guarded `demo_salon` runs may surface a new failure family unrelated to target materialization; that must split into a new package instead of being fixed inside re-entry
- `clinic_pack` or `generic` matrix rows may expose domain-pack or scenario-context failures that were invisible under beauty-only evidence
- deterministic scenario generation may fail to cover one required profile if the seed bundle is assembled incorrectly
- the closure artifact may still fail despite green matrix rows if deterministic coverage or failure-family hygiene is incomplete

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- consultant runtime cutover remains incomplete overall even after truthful target materialization
- the operator-facing onboarding autopilot action ledger still over-reports `knowledge_publish_failed` despite published rows existing
- final program closure still depends on new acceptance evidence that does not exist yet

### Why not in this block
- this block only locks the truthful re-entry contract for the final evidence lane
- runtime/provisioning changes are already finished for the current failure family and must not be reopened here

### Risk if deferred
- teams can drift into stale baseline reuse or beauty-only acceptance claims again
- the final closure step remains narrative instead of machine-readable
- expensive runs can happen without one fixed evidence contract and stop condition set

### Linked follow-up Task Package(s)
- implementation of this re-entry package
- if blocked: one new failure-family TP authored from `matrix_summary.json` / `multi-pack-closure-a922-reentry.json`

### Expiry/trigger to stop deferral
- stop deferral immediately if anyone tries to close the program without `clinic_pack` + `generic` matrix evidence and a valid `llm-quality-open-world-closure` artifact

## Next-block contract (mandatory)
### Next block objective
- implement one bounded acceptance re-entry closure bundle using actual targets `demo_salon/main`, `clinic_pack/main`, and `generic/main`, then publish either a valid machine-readable closure artifact or an exact `GAP`

### First deterministic check command
- `python3 scripts/quality_artifact_report.py --hours 72 --show-commands && rg -n "demo_salon/main|clinic_pack/main|generic/main|llm-quality-matrix|llm-quality-open-world-closure|lock/replay/canary/full" docs/REPORTS/artifacts/2026-03-18-consultant-core-multi-pack-runtime-target-materialization-a922.md docs/runbooks/BOOKING_CONFIRM_VERIFY.md`

### Blocked-by conditions
- any guarded canary run lacks valid preflight, judge, or artifact integrity
- deterministic scenario bundle misses any required language / noise / semantic / slot-format profile
- any `llm-quality-matrix` row fails `cross_domain_contract`, `scenario_context_contract`, threshold, run-integrity, or failure-family gates
- the only way to make the bundle pass is runtime/core/proof-owner edits or gate weakening

### Owner role for closure
- Brain / Top Architect
