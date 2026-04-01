# Consultant Core Target Decision

Status: `open`
Purpose: record the archived target hypothesis that previously guided implementation planning. After the fresh primary deep audit, this is no longer the unchallengeable current outside-reader decision.

Archive-layer note: this document now acts as an archived target hypothesis. It may inform the current packet, but it is not the current implementation go-signal and it remains challengeable by outside review.

## Decision
Accepted target architecture:
- `Governed Semantic Kernel + Durable Action Plane`

Accepted online runtime shape:
- bounded single-agent online runtime
- exactly one semantic owner per user turn
- no online multi-agent co-ownership of meaning

Accepted execution direction:
- semantic owner emits one typed `SemanticDecisionV1`
- binding is a separate deterministic boundary via `BindingPlanV1`
- canonical semantic state is append-only `TurnJournalV1` plus one materialized `ConversationProjectionV1`
- compatibility views may exist temporarily, but only as derived projections

Accepted operating model:
- online runtime plane
- control/governance plane
- offline improvement plane

Accepted migration mode:
- semantic strangler
- shadow comparison
- phased authority removal
- no big-bang rewrite

## Why This Decision Is Accepted
1. It directly addresses the repo-backed failure classes:
- split semantic ownership
- fragmented truth carriers
- deterministic post-owner rewrite
- legacy compatibility authority
- runtime-core growth through branching

2. It preserves the strongest invariant already established in canon:
- one semantic owner / one canonical semantic state / one control path

3. It turns future growth into governance and registry work instead of repeated runtime branching.

4. It is migration-realistic from the current spine:
- `consultant_core_v2 -> consultant_runtime -> turn_planner -> intent_service -> turn_executor -> dialog_state_service`

## Accepted As-Is
1. `bounded single-agent online`
2. `multi-agent mainly offline`
3. `first extraction block = SemanticDecisionV1 + BindingGatewayV1`
4. `meaning != binding != execution != persistence`
5. `append-only journal + materialized projection`
6. `control plane is required, not optional`
7. `durable workflows belong to action/runtime execution, not to semantic ownership`

## Accepted With Hardening Required
These are directionally accepted but need stronger contract docs before implementation expands.

1. `SemanticDecisionV1`
- must define writer law, reader law, forbidden mutations, and explicit field ownership

2. `BindingPlanV1`
- must define exactly what binding is allowed to derive and what it is forbidden to reinterpret

3. `TurnJournalV1`
- must keep event vocabulary intentionally small and authority-based

4. `ConversationProjectionV1`
- must define what is canonical projection versus temporary compatibility surface

5. `Minimum Control Plane`
- must start small and authority-critical, not as a giant platform rebuild

## Explicitly Not Accepted
1. `online multi-agent supervisor as default runtime`
- rejected because it recreates semantic co-ownership and governance sprawl

2. `workflow engine as semantic owner`
- rejected because durable execution is the wrong authority boundary for top-level meaning

3. `keep planner/executor/state-service and just improve them`
- rejected because it preserves the wrong long-term authority decomposition

4. `event sourcing everywhere`
- rejected because it turns a useful bounded pattern into uncontrolled complexity

5. `vendor platform first`
- rejected as the primary move because it can rename rather than remove internal semantic fragmentation

## Runtime Plane Decision
The online hot path should converge toward:
1. ingress normalization
2. canonical state load
3. context compilation
4. semantic owner -> `SemanticDecisionV1`
5. binding boundary -> `BindingPlanV1`
6. action runtime / tool execution / workflow start
7. journal append + projection refresh
8. response / handoff composition
9. trace emission

## Control Plane Decision
The control plane must eventually own:
- capability registry
- tool/workflow registry
- policy packs
- context recipes
- model profiles
- tenant/regulatory profiles
- eval suites
- release manifests

But phase 1 must keep this minimal:
- capability registry
- tool/workflow registry
- policy packs
- context recipes

## Offline Improvement Decision
The offline plane is the only place where the system should freely do:
- synthetic stress
- model-routing experiments
- critique loops
- offline multi-agent experiments
- agent-gym style exploration
- prompt/context optimization beyond production safety limits

## Non-Negotiable Invariants For Implementation
1. Only one component may write `SemanticDecisionV1` for a turn.
2. Downstream layers may not mutate semantic meaning fields after owner issuance.
3. Binding may not choose a different capability than the owner chose.
4. State writers may not invent new semantic truths outside journal + projection law.
5. Legacy compatibility surfaces may only read or derive once demoted; they may not retain write authority.
6. Degrade and handoff must be explicit, typed, and reason-coded.

## Immediate Follow-On Documents Required
This target decision is only valid together with:
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/TURN_JOURNAL_V1.md`
- `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`

## Success Condition For This Decision
This document has done its job when future implementation work no longer asks:
- "what architecture are we even building?"
- "should we keep planner/executor as the center?"
- "should online runtime be multi-agent?"
- "is binding part of meaning?"

Those questions are now frozen by this decision.
