# TP-2026-03-16-consultant-core-proof-booking-progress-helper-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PROOF-BOOKING-PROGRESS-HELPER-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PROOF-MASTER-SPECIALIST-FOLLOWUP-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-master-specialist-followup-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTROLLER-ROUTE-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Снять следующий bounded proof-only seam: вынести remaining booking-progress expectation helper family из `scripts/booking_dialog_scenarios.py` в shared `truffles-api/app/services/llm_quality_contracts.py`, чтобы proof script перестал владеть multi-service clarify, service-grounded booking progress, exact/partial time collect, grounded partial-date daypart fill, и active-name time availability followup shaping.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-master-specialist-followup-slice-a922.md`
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
  - `sed -n '1670,2305p' scripts/booking_dialog_scenarios.py`
  - `sed -n '2668,2948p' truffles-api/app/services/llm_quality_contracts.py`
  - `rg -n 'multi_service_booking_clarify|catalog_service_booking_progress|booking_time_availability_followup|grounded_partial_date_daypart_fill' truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `FACT findings`:
  - proof-only `scripts/booking_dialog_scenarios.py` still owns the remaining booking-progress expectation family: service-grounded booking predicates plus the related expectation shapers used by `_sanitize_llm_turns(...)`.
  - shared `repair_booking_scenario_post_coverage_dialogs(...)` still depends on callback fields for six of those apply-functions, which means the proof script still owns a medium-sized expectation family even after the master/specialist extraction.
  - adjacent predicates and normalize helpers for slot/time/master-specialist flows already live in `truffles-api/app/services/llm_quality_contracts.py`, so remaining proof-only ownership is now concentrated in booking-progress shaping rather than scattered across unrelated concerns.
  - deterministic coverage already exists for service-grounded booking reply-type repair, multi-service clarify, grounded partial-date daypart fill, catalog service booking progress, and active-name time availability followup preservation.
- `Detected drift (docs vs code)`: proof path is still not close enough to a thin wrapper because the remaining booking-progress expectation family still lives only in the proof script.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/dataclasses.html Python dataclasses field default_factory documentation`
- **Date/time (local):** `2026-03-16 10:34 +05`
- **Why this query is precise:** this block is expected to shrink `BookingScenarioPostCoverageRepairCallbacks` again; the cleanest bounded shape is to keep remaining runtime-free configuration as dataclass data instead of adding new proof-script wrappers.
- **Sources opened (from this query):**
  - `Python Standard Library — dataclasses` — `https://docs.python.org/3/library/dataclasses.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `dataclasses.field(default_factory=...)` is the standard way to attach immutable default container/config payloads to a dataclass without sharing mutable state across instances.
- **Decision:** `reuse + integrate` — shrink `BookingScenarioPostCoverageRepairCallbacks` by replacing extracted apply-callback ownership with shared functions plus a dataclass config field for service candidates, instead of adding more script-local wrappers.
- **Rejected options:**
  - leaving the booking-progress helper family in the proof script
  - widening the block into runtime or frozen-router edits
  - keeping extracted helpers behind a new layer of script-local wrapper callbacks
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** proof-only booking-scenario generation still owns the remaining booking-progress expectation helper family.
- **Minimal reproduction:**
  1. Open `scripts/booking_dialog_scenarios.py` around `_apply_service_grounded_booking_expectations(...)` through `_apply_active_name_time_availability_followup_expectations(...)`.
  2. Observe that `_sanitize_llm_turns(...)` still calls those script-local helpers directly.
  3. Open `truffles-api/app/services/llm_quality_contracts.py` and observe that `BookingScenarioPostCoverageRepairCallbacks` still requires six callback fields for that family.
- **Evidence to capture:**
  - shared booking-progress helper family exists in `truffles-api/app/services/llm_quality_contracts.py`
  - `scripts/booking_dialog_scenarios.py` no longer defines the extracted booking-progress helper family locally
  - `BookingScenarioPostCoverageRepairCallbacks` shrinks for the extracted helper subset
  - deterministic booking-progress sanitize/repair tests stay green
- **Five Whys (or equivalent):**
  1. Why is proof path still semantically thick? Because booking-progress expectation helpers still live only in the script.
  2. Why does that matter? Because both sanitize and post-coverage repair still depend on proof-only ownership for those reply-type/contract shapers.
  3. Why is this the right next bounded seam? Because it is the next largest remaining pure helper family and does not require runtime or frozen-router edits.
  4. Why is extraction safe? Because behavior is deterministic and already covered by focused booking-scenario tests.
  5. Why does this reduce drift? Because one more reusable helper family stops living in the file that should converge toward a thin wrapper.
- **Root cause statement:** remaining booking-progress expectation shaping stayed concentrated in `scripts/booking_dialog_scenarios.py`, so proof-only code still owns a medium-sized semantic helper family used by both sanitize and repair flows.
- **Fix mechanism:**
  - move the bounded booking-progress helper family into `truffles-api/app/services/llm_quality_contracts.py`
  - rewire `scripts/booking_dialog_scenarios.py` to import those shared helpers
  - shrink `BookingScenarioPostCoverageRepairCallbacks` for helper functions that no longer require proof-script ownership
  - keep behavior locked by deterministic booking-progress sanitize and repair tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing shared `truffles-api/app/services/llm_quality_contracts.py`
  - existing slot/time/master-specialist helper primitives already extracted there
  - existing deterministic booking-scenario tests for service-grounded booking, multi-service clarify, time collect, and followup preservation
- **External reuse:**
  - official Python `dataclasses` documentation
- **Why not reinvent the wheel:** the repo already has the shared helper module and dataclass-based repair pipeline; this block should extend that existing pattern instead of inventing another proof-only indirection layer.

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
- Booking-progress sanitize and repair outputs stay intact for covered cases.

## Scope
- Move bounded booking-progress helper family into `truffles-api/app/services/llm_quality_contracts.py`.
- Rewire `scripts/booking_dialog_scenarios.py` to import those helpers.
- Shrink `BookingScenarioPostCoverageRepairCallbacks` for helper functions that no longer require script ownership.
- Add or update deterministic booking-progress coverage.
- Sync canon/session artifacts.

## Out of scope
- runtime semantic cutover
- continuity collapse
- neutral runtime work
- multi-pack acceptance
- frozen router edits
- malformed-check-booking, reschedule, or check-booking followup helper extraction
- any new proof block beyond this bounded booking-progress seam

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-booking-progress-helper-slice-a922.md`
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
2. Add shared booking-progress helper family to `truffles-api/app/services/llm_quality_contracts.py`.
3. Rewire `scripts/booking_dialog_scenarios.py` to import those helpers and remove local ownership.
4. Shrink `BookingScenarioPostCoverageRepairCallbacks` for the extracted helper subset.
5. Revalidate deterministic booking-scenario tests and required guards.
6. Sync canon/session artifacts.

