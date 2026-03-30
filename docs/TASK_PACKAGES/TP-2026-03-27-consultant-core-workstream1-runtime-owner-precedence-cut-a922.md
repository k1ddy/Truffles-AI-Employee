# TP-2026-03-27-consultant-core-workstream1-runtime-owner-precedence-cut-a922

Название/цель:
- Следующий крупный bounded cut внутри Workstream 1: убрать runtime state-first semantic precedence на owner-backed path.
- Сделать так, чтобы при наличии `SemanticDecisionV1` runtime trace/meta/contract action читали owner semantics как primary source, а state/execution использовались только как allowed enrichment, а не как semantic override.

Canon refs:
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/TURN_JOURNAL_V1.md`
- `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
- `docs/system_forensics/ledgers/CONTROL_PATHS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `STATE.md` NOW: `workstream1_owner_output_singularity_cut`

Invariant:
- `SemanticDecisionV1` stays the only semantic owner on canaried turns.
- Runtime may enrich owner output with grounding/referent execution facts, but may not reinterpret owner intent/capability/pending-question meaning.
- Explicit boundary/degrade/preflight paths remain typed and allowed.

Scope:
- `truffles-api/app/core/consultant_runtime.py`
- targeted regressions in `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `STATE.md`
- `STRUCTURE.md`

Out of scope:
- canonical state model redesign
- pre-owner memory-profile redesign
- legacy webhook mesh strangler
- TurnJournal / ConversationProjection implementation

Touch-list:
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-runtime-owner-precedence-cut-a922.md`
- `STATE.md`
- `STRUCTURE.md`

Work mode:
- implementation

One web search (mandatory before implementation):
- Query: `site:docs.python.org ChainMap documentation`
- Date/time: `2026-03-27 Asia/Almaty`
- Opened sources:
  - `https://docs.python.org/3/library/collections.html`
- Source quality:
  - high-signal official Python documentation
- Found reusable solution:
  - `ChainMap` gives precedence-ordered lookups across mappings without mutating later maps.
- Decision:
  - `build`
  - reuse the precedence idea only; do not use `ChainMap` directly because runtime semantic merging here is nested and field-whitelisted, not shallow key lookup.
- Rejected options:
  - direct `ChainMap` usage — rejected because nested referents/entity refs/grounding need explicit merge rules and conflict handling.

Root cause (mandatory):
- Symptom:
  - even after owner extraction and shadow-carrier demotion, runtime trace/meta still reads stale dialog state first and only backfills missing fields from owner semantics.
- Minimal reproduction:
  - on an owner-backed decision, populate `dialog_state.meta.semantic_contract` or `dialog_state.pending_question_contract` with stale conflicting values and call runtime semantic projection.
  - current runtime keeps stale `capability` / `next_question` if those keys are already present, even though canonical owner semantics disagree.
