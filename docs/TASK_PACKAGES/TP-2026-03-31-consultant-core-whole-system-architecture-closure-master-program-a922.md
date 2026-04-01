# TP-2026-03-31-consultant-core-whole-system-architecture-closure-master-program-a922

## Название / цель
Зафиксировать ускоренную whole-system программу consultant-core recovery так, чтобы любой следующий агент работал от одного полного плана, а не от микрофиксов, отдельных family-симптомов или canary-only памяти.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/DECISIONS/DEC-2026-03-31-consultant-core-whole-system-architecture-closure-governing-decision.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- `docs/system_forensics/failure_family_registry.json`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/CUTOVER_DEPENDENCY_GRAPH.md`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com branch by abstraction parallel change legacy system`
- Date/time (local): `2026-03-31 00:00 +0500`
- Sources opened:
  - `https://martinfowler.com/ieeeSoftware/beforeClarity.pdf`
- Source quality:
  - primary source / Michael Feathers via Martin Fowler archive
- Ready solutions found:
  - dependency-breaking work must come before large cleanup if you want testable, safe change;
  - clarity alone is not enough; conservative seam work is required before deeper restructuring;
  - the execution plan must prefer safe dependency-breaking and staging over broad rewrite rhetoric.
- Decision (`reuse/integrate/build`): `reuse + integrate`
  - reuse the current typed spine and the forensic packet;
  - integrate a wave-based whole-system plan;
  - build only the missing machine-readable closure program and enforcing guards.
- Rejected options:
  - symptom-first family patching;
  - replay before architecture closure;
  - journal-first rewrite as the first plumbing pivot;
  - deleting legacy surfaces before caller proof.

## Invariant
- Do not relabel canary closure as whole-system closure.
- Do not open replay or human-audit lanes before architecture closure.
- Do not allow document/state churn after micro-fixes inside an unfinished block.
- Do not permit any block to claim progress without a named authority delta.

## Scope
- Define the full accelerated whole-system recovery program.
- Define wave order, parallel lanes, merge order, and final closure criteria.
- Define machine-readable governance artifacts required for full closure.
- Define block-closeout reporting discipline.

## Out of scope
- Runtime implementation for the downstream waves.
- Replay or human semantic audit.
- Family-local bugfixes outside the governing slices.