## DoD
- shared booking-progress helper family exists in `truffles-api/app/services/llm_quality_contracts.py`
- `scripts/booking_dialog_scenarios.py` no longer defines the extracted booking-progress helper family locally
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
- shared booking-progress helper family in `truffles-api/app/services/llm_quality_contracts.py`
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
- **Post-release monitoring window:** after this block, either take one last similarly bounded proof seam or switch back to richer runtime cutover

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the booking-progress helper extraction actually implemented.

## Rollback
- Revert this TP's shared-helper, script, test, and doc changes only.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No new runtime semantic branches.
- No duplicate ownership of the extracted booking-progress helper family in both the script and the shared module.

## Risks/Blockers
- helper extraction may accidentally drift booking-progress `meta_any` or `trace_contains` payloads.
- callback shrinkage may accidentally change post-coverage repair behavior for multi-service clarify, service-grounded progress interrupts, or active-name time followups.
- if deterministic booking-progress sanitize/repair outputs drift, the block is not done.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: malformed-check-booking and management followup helper ownership, runtime semantic ownership, continuity collapse, neutral runtime, and multi-pack acceptance remain open.
- `Why not in this block`: this slice only removes the bounded booking-progress helper family and keeps the block safely inside proof-path excision.
- `Risk if deferred`: proof-only script would still own the remaining booking-progress expectation family and callback bundle would remain wider than necessary.
- `Linked follow-up Task Package(s)`: `TP-2026-03-16-consultant-core-controller-route-bridge-a922`
- `Expiry/trigger to stop deferral`: before claiming proof path is black-box for booking scenarios or before adding any new booking-progress helper to the script.

## Next-block contract (mandatory)
- `Next block objective`: if one more proof seam of similar size remains after this extraction, take only that bounded seam; otherwise return to richer semantic cutover in `reasoning_core`.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: booking-progress helper outputs drift; source-of-truth/session metadata not synced; architecture guard fails.
- `Owner role for closure`: `Top Architect`
