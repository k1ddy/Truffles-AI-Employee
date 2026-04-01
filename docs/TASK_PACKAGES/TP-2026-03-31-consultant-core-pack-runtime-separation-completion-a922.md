# TP-2026-03-31-consultant-core-pack-runtime-separation-completion-a922

## Название / цель
Сузить active pack/runtime seam так, чтобы hot-path fact/service retrieval and rendering больше не зависели от slug-selected adapter behavior или adapter-private helper calls. Active runtime path должен остаться pack-agnostic at the behavior layer while legacy/demo adapters survive only as frozen residual surfaces for later legacy drain.

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
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-boundary-constriction-a922.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

## One web search (mandatory before implementation)
- Query: `site:docs.python.org importlib import_module import by name`
- Date/time (local): `2026-03-31 21:11 +0500`
- Sources opened:
  - `https://docs.python.org/uk/3.10/faq/programming.html`
- Source quality:
  - official Python documentation / primary source
- Ready solutions found:
  - import-by-name seams should stay behind one explicit loader boundary instead of leaking through multiple call sites;
  - module dispatch can be preserved for compatibility, but active runtime callers should depend on a narrow public facade, not on dynamic module internals;
  - separation work should reduce direct module knowledge in hot-path callers before any later deletion.
- Decision (`reuse/integrate/build`): `reuse + integrate`
  - reuse the existing neutral adapter, pack query engine, and truth facade pieces;
  - integrate them into one public pack-runtime surface for the active hot path;
  - build only the missing public helper seam, guard, and proofs.
- Rejected options:
  - deleting demo/legacy adapters in this block;
  - keeping active hot-path adapter-private calls and only renaming them;
  - broad legacy drain before the active runtime seam is neutralized.

## Invariant
- Do not reopen boundary constriction.
- Active runtime callers may consume only public pack-runtime helpers, not `get_pack_adapter(...)` or adapter-private helper names.
- Pack truth may stay pack-specific, but active runtime behavior must remain data-driven and pack-agnostic.
- Do not widen this block into legacy deletion or replay.
- Do not sync active canon/state/packet until the full block is green.

## Scope
- build a public pack-runtime helper surface for active fact/service flows
- remove active hot-path adapter-private calls from `tool_registry_service.py`
- reduce `turn_executor.py` active fact fallback dependence on slug-selected adapter behavior
- freeze the new pack/runtime hotspot set under a dedicated guard
- close the block with one whole-system sync after checks pass

## Out of scope
- legacy mesh deletion
- broader fact-family migration beyond the active shared hot path
- replay or human semantic audit
- operational entrypoint dedupe
- quality-lane evaluator work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-pack-runtime-separation-completion-a922.md`
- `docs/REPORTS/2026-03-31-consultant-core-pack-runtime-separation-completion-a922.md`
- `docs/PACK_RUNTIME_SEPARATION_GUARD.yaml`
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
- `scripts/pack_runtime_separation_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/tests/test_pack_runtime_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_booking_appointments.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_pack_runtime_separation_guard.py`
- `git diff --check`

## Root cause (mandatory)
### Symptom
The typed runtime spine is already owner-first and boundary-constricted, but active fact/service execution still depends on slug-selected adapter behavior and direct adapter-private helper calls.

### Minimal reproduction
1. Inspect `turn_executor.py` and `tool_registry_service.py` on the active fact path.
2. Observe that `turn_executor.py` still reaches pack behavior through `pack_runtime_service.get_pack_decision(...)`, which currently delegates to default adapter runtime behavior.
3. Observe that `tool_registry_service.py` imports `get_pack_adapter(...)` and calls adapter-private helpers such as `_format_service_duration_reply`, `_find_best_price_item`, `_format_service_reply`, `_format_service_presence_reply_for_name`, `_format_price_reply`, and `_format_service_not_found_reply`.
4. Observe that those helpers resolve to demo-specific pack code through slug-selected module dispatch.

### Evidence
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/pack_runtime_default.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/core/turn_executor.py`

### Five Whys
1. Why is pack/runtime separation still open after the fact contract and boundary work?
  - Because active runtime callers still depend on adapter-selected behavior, not only on truth/config data.
2. Why is that a blocker?
  - Because the runtime hot path still has a second behavior authority beyond the public typed runtime seam.
3. Why is `tool_registry_service.py` especially problematic?
  - Because it reaches directly into adapter-private helper names and therefore inherits whatever the selected pack module decides.
4. Why is `turn_executor.py` still part of the problem?
  - Because its pack fallback still flows through adapter-selected `get_pack_decision(...)` behavior.
5. Why must this close before legacy drain?
  - Because legacy deletion is unsafe until the active runtime path is already neutralized and can survive without adapter-private behavior ownership.

### Broken invariant
Active runtime behavior must not depend on slug-selected adapter-private functions.

### Shared mechanism
Pack/runtime separation completion.

