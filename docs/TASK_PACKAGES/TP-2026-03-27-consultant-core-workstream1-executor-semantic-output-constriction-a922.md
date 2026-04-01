# TP-2026-03-27-consultant-core-workstream1-executor-semantic-output-constriction-a922

## Block identity
- `BLOCK_ID`: `WS1-F3-executor-semantic-output-constriction`
- `PARENT_BLOCK_ID`: `WS1-F2-state-writer-owner-read-cut`
- `DEPENDS_ON`: `TP-2026-03-27-consultant-core-workstream1-state-writer-owner-read-cut-a922.md`
- `UNLOCKS`: `WS1-F4-planner-synthetic-authority-cut`

## Название/цель
Сжать executor output на canaried hot path до operational enrichment only: при наличии `SemanticDecisionV1` executor не должен выпускать еще один semantic carrier (`semantic_contract` / `pending_question_contract`) в `RuntimeExecutionResult.meta`.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`

## FACT pre-check (before implementation)
- `Impacted code/contracts/tests`:
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `Baseline commands`:
  - `rg -n "_attach_semantic_contract_meta|semantic_contract|pending_question_contract" truffles-api/app/core/turn_executor.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/consultant_runtime.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_contract or pending_question_contract"`
- `FACT findings`:
  - `turn_executor.py` still attaches full `semantic_contract` and `pending_question_contract` into `RuntimeExecutionResult.meta` through `_attach_semantic_contract_meta(...)`, so executor continues to publish a post-owner semantic artifact even after state-writer authority was reduced.
  - `consultant_runtime.py` and `dialog_state_service.py` still accept execution semantic carriers as possible downstream inputs, even though the canaried path now has canonical owner/state projections available.
  - Tests still prove the legacy/synthetic path needs compatibility semantic meta, so the cut must be gated to `semantic_decision`-backed decisions only.
- `Detected drift (docs vs code)`: `present`
  - Workstream 1 says planner/executor/state layers stop re-authoring meaning, but executor output still looks like a second semantic owner artifact on the canaried path.

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python copy deepcopy docs`
- **Date/time (local):** `2026-03-27 11:17 +05`
- **Why this query is precise:** This block needs to emit bounded executor enrichment without leaking shared nested semantic payloads into downstream mutation paths. The official Python copy semantics are the exact reuse candidate for snapshotting that enrichment safely.
- **Sources opened (from this query):**
  - `Python standard library / copy`: `https://docs.python.org/3/library/copy.html`
- **Source quality:** Python standard library docs (primary source).
- **Existing solutions found:** `copy.deepcopy(...)` is the standard way to snapshot nested mappings/lists before passing them downstream without shared-reference mutation.
- **Decision:** `integrate` — emit a deep-copied bounded `semantic_enrichment` payload on the canaried path instead of reusing the full execution semantic contract dict.
- **Rejected options:**
  - Keep forwarding full `semantic_contract` and rely only on downstream ignore rules: rejected because the extra semantic carrier remains live and authoritative-looking.
  - Introduce a new serializer layer/package: rejected because the block only needs a bounded payload cut, not a new framework.

## Root cause (mandatory)
- **Symptom:** After planner and state-writer cuts, executor still emits `semantic_contract` / `pending_question_contract` in `RuntimeExecutionResult.meta`, so the hot path still has a post-owner semantic carrier.
- **Minimal reproduction:**
  - `rg -n "payload\[\"semantic_contract\"\]|payload\[\"pending_question_contract\"\]|_attach_semantic_contract_meta" truffles-api/app/core/turn_executor.py`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_contract or pending_question_contract"`
- **Evidence to capture:**
  - exact executor helper that publishes semantic carriers into runtime meta
  - focused deterministic tests proving canaried executor output now emits enrichment-only payloads while legacy/synthetic compatibility remains intact
- **Five Whys (or equivalent):**
  1. Why does executor still look like a semantic owner? Because it publishes full semantic contract and pending-question contract payloads after execution begins.
  2. Why are those payloads problematic? Because they look authoritative and can be consumed downstream as peer meaning carriers.
  3. Why does that remain after Family 2? Because state-writer authority was reduced, but executor output shape was not yet narrowed.
  4. Why is narrowing needed now? Because Workstream 1 is about deleting semantic authority, not only teaching downstream to ignore it.
  5. Why can’t this wait until binding/state unification? Because leaving a second semantic-looking artifact on the hot path keeps executor in the semantic owner set.
