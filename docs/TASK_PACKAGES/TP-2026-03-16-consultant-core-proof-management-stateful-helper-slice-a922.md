# TP-2026-03-16-consultant-core-proof-management-stateful-helper-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PROOF-MANAGEMENT-STATEFUL-HELPER-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PROOF-BOOKING-PROGRESS-HELPER-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-booking-progress-helper-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-CONTROLLER-ROUTE-BRIDGE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Снять последний bounded management/stateful proof-only seam: вынести remaining reschedule/check-booking/generic-booking predicates, malformed/stateful normalize helpers, и ambiguous-time expectation shaper из `scripts/booking_dialog_scenarios.py` в shared `truffles-api/app/services/llm_quality_contracts.py`, чтобы proof script перестал владеть этим helper family, а `BookingScenarioPostCoverageRepairCallbacks` схлопнулся до config-only carrier.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-booking-progress-helper-slice-a922.md`
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
  - `sed -n '1,90p' scripts/booking_dialog_scenarios.py`
  - `sed -n '1360,1565p' truffles-api/app/services/llm_quality_contracts.py`
  - `sed -n '3330,3515p' truffles-api/app/services/llm_quality_contracts.py`
  - `rg -n 'malformed_check_booking|reschedule_followup|check_booking_followup|ambiguous_time_fill|generic_booking_request' truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `FACT findings`:
  - proof script now imports the remaining management/stateful helpers from shared code, but the current block is not closed because callback wiring and direct coverage are not finished.
  - `BookingScenarioPostCoverageRepairCallbacks` in shared code has already been reduced to config-only, but `scripts/booking_dialog_scenarios.py` still instantiates removed callback fields and will fail at runtime when repair executes.
  - new helper functions exist in `truffles-api/app/services/llm_quality_contracts.py`, but they are not exported through `__all__`, so the shared-module contract is incomplete.
  - deterministic sanitize/repair tests already exist for malformed check-booking, reschedule followup, check-booking followup, and ambiguous time repair, so this seam can stay bounded and proof-only.
- `Detected drift (docs vs code)`: proof path is still not a thin wrapper because this last management/stateful helper family is only partially extracted and not yet closed with runtime-safe callback wiring + explicit shared-helper coverage.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/copy.html Python copy deepcopy documentation`
- **Date/time (local):** `2026-03-16 11:05 +05`
- **Why this query is precise:** the extracted expectation helper mutates nested `meta_any` / `trace_contains` payloads; the block must keep detached copies in shared helpers instead of leaking mutable aliases across calls.
- **Sources opened (from this query):**
  - `Python Standard Library — copy` — `https://docs.python.org/3/library/copy.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy()` is the standard library mechanism for detached nested copies when a helper must return a new mutable structure without aliasing previous callers.
- **Decision:** `reuse + integrate` — keep shared expectation helpers and callback/config payloads using detached copies via `deepcopy`, instead of adding proof-script wrappers or shared mutable defaults.
- **Rejected options:**
  - leaving the remaining helper family in the proof script
  - widening the block into runtime or frozen-router edits
  - keeping extracted helpers hidden without shared-module exports
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** the previous proof extraction left a partially-finished management/stateful seam.
- **Minimal reproduction:**
  1. Open `scripts/booking_dialog_scenarios.py` around `_BOOKING_SCENARIO_POST_COVERAGE_REPAIR_CALLBACKS`.
  2. Observe that the script still passes removed callback fields into `BookingScenarioPostCoverageRepairCallbacks(...)`.
  3. Open `truffles-api/app/services/llm_quality_contracts.py` and observe that the shared dataclass only accepts `service_candidates` while the newly added helper functions are not exported through `__all__`.
- **Evidence to capture:**
  - config-only callback bundle in `scripts/booking_dialog_scenarios.py`
  - exported shared helper family in `truffles-api/app/services/llm_quality_contracts.py`
  - direct deterministic coverage for the extracted helpers
  - unchanged sanitize/repair outputs for malformed/stateful followup cases
- **Five Whys (or equivalent):**
  1. Why is proof-path excision still incomplete? Because the last management/stateful helper family is only partially moved.
  2. Why is that dangerous? Because runtime repair entry still instantiates obsolete callback fields and shared-module imports remain incomplete.
  3. Why not jump back to runtime now? Because this is the last similarly-sized proof seam and closing it prevents carrying half-extracted proof ownership forward.
  4. Why is the block safe? Because affected behavior is deterministic and already covered by focused sanitize/repair tests.
  5. Why does this reduce drift? Because it removes one more semantic helper family from the proof-only file and finishes the callback contraction cleanly.
