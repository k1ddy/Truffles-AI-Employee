# TP-2026-03-30-consultant-core-post-owner-reconstruction-constriction-a922

## Название / цель
Зафиксировать и закрыть текущий post-owner reconstruction seam set как активный root-first recovery block. Этот блок не должен нормализовать всю continuity или строить fact plane; он должен сделать machine-readable и deterministically-guarded тот факт, что owner-backed hot path уже не допускает post-owner semantic rewrite без явного degrade, а новые reconstruction seams не могут незаметно вырасти.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/DECISIONS/DEC-2026-03-30-consultant-core-architecture-recovery-governing-decision.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-owner-output-singularity-cut-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-owner-adjacent-shadow-cut-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-executor-semantic-output-constriction-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-runtime-owner-precedence-cut-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-workstream1-memory-profile-canonical-read-cut-a922.md`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com cqrs read model source of truth derived data projection`
- Date/time (local): `2026-03-30 15:34:08 +0500`
- Sources opened:
  - `https://martinfowler.com/bliki/EagerReadDerivation.html`
- Source quality:
  - high-signal architecture source / Martin Fowler
- Ready solutions found:
  - the write model and its derived read/projection layers must stay explicitly separated;
  - derivation is acceptable only when projections do not become peer sources of truth;
  - projection drift is prevented by making the derivation contract explicit and bounded.
- Decision (`reuse/integrate/build`): `reuse + integrate`
  - reuse the current owner-backed runtime cuts already present in `turn_planner`, `turn_executor`, `consultant_runtime`, and `dialog_state_service`;
  - integrate one machine-readable hotspot freeze plus deterministic runtime proof that post-owner mutation is blocked on the live hot path.
- Rejected options:
  - reopen broad runtime redesign before proving the current seam set;
  - treat prior workstream cuts as sufficient without current-canon registry/guard alignment;
  - widen this block into continuity normalization or fact-plane work.

## Invariant
- Do not reintroduce any second semantic owner.
- Do not let planner / executor / runtime shell silently mutate owner-authored `action`, `intent`, `slots`, pending-question meaning, or shadow carriers on owner-backed turns.
- Do not widen this block into continuity normalization, fact-plane materialization, or legacy deletion.
- Do not weaken existing schema/mutation guards to make tests pass.

## Scope
- Materialize the active post-owner reconstruction seam set in machine-readable guard config and authority registry evidence.
- Add deterministic runtime proof that `_plan_turn(...)` degrades when owner-backed decisions are mutated after the owner speaks.
- Close the missing schema proof that owner-backed `semantic_frame` cannot be repopulated as a live carrier.
- Sync the active canon/program/packet/report/state to the post-owner reconstruction block.

## Out of scope
- Boundary/degrade constriction beyond existing typed override paths.
- Continuity normalization of enriched referents or other continuity payloads.
- Fact-plane materialization.
- Legacy mesh deletion.
- Family-specific fixes such as `location / hours / parking`.

## Touch-list
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/SEMANTIC_BRIDGE_GUARD.yaml`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `scripts/recovery_execution_guard.py`
- `scripts/semantic_bridge_growth_guard.py`
- `scripts/continuity_writer_guard.py`
- `scripts/legacy_mesh_caller_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_truth_carrier_freeze.py`
- `truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `truffles-api/tests/architecture/test_semantic_bridge_growth_guard.py`
- `truffles-api/tests/architecture/test_single_continuity_writer.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `docs/REPORTS/2026-03-30-consultant-core-adapter-only-legacy-mesh-and-caller-proof-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-post-owner-reconstruction-constriction-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-adapter-only-legacy-mesh-and-caller-proof-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-post-owner-reconstruction-constriction-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Freeze the exact post-owner reconstruction hotspot set in `docs/SEMANTIC_BRIDGE_GUARD.yaml`.
2. Update `authority_registry.json` so the post-owner mechanism reflects the current repo truth, not the older narrative-only carrier list.
3. Add deterministic proof that runtime `_plan_turn(...)` blocks post-owner mutation on the live owner-backed path.
4. Add the missing schema proof for owner-backed populated `semantic_frame`.
5. Sync source-of-truth / active canon / packet / report / state to this block.

## Root cause (mandatory)
### Symptom
The repo already contains several bounded workstream cuts that constrain owner-backed post-owner reconstruction, but the current root-first program still lacks one active-block proof layer that freezes the exact seam set and proves the runtime guard actually fires on the hot path.

### Minimal reproduction
1. Inspect `truffles-api/app/core/turn_planner.py`, `truffles-api/app/core/turn_executor.py`, `truffles-api/app/core/consultant_runtime.py`, and `truffles-api/app/core/dialog_state_service.py`.
2. Observe that the owner-backed path is already partially constrained: planner shadow carriers stay empty, executor emits `semantic_enrichment` only on owner-backed turns, runtime prefers canonical owner projections, and memory-profile reads canonical state.
3. Observe that the active root-first artifacts still do not freeze the exact reconstruction hotspot set in one machine-readable guard config.
4. Observe that current deterministic tests prove mutation detection in isolation, but not that `ConsultantRuntime._plan_turn(...)` actually degrades when a post-owner mutation reaches the live hot path.
5. Observe that there is no explicit schema proof for owner-backed populated `semantic_frame` as a blocked shadow-carrier violation.

