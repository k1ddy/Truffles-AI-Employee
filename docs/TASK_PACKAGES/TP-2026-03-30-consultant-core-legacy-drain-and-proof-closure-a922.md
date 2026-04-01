# TP-2026-03-30-consultant-core-legacy-drain-and-proof-closure-a922

## Название / цель
Закрыть последний root-first implementation block для уже затронутого canary mechanism envelope. Цель блока — не объявить всю legacy mesh удаленной, а сузить mounted package root так, чтобы touched `location / hours / parking` envelope больше не подгружал startup-loaded legacy helper writers, и зафиксировать machine-readable proof, что для этого envelope старые поверхности либо adapter-only, либо unreachable.

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
- `docs/LEGACY_SUNSET.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-architecture-recovery-master-program-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-touched-slice-continuity-normalization-a922.md`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com strangler fig application legacy adapter pattern old path unreachable`
- Date/time (local): `2026-03-30 19:03:00 +0500`
- Sources opened:
  - `https://martinfowler.com/bliki/OriginalStranglerFigApplication.html`
- Source quality:
  - high-signal primary architecture source / Martin Fowler
- Ready solutions found:
  - legacy displacement should keep the new path authoritative while the old path degrades to adapter or unreachable status;
  - the critical proof is not deleting every old file at once but proving that the old path no longer participates in the governed behavior;
  - startup loading of compatibility surfaces can preserve accidental authority even when hot-path logic has moved.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the governed consultant runtime hot path and the existing machine-readable surface registry;
  - integrate a startup-load drain in `webhook/__init__.py` instead of editing frozen legacy files;
  - build the final legacy-drain closure guard and deterministic proof layer for the touched mechanism envelope.
- Rejected options:
  - claim global legacy deletion without touched-envelope proof;
  - edit frozen legacy helper files to make the closure story look cleaner;
  - skip machine-readable proof and rely on narrative-only reasoning about imports.

## Invariant
- Do not reopen earlier root-first blocks.
- Do not add semantic, continuity, or fact logic to frozen legacy surfaces.
- Do not claim practical/product closure from deterministic proof alone.
- Keep the touched canary envelope on the governed runtime path.
- Any remaining legacy surface in this block must be explicitly classified as adapter-only or unreachable for the touched envelope.

## Scope
- mounted package-root startup-load drain for legacy webhook helper exports
- exact touched-envelope proof for `location / hours / parking`
- machine-readable registry/guard/test/report sync for final legacy drain on the already-touched envelope
- runtime proof that the only live legacy seam on the governed path is ingress preflight + reset-only control helper usage

## Out of scope
- deleting the entire legacy webhook tree
- global continuity redesign beyond the touched envelope
- fresh practical replay and full human semantic audit acceptance
- product-ready closure claim
- non-canary fact families

## Touch-list
- `docs/LEGACY_DRAIN_CLOSURE_GUARD.yaml`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `scripts/legacy_drain_closure_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/app/routers/webhook/__init__.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `truffles-api/tests/architecture/test_legacy_drain_closure_guard.py`
- `docs/REPORTS/2026-03-30-consultant-core-legacy-drain-and-proof-closure-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-legacy-drain-and-proof-closure-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Activate block 10 in canon/source-of-truth and define the machine-readable legacy-drain closure guard.
2. Drain startup-loaded legacy helper imports from `truffles-api/app/routers/webhook/__init__.py` while preserving lazy compatibility exports for tests and shadow callers.
3. Update the surface registry so the touched envelope records which surfaces are adapter-only, which are unreachable, and which startup-loaded surfaces are now lazy-export-only.
4. Add deterministic proof that `consultant_runtime.py` imports only the allowed legacy seam (`http._run_preflight` and reset-only `session_memory` helpers) and that normal first-family fact turns do not route through the control-turn helper.
5. Sync authority/compatibility registries, packet, state, structure, and report, and leave practical replay + human semantic audit explicitly open.

## Root cause (mandatory)
### Symptom
After block 9, the first canary family already used canonical runtime continuity and the explicit fact plane, but the mounted `app.routers.webhook` package root still eagerly imported several legacy helper modules at startup. That left the final legacy story too broad: the touched envelope was functionally governed by the new path, yet the package surface still loaded old helper surfaces as if they were live runtime participants.

### Minimal reproduction
1. Import `app.routers.webhook` on the mounted runtime path.
2. Observe that `webhook/__init__.py` eagerly imports legacy helper surfaces such as `booking`, `context_manager`, `dedup`, and `response`.
3. Compare that to the actual governed canary envelope, whose live path is now `consultant_runtime -> turn_planner -> turn_executor -> dialog_state_service` plus preflight and reset-only control helpers.
4. Observe that the registry still needs one more closure step to distinguish startup-loaded compatibility exports from true live touched-envelope authority.

### Evidence
- `truffles-api/app/routers/webhook/__init__.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/app/routers/webhook/http.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`

