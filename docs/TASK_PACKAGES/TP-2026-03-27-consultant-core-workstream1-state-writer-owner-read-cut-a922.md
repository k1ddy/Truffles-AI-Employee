# TP-2026-03-27-consultant-core-workstream1-state-writer-owner-read-cut-a922

## Block identity
- `BLOCK_ID`: `WS1-F2-state-writer-owner-read-cut`
- `PARENT_BLOCK_ID`: `WS1-F1-semantic-decision-hot-path`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-semantic-decision-hot-path-a922.md`
- `UNLOCKS`: `WS1-F3-executor-semantic-output-constriction`

## Название/цель
Сделать state-writer на canaried hot path read-only по owner meaning: при наличии `SemanticDecisionV1` `dialog_state_service` должен материализовать состояние из канонического owner output, а не домешивать смысл из existing state / execution semantic carriers.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/TURN_JOURNAL_V1.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `Baseline commands`:
  - `rg -n "_merge_semantic_frame|_build_runtime_semantic_contract|_build_runtime_grounded_referents|project_state_compatibility_fields" truffles-api/app/core/dialog_state_service.py`
  - `rg -n "semantic_contract|pending_question_contract|semantic_decision" truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `FACT findings`:
  - `dialog_state_service.py:_merge_semantic_frame(...)` still starts from existing semantic frame and merges decision/execution carriers into it, so owner meaning can be backfilled from old state or execution-side semantic payloads even after `SemanticDecisionV1` exists.
  - `dialog_state_service.py:_build_runtime_semantic_contract(...)` still composes semantic contract fields from `existing_contract`, `decision_contract`, and `execution_contract`, which leaves state-writer semantic authority alive on the canaried path.
  - `project_state_compatibility_fields(...)` then republishes pending-question and semantic-contract compatibility carriers from the materialized frame, so any state-writer drift becomes the live read model.
- `Detected drift (docs vs code)`: `present`
  - `docs/system_forensics/final/SEMANTIC_DECISION_V1.md` forbids downstream mutation of `requested_outcome`, `capability_id`, `semantic_slots`, `missing_information`, and grounding semantics, but the state writer still has code paths that can reconstruct those fields from non-owner carriers.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.pydantic.dev pydantic model_copy deep official docs`
- **Date/time (local):** `2026-03-27 23:46, Asia/Almaty`
- **Why this query is precise:** This block needs to start state materialization from canonical owner projections without mutating the original nested Pydantic payloads. The query targets the official copy semantics for the repo’s contract system.
- **Sources opened (from this query):**
  - `Pydantic models / model_copy`: `https://docs.pydantic.dev/latest/concepts/models/`
- **Source quality:** official Pydantic documentation (primary source).
- **Existing solutions found:** `model_copy(deep=True)` gives a deep copy of nested model state, while default `model_copy()` is shallow; that fits a read-only owner projection with local runtime enrichment.
- **Decision:** `integrate` — use canonical planner projections plus deep copies when local runtime enrichment is still needed, instead of mutating nested owner-derived models in place.
- **Rejected options:**
  - Reconstruct fresh dicts from mixed existing/execution carriers: rejected because it preserves the current split-authority problem.
  - New immutable wrapper layer: rejected because the repo already standardizes on Pydantic contracts and this block is about removing authority, not adding a parallel contract system.

## Root cause (mandatory)
- **Symptom:** After Workstream 1 / Family 1, the planner hot path writes one canonical `SemanticDecisionV1`, but the state writer can still materialize semantic state by mixing prior state and execution semantic carriers.
- **Minimal reproduction:**
  - `rg -n "existing_contract, decision_contract, execution_contract|materialized = deepcopy\(existing_payload\)|pending_question_contract = self.project_pending_question_contract" truffles-api/app/core/dialog_state_service.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "semantic_contract or pending_question_contract"`
- **Evidence to capture:**
  - exact dialog-state write helpers that merge owner/existing/execution semantic carriers
  - focused deterministic tests showing owner fields survive conflicting execution/state payloads on the canaried path
- **Five Whys (or equivalent):**
  1. Why can semantic drift still happen after the owner call? Because the state writer still builds materialized semantic state by merging non-owner carriers.
  2. Why does it merge them? Because canonical state is still implemented as a compatibility merge layer instead of an owner-read-only projection.
  3. Why is that dangerous? Because old state and execution payloads can silently preserve or override meaning after owner issuance.
  4. Why is that still active on the canaried path? Because Workstream 1 Family 1 stopped planner/runtime re-authoring first, but did not yet constrain the state writer.
  5. Why does the architecture remain open? Because `planner/executor/state layers stop re-authoring meaning` is an explicit Workstream 1 completion criterion.
