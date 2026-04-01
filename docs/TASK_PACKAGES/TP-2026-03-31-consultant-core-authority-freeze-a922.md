# TP-2026-03-31-consultant-core-authority-freeze-a922

## Название / цель
Завершить первый whole-system implementation block: зафиксировать machine-readable authority freeze по всей consultant-core системе, чтобы следующий runtime block начинался уже от точной writer/caller topology, а не от неявной памяти по canary-sequence или symptom-family residue.

## Canon refs
- `docs/DECISIONS/DEC-2026-03-31-consultant-core-whole-system-architecture-closure-governing-decision.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-architecture-closure-master-program-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-closure-program-reset-a922.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/failure_family_registry.json`
- `STATE.md`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com architecture fitness function evolutionary architecture`
- Date/time (local): `2026-03-31 09:05 +0500`
- Sources opened:
  - `https://martinfowler.com/articles/break-monolith-into-microservices.html`
- Source quality:
  - high-signal primary architecture source / Thoughtworks-M Fowler publication
- Ready solutions found:
  - migration must happen in atomic evolutionary steps;
  - every step must leave the architecture objectively closer to the target state;
  - decouple the new path, redirect all consumers, then retire the old path;
  - if the old path stays untracked, the architecture gets worse even when a new path exists.
- Decision (`reuse/integrate/build`): `integrate + build`
  - integrate the atomic-step / fitness-function discipline into the authority-freeze block;
  - build the missing machine-readable authority/caller freeze artifacts and guards for this repo.
- Rejected options:
  - jump directly into fact-schema runtime code without a frozen caller/writer map;
  - broad cleanup of legacy modules before caller-proof inventory exists;
  - replay or family-local fixes before authority-freeze closeout.

## Invariant
- No runtime behavior changes.
- No replay or human semantic audit.
- No new semantic, continuity, fact-scope, or boundary logic inside frozen legacy modules.
- No `STATE.md`, `docs/ACTIVE_*`, packet, or report sync until this full block closes.
- Every claimed freeze delta must be machine-readable.

## Scope
- Freeze the whole-system semantic writer map.
- Freeze the continuity writer/reader inventory.
- Freeze fact-scope widening surfaces.
- Freeze boundary override surfaces.
- Publish an exact legacy caller-surface inventory for frozen modules.
- Publish a machine-readable governance delta for this block.
- Wire a deterministic authority-freeze guard and tests.

## Out of scope
- Fact contract runtime implementation.
- Narrow fact-family cutover.
- Continuity normalization runtime extraction.
- Post-owner semantic constriction runtime changes.
- Replay / human audit.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-authority-freeze-a922.md`
- `docs/REPORTS/2026-03-31-consultant-core-authority-freeze-a922.md`
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
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/legacy_caller_surface.json`
- `docs/system_forensics/governance_delta.json`
- `STATE.md`
- `STRUCTURE.md`
- `scripts/build_agent_packet.py`
- `scripts/recovery_execution_guard.py`
- `scripts/arch_guard.py`
- `scripts/authority_freeze_guard.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_authority_freeze_guard.py`

## Root cause (mandatory)
### Symptom
Whole-system implementation can still drift into local runtime work because the repo lacks one explicit machine-readable freeze of writers, carriers, fact wideners, boundary overrides, and frozen legacy caller surfaces.

### Minimal reproduction
1. Read the whole-system governing DEC and master TP.
2. Observe that the next implementation block is `Authority Freeze`.
3. Inspect the current registries: they still primarily reflect canary-era evidence and do not yet expose one dedicated whole-system caller-surface artifact or one machine-readable authority delta for the new program.
4. Observe that frozen legacy modules are listed, but the exact frozen caller envelope is not yet published as one dedicated block artifact.

### Evidence
- `docs/DECISIONS/DEC-2026-03-31-consultant-core-whole-system-architecture-closure-governing-decision.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-architecture-closure-master-program-a922.md`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

### Five Whys
1. Why can later runtime work drift? Because the whole-system writer/caller freeze is not fully machine-readable yet.
2. Why is that dangerous? Because later blocks can misread canary evidence as whole-system closure.
3. Why does that reopen debt? Because live and shadow callers of frozen compatibility surfaces stay under-specified.
4. Why is that a blocker to fact work? Because fact-schema work depends on knowing exactly which frozen modules may not regain authority.
5. Why must this be the first implementation block? Because the governing DEC explicitly makes caller/writer freeze the first admissible runtime-adjacent move.

