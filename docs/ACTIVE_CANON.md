# ACTIVE CANON

## Current Truth
- External packet status: `ready_for_external_handoff`
- Current practical truth: `r35f`
- Runtime implementation status: continuity, boundary, pack/runtime, legacy, and operational reproof is complete repo-side; replay and full human semantic audit are the next admissible acceptance lane
- Active block: `Consultant Core Continuity / Boundary / Pack-Runtime / Legacy / Operational Reproof`
- This block does not claim product or practical closure; it only reproves the remaining live-code architecture claims in the reopened envelope.
- Machine-readable governance status: active registries are now on a live-code reproof base, not on product or practical closure.
- Practical/product closure status: open; fresh replay and full human semantic audit remain mandatory before any product or practical closure claim.
- Historical residue rule: later `r36*` replay/RCA/runtime materials and invalidated whole-system closure claims remain preserved history only under `docs/RECOVERY_EXECUTION_LOCK.yaml`; they do not advance the active block or practical truth while the live-code reproof block is active.

## Governing Architecture
`Single Semantic Owner + Strict Binding Boundary + Canonical Continuity State + First-Class Fact Plane + Adapter-only Legacy Mesh`

Operational implication:
- the target architecture is unchanged;
- hot-path semantic ownership remains reproven;
- continuity, boundary restore, pack/runtime seams, legacy non-authority, and operational canonical ownership are now reproven repo-side;
- acceptance is still a separate lane.

Primary governing docs:
- `docs/DECISIONS/DEC-2026-03-31-consultant-core-whole-system-architecture-closure-governing-decision.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-whole-system-architecture-closure-master-program-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-31-consultant-core-continuity-boundary-pack-runtime-legacy-and-operational-reproof-a922.md`
- `docs/RECOVERY_EXECUTION_LOCK.yaml`

## Writer Laws
### Semantic writer law
Only the semantic owner may author turn meaning.
Planner, executor, runtime shell, boundary, adapters, and evaluators may package, bind, validate, deny, degrade, or observe. They may not re-author meaning.

Current truth:
- hot-path business semantic authorship remains owner-backed only;
- planner/runtime synthetic control turns remain explicit `system_control` envelopes;
- no reopened semantic-owner work remains inside this block.

### Continuity writer law
Only canonical continuity state may own mutable pending-question and interaction continuity.
Any compatibility carrier is derived-only unless explicitly registered with owner, expiry, and deletion plan.

Current truth:
- canonical runtime reprojection remains active;
- pending-resume and boundary restore now reuse only canonical `pending_question_contract` from `context_manager.canonical_dialog_state` on the active path;
- non-canonical expected-reply fallback no longer drives restore on the reproofed path.

### Fact writer law
Owner writes requested fact scope.
Binding writes allowed emitted scope.
Resolver/renderer writes emitted scope.
No other layer may widen fact scope.

Current truth:
- typed fact contract remains active;
- first-family cutover remains active;
- active pack/runtime callers stay on the public runtime seam during this block.

### Boundary law
Deterministic boundary may only:
- validate
- deny
- degrade with explicit reason-code
- preserve or reuse canonical continuity artifacts
- request replan

Deterministic boundary may not:
- infer new intent
- invent a new pending question
- widen fact scope
- write new semantic meaning after the owner speaks

Current truth:
- reply-envelope narrowing remains active;
- boundary restore helpers now reuse canonical pending-question contracts only;
- stale boundary expected-reply fallback is removed from the reproofed restore path.

## Reopened Execution Order
1. `Semantic Owner And Post-Owner Reconstruction Reopen`
2. `Continuity / Boundary / Pack-Runtime / Legacy / Operational Reproof`
3. `Replay + Full Human Semantic Audit`

## Block-Closeout Reporting Discipline
- Do not update `STATE.md`, `docs/ACTIVE_*`, packet, or reports after micro-fixes inside an unfinished block.
- Update canon/state/report only once, at the close of one full block with its checks and evidence.

## Truth-Correction Law
- No block may claim repo-side closure while live code still contains a competing writer, synthetic semantic control path, or downstream semantic reconstruction path inside the declared mechanism envelope.
- Registry and test green status do not count as closure proof if they only restate the registry narrative.
- Closure claims must follow live-code proof, not replace it.

## Immediate Next Move
The current non-negotiable next move is:
- run fresh replay and full human semantic audit before any product or practical closure claim
