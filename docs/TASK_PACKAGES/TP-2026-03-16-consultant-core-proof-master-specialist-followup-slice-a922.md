# TP-2026-03-16-consultant-core-proof-master-specialist-followup-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PROOF-MASTER-SPECIALIST-FOLLOWUP-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PROOF-PENDING-QUESTION-CONTRACT-HELPER-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-pending-question-contract-helper-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTROLLER-ROUTE-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Снять следующий high-ROI proof-only seam: вынести master/specialist followup helper family из `scripts/booking_dialog_scenarios.py` в shared `truffles-api/app/services/llm_quality_contracts.py`, чтобы proof script перестал владеть specialist-reference detection, master-tag normalization, и specialist/master followup expectation shaping.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-pending-question-contract-helper-slice-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `scripts/booking_dialog_scenarios.py`
- `truffles-api/app/services/llm_quality_contracts.py`
- `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/services/llm_quality_contracts.py`
  - `scripts/booking_dialog_scenarios.py`
  - `truffles-api/tests/test_booking_dialog_scenarios_script.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `sed -n '1668,2068p' scripts/booking_dialog_scenarios.py`
  - `sed -n '2628,3068p' scripts/booking_dialog_scenarios.py`
  - `rg -n 'specialist|master_info|specialist_availability_followup|booking_specialist_followup' truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `FACT findings`:
  - proof-only `scripts/booking_dialog_scenarios.py` still owns the main master/specialist followup seam: specialist-reference predicates, master-tag normalization, and specialist/master expectation shapers.
  - `truffles-api/app/services/llm_quality_contracts.py` already owns adjacent primitives: specialist-reference regex patterns, generic-master question predicates, grounded specialist availability transition predicates, pending-question target inference, and active-time specialist followup compiler support.
  - shared post-coverage repair still depends on script callbacks for `normalize_active_time_specialist_master_tags`, `normalize_active_time_master_info_tags`, `apply_active_time_specialist_followup_expectations`, and `apply_active_time_master_info_interrupt_expectations`, which means the proof script still owns a large semantic helper family.
  - deterministic coverage already exists for active-name specialist followups, generic master info interrupts, specialist availability followups, and post-coverage repair preservation paths.
- `Detected drift (docs vs code)`: proof path is still not a thin wrapper because master/specialist semantic helper ownership remains in the proof script.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/re.html Python re module compile search pattern documentation`
- **Date/time (local):** `2026-03-16 10:09 +05`
- **Why this query is precise:** this block moves regex-backed specialist/master predicates into shared code and must keep compiled-pattern behavior deterministic without inventing a new pattern protocol.
- **Sources opened (from this query):**
  - `Python Standard Library — re` — `https://docs.python.org/3/library/re.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** Python `re` compiled patterns are intended to be reused for repeated searches and are safe to keep as module-level constants; that matches the shared extraction shape for specialist/master predicates.
- **Decision:** `reuse + integrate` — keep regex patterns as shared module-level compiled constants in `llm_quality_contracts.py` and route script helpers through imported shared functions instead of inventing a new DSL or callback protocol.
- **Rejected options:**
  - leaving regex-backed specialist/master ownership in the script
  - introducing a second pattern registry only for proof-path code
  - widening the block into runtime or frozen-router edits
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** proof-only booking-scenario generation still owns the largest remaining master/specialist followup helper family.
- **Minimal reproduction:**
  1. Open `scripts/booking_dialog_scenarios.py` around `_looks_like_specialist_reference(...)`, `_normalize_active_*master*_tags(...)`, and `_apply_*master*/specialist*expectations(...)`.
  2. Observe that `_sanitize_llm_turns(...)` and shared post-coverage repair both depend on those script-local helpers.
  3. Note that adjacent predicates and normalization primitives already live in `truffles-api/app/services/llm_quality_contracts.py`, so proof-only ownership is now fragmented and inconsistent.
- **Evidence to capture:**
  - shared master/specialist helper family exists in `truffles-api/app/services/llm_quality_contracts.py`
  - script imports the new shared helpers instead of defining them locally
  - `BookingScenarioPostCoverageRepairCallbacks` shrinks again because fewer specialist/master functions remain script-owned
  - deterministic specialist/master sanitize/repair tests stay green
- **Five Whys (or equivalent):**
  1. Why does proof path still own semantics? Because master/specialist followup helpers still live only in the script.
  2. Why is that a problem? Because both sanitize and repair flows depend on proof-only ownership for specialist/master retagging and expectation shaping.
  3. Why is this seam the best ROI? Because it is the largest remaining pure helper family and already sits next to extracted shared primitives.
  4. Why is extraction safe? Because the helpers are deterministic, regex-backed, and covered by focused sanitize/repair tests.
  5. Why does this reduce drift? Because one more large proof-only semantic family stops living in the file that should converge toward a thin wrapper.
