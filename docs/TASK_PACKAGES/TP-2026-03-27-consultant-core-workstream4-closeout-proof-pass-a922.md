# TP-2026-03-27-consultant-core-workstream4-closeout-proof-pass-a922

## Title / Goal
Replay a deterministic closeout envelope for `Workstream 4` and freeze the remaining planner/executor demotion boundary with architecture guards so compatibility control authority cannot quietly grow back.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 4 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 4 — Planner / Executor Demotion`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`

## One Web Search (mandatory before implementation)
- Query: `Stately XState guards docs`
- Date/time: `2026-03-27T20:17:08+05:00`
- Opened sources:
  - `https://stately.ai/docs/guards`
- High-signal source quality:
  - official Stately/XState docs
- Found reusable idea:
  - guards should be pure condition functions and transition selection should be explicit and serializable, not hidden in ambient imperative branching.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - this block is about freezing demotion boundaries; the relevant reusable idea is to make remaining control predicates explicit and guardable instead of leaving them as ambient imperative compatibility branches.
- Rejected options:
  - rely only on behavior tests: rejected because silent control-branch growth in core would be missed.
  - postpone closeout proof until legacy strangler: rejected because Workstream 4 needs its own factual closure evidence now.

## Root Cause (mandatory)
### Symptom
After the two demotion cuts, the code likely satisfies Workstream 4 behaviorally, but there is no explicit freeze guard proving that executor dispatch, runtime control predicates, and planner synthetic boundary builders remain constrained.

### Minimal Reproduction
1. Inspect `truffles-api/app/core/turn_executor.py` `execute(...)`.
2. Inspect `truffles-api/app/core/consultant_runtime.py` `_decision_requests_handoff(...)` / `_decision_collects(...)`.
3. Inspect `truffles-api/app/core/turn_planner.py` synthetic boundary builders.
4. Observe that without explicit architecture guards, compatibility control branches could be reintroduced silently in later edits.

### Evidence
- `truffles-api/app/core/turn_executor.py:237`
- `truffles-api/app/core/consultant_runtime.py:1478`
- `truffles-api/app/core/turn_planner.py:690`
- `truffles-api/app/core/turn_planner.py:724`

### Five Whys
1. Why is closeout not yet proven?
   - Because current evidence is mostly behavioral regression tests.
2. Why is that insufficient for freeze?
   - Because control-branch growth can reappear without immediately breaking those particular behaviors.
3. Why is this important now?
   - Because Workstream 4 done criteria are structural: planner/executor demotion, not just passing examples.
4. Why could it regress silently?
   - Because compatibility fields (`decision.outcome`, `decision.tool_action`) still exist as data surfaces.
5. Why does this need a dedicated family?
   - Because a closeout proof pass must explicitly lock the achieved boundary before Workstream 5 starts.

### Root Cause Statement
Workstream 4 implementation cuts are in place, but the repo lacks explicit structural proof that planner/executor control authority stays bounded, so closure would otherwise rely on narrative rather than a frozen guard envelope.

### Fix Mechanism
Add architecture guards for binding-only executor/runtime routing and fixed-shape planner synthetic builders, replay the deterministic contract envelope, and then mark Workstream 4 done if all criteria stay green.

## Invariant
- No new semantic/control authority in planner/executor.
- No weakening of `BindingPlanV1` or post-owner mutation guarantees.
- Boundary ignore/reject/degrade behavior remains intact.

## Scope
- Add architecture freeze guards for Workstream 4 boundaries.
- Add/refresh deterministic tests for fixed planner synthetic builder shape if needed.
- Run closure envelope and update repo truth.

## Out of Scope
- `decision.py` strangler
- legacy mesh deletion
- durable action plane
- LLM quality acceptance

## Touch-list
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Add architecture guard for binding-only executor dispatch and runtime control predicates.
2. Add/refresh deterministic guard for fixed planner synthetic boundary shapes.
3. Replay closeout deterministic suites.
4. If all criteria hold, mark `Workstream 4` done in repo truth.

## DoD
- Executor dispatch freeze guard exists.
- Runtime handoff/collect predicate freeze guard exists.
- Planner synthetic boundary shape freeze guard exists.
- Deterministic closeout envelope is green.
- `STATE.md` truthfully marks `Workstream 4` done if criteria are satisfied.

## Work Mode
- `closure`

## Checks
- `python3 -m py_compile truffles-api/tests/architecture/test_legacy_freeze_guard.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "binding_plan or preflight or degrade or planner"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py -k "preflight or duplicate_message or sender_branch or remote_branch_phone"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "binding_only or synthetic_boundary or continuity_writer or policy_decision_creation"`
- `git diff --check`

## Evidence
- TP
- deterministic pytest outputs
- repo truth update in `STATE.md`

## Release Safety
- local worktree only
- no rollout / no deploy
- rollback by reverting touched files

## Rollback
- revert touch-list files

## No-go
- no narrative-only closeout
- no weakening of previous W4 cuts
- no new compatibility routing in executor/runtime/planner

## Risks / Blockers
- architecture guard may need to tolerate harmless metadata reads while still catching control routing drift

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Compatibility fields still exist on `PolicyDecision`
- Planner/executor still emit compatibility metadata surfaces for migration consumers

### Why not in this block
- This block closes demotion, not deletion of compatibility shell

### Risk if deferred
- Workstream 5 still has to strangler the compatibility shell even after W4 closure

### Linked follow-up Task Package(s)
- `TP-2026-03-27-consultant-core-workstream5-legacy-mesh-strangler-entry-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if any runtime path starts treating compatibility fields as live control authority again.

## Next-block Contract (mandatory)
### Next block objective
Start Workstream 5 by identifying and cutting the first still-live control/authority seam in the legacy mesh, likely centered in `decision.py` consumers.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture -k legacy`

### Blocked-by conditions
- Workstream 4 closeout proof must be green and repo truth updated.

### Owner role for closure
- Brain / Top Architect
