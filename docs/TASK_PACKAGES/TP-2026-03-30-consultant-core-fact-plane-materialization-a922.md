# TP-2026-03-30-consultant-core-fact-plane-materialization-a922

## Название / цель
Материализовать first-class fact plane на live consultant-core hot path so owner-requested fact scope, binding-allowed emitted scope, and resolver or renderer emitted scope become explicit typed contracts instead of ad hoc `info_sections` widening spread across executor, tool registry, and pack fallbacks. Этот блок не переводит `location / hours / parking` как proving slice; он вводит контрактную плоскость и ограничивает текущий emitted scope на уровне root-first mechanism.

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
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-boundary-degrade-constriction-a922.md`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com query model source of truth contract derived data architecture`
- Date/time (local, recorded): `2026-03-30 19:15:00 +0500`
- Sources opened:
  - site-filtered `martinfowler.com` result set for query model / source of truth / contract / derived data architecture
- Source quality:
  - high-signal architecture source class / Martin Fowler
- Ready solutions found:
  - derived data must be explicit and downstream consumers must not become silent co-owners of truth;
  - a query/result model is useful when multiple downstream surfaces would otherwise recompute output shape independently;
  - the correct move here is to materialize a contract chain around the existing hot path, not to jump directly into a family-specific rewrite.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the existing semantic-owner and binding-plan seams plus the existing capability fact-scope snapshot vocabulary;
  - integrate those seams into explicit `FactRequestV1 / FactPlanV1 / FactResultV1` contracts;
  - build one deterministic fact-plane guard because no existing guard freezes emitted-scope authorship on the live path.
- Rejected options:
  - jumping straight to `location / hours / parking` proving slice before the fact-plane contract exists;
  - broad pack/runtime rewrite before constricting the current emitted-scope seam;
  - leaving `turn_executor.py` and `tool_registry_service.py` free to append fact scope opportunistically because `info_sections` “already works most of the time`.

## Invariant
- Do not introduce a second semantic owner.
- Owner writes requested fact scope only.
- Binding writes allowed emitted fact scope only.
- Resolver or renderer writes emitted fact scope only.
- No downstream helper may widen emitted fact scope opportunistically.
- Do not add new semantic/fact/continuity logic to frozen legacy files.
- Do not widen this block into proving-slice family cutover, continuity normalization, or legacy deletion.

## Scope
- Add explicit runtime contracts for `FactRequestV1`, `FactPlanV1`, and `FactResultV1`.
- Carry that fact contract chain through the live `turn_executor` fact path.
- Constrict `tool_registry_service.py` so fact-emitting branches honor binding-authorized scope instead of message-driven widening.
- Stop `turn_executor.py` from appending or widening emitted fact scope opportunistically after resolver output.
- Add one machine-readable fact-plane guard that freezes the new contract seam and blocks new unplanned emitted-scope writers.
- Sync source-of-truth / authority registry / packet / report / state to the active fact-plane block.

## Out of scope
- `location / hours / parking` proving slice cutover.
- Broad pack adapter rewrite or pack-neutral redesign.
- Legacy webhook info path deletion.
- Full practical replay / human semantic closure.
- Continuity normalization beyond fact-contract observability fields.

## Touch-list
- `contracts/runtime/fact_request.v1.jsonschema`
- `contracts/runtime/fact_plan.v1.jsonschema`
- `contracts/runtime/fact_result.v1.jsonschema`
- `docs/FACT_PLANE_GUARD.yaml`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `scripts/fact_plane_guard.py`
- `scripts/recovery_execution_guard.py`
- `scripts/continuity_writer_guard.py`
- `scripts/legacy_mesh_caller_guard.py`
- `scripts/semantic_bridge_growth_guard.py`
- `scripts/boundary_degrade_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/app/core/fact_plane.py`
- `truffles-api/app/core/__init__.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_fact_plane_guard.py`
- `docs/REPORTS/2026-03-30-consultant-core-fact-plane-materialization-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-boundary-degrade-constriction-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-fact-plane-materialization-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Add explicit fact-plane contract types and schemas for request, plan, and result.
2. Route the live `TurnExecutor._execute_fact(...)` path through that contract chain.
3. Constrict `tool_registry_service.execute_tool_action(...)` to accept binding-authorized fact scope and block out-of-plan widening.
4. Add a deterministic fact-plane guard that freezes the contract seam and requires `allowed_fact_refs` on live tool-registry fact calls.
5. Add runtime and architecture tests for request → plan → result contract validation, emitted-scope constriction, and guard enforcement.
6. Sync authority registry, source-of-truth, packet, report, state, and structure to the new active block.

