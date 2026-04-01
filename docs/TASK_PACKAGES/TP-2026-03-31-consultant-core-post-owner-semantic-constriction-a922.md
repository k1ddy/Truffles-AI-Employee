# TP-2026-03-31-consultant-core-post-owner-semantic-constriction-a922

## Название / цель
Сузить post-owner semantic seam на whole-system hot path так, чтобы planner/executor/runtime shell перестали переписывать смысл после owner decision. На owner-backed turn canonical semantic contract и pending-question contract должны идти downstream как owner-authored artifacts; downstream layers могут только исполнять план, прикладывать bounded grounding enrichment и деградировать typed reason-code, но не собирать новый semantic contract из booking state, runtime state или legacy compatibility carriers.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/DECISIONS/DEC-2026-03-31-consultant-core-whole-system-architecture-closure-governing-decision.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-architecture-closure-master-program-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-continuity-state-normalization-a922.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/SEMANTIC_BRIDGE_GUARD.yaml`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com anti corruption layer downstream translation model ownership`
- Date/time (local): `2026-03-31 18:36 +0500`
- Sources opened:
  - `https://martinfowler.com/articles/patterns-legacy-displacement/legacy-mimic.html`
- Source quality:
  - Martin Fowler architecture primary source / high-signal reference
- Ready solutions found:
  - downstream compatibility layers may translate or mimic legacy surfaces, but they must not become the new domain owner;
  - contract-preserving displacement works when downstream translation remains bounded and does not invent upstream business meaning;
  - the correct move is to keep owner-authored meaning intact and confine downstream layers to adaptation, transport, and bounded enrichment.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the existing owner-backed `SemanticDecisionV1`, `BindingPlanV1`, `TurnPlanner` canonical projections, and runtime mutation guard;
  - integrate stricter owner-precedence into executor/runtime projection seams;
  - build deterministic block proof and guard updates for the reduced hotspot set.
- Rejected options:
  - broad rewrite before constricting the live hot path;
  - leaving booking/runtime state as a second semantic reconstruction source;
  - fixing only one scenario family while keeping downstream semantic rebuilding in place.

## Invariant
- Do not reopen fact-family cutover or continuity normalization.
- Do not let executor or runtime state merge override owner-authored `intent`, `goal`, `requested fact scope`, `pending-question meaning`, or `semantic referent contract` on owner-backed turns.
- Do not move new semantic logic into frozen legacy webhook files.
- Do not sync active canon/state/packet until the full post-owner block is green.

## Scope
- owner-backed semantic contract and pending-question contract remain canonical downstream artifacts
- executor stops rebuilding meaning-bearing contracts from booking state / service query / runtime projection on owner-backed turns
- runtime trace/meta stops merging owner-backed semantic contract with stale state semantic projections
- hotspot freeze and deterministic proof for the post-owner seam set

## Out of scope
- boundary constriction
- broad pack/runtime separation completion
- broader fact-family migration
- broad legacy mesh drain or deletions
- replay or human semantic audit

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-post-owner-semantic-constriction-a922.md`
- `docs/REPORTS/2026-03-31-consultant-core-post-owner-semantic-constriction-a922.md`
- `docs/SEMANTIC_BRIDGE_GUARD.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/legacy_caller_surface.json`
- `docs/system_forensics/governance_delta.json`
- `STATE.md`
- `STRUCTURE.md`
- `scripts/recovery_execution_guard.py`
- `scripts/semantic_bridge_growth_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_semantic_bridge_growth_guard.py`
- `git diff --check`

## Root cause (mandatory)
### Symptom
The first fact family and continuity slice now run through the governed hot path, but downstream executor/runtime layers still rebuild meaning-bearing artifacts after the owner speaks. Owner-authored `semantic_contract` and `pending_question_contract` can still be reassembled from booking state, runtime state, or compatibility projections, so planner ownership is narrowed at the top and then re-expanded downstream.

### Minimal reproduction
1. Create an owner-backed `PolicyDecision` with canonical semantic contract and pending-question contract.
2. Add stale or conflicting `dialog_state.meta.semantic_contract`, `dialog_state.pending_question_contract`, `booking_state`, or execution-side semantic payload.
3. Run executor/runtime projection helpers.
4. Observe that downstream helpers can still merge booking/runtime state back into the effective semantic contract or pending-question contract.

### Evidence
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/dialog_state_service.py`

### Five Whys
1. Why is semantic ownership still open after the continuity block? Because downstream execution/runtime layers still reconstruct semantic artifacts after the owner has already emitted them.
2. Why is that a blocker? Because the system still has a practical second semantic lane: owner meaning can be narrowed upstream and then widened or reshaped downstream.
3. Why is executor a hotspot? Because it still builds execution semantic/pending contracts and mixes booking/service state into them.
4. Why is runtime a hotspot? Because it still merges owner-backed trace/meta contracts with semantic data projected from runtime state.
5. Why must this be fixed before boundary and legacy drain? Because later constriction depends on owner-authored meaning already being the sole hot-path semantic authority.

### Broken invariant
Once a canonical semantic owner exists for a turn, downstream planner/executor/runtime layers may not mint, widen, or repopulate meaning-bearing semantic artifacts from compatibility state or execution convenience data.

### Shared mechanism
Post-owner semantic reconstruction.

