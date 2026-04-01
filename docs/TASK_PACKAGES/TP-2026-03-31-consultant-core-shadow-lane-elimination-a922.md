# TP-2026-03-31-consultant-core-shadow-lane-elimination-a922

## Название / цель
Удалить runtime shadow-wrapper lanes `truffles-api/app/services/reasoning_core.py` и `truffles-api/app/webhook.py` из живого кода так, чтобы их контракты сохранились только в test-only support residues, а router shadow surfaces `decision.py` и `_legacy.py` остались вне live app runtime.

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
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-legacy-mesh-drain-a922.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`

## One web search (mandatory before implementation)
- Query: `site:fastapi.tiangolo.com APIRouter include_router FastAPI official docs`
- Date/time (local): `2026-03-31 23:35 +0500`
- Sources opened:
  - `https://fastapi.tiangolo.com/reference/apirouter/`
  - `https://fastapi.tiangolo.com/tutorial/bigger-applications/`
- Source quality:
  - official FastAPI documentation / primary source
- Ready solutions found:
  - legacy route wrappers can survive only as thin compatibility delegates while the mounted router tree routes through the canonical package/router composition;
  - shadow wrappers should preserve route/function contracts for tests without staying mounted in the live runtime;
  - route-layer elimination should remove the runtime file, then keep any residual contract only in test support until the next infrastructure block.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the existing public entrypoint contract and mounted webhook package composition;
  - integrate test-only shadow support files for the deleted wrapper lanes;
  - build only the missing guard/config/report sync for the shadow-lane block.
- Rejected options:
  - keeping `app/services/reasoning_core.py` as a runtime shadow delegate;
  - keeping `app/webhook.py` as an unmounted runtime wrapper;
  - deleting `decision.py` or `_legacy.py` in this block;
  - starting operational entrypoint dedupe before the shadow wrapper lanes are removed.

## Invariant
- Do not reopen fact-contract, continuity, boundary, pack/runtime, or router legacy-mesh blocks.
- `decision.py` and `_legacy.py` may survive only as shadow/test router residue, not as live app-runtime imports.
- Removed runtime wrapper lanes may survive only as test-only shadow support files.
- Do not sync `STATE.md`, active canon/program, packet, or reports before the full block is green.

## Scope
- delete `truffles-api/app/services/reasoning_core.py` from runtime code
- delete `truffles-api/app/webhook.py` from runtime code
- preserve their former shim contracts only through test-only support files
- prove that no repo imports remain for `app.services.reasoning_core` or `app.webhook`
- prove that app runtime still imports `decision.py` only through `_legacy.py`, and `_legacy.py` remains outside app runtime
- freeze the resulting topology under a dedicated deterministic guard
- close the block with one full sync after checks pass

## Out of scope
- deleting `decision.py` or `_legacy.py`
- broader legacy helper deletion (`info.py`, `response.py`, `context_manager.py`, `pending.py`, `policy.py`, `guards.py`, `dedup.py`)
- operational entrypoint dedupe
- whole-system governance closure
- replay or human semantic audit

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-shadow-lane-elimination-a922.md`
- `docs/REPORTS/2026-03-31-consultant-core-shadow-lane-elimination-a922.md`
- `docs/SHADOW_LANE_ELIMINATION_GUARD.yaml`
- `docs/BOUNDARY_DEGRADE_GUARD.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
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
- `scripts/shadow_lane_elimination_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/tests/support_reasoning_core_shadow.py`
- `truffles-api/tests/support_legacy_webhook_shadow.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_outbox_payload_contract.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_shadow_lane_elimination_guard.py`
- `git diff --check`

## Root cause (mandatory)
### Symptom
Even after router legacy-mesh drain, two runtime wrapper lanes still preserved stale authority memory and kept the repo one re-add away from shadow-owner re-entry: `truffles-api/app/services/reasoning_core.py` and `truffles-api/app/webhook.py`.

### Minimal reproduction
1. Inspect the live runtime tree after Legacy Mesh Drain.
2. Observe that router composition no longer needs `app/services/reasoning_core.py` or `app/webhook.py`.
3. Observe that both files still exist in runtime code only as shadow compatibility delegates.
4. Observe that their contracts are needed only by tests, not by live runtime imports.

