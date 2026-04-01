# TP-2026-03-30-consultant-core-fact-contract-location-hours-parking-first-slice-a922

## Название / цель
Перевести первый canary family `location / hours / parking` на explicit fact-plane path поверх уже материализованных `FactRequestV1 / FactPlanV1 / FactResultV1`. Блок должен доказать, что на governed hot path этот family больше не уходит в direct-truth или pack-runtime sibling bypass и исполняется через binding-authorized `catalog.location` contract.

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
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-fact-plane-materialization-a922.md`
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- `docs/system_forensics/END_TO_END_TURN_WALKTHROUGH.md`
- `docs/REPORTS/2026-03-30-consultant-core-r35f-human-semantic-audit-a922.md`

## One web search (mandatory before implementation)
- Query: `site:json-schema.org object schema required additionalProperties emitted scope contract design`
- Date/time (local): `2026-03-30 17:32:25 +0500`
- Sources opened:
  - `https://json-schema.org/understanding-json-schema/reference/object`
- Source quality:
  - official JSON Schema documentation / primary reference
- Ready solutions found:
  - strict contracts should enumerate allowed object properties explicitly;
  - extra object properties stay open by default and must be closed deliberately;
  - contract closure is safer when the runtime path reuses one explicit schema-backed authority chain instead of allowing local ad hoc widening.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the already-materialized `FactRequestV1 / FactPlanV1 / FactResultV1` chain;
  - integrate the first family onto that chain by reusing `catalog.location` as the explicit runtime resolver;
  - build only the family cutover guard/proof layer plus the minimum runtime narrowing needed to remove sibling bypass.
- Rejected options:
  - widen the slice into generic fact migration;
  - edit frozen legacy router files;
  - keep direct-truth or pack-runtime fallback alive for the targeted family on the governed hot path.

## Invariant
- Root-first prerequisites remain accepted and are not reopened here.
- No frozen legacy authority surface receives new semantic/fact/continuity logic.
- The targeted family must not widen emitted scope beyond binding authority.
- The block closes the full governed hot-path family envelope, not one scenario.

## Scope
- `location / hours / parking` only.
- Live `turn_executor.py` fact routing for the targeted family.
- `catalog.location` emitted-scope behavior under explicit `allowed_fact_refs`.
- Deterministic family-cutover guard / tests / report / canon sync.

## Out of scope
- other fact families
- touched-slice continuity normalization
- legacy deletion
- broad pack/runtime separation beyond the targeted family
- practical replay / human semantic closeout for overall program completion

