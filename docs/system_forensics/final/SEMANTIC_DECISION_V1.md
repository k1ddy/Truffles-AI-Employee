# SemanticDecisionV1

Status: `draft-required-for-implementation`
Purpose: define the only hot-path semantic meaning artifact that the online runtime may mint per user turn.

## Role
`SemanticDecisionV1` is the single semantic owner output.

It is the only artifact allowed to decide:
- requested outcome
- selected capability
- semantic slot state
- missing information needed to proceed
- grounding requirements
- explicit degrade reason
- explicit handoff reason

It is not allowed to contain concrete tool execution arguments.

## Writer Law
Exactly one component may write `SemanticDecisionV1` for a user turn:
- the semantic owner

No other component may create a second authoritative semantic decision for the same turn.

## Reader Law
The following layers may read `SemanticDecisionV1`:
- binding boundary
- execution runtime
- state writer/projector
- response/handoff composer
- observability/eval layers
- compatibility adapters during migration

Reading is allowed.
Re-authoring meaning is not.

## Forbidden Downstream Mutations
After `SemanticDecisionV1` is emitted, no downstream layer may mutate:
- `capability_id`
- `requested_outcome`
- `semantic_slots`
- `missing_information`
- `degrade_reason_code`
- `handoff_reason_code`
- `grounding_requirements`

If downstream cannot proceed, it must emit:
- explicit deny,
- explicit degrade,
- explicit handoff,
- or explicit execution failure,

but it may not rewrite the semantic decision.

## Minimum Field Set
Minimum required fields:
- `decision_id`
- `schema_version`
- `turn_id`
- `conversation_id`
- `requested_outcome`
- `capability_id`
- `semantic_slots`
- `missing_information`
- `grounding_requirements`
- `needs_human`
- `degrade_reason_code`
- `handoff_reason_code`
- `decision_summary`

Optional but strongly recommended:
- `confidence_band`
- `source_requirements`
- `policy_obligations`
- `continuation_contract`
- `channel_constraints`

## What It Must Not Contain
Forbidden contents:
- raw `tool_args`
- transport-specific reply text
- channel formatting details
- compatibility shadow fields
- planner/executor private repair instructions

## Allowed Follow-On Artifacts
`SemanticDecisionV1` may deterministically produce:
- `BindingPlanV1`
- state events in `TurnJournalV1`
- `ConversationProjectionV1` updates
- response/handoff artifacts
- trace/eval artifacts

## Validation Rules
1. exactly one semantic decision per turn
2. schema-valid before binding starts
3. if `needs_human=true`, handoff reason must be explicit
4. if `requested_outcome=degrade`, degrade reason must be explicit
5. if `missing_information` is empty, downstream may not fabricate new required fields silently
6. `capability_id` must exist in the capability registry once control-plane phase is active

## Migration Rule
During migration, legacy layers may derive compatibility views from `SemanticDecisionV1`, but they may not remain peer semantic truths.

## Implementation Gate
No Workstream 1 implementation is acceptable unless this document is concretized into code/test contracts and post-owner mutation checks.
