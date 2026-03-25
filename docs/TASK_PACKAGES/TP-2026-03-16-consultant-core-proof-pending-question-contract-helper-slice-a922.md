# TP-2026-03-16-consultant-core-proof-pending-question-contract-helper-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-PROOF-PENDING-QUESTION-CONTRACT-HELPER-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PROOF-POST-COVERAGE-REWRITE-EXCISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-post-coverage-rewrite-excision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PROOF-MASTER-SPECIALIST-FOLLOWUP-SLICE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Снять еще один proof-only seam: вынести pending-question contract/helper family из `scripts/booking_dialog_scenarios.py` в shared `truffles-api/app/services/llm_quality_contracts.py`, чтобы script перестал быть owner для contract-reason/context progression и pure interrupt/cancel expectation shaping.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-post-coverage-rewrite-excision-a922.md`
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
  - `rg -n 'ACTIVE_PENDING_QUESTION_INFO_INTERRUPT_TAGS|PENDING_QUESTION_CONTEXT_PRESERVE_TAGS|_expectation_has_contract_reason|_advance_pending_question_context|_advance_multi_service_clarify_context|_advance_partial_date_anchor_context' scripts/booking_dialog_scenarios.py truffles-api/app/services/llm_quality_contracts.py`
  - `sed -n '2176,3325p' scripts/booking_dialog_scenarios.py`
  - `sed -n '1760,2095p' truffles-api/app/services/llm_quality_contracts.py`
- `FACT findings`:
  - proof-only `scripts/booking_dialog_scenarios.py` still owned the pure pending-question contract helpers used by both `_sanitize_llm_turns(...)` and shared post-coverage repair orchestration.
  - the current `BookingScenarioPostCoverageRepairCallbacks` dataclass still had callback fields for pure interrupt/cancel/context-progression helpers that do not need script-local ownership.
  - deterministic booking-scenario tests already cover these semantics through sanitize/repair flows, so the block can stay bounded and runtime-free.
- `Detected drift (docs vs code)`: proof path was still not a thin wrapper because contract-reason/context progression and pure info/cancel expectation shaping lived only in the script.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org/3/library/copy.html Python copy.deepcopy nested dict list documentation`
- **Date/time (local):** `2026-03-16 11:26 +05`
- **Why this query is precise:** this block moves nested `expect/meta/meta_any/trace_contains` shaping into shared code and needs detached payload updates without aliasing old script-owned structures.
- **Sources opened (from this query):**
  - `Python Standard Library — copy` — `https://docs.python.org/3/library/copy.html`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy` is the standard-library mechanism for detached nested copies of mutable dict/list payloads; it fits the shared-helper extraction because the helper family rewrites nested expectation payloads in place.
- **Decision:** `reuse + integrate` — keep using `deepcopy` for detached nested expectation payloads in shared helpers instead of inventing ad-hoc copy rules.
- **Rejected options:**
  - leaving pure helper ownership in the script and only documenting it
  - adding partial shallow-copy rules per helper branch
  - widening the block into runtime or frozen-router code
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** proof-only booking-scenario generation still owned pending-question contract progression and pure interrupt/cancel expectation shaping.
- **Minimal reproduction:**
  1. Open `scripts/booking_dialog_scenarios.py` around `_apply_active_pending_question_info_interrupt_expectations(...)`, `_clear_multi_service_info_interrupt_followup_expectations(...)`, `_apply_active_pending_question_cancel_interrupt_expectations(...)`, and `_advance_*` helpers.
  2. Observe that `_sanitize_llm_turns(...)` and shared post-coverage repair both depend on those functions.
  3. Note that these helpers are deterministic and do not require script-local randomness or runtime state, yet remained proof-script-owned.
- **Evidence to capture:**
  - shared helper family exists in `truffles-api/app/services/llm_quality_contracts.py`
  - script imports/delegates to shared helpers instead of defining them locally
  - callback bundle shrinks because pure helpers are no longer passed from the script
  - deterministic tests remain green
- **Five Whys (or equivalent):**
  1. Why does proof path still own semantics? Because pure pending-question helpers remained defined only in the script.
  2. Why is that a problem? Because both sanitize and repair flows depended on proof-only ownership for contract progression.
  3. Why are these helpers safe to extract? Because they are deterministic, nested-payload shapers with no runtime side effects.
  4. Why not keep them as callbacks? Because callback wiring was preserving unnecessary script ownership for logic that already fits the shared contracts module.
  5. Why does this reduce drift? Because one more shared semantic family stops living in the file that should converge toward a thin wrapper.
