# TP-2026-03-30-consultant-core-architecture-recovery-master-program-a922

## Название / цель
Зафиксировать полный root-first architecture-recovery program как единственную governing base для consultant-core. Этот блок не делает runtime cutover. Он определяет полный порядок восстановления системы по root causes, а не по симптомам, и запрещает future work закрывать локальные families без системного закрытия механизма внутри заявленного envelope.

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
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_AUDIT.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
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
  - legacy displacement succeeds when authority is intercepted through explicit seams and the old path is demoted to adapter/shadow status;
  - extraction order must follow control and authority, not just file size or visible symptoms;
  - parity proof must precede deletion.
- Decision (`reuse/integrate/build`): `reuse + integrate`
  - reuse the typed runtime spine and the forensic packet;
  - integrate an explicit root-first order and acceptance law;
  - build only the governing program and phase contracts.
- Rejected options:
  - start with the first visible symptom family;
  - use broad rewrite rhetoric without explicit seam order;
  - let future TPs claim closure without full mechanism-envelope proof.

## Invariant
- Do not change runtime behavior.
- Do not let the first active slice start at the symptom layer.
- Do not permit partial closure of a mechanism.
- Do not weaken evidence or acceptance thresholds.
- Keep packet status `ready_for_external_handoff` and practical truth `r35f` unchanged.

## Scope
- Publish the root-first phased program.
- Establish the order of future implementation slices.
- Make explicit which classes of work are blocked until earlier phases close.
- Demote the fact-family cutover from first block to later proving slice.
- Sync active canon and machine-readable program base.

## Out of scope
- Runtime implementation.
- New replay runs.
- Family-specific fixes.
- Legacy deletion.

## Touch-list
- `docs/DECISIONS/DEC-2026-03-30-consultant-core-architecture-recovery-governing-decision.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-architecture-recovery-master-program-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-authority-registry-and-writer-law-enforcement-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-fact-contract-location-hours-parking-first-slice-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Fix the governing architecture statement.
2. Publish the root-cause stack and phase order.
3. Make the authority-registry block the first active slice.
4. Demote fact-family cutover to a later proving slice.
5. Sync state/structure and machine-readable program references.

## Root cause (mandatory)
### Symptom
The previous active program jumped too quickly from architecture verdict to a family-level fact slice, which risked repeating the same mistake as earlier patch loops: using a visible symptom as the first implementation anchor before the full authority topology was constrained.

### Minimal reproduction
1. Read the external packet and the recovery analyses.
2. Observe that the root-cause stack includes distributed authority, multiple truth carriers, boundary leakage, false pack/runtime split, and live legacy mesh.
3. Compare that to an implementation order that starts directly with `location / hours / parking`.
4. Observe that the symptom family is later in the stack than the authority and truth-carrier causes it depends on.

### Evidence
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_AUDIT.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`

### Five Whys
1. Why is symptom-first sequencing dangerous? Because it can repair one visible family while leaving upstream authority debt intact.
2. Why would that repeat the old failure mode? Because the same mixed-authority system can re-surface the problem through other callers and carriers.
3. Why is the authority topology prior? Because semantics, continuity, boundary, and fact scope all depend on who is allowed to write them.
4. Why must the program order reflect that? Because implementation follows the active canon and machine-readable guard base.
5. Why fix this before code? Because otherwise the next implementation can be disciplined locally and still wrong globally.

### Broken invariant
The active program must start with the highest-leverage root-cause layer, not with the first visible family symptom.

### Shared mechanism
Program-level sequencing and acceptance governance.

### Why this surfaced family belongs to that mechanism
The problem is not with `location / hours / parking` itself. The problem is choosing a later proving slice as if it were the first root-cause recovery move.

### Open-world envelope expected to improve after the fix
- future work starts by constraining authority instead of chasing symptoms;
- later family slices inherit stricter governance and clearer ownership;
- the repo becomes harder to use for patch-loop behavior.

### Root cause statement
The earlier post-review operating base still sequenced work too close to the visible symptom layer. The true recovery path must first constrain authority, truth carriers, and legacy ownership before it treats any fact family as the first proving slice.

### Fix mechanism
- rewrite the phased program around root causes;
- make authority registry the first active block;
- move fact-family cutover later in the sequence.

## DoD
- The phased program is root-first and explicit.
- The first active block is authority registry and writer-law enforcement.
- The fact-family cutover is explicitly blocked by earlier phases.
- `STATE.md`, `STRUCTURE.md`, and machine-readable program docs are synchronized.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `git diff --check`

## Evidence
- this TP
- updated governing docs and machine-readable program base

## Rollback
- restore the previous operating base and demotion of the authority-registry block

## No-go
- do not reopen implementation during this block
- do not call the root-cause order resolved unless the active docs and machine-readable guards agree on it

## Risks / blockers
- future work can still drift if the authority registry block is not actually executed
- some latent callers will only surface during later slices

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- the authority topology is still live in code
- truth carriers still compete
- fact plane still not materialized
- legacy mesh still co-owns behavior

### Why not in this block
This block only fixes the governing order.

### Risk if deferred
The repo would still be vulnerable to starting at the wrong layer.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-authority-registry-and-writer-law-enforcement-a922.md`

### Expiry / trigger to stop deferral
- stop deferral before any runtime implementation resumes

## Next-block contract (mandatory)
### Next block objective
Materialize the live authority registry, compatibility-carrier inventory, dead-surface registry, and writer-law guard base before any runtime slice resumes.

### First deterministic check command
`python3 - <<'PY'
from pathlib import Path
assert Path('docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-authority-registry-and-writer-law-enforcement-a922.md').exists()
print('root_first_program_ready')
PY`

### Blocked-by conditions
- governing docs not synchronized
- source-of-truth still points to a symptom-layer block

### Owner role for closure
Brain / Top Architect
