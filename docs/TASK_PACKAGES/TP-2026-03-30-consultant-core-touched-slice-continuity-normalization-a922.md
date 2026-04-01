# TP-2026-03-30-consultant-core-touched-slice-continuity-normalization-a922

## Название / цель
Нормализовать continuity для уже затронутого canary family `location / hours / parking` так, чтобы family-level info follow-up continuity больше не зависела от живого legacy class-carryover writer mesh. Для этого canonical runtime state должен писать touched-slice class carryover на governed hot path, а `context_manager.class_carryover` должен оставаться derived compatibility projection от canonical runtime payload, а не самостоятельным автором continuity.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/DECISIONS/DEC-2026-03-30-consultant-core-architecture-recovery-governing-decision.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-architecture-recovery-master-program-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-fact-contract-location-hours-parking-first-slice-a922.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com event sourcing projection source of truth mutable state derived projection`
- Date/time (local): `2026-03-30 18:06:08 +0500`
- Sources opened:
  - site-filtered `martinfowler.com` result set for projection / source-of-truth / derived projection architecture
- Source quality:
  - high-signal architecture source class / Martin Fowler
- Ready solutions found:
  - mutable source of truth should stay singular while downstream projections remain derived read models;
  - projections are allowed to mirror state for compatibility, but they must not regain authorship;
  - continuity slices should be normalized by moving the mutable artifact into canonical state and projecting outward, not by hardening legacy mirrors.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the existing `DialogStateService` canonical continuity nucleus and the existing class-carryover payload helpers;
  - integrate the touched fact family into that nucleus by writing canonical `meta.class_carryover` on the governed runtime path;
  - build only the touched-slice continuity guard/proof layer plus the minimal compatibility projection needed for legacy readers.
- Rejected options:
  - writing new continuity logic into frozen legacy webhook files;
  - widening this block into generic continuity cleanup for every family;
  - leaving `context_manager.class_carryover` as the live touched-slice owner after the fact-family cutover.

## Invariant
- Do not reopen earlier root-first blocks.
- Do not edit frozen legacy router files.
- Do not introduce a second continuity writer outside `DialogStateService`.
- The touched slice must move continuity authority, not just duplicate it.
- Compatibility carriers may mirror the touched slice, but they may not author it.

## Scope
- `location / hours / parking` continuity only.
- Canonical runtime `DialogState.meta.class_carryover` for the touched slice.
- Derived `context_manager.class_carryover` and `context_manager.canonical_dialog_state.meta.class_carryover` projection for the touched slice.
- Deterministic guard / tests / registry / report / canon sync for the touched-slice continuity seam.

## Out of scope
- all other fact families
- generic session-memory redesign
- legacy mesh deletion
- full practical replay / human semantic closure
- legacy drain and proof closure

## Touch-list
- `docs/TOUCHED_SLICE_CONTINUITY_GUARD.yaml`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `scripts/touched_slice_continuity_guard.py`
- `scripts/recovery_execution_guard.py`
- `scripts/continuity_writer_guard.py`
- `scripts/legacy_mesh_caller_guard.py`
- `scripts/semantic_bridge_growth_guard.py`
- `scripts/boundary_degrade_guard.py`
- `scripts/fact_plane_guard.py`
- `scripts/fact_family_cutover_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_touched_slice_continuity_guard.py`
- `docs/REPORTS/2026-03-30-consultant-core-touched-slice-continuity-normalization-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-fact-contract-location-hours-parking-first-slice-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-touched-slice-continuity-normalization-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Activate block 9 in canon/source-of-truth and define the machine-readable touched-slice continuity guard.
2. Move the first-family carryover artifact into canonical runtime state by having `DialogStateService.write_runtime_payload(...)` author `DialogState.meta.class_carryover` for the governed family.
3. Project that canonical touched-slice artifact into `context_manager.class_carryover` and `context_manager.canonical_dialog_state.meta.class_carryover` as derived compatibility mirrors.
4. Prove that the touched-slice payload survives the next non-family turn without regaining legacy authorship.
5. Sync authority registry, compatibility carrier inventory, packet, state, structure, and report to block 9.

## Root cause (mandatory)
### Symptom
After block 8, the first fact family used the explicit fact plane on the governed hot path, but its continuity still depended on the legacy class-carryover mesh. The runtime hot path itself did not yet author the touched-slice carryover artifact canonically.

### Minimal reproduction
1. Execute a first-family `hours` fact turn through the governed hot path.
2. Observe that the runtime payload does not author `DialogState.meta.class_carryover` even though legacy `context_manager.class_carryover` remains the follow-up continuity surface.
3. Observe that the next follow-up turn can still rely on compatibility carryover state that was not authored by the canonical runtime hot path.