- **Root cause statement:** Executor output still publishes full post-owner semantic carriers, so even with canonical owner/state projections in place the runtime plane continues to transport another artifact that can be mistaken for semantic authority.
- **Fix mechanism:** On `semantic_decision`-backed decisions, emit only bounded `semantic_enrichment` from executor meta, stop emitting execution `pending_question_contract`, and update downstream readers to merge enrichment into canonical owner/state projections instead of reading another semantic carrier.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - Reuse canonical owner/state projections already added in `TurnPlanner`, `DialogStateService`, and `ConsultantRuntime`.
  - Reuse existing trace/meta projection logic in `consultant_runtime.py` so final runtime evidence still reads from canonical state.
- **External reuse:**
  - Python stdlib `copy.deepcopy(...)` for bounded enrichment snapshots.
- **Why not reinvent the wheel:** The executor already computes the enrichment ingredients; this block only narrows what it exports.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `4`
- **Code dominance:** `required`
- **Override token:** `none`
- **Why this profile fits:** This is a narrow runtime-authority cut across executor/state/runtime readers, not a larger architecture rewrite.

## Invariant
- When `semantic_decision` exists, executor may emit operational enrichment only, not a second semantic owner artifact.
- Legacy/synthetic non-canaried paths may keep compatibility payloads until explicitly strangled.
- Runtime trace/meta must still expose canonical semantic state and pending-question state after the cut.
- No hidden semantic rewrite may move into another helper or dict key.

## Scope
- Narrow executor meta output on the canaried path from full semantic carriers to bounded enrichment.
- Update state/runtime readers to consume bounded enrichment on that path.
- Add focused deterministic regressions for executor output shape and downstream runtime trace/meta.
- Update repo truth/docs for the removed executor authority.

## Out of scope
- `BindingPlanV1` extraction.
- Full legacy compatibility strangler.
- Planner synthetic compatibility cleanup outside canaried runtime.
- `TurnJournalV1` / `ConversationProjectionV1` cutover.

## Touch-list
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-executor-semantic-output-constriction-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan (1..N)
1. Add a bounded executor enrichment payload for `semantic_decision`-backed decisions and stop attaching execution `pending_question_contract` there.
2. Update state/runtime readers to merge `semantic_enrichment` into canonical owner/state projections.
3. Keep legacy/synthetic paths on the old compatibility payload shape for now.
4. Add focused deterministic tests for canaried executor output and downstream runtime trace/meta behavior.
5. Run bounded checks, then update `STATE.md` / `STRUCTURE.md` truthfully.

## DoD
- Canaried executor output no longer includes full `semantic_contract` or execution `pending_question_contract` in `RuntimeExecutionResult.meta`.
- Downstream runtime/state still preserves bounded enrichment and canonical semantic state for traces/meta.
- Legacy/synthetic paths keep compatibility behavior unless explicitly excluded by this block.
- Focused deterministic tests prove the authority cut.

## Checks
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_decision or semantic_contract or pending_question_contract"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "semantic_decision or semantic_contract or pending_question_contract"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture`
- `git diff --check`

## Evidence
- Code diff showing executor canaried output switched from full semantic carrier to bounded enrichment.
- Focused deterministic tests proving downstream runtime/state still reads canonical owner/state semantics.
- Truthful `STATE.md` entry naming exactly which executor authority was removed and what remains.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Fail-fast / scenario lock:** deterministic-only in this family; no open-ended quality replay loop.
- **Stop condition:** if two code/test iterations fail without new authority-reduction evidence, stop and reopen RCA.
- **Escalation path:** `Brain / Top Architect` for any extra long realism or acceptance runs.

## Release safety (mandatory for non-doc changes)
- **Strategy:** local canary only in this worktree; no production rollout in this block.
- **Go/no-go signals:** canaried executor meta no longer publishes full semantic carriers; downstream traces/meta still show canonical semantic state; focused tests pass.
- **Rollback:** revert executor output narrowing and the associated reader/test changes together.
- **Post-release monitoring window:** local deterministic regression pass for this block only.

## Doc sync plan (after implementation)
- `Docs/specs to update in same block`:
  - `STATE.md`
  - `STRUCTURE.md`
  - this TP with implementation evidence
- `Drift closeout rule`:
  - if any downstream code still reads `execution.meta["semantic_contract"]` on the canaried path after this block, record it explicitly as residual debt.

