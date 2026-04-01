# TP-2026-03-15-consultant-core-controlled-demolition-master

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-CONTROLLED-DEMOLITION-MASTER-2026-03-15`
- `PARENT_BLOCK_ID`: `none`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o79-executable-interaction-core-redesign-reset-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o80-base-canon-interaction-model-sync-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o81-machine-readable-owner-matrix-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o82-persisted-interaction-state-a1.md`, `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o83-owner-resolver-m27-vertical-slice-a1.md`
- `UNLOCKS`: `CONSULTANT-CORE-GOVERNANCE-LOCK-A922`, `CONSULTANT-CORE-RUNTIME-CONTRACTS`, `CONSULTANT-CORE-NEW-RUNTIME-SLICE`, `CONSULTANT-CORE-MULTI-PACK-ACCEPTANCE`

## Название/цель
Заменить multi-owner consultant runtime на one semantic core, one continuity store, and black-box proof path while preserving the reusable pack/capability substrate.

## Canon refs
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `STRATEGY/REQUIREMENTS.md`
- `SPECS/ARCHITECTURE.md`
- `SPECS/CONSULTANT.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`

## Invariant
- every inbound still ends in exactly one of `FACT`, `COLLECT`, `HANDOFF`
- semantic ownership belongs only to policy core
- continuity truth belongs only to dialog state
- proof/eval never authors semantics
- legacy router core may not keep growing semantically
- reusable pack/capability substrate remains reusable and tenant-agnostic

## Scope
- freeze legacy semantic core
- define executable top-level governance canon
- generate minimal agent context
- create runtime-contract migration program
- collapse continuity to one writer over time
- remove semantic authority from proof/eval
- remove salon coupling from generic runtime
- establish multi-pack acceptance before platform claims

## Out of scope
- full repo reset
- cosmetic cleanup
- unrelated UI work
- new product features outside consultant core correctness

## Touch-list
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/ACTIVE_CANON.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/LEGACY_SUNSET.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `scripts/build_agent_packet.py`
- `scripts/legacy_freeze_guard.py`
- `scripts/continuity_writer_guard.py`
- `scripts/proof_path_guard.py`
- `scripts/arch_guard.py`
- `truffles-api/tests/architecture/`
- future runtime-contract and new-core files in follow-up blocks only

## Plan (1..N)
1. Establish operational canon and freeze rules.
2. Add generated agent packet flow.
3. Add architecture guard entrypoint and tests.
4. Materialize runtime contracts.
5. Introduce the new runtime core package for one bounded slice.
6. Cut reasoning entrypoint to the new core for that slice.
7. Collapse continuity writes to one service for that slice.
8. Remove proof semantic rewrites for that slice.
9. Remove salon-root generic assumptions for that slice.
10. Expand slice coverage until legacy runtime is compatibility-only.
11. Add multi-pack acceptance battery.
12. Retire remaining legacy semantic paths.

## Blocks

### Block A — Governance Lock
- Objective: make wrong architectural moves fail before merge.
- Authority removed in this block: narrative-only canon.
- Legacy path retired in this block: none.
- What becomes forbidden after merge:
  - new executable additions in sunset legacy router files without recorded waiver
  - new continuity-writer drift outside the current canonical writer set
  - new proof-path imports or semantic rewrite growth in governed proof-only files

### Block B — Runtime Contracts
- Objective: publish machine-readable runtime contracts for `PolicyDecision`, `DialogState`, `BoundaryOverride`, and `TurnResult`.
- Authority removed in this block: implicit runtime contract assumptions.
- Legacy path retired in this block: none yet; this is contract materialization.
- What becomes forbidden after merge:
  - new runtime slices without versioned contract artifacts

### Block C — Semantic Core Cutover
- Objective: route one bounded flow through the new runtime core.
- Authority removed in this block: migrated-flow semantic routing from the legacy router.
- Legacy path retired in this block: migrated-flow branching in `decision.py`.
- What becomes forbidden after merge:
  - runtime outcome rewriting after planner without explicit boundary override

### Block D — Continuity Collapse
- Objective: one writable `DialogState`.
- Authority removed in this block:
  - live authority of `expected_reply_*`
  - live authority of `session_memory.interaction_state`
  - live authority of `pending_resume` semantic fields
- Legacy path retired in this block: direct semantic writes outside the target dialog-state writer.

### Block E — Proof Path Excision
- Objective: proof reads runtime only.
- Authority removed in this block:
  - scenario retagging as acceptance truth
  - evaluator semantic inference as acceptance truth
- Legacy path retired in this block: self-referential proof logic.

### Block F — Multi-Pack Proof
- Objective: prove platform claims on multiple packs.
- Authority removed in this block: beauty-only proof as platform evidence.
- Legacy path retired in this block: `demo_salon` as de facto architecture center.

## DoD
- top-level governance canon exists and is machine-checked
- generated agent packet exists and is reproducible
- legacy freeze is guarded before merge
- continuity drift is guarded before merge
- proof-path drift is guarded before merge
- runtime contracts and new-core migration remain blocked until those Week 1 fences are green

## Checks
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`

## Evidence
- generated agent packet files
- guard outputs
- architecture tests
- `STATE.md` update with FACT-only evidence

## Rollback
- keep old runtime path as-is until later migration blocks
- revert governance artifacts only if they are wrong
- do not restore silent semantic authority to proof path

## No-go
- no new semantic helper forests in legacy router files
- no more row-closure as the primary progress signal
- no beauty-only evidence for platform claims
- no dual semantic truth between runtime and evaluator
- no hidden runtime cutover inside governance-only blocks

## Risks/Blockers
- current runtime is still mixed/legacy; this master program only constrains it first
- top-level truth must stay aligned with actual code reality, not aspirational only

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block`: legacy runtime still exists; runtime contracts are not yet fully materialized; multi-pack acceptance is not yet an acceptance gate.
- `Why not in this block`: the master program defines the migration order; it does not implement every block at once.
- `Risk if deferred`: without disciplined sequencing, the repo will continue mixing target architecture with legacy survival code.
- `Linked follow-up Task Package(s)`: `TP-2026-03-15-consultant-core-governance-lock-a922`, `TP-2026-03-15-consultant-core-runtime-contracts-a922`, `TP-2026-03-15-consultant-core-new-runtime-slice-a922`
- `Expiry/trigger to stop deferral`: before any new consultant-core feature or platform-level claim.

## Next-block contract (mandatory)
- `Next block objective`: finish Week 1 Governance Lock and make the repo self-constraining.
- `First deterministic check command`: `python3 scripts/arch_guard.py`
- `Blocked-by conditions`: governance canon missing; packet generation missing; guards not green.
- `Owner role for closure`: `Top Architect`