### Five Whys
1. Why was the touched envelope not ready for final closure after block 9? Because continuity and fact authority had moved, but legacy package startup still loaded helper surfaces broader than the governed envelope.
2. Why does startup loading matter if those helpers are not on the hot path? Because it preserves an ambiguous live authority picture and makes future drift easier.
3. Why not edit the legacy helpers directly? Because they are frozen authority surfaces; the narrow admissible move is to drain or lazy-wrap their callers outside those files.
4. Why is `webhook/__init__.py` the right place? Because it is the mounted package surface that still widened runtime startup reachability without being the semantic owner.
5. Why is this a mechanism closure step rather than cleanup? Because it reduces live legacy reachability for the already-governed canary envelope and turns the residual legacy seam into explicit adapter-only proof.

### Broken invariant
Once the canary family is governed by canonical runtime state and the explicit fact plane, mounted package startup may not continue to present unrelated legacy helper modules as if they were live touched-envelope runtime dependencies.

### Shared mechanism
Mounted package-root legacy startup loading versus explicit adapter-only touched-envelope seam.

### Why this surfaced family belongs to that mechanism
`location / hours / parking` is already the only family whose semantics, fact scope, and touched continuity moved onto the governed path. That makes it the first legitimate envelope where final legacy drain can be proven instead of guessed.

### Open-world envelope expected to improve after the fix
- future startup imports of `app.routers.webhook` no longer drag legacy helper writers into the mounted path by default;
- touched canary turns rely only on the governed runtime path plus explicit ingress/reset adapters;
- future drift becomes easier to catch because the residual legacy seam is machine-readable and narrow.

### Root cause statement
The first canary family still lacked final legacy closure because the mounted webhook package root eagerly imported legacy helper modules even though the family’s actual governed path had already moved to canonical runtime and the explicit fact plane.

### Fix mechanism
Drain eager legacy helper imports from `webhook/__init__.py`, keep them as lazy compatibility exports only, and add machine-readable proof that the touched envelope now sees legacy surfaces only as explicit adapters or unreachable residues.

## DoD
- block 10 is the active block in canon/source-of-truth/packet
- `webhook/__init__.py` no longer eagerly imports legacy helper modules for booking/context-manager/dedup/response
- the touched canary envelope records explicit adapter-only versus unreachable legacy surfaces in machine-readable form
- `consultant_runtime.py` proves the only remaining allowed legacy seam is ingress preflight plus reset-only session-memory control helpers
- deterministic guard/test evidence is green and registry/report/state/structure are synced
- practical replay and full human semantic audit remain explicitly open rather than silently implied

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/legacy_drain_closure_guard.py`
- `python3 scripts/touched_slice_continuity_guard.py`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/fact_family_cutover_guard.py`
- `python3 scripts/boundary_degrade_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_mesh_caller_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "control_turn_gate_does_not_claim_first_fact_family_question or reset_runtime_context_clears_touched_slice_carryover or projects_touched_slice_class_carryover or persists_semantic_runtime_path"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_drain_closure_guard.py`
- `git diff --check`

## Evidence
- `docs/LEGACY_DRAIN_CLOSURE_GUARD.yaml`
- `scripts/legacy_drain_closure_guard.py`
- `truffles-api/app/routers/webhook/__init__.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_legacy_drain_closure_guard.py`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/REPORTS/2026-03-30-consultant-core-legacy-drain-and-proof-closure-a922.md`

## Rollback
- restore the eager legacy helper imports in `truffles-api/app/routers/webhook/__init__.py`
- remove the new legacy-drain closure guard and return source-of-truth to block 9 if the startup-load drain proves unsafe

## No-go
- do not edit frozen legacy helper files for convenience
- do not claim the entire legacy tree is deleted
- do not claim final program completion without fresh replay and full human semantic audit
- do not widen this block into unrelated product-family fixes

## Risks / blockers
- lazy compatibility exports can still keep shadow/tests working, but a missed export would break compatibility callers immediately
- global legacy authority still exists outside the touched envelope
- practical replay / human semantic acceptance still remains a separate closure lane

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- global legacy surfaces still exist outside the touched canary envelope
- practical replay and full human semantic audit are still not rerun on this new head
- broader semantic and continuity debt beyond the canary slice still remains open at program level

### Why not in this block
This is the final architecture-recovery implementation block, not the replay/audit acceptance lane and not a global legacy deletion campaign.

### Risk if deferred
If package-root startup drain is not done now, the canary mechanism still appears to depend on broader legacy helpers than it actually does, which makes future authority drift easier.

### Linked follow-up Task Package(s)
- none inside the root-first implementation sequence
- acceptance follow-up remains `practical replay + full human semantic audit` under `docs/PRACTICAL_CLOSURE_ADDENDUM.md`

### Expiry / trigger to stop deferral
- stop deferral immediately if a new core hot-path file imports a frozen legacy helper directly or if the mounted package root regains eager legacy helper imports

## Next-block contract (mandatory)
### Next block objective
There is no additional root-first implementation block after block 10. The next admissible step is acceptance closure: fresh practical replay plus full human semantic audit for the recovered canary mechanism envelope.

### First deterministic check command
`python3 scripts/legacy_drain_closure_guard.py`

### Blocked-by conditions
- `webhook/__init__.py` still eagerly imports legacy booking/context-manager/dedup/response helpers
- the dead-surface registry does not distinguish adapter-only versus unreachable touched-envelope surfaces
- `consultant_runtime.py` imports any legacy webhook helper beyond the allowed preflight/reset seam

### Owner role for closure
Brain / Top Architect
