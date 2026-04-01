# TP-2026-03-31-consultant-core-fact-contract-schema-a922

## Название / цель
Материализовать whole-system `Fact Contract Schema` как следующий полный блок после Authority Freeze. Блок должен сделать fact-side contract machine-readable и executable через `FactManifestV1`, `FactRequestV1`, `FactPlanV1`, `FactResultV1`, `FactContractV1`, не расширяясь в narrow family cutover, continuity normalization или replay.

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
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-authority-freeze-a922.md`
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/failure_family_registry.json`

## One web search (mandatory before implementation)
- Query: `site:json-schema.org JSON Schema object additionalProperties contract design`
- Date/time (local): `2026-03-31 16:xx +0500`
- Sources opened:
  - `https://tour.json-schema.org/content/03-Objects/02-Additional-Properties`
- Source quality:
  - official JSON Schema learning/reference source
- Ready solutions found:
  - contract objects must reject undeclared fields to stop silent widening;
  - explicit schema envelopes are the right stop-the-line for downstream helpers that would otherwise drift through extra payload keys.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the existing `FactRequestV1 / FactPlanV1 / FactResultV1` hot-path seam;
  - integrate the missing `FactManifestV1` and top-level `FactContractV1` envelope;
  - build one block-specific guard that proves schema files, exports, meta keys, and authority registry alignment.
- Rejected options:
  - going straight to family cutover without a complete contract envelope;
  - treating legacy `FactContract` in webhook schemas as the governing fact contract;
  - relying on runtime meta dict shape without explicit schema files.

## Invariant
- Do not reopen replay.
- Do not let downstream helpers widen fact scope outside an explicit allowed emitted set.
- Do not treat the narrow `location / hours / parking` cutover as already closed by this block.
- Do not add new semantic, continuity, or boundary authority to frozen legacy modules.
- Do not update `STATE.md`, `docs/ACTIVE_*`, packet, or reports until the full block is complete.

## Scope
- Add `FactManifestV1` and `FactContractV1` to the typed fact-plane contract set.
- Extend `FactRequestV1`, `FactPlanV1`, and `FactResultV1` so the contract records composition mode, allowed emitted sets, renderer/provenance, and exact emitted-set legality.
- Publish runtime JSON schemas for manifest and top-level fact contract.
- Rebase the whole-system authority registry so `fact_scope` truth is honest at the schema block: contract materialized, family cutover still next.
- Add a block-specific `fact_contract_schema_guard` and tests.

## Out of scope
- `location / hours / parking` family cutover closeout.
- continuity/state normalization.
- boundary constriction.
- pack/runtime separation completion.
- replay or human semantic audit.

## Touch-list
- `contracts/runtime/fact_manifest.v1.jsonschema`
- `contracts/runtime/fact_request.v1.jsonschema`
- `contracts/runtime/fact_plan.v1.jsonschema`
- `contracts/runtime/fact_result.v1.jsonschema`
- `contracts/runtime/fact_contract.v1.jsonschema`
- `docs/FACT_CONTRACT_SCHEMA_GUARD.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-fact-contract-schema-a922.md`
- `docs/REPORTS/2026-03-31-consultant-core-fact-contract-schema-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/legacy_caller_surface.json`
- `docs/system_forensics/governance_delta.json`
- `docs/system_forensics/INDEX.md`
- `STATE.md`
- `STRUCTURE.md`
- `scripts/recovery_execution_guard.py`
- `scripts/fact_plane_guard.py`
- `scripts/fact_contract_schema_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/app/core/fact_plane.py`
- `truffles-api/app/core/__init__.py`
- `truffles-api/app/schemas/webhook.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_fact_contract_schema_guard.py`

## Root cause (mandatory)
### Symptom
The fact path already has request/plan/result objects on the hot path, but the governing contract is still incomplete: no `FactManifestV1`, no top-level `FactContractV1` schema envelope, and the authority registry still overclaims canary cutover evidence at the schema stage.

### Minimal reproduction
1. Read `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md` and `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`.
2. Inspect `truffles-api/app/core/fact_plane.py` and confirm request/plan/result exist.
3. Observe there is no runtime schema for `fact_manifest` or `fact_contract`.
4. Observe the authority registry still points `fact_scope` evidence at later family/cutover artifacts instead of only the schema block.

### Evidence
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- `truffles-api/app/core/fact_plane.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`

### Five Whys
1. Why is fact architecture still structurally open? Because the runtime contract is only partially typed.
2. Why is partial typing unsafe? Because downstream helpers can still drift through undeclared envelope fields or over-broad allowed scope.
3. Why is a manifest required? Because canonical refs, aliases, companion rules, renderer ids, and provenance must be declarative, not scattered across helpers.
4. Why is a top-level fact contract envelope required? Because runtime meta currently carries nested request/plan/result without its own schema or closure proof.
5. Why must registry evidence be corrected now? Because the current whole-system block must not claim later family/cutover proof as if it were schema closure.

