# TP-2026-03-30-consultant-core-authority-registry-and-writer-law-enforcement-a922

## Название / цель
Материализовать live authority topology consultant-core и превратить ее в enforceable repository law до любого нового runtime slice. Этот блок должен создать machine-readable authority registry, compatibility-carrier inventory, dead-surface registry и guard/test updates так, чтобы дальнейшие implementation blocks больше не могли выдавать symptom-fixes за architecture recovery.

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
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_AUDIT.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/failure_family_registry.json`
- `docs/system_forensics/runtime_path_registry.json`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com branch by abstraction legacy seams strangler`
- Date/time (local): `2026-03-30 12:17:10 +0500`
- Sources opened:
  - `https://martinfowler.com/articles/patterns-legacy-displacement/event-interception.html`
- Source quality:
  - primary architecture source / Martin Fowler
- Ready solutions found:
  - legacy displacement must first identify the real system-of-record and interception points;
  - new governance must be attached to explicit seams before old authority is drained;
  - hidden caller contracts must be surfaced before safe deletion or cutover.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the existing forensic packet and typed runtime spine;
  - integrate one live authority map and one compatibility-carrier map;
  - build enforcement only where the current repo still lacks machine-readable control.
- Rejected options:
  - start runtime code changes before the authority map exists;
  - infer live authority from memory or old docs;
  - treat evaluator success as authority proof.

## Invariant
- Do not change runtime behavior.
- Do not close the block if any major live authority seam remains undocumented in the registries.
- Do not classify a file as dead without caller proof or explicit shadow/deletion evidence.
- Do not leave compatibility carriers unnamed and still allow future slices to depend on them.
- Do not weaken frozen-surface rules to make future implementation easier.

## Scope
- Create and populate:
  - `docs/system_forensics/authority_registry.json`
  - `docs/system_forensics/compatibility_carrier_inventory.json`
  - `docs/system_forensics/dead_surface_registry.json`
- Update machine-readable source-of-truth / agent packet to include these registries.
- Update architecture guards/tests so future work cannot ignore the registries.
- Record exact current writer/caller categories for:
  - semantic meaning
  - continuity state
  - fact scope
  - boundary/degrade
  - dead/shadow surfaces
- Establish allowed future-writer law for later slices.

## Out of scope
- Runtime cutover.
- Truth-carrier elimination.
- Planner/executor constriction.
- Boundary constriction.
- Fact-plane implementation.
- Legacy deletion.

## Touch-list
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `scripts/build_agent_packet.py`
- `scripts/arch_guard.py`
- `scripts/authority_registry_block_guard.py`
- `scripts/recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_authority_registry_block_guard.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `docs/REPORTS/2026-03-30-consultant-core-authority-registry-and-writer-law-enforcement-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Map all live authority seams by mechanism, not by file size.
2. Write one machine-readable authority registry with current owners, competing writers, target owners, and closure criteria.
3. Write one compatibility-carrier inventory with carrier, writers, readers, truth rank, expiry, and deletion owner.
4. Write one dead-surface registry with mounted/unmounted/removed/shadow-only evidence.
5. Update source-of-truth and agent packet so these registries become part of the active operating base.
6. Add tests/guards that fail when the active operating base drifts.
7. Lock the governing base itself so derived active docs cannot silently advance practical truth, active block, or runtime phase without explicit waiver.
8. Keep owner-status fields and registry phase credit block-2-honest so generated packet text cannot silently re-promote later-phase completion claims.
9. Keep the `historical residue` rule machine-readable so preserved `r36*`/runtime/RCA materials can never silently become active canon while block 2 is locked.

## Root cause (mandatory)
### Symptom
The repo has a strong forensic packet but still lacks one machine-readable live authority map that future work must obey. Without that, slices can still declare success while hidden co-writers or compatibility carriers remain active.

### Minimal reproduction
1. Read the packet and identify the root-cause families.
2. Ask one machine-readable question: who currently writes semantic meaning, continuity state, fact scope, and boundary overrides?
3. Observe that the answer is distributed across narrative docs, code inspection, and partial ledgers rather than one active registry.
4. Ask which carriers are derived-only versus live truth competitors.
5. Observe that the answer is similarly spread out and not yet enforceable by the active guard base.