### Evidence
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`

### Five Whys
1. Why is the block still open even though several runtime cuts already landed? Because the root-first program requires mechanism-level proof and guard closure, not just earlier bounded implementation slices.
2. Why is earlier bounded code not enough by itself? Because future drift can still add one more reconstruction seam unless the seam set is frozen machine-readably and checked deterministically.
3. Why does `_plan_turn(...)` runtime proof matter? Because the semantic writer law is violated only if a live caller can mutate owner output without a typed degrade, not merely because a unit helper can detect the mutation.
4. Why does schema proof for populated `semantic_frame` matter? Because owner-backed shadow carriers must stay shadow-only both in code and in contract.
5. Why must this happen before boundary or fact-plane work? Because those later blocks depend on the owner-backed hot path already being constrained and provably guarded against post-owner meaning drift.

### Broken invariant
After the owner speaks, planner / executor / runtime shell may not mutate owner meaning-bearing artifacts without an explicit typed degrade path.

### Shared mechanism
Post-owner semantic reconstruction constriction.

### Why this surfaced family belongs to that mechanism
This is not one test gap and not one local bug. It is the missing active-block proof and freeze layer for the mechanism that sits between semantic owner output and runtime/state projections.

### Open-world envelope expected to improve after the fix
- new post-owner reconstruction helpers cannot appear silently in the core hotspot files;
- owner-backed runtime turns prove that mutation reaches a typed degrade rather than silently surviving;
- the active machine-readable authority map reflects the real post-owner carrier set rather than older narrative-only assumptions.

### Root cause statement
The repository already contains most of the bounded runtime constriction for owner-backed post-owner reconstruction, but the current root-first block still lacks one machine-readable hotspot freeze and one live runtime proof that the mutation guard fires through `_plan_turn(...)`. Without that layer, the mechanism is only partially closed and future reconstruction drift remains too easy.

### Fix mechanism
- freeze the exact hotspot function set in `docs/SEMANTIC_BRIDGE_GUARD.yaml`;
- refresh `authority_registry.json` to the current post-owner carrier truth;
- add deterministic runtime and schema proofs for owner-backed mutation rejection;
- sync packet/canon/report/state to the new active block.

## DoD
- `docs/SEMANTIC_BRIDGE_GUARD.yaml` machine-readably freezes the current post-owner reconstruction hotspot set.
- `authority_registry.json` reflects the current post-owner carrier truth for owner-backed paths.
- deterministic tests prove `ConsultantRuntime._plan_turn(...)` degrades on post-owner mutation, including at least one non-shadow semantic mutation and one shadow-carrier mutation.
- deterministic tests prove owner-backed populated `semantic_frame` is rejected by contract.
- active canon/program/packet/report/state are synced to this block.
- no new semantic authority is introduced.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_mesh_caller_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "semantic_mutation or semantic_frame or owner_backed or memory_profile"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_semantic_bridge_growth_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/SEMANTIC_BRIDGE_GUARD.yaml`
- updated `docs/system_forensics/authority_registry.json`
- updated source-of-truth / active canon / packet / report / state
- updated deterministic runtime and architecture tests

## Rollback
- restore the previous active block docs and remove the new post-owner hotspot freeze / proof updates only

## No-go
- do not widen this block into boundary, fact-plane, or continuity-normalization work
- do not claim full runtime closure if enriched continuity/state projections still remain as residual debt
- do not treat one unit test as enough if the live hot-path runtime proof is still missing

## Risks / blockers
- older tests may still encode pre-root-first narrative assumptions about the post-owner carrier set
- hotspot freeze that is too broad will create noisy guard failures; hotspot freeze that is too narrow will miss drift
- continuity-enrichment residuals inside canonical state remain and must not be mislabeled as solved by this block

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- canonical continuity state still carries derived semantic-enrichment style payloads that are not yet normalized slice-by-slice
- boundary/degrade constriction is still open
- first-class fact plane is still missing
- legacy webhook compatibility readers still exist outside the hot-path owner core

### Why not in this block
This block constricts and proves post-owner runtime meaning discipline. It does not yet normalize all continuity payloads or materialize fact contracts.

### Risk if deferred
Future cuts could silently reintroduce post-owner semantic shaping and claim they only touched a local runtime helper.

### Linked follow-up Task Package(s)
- boundary/degrade constriction block
- fact-plane materialization block
- touched-slice continuity normalization block

### Expiry / trigger to stop deferral
- stop deferral immediately if a new owner-backed runtime helper starts minting semantic carriers or if runtime mutation guard proof drifts red

## Next-block contract (mandatory)
### Next block objective
Constrict deterministic boundary/degrade so it only validates, denies, degrades with explicit reason, requests replan, or preserves canonical continuity — without writing new semantic meaning.

### First deterministic check command
`python3 - <<'PY'
from pathlib import Path
assert Path('docs/SEMANTIC_BRIDGE_GUARD.yaml').exists()
assert Path('docs/system_forensics/authority_registry.json').exists()
print('post_owner_block_ready')
PY`

### Blocked-by conditions
- post-owner hotspot freeze not materialized
- runtime `_plan_turn(...)` still lacks deterministic mutation-guard proof
- authority registry still describes stale post-owner carriers

### Owner role for closure
Brain / Top Architect