- Evidence:
  - `truffles-api/app/core/consultant_runtime.py:741-818`
  - `truffles-api/app/core/consultant_runtime.py:821-855`
  - existing regression area in `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- Five Whys:
  1. Why can stale state still win? Because runtime projection starts from `dialog_state.project_runtime_*` and only fills missing keys from owner.
  2. Why is that wrong? Because on owner-backed turns, state is downstream persistence/read-model, not the semantic authority for the current turn.
  3. Why does execution still matter? Because execution may contribute grounding/referent enrichment, but not semantic reinterpretation.
  4. Why is current behavior dangerous? Because old dialog state or execution meta can silently override owner meaning in trace/meta and contract derivation.
  5. Why does this block Workstream 1? Because planner/executor/state are still semantic co-owners if runtime consumes them as primary meaning after owner issuance.
- Root cause statement:
  - runtime read paths still implement state-first merge semantics on owner-backed turns, so canonical owner semantics are not yet the primary read source at the runtime boundary.
- Fix mechanism:
  - for owner-backed turns, make runtime semantic projections owner-first; allow state/execution only as whitelisted enrichment (`referents`, `entity_refs`, `grounding_provenance`) and drop full execution semantic fallback plus stale pending-question carryover.

Plan:
1. Add bounded runtime helpers for owner-first semantic enrichment merge.
2. Switch `_project_runtime_semantic_contract(...)` to owner-first behavior when `semantic_decision` is present.
3. Switch `_project_runtime_pending_question_contract(...)` to owner-only behavior on owner-backed turns.
4. Make `_derive_contract_action(...)` prefer owner goal on owner-backed turns.
5. Add deterministic regressions for stale state/execution override attempts on owner-backed turns.
6. Update `STATE.md` and `STRUCTURE.md` truthfully.

DoD:
- On owner-backed turns, stale `dialog_state.meta.semantic_contract` cannot override owner semantic fields in runtime trace/meta.
- On owner-backed turns, stale `dialog_state.pending_question_contract` cannot override or resurrect pending-question semantics.
- Execution `semantic_contract` may enrich referents/grounding only; it may not override owner semantic fields.
- Deterministic regressions pass.

Checks:
- `python3 -m py_compile truffles-api/app/core/consultant_runtime.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "owner_backed or stale_legacy_carriers or canonical_semantic_state or semantic_decision"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture`
- `git diff --check`

Evidence:
- changed authority map in code
- deterministic test output
- updated `STATE.md`
- updated `STRUCTURE.md`

Rollback:
- Revert only the touched runtime/test/doc files from this TP.
- If owner-first merge breaks current deterministic runtime contract behavior outside this family, stop and narrow the field whitelist rather than restoring state-first semantics.

No-go:
- no new semantic hardcode in runtime core
- no new peer semantic carrier
- no expansion of executor/state semantic write authority
- no drift into Workstream 2/3 redesign

Risks/blockers:
- Some current tests rely on state-written enrichment from executor and must continue to pass.
- Over-tightening merge rules could accidentally drop allowed enrichment if not field-whitelisted correctly.

Residual architecture debt (mandatory):
- Current residuals accepted in this block:
  - pre-owner memory profile still depends on projected runtime state from previous turns
  - legacy webhook mesh still has compatibility readers
  - semantic frame observability still uses runtime materialized state surfaces
- Why not in this block:
  - this block is limited to owner-backed runtime precedence, not pre-owner memory redesign or full legacy strangler.
- Risk if deferred:
  - stale runtime semantic views could still leak through other compatibility readers even after runtime trace/meta become owner-first.
- Linked follow-up Task Package(s):
  - `TP-2026-03-27-consultant-core-workstream1-owner-output-singularity-cut-a922.md`
  - next TP TBD for memory-profile / legacy reader closeout
- Expiry/trigger to stop deferral:
  - if a canaried owner-backed turn still shows stale state as primary meaning after this block, deferral expires immediately.

Next-block contract (mandatory):
- Next block objective:
  - close remaining owner-adjacent legacy readers outside runtime core, starting with pre-owner memory profile and legacy webhook compatibility reads.
- First deterministic check command:
  - `rg -n "project_runtime_semantic_contract|project_runtime_pending_question_contract|memory_profile|pending_question_contract|semantic_contract" truffles-api/app/core/consultant_runtime.py truffles-api/app/core/booking_prompt_owner.py truffles-api/app/routers/webhook`
- Blocked-by conditions:
  - runtime still lets stale dialog state override owner-backed semantics
  - execution semantic fallback still overrides owner semantic fields
- Owner role for closure:
  - Brain / Top Architect

## Implementation result
- Status: completed for this bounded family.
- Authority removed:
  - owner-backed runtime semantic reads no longer start from stale dialog state; `SemanticDecisionV1` now provides the primary runtime semantic contract on that path.
  - owner-backed runtime pending-question reads no longer resurrect stale pending contracts from dialog state.
  - owner-backed runtime execution fallback no longer allows full `execution.meta.semantic_contract` to override owner semantic fields; execution contributes enrichment only.
  - contract-action derivation now prefers owner goal on owner-backed turns instead of stale runtime current-goal.
- Files touched:
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-runtime-owner-precedence-cut-a922.md`
  - `STATE.md`
  - `STRUCTURE.md`
- Deterministic checks:
  - `python3 -m py_compile truffles-api/app/core/consultant_runtime.py truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `pass`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "owner_backed or stale_legacy_carriers or canonical_semantic_state or semantic_decision"` -> `11 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `72 passed`
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture` -> `24 passed`
  - `git diff --check` -> `pass`
- Residual debt left for next block:
  - pre-owner memory profile still projects previous-turn semantic state from runtime storage
  - semantic-frame observability still depends on runtime materialized state surfaces
  - legacy webhook compatibility readers remain outside runtime core
