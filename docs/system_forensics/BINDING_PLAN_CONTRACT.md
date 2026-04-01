# Binding Plan Contract

## Purpose
Explain `BindingPlanV1` in outside-reader language.
This is the typed boundary between semantic meaning and executable action.

## What it is
`BindingPlanV1` answers a different question than `SemanticDecisionV1`:
Given the chosen meaning, what is the authorized executable plan?

It is not allowed to choose new meaning.
It is only allowed to bind meaning to execution.

## Where it lives in code today
- model: `truffles-api/app/core/binding_plan.py`
- runtime contract schema: `contracts/runtime/binding_plan.v1.jsonschema`
- builder: `truffles-api/app/core/policy_tool_projector.py`
- consumers: `truffles-api/app/core/turn_executor.py`, `truffles-api/app/core/runtime_trace_contract.py`, `truffles-api/app/core/turn_journal.py`

## What it contains
At minimum it carries:
- pointer to the prior semantic decision
- binding outcome type
- selected tool or workflow reference
- resolved execution arguments
- authz scope
- timeout policy
- retry policy
- idempotency key
- explicit deny/degrade/handoff reason codes when needed

## Allowed outcomes
`BindingPlanV1` may resolve to:
- `tool_call`
- `workflow_start`
- `workflow_advance`
- `deny`
- `degrade`
- `handoff`

## Boundary law
Binding is allowed to:
- select the registered tool/workflow for the already selected capability
- resolve execution arguments from canonical state and grounding
- apply policy/authz/tenant/channel restrictions
- set execution-level timeout, retry, and idempotency metadata

Binding is forbidden to:
- choose a different capability than the owner chose
- reinterpret user intent
- invent new missing-information semantics
- silently replace a semantic fact request with a broader semantic bundle

## Why it matters
This contract is the cleanest architectural place to keep deterministic safety and execution wiring from turning into a second semantic owner.
If binding grows beyond that role, the system falls back into hidden co-ownership of meaning.

## Current implementation posture
The repo already has a typed `BindingPlanV1` model and builder.
But the binding boundary is still partly compatibility-shaped:
- `build_compat(...)` in `binding_plan.py` still maps older requested outcomes into current binding outcome types
- runtime consumers still live in a mixed migration environment

So the contract is real, but the cutover is still incomplete.

## Why outside researchers should care
This object is the main seam where deterministic safety can stay strong without becoming the system's semantic author.
If reviewers want to challenge the target architecture, this is one of the critical boundaries to evaluate.