## Touch-list
- `docs/FACT_FAMILY_CUTOVER_GUARD.yaml`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `scripts/fact_plane_guard.py`
- `scripts/fact_family_cutover_guard.py`
- `scripts/recovery_execution_guard.py`
- `scripts/continuity_writer_guard.py`
- `scripts/legacy_mesh_caller_guard.py`
- `scripts/semantic_bridge_growth_guard.py`
- `scripts/boundary_degrade_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/app/core/__init__.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_fact_plane_guard.py`
- `truffles-api/tests/architecture/test_fact_family_cutover_guard.py`
- `docs/REPORTS/2026-03-30-consultant-core-fact-contract-location-hours-parking-first-slice-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-fact-contract-location-hours-parking-first-slice-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Activate block 8 in canon/source-of-truth and define the machine-readable family-cutover guard.
2. Narrow `turn_executor.py` so the targeted family reroutes to `catalog.location` on the fact plane even when stale binding still points to generic `info` or `catalog.service_query`.
3. Remove targeted-family sibling bypass on the governed hot path: no direct-truth fallback and no pack-runtime fallback after the family is cut over.
4. Narrow `tool_registry_service.py` so `catalog.location` respects binding-authorized `allowed_fact_refs` and cannot re-infer `parking` from raw message text when parking is out of scope.
5. Prove the family cutover deterministically, update the authority registry, sync packet/state/structure/report, and leave the next admissible block explicit.

## Root cause (mandatory)
### Symptom
`location / hours / parking` turns still had sibling resolution paths after fact-plane materialization: stale binding could point at non-family tool actions, direct-truth fallback could answer the family outside `catalog.location`, and `catalog.location` could re-infer `parking` from raw text even when binding excluded it.

### Minimal reproduction
- Build a fact decision for `hours` with stale binding `catalog.service_query`; executor can still enter the family with a non-family binding artifact.
- Build a fact decision for `parking` with binding `info`; if `catalog.location` does not resolve, executor can still fall through to direct truth or pack runtime unless explicitly blocked.
- Call `catalog.location` with `allowed_fact_refs=["location", "hours"]` and parking-shaped `message_text`; parking can reappear unless the tool branch honors the binding scope over raw text.

### Evidence
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/tool_registry_service.py`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`

### Five Whys
1. Why was the family not closed after block 7? Because block 7 materialized the fact plane, but it did not yet force one proving family onto that plane end-to-end.
2. Why could the family still bypass the new plane? Because executor still tolerated sibling direct-truth / pack-runtime fallbacks after the explicit plan existed.
3. Why could `catalog.location` still overreach? Because raw message text could still re-enable `parking` even when binding-authorized scope excluded it.
4. Why is that a root-cause expression rather than a local bug? Because it is the same authority problem as the broader fact plane: emitted scope and resolver selection were still partially controlled by helper-local heuristics.
5. Why fix it as a bounded family cutover? Because the root-first prerequisites are now closed enough to prove the contract on one family without widening into broad runtime cleanup.

### Broken invariant
Emitted fact scope for the targeted family must be a refinement of owner-requested scope and binding-authorized scope, executed through one explicit resolver path.

### Shared mechanism
Family cutover on the explicit fact plane: requested refs -> allowed refs -> emitted refs -> no sibling fallback authority.

### Why this surfaced family belongs to that mechanism
`location / hours / parking` is the first family where the new fact plane already exposes a natural bundle policy (`location_base_bundle`) and one bounded resolver (`catalog.location`), so it is the correct proving slice for emitted-scope authority.

### Open-world envelope expected to improve after the fix
- stale hours/location bindings on the governed hot path
- parking turns under mixed booking/info context
- catalog.location replies where raw text mentions parking but binding scope excludes it

### Root cause statement
The first fact family stayed unstable because the fact plane existed structurally but the governed hot path still permitted sibling execution authority and raw-text widening after the binding plan had already fixed the allowed emitted scope.

### Fix mechanism
Force the family onto `catalog.location`, block direct-truth / pack-runtime sibling bypass for that family on the governed hot path, and make `catalog.location` subordinate to `allowed_fact_refs` rather than raw parking text.

## DoD
- block 8 is the active block in canon/source-of-truth/packet
- the targeted family reroutes to `catalog.location` on the fact-plane hot path even when stale binding still points at `info` or `catalog.service_query`
- direct-truth and pack-runtime sibling bypass are absent for the targeted family on the governed hot path
- `catalog.location` does not re-infer `parking` when `allowed_fact_refs` exclude it
- deterministic guard/test evidence is green and authority registry/report/state/structure are synced

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/fact_family_cutover_guard.py`
- `python3 scripts/boundary_degrade_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_mesh_caller_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "location_base_bundle or stale_service_query_binding or direct_truth_and_pack_bypass or reinfer_parking_outside_allowed_scope or fact_family"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_single_continuity_writer.py`
- `pytest -q truffles-api/tests/architecture/test_truth_carrier_freeze.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_mesh_caller_proof.py`
- `pytest -q truffles-api/tests/architecture/test_semantic_bridge_growth_guard.py`
- `pytest -q truffles-api/tests/architecture/test_boundary_degrade_guard.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "continuity_writer"`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "legacy_root_webhook_is_thin_delegate_only or booking_prompt_owner_removed_from_app_core or reasoning_core_has_no_app_runtime_importers or webhook_legacy_adapter_uses_explicit_export_allowlist"`
- `pytest -q truffles-api/tests/architecture/test_fact_plane_guard.py`
- `pytest -q truffles-api/tests/architecture/test_fact_family_cutover_guard.py`
- `git diff --check`

## Evidence
- `docs/FACT_FAMILY_CUTOVER_GUARD.yaml`
- `scripts/fact_family_cutover_guard.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_fact_family_cutover_guard.py`
- `docs/system_forensics/authority_registry.json`
- `docs/REPORTS/2026-03-30-consultant-core-fact-contract-location-hours-parking-first-slice-a922.md`

## Rollback
- revert the targeted family reroute in `turn_executor.py`
- drop the family-cutover guard and restore block 7 as the active source-of-truth block if the family cutover has to be abandoned

## No-go
- do not widen into generic fact cleanup
- do not edit frozen legacy router surfaces
- do not claim full fact-plane closure for all families
- do not claim practical or human-semantic closure from deterministic proof alone

## Risks / blockers
- runtime still contains broader mixed-authority fact behavior outside this family
- targeted family closure at repo-side does not replace the later touched-slice continuity and legacy-drain blocks
- practical replay / human semantic audit remain required before any product-quality claim

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- only `location / hours / parking` is cut over; other fact families still rely on mixed behavior
- touched-slice continuity for this family is not normalized yet
- legacy mesh and pack-runtime adapters still exist outside the governed family slice

### Why not in this block
The governing order requires this bounded proving slice before continuity normalization and final legacy drain.

### Risk if deferred
If the next blocks are skipped, the family can still regress via continuity carriers or broader legacy/runtime competition even though the hot-path resolver cutover is in place.

### Linked follow-up Task Package(s)
- `touched_slice_continuity_normalization`
- `legacy_drain_and_proof_closure`

### Expiry / trigger to stop deferral
- stop deferral immediately if the targeted family starts writing pending-question continuity outside canonical state or if any new sibling resolver path reappears for this family

## Next-block contract (mandatory)
### Next block objective
Normalize pending-question and interaction continuity for the touched fact-family slice so the new resolver path does not still depend on compatibility carriers.

### First deterministic check command
`python3 - <<'PY'
from pathlib import Path
assert Path('docs/FACT_FAMILY_CUTOVER_GUARD.yaml').exists()
assert Path('scripts/fact_family_cutover_guard.py').exists()
print('first_fact_family_cutover_ready_for_continuity_normalization')
PY`

### Blocked-by conditions
- targeted family still falls through to direct-truth or pack-runtime sibling paths
- `catalog.location` can still widen `parking` from raw text when binding excludes it
- runtime metadata no longer carries explicit `fact_contract` for the targeted family

### Owner role for closure
Brain / Top Architect
