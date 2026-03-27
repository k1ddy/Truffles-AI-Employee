# BindingPlanV1

Status: `draft-required-for-implementation`
Purpose: define the deterministic boundary that turns semantic intent into an authorized executable plan without changing meaning.

## Role
`BindingPlanV1` is the output of the binding boundary.

It translates:
- `SemanticDecisionV1`
- capability registry
- policy/authz context
- tenant/channel/runtime constraints

into one of these outcomes:
- direct tool invocation plan
- workflow start/advance plan
- explicit deny
- explicit handoff
- explicit degrade

## Boundary Law
Binding is allowed to:
- choose the registered tool/workflow implementation for the selected capability
- fill arguments from canonical referents/projections
- validate schemas and required fields
- apply authz/policy/tenant/channel restrictions
- set execution-level timeout/retry/idempotency metadata

Binding is forbidden to:
- choose a different capability than the owner selected
- reinterpret intent
- invent new missing-information semantics
- rewrite degrade/handoff reason codes into new semantic meaning

## Minimum Field Set
Minimum required fields:
- `binding_id`
- `schema_version`
- `decision_id`
- `binding_outcome_type`
- `capability_id`
- `selected_tool_or_workflow_ref`
- `authz_scope`
- `resolved_args`
- `timeout_policy`
- `retry_policy`
- `idempotency_key`
- `deny_reason_code`
- `degrade_reason_code`
- `handoff_reason_code`

## Allowed Outcome Types
- `tool_call`
- `workflow_start`
- `workflow_advance`
- `deny`
- `degrade`
- `handoff`

## Required Rules
1. `BindingPlanV1` must always reference one prior `SemanticDecisionV1`
2. if outcome is `deny`, `degrade`, or `handoff`, reason code must be explicit
3. if required args cannot be resolved from canonical state, binding must not silently improvise
4. binding must use authorized registry entries only once control plane is active

## Relationship To Execution
Execution may consume `BindingPlanV1` and produce operational results.
Execution may not reinterpret `BindingPlanV1` as permission to change the original semantic meaning.

## Relationship To Control Plane
Once phase-1 control plane exists, binding must resolve only through:
- capability registry
- tool/workflow registry
- policy packs
- context/tenant constraints

## Migration Rule
Until full cutover, legacy executors may consume derived binding data, but they may not stay meaning owners by virtue of how they bind tools.
