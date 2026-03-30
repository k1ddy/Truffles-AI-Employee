# TP-2026-03-27-consultant-core-workstream2-typed-binding-first-runtime-read-cut-a922

- Title/goal: Make executor and runtime read typed binding outcomes first wherever `binding_plan` is present, instead of keying those control decisions off compatibility `decision.outcome` / `decision.tool_action`.
- Canon refs: `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` (Workstream 2), `docs/system_forensics/final/BINDING_PLAN_V1.md`, `STATE.md`
- Invariant: semantic meaning remains unchanged; this block only changes which executable carrier runtime/executor trust first.
- Scope: `turn_executor.py`, `consultant_runtime.py`, focused runtime contract tests, factual repo truth updates.
- Out of scope: Workstream 3 state unification, legacy mesh strangler, control plane, LLM quality acceptance.
- Touch-list:
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `STATE.md`
  - `STRUCTURE.md`
- Work mode: implementation

## One web search (mandatory before implementation)
- Query: `python typing Literal official docs`
- Date/time: `2026-03-27 18:44:00 +05`
- Opened sources:
  - `https://docs.python.org/3.13/library/typing.html`
- Found reusable solutions:
  - official typing docs confirm `Literal[...]` is the right static contract for a small closed outcome set and support centralizing outcome readers instead of scattering string comparisons
- Reuse/integrate/build decision:
  - `integrate`
  - Reason: keep outcome interpretation behind a small typed helper layer instead of more raw string branching across runtime/executor
- Rejected variants:
  - more ad-hoc inline string checks: keeps fallback authority smeared across runtime/executor

## Root cause (mandatory)
- Symptom:
  - even after typed binding exists for owner-backed and synthetic boundary paths, runtime/executor still read some control branches from compatibility `decision.outcome` / `decision.tool_action` first.
- Minimal reproduction:
  - `TurnExecutor.execute(...)` still falls back to `decision.outcome` / `decision.tool_action` once outside the owner-backed guard; `ConsultantRuntime._apply_execution_boundary_override(...)` and `_should_activate_handoff(...)` still key off `decision.outcome == "HANDOFF"`.
- Evidence:
  - `truffles-api/app/core/turn_executor.py:263`
  - `truffles-api/app/core/turn_executor.py:299`
  - `truffles-api/app/core/consultant_runtime.py:1006`
  - `truffles-api/app/core/consultant_runtime.py:1025`
- Five Whys:
  1. Why do runtime/executor still consult compatibility fields first? Because typed binding was added incrementally around the owner-backed hot path.
  2. Why is that incomplete? Because any decision that already carries `binding_plan` can still be interpreted through stale compatibility fields.
  3. Why is that risky? Because executable authority remains split between two carriers.
  4. Why does that matter? Because Workstream 2 is supposed to make binding the single executable boundary artifact.
  5. Why hasn't it been closed yet? Because runtime/executor read cleanup has not been consolidated into one cut.
- Root cause statement:
  - Executor and runtime still have compatibility-first reads even when typed binding is already present, so binding boundary authority is only partially enforced.
- Fix mechanism:
  - add small typed outcome readers and switch executor/runtime control branches to prefer `binding_plan` whenever it exists.

## Plan
1. Add typed binding-outcome helpers in executor/runtime.
2. Make executor route by `binding_plan` whenever it is present for handoff/tool-call/workflow-advance reads.
3. Make runtime handoff/collect reads prefer typed binding over compatibility outcome fields.
4. Add focused runtime contract tests and run deterministic checks.

## DoD
- executor prefers `binding_plan` for routing whenever `binding_plan` exists
- runtime handoff/collect reads prefer typed binding when available
- no semantic fields change
- focused deterministic tests pass

## Checks
- `python3 -m py_compile truffles-api/app/core/turn_executor.py truffles-api/app/core/consultant_runtime.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "binding_plan or handoff or collect or boundary_override or contract_action"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `git diff --check`

## Evidence
- focused runtime contract output
- exact files changed
- `STATE.md` update after checks

## Rollback
- revert this TP diff; runtime/executor return to compatibility-first outcome reads.

## No-go
- no new semantic owner path
- no boundary behavior downgrade via silent fallback
- no expansion into state-unification or legacy-mesh scope

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - non-binding compatibility fields still exist on `PolicyDecision`
  - some non-owner legacy callers may still construct decisions without `binding_plan`
- Why not in this block:
  - this block only changes runtime/executor reads when `binding_plan` is already present
- Risk if deferred:
  - executable authority remains split even after typed binding is attached
- Linked follow-up Task Package(s):
  - W2 closeout / remaining non-owner binding fallback deletion
- Expiry/trigger to stop deferral:
  - if new runtime branches read compatibility outcomes before existing `binding_plan`, stop and finish W2 cleanup first

## Next-block contract (mandatory)
- Next block objective:
  - close remaining non-owner binding fallbacks and decide whether Workstream 2 can be marked done
- First deterministic check command:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "binding_plan or boundary or contract_action or tool_execution_projection"`
- Blocked-by conditions:
  - typed-binding-first executor/runtime reads must be green first
- Owner role for closure:
  - Brain / Top Architect


## Implementation result
- `TurnExecutor.execute(...)` now prefers `binding_plan` routing whenever a typed binding plan is present, not only on canonical-owner decisions.
- `TurnExecutor._execute_fact(...)` now prefers `binding_plan` tool-call projections whenever a typed tool-call binding plan is present, and direct policy-info fallback uses the typed binding-first read too.
- `ConsultantRuntime` now prefers typed binding outcomes for handoff/collect reads in `_apply_execution_boundary_override(...)`, `_should_activate_handoff(...)`, `_write_runtime_state(...)`, and `_derive_contract_action(...)`.

## Checks run
- `python3 -m py_compile truffles-api/app/core/turn_executor.py truffles-api/app/core/consultant_runtime.py truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `pass`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "binding_plan or handoff or collect or boundary_override or contract_action"` -> `16 passed`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `83 passed`
- `git diff --check` -> `pass`

## Authority removed
- Executor/runtime no longer keep a separate compatibility-first control path when `binding_plan` is already present.
- Runtime handoff/collect state/action reads now honor typed binding before stale `decision.outcome` residue.

## Residual debt after this block
- Some non-owner legacy callers still create `PolicyDecision` without `binding_plan`.
- `PolicyDecision` compatibility fields still exist and still backstop those legacy callers.
