# TP-2026-03-27-consultant-core-workstream2-typed-deny-degrade-binding-cut-a922

- Title/goal: Thread explicit typed `deny` / `degrade` binding outcomes through synthetic planner and boundary decisions so boundary control no longer lives only in raw compatibility `tool_action` / `meta` fields.
- Canon refs: `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` (Workstream 2), `docs/system_forensics/final/BINDING_PLAN_V1.md`, `STATE.md`
- Invariant: semantic ownership stays outside deterministic boundary decisions; this block only types executable deny/degrade outcomes.
- Scope: `TurnPlanner` synthetic decision constructors, boundary request builders in `TurnExecutor`, focused runtime contract tests, factual repo truth updates.
- Out of scope: owner-backed semantic extraction, state unification, legacy-mesh strangler, LLM quality acceptance.
- Touch-list:
  - `truffles-api/app/core/binding_plan.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `STATE.md`
  - `STRUCTURE.md`
- Work mode: implementation

## One web search (mandatory before implementation)
- Query: `pydantic model_validator official docs`
- Date/time: `2026-03-27 18:37:00 +05`
- Opened sources:
  - `https://docs.pydantic.dev/2.5/concepts/models/`
- Found reusable solutions:
  - official Pydantic model validation docs confirm it is correct to keep outcome-specific invariants on the typed model and construct specialized artifacts through explicit factory helpers instead of loose dict mutation
- Reuse/integrate/build decision:
  - `integrate`
  - Reason: keep outcome validation inside `BindingPlanV1` and add explicit constructors for synthetic `deny` / `degrade` plans
- Rejected variants:
  - attach raw `binding_plan` dicts in planner meta only: preserves untyped boundary control and weakens the contract

## Root cause (mandatory)
- Symptom:
  - owner-backed routing now follows typed binding outcomes, but synthetic boundary decisions still encode deny/degrade control only in compatibility `tool_action`, boundary overrides, and `meta.reason_code`.
- Minimal reproduction:
  - `TurnPlanner.build_preflight_reject(...)` and `TurnPlanner.build_controlled_degrade(...)` return `PolicyDecision` without `binding_plan`, while `TurnExecutor.build_*_boundary_artifact_from_request(...)` still depends on those synthetic decisions.
- Evidence:
  - `truffles-api/app/core/turn_planner.py:683`
  - `truffles-api/app/core/turn_planner.py:712`
  - `truffles-api/app/core/turn_executor.py:1545`
  - `truffles-api/app/core/turn_executor.py:1581`
- Five Whys:
  1. Why are boundary decisions still untyped at the binding layer? Because synthetic planner constructors never started emitting `BindingPlanV1`.
  2. Why not? Because Workstream 2 first cut only targeted owner-backed hot-path FACT execution.
  3. Why is that a problem now? Because boundary deny/degrade still bypass the typed binding contract.
  4. Why does that matter? Because execution control remains split between typed binding and raw compatibility surfaces.
  5. Why is that wrong? Because Workstream 2 is supposed to make the binding boundary the single executable outcome carrier.
- Root cause statement:
  - Synthetic deny/degrade planner paths still bypass `BindingPlanV1`, so boundary execution authority is only partially extracted from compatibility fields.
- Fix mechanism:
  - add explicit typed `deny` / `degrade` binding-plan constructors, attach them in synthetic planner decisions, and prove boundary artifact builders preserve them end-to-end.

## Plan
1. Add explicit `BindingPlanV1` constructors for synthetic `deny` / `degrade` outcomes.
2. Attach typed binding plans in `TurnPlanner.build_preflight_reject(...)` and `TurnPlanner.build_controlled_degrade(...)`.
3. Extend runtime contract tests to prove boundary artifact builders preserve typed deny/degrade binding outcomes.
4. Run focused deterministic checks and record factual repo truth.

## DoD
- synthetic preflight reject decisions carry `binding_plan.binding_outcome_type == "deny"`
- synthetic degrade decisions carry `binding_plan.binding_outcome_type == "degrade"`
- boundary artifact builders preserve those typed binding outcomes
- focused deterministic tests pass

## Checks
- `python3 -m py_compile truffles-api/app/core/binding_plan.py truffles-api/app/core/turn_planner.py truffles-api/app/core/turn_executor.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "binding_plan and (deny or degrade or preflight_reject or boundary_artifact)"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `git diff --check`

## Evidence
- focused runtime contract output
- exact files changed
- `STATE.md` update after checks

## Rollback
- revert this TP diff; synthetic boundary decisions return to compatibility-only routing metadata.

## No-go
- no new semantic owner path
- no regex/phrase routing in core
- no broad boundary refactor beyond typed binding outcome propagation

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - non-owner compatibility execution still exists outside the synthetic deny/degrade cut
  - typed authz/timeout/retry policy remains mostly empty/default
- Why not in this block:
  - this block only closes typed boundary outcome carriage for synthetic planner decisions
- Risk if deferred:
  - boundary execution remains split between typed and untyped carriers
- Linked follow-up Task Package(s):
  - next W2 block for remaining non-owner binding fallbacks / boundary read cleanup
- Expiry/trigger to stop deferral:
  - if any new boundary path is added without typed binding outcome carriage, stop and finish W2 before moving on

## Next-block contract (mandatory)
- Next block objective:
  - remove remaining non-owner binding fallbacks and make executor/boundary readers consume typed binding outcomes first everywhere they are available
- First deterministic check command:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "binding_plan or boundary or tool_execution_projection"`
- Blocked-by conditions:
  - synthetic deny/degrade binding plans must be green first
- Owner role for closure:
  - Brain / Top Architect


## Implementation result
- Added explicit `BindingPlanV1.build_deny(...)` and `BindingPlanV1.build_degrade(...)` constructors for synthetic boundary outcomes.
- `TurnPlanner.build_preflight_reject(...)` now attaches typed `binding_plan` with `binding_outcome_type="deny"`.
- `TurnPlanner.build_controlled_degrade(...)` now attaches typed `binding_plan` with `binding_outcome_type="degrade"`.
- Boundary artifact builders now preserve those typed synthetic binding outcomes end-to-end because they operate on planner-built `PolicyDecision` objects that already carry the binding plan.

## Checks run
- `python3 -m py_compile truffles-api/app/core/binding_plan.py truffles-api/app/core/turn_planner.py truffles-api/app/core/turn_executor.py truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `pass`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "binding_plan and (deny or degrade or preflight_reject or boundary_artifact)"` -> `1 passed`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `80 passed`
- `git diff --check` -> `pass`

## Authority removed
- Synthetic boundary deny/degrade control is no longer carried only by raw compatibility `tool_action` / `meta.reason_code`; the typed binding boundary now carries those executable outcomes too.

## Residual debt after this block
- Non-owner compatibility routing still exists outside the synthetic boundary cut.
- Typed authz/timeout/retry policy is still mostly default/empty.