### Why the surfaced family belongs to that mechanism
This is not a single dialog symptom. It is one shared downstream mechanism: owner-backed turns still pass through helpers that can reconstruct semantic contract, pending-question contract, and referent meaning outside the owner.

### Open-world envelope expected to improve after the fix
- owner-backed collect turns with conflicting booking state
- owner-backed fact turns with stale runtime semantic state
- runtime trace/meta on owner-backed turns after continuity re-projection
- any future owner-backed path that would otherwise reintroduce post-owner contract rebuilding

### Root cause statement
The runtime spine already has a real owner-backed semantic contract, but executor/runtime helpers still treat booking state, runtime projections, and compatibility payloads as valid inputs for rebuilding that contract. This leaves a live post-owner semantic reconstruction lane on the hot path.

### Fix mechanism
- make owner-backed executor pending/semantic contract builders return canonical owner contracts only;
- keep downstream additions as bounded `semantic_enrichment` rather than rebuilt contract state;
- make owner-backed runtime trace/meta project the owner contract directly, ignoring stale runtime semantic projections;
- freeze the hotspot set and add deterministic proof for owner-precedence on the active path.

## Plan
1. Create the whole-system TP for this block and keep active docs untouched until closeout.
2. Constrict executor owner-backed contract builders so they stop rebuilding semantic/pending contracts from booking/service state.
3. Constrict runtime owner-backed trace/meta projection so it uses the owner contract directly and ignores stale runtime semantic projection state.
4. Tighten the hotspot guard snapshot for the active post-owner seam set.
5. Add deterministic runtime tests that prove owner-backed contracts remain canonical under conflicting booking/runtime state.
6. Close the block only after runtime tests, architecture tests, guard chain, packet, and diff checks are green.

## DoD
- `TurnExecutor._build_execution_pending_question_contract(...)` returns the canonical owner pending-question contract on owner-backed turns.
- `TurnExecutor._build_execution_semantic_contract(...)` returns the canonical owner semantic contract on owner-backed turns and does not rebuild it from booking state or service-query hints.
- `ConsultantRuntime._project_runtime_semantic_contract(...)` ignores stale runtime semantic projection state when a canonical owner exists.
- owner-backed execution meta stays enrichment-only and does not emit `semantic_contract` / `pending_question_contract` as second-owner artifacts.
- deterministic tests prove conflicting booking/runtime state cannot override owner-backed semantic contract or pending-question contract.
- active docs and packet move from `Continuity / State Normalization` to `Post-Owner Semantic Constriction` only after checks pass.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/authority_freeze_guard.py`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/fact_family_cutover_guard.py`
- `python3 scripts/touched_slice_continuity_guard.py`
- `python3 scripts/continuity_state_normalization_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_mutation or semantic_frame or owner_backed or memory_profile or execution_contract"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_semantic_bridge_growth_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-31-consultant-core-post-owner-semantic-constriction-a922.md`
- `docs/SEMANTIC_BRIDGE_GUARD.yaml`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/consultant_runtime.py`
- updated runtime and architecture tests
- updated `docs/system_forensics/authority_registry.json`
- updated `docs/system_forensics/governance_delta.json`

## Rollback
- revert executor/runtime owner-precedence changes for this block
- revert hotspot guard snapshot changes
- restore `Continuity / State Normalization` as the active block if the post-owner block must be abandoned

## No-go
- do not solve this block with scenario-specific branches or phrase-hardcodes
- do not reintroduce `semantic_contract` / `pending_question_contract` into owner-backed execution meta as a shortcut
- do not let stale runtime semantic state override owner-authored contracts
- do not sync `STATE.md` / active docs / packet before the full block is green

## Risks / blockers
- some older tests still encode executor/runtime reconstruction as acceptable behavior and may need to be corrected to canonical-owner law;
- dialog-state semantic enrichment remains intentionally narrow in this block and wider pack/runtime separation stays open;
- frozen legacy readers still observe derived projections and are not drained here.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- broader fact families remain outside the governed first-family cutover
- boundary constriction remains open
- pack/runtime separation completion remains open
- legacy mesh drain remains open
- broader continuity carrier collapse outside the active slice remains open

### Why not in this block
This block is limited to post-owner semantic precedence on the active hot path.

### Risk if deferred
Without this block, downstream execution/runtime helpers can keep reopening semantic co-ownership even after fact-plane and continuity slices are improved.

### Linked follow-up Task Package(s)
- future boundary constriction TP
- future pack/runtime separation completion TP
- future legacy mesh drain TP

### Expiry / trigger to stop deferral
- stop deferral immediately if any owner-backed path emits or stores rebuilt semantic/pending contracts from booking/runtime state outside the canonical owner path.

## Next-block contract (mandatory)
### Next block objective
Constrict deterministic boundary/degrade so it only validates, denies, degrades with explicit reason, or preserves canonical continuity without minting new semantic meaning.

### First deterministic check command
`python3 scripts/boundary_degrade_guard.py`

### Blocked-by conditions
- owner-backed executor/runtime path still rebuilds semantic or pending-question contracts
- runtime trace/meta still merges stale runtime semantic projections over owner contracts
- semantic-bridge hotspot snapshot still drifts

### Owner role for closure
- Top Architect / Brain