- **Root cause statement:** pure pending-question contract helpers stayed in `scripts/booking_dialog_scenarios.py`, so proof-only code remained the owner of deterministic contract progression and interrupt/cancel expectation shaping even after prior helper and orchestration extractions.
- **Fix mechanism:**
  - move the pure pending-question helper family into `truffles-api/app/services/llm_quality_contracts.py`
  - let the script import those shared helpers instead of defining them locally
  - remove now-unnecessary callback fields from `BookingScenarioPostCoverageRepairCallbacks`
  - keep behavior locked by deterministic tests

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing shared `truffles-api/app/services/llm_quality_contracts.py`
  - existing `repair_booking_scenario_post_coverage_dialogs(...)` extraction seam
  - existing deterministic booking-scenario tests
- **External reuse:**
  - official Python `copy` documentation
- **Why not reinvent the wheel:** the repo already has the shared module and uses `deepcopy`; this block extends that pattern instead of creating a new proof-side abstraction.

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
- Pending-question interrupt/cancel/context progression outputs stay intact for covered cases.

## Scope
- Move pure pending-question contract/helper family into `truffles-api/app/services/llm_quality_contracts.py`.
- Shrink `BookingScenarioPostCoverageRepairCallbacks` so it no longer carries pure helper callbacks.
- Rewire `scripts/booking_dialog_scenarios.py` to import shared helpers.
- Add or update deterministic test coverage.
- Sync canon/session artifacts.

## Out of scope
- runtime semantic cutover
- continuity collapse
- neutral runtime work
- multi-pack acceptance
- frozen router edits
- master/specialist followup detection extraction

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-16-consultant-core-proof-pending-question-contract-helper-slice-a922.md`
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
2. Add shared pending-question contract/helper family to `truffles-api/app/services/llm_quality_contracts.py`.
3. Rewire `scripts/booking_dialog_scenarios.py` to import those helpers and remove local ownership.
4. Shrink the post-coverage repair callback bundle accordingly.
5. Revalidate deterministic booking-scenario tests and required guards.
6. Sync canon/session artifacts.

## DoD
- shared pending-question contract/helper family exists in `truffles-api/app/services/llm_quality_contracts.py`
- `scripts/booking_dialog_scenarios.py` no longer defines the extracted pure helper family
- `BookingScenarioPostCoverageRepairCallbacks` no longer carries callbacks for those pure helpers
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
- shared helper family in `truffles-api/app/services/llm_quality_contracts.py`
- script imports/delegates instead of defining the extracted helper family locally
- shrunken callback bundle in `scripts/booking_dialog_scenarios.py`
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
- **Post-release monitoring window:** next block should either remove the higher-ROI master/specialist followup seam or switch back to richer runtime cutover, not add new proof-only helper ownership

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the pending-question helper extraction actually implemented.

## Rollback
- Revert this TP's shared-helper, script, test, and doc changes only.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No new runtime semantic branches.
- No duplicate ownership of the extracted helper family in both the script and the shared module.

## Risks/Blockers
- helper extraction may accidentally drift nested `expect/meta/meta_any/trace_contains` payloads.
- callback shrinkage may accidentally change post-coverage repair state progression.
- if deterministic sanitize/repair outputs drift, the block is not done.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: master/specialist followup detection and expectation families still remain partially script-owned; runtime semantic ownership, continuity collapse, neutral runtime, and multi-pack acceptance remain open.
- `Why not in this block`: this slice only removes the pure pending-question contract progression family and keeps the block bounded.
- `Risk if deferred`: proof-only script still owns the larger master/specialist followup seam.
- `Linked follow-up Task Package(s)`: `TP-2026-03-16-consultant-core-proof-master-specialist-followup-slice-a922`, `TP-2026-03-16-consultant-core-controller-route-bridge-a922`
- `Expiry/trigger to stop deferral`: before claiming proof path is black-box for booking scenarios or before adding any new master/specialist followup helper in the script.

## Next-block contract (mandatory)
- `Next block objective`: remove the higher-ROI master/specialist followup seam from `scripts/booking_dialog_scenarios.py` if it stays bounded; otherwise return to richer semantic cutover in `reasoning_core`.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: pending-question helper outputs drift; source-of-truth/session metadata not synced; architecture guard fails.
- `Owner role for closure`: `Top Architect`