### Evidence
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/runtime_path_registry.json`
- `docs/system_forensics/failure_family_registry.json`

### Five Whys
1. Why can future work still drift? Because the active operating base does not yet expose one enforceable live authority map.
2. Why is that dangerous? Because hidden co-writers or legacy callers can stay active while a slice claims recovery.
3. Why are narrative docs insufficient? Because guards and future agents need machine-readable governance, not only prose.
4. Why must compatibility carriers be inventoried separately? Because continuity drift often hides in carriers that look like transport details.
5. Why must this happen before runtime code? Because otherwise any next slice can still mis-scope the system it claims to fix.

### Broken invariant
The active repo governance must have one machine-readable live authority map before any runtime recovery slice resumes.

### Shared mechanism
Authority-topology governance and writer-law enforcement.

### Why this surfaced family belongs to that mechanism
This is not one docs problem. It is the missing control surface for all later runtime work.

### Open-world envelope expected to improve after the fix
- future slices start from one explicit authority map;
- hidden legacy or compatibility writers are harder to ignore;
- closure becomes mechanism-based instead of scenario-based.

### Root cause statement
The consultant-core packet already knows the system is mixed-authority, but the repository still lacks one enforceable machine-readable authority map and compatibility-carrier map. Without them, later work can still start from partial memory and close blocks before the actual system envelope is reduced.

### Fix mechanism
- create live registries;
- wire them into the active machine-readable governance base;
- add tests/guards that fail on drift.

## DoD
- `authority_registry.json` exists and names current owner, competing writers, target owner, target phase, closure criteria for each major mechanism.
- `compatibility_carrier_inventory.json` exists and names current writers/readers/truth-rank/expiry for each live compatibility carrier.
- `dead_surface_registry.json` exists and distinguishes mounted, unmounted, removed, and shadow-only surfaces with evidence.
- `docs/SOURCE_OF_TRUTH.yaml` and the generated agent packet point to these registries.
- `docs/RECOVERY_EXECUTION_LOCK.yaml` and `docs/RECOVERY_PHASE_WAIVER.yaml` freeze the governing base and phase-advance law.
- architecture guards/tests fail if the operating base drifts from these registries or the governing lock.
- the active registry layer does not cite later-phase runtime/proof artifacts as if they were block-2 evidence.
- derived owner-status fields and packet wording remain block-2-honest instead of reusing later-phase completion language.
- the historical-residue rule is machine-readable in the lock/source-of-truth layer and visible in the generated packet.
- no runtime behavior changed.

## Checks
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/authority_registry_block_guard.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry_block_guard.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `git diff --check`

## Evidence
- this TP
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- updated source-of-truth / recovery lock / agent packet / tests
- `docs/REPORTS/2026-03-30-consultant-core-authority-registry-and-writer-law-enforcement-a922.md`

## Rollback
- remove the new registries and revert the machine-readable governance updates

## No-go
- do not start runtime implementation in this block
- do not classify a surface as dead without evidence
- do not leave `unknown` as a blanket answer where code or packet evidence can narrow it
- do not cite later-phase runtime implementations, later-phase reports, or later-phase guards as if they were proof of block-2 closure

## Risks / blockers
- some indirect callers may still require deeper code search
- some carriers may require explicit runtime read/write tracing later
- dead-surface claims can be wrong if they rely on stale docs instead of live code/tests

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- no runtime authority is reduced yet
- truth carriers remain live
- fact plane remains missing
- boundary overreach remains open
- legacy mesh remains live

### Why not in this block
This block creates the governance substrate for all later runtime reductions.

### Risk if deferred
Later slices can still misstate what they actually fixed.

### Linked follow-up Task Package(s)
- truth-carrier inventory and freeze block
- adapter-only legacy mesh and caller proof block
- only after those: planner/executor constriction, boundary constriction, fact plane materialization

### Expiry / trigger to stop deferral
- stop deferral before any runtime slice resumes

## Next-block contract (mandatory)
### Next block objective
Freeze truth carriers by turning the compatibility-carrier inventory into an explicit writer/read-precedence law and blocking new competing carriers.

### First deterministic check command
`python3 - <<'PY'
from pathlib import Path
for path in [
  'docs/system_forensics/authority_registry.json',
  'docs/system_forensics/compatibility_carrier_inventory.json',
  'docs/system_forensics/dead_surface_registry.json',
]:
    assert Path(path).exists(), path
print('authority_base_artifacts_present')
PY`

### Blocked-by conditions
- authority registries absent or incomplete
- source-of-truth / agent packet not wired to them
- guards/tests still ignore them

### Owner role for closure
Brain / Top Architect