### Broken invariant
Requested fact scope, allowed emitted scope, and emitted fact scope must be explicit, typed, exact-set constrained, and declared in machine-readable contract artifacts before family-specific cutover begins.

### Shared mechanism
Whole-system fact contract schema materialization.

### Why the surfaced family belongs to that mechanism
The visible family residue is only the symptom. The shared mechanism is that fact-side behavior still lacks a complete declarative contract envelope.

### Open-world envelope expected to improve after the fix
- every fact turn exposes manifest id, requested refs, allowed emitted sets, and emitted refs;
- exact emitted-set legality becomes explicit;
- narrow family cutover can build on a stable contract instead of helper memory.

### Root cause statement
The system recovered a partial fact-plane chain, but the governing fact contract remains incomplete because declarative manifest truth and the top-level fact contract envelope were never materialized and the registry still carried later-slice evidence as if the schema block were already closed.

### Fix mechanism
- add `FactManifestV1` and `FactContractV1`;
- extend request/plan/result models and schemas with composition mode, allowed emitted sets, renderer/provenance, and exact emitted-set legality;
- rebase the authority registry and active whole-system docs to the full schema block;
- enforce the block with a dedicated guard.

## Plan
1. Materialize `FactManifestV1` and `FactContractV1` in `app/core/fact_plane.py`.
2. Extend request/plan/result models and runtime schemas.
3. Strengthen meta output so manifest id and allowed emitted sets are explicit.
4. Rebase `fact_scope` registry evidence to the whole-system schema block and move the next phase to `narrow_fact_family_cutover`.
5. Add `fact_contract_schema_guard` plus architecture/runtime tests.
6. Close the block by syncing active canon/program/lock/packet/state once.

## DoD
- `FactManifestV1`, `FactRequestV1`, `FactPlanV1`, `FactResultV1`, and `FactContractV1` exist and validate.
- Runtime JSON schemas exist for all five artifacts.
- `FactPlanV1` records exact `allowed_emitted_sets`, and `FactResultV1` marks non-authorized emitted sets as out-of-scope.
- Runtime meta exposes `fact_manifest_id` and `fact_allowed_sets` in addition to existing fact keys.
- The authority registry truth for `fact_scope` points to the schema block and names `narrow_fact_family_cutover` as the next phase.
- Active docs and packet move from `Authority Freeze` to `Fact Contract Schema` only after checks pass.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/authority_freeze_guard.py`
- `python3 scripts/fact_contract_schema_guard.py`
- `python3 scripts/fact_plane_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "fact_manifest or fact_contract or fact_plan or fact_request or fact_result or emitted_scope or allowed_fact_refs or info_sections"`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_fact_contract_schema_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-31-consultant-core-fact-contract-schema-a922.md`
- `docs/FACT_CONTRACT_SCHEMA_GUARD.yaml`
- `contracts/runtime/fact_manifest.v1.jsonschema`
- `contracts/runtime/fact_contract.v1.jsonschema`
- updated `truffles-api/app/core/fact_plane.py`
- updated `docs/system_forensics/authority_registry.json`
- generated packet and passing checks

## Rollback
- revert this block’s touch-list and restore `Authority Freeze` as the active block.

## No-go
- do not claim narrow family cutover closure in this block
- do not add family-specific branching to legacy frozen modules
- do not reopen replay
- do not sync active docs or `STATE.md` before the full block is green

## Risks / blockers
- existing canary cutover code still lives in the repo and must not be mistaken for schema-block closure
- compatibility schemas outside the hot path may still lag and remain residual debt until later blocks

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- narrow `location / hours / parking` family cutover remains open as the next block
- continuity/state normalization remains open
- boundary constriction remains open
- legacy mesh drain remains open

### Why not in this block
This block only closes the declarative and executable fact contract layer.

### Risk if deferred
Without the full schema block, every later fact or legacy change can drift through ad hoc contract shape and reopen widening behavior.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-narrow-fact-family-cutover-a922.md`

### Expiry / trigger to stop deferral
- stop deferral immediately after this block closes; the next admissible move is the narrow family cutover.

## Next-block contract (mandatory)
### Next block objective
Complete the whole-system `Narrow Fact-Family Cutover` for `location / hours / parking` against the now-explicit fact contract.

### First deterministic check command
`python3 - <<'PY'
from pathlib import Path
for rel in [
    'contracts/runtime/fact_manifest.v1.jsonschema',
    'contracts/runtime/fact_request.v1.jsonschema',
    'contracts/runtime/fact_plan.v1.jsonschema',
    'contracts/runtime/fact_result.v1.jsonschema',
    'contracts/runtime/fact_contract.v1.jsonschema',
]:
    assert Path(rel).exists(), rel
print('fact_contract_schema_ready')
PY`

### Blocked-by conditions
- Fact Contract Schema block not accepted
- authority registry fact_scope entry still points to schema work instead of family cutover
- active docs still point to Authority Freeze

### Owner role for closure
- Top Architect / Brain
