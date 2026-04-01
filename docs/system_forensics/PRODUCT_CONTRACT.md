# Consultant Core Product Contract

## Purpose
Explain what the product must do before discussing how the runtime is built.

## Core contract
Every user message must end in one of three product outcomes:
- `FACT`
- `COLLECT`
- `HANDOFF`

## Meaning of each outcome
- `FACT`: a short truthful answer from packs, registries, or verified system data
- `COLLECT`: a bounded follow-up that asks only for still-missing state needed for booking, lookup, or escalation
- `HANDOFF`: explicit transfer to a human queue or manager flow with visible status

## What matters more than wording
- the right outcome
- the right slots/facts being grounded
- continuity with the prior turn
- explicit degrade reasons when the happy path fails
- traceable causal evidence

## Acceptance model
The product is not accepted by byte-identical wording.
It is accepted by:
- correct outcome
- correct semantic grounding
- correct trace/meta
- correct boundary behavior
- acceptable visible behavior on human audit

## Current truth
Current practical truth is still replay `r35f`.
That truth shows:
- no visible human-semantic fail dialogs
- visible weak fact over-composition residue
- deterministic contract lane still not fully green

## Why this matters for external researchers
The main architectural question is not “how do we phrase answers better?”
It is “how do we guarantee the system keeps the right outcome and the right grounded scope as the product grows?”