- **Root cause statement:** master/specialist followup semantics remained concentrated in `scripts/booking_dialog_scenarios.py`, so proof-only code still owns the largest remaining pure helper family for specialist/master retagging and expectation shaping.
- **Fix mechanism:**
  - move the bounded master/specialist helper family into `truffles-api/app/services/llm_quality_contracts.py`
  - import those shared helpers back into `scripts/booking_dialog_scenarios.py`
  - shrink `BookingScenarioPostCoverageRepairCallbacks` for helper functions that no longer require script ownership
  - keep behavior locked by deterministic specialist/master sanitize and repair tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing shared `truffles-api/app/services/llm_quality_contracts.py`
  - existing specialist/master regex patterns and generic-master predicates already in that shared module
  - existing deterministic booking-scenario tests for specialist/master flows
- **External reuse:**
  - official Python `re` documentation
- **Why not reinvent the wheel:** the repo already has the shared module and compiled-pattern approach; this block extends that pattern instead of creating a proof-only registry.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `19`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded proof-path extraction with deterministic tests and no runtime/frozen-router edits.

## Invariant
- No edits in frozen legacy semantic router files.
- No runtime behavior changes.
- No new proof-only helper ownership added to `scripts/booking_dialog_scenarios.py`.
- Specialist/master sanitize and repair outputs stay intact for covered cases.

## Scope
- Move bounded specialist/master helper family into `truffles-api/app/services/llm_quality_contracts.py`.
- Rewire `scripts/booking_dialog_scenarios.py` to import those helpers.
- Shrink `BookingScenarioPostCoverageRepairCallbacks` for helper functions that no longer require script ownership.
- Add or update deterministic specialist/master coverage.
- Sync canon/session artifacts.

## Out of scope
- runtime semantic cutover
- continuity collapse
- neutral runtime work
- multi-pack acceptance
- frozen router edits
- reschedule/check-booking helper extraction
- generic multi-service helper extraction outside the touched master/specialist seam

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-master-specialist-followup-slice-a922.md`
- `truffles-api/app/services/llm_quality_contracts.py`
- `scripts/booking_dialog_scenarios.py`
- `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `STRUCTURE.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`

## Plan (1..N)
1. Publish this TP with RCA and one web search.
2. Add shared master/specialist helper family to `truffles-api/app/services/llm_quality_contracts.py`.
3. Rewire `scripts/booking_dialog_scenarios.py` to import those helpers and remove local ownership.
4. Shrink the post-coverage repair callback bundle where shared helper ownership becomes sufficient.
5. Revalidate deterministic booking-scenario tests and required guards.
6. Sync canon/session artifacts.

## DoD
- shared master/specialist helper family exists in `truffles-api/app/services/llm_quality_contracts.py`
- `scripts/booking_dialog_scenarios.py` no longer defines the extracted specialist/master helper family locally
- `BookingScenarioPostCoverageRepairCallbacks` shrinks for the extracted helper subset
- deterministic booking-scenario tests remain green
- proof-path architecture checks remain green

## Checks
- `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- shared master/specialist helper family in `truffles-api/app/services/llm_quality_contracts.py`
- script imports/delegates instead of defining the extracted helper family locally
- smaller callback bundle in `scripts/booking_dialog_scenarios.py`
- deterministic booking-scenario coverage in `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- synced source-of-truth/session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if the block requires runtime behavior changes or frozen-router edits, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** deterministic proof-path extraction only; no runtime code-path changes
- **Go/no-go signals:** booking-scenario tests + quality-response-guard + runtime-contract tests + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's shared-helper/script/test/doc changes only
- **Post-release monitoring window:** next block should either finish the remaining proof seams only if still bounded or switch back to richer runtime cutover

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the master/specialist helper extraction actually implemented.

## Rollback
- Revert this TP's shared-helper, script, test, and doc changes only.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No new runtime semantic branches.
- No duplicate ownership of the extracted specialist/master helper family in both the script and the shared module.

## Risks/Blockers
- helper extraction may accidentally drift specialist/master `meta_any` or `trace_contains` payloads.
- callback shrinkage may accidentally change post-coverage repair behavior for active-name or active-time specialist followups.
- if deterministic specialist/master sanitize/repair outputs drift, the block is not done.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: generic multi-service/service-grounded helper ownership, reschedule/check-booking helper ownership, runtime semantic ownership, continuity collapse, neutral runtime, and multi-pack acceptance remain open.
- `Why not in this block`: this slice only removes the high-ROI master/specialist family and keeps the block bounded.
- `Risk if deferred`: proof-only script would still own the largest remaining specialist/master semantic family.
- `Linked follow-up Task Package(s)`: `TP-2026-03-16-consultant-core-controller-route-bridge-a922`
- `Expiry/trigger to stop deferral`: before claiming proof path is black-box for booking scenarios or before adding any new specialist/master helper to the script.

## Next-block contract (mandatory)
- `Next block objective`: if no bounded proof seam of similar ROI remains, return to richer semantic cutover in `reasoning_core`; otherwise take only one more bounded proof seam.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: specialist/master helper outputs drift; source-of-truth/session metadata not synced; architecture guard fails.
- `Owner role for closure`: `Top Architect`
