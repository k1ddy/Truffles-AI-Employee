# ConversationProjectionV1

Status: `draft-required-for-implementation`
Purpose: define the single primary materialized read model derived from `TurnJournalV1` for runtime use.

## Role
`ConversationProjectionV1` is the primary canonical conversation read model.

It exists so the runtime can efficiently read current state without treating scattered compatibility carriers as peer truths.

## Projection Law
1. derived from `TurnJournalV1`
2. one primary projection per conversation
3. runtime reads this as the main conversation state substrate
4. compatibility views are derived from this projection or the journal, not peer canonical stores

## Minimum Projection Contents
Minimum required fields:
- `conversation_id`
- `projection_version`
- `last_turn_id`
- `current_semantic_decision_ref`
- `active_capability`
- `semantic_slots`
- `missing_information`
- `active_workflow_ref`
- `pending_handoff_state`
- `last_reply_ref`
- `compatibility_view_refs`

## What It Must Not Become
Forbidden anti-patterns:
- a second free-form semantic rewrite surface
- a bag of legacy top-level fields that outrank the journal
- a dumping ground for convenience caches without ownership law

## Compatibility View Rule
Temporary compatibility views may exist during migration, but they must satisfy all of the following:
1. clearly marked as derived
2. rebuildable from journal + projection rules
3. no independent write authority over semantic meaning
4. removable after consumer migration

## Reader / Writer Law
Writers:
- only the canonical state writer/projector

Readers:
- runtime kernel
- binding/runtime execution where needed
- response/handoff composition
- compatibility adapters during migration
- observability/eval tools

No other component may bypass projection law by inventing peer current-state stores.

## Cutover Rule
Canonical-state cutover is not complete until the active runtime reads `ConversationProjectionV1` as the primary state source and all remaining peer continuity surfaces are either:
- derived compatibility views,
- caches,
- or deleted.
