# TP-2026-03-31-consultant-core-boundary-constriction-a922

## Название / цель
Сузить whole-system boundary/degrade seam так, чтобы boundary оставался только typed validation / deny / degrade layer и не мог определять видимый reply-kind или semantic continuity шире явного handoff/system degrade envelope. На active hot path degrade must be explicit, handoff-safe, and machine-readably frozen before pack/runtime separation begins.

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
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-post-owner-semantic-constriction-a922.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_DEEP_AUDIT.md`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/BOUNDARY_DEGRADE_GUARD.yaml`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com fail fast validation boundary architecture domain model`
- Date/time (local): `2026-03-31 15:47 +0500`
- Sources opened:
  - `https://martinfowler.com/bliki/ContextualValidation.html`
- Source quality:
  - Martin Fowler architecture primary source / high-signal reference
- Ready solutions found:
  - validation must be bound to the action/context being performed, not act as a second domain owner;
  - boundary checks should remain contextual and narrow instead of broadening into generic meaning or output authorship;
  - the correct move is explicit boundary control around degrade/block paths, not downstream invention of new visible semantics.
- Decision (`reuse/integrate/build`): `reuse + integrate`
  - reuse the existing typed `BoundaryOverride`, `BoundaryValidator`, `ResponseRealizer`, and runtime boundary seam;
  - integrate stricter degrade reply-kind narrowing and explicit planner degrade metadata on the active hot path;
  - build whole-system guard/test/report sync for boundary constriction.
- Rejected options:
  - broad runtime rewrite before constricting the live boundary seam;
  - leaving degrade reply-kind fallback implicit via `decision.outcome`;
  - widening this block into pack/runtime separation or legacy drain.

## Invariant
- Do not reopen post-owner semantic constriction.
- Boundary may validate, deny, degrade with explicit reason-code, preserve canonical continuity, or request replan only.
- Boundary may not widen fact scope, mint new semantic meaning, or choose visible `fact/collect` reply kinds on degrade paths.
- Do not add semantic/fact/continuity logic to frozen legacy webhook surfaces.
- Do not sync active canon/state/packet until the full boundary block is green.

## Scope
- narrow live degrade reply-kind behavior to the explicit boundary-safe envelope
- make planner degrade-path boundary metadata explicit on the active hot path
- freeze the whole-system boundary/degrade hotspot set and callsites
- add deterministic runtime and architecture proof for boundary narrowing
- close the block via one whole-system sync after checks pass