- **Root cause statement:** `dialog_state_service` still treats existing state and execution semantic payloads as semantic inputs on the canaried path, so state materialization remains a downstream meaning owner instead of a read-only consumer of `SemanticDecisionV1`.
- **Fix mechanism:** On the canaried path, materialize semantic state from canonical planner projections derived from `SemanticDecisionV1`, allow only bounded runtime enrichment (`referents`, `entity_refs`, grounding provenance, slot-value shadowing), and block existing/execution carriers from rewriting owner semantic fields.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Reuse `TurnPlanner().canonical_semantic_frame(...)`, `canonical_semantic_contract(...)`, and `canonical_pending_question_contract(...)` as the single state-writer input.
  - Reuse `project_state_compatibility_fields(...)` as the compatibility projection surface after the canonical frame is materialized.
- **External reuse:**
  - Official Pydantic `model_copy(deep=True)` semantics for safe deep copies of owner-derived models during bounded enrichment.
- **Why not reinvent the wheel:** The planner already exposes canonical owner projections; this block should consume them instead of introducing another semantic builder.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `4`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** This is a bounded authority cut inside the active runtime/state path, not a broader state-unification rewrite.

## Invariant
- When `PolicyDecision.semantic_decision` exists, state writer must not derive semantic owner fields from existing state or execution semantic carriers.
- Runtime may still record operational enrichment, but may not rewrite owner capability, outcome-adjacent meaning, missing-information semantics, or grounding intent.
- Compatibility views remain derived-only.
- Explicit degrade/handoff behavior remains unchanged.

## Scope
- Constrain `dialog_state_service` canaried state materialization to canonical owner projections.
- Limit execution/state semantic enrichment to bounded non-owner fields.
- Add focused deterministic tests that prove conflicting execution/state payloads cannot rewrite owner semantic fields.
- Update repo truth/docs for the reduced state-writer authority.

## Out of scope
- Full `TurnJournalV1` / `ConversationProjectionV1` rollout.
- `BindingPlanV1` extraction.
- Legacy context-manager strangler work.
- Removal of synthetic compatibility builders used only in tests.

## Touch-list
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-state-writer-owner-read-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Add canonical-owner helpers inside `dialog_state_service` for semantic frame/contract/pending-question reads on the canaried path.
2. Change state materialization so owner semantic fields come from `SemanticDecisionV1`-derived projections, not existing/execution semantic carriers.
3. Keep only bounded runtime enrichment (`referents`, `entity_refs`, `grounding_provenance`, slot-value shadowing) and prevent rewrite of owner fields.
4. Add/update focused deterministic tests for conflicting execution/state semantic payloads.
5. Run bounded checks, then update `STATE.md` and `STRUCTURE.md` truthfully.

## DoD
- On the canaried path, `dialog_state_service` uses canonical planner projections for semantic frame / semantic contract / pending-question semantics.
- Existing state and execution semantic carriers cannot rewrite owner capability, pending-question semantics, or canonical semantic frame fields.
- Focused deterministic tests prove the state writer remains read-only for owner meaning while still preserving allowed runtime enrichment.

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "semantic_decision or semantic_contract or pending_question_contract"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_decision or canonical_pending_question_contract or semantic_contract"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture`
- `git diff --check`

## Evidence
- Code diff showing state-writer reads from canonical owner projections.
- Focused deterministic tests proving conflicting execution/state payloads do not rewrite owner fields.
- Truthful `STATE.md` entry naming exactly which state-writer authority was removed and what remains.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** deterministic-only in this family; no open-ended quality replay loop.
- **Stop condition:** if two code/test iterations fail without new authority-reduction evidence, stop and reopen RCA.
- **Escalation path:** `Brain / Top Architect` for any extra long realism or acceptance runs.

## Release safety (mandatory for non-doc changes)
- **Strategy:** local canary only in this worktree; no production rollout in this block.
- **Go/no-go signals:** canonical state write uses owner projections; conflicting execution semantic payload no longer rewrites owner fields; focused tests pass.
- **Rollback:** revert the state-writer canonical-read cut and related tests together.
- **Post-release monitoring window:** local deterministic regression pass for this block only.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `STATE.md`
  - `STRUCTURE.md`
  - this TP with implementation evidence