### Why the surfaced family belongs to that mechanism
This is not a scenario patch. It is one shared authority seam: runtime fact/service behavior still leaks through adapter dispatch and demo-pack behavior code instead of staying behind one public pack-runtime facade.

### Open-world envelope expected to improve after the fix
- active fact/service execution no longer depends on adapter-private helpers
- `tool_registry_service.py` becomes a consumer of public runtime pack helpers only
- `turn_executor.py` pack fallback becomes data-driven at the active hot path
- legacy/demo adapters can remain frozen residual surfaces without co-owning active behavior

### Root cause statement
The runtime already has a pack facade, but active callers still reach behavior through default adapter dispatch and adapter-private helpers. That leaves the pack/runtime seam only partially abstracted and keeps demo-pack code in control of active runtime behavior.

### Fix mechanism
- materialize missing public pack-runtime helpers in `pack_runtime_service.py`
- route active tool and executor paths through those helpers instead of adapter-private functions
- freeze the narrowed hotspot/callsite set under a dedicated guard and prove it with runtime + architecture tests

## Plan
1. Author this TP and keep active docs untouched until full block closeout.
2. Materialize public pack-runtime helper APIs in `pack_runtime_service.py` for active service duration, presence, pricing, not-found, and pack-fallback decision flows.
3. Remove active hot-path `get_pack_adapter(...)` / `_call_pack_adapter(...)` usage from `tool_registry_service.py`.
4. Narrow `turn_executor.py` pack fallback to the public data-driven pack-runtime seam.
5. Add guard/test proof that active pack/runtime callers no longer rely on adapter-private helpers.
6. Close the block only after guard chain, runtime tests, architecture tests, packet, and diff checks are green.

## DoD
- `tool_registry_service.py` no longer imports `get_pack_adapter(...)` or calls adapter-private helper names on the active hot path.
- `pack_runtime_service.py` exposes public runtime helpers for the active fact/service behaviors previously obtained via adapter-private calls.
- `turn_executor.py` active pack fallback no longer depends on adapter-selected private behavior.
- `docs/PACK_RUNTIME_SEPARATION_GUARD.yaml` and `scripts/pack_runtime_separation_guard.py` freeze the active hotspot/callsite set.
- deterministic runtime tests and architecture tests prove the active path is public-facade-only.
- active docs and packet move from `Boundary Constriction` to `Pack / Runtime Separation Completion` only after checks pass.

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
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_pack_runtime_service.py`
- `pytest -q truffles-api/tests/test_booking_appointments.py -k "service_query_pricing_uses_price_item_fallback or service_query_duration_prefers_message_service_over_stale_slot"`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "direct_truth_and_pack_bypass or pack_runtime or service_query or fact_family"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_pack_runtime_separation_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-31-consultant-core-pack-runtime-separation-completion-a922.md`
- `docs/PACK_RUNTIME_SEPARATION_GUARD.yaml`
- `truffles-api/app/services/pack_runtime_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/core/turn_executor.py`
- updated runtime and architecture tests
- updated `docs/system_forensics/authority_registry.json`
- updated `docs/system_forensics/governance_delta.json`

## Rollback
- restore adapter-private pack helper usage on the active path
- restore prior pack-runtime service imports/exports if the public seam proves insufficient
- restore `Boundary Constriction` as the active block if this block must be abandoned

## No-go
- do not solve this block with service-specific or phrase-specific hardcodes
- do not delete demo/legacy adapters in this block
- do not widen this block into legacy drain, shadow deletion, or replay
- do not sync `STATE.md` / active docs / packet before the full block is green

## Risks / blockers
- older tests may encode direct adapter behavior assumptions and will need to be rewritten to the public-facade law
- public helper extraction can expose gaps in generic truth shape across packs
- legacy modules will still import old pack helpers after this block; that residue must stay fenced and honest

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- legacy mesh drain remains open
- shadow lane elimination remains open
- operational entrypoint dedupe remains open
- replay and human semantic audit remain closed

### Why not in this block
This block constricts only the active pack/runtime seam after fact contract, continuity normalization, post-owner semantic constriction, and boundary constriction are already in force.

### Risk if deferred
Without this block, legacy/demo pack behavior still co-owns active runtime behavior, so later legacy drain would either be unsafe or dishonest.

### Linked follow-up Task Package(s)
- future legacy mesh drain TP
- future shadow lane elimination TP
- future whole-system governance closure TP

### Expiry / trigger to stop deferral
- stop deferral immediately if any new active runtime caller imports `get_pack_adapter(...)` or adds new adapter-private helper calls.

## Next-block contract (mandatory)
### Next block objective
Drain remaining live legacy compatibility surfaces now that the active runtime path no longer depends on adapter-private pack behavior.

### First deterministic check command
`python3 scripts/pack_runtime_separation_guard.py`

### Blocked-by conditions
- active tool path still imports `get_pack_adapter(...)`
- active executor path still relies on adapter-private pack behavior
- new public pack-runtime helper seam not yet covered by deterministic tests

### Owner role for closure
- Top Architect / Brain
