# TP-2026-03-27-consultant-core-workstream4-planner-synthetic-boundary-demotion-cut-a922

## Title / Goal
Shrink planner synthetic boundary decisions so preflight/degrade paths carry fixed planner shape plus typed binding, while ignore/reject transport differences stay in boundary outcome builders instead of caller-shaped planner fields.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 1-3 done`, `Workstream 4 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 4 — Planner / Executor Demotion`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`

## One Web Search (mandatory before implementation)
- Query: `XState guards actions separation docs`
- Date/time: `2026-03-27T20:11:00+05:00`
- Opened sources:
  - `https://stately.ai/docs/actions`
- High-signal source quality:
  - official Stately/XState docs
- Found reusable idea:
  - action objects should be declarative and interpreted by the machine/runtime, not imperatively constructed in arbitrary custom branches.
  - fixed action semantics are safer than letting callers shape transition behavior ad hoc.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - repo already has typed boundary and binding artifacts; the correct move is to freeze planner synthetic decision shape and keep caller variation in explicit boundary metadata only.
- Rejected options:
  - keep caller-provided synthetic `action` on planner boundary builders: rejected because it leaves planner-side control shaping ambient.
  - move ignore/reject distinction into planner decision fields: rejected because that keeps boundary outcome semantics coupled to planner synthetic envelopes.

## Root Cause (mandatory)
### Symptom
Planner synthetic boundary builders still accept caller-shaped `action` / `tool_action` / `outcome`, and boundary request objects still pass those values through, so planner remains a live control shaper on preflight/degrade paths.

### Minimal Reproduction
1. Inspect `truffles-api/app/core/turn_planner.py:695-764`.
2. Observe `build_controlled_degrade(...)` and `build_preflight_reject(...)` accept caller-shaped control fields.
3. Inspect `truffles-api/app/core/turn_executor.py:1399-1458`.
4. Observe `BlockBoundaryRequest` / `DegradeBoundaryRequest` forward caller action values into planner synthetic decisions.

### Evidence
- `truffles-api/app/core/turn_planner.py:695-764`
- `truffles-api/app/core/turn_executor.py:72-98`
- `truffles-api/app/core/turn_executor.py:1399-1458`
- `truffles-api/app/services/reasoning_core.py:121-259`

### Five Whys
1. Why is planner still a control shaper?
   - Because synthetic boundary builders accept caller-defined control fields.
2. Why do callers still shape these decisions?
   - Because boundary request objects preserve older compatibility semantics like `ignore` vs `preflight_reject` in planner fields.
3. Why is that wrong after Workstream 2/4 progress?
   - Because typed binding and boundary outcomes already exist and should own execution/control semantics.
4. Why is that a problem?
   - Because planner synthetic decisions keep parallel control authority that should live in boundary metadata/outcomes.
5. Why does this block Workstream 4?
   - Because planner demotion requires planner to emit fixed boundary envelopes, not bespoke caller-shaped control contracts.

### Root Cause Statement
Synthetic boundary flows still let upstream callers shape planner control fields directly, so planner remains a live control-authority surface instead of a fixed adapter that emits governed boundary envelopes.

### Fix Mechanism
Freeze planner synthetic decision shape (`handoff` for degrade, `preflight_reject` for block), remove caller `action` from boundary request APIs, and keep ignore/reject distinction only in boundary outcome builders via explicit request flags.

## Invariant
- Typed `BindingPlanV1` remains attached to all synthetic boundary decisions.
- Boundary turn outcomes still expose correct reject/ignore/handoff behavior.
- Reason codes and interaction metadata remain observable.
- Executor binding-only routing from the previous block stays green.

## Scope
- Freeze planner synthetic boundary builder shape.
- Remove caller `action` from `BlockBoundaryRequest` / `DegradeBoundaryRequest`.
- Update boundary artifact builders and reasoning-core preflight/degrade helpers.
- Add deterministic regressions proving ignore/reject stays a boundary-outcome concern, not planner decision shaping.

## Out of Scope
- `decision.py` strangler
- broader legacy mesh deletion
- LLM quality acceptance
- durable action plane work

## Touch-list
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_reasoning_core.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Freeze planner synthetic boundary builders to fixed control shape.
2. Remove `action` from boundary request dataclasses and update call sites.
3. Keep ignore/reject distinction only in boundary outcome building.
4. Add regressions for ignored preflight and fixed synthetic planner shape.
5. Run deterministic checks and update repo truth.

## DoD
- `build_controlled_degrade(...)` no longer accepts caller-shaped `action` / `tool_action` / `outcome`.
- `build_preflight_reject(...)` no longer accepts caller-shaped `action`.
- `BlockBoundaryRequest` / `DegradeBoundaryRequest` no longer carry planner decision action shaping.
- Ignore/reject behavior still works through boundary outcomes.
- Deterministic suites are green and `git diff --check` passes.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/core/turn_planner.py truffles-api/app/core/turn_executor.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_reasoning_core.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "preflight or degrade or binding_plan or ignored"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py -k "preflight or duplicate_message or sender_branch or remote_branch_phone"`
- `git diff --check`

## Evidence
- TP update
- deterministic pytest outputs
- repo truth update in `STATE.md`

## Release Safety
- local worktree only
- no rollout / no deploy
- rollback by reverting touched files

## Rollback
- revert files in touch-list

## No-go
- no new semantic hardcode
- no new planner compatibility control branches
- no weakening of typed binding or boundary observability
- no doc-only closeout without authority reduction

## Risks / Blockers
- reasoning-core helper tests may rely on old request signatures
- some older tests may implicitly assume synthetic planner action mirrors ignore vs reject

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Synthetic boundary decisions still carry compatibility `intent` and `interaction` fields.
- `PolicyDecision` still contains compatibility `outcome` / `tool_action` fields.

### Why not in this block
- This block is bounded to removing caller-shaped planner control fields, not deleting the remaining compatibility shell.

### Risk if deferred
- Planner synthetic envelopes stay fixed-shape now, but compatibility fields still exist and can confuse future readers until later shrink passes.

### Linked follow-up Task Package(s)
- `TP-2026-03-27-consultant-core-workstream4-planner-executor-closeout-proof-pass-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if any new runtime path starts reading synthetic `intent` / compatibility fields as live control authority.

## Next-block Contract (mandatory)
### Next block objective
Replay a deterministic closeout envelope for Workstream 4 and identify any remaining planner/executor control authority beyond fixed synthetic boundary envelopes.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "binding_plan or preflight or degrade or planner"`

### Blocked-by conditions
- This block must first prove boundary requests no longer shape planner decision action.

### Owner role for closure
- Brain / Top Architect
