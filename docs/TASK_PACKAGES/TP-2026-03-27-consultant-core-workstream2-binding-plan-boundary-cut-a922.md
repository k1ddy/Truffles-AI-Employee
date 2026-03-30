# TP-2026-03-27-consultant-core-workstream2-binding-plan-boundary-cut-a922

- Title/goal: Introduce `BindingPlanV1` on the owner-backed hot path and make executor consume binding output instead of re-selecting tools and re-projecting args from semantic state.
- Canon refs: `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` (Workstream 2), `docs/system_forensics/final/BINDING_PLAN_V1.md`, `STATE.md` (Workstream 1 done, program open)
- Invariant: `SemanticDecisionV1` remains the only meaning owner; binding may derive execution data but may not reinterpret capability/intent.
- Scope: owner-backed planner/executor binding path; typed binding artifact; runtime guard for missing binding plan; focused contract tests.
- Out of scope: control-plane registry rollout, state unification, legacy mesh delete pass, LLM quality acceptance.
- Touch-list:
  - `truffles-api/app/core/binding_plan.py`
  - `truffles-api/app/core/__init__.py`
  - `truffles-api/app/core/policy_tool_projector.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/consultant_runtime.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/services/intent_service.py`
  - `contracts/runtime/binding_plan.v1.jsonschema`
  - `contracts/runtime/policy_decision.v1.jsonschema`
  - `truffles-api/tests/test_intent.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- Work mode: implementation

## One web search (mandatory before implementation)
- Query: `Pydantic v2 discriminated unions official docs`
- Date/time: `2026-03-27 16:39:08 +05`
- Opened sources:
  - `https://docs.pydantic.dev/latest/concepts/unions/`
- Found reusable solutions:
  - Pydantic recommends discriminated unions for predictable tagged variants.
- Reuse/integrate/build decision:
  - `build`
  - Reason: current binding cut only needs one flat typed artifact with an explicit outcome field, not a nested tagged union tree. A single `BaseModel` keeps schema/test churn bounded while still giving a typed boundary.
- Rejected variants:
  - full discriminated-union hierarchy now: more schema churn than needed for the first boundary cut.

## Root cause (mandatory)
- Symptom:
  - binding is still a raw dict and executor still chooses/reinterprets executable tool behavior on the owner-backed FACT path.
- Minimal reproduction:
  - owner path returns semantic payload plus raw `binding`; planner stores `tool_action/tool_args`; executor remaps `info -> catalog.*` and reprojects args from `semantic_contract`.
- Evidence:
  - `truffles-api/app/services/intent_service.py:3139`
  - `truffles-api/app/core/turn_planner.py:757`
  - `truffles-api/app/core/turn_executor.py:511`
  - `truffles-api/app/core/turn_executor.py:1116`
- Five Whys:
  1. Why can executor still choose tools? Because binding is not a first-class typed artifact.
  2. Why is binding not first-class? Because planner only consumes a raw `binding` dict.
  3. Why does executor reproject args? Because resolved args are not treated as canonical binding output.
  4. Why is that allowed? Because `PolicyDecision` carries compatibility `tool_action/tool_args` but no governed binding contract.
  5. Why does that matter? Because binding authority still leaks into executor behavior.
- Root cause statement:
  - Workstream 1 extracted semantic ownership, but binding remained an untyped compatibility payload, so executor retained binding authority on the hot path.
- Fix mechanism:
  - Introduce typed `BindingPlanV1`, require it on owner-backed decisions, derive compatibility `binding` from it, and make executor consume it directly.

## Plan
1. Add `BindingPlanV1` contract/model and thread it through owner-backed planner output.
2. Make `route_llm_policy_core(...)` produce `binding_plan` plus derived compatibility `binding`.
3. Make planner require/validate binding plan on owner-backed path and add a missing-binding guard.
4. Make executor consume `binding_plan` on owner-backed FACT execution instead of re-selecting tools / re-projecting args.
5. Update focused contract/schema tests.