## Touch-list
- `docs/DECISIONS/DEC-2026-03-31-consultant-core-whole-system-architecture-closure-governing-decision.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-architecture-closure-master-program-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-closure-program-reset-a922.md`
- `docs/REPORTS/2026-03-31-consultant-core-whole-system-closure-program-reset-a922.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `STATE.md`
- `STRUCTURE.md`
- `scripts/recovery_execution_guard.py`
- `scripts/whole_system_program_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_whole_system_program_guard.py`

## Root cause (mandatory)
### Symptom
The repo repeatedly converges on canary-scoped progress while whole-system architecture debt remains open.

### Minimal reproduction
1. Read the canary recovery program and its closeout.
2. Read the whole-system audits and `failure_family_registry.json`.
3. Observe that whole-system blockers remain open after canary completion.
4. Observe that the current next move was still replay instead of broader architecture closure.

### Evidence
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/failure_family_registry.json`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`

### Five Whys
1. Why do fixes not reach whole-system completion? Because the formal execution program was narrower than the full audited problem.
2. Why was the program narrower? Because canary closure was treated as if it were whole-system closure.
3. Why is that unsafe? Because open blocker families still live outside the canary envelope.
4. Why do they reopen? Because semantic authority, continuity carriers, fact widening, and legacy compatibility remain system-wide.
5. Why must the program change first? Because without a new governing plan, future work can still optimize locally and fail globally.

### Broken invariant
The governing program must cover the full audited system debt, not only the canary envelope.

### Shared mechanism
Program-level architecture execution, sequencing, and closure law.

### Why surfaced families belong to that mechanism
Visible families reopen because the program allows local closure claims while the broader architecture mechanism remains open.

### Open-world envelope expected to improve after the fix
- future agents start from one whole-system program;
- all remaining blocker families map to explicit waves and lanes;
- state/canon/report updates happen only at block closeout, not after each micro-fix.

### Root cause statement
The current governing execution layer still treated canary recovery as the main program. That left the whole-system audited debt without one active executable plan.

### Fix mechanism
Replace the active canary-closeout operating base with a whole-system accelerated program and a program-reset block that freezes execution law before implementation resumes.

## Plan
### Wave 0. Program Reset And Freeze
- publish one whole-system governing DEC
- publish one whole-system master TP
- publish one active reset block TP
- forbid replay until whole-system architecture closure blocks complete

### Wave 1. Foundation Freeze
- authority freeze
- compatibility-carrier freeze
- legacy caller surface freeze
- frozen module law
- fact contract schema freeze

### Wave 2. Parallel Lanes
#### Lane A. Fact Plane
- `FactManifest`
- `FactRequestV1`
- `FactPlanV1`
- `FactResultV1`
- first narrow family cutover: `location / hours / parking`

#### Lane B. Continuity Collapse
- one canonical continuity nucleus around current `DialogState`
- demote competing carriers to derived/adapter/delete-candidate roles

#### Lane C. Semantic Owner Constriction
- isolate owner-only path
- make planner thin
- make executor execution-only

#### Lane D. Legacy Mesh Drain
- caller proof
- adapter-only or delete-ready classification
- legacy fanout collapse order

### Wave 3. Integration Merge
- merge order: Lane A -> Lane B -> Lane C -> Lane D
- only then final boundary constriction and pack/runtime separation completion

### Wave 4. Shadow And Operational Closure
- shadow lane elimination
- operational entrypoint dedupe

### Wave 5. Closure-Claim Truth Correction
- retract unsupported final-closure claims
- re-open semantic-owner and post-owner reconstruction as active unresolved invariants
- align registries/tests to live-code truth

### Wave 6. Semantic Owner And Post-Owner Reconstruction Reopen
- remove live non-owner semantic control decisions
- remove downstream semantic-contract reconstruction on the hot path

### Wave 7. Continuity / Boundary / Pack-Runtime / Legacy / Operational Reproof
- re-prove partial closure claims after semantic-owner reopen

### Wave 8. Final Acceptance
- locked replay
- requested vs emitted refs proof
- full human semantic audit
- failure-family closure update

## DoD
- The repo exposes one whole-system accelerated recovery program.
- The prior final-closure claim is explicitly retractable if live-code proof fails.
- The current active block is closure-claim truth correction.
- `Semantic Owner And Post-Owner Reconstruction Reopen` is the next admissible runtime block.
- The block-closeout reporting discipline is explicit: no `STATE.md` / canon / report sync after micro-fixes inside unfinished blocks.
- Generated packet, lock, and guard chain all reflect the new program.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/whole_system_program_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `pytest -q truffles-api/tests/architecture/test_whole_system_program_guard.py`
- `git diff --check`

## Evidence
- updated governing DEC
- updated active canon/program/source-of-truth/lock
- updated registries showing the new active block and next system-wide phases
- generated packet
- guard/test outputs

## Rollback
- restore the previous canary-closeout operating base and packet if the whole-system reset is rejected

## No-go
- no replay
- no human audit
- no runtime implementation during this reset block
- no micro-fix-based `STATE.md` or canon updates before a full block completes

## Risks / blockers
- unknown callers still block some future deletion steps
- whole-system closure still requires multi-wave implementation; this block only makes that execution unambiguous

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- all whole-system runtime blockers remain open
- no runtime authority has moved yet in this block

### Why not in this block
This block only resets and accelerates the governing program.

### Risk if deferred
The repo would continue to optimize canary residue while the system-wide debt remained open.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-closure-program-reset-a922.md`
- future: `Authority Freeze` TP

### Expiry / trigger to stop deferral
- stop deferral before any new runtime architecture slice starts

## Next-block contract (mandatory)
### Next block objective
Materialize `Authority Freeze` as the first whole-system implementation block and freeze semantic writers, continuity carriers, fact-scope wideners, boundary overrides, and legacy caller surfaces.

### First deterministic check command
`python3 - <<'PY'
from pathlib import Path
assert Path('docs/system_forensics/authority_registry.json').exists()
assert Path('docs/system_forensics/compatibility_carrier_inventory.json').exists()
assert Path('docs/system_forensics/dead_surface_registry.json').exists()
print('whole_system_authority_freeze_ready')
PY`

### Blocked-by conditions
- whole-system program reset block not accepted
- active docs still point to replay as the next move
- authority registry layer not aligned to the new active block

### Owner role for closure
Brain / Top Architect
