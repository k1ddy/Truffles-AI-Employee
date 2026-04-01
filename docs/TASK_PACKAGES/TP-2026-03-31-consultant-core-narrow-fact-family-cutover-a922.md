# TP-2026-03-31-consultant-core-narrow-fact-family-cutover-a922

## Название / цель
Перевести whole-system narrow fact family `location / hours / parking` на explicit fact contract, уже материализованный в `FactManifestV1 / FactRequestV1 / FactPlanV1 / FactResultV1 / FactContractV1`, и закрыть family cutover без opportunistic widening, direct-truth bypass, или pack-runtime sibling co-ownership.

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
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-fact-contract-schema-a922.md`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- `docs/system_forensics/failure_family_registry.json`
- `docs/system_forensics/SYSTEM_VERDICT.md`

## One web search (mandatory before implementation)
- Query: `site:docs.pydantic.dev pydantic v2 model_validator nested list exact set validation`
- Date/time (local): `2026-03-31 09:54 +0500`
- Sources opened:
  - `https://docs.pydantic.dev/latest/concepts/performance/`
- Source quality:
  - official Pydantic documentation
- Ready solutions found:
  - keep validation in the typed contract layer rather than helper branches;
  - prefer explicit list/tuple contract surfaces over looser generic sequence shapes on the hot path;
  - avoid adding extra wrap-validator lanes when the model contract already expresses the invariant.
- Decision (`reuse/integrate/build`): `reuse + integrate`
  - reuse the explicit fact contract from the previous block;
  - integrate the first family cutover into the governed `catalog.location` path;
  - reject new wrapper validators or legacy helper branches as the cutover mechanism.
- Rejected options:
  - patching `webhook/info.py` as the primary fix;
  - restoring direct-truth or pack-runtime sibling fallback for the family;
  - solving the family with scenario-local wording branches.

## Invariant
- Do not widen beyond manifest-authorized emitted sets.
- Do not reopen direct-truth or pack-runtime sibling bypass.
- Do not claim continuity normalization, boundary constriction, or replay closure in this block.
- Do not add new semantic, continuity, fact, or boundary authority to frozen legacy modules.
- Do not update active docs/state until the full family block is green.

## Scope
- route the narrow family through the explicit fact contract only
- prove exact requested/allowed/emitted behavior for `location / hours / parking`
- drain the remaining family-local legacy composition pressure on the governed hot path
- promote the family cutover to the active whole-system block

