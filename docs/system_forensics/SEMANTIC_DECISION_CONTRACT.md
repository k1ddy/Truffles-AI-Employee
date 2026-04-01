# Semantic Decision Contract

## Purpose
Explain `SemanticDecisionV1` in outside-reader language.
This is the single typed meaning artifact that the hot path is trying to converge around.

## What it is
`SemanticDecisionV1` is the owner-issued answer to one question:
What does this user turn mean, at the product-contract level?

It does not execute anything.
It decides the semantic shape of the turn.

## Why it matters
Without this contract, downstream layers can keep inventing their own interpretation of the turn.
With this contract, the architecture has one typed place where meaning is supposed to become explicit.

## Where it lives in code today
- model: `truffles-api/app/core/semantic_decision.py`
- runtime contract schema: `contracts/runtime/semantic_decision.v1.jsonschema`
- hot-path producer entry: `truffles-api/app/services/intent_service.py`
- planner intake: `truffles-api/app/core/turn_planner.py`

## What it decides
At minimum it carries:
- requested outcome: `fact`, `collect`, or `handoff`
- semantic intent
- chosen capability
- semantic slots already known
- missing information still needed
- grounding requirements such as pack refs, entity refs, referents, subject kind, temporal scope, and resolution mode
- whether a human is required
- explicit degrade or handoff reason codes when relevant
- one short decision summary

## What it must not decide
It must not carry:
- concrete tool arguments as the semantic contract
- transport-specific response wording
- channel formatting details
- planner/executor repair instructions

That separation matters because meaning and execution are different authority layers.

## Writer law
Only the semantic owner may mint `SemanticDecisionV1` for a turn.
In the current runtime, that means the policy-core owner path reached through `intent_service.route_llm_policy_core(...)` and then normalized in `turn_planner.py`.

## Reader law
Other layers may read it:
- binding
- execution
- state writing
- response composition
- trace/eval
- migration compatibility adapters

They may not rewrite its meaning fields.

## Current downstream guardrails
The repo already has partial enforcement:
- `truffles-api/app/core/turn_planner.py` coerces owner payload into the typed artifact and rejects invalid projection
- `truffles-api/app/core/consultant_runtime.py` carries post-owner mutation and missing-binding guards
- contract tests and runtime guards already check that owner-backed decisions do not silently fall back into older semantic carriers

## Why outside researchers should care
This contract is the strongest proof that the architecture is not purely heuristic anymore.
It also shows the main remaining challenge: typed ownership exists, but some downstream paths still reconstruct adjacent semantic views around it.

## Current limitation
`SemanticDecisionV1` is real, but it is not yet the only meaning carrier in practice.
Compatibility views and state/projection mirrors still coexist around it.
