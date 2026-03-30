# TP-2026-03-27-consultant-core-workstream4-binding-only-executor-routing-cut-a922

## Title / Goal
Collapse executor/runtime control routing to typed `BindingPlanV1` on the active path so planner/executor stop treating `decision.outcome` and `decision.tool_action` as live control authority once governed binding exists.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 1-3 done`, overall program `open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 4 — Planner / Executor Demotion`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`

## One Web Search (mandatory before implementation)
- Query: `Temporal workflow activities separation deterministic execution docs`
- Date/time: `2026-03-27T19:50:23+05:00`
- Opened sources:
  - `https://docs.temporal.io/workflows`
  - `https://docs.temporal.io/activities`
- High-signal source quality:
  - official Temporal docs
- Found reusable idea:
  - workflow/orchestration code should only decide and orchestrate deterministic steps, while activity/execution code performs one well-defined action.
  - docs evidence: workflows define the sequence of steps and must stay deterministic; activities execute a single, well-defined action and larger behavior should be broken into multiple activities.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - repo already has the right substrate (`BindingPlanV1`), so the correct move is to route executor/runtime exclusively from typed binding outcomes instead of inventing a new abstraction.
- Rejected options:
  - keep `decision.outcome` / `decision.tool_action` compatibility fallbacks in executor: rejected because they preserve parallel control authority after binding already exists.
  - move routing authority into `consultant_runtime.py`: rejected because that widens runtime control logic instead of shrinking executor/planner roles.

## Root Cause (mandatory)
### Symptom
`turn_executor.py` and parts of `consultant_runtime.py` still branch on compatibility fields (`decision.outcome`, `decision.tool_action`) even though `BindingPlanV1` is already mandatory on valid active-path decisions.

### Minimal Reproduction
1. Inspect `truffles-api/app/core/turn_executor.py:263-320`.
2. Observe binding-first routing, then fallback routing on `decision.outcome` / `decision.tool_action`.
3. Inspect `truffles-api/app/core/consultant_runtime.py:1478-1485`.
4. Observe runtime handoff/collect predicates still accept `decision.outcome` fallbacks after `binding_plan` is present.

### Evidence
- `truffles-api/app/core/turn_executor.py:263-320`
- `truffles-api/app/core/turn_executor.py:547-576`
- `truffles-api/app/core/turn_executor.py:1189-1201`
- `truffles-api/app/core/consultant_runtime.py:1478-1485`

### Five Whys
1. Why does executor still hold control authority?
   - Because it still switches on `decision.outcome` / `decision.tool_action` after reading binding.
2. Why are those branches still present?
   - Because legacy compatibility routing was kept during the binding migration.
3. Why is that now wrong?
   - Because `Workstream 2` made `binding_plan` mandatory for semantic-owner and synthetic boundary decisions.
4. Why is that dangerous?
   - Because stale compatibility fields can silently override typed binding and recreate planner/executor control ownership.
5. Why does that block `Workstream 4`?
   - Because planner/executor demotion requires executor to execute binding outcomes, not reinterpret meaning/control from compatibility carriers.

### Root Cause Statement
Binding extraction is complete, but executor/runtime still preserve compatibility-first control branches, so execution authority remains split between `BindingPlanV1` and legacy `PolicyDecision` fields.

### Fix Mechanism
Make executor dispatch and runtime collect/handoff predicates binding-only on valid active-path decisions; keep compatibility fields as derived metadata, not live routing authority.

## Invariant
- Semantic ownership stays in `SemanticDecisionV1`.
- `BindingPlanV1` remains the only execution-routing artifact on valid active-path decisions.
- Post-owner mutation guard stays green.
- Explicit `deny` / `degrade` / `handoff` boundary behavior remains observable with reason codes.

## Scope
- Collapse executor dispatch to typed binding outcomes.
- Remove executor-side `info -> tool` control remap fallback when binding already exists.
- Remove runtime collect/handoff predicates that fallback to `decision.outcome` when binding is present.
- Add deterministic regressions and architecture-proof checks for the new binding-only control path.

## Out of Scope
- Full planner synthetic boundary shrink.
- `decision.py` strangler work.
- Durable action plane / workflow engine changes.
- LLM quality acceptance runs.

## Touch-list
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/core/consultant_runtime.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Collapse `TurnExecutor.execute(...)` to binding-only dispatch on valid runtime decisions.
2. Push `_execute_fact(...)` to use `BindingPlanV1` as the executable tool source instead of compatibility remap fallback.
3. Remove runtime collect/handoff fallback predicates that still accept stale `decision.outcome`.
4. Add regressions covering stale-compat-field scenarios.
5. Run deterministic checks and update repo truth.

## DoD
- Executor no longer routes valid active-path decisions by `decision.outcome` / `decision.tool_action` after `binding_plan` is present.
- Runtime handoff/collect predicates are binding-only.
- Existing binding-first tests stay green.
- New regressions prove stale compatibility fields cannot override binding routing.
- `git diff --check` passes.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/core/turn_executor.py truffles-api/app/core/consultant_runtime.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "binding_plan or handoff or collect or fact or tool_action"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `git diff --check`

## Evidence
- Updated TP
- Targeted pytest outputs
- Full deterministic contract suite output for `test_consultant_core_runtime_contracts.py`
- `STATE.md` update with exact authority removed

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert changes in touch-list files.

## No-go
- No new phrase/regex semantic routing.
- No reintroduction of compatibility-first executor control branches.
- No weakening of binding contract or runtime guards.
- No doc-only closeout without code-level authority reduction.

## Risks / Blockers
- Some tests may still manufacture stale `PolicyDecision` compatibility payloads and need explicit `binding_plan` updates.
- Full local realism contour may remain pending if no judge key is available.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Planner still constructs synthetic degrade/preflight `PolicyDecision` envelopes.
- `PolicyDecision` still carries compatibility `outcome` / `tool_action` fields.

### Why not in this block
- This block is bounded to executor/runtime control demotion. Planner synthetic-envelope shrink is the next Workstream 4 family.

### Risk if deferred
- Planner remains a bounded control shaper on synthetic boundary paths, even after executor demotion.

### Linked follow-up Task Package(s)
- `TP-2026-03-27-consultant-core-workstream4-planner-synthetic-boundary-demotion-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if executor demotion lands but planner synthetic decisions still need compatibility control fields for live routing.

## Next-block Contract (mandatory)
### Next block objective
Shrink planner synthetic boundary decisions so degrade/preflight paths carry only boundary/control metadata and typed binding, not extra compatibility control authority.

### First deterministic check command
`PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "preflight or degrade or binding_plan"`

### Blocked-by conditions
- This block must first prove executor/runtime no longer route on compatibility control fields.

### Owner role for closure
- Brain / Top Architect