## Out of scope
- pack/runtime separation completion
- broader fact-family migration
- legacy mesh drain or deletions
- replay or human semantic audit
- quality-lane evaluator drift work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-boundary-constriction-a922.md`
- `docs/REPORTS/2026-03-31-consultant-core-boundary-constriction-a922.md`
- `docs/BOUNDARY_DEGRADE_GUARD.yaml`
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
- `scripts/boundary_degrade_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/core/response_realizer.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_boundary_degrade_guard.py`
- `git diff --check`

## Root cause (mandatory)
### Symptom
The whole-system hot path now preserves owner-authored meaning downstream, but the boundary/degrade seam still leaves one authority gap: degrade reply shaping can still fall back to `decision.outcome`, and one planner degrade branch does not state the boundary-visible reply envelope explicitly. That leaves boundary behavior narrower than before, but not yet fully compiled into a strict handoff-safe contract.

### Minimal reproduction
1. Construct a `PolicyDecision` with outcome `FACT` or `COLLECT`.
2. Pass a `BoundaryOverride(decision="degrade")` without a valid `reply_kind` override into `ResponseRealizer.realize(...)`.
3. Observe that the realizer can still derive the visible reply kind from `decision.outcome` instead of the explicit boundary-safe envelope.
4. Inspect `_plan_turn(...)` in `ConsultantRuntime` and observe that the generic `decision.meta["degrade_path"]` branch emits a degrade override without explicit reply-kind metadata.

### Evidence
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_DEEP_AUDIT.md`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/response_realizer.py`
- `truffles-api/app/core/consultant_runtime.py`
- `docs/BOUNDARY_DEGRADE_GUARD.yaml`

### Five Whys
1. Why is boundary work still open after typed boundary seams exist?
   - Because the repo has the seam, but not the fully narrowed behavior contract for every degrade path.
2. Why is that a blocker?
   - Because boundary can still influence visible reply semantics more broadly than a strict deny/degrade layer should.
3. Why does reply-kind fallback matter?
   - Because fallback to `decision.outcome` lets a degrade path reuse `fact/collect` semantics instead of staying in an explicit safe degrade envelope.
4. Why does the planner degrade metadata matter?
   - Because one generic degrade path still relies on implicit response-realizer behavior instead of an explicit boundary contract.
5. Why must this close before pack/runtime separation?
   - Because later fact and pack/runtime closure depends on boundary already being a strict validator/degrade layer, not a second visible behavior router.

### Broken invariant
Deterministic boundary may not decide visible `fact/collect` reply behavior after the owner speaks; degrade must remain an explicit, bounded handoff/system control path.

### Shared mechanism
Boundary constriction.

### Why the surfaced family belongs to that mechanism
This is not a scenario patch. It is one shared downstream mechanism: boundary overrides and degrade handling still retain a broader visible reply fallback than the governing boundary law allows.

### Open-world envelope expected to improve after the fix
- any future degrade path without explicit `reply_kind` stays handoff-safe
- planner-generated degrade paths remain explicit in meta/trace instead of depending on implicit realizer fallback
- boundary hotspot growth stays frozen under one machine-readable guard
- future fact-plane and pack/runtime work no longer has to compensate for broad boundary reply shaping

### Root cause statement
The runtime spine already has a typed boundary seam, but boundary closure is still incomplete because degrade handling still retains an implicit visible reply-kind fallback via `decision.outcome`, and one generic planner degrade path does not state its boundary-safe envelope explicitly.

### Fix mechanism
- make `ResponseRealizer` default degrade replies to the strict boundary-safe envelope instead of `decision.outcome`
- make the generic planner degrade path emit explicit handoff boundary metadata
- keep the boundary hotspot set frozen and prove the narrowed behavior with deterministic runtime and architecture tests

## Plan
1. Author this whole-system TP and keep active docs untouched until full boundary closeout.
2. Narrow `ResponseRealizer` degrade reply-kind fallback so it cannot emit `fact/collect` from a boundary-degrade path.
3. Make the generic planner `degrade_path` override explicit about handoff reply-kind metadata.
4. Refresh boundary runtime tests and boundary guard proof around the narrowed seam.
5. Close the block only after guard chain, runtime tests, architecture tests, packet, and diff checks are green.

## DoD
- `ResponseRealizer.realize(...)` no longer derives degrade `reply_kind` from `decision.outcome`; degrade stays in the explicit boundary-safe envelope.
- the generic planner `degrade_path` branch emits explicit handoff boundary metadata.
- `docs/BOUNDARY_DEGRADE_GUARD.yaml` and `scripts/boundary_degrade_guard.py` remain in sync with the live hotspot/callsite set.
- deterministic tests prove degrade reply kinds cannot widen into `fact/collect`, planner invalid/degrade paths remain explicit, and the repo boundary snapshot stays frozen.
- active docs and packet move from `Post-Owner Semantic Constriction` to `Boundary Constriction` only after checks pass.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/authority_freeze_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/fact_family_cutover_guard.py`
- `python3 scripts/touched_slice_continuity_guard.py`
- `python3 scripts/continuity_state_normalization_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/boundary_degrade_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "boundary or invalid_outcome or handoff or ignored_path"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_boundary_degrade_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-31-consultant-core-boundary-constriction-a922.md`
- `docs/BOUNDARY_DEGRADE_GUARD.yaml`
- `truffles-api/app/core/response_realizer.py`
- `truffles-api/app/core/consultant_runtime.py`
- updated runtime and architecture tests
- updated `docs/system_forensics/authority_registry.json`
- updated `docs/system_forensics/governance_delta.json`

## Rollback
- revert boundary reply-kind narrowing and planner degrade metadata changes
- revert boundary guard/test updates
- restore `Post-Owner Semantic Constriction` as the active block if the boundary block must be abandoned

## No-go
- do not solve this block with scenario-specific branches or phrase hardcodes
- do not use boundary to synthesize new pending-question or fact-scope semantics
- do not widen this block into pack/runtime separation or legacy deletion
- do not sync `STATE.md` / active docs / packet before the full block is green

## Risks / blockers
- older tests may implicitly encode broader degrade fallback behavior and will need to be corrected to the stricter boundary law
- boundary hotspot freeze already exists from earlier canary work, so closeout wording must stay honest about preserved vs newly reduced authority
- broader boundary-heavy legacy timeout services remain outside this block and must not be overclaimed

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- pack/runtime separation completion remains open
- broader fact families remain open
- legacy mesh drain remains open
- replay and human semantic audit remain closed

### Why not in this block
This block constricts only the active whole-system boundary/degrade seam after post-owner semantic precedence is in force.

### Risk if deferred
Without this block, later fact/pack/runtime work can still inherit a boundary layer that remains broader than the governing architecture allows.

### Linked follow-up Task Package(s)
- future pack/runtime separation completion TP
- future legacy mesh drain TP
- future whole-system governance closure TP

### Expiry / trigger to stop deferral
- stop deferral immediately if any new boundary path emits `fact/collect` degrade replies or consumes new semantic/continuity meta keys.

## Next-block contract (mandatory)
### Next block objective
Constrict pack/runtime behavior so tenant/domain differences stop living in active runtime behavior branches and the fact contract remains the sole fact authority surface.

### First deterministic check command
`python3 scripts/fact_plane_guard.py`

### Blocked-by conditions
- boundary degrade still able to emit non-explicit `fact/collect` reply kinds
- planner degrade-path not explicit in boundary metadata
- boundary hotspot/callsite guard not stable

### Owner role for closure
- Top Architect / Brain
