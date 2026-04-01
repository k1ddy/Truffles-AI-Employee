# TP-2026-03-30-consultant-core-truth-carrier-inventory-and-freeze-a922

## Название / цель
Превратить compatibility-carrier inventory в enforceable truth-carrier freeze law для consultant-core до любых runtime cutover slices. Этот блок должен не переписывать runtime, а сделать machine-readable writer/read precedence, materialize allowed-vs-competing carrier rules, and block any new competing continuity writers from entering the repo by drift.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/DECISIONS/DEC-2026-03-30-consultant-core-architecture-recovery-governing-decision.md`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/ledgers/STATE_SURFACE_INVENTORY.md`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/authority_registry.json`

## One web search (mandatory before implementation)
- Query: `site:martinfowler.com cqrs projections source of truth read model derived view`
- Date/time (local): `2026-03-30 13:41:55 +0500`
- Sources opened:
  - `https://martinfowler.com/bliki/ProjectionalEditing.html`
- Source quality:
  - primary architecture source / Martin Fowler
- Ready solutions found:
  - one system definition should have one core definition and multiple projections, not multiple peer truth surfaces;
  - projections can be useful, but they must stay derived from the core definition;
  - storage, editable, and executable representations must be separated explicitly or they drift into competing sources.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the current compatibility-carrier inventory and state-surface evidence;
  - integrate one explicit writer/read precedence law plus one continuity guard contract;
  - build only the missing machine-readable freeze/enforcement layer.
- Rejected options:
  - keep grouped low-confidence carriers without sharpening them;
  - let continuity guard stay implicit or empty;
  - move to legacy cutover before continuity precedence is frozen.

## Invariant
- Do not change runtime behavior.
- Do not remove live carriers in this block.
- Do not claim one-canonical-state is achieved yet.
- Do not allow new competing continuity writes to appear outside the frozen writer set.
- Do not leave grouped or ambiguous carrier families where repo-backed evidence can split them further.

## Scope
- Upgrade `docs/system_forensics/compatibility_carrier_inventory.json` from inventory to explicit truth-carrier freeze law.
- Sharpen currently low-confidence or grouped carrier entries into explicit machine-readable carrier rows where evidence supports it.
- Materialize writer precedence, reader precedence, allowed future write paths, guarded context tokens, and expiry triggers.
- Wire the freeze law into `docs/SOURCE_OF_TRUTH.yaml`, `docs/LEGACY_SUNSET.yaml`, `docs/_generated/AGENT_PACKET.*`, `scripts/build_agent_packet.py`, `scripts/continuity_writer_guard.py`, `scripts/arch_guard.py`, and architecture tests.
- Sync active canon/program/state/report so the next block starts from frozen continuity truth rather than narrative-only inventory.

## Out of scope
- Runtime cutover or carrier removal.
- Legacy caller deletion.
- Planner/executor semantic constriction.
- Boundary constriction.
- Fact-plane implementation.
- Family-specific behavior fixes.

