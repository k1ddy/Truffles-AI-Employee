# TP-2026-03-27-consultant-core-workstream2-binding-outcome-routing-cut-a922

- Title/goal: Make typed binding outcomes drive owner-backed execution routing for `handoff` and `collect`, and validate binding-plan outcome consistency against `SemanticDecisionV1`.
- Canon refs: `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` (Workstream 2), `docs/system_forensics/final/BINDING_PLAN_V1.md`, `STATE.md`
- Invariant: semantic ownership stays in `SemanticDecisionV1`; binding only governs executable outcome selection, never meaning.
- Scope: `BindingPlanV1` outcome typing, planner consistency validation, owner-backed executor routing for `handoff`/`collect`, focused contract tests.
- Out of scope: control-plane registries, non-owner fallback delete pass, Workstream 3 state unification, LLM quality acceptance.
- Touch-list:
  - `truffles-api/app/core/binding_plan.py`
  - `truffles-api/app/core/policy_tool_projector.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/tests/test_intent.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `STATE.md`
  - `STRUCTURE.md`
- Work mode: implementation

## One web search (mandatory before implementation)
- Query: `JSON Schema if then else official reference`
- Date/time: `2026-03-27 16:54:40 +05`
- Opened sources:
  - `https://json-schema.org/draft/2020-12/draft-bhutton-json-schema-00`
- Found reusable solutions:
  - official draft confirms `if/then/else` conditional subschemas are the correct way to bind field requirements to outcome types
- Reuse/integrate/build decision:
  - `integrate`
  - Reason: keep using conditional schema constraints and mirror the same outcome-consistency rules in planner validation
- Rejected variants:
  - separate per-outcome schemas right now: too much churn for one boundary cut

## Root cause (mandatory)
- Symptom:
  - `BindingPlanV1` exists, but owner-backed executor routing still mostly follows `decision.outcome` / `decision.tool_action` compatibility fields.
- Minimal reproduction:
  - `truffles-api/app/core/turn_executor.py` still routes top-level execution by `decision.outcome == HANDOFF/FACT` and `decision.tool_action == calendar.book_slot`.
- Evidence:
  - `truffles-api/app/core/turn_executor.py:263`
  - `truffles-api/app/core/turn_executor.py:271`
  - `truffles-api/app/core/turn_executor.py:281`
- Five Whys:
  1. Why does executor still depend on compatibility fields? Because only FACT tool-call routing was switched to `binding_plan`.
  2. Why not collect/handoff? Because binding outcomes were still mostly implicit.
  3. Why are they implicit? Because `build_compat(...)` mapped almost everything to `tool_call`.
  4. Why is that a problem? Because typed binding still does not fully own execution routing.
  5. Why does that matter? Because executor retains control authority that should belong to the binding boundary.
- Root cause statement:
  - Workstream 2 is only half cut: typed binding exists, but its outcome type is not yet the executable routing authority for owner-backed `handoff` and `collect` turns.
- Fix mechanism:
  - make binding outcome type explicit from semantic decision, validate it in planner, and route owner-backed execution by binding outcome before compatibility fields.

## Plan
1. Make `BindingPlanV1` derive explicit outcome types from semantic requested outcome.
2. Validate `binding_plan` outcome consistency against `SemanticDecisionV1` in planner.
3. Route owner-backed executor `handoff` and `collect` via `binding_plan.binding_outcome_type`.
4. Add focused tests for typed collect/handoff routing and mismatch rejection.

## DoD
- owner-backed collect decisions emit `workflow_advance`
- owner-backed handoff decisions emit `handoff`
- planner rejects mismatched binding outcome type
- executor owner-backed routing uses binding outcome type for handoff/collect
- focused deterministic tests pass

## Checks
- `python3 -m py_compile truffles-api/app/core/binding_plan.py truffles-api/app/core/policy_tool_projector.py truffles-api/app/core/turn_planner.py truffles-api/app/core/turn_executor.py truffles-api/tests/test_intent.py truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "binding_plan or handoff or collect"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "binding_plan or handoff or collect or binding_outcome"`
- `git diff --check`

## Evidence
- focused test output
- exact files changed
- `STATE.md` update after checks

## Rollback
- revert this TP diff; owner-backed handoff/collect routing returns to compatibility-field control.

## No-go
- no new semantic owner path
- no regex/phrase routing in core
- no expansion into control plane or state-unification scope

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - non-owner fallback routing still exists
  - `decision.py` remains a compatibility hotspot
- Why not in this block:
  - this block only finishes owner-backed binding outcome control
- Risk if deferred:
  - executor still carries broader compatibility debt outside the owner-backed path
- Linked follow-up Task Package(s):
  - next W2 block for explicit typed deny/degrade binding outcomes
- Expiry/trigger to stop deferral:
  - if owner-backed execution still adds new compatibility routing after this block, stop and continue W2 before other workstreams

## Next-block contract (mandatory)
- Next block objective:
  - type explicit deny/degrade binding outcomes and remove remaining owner-backed executor fallbacks
- First deterministic check command:
  - `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "binding_plan or deny or degrade"`
- Blocked-by conditions:
  - collect/handoff outcome typing and routing must be green first
- Owner role for closure:
  - Brain / Top Architect


## Implementation result
- `BindingPlanV1.build_compat(...)` now emits explicit `binding_outcome_type` values from the owner-requested outcome: `tool_call` for `fact`, `workflow_advance` for `collect`, and `handoff` for `handoff`.
- Planner now validates `binding_plan` outcome consistency against `SemanticDecisionV1` and rejects mismatches with explicit `binding_outcome_conflict`.
- Executor now routes owner-backed `collect` and `handoff` turns by `binding_plan.binding_outcome_type` before compatibility `decision.outcome` / `decision.tool_action` fields.
- `route_llm_policy_core(...)` coverage now proves handoff and collect binding outcomes are typed explicitly on the owner-backed path.

## Checks run
- `python3 -m py_compile truffles-api/app/core/binding_plan.py truffles-api/app/core/policy_tool_projector.py truffles-api/app/core/turn_planner.py truffles-api/app/core/turn_executor.py truffles-api/tests/test_intent.py truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `pass`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "binding_plan or handoff or collect"` -> `5 passed`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "binding_plan or handoff or collect or binding_outcome"` -> `11 passed`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py` -> `80 passed`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` -> `80 passed`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_turn_planner_expected_reply_validation.py` -> `8 passed`
- `git diff --check` -> `pass`

## Authority removed
- Executor no longer decides owner-backed `collect` vs `handoff` routing from compatibility `decision.outcome`; the typed binding boundary now controls those execution branches.
- Planner no longer accepts owner-backed binding plans whose executable outcome conflicts with the semantic owner outcome.

## Residual debt after this block
- Typed `deny` / `degrade` binding outcomes still are not threaded through the owner-backed path.
- Non-owner compatibility routing still exists outside the owner-backed cut.
