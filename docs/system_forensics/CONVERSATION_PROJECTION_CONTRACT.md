# Conversation Projection Contract

## Purpose
Explain `ConversationProjectionV1` in outside-reader language.
This is the intended primary read model for current conversation state.

## What it is
`ConversationProjectionV1` is the materialized current-state view derived from turn-level history.
It exists so the runtime can read one structured current state instead of reconciling many peer state surfaces each time.

## Where it lives in code today
- model: `truffles-api/app/core/conversation_projection.py`
- journal source: `truffles-api/app/core/turn_journal.py`
- main writer/normalizer seam: `truffles-api/app/core/dialog_state_service.py`
- trace/state exposure: `truffles-api/app/core/runtime_trace_contract.py`

## What it carries
The implemented model already includes the main fields outside reviewers need to know:
- current semantic decision ref
- active capability
- semantic slots
- missing information
- active workflow ref
- pending handoff state
- last reply ref
- compatibility view refs
- current goal
- booking state

It also still carries compatibility-heavy fields such as:
- `semantic_frame`
- `semantic_contract`
- `pending_question_contract`

## Why that dual nature matters
This projection is both promising and revealing.
Promising, because it is the clearest current candidate for one canonical conversation read model.
Revealing, because it still stores canonical-looking data and migration compatibility views together.

That is one of the core truths of the current architecture:
- the typed target exists,
- but migration debt still lives inside the same read model.

## Projection law
The intended law is:
- derive from journaled authority
- keep one primary projection per conversation
- let runtime read this first
- force compatibility views to stay derived and removable

## Current implementation posture
The repo already has:
- the projection model
- projection rebuild logic from journal events
- integration with dialog-state normalization and runtime trace/state transitions

But the cutover is incomplete because:
- several continuity carriers still exist outside the projection
- compatibility fields still coexist inside it
- some readers still merge from other state surfaces as well

## Why outside researchers should care
This contract is where “one canonical state” becomes operational instead of theoretical.
If a proposed target architecture cannot explain how this projection becomes primary while compatibility debt shrinks, it is not yet migration-realistic.