## Root cause (mandatory)
### Symptom
The repo has semantic-owner and binding-plan seams, but the fact path still spreads scope authorship across `turn_executor.py`, `tool_registry_service.py`, pack fallbacks, and legacy info helpers. `info_sections` is still a compatibility carrier, not a first-class contract.

### Minimal reproduction
1. Inspect `truffles-api/app/core/turn_executor.py` and observe that requested refs are rebuilt ad hoc from `pack_refs`, `fact_refs`, `capability_refs`, and intent-derived helpers.
2. Observe that `turn_executor.py` still appends `pricing`, `duration`, and `services_overview` to emitted `info_sections` after resolver output.
3. Inspect `truffles-api/app/services/tool_registry_service.py` and observe that info-related tool replies still widen fact output according to message signals and local helper logic instead of one binding-authored allowed scope.
4. Observe there is no explicit typed `FactRequestV1 / FactPlanV1 / FactResultV1` runtime object chain and no guard that forces emitted scope to stay inside a declared plan.

### Evidence
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/tool_registry_service.py`
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- deterministic fact-scope helpers already present in `truffles-api/app/services/capability_manifest_service.py` and `truffles-api/app/services/capability_registry_snapshot_service.py`

### Five Whys
1. Why is the fact plane still missing after semantic/binding/boundary blocks?
   - Because fact scope is still carried as compatibility metadata and helper behavior, not as first-class request/plan/result contracts.
2. Why is that a problem on the live hot path?
   - Because owner request, binding authorization, and emitted fact scope can drift apart silently while still producing a plausible user-visible reply.
3. Why do `turn_executor.py` and `tool_registry_service.py` matter here?
   - Because they are the live points where requested scope is reconstructed, hints are widened, and emitted scope is shaped before the response leaves the governed hot path.
4. Why can’t we go straight to the `location / hours / parking` slice?
   - Because the proving slice would sit on top of the same unmaterialized fact-plane contract and would not close the shared mechanism.
5. Why is a deterministic guard required now?
   - Because without one, new emitted-scope writers or new out-of-plan tool-registry fact calls can silently regrow the same mixed-authority mesh.

### Broken invariant
Fact scope must flow through one explicit contract chain: owner-requested scope, binding-authorized emitted scope, and resolver or renderer emitted scope.

### Shared mechanism
First-class fact-plane materialization.

### Why this surfaced family belongs to that mechanism
This is not one fact bug. It is the missing contract plane that lets multiple downstream helpers co-own what facts are allowed to be emitted.

### Open-world envelope expected to improve after the fix
- fact requests become explicit and machine-readable on the hot path;
- binding-authorized emitted scope becomes explicit and reusable across tool, truth, and pack paths;
- out-of-plan emitted scope is blocked deterministically instead of silently reaching the user;
- future fact-family cutovers can happen against an existing contract plane rather than ad hoc helper behavior.

### Root cause statement
The repository already has semantic-owner and binding-plan seams, but the fact plane is still absent because requested fact scope is reconstructed ad hoc, emitted fact scope is widened opportunistically inside executor and tool-registry branches, and no typed runtime contract or guard currently forces emitted scope to remain inside binding authority.

### Fix mechanism
- add explicit `FactRequestV1`, `FactPlanV1`, and `FactResultV1` contracts plus schemas;
- build and carry that chain inside `TurnExecutor._execute_fact(...)`;
- require live tool-registry fact calls to receive `allowed_fact_refs` from the fact plan;
- reject or bypass emitted scope that exceeds the explicit fact plan;
- freeze the seam with a dedicated fact-plane guard and sync governance evidence.

## DoD
- `FactRequestV1`, `FactPlanV1`, and `FactResultV1` exist as explicit runtime contracts with validating schemas.
- `turn_executor.py` uses that chain on the live fact path.
- `tool_registry_service.py` accepts binding-authorized fact scope and does not widen fact replies outside it.
- `turn_executor.py` no longer appends emitted fact scope opportunistically after resolver output.
- `docs/FACT_PLANE_GUARD.yaml` and `scripts/fact_plane_guard.py` freeze the fact-plane seam and fail on unplanned emitted-scope writer growth.
- authority registry / source-of-truth / packet / report / state reflect block 7 as the active governing move.
- deterministic tests prove contract validation, emitted-scope constriction, and guard coverage.

## Checks
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/boundary_degrade_guard.py`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_mesh_caller_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "fact_plan or fact_request or fact_result or emitted_scope or allowed_fact_refs or info_sections"`
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
- `git diff --check`

## Evidence
- this TP
- `contracts/runtime/fact_request.v1.jsonschema`
- `contracts/runtime/fact_plan.v1.jsonschema`
- `contracts/runtime/fact_result.v1.jsonschema`
- `docs/FACT_PLANE_GUARD.yaml`
- `scripts/fact_plane_guard.py`
- updated `docs/system_forensics/authority_registry.json`
- updated source-of-truth / active canon / packet / report / state
- updated deterministic runtime and architecture tests

## Rollback
- revert touched files in the touch-list and restore the previous active block docs only

## No-go
- do not jump to `location / hours / parking` cutover inside this block
- do not add new fact logic to frozen legacy files
- do not keep opportunistic emitted-scope widening in executor or tool registry and still claim fact-plane materialization
- do not weaken existing semantic, continuity, boundary, or legacy guards to make this block pass

## Risks / blockers
- some fact-related tests may currently assume `tool_registry_service.py` can widen reply scope from message text alone
- pack fallback replies may surface mixed scope and will need to be rejected rather than trusted when out of plan
- guard design must be tight enough to catch writer drift without blocking pure observer changes

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- pack adapters still mix selection and rendering behind the new fact contract boundary
- legacy `webhook/info.py` still exists as a frozen compatibility surface outside the governed hot path
- first-family proving slice is still open
- touched-slice continuity normalization is still open

### Why not in this block
This block materializes the shared fact-plane contract and constricts emitted scope on the live hot path. It does not yet migrate one family fully or drain legacy info surfaces.

### Risk if deferred
Without this block, later family cutovers will keep landing on top of mixed emitted-scope authority and will not close the shared mechanism.

### Linked follow-up Task Package(s)
- first fact-family cutover block
- touched-slice continuity normalization block
- legacy drain and proof closure block

### Expiry / trigger to stop deferral
- stop deferral immediately if a new app runtime path emits fact scope without a `FactPlanV1` or if `tool_registry_service.py` grows new out-of-plan fact reply branches

## Next-block contract (mandatory)
### Next block objective
Move the first canary family `location / hours / parking` onto the explicit fact plane with no opportunistic widening or legacy sibling bypass.

### First deterministic check command
`python3 - <<'PY'
from pathlib import Path
assert Path('docs/FACT_PLANE_GUARD.yaml').exists()
assert Path('scripts/fact_plane_guard.py').exists()
print('fact_plane_block_ready')
PY`

### Blocked-by conditions
- `FactRequestV1 / FactPlanV1 / FactResultV1` chain not materialized on the live hot path
- tool-registry fact replies can still emit scope outside binding authority
- executor still appends emitted fact scope opportunistically after resolver output

### Owner role for closure
Brain / Top Architect
