# TurnJournalV1

Status: `draft-required-for-implementation`
Purpose: define the append-only canonical record of turn-level semantic and execution events.

## Role
`TurnJournalV1` is the canonical append-only journal.
It is the system of record for turn history.

It exists to support:
- auditability
- replay/debugging
- projection rebuilds
- shadow comparison during migration
- explicit causal history without raw chain-of-thought dependence

## Journal Law
1. append-only
2. immutable once written
3. one turn may write multiple ordered events
4. events must be authority-based, not implementation-noise-based
5. the journal is canonical; projections are derived

## Minimal Event Vocabulary
Phase-1 event vocabulary should stay intentionally small.

Allowed initial event families:
- `TurnReceived`
- `SemanticDecisionIssued`
- `BindingPlanIssued`
- `ExecutionStarted`
- `ExecutionCompleted`
- `ExecutionFailed`
- `DegradeIssued`
- `HandoffIssued`
- `ReplyCommitted`

Anything beyond this set requires explicit justification.

## Event Requirements
Every journal event must minimally contain:
- `event_id`
- `schema_version`
- `turn_id`
- `conversation_id`
- `event_type`
- `timestamp`
- `source_component`
- `causal_parent_id` when applicable
- `trace_id`

## What The Journal Must Not Become
Forbidden anti-patterns:
- dumping raw internal noise for every helper branch
- using events as a second prompt log
- encoding peer semantic truths outside the event authority model
- letting compatibility fields become canonical through journal side doors

## Relationship To Projection
`ConversationProjectionV1` is built from `TurnJournalV1`.
Any compatibility or domain-specific view must be rebuildable from journal + projection rules.

## Migration Rule
During migration, journal writes may be shadow writes first.
But once canonical state cutover happens, no peer state surface may outrank the journal.

## Implementation Gate
No Workstream 3 implementation is acceptable unless event vocabulary stays deliberately bounded and authority-based.