### Evidence
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_outbox_payload_contract.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/_legacy.py`
- `docs/system_forensics/dead_surface_registry.json`

### Five Whys
1. Why was legacy-mesh drain not enough?
  - Because two runtime wrapper files still existed even though live runtime no longer imported them.
2. Why is that a blocker?
  - Because removed authority is not real if dormant runtime files can silently become active again.
3. Why not delete `decision.py` and `_legacy.py` too?
  - Because router shadow/test residue still depends on them, and that belongs to a later deletion/governance phase.
4. Why keep any contract at all?
  - Because tests still need deterministic coverage of the former wrapper behavior while runtime ownership is removed.
5. Why add a dedicated guard?
  - Because without deterministic proof, wrapper files can silently return or new imports can recreate the same shadow lane.

### Broken invariant
Runtime shadow-wrapper files may not survive in app code once live runtime no longer imports them.

### Shared mechanism
Shadow Lane Elimination.

### Why the surfaced family belongs to that mechanism
This is one authority-topology seam: dormant runtime wrapper files still preserved hidden re-entry lanes even after mounted router legacy drain completed.

### Open-world envelope expected to improve after the fix
- no runtime file exists at `truffles-api/app/services/reasoning_core.py` or `truffles-api/app/webhook.py`
- their contracts survive only in test-only support residues
- app runtime keeps `decision.py` and `_legacy.py` outside the live import graph
- the next admissible runtime block can move to operational entrypoint dedupe without hidden shadow wrappers still present

### Root cause statement
Legacy mesh drain removed live router dependencies, but runtime shadow-wrapper files were still left in app code. That preserved stale alternate lanes in the repo even though only tests still needed those contracts.

### Fix mechanism
- delete the runtime wrapper files
- move their residual contract into test-only support modules
- freeze the removed/runtime-shadow topology with a dedicated guard and registry proof

## Plan
1. Author this TP and keep active docs untouched until full block closeout.
2. Delete `truffles-api/app/services/reasoning_core.py` and `truffles-api/app/webhook.py` from runtime code.
3. Preserve the required deterministic contract only through `truffles-api/tests/support_reasoning_core_shadow.py` and `truffles-api/tests/support_legacy_webhook_shadow.py`.
4. Update targeted tests to consume the test-only support residues instead of runtime wrapper files.
5. Add deterministic proof that no repo imports remain for `app.services.reasoning_core` or `app.webhook`, while `decision.py` remains shadow-only through `_legacy.py` and `_legacy.py` remains outside app runtime.
6. Sync registries, active docs, and packet once after the full block is green.

## DoD
- `truffles-api/app/services/reasoning_core.py` does not exist.
- `truffles-api/app/webhook.py` does not exist.
- test-only support files preserve the removed contracts.
- repo imports for `app.services.reasoning_core` and `app.webhook` are empty.
- app-runtime imports of `decision.py` remain exactly `truffles-api/app/routers/webhook/_legacy.py`.
- app runtime has no `_legacy.py` importers.
- `docs/SHADOW_LANE_ELIMINATION_GUARD.yaml` and `scripts/shadow_lane_elimination_guard.py` freeze that topology.
- machine-readable registries represent removed runtime wrapper files as removed and support residues as shadow-only test support.
- active docs and packet move from `Legacy Mesh Drain` to `Shadow Lane Elimination` only after checks pass.

## Work mode
- implementation

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
- `python3 scripts/pack_runtime_separation_guard.py`
- `python3 scripts/legacy_mesh_drain_guard.py`
- `python3 scripts/shadow_lane_elimination_guard.py`
- `python3 scripts/arch_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_outbox_payload_contract.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_message_endpoint.py -k "legacy_webhook_compat_routes_through_public_entrypoint_contract"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "legacy_root_webhook_removed_from_app_runtime or reasoning_core_has_no_app_runtime_importers or reasoning_core_shadow_support_has_no_direct_decision_router_import or reasoning_core_routing_reads_compiled_policy_snapshot"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_shadow_lane_elimination_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-31-consultant-core-shadow-lane-elimination-a922.md`
- `docs/SHADOW_LANE_ELIMINATION_GUARD.yaml`
- `scripts/shadow_lane_elimination_guard.py`
- `truffles-api/tests/support_reasoning_core_shadow.py`
- `truffles-api/tests/support_legacy_webhook_shadow.py`
- updated architecture and targeted runtime tests
- updated `docs/system_forensics/authority_registry.json`
- updated `docs/system_forensics/dead_surface_registry.json`
- updated `docs/system_forensics/legacy_caller_surface.json`
- updated `docs/system_forensics/governance_delta.json`

## Rollback
- restore the removed runtime wrapper files from git history
- repoint tests back to the runtime files if the support residues prove insufficient
- restore `Consultant Core Legacy Mesh Drain` as the active block if the shadow-lane proof is rejected

## No-go
- do not delete `decision.py` or `_legacy.py` in this block
- do not widen this block into operational entrypoint dedupe or replay
- do not reintroduce runtime wrapper files as a shortcut for tests
- do not sync `STATE.md` / active docs / packet before the full block is green

## Risks / blockers
- tests still rely on the removed wrapper contracts, so support residues must stay accurate enough for deterministic coverage
- router shadow surfaces still remain in the repo after this block
- broader legacy deletion and whole-system governance closure remain open after this block

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `decision.py` remains a shadow-only router residue
- `_legacy.py` remains a shadow-only router residue
- broader fact families remain open
- operational entrypoint dedupe remains open
- whole-system governance closure remains open
- replay and human semantic audit remain forbidden

### Why not in this block
This block removes only the dormant runtime wrapper lanes. Router shadow surfaces and operational caller duplication belong to later blocks.

### Risk if deferred
Without this block, dormant runtime wrapper files can silently re-enter behavior ownership even though live runtime no longer needs them.

### Linked follow-up Task Package(s)
- future operational entrypoint dedupe TP
- future whole-system governance closure TP

### Expiry / trigger to stop deferral
- stop deferral immediately if repo imports reappear for `app.services.reasoning_core` or `app.webhook`, or if `_legacy.py` gains an app-runtime importer.

## Next-block contract (mandatory)
### Next block objective
Unify duplicated operational entrypoints once shadow wrapper lanes are removed from runtime.

### First deterministic check command
`python3 scripts/shadow_lane_elimination_guard.py`

### Blocked-by conditions
- repo imports still exist for `app.services.reasoning_core` or `app.webhook`
- `decision.py` app-runtime importers are wider than `_legacy.py` only
- `_legacy.py` still has app-runtime importers
- registry proof is not aligned to the removed runtime wrapper topology

### Owner role for closure
Brain / Top Architect
