# TP-2026-03-15-consultant-core-booking-scenario-expectation-helper-slice-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-BOOKING-SCENARIO-EXPECTATION-HELPER-SLICE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PROOF-HELPER-EXTRACTION-SLICE-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-proof-helper-extraction-slice-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-PROOF-PATH-SCENARIO-REWRITE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Название/цель
Сделать следующий bounded proof-path excision slice без изменения runtime поведения: вынести booking-scenario expectation merge helper family из proof-only `scripts/booking_dialog_scenarios.py` в shared `truffles-api/app/services/llm_quality_contracts.py`, чтобы expectation-merge semantics больше не жили только в proof generator script.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-proof-helper-extraction-slice-a922.md`
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
  - `scripts/booking_dialog_scenarios.py`
  - `truffles-api/app/services/llm_quality_contracts.py`
  - `truffles-api/tests/test_booking_dialog_scenarios_script.py`
  - `truffles-api/tests/test_booking_quality_response_guard.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
- `Baseline commands`:
  - `rg -n "def _merge_expectations|def _default_expect|def _normalize_llm_expect_override|def _sanitize_expect_state_by_tags|def _sanitize_expect_action_by_tags|def _sanitize_expect_override_for_tags|def _apply_pending_question_target_expectations" scripts/booking_dialog_scenarios.py`
  - `rg -n "_merge_expectations =|test_merge_expectations_" truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `FACT findings`:
  - `scripts/booking_dialog_scenarios.py` still owns the booking-scenario expectation merge semantics through `_merge_expectations(...)` plus its normalization/sanitization helper family.
  - `truffles-api/tests/test_booking_dialog_scenarios_script.py` still loads the full proof-only script and binds `_merge_expectations = _module._merge_expectations` for direct expectation-merge tests.
  - this keeps another semantic helper family living only inside a proof generator script instead of a shared non-proof helper module.
- `Detected drift (docs vs code)`: proof/eval should be observer/generator infrastructure, but booking-scenario expectation merge semantics still live only in `scripts/booking_dialog_scenarios.py` and are tested from there directly.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python copy deepcopy documentation`
- **Date/time (local):** `2026-03-15 21:08 Asia/Almaty`
- **Why this query is precise:** this slice extracts nested expectation/trace/meta helpers into a shared module and must preserve detached mutable payloads instead of leaking shared list/dict references between callers.
- **Sources opened (from this query):**
  - `copy — Shallow and deep copy operations` — `https://docs.python.org/3/library/copy.html#copy.deepcopy`
- **Source quality:** official Python documentation.
- **Existing solutions found:** `copy.deepcopy(...)` is the standard-library mechanism for producing detached nested copies of compound objects during helper extraction.
- **Decision:** `reuse + integrate` — reuse `copy.deepcopy(...)` where extracted expectation helpers need safe detached nested structures instead of handwritten alias-prone copies.
- **Rejected options:**
  - leaving the expectation merge helper family inside `scripts/booking_dialog_scenarios.py`
  - broad scenario-generator rewrite in one block
  - touching frozen legacy runtime files
- **Open questions:** none for this bounded slice.

## Root cause (mandatory)
- **Symptom:** booking-scenario expectation merge semantics still live only inside `scripts/booking_dialog_scenarios.py` and direct tests bind `_merge_expectations` from the proof-only script.
- **Minimal reproduction:**
  1. Open `scripts/booking_dialog_scenarios.py`.
  2. Find `_merge_expectations(...)` and its helper family (`_default_expect`, `_normalize_llm_expect_override`, `_sanitize_expect_state_by_tags`, `_sanitize_expect_action_by_tags`, `_sanitize_expect_override_for_tags`, `_apply_pending_question_target_expectations`).
  3. Open `truffles-api/tests/test_booking_dialog_scenarios_script.py` and observe direct `_merge_expectations = _module._merge_expectations` binding from the proof-only script.
- **Evidence to capture:**
  - extracted helper family lives in `truffles-api/app/services/llm_quality_contracts.py`
  - `scripts/booking_dialog_scenarios.py` delegates `_merge_expectations(...)` to the shared helper module
  - direct `_merge_expectations` tests no longer depend on the proof-only script
  - targeted script/runtime/architecture suites stay green
- **Five Whys (or equivalent):**
  1. Why is proof/eval still too authoritative? Because another semantic helper family is still defined only inside a proof generator script.
  2. Why is that wrong? Because proof-only scripts should not remain the only home of reusable semantic contract logic.
  3. Why did it happen? Because scenario expectation shaping grew locally inside the generator script and tests reached for the nearest implementation.
  4. Why is extraction safe? Because expectation merge semantics are pure helper logic and do not require runtime-router edits.
  5. Why does this reduce drift? Because one more semantic helper family stops living only in a proof-only file.