### Evidence
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`

### Five Whys
1. Why did block 8 not close touched-slice continuity? Because block 8 cut over resolver authority, not the continuity artifact used for short info follow-ups.
2. Why did continuity stay mixed? Because `class_carryover` still lived primarily as a legacy compatibility carrier and the governed runtime path did not re-author it canonically.
3. Why is that a mechanism problem rather than a local follow-up bug? Because the same continuity artifact spans multiple turns and legacy readers, so leaving authorship in compatibility state preserves mixed authority.
4. Why is `DialogStateService` the right move? Because it already owns canonical mutable continuity state and already exposes the class-carryover payload helpers.
5. Why keep a compatibility mirror at all? Because legacy readers are still live, but they must read a derived mirror of the canonical artifact rather than remain the touched-slice writer.

### Broken invariant
The touched slice may not rely on a compatibility carrier as its mutable continuity owner once the governed runtime path already owns the family.

### Shared mechanism
Canonical touched-slice continuity artifact with derived compatibility projection.

### Why this surfaced family belongs to that mechanism
`location / hours / parking` is the first fact family already cut over onto the governed hot path, so it is the first slice where continuity can be moved into canonical runtime state without broad speculative cleanup.

### Open-world envelope expected to improve after the fix
- short follow-up turns after `location / hours / parking` replies;
- booking-interrupt info turns that re-enter the first fact family;
- legacy class-router readers that still need a mirror but should no longer own the touched slice.

### Root cause statement
The first fact family still carried continuity debt because resolver authority had moved to the governed runtime path, but the family-level carryover artifact remained authored in compatibility space instead of canonical runtime state.

### Fix mechanism
Write the first-family class-carryover artifact into `DialogState.meta.class_carryover` on the governed hot path and mirror it into `context_manager.class_carryover` / `context_manager.canonical_dialog_state.meta.class_carryover` as derived compatibility payloads only.

## DoD
- block 9 is the active block in canon/source-of-truth/packet
- `DialogStateService.write_runtime_payload(...)` authors canonical touched-slice `meta.class_carryover` for the first fact family
- the next non-family turn preserves the canonical touched-slice artifact instead of dropping back to legacy authorship
- `context_manager.class_carryover` and `context_manager.canonical_dialog_state.meta.class_carryover` are derived mirrors of the canonical runtime payload for the touched slice
- deterministic guard/test evidence is green and registry/report/state/structure are synced

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/touched_slice_continuity_guard.py`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/fact_family_cutover_guard.py`
- `python3 scripts/boundary_degrade_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_mesh_caller_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_dialog_state_service.py -k "touched_slice_class_carryover or materializes_touched_slice_class_carryover or preserves_existing_touched_slice_class_carryover"`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "projects_touched_slice_class_carryover or persists_semantic_runtime_path"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_single_continuity_writer.py`
- `pytest -q truffles-api/tests/architecture/test_truth_carrier_freeze.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `pytest -q truffles-api/tests/architecture/test_semantic_bridge_growth_guard.py`
- `pytest -q truffles-api/tests/architecture/test_boundary_degrade_guard.py`
- `pytest -q truffles-api/tests/architecture/test_fact_plane_guard.py`
- `pytest -q truffles-api/tests/architecture/test_fact_family_cutover_guard.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "continuity_writer"`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "legacy_root_webhook_is_thin_delegate_only or booking_prompt_owner_removed_from_app_core or reasoning_core_has_no_app_runtime_importers or webhook_legacy_adapter_uses_explicit_export_allowlist"`
- `pytest -q truffles-api/tests/architecture/test_touched_slice_continuity_guard.py`
- `git diff --check`

## Evidence
- `docs/TOUCHED_SLICE_CONTINUITY_GUARD.yaml`
- `scripts/touched_slice_continuity_guard.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_touched_slice_continuity_guard.py`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/REPORTS/2026-03-30-consultant-core-touched-slice-continuity-normalization-a922.md`

## Rollback
- revert the touched-slice class-carryover write/projection changes in `truffles-api/app/core/dialog_state_service.py`
- drop the touched-slice continuity guard and restore block 8 as the active source-of-truth block if the continuity normalization must be abandoned

## No-go
- do not widen into generic continuity refactor
- do not edit frozen legacy router surfaces
- do not claim full continuity closure for all families
- do not claim practical or human-semantic closure from deterministic proof alone

## Risks / blockers
- legacy readers remain live, so any mismatch between canonical carryover and derived mirror will still surface behavior drift
- session-memory and broader compatibility carriers still remain outside this block
- final legacy drain / proof closure still remains necessary before program completion

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- only the first fact family continuity is normalized; other continuity carriers remain mixed
- session-memory and pending-resume carriers are still broader than the touched family
- legacy mesh is still live outside the governed touched slice

### Why not in this block
The governing order limits this block to the touched canary slice after resolver cutover and before final legacy drain.

### Risk if deferred
If the touched slice is not normalized now, the first family can still regress via compatibility carryover even though resolver authority moved to the explicit fact plane.

### Linked follow-up Task Package(s)
- `legacy_drain_and_proof_closure`

### Expiry / trigger to stop deferral
- stop deferral immediately if the first fact family regains a live legacy carryover writer outside `DialogStateService` or if a new canonical/compatibility mismatch appears in the touched slice

## Next-block contract (mandatory)
### Next block objective
Drain the remaining legacy behavior authority and prove that old authority paths are adapter-only or unreachable for the already-touched mechanism envelope.

### First deterministic check command
`python3 - <<'PY'
from pathlib import Path
assert Path('docs/TOUCHED_SLICE_CONTINUITY_GUARD.yaml').exists()
assert Path('scripts/touched_slice_continuity_guard.py').exists()
print('touched_slice_continuity_block_ready_for_legacy_drain')
PY`

### Blocked-by conditions
- first fact-family carryover is still authored primarily in `context_manager.class_carryover`
- canonical runtime payload does not preserve the touched-slice artifact across the next non-family turn
- deterministic guard cannot prove the runtime-to-compatibility projection chain

### Owner role for closure
Brain / Top Architect
