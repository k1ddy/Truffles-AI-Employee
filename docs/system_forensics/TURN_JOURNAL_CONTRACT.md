# Turn Journal Contract

## Purpose
Explain `TurnJournalV1` in outside-reader language.
This is the intended append-only record of what the system decided and did for a turn.

## What it is
`TurnJournalV1` is the canonical event history for turn-level semantic and execution state.
It is meant to support:
- auditability
- replay and debugging
- projection rebuilds
- migration shadow comparison
- explicit causal traceability without relying on hidden chain-of-thought

## Where it lives in code today
- model: `truffles-api/app/core/turn_journal.py`
- related trace contract: `truffles-api/app/core/runtime_trace_contract.py`
- projection consumer: `truffles-api/app/core/conversation_projection.py`
- state writer integration: `truffles-api/app/core/dialog_state_service.py`

## Event law
The journal is intended to be:
- append-only
- immutable once written
- small in vocabulary
- authority-based rather than helper-noise-based

## Current event families
The implemented event vocabulary already points to the target shape:
- `SemanticDecisionIssued`
- `BindingPlanIssued`
- terminal execution-style events such as `ExecutionCompleted`, `ExecutionFailed`, `DegradeIssued`, `HandoffIssued`

This is intentionally narrower than logging every helper branch.

## Why it matters
Without a bounded canonical journal, the system has to reconstruct history from scattered state carriers and ad hoc trace events.
With it, outside reviewers can reason about what the runtime believed happened, in what order, and from which authority.

## Current implementation posture
The repo already defines:
- `TurnJournalEventV1`
- `TurnJournalV1`
- journal-event builders keyed off the current `PolicyDecision`, `BindingPlanV1`, and projection state

So the journal is not a pure theory.
But it is still early:
- some runtime truth still lives outside the journal
- many compatibility carriers remain live
- the active runtime is not yet reading one journal-derived state model everywhere

## Why outside researchers should care
This contract is the clearest current candidate for auditable causal history.
It is also a key check against architecture proposals that would add more opaque co-owners or more hidden mutable state.