- **Root cause statement:** proof-path authority is still too high because booking-scenario expectation merge semantics and direct tests remain coupled to `scripts/booking_dialog_scenarios.py` instead of a shared helper module.
- **Fix mechanism:**
  - extract the expectation merge helper family into `truffles-api/app/services/llm_quality_contracts.py`
  - delegate `_merge_expectations(...)` from `scripts/booking_dialog_scenarios.py`
  - update direct `_merge_expectations` tests to import the shared helper instead of the proof-only script
  - add a regression check so the direct helper tests do not silently revert to script-only ownership

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/llm_quality_contracts.py`
  - existing `_merge_expectations(...)` helper family in `scripts/booking_dialog_scenarios.py`
  - existing scenario-contract compiler helpers
  - existing proof response guard tests
- **External reuse:**
  - official Python `copy.deepcopy(...)` documentation
- **Why not reinvent the wheel:** the repo already has a shared llm-quality helper module and Python already ships a safe nested-copy primitive; this block should only move the expectation helper family out of the proof-only script.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `16`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** bounded helper extraction with direct regression tests and no runtime-router edits.

## Invariant
- No changes in frozen legacy semantic router files.
- No change to runtime decision semantics.
- No change to generated dialog wording beyond current helper semantics.

## Scope
- Extract booking-scenario expectation merge helper family into `truffles-api/app/services/llm_quality_contracts.py`.
- Rewire `_merge_expectations(...)` in `scripts/booking_dialog_scenarios.py` to delegate to the shared helper module.
- Stop direct `_merge_expectations` tests from depending on the proof-only script.
- Add regression coverage and sync source-of-truth/state/session docs.

## Out of scope
- `_sanitize_llm_turns(...)` decomposition
- `_repair_post_coverage_orphan_pending_question_turns(...)` removal
- frozen runtime file edits
- multi-pack acceptance

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-booking-scenario-expectation-helper-slice-a922.md`
- `scripts/booking_dialog_scenarios.py`
- `truffles-api/app/services/llm_quality_contracts.py`
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
1. Publish this booking-scenario expectation-helper TP with RCA and one web search.
2. Extract the expectation merge helper family into `truffles-api/app/services/llm_quality_contracts.py`.
3. Rewire `scripts/booking_dialog_scenarios.py` to delegate `_merge_expectations(...)` to the shared helper module.
4. Update direct `_merge_expectations` tests to import the shared helper instead of the proof-only script.
5. Run targeted proof/runtime/architecture checks and sync docs.

## DoD
- booking-scenario expectation merge helper family no longer lives only inside `scripts/booking_dialog_scenarios.py`
- direct `_merge_expectations` tests no longer bind that helper from the proof-only script
- `scripts/booking_dialog_scenarios.py` remains behaviorally compatible for the touched helper family
- deterministic proof/runtime/architecture/session checks are green

## Checks
- `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py -k 'merge_expectations'`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- extracted booking-scenario expectation helper family in `truffles-api/app/services/llm_quality_contracts.py`
- updated `scripts/booking_dialog_scenarios.py` delegating `_merge_expectations(...)`
- direct `_merge_expectations` tests without proof-only script ownership
- updated `STATE.md` and session log

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic only
- **Stop condition:** if this block requires `_sanitize_llm_turns(...)` decomposition or scenario-generator rewrite removal, stop and split
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** proof-path helper extraction only
- **Go/no-go signals:** targeted script tests + proof guard + architecture suite + packet + arch guard + session check all green
- **Rollback:** revert this TP's helper extraction/test/doc changes only
- **Post-release monitoring window:** next proof block should either continue extracting a bounded helper family from `scripts/booking_dialog_scenarios.py` or switch back to richer semantic cutover if proof ROI drops

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
- `Drift closeout rule`:
  - active block metadata must match the actual booking-scenario expectation-helper slice being executed.

## Rollback
- Revert this TP's helper extraction, test, and doc changes; keep already-landed governance/runtime/continuity/proof-helper blocks intact.

## No-go
- No edits in `truffles-api/app/routers/webhook/decision.py`.
- No edits in `truffles-api/app/routers/webhook/booking.py`.
- No edits in `truffles-api/app/routers/webhook/pending.py`.
- No changes to runtime policy semantics.

## Risks/Blockers
- extracting too much of `scripts/booking_dialog_scenarios.py` in one slice will turn this into a generic proof-generator refactor.
- direct sanitize/repair tests still need the script module after this slice; only the expectation-helper family should move.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: `_sanitize_llm_turns(...)`, `_repair_post_coverage_orphan_pending_question_turns(...)`, and other scenario rewrite authority still remain in `scripts/booking_dialog_scenarios.py`.
- `Why not in this block`: removing those semantic rewrites would exceed a safe bounded helper extraction slice.
- `Risk if deferred`: the proof generator still owns post-hoc normalization authority beyond the extracted expectation-helper family.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-proof-path-scenario-rewrite-followup-a922`
- `Expiry/trigger to stop deferral`: before accepting any proof-lane claim that depends on scenario post-processing as semantic truth.

## Next-block contract (mandatory)
- `Next block objective`: continue proof-path excision on scenario rewrite helpers in `scripts/booking_dialog_scenarios.py` or switch back to richer semantic cutover if proof ROI drops.
- `First deterministic check command`: `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py -k 'merge_expectations' && python3 scripts/arch_guard.py`
- `Blocked-by conditions`: direct `_merge_expectations` tests still depend on the proof-only script; source-of-truth not synced; shared helper family absent.
- `Owner role for closure`: `Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `yes`
- `Start from`: `docs/_generated/AGENT_PACKET.md`
- `Do not touch`: frozen legacy semantic router files and scenario rewrite logic outside the extracted expectation-helper family
- `Open risks`: widening extraction into `_sanitize_llm_turns(...)` or `_repair_post_coverage_orphan_pending_question_turns(...)` in the same block
- `First command to verify`: `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py -k 'merge_expectations'`