## DoD
- Owner-backed `PolicyDecision` carries typed `binding_plan`.
- Runtime degrades explicitly if owner-backed decision lacks `binding_plan`.
- Executor owner-backed FACT path uses binding plan as execution authority.
- Policy/executor info-tool remap no longer happens in executor for owner-backed path.
- Deterministic contract tests pass.

## Checks
- `python3 -m py_compile truffles-api/app/core/binding_plan.py truffles-api/app/core/policy_tool_projector.py truffles-api/app/core/turn_planner.py truffles-api/app/core/consultant_runtime.py truffles-api/app/core/turn_executor.py truffles-api/app/services/intent_service.py truffles-api/tests/test_intent.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "binding_plan or route_llm_policy_core or tool_args_sanitized"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "binding_plan or semantic_decision_required or semantic_enrichment or tool_execution_projection"`
- `git diff --check`

## Evidence
- updated runtime schemas
- focused pytest output
- exact files changed
- `STATE.md` update after checks

## Rollback
- revert this TP diff; owner path falls back to current raw binding dict behavior.

## No-go
- no phrase/regex semantic routing in core
- no new second owner path
- no acceptance/quality bar weakening
- no legacy compatibility authority increase in executor

## Risks/blockers
- tests and helper builders that assert raw `binding` or executor-side projection may need compatibility updates.

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - `decision.py` remains a large compatibility hotspot.
  - state canonicalization still has legacy fallback paths for non-owner state hydration.
- Why not in this block:
  - this block is only binding authority extraction.
- Risk if deferred:
  - large legacy files still increase maintenance risk, but they no longer own hot-path meaning.
- Linked follow-up Task Package(s):
  - next W2 block for typed deny/handoff/degrade binding outcomes
  - later W5 strangler on `decision.py`
- Expiry/trigger to stop deferral:
  - if executor still needs new binding-specific branching after this cut, stop and continue W2 before other workstreams.

## Next-block contract (mandatory)
- Next block objective:
  - finish W2 by typing explicit deny/handoff/degrade binding outcomes and removing remaining executor-side binding fallbacks.
- First deterministic check command:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "binding_plan or deny or handoff or degrade"`
- Blocked-by conditions:
  - this block must land with owner-backed binding plan and green focused contract tests.
- Owner role for closure:
  - Brain / Top Architect

## Implementation result
- Added typed `BindingPlanV1` in `truffles-api/app/core/binding_plan.py` and schema in `contracts/runtime/binding_plan.v1.jsonschema`.
- `route_llm_policy_core(...)` now emits `binding_plan` plus compatibility `binding` derived from the typed artifact.
- Planner now stores `binding_plan` on owner-backed `PolicyDecision`, auto-derives compatibility `tool_action/tool_args` from it, and rejects missing plan payloads via explicit guard.
- Runtime now degrades explicitly on owner-backed `missing_binding_plan`.
- Executor owner-backed FACT path now consumes `binding_plan` directly and records `tool_execution_projection` with `projection_source="binding_plan.v1"`.

## Checks run
- `python3 -m py_compile truffles-api/app/core/binding_plan.py truffles-api/app/core/__init__.py truffles-api/app/core/policy_tool_projector.py truffles-api/app/core/turn_planner.py truffles-api/app/core/consultant_runtime.py truffles-api/app/core/turn_executor.py truffles-api/app/services/intent_service.py truffles-api/tests/test_intent.py truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `pass`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py` -> `79 passed`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `77 passed`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_turn_planner_expected_reply_validation.py` -> `8 passed`
- `git diff --check` -> `pass`

## Authority removed
- Owner-backed executor no longer re-selects tool execution or re-projects tool args from semantic state on the FACT hot path.
- Raw `binding` dict is no longer the only owner-backed binding artifact; typed `BindingPlanV1` now carries executable binding state.

## Residual debt after this block
- Typed `deny/degrade/handoff` binding outcomes are not fully threaded yet.
- Legacy/non-owner-backed executor fallbacks still retain old binding behavior.