## Touch-list
- `docs/RECOVERY_EXECUTION_LOCK.yaml`
- `docs/RECOVERY_PHASE_WAIVER.yaml`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_CANON.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `scripts/build_agent_packet.py`
- `scripts/continuity_writer_guard.py`
- `scripts/arch_guard.py`
- `scripts/recovery_execution_guard.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/tests/architecture/test_authority_registry.py`
- `truffles-api/tests/architecture/test_single_continuity_writer.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `truffles-api/tests/architecture/test_truth_carrier_freeze.py`
- `truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `docs/REPORTS/2026-03-30-consultant-core-truth-carrier-inventory-and-freeze-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-truth-carrier-inventory-and-freeze-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Reconstruct the full continuity carrier envelope from current registry plus code evidence.
2. Split or sharpen grouped carrier families that are still too coarse for freeze law.
3. Add explicit writer/read precedence and no-new-writer growth rules to the carrier inventory.
4. Wire continuity guard to the machine-readable freeze law and fail on drift.
5. Record the explicit phase advance in the lock/waiver layer while keeping `r35f` and runtime pause unchanged.
6. Sync source-of-truth / active block / agent packet / tests / report / state.

## Root cause (mandatory)
### Symptom
The repo now has a machine-readable authority base, but continuity truth is still only partially frozen. Multiple carriers still coexist, and the guard layer does not yet enforce one explicit no-new-competing-writer law for them.

### Minimal reproduction
1. Read `docs/system_forensics/compatibility_carrier_inventory.json`.
2. Observe that it inventories carriers, but does not yet fully encode writer/read precedence and guard contract for each carrier family.
3. Read `docs/LEGACY_SUNSET.yaml` and `scripts/continuity_writer_guard.py`.
4. Observe that the continuity guard contract is not yet fully materialized from the active machine-readable carrier base.
5. Observe that grouped low-confidence carrier families still remain, which keeps the continuity freeze partly narrative.

### Evidence
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/ledgers/STATE_SURFACE_INVENTORY.md`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/services/reasoning_core.py`

### Five Whys
1. Why can continuity drift still happen? Because several carriers are still live and their precedence is not yet frozen in one enforceable machine-readable law.
2. Why is inventory alone insufficient? Because inventory says what exists, but not yet the exact precedence, allowed future writers, and guard contract.
3. Why is that dangerous? Because future slices can add one more context write and still claim they only touched a local behavior.
4. Why must grouped low-confidence carriers be sharpened? Because broad buckets hide the exact write/read seams that later blocks must drain.
5. Why must this happen before legacy cutover or post-owner constriction? Because those blocks depend on knowing exactly which continuity surfaces are canonical, derived, competing, adapter-only, or observer-only.

### Broken invariant
Before runtime recovery resumes, continuity truth must have one explicit writer/read precedence law and one enforceable no-new-competing-writer guard.

### Shared mechanism
Truth-carrier freeze and continuity writer-law enforcement.

### Why this surfaced family belongs to that mechanism
This is not one session-memory issue or one pending-resume issue. It is the missing continuity freeze layer for the whole system.

### Open-world envelope expected to improve after the fix
- future slices start from one explicit continuity precedence law;
- grouped or hidden carrier seams become harder to ignore;
- new competing continuity writes fail deterministically instead of surfacing later in behavior.

### Root cause statement
The repository now knows which continuity carriers exist, but it still lacks one fully machine-readable writer/read precedence law and guard contract for them. Without that freeze layer, multiple carriers remain governable only by narrative and future drift is still easy.

### Fix mechanism
- sharpen the carrier inventory into a truth-carrier freeze law;
- wire a deterministic continuity guard to that law;
- sync packet/tests/report/state so future work must obey it.

## DoD
- `docs/system_forensics/compatibility_carrier_inventory.json` explicitly encodes writer precedence, reader precedence, allowed future write paths, guarded context tokens, and expiry trigger for every in-scope carrier.
- previously grouped low-confidence carrier families are either split into explicit carriers or justified with stronger evidence and no longer remain vague.
- `docs/LEGACY_SUNSET.yaml` and `scripts/continuity_writer_guard.py` enforce the frozen continuity writer set.
- the recovery execution lock and waiver now point to this block while keeping `r35f` and runtime pause unchanged.
- `docs/SOURCE_OF_TRUTH.yaml` and generated packet make this block the active operating base.
- deterministic tests fail if continuity freeze law or guard contract drifts.
- no runtime behavior changed.

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/recovery_execution_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture/test_authority_registry.py`
- `pytest -q truffles-api/tests/architecture/test_single_continuity_writer.py`
- `pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k continuity_writer`
- `pytest -q truffles-api/tests/architecture/test_truth_carrier_freeze.py`
- `pytest -q truffles-api/tests/architecture/test_recovery_execution_guard.py`
- `git diff --check`

## Evidence
- this TP
- updated `docs/system_forensics/compatibility_carrier_inventory.json`
- updated source-of-truth / legacy sunset / agent packet / guards / tests
- `docs/REPORTS/2026-03-30-consultant-core-truth-carrier-inventory-and-freeze-a922.md`

## Rollback
- restore the previous compatibility-carrier inventory and remove the freeze-law / guard sync changes

## No-go
- do not remove carriers in this block
- do not claim continuity normalization or legacy drain is done
- do not permit continuity guard to remain a stale or empty shell
- do not treat grouped carrier buckets as “good enough” if repo-backed evidence can split them further

## Risks / blockers
- some auxiliary carrier families may still need deeper evidence to split precisely
- some readers merge multiple carriers indirectly through snapshot builders
- old tests may encode stale assumptions about continuity guard state and need explicit correction

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- competing carriers remain live at runtime
- legacy readers and writers still exist
- runtime shell / planner / executor still reconstruct semantic-adjacent artifacts
- fact plane is still missing

### Why not in this block
This block freezes the continuity map and writer/read law; it does not cut runtime paths yet.

### Risk if deferred
Future slices could continue adding or relying on continuity bypasses without being forced to name them.

### Linked follow-up Task Package(s)
- adapter-only legacy mesh and caller proof block
- post-owner reconstruction constriction block
- boundary/degrade constriction block

### Expiry / trigger to stop deferral
- stop deferral before any legacy mesh cutover or post-owner runtime constriction resumes

## Next-block contract (mandatory)
### Next block objective
Prove exact live callers of the legacy mesh and reduce legacy surfaces to adapter-only/shadow-only semantics without hidden co-ownership.

### First deterministic check command
`python3 - <<'PY'
from pathlib import Path
assert Path('docs/system_forensics/compatibility_carrier_inventory.json').exists()
assert Path('docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-truth-carrier-inventory-and-freeze-a922.md').exists()
print('truth_carrier_freeze_block_ready')
PY`

### Blocked-by conditions
- compatibility-carrier freeze law incomplete
- continuity guard not wired to the active machine-readable base
- grouped low-confidence continuity carrier families still unresolved

### Owner role for closure
Brain / Top Architect