## Rollback
- Revert executor meta narrowing and related reader/test updates together.

## No-go
- No new semantic fields hidden inside `semantic_enrichment`.
- No removal of compatibility payloads from legacy/synthetic paths in this block.
- No claim that executor is fully demoted beyond the canaried path.
- No binding extraction work in this block.

## Risks/Blockers
- Some tests pin executor meta shape through synthetic planner paths; the cut must stay gated to `semantic_decision` decisions.
- Runtime trace/meta must still preserve enrichment-driven referents/grounding after the executor output shape changes.
- Mis-scoping the enrichment subset could accidentally drop operational data needed for booking/info follow-up continuity.

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: planner synthetic compatibility builders remain; legacy context/session-memory compatibility mesh remains; full canonical state substrate is still not cut over.
- `Why not in this block`: this family is limited to removing executor semantic-looking output on the canaried path.
- `Risk if deferred`: executor would remain a semantic-looking peer truth carrier even after planner/state cuts.
- `Linked follow-up Task Package(s)`: `WS1-F4-planner-synthetic-authority-cut` (to be authored after this block lands).
- `Expiry/trigger to stop deferral`: if a canaried runtime trace still depends on `execution.meta["semantic_contract"]` after this block, the next block must target that exact reader before broader workstreams resume.

## Next-block contract (mandatory)
- `Next block objective`: remove remaining planner-side synthetic compatibility authority that can mint semantic-looking decisions without canonical owner output.
- `First deterministic check command`: `rg -n "build_from_policy_override|synthetic_policy_decision|semantic_decision" truffles-api/app/core/turn_planner.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `Blocked-by conditions`: canaried executor output still emits full `semantic_contract` / `pending_question_contract`, or downstream runtime trace/meta loses bounded enrichment after the cut.
- `Owner role for closure`: `Brain / Top Architect`

## Handoff (for zero-context next agent)
- `Ready for next agent`: `no`
- `Start from`: `truffles-api/app/core/turn_executor.py`
- `Do not touch`: `legacy webhook compatibility surfaces outside the canaried executor/state/runtime path`
- `Open risks`: `legacy tests pinned to compatibility meta`, `runtime trace/meta enrichment preservation`, `planner synthetic carriers still present`
- `First command to verify`: `rg -n "_attach_semantic_contract_meta|semantic_contract|pending_question_contract" truffles-api/app/core/turn_executor.py`


## Implementation result
- `Status`: `done`
- `Changed authority map`:
  - `turn_executor.py` no longer emits execution `semantic_contract` or `pending_question_contract` on `semantic_decision`-backed turns; it now publishes bounded `semantic_enrichment` only.
  - `dialog_state_service.py` and `consultant_runtime.py` now read execution enrichment as operational data merged into canonical owner/state projections instead of treating execution semantic meta as a peer meaning carrier.
  - legacy/synthetic non-canaried paths still keep compatibility semantic meta for now.
- `Files touched`:
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_dialog_state_service.py`
- `Deterministic checks`:
  - `python3 -m py_compile truffles-api/app/core/turn_executor.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/consultant_runtime.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_dialog_state_service.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_decision or semantic_contract or pending_question_contract or semantic_enrichment"` -> `5 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py -k "semantic_decision or semantic_contract or pending_question_contract or semantic_enrichment"` -> `7 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `64 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_dialog_state_service.py` -> `80 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture` -> `23 passed`
  - `git diff --check` -> `pass`
- `Contract checks`:
  - added executor regression proving `semantic_decision` turns emit `semantic_enrichment` only and omit execution `semantic_contract` / `pending_question_contract`.
  - added state/runtime regressions proving canonical semantic contract and pending-question views still survive state write, runtime memory-profile, and runtime trace/meta projection when execution provides enrichment-only payloads.
- `Realistic/local behavior checks`:
  - not run in this bounded family; no `llm-quality` acceptance run was part of this block.
- `Authority removed`:
  - executor is no longer a hot-path semantic co-owner on the canaried path because it no longer publishes a second full semantic carrier after owner issuance.
- `Residual debt left for next block`:
  - planner synthetic compatibility builders can still mint `PolicyDecision` artifacts without canonical `semantic_decision`.
  - runtime/state still retain legacy fallback readers for non-canaried compatibility paths until those authorities are strangled in later Workstream 1 blocks.