- **Root cause statement:** management/stateful proof helpers were extracted incrementally, but the extraction stopped before callback wiring, exports, and direct shared-helper coverage were finished, leaving a half-migrated proof seam.
- **Fix mechanism:**
  - finalize shared helper exports in `truffles-api/app/services/llm_quality_contracts.py`
  - collapse script callback wiring to config-only
  - add direct deterministic coverage for the extracted helpers
  - keep sanitize/repair regression coverage green

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing shared `truffles-api/app/services/llm_quality_contracts.py`
  - existing `BookingScenarioPostCoverageRepairCallbacks` dataclass
  - existing sanitize/repair deterministic tests in `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- **External reuse:**
  - official Python `copy` documentation
- **Why not reinvent the wheel:** the repo already has a shared proof-helper module and deep-copy pattern for detached expectation payloads; this block should finish that pattern instead of adding another wrapper layer.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `20`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded proof-path closeout with deterministic tests and no runtime/frozen-router edits.

## Invariant
- No edits in frozen legacy semantic router files.
- No runtime behavior changes.
- No new proof-only helper ownership added to `scripts/booking_dialog_scenarios.py`.
- Malformed/stateful sanitize and repair outputs stay intact for covered cases.

## Scope
- Finish shared export/wiring for the management/stateful proof helper family.
- Collapse `_BOOKING_SCENARIO_POST_COVERAGE_REPAIR_CALLBACKS` to config-only.
- Add direct deterministic shared-helper coverage.
- Sync canon/session artifacts.

## Out of scope
- runtime semantic cutover
- continuity collapse
- neutral runtime work
- multi-pack acceptance
- frozen router edits
- any new proof block beyond this last management/stateful seam

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-management-stateful-helper-slice-a922.md`
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
2. Finalize shared helper exports in `truffles-api/app/services/llm_quality_contracts.py`.
3. Collapse `_BOOKING_SCENARIO_POST_COVERAGE_REPAIR_CALLBACKS` to config-only in `scripts/booking_dialog_scenarios.py`.
4. Add direct deterministic shared-helper tests plus targeted sanitize/repair regression coverage.
5. Run focused proof checks, then required architecture/packet/session checks.
6. Sync canon/session artifacts.

## DoD
- shared management/stateful helper family is exported from `truffles-api/app/services/llm_quality_contracts.py`
- `scripts/booking_dialog_scenarios.py` uses a config-only callback bundle
- deterministic shared-helper coverage exists for the extracted helper family
- sanitize/repair regression coverage remains green
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
- config-only `_BOOKING_SCENARIO_POST_COVERAGE_REPAIR_CALLBACKS`
- shared helper exports in `truffles-api/app/services/llm_quality_contracts.py`
- direct deterministic helper tests in `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- unchanged sanitize/repair behavior for malformed/stateful cases
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
- **Post-release monitoring window:** after this block, switch focus back to richer runtime semantic cutover

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the management/stateful helper closeout actually implemented.

## Rollback
- Revert this TP's shared-helper, script, test, and doc changes only.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No new runtime semantic branches.
- No duplicate ownership of the extracted helper family in both the script and the shared module.

## Risks/Blockers
- helper export/wiring may accidentally drift malformed check-booking or reschedule followup repair outputs.
- ambiguous-time helper extraction may accidentally mutate nested expectation payloads by reference.
- if direct helper tests or sanitize/repair tests drift, the block is not done.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: runtime semantic ownership, remaining proof-script orchestration wrappers, continuity collapse, neutral runtime, and multi-pack acceptance remain open.
- `Why not in this block`: this slice only closes the last similarly-sized proof helper family and keeps the block bounded inside proof-path excision.
- `Risk if deferred`: proof script would carry a half-migrated callback seam and incomplete shared helper contract into the next runtime block.
- `Linked follow-up Task Package(s)`: `TP-2026-03-16-consultant-core-controller-route-bridge-a922`
- `Expiry/trigger to stop deferral`: before any new runtime semantic cutover claims that proof path is thin enough for the migrated slice.

## Next-block contract (mandatory)
- `Next block objective`: switch back to richer semantic cutover in `reasoning_core`, starting with the controller-route bridge.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_reasoning_core.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: proof helper outputs drift; source-of-truth/session metadata not synced; architecture guard fails.
- `Owner role for closure`: `Top Architect`
