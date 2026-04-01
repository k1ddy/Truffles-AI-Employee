# State And Truth Carriers Audit

Status: `open_first_pass`
Purpose: explain how consultant-core currently stores, transports, and reprojects meaning-bearing state.

## What this document covers
This audit focuses on one system question:
If the product wants one semantic owner and one canonical state, where does meaning actually live today?

## Typed artifacts that already exist
### Semantic owner artifact
`truffles-api/app/core/semantic_decision.py`
- defines `SemanticDecisionV1`
- contains requested outcome, intent, semantic slots, missing information, grounding requirements, handoff/degrade signals
Meaning:
- interaction-side architecture has a real typed semantic artifact.
- this is one of the strongest signs that the architecture is recoverable without a rewrite.

### Binding artifact
`truffles-api/app/core/binding_plan.py`
- defines `BindingPlanV1`
- represents deterministic binding outcome type, selected tool/workflow ref, resolved args, deny/degrade/handoff reason codes
Meaning:
- the intended owner/boundary split is not only conceptual; it already has a typed binding artifact.

### Turn journal artifact
`truffles-api/app/core/turn_journal.py`
- defines `TurnJournalV1` and `TurnJournalEventV1`
- records semantic decision, binding, and terminal/projection events
Meaning:
- the repo already has a candidate append-only event carrier for per-turn truth.

### Conversation projection artifact
`truffles-api/app/core/conversation_projection.py`
- defines `ConversationProjectionV1`
- stores current semantic decision ref, active capability, semantic slots, missing information, workflow ref, handoff state, compatibility refs, semantic frame, semantic contract, pending question contract, goal, booking state
Meaning:
- the projection is powerful, but also shows the current duplication problem: it still stores both canonical-looking data and compatibility-looking data together.

## Dialog state as current normalization seam
`truffles-api/app/core/dialog_state_service.py`

### Important models
- `DialogState`
- `CanonicalSemanticState`
- `InteractionState`
- `DialogStateProjections`

### What this file is doing architecturally
It is not just persistence glue.
It performs several meaning-bearing jobs:
- normalizes typed runtime artifacts
- builds conversation projection
- keeps pending-question contract alive
- stores interaction continuation state
- synthesizes compatibility view references
- reconciles semantic contract and pending-question data with older carriers

### Why this matters
This file is one of the main proofs that the system still has more than one truth-carrying surface even after typed artifacts were introduced.
It is simultaneously:
- canonicalization seam,
- projection writer,
- compatibility bridge,
- continuity transport layer.

## Current truth carriers still coexisting
### 1. Typed semantic owner artifact
- `SemanticDecisionV1`

### 2. Planner/runtime compatibility carriers
- `PolicyDecision` fields
- compatibility semantic frame / pending question / semantic contract views

### 3. Dialog state
- `DialogState.semantic_state`
- `DialogState.pending_question_contract`
- `DialogState.interaction_state`
- `DialogState.meta`

### 4. Conversation projection
- `ConversationProjectionV1.semantic_frame`
- `ConversationProjectionV1.semantic_contract`
- `ConversationProjectionV1.pending_question_contract`
- `ConversationProjectionV1.booking_state`
- `ConversationProjectionV1.compatibility_view_refs`

### 5. Session memory and context-manager compatibility surfaces
Visible in `dialog_state_service.py` constants and compatibility refs:
- `session_memory`
- `context_manager`
- `pending_resume`
Meaning:
- pending-question continuity is still spread across typed state and older continuity surfaces.

## Why one-canonical-state is not yet achieved
### Reason 1. Canonical state and compatibility projection are still co-located
The same service builds canonical-looking state and also preserves compatibility projections.
That is practical for migration, but it keeps old truth surfaces alive.

### Reason 2. Pending-question continuity has several homes
The code still carries pending-question semantics through:
- semantic decision missing-information fields
- dialog state pending-question contract
- conversation projection pending-question contract
- expected-reply/context-manager/session-memory compatibility surfaces

### Reason 3. Semantic contract is still mirrored
`ConversationProjectionV1` keeps `semantic_contract` and `semantic_frame` while dialog state also materializes `CanonicalSemanticState`.
That means the system still needs rules for which projection is authoritative in each stage.


## Additional live continuity readers surfaced in the fresh pass
### Runtime trace contract
`truffles-api/app/core/runtime_trace_contract.py`
- encodes owner/binding/action/state transitions into a trace-friendly contract
Meaning:
- observability is itself another truth surface carrying semantic and continuity information.

### Session memory helpers
`truffles-api/app/routers/webhook/session_memory.py`
- still maintain legacy session-memory continuity
Meaning:
- pending-question continuity is not fully contained inside typed runtime artifacts.

### State service handoff/pending snapshots
`truffles-api/app/services/state_service.py`
- persists `pending_resume` snapshots and boundary-side continuity state
Meaning:
- handoff and resume continuity still have their own carrier path.

### Reasoning snapshot builder
`truffles-api/app/services/reasoning_core.py`
- builds merged snapshot views from several carriers
Meaning:
- the repo already documents the coexistence problem in code: some readers still merge several possible sources instead of trusting one canonical state.

## Main verdicts
### Verdict 1. Interaction-side recovery is real
The presence of typed artifacts means the architecture is not hypothetical.
There is already a strong base for a governed interaction-side model.

### Verdict 2. The state layer is still overloaded
`dialog_state_service.py` carries too many responsibilities.
It is the current center of state normalization, compatibility bridging, and projection writing.

### Verdict 3. Multiple truth carriers remain the core continuity problem
The system does not mainly fail because it has no typed state.
It fails because typed state and legacy continuity carriers still coexist and require reconciliation.

### Verdict 4. This is a migration problem, not only a data-model problem
Deleting the old carriers blindly would be unsafe.
But keeping them indefinitely prevents one-canonical-state from becoming operationally true.

## Main blockers surfaced by this audit
- canonical and compatibility state are not fully separated
- pending-question continuity still spans several carriers
- projection objects still store semantic and compatibility views together
- one service (`dialog_state_service.py`) remains a very dense authority seam

## Evidence anchors
- `truffles-api/app/core/semantic_decision.py`
- `truffles-api/app/core/binding_plan.py`
- `truffles-api/app/core/turn_journal.py`
- `truffles-api/app/core/conversation_projection.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/runtime_trace_contract.py`
- `truffles-api/app/services/owner_resolver.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/routers/webhook/trace.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
- `docs/system_forensics/files/app_core_dialog_state_service.md`
- `docs/system_forensics/files/app_core_turn_planner.md`
- `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`
- `docs/system_forensics/ledgers/STATE_SURFACE_INVENTORY.md`