- `Drift closeout rule`:
  - update docs in this block; if executor still emits semantic-side carriers that the state writer merely ignores, record that residual explicitly for the next block.

## Rollback
- Revert the state-writer canonical-read changes and the focused regression tests together.

## No-go
- No new regex/phrase hardcoding in core.
- No execution-side semantic rewriting disguised as state enrichment.
- No claim that canonical state unification is complete in this block.
- No binding extraction work in this block.

## Risks/Blockers
- Some continuity behavior may have been relying on state-writer backfill from stale carriers; tests must distinguish allowed runtime enrichment from semantic rewrite.
- Execution/meta consumers still expect compatibility carriers, so the block must keep derived compatibility projections alive.
- `build_from_policy_override(...)` remains a test-only synthetic path and must not be mislabeled as hot-path closure.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: executor still emits semantic-side meta carriers; context-manager/session-memory/current-goal compatibility mesh still exists; full canonical state substrate is not cut over.
- `Why not in this block`: this family is limited to removing state-writer semantic authority on the canaried path, not to Workstreams 2-5.
- `Risk if deferred`: execution/state compatibility carriers could continue to look canonical unless the next block removes or narrows them.
- `Linked follow-up Task Package(s)`: `WS1-F3-executor-semantic-output-constriction` (to be authored after this block lands).
- `Expiry/trigger to stop deferral`: if state writer still depends on execution semantic payloads for owner fields after this block, the next block must target executor output before any broader workstream starts.

## Next-block contract (mandatory)
- `Next block objective`: constrain executor semantic outputs to operational enrichment only, so state write no longer receives post-owner semantic carriers that look authoritative.
- `First deterministic check command`: `rg -n "semantic_contract|pending_question_contract" truffles-api/app/core/turn_executor.py truffles-api/app/core/dialog_state_service.py`
- `Blocked-by conditions`: this block fails to make state materialization read canonical owner projections first, or focused tests still prove owner-field rewrite from execution/existing semantic carriers.
- `Owner role for closure`: `Brain / Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `no`
- `Start from`: `truffles-api/app/core/dialog_state_service.py`
- `Do not touch`: `legacy context-manager strangler surfaces outside the active runtime write path`
- `Open risks`: `continuity behaviors relying on stale backfill`, `executor semantic meta still live`, `compatibility projections still numerous`
- `First command to verify`: `rg -n "_merge_semantic_frame|_build_runtime_semantic_contract|semantic_decision" truffles-api/app/core/dialog_state_service.py`


## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - `dialog_state_service.py` now treats canonical planner projections derived from `SemanticDecisionV1` as the semantic source on the canaried state-write path.
  - existing state and execution semantic carriers are no longer allowed to rewrite owner `subject_kind`, `capability`, `temporal_scope`, `resolution_mode`, or pending-question semantics when `semantic_decision` exists.
  - execution-side enrichment is limited to `referents`, `entity_refs`, `grounding_provenance`, and `slot_values` shadow data on that path.
- `Files touched`:
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/tests/test_dialog_state_service.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `Deterministic checks`:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "semantic_decision_state_write_ignores_conflicting_execution_semantics"` -> `1 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "state_written_semantic_decision_contract"` -> `1 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "semantic_decision or semantic_contract or pending_question_contract"` -> `6 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_decision or canonical_pending_question_contract or semantic_contract"` -> `3 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py` -> `79 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `63 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture` -> `23 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_turn_planner_expected_reply_validation.py truffles-api/tests/test_intent.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_llm_policy_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_dialog_state_service.py` -> `268 passed`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - added state-writer regression proving conflicting execution semantics cannot rewrite owner semantic fields when `semantic_decision` exists.
  - added runtime memory-profile regression proving downstream reads continue to see owner semantic contract/pending-question semantics after the state write.
- `Realistic/local behavior checks`:
  - not run in this bounded family; no `llm-quality` acceptance run was part of this block.
- `Authority removed`:
  - state writer no longer has live semantic authority to rewrite owner capability and pending-question semantics from existing/execution semantic carriers on the canaried path.
- `Residual debt left for next block`:
  - executor still emits post-owner semantic meta carriers that look authoritative even though the state writer now narrows their effect.
  - planner synthetic compatibility builders remain in test/support surfaces and should not be mistaken for hot-path closure.