## Out of scope
- broader continuity normalization
- boundary constriction
- pack/runtime separation completion
- whole legacy mesh drain
- replay or human semantic audit

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-narrow-fact-family-cutover-a922.md`
- `docs/REPORTS/2026-03-31-consultant-core-narrow-fact-family-cutover-a922.md`
- `docs/FACT_FAMILY_CUTOVER_GUARD.yaml`
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
- `scripts/arch_guard.py`
- `scripts/fact_family_cutover_guard.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/services/pack_runtime_default.py`
- `truffles-api/app/services/demo_salon_knowledge.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_fact_family_cutover_guard.py`

## Root cause (mandatory)
### Symptom
The explicit fact contract exists, but the first visible family `location / hours / parking` still risks reopening through stale binding projections, direct-truth fallback, pack-runtime sibling replies, or raw-text re-inference inside `catalog.location`.

### Minimal reproduction
1. Construct an owner-authored `hours` fact turn whose stale binding still points to `catalog.service_query`.
2. Confirm the governed hot path reroutes it to `catalog.location`.
3. Construct a `parking` fact turn where `catalog.location` does not resolve.
4. Confirm the runtime returns explicit family-unresolved output instead of direct-truth or pack-runtime sibling content.
5. Invoke `catalog.location` with `allowed_fact_refs=["location", "hours"]` and verify it does not re-infer `parking` from raw text.

### Evidence
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- `docs/system_forensics/failure_family_registry.json`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `scripts/fact_family_cutover_guard.py`

### Five Whys
1. Why is the first visible family still risky after the schema block? Because routing and emission can still drift through stale binding and sibling fallback paths.
2. Why is stale binding a problem? Because it can point outside the governed family resolver even when the owner/binding contract already narrowed the family.
3. Why is direct-truth or pack-runtime fallback a problem? Because it creates a second fact authority for the same family.
4. Why is raw-text re-inference in `catalog.location` a problem? Because it widens emitted scope outside the binding-authorized set.
5. Why must this be fixed now? Because the first family is the proof slice that the explicit fact contract actually governs runtime behavior rather than sitting beside legacy helper logic.

### Broken invariant
For the first governed family, requested refs must survive into the runtime, binding-authorized emitted sets must constrain the resolver exactly, and no sibling helper path may introduce extra facts or alternate ownership.

### Shared mechanism
Narrow fact-family cutover for `location / hours / parking`.

### Why the surfaced family belongs to that mechanism
This is the first family where the visible residue and the missing runtime cutover coincide. Fixing it proves the shared fact-plane mechanism, not a scenario patch.

### Open-world envelope expected to improve after the fix
- `hours`, `location`, and `parking` turns stay inside explicit requested/allowed/emitted scope on the governed hot path;
- stale family binding no longer escapes to another resolver;
- sibling fact authorities stop co-owning the family.

### Root cause statement
The explicit fact contract was materialized, but the first family still depended on residual downstream routing and widening behavior that could bypass or overrule the governed contract unless the family was explicitly cut over to one resolver path with exact scope enforcement.

### Fix mechanism
- reroute the family to `catalog.location` on the governed hot path;
- block direct-truth and pack-runtime sibling bypass for the family;
- enforce `allowed_fact_refs` inside `catalog.location`;
- promote the family guard and whole-system registry/report/state sync only after the full block is green.

## Plan
1. Validate the governed family reroute and bypass removal on the existing runtime slice.
2. Confirm `catalog.location` obeys binding-authorized `allowed_fact_refs` for the targeted family.
3. Promote the family cutover to the active whole-system block in lock/source/registries/canon/program/state.
4. Close the block only after packet, guards, runtime tests, architecture tests, and diff checks are green.

## DoD
- `parking`, `hours`, and `location` turns emit only manifest-authorized sets.
- stale binding for the targeted family reroutes to `catalog.location` on the governed hot path.
- direct-truth and pack-runtime sibling bypass do not co-own the family.
- `catalog.location` does not re-infer `parking` when `allowed_fact_refs` exclude it.
- the authority registry truth for `fact_scope` names `continuity_state_normalization` as the next phase.
- active docs and packet move from `Fact Contract Schema` to `Narrow Fact-Family Cutover` only after checks pass.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/authority_freeze_guard.py`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/fact_family_cutover_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "fact_manifest or fact_contract or fact_plan or fact_request or fact_result or emitted_scope or allowed_fact_refs or info_sections"`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "location_base_bundle or stale_service_query_binding or direct_truth_and_pack_bypass or reinfer_parking_outside_allowed_scope or fact_family"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_fact_family_cutover_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-31-consultant-core-narrow-fact-family-cutover-a922.md`
- `docs/FACT_FAMILY_CUTOVER_GUARD.yaml`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/tool_registry_service.py`
- updated `docs/system_forensics/authority_registry.json`
- generated packet and passing checks

## Rollback
- revert this block’s touch-list and restore `Fact Contract Schema` as the active block.

## No-go
- do not reopen direct-truth or pack-runtime sibling authority for the family
- do not solve the family via local phrasing or regex branches
- do not reopen replay
- do not sync active docs or `STATE.md` before the full block is green

## Risks / blockers
- broader fact families remain mixed and are not closed by this block
- broader continuity carriers can still reopen adjacent behavior until the next block closes

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- continuity/state normalization remains open
- boundary constriction remains open
- broader fact families remain open beyond `location / hours / parking`
- broader legacy drain remains open
- legacy `webhook/info.py` and direct truth/render helpers remain frozen residual surfaces outside the governed hot path

### Why not in this block
This TP is only the first whole-system fact-family cutover.

### Risk if deferred
Without the first governed family cutover, the explicit fact contract remains unproven on the main visible residue slice.

### Linked follow-up Task Package(s)
- future continuity normalization TP

### Expiry / trigger to stop deferral
- stop deferral immediately after this block closes; the next admissible move is continuity/state normalization.

## Next-block contract (mandatory)
### Next block objective
Normalize continuity/state so the first fact-family slice no longer depends on competing carriers.

### First deterministic check command
`python3 scripts/touched_slice_continuity_guard.py`

### Blocked-by conditions
- Narrow Fact-Family Cutover not accepted
- family still has unresolved sibling or bypass surfaces

### Owner role for closure
- Top Architect / Brain