### Broken invariant
No new architecture block may start before the whole-system writer/caller envelope is frozen and machine-readable.

### Shared mechanism
Architecture governance and authority-topology control.

### Why the surfaced family belongs to that mechanism
Without an explicit freeze, later fact, continuity, boundary, or legacy work can still mutate the same authority surfaces under different labels.

### Open-world envelope expected to improve after the fix
- future runtime blocks start from one frozen authority map;
- frozen legacy modules have explicit caller surfaces;
- block closeout can name the exact authority delta;
- future agents can distinguish whole-system freeze evidence from canary salvage evidence.

### Root cause statement
The whole-system program reset established the new order, but it did not yet finish the first executable enforcement layer: an explicit whole-system authority freeze with dedicated caller-surface and delta artifacts.

### Fix mechanism
Publish dedicated machine-readable authority-freeze artifacts, wire them into source-of-truth and packet generation, and enforce them through an active block guard and tests.

## Plan
1. Create the Authority Freeze TP and report shell.
2. Publish `legacy_caller_surface.json` for the frozen legacy modules and wrapper/shadow surfaces that block future drain.
3. Publish `governance_delta.json` for the authority moved/locked by this block.
4. Rebase the three existing governance registries to `Authority Freeze` status and add whole-system scope notes/freeze metadata.
5. Add `authority_freeze_guard.py`.
6. Extend packet/source-of-truth validation to include the new artifacts.
7. Close the block in one sync: lock, active docs, packet, state, report, tests.

## DoD
- Active block becomes `Consultant Core Authority Freeze`.
- `authority_registry.json`, `compatibility_carrier_inventory.json`, and `dead_surface_registry.json` all expose authority-freeze status and whole-system scope notes.
- `legacy_caller_surface.json` exists and covers the frozen legacy modules with exact caller surfaces.
- `governance_delta.json` exists and records the authority locked by this block.
- `authority_freeze_guard.py` enforces the block and is part of the active guard chain.
- Packet/source-of-truth expose the new artifacts and statuses.
- No runtime code changed.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/authority_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_authority_freeze_guard.py`
- `git diff --check`

## Evidence
- new block TP and report
- updated authority/compatibility/surface registries
- new `legacy_caller_surface.json`
- new `governance_delta.json`
- new authority-freeze guard + tests
- packet and source-of-truth outputs synced once at block closeout

## Rollback
- restore the previous whole-system reset block as active if this authority-freeze block is rejected
- remove the new caller-surface and governance-delta artifacts from source-of-truth if the freeze is not accepted

## No-go
- no runtime changes under `truffles-api/app/core/*` or active router behavior paths
- no replay
- no fact-family local patching
- no boundary tightening beyond freeze metadata
- no state/canon/report churn before full block closeout

## Risks / blockers
- hidden non-test callers outside the visible repo can still exist for `app/webhook.py`
- dead-surface and caller-surface inventories must stay consistent or later drain work will target the wrong envelope
- future fact work remains blocked until this block closes

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- fact contract schema still open
- continuity normalization still open
- post-owner constriction still open
- boundary constriction still open
- pack/runtime separation still open
- legacy drain still open

### Why not in this block
This block only freezes authority and caller topology.

### Risk if deferred
Future runtime work can still misread the active authority boundary and reintroduce mixed ownership under a new label.

### Linked follow-up Task Package(s)
- future: `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-fact-contract-schema-a922.md`
- future: narrow fact-family cutover TP

### Expiry / trigger to stop deferral
- stop deferral immediately after this block closes; `Fact Contract Schema` becomes the only admissible next block.

## Next-block contract (mandatory)
### Next block objective
Materialize `Fact Contract Schema` and make the requested/allowed/emitted fact contract explicit before any narrow family cutover.

### First deterministic check command
`python3 - <<'PY'
from pathlib import Path
for rel in [
    'contracts/runtime/fact_request.v1.jsonschema',
    'contracts/runtime/fact_plan.v1.jsonschema',
    'contracts/runtime/fact_result.v1.jsonschema',
]:
    assert Path(rel).exists(), rel
print('fact_contract_schema_inputs_present')
PY`

### Blocked-by conditions
- authority-freeze block not accepted
- caller-surface inventory not machine-readable
- frozen module set not enforced by active guard/tests

### Owner role for closure
Brain / Top Architect
