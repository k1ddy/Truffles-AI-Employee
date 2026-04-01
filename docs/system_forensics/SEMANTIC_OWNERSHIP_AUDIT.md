# Semantic Ownership Audit

## Purpose
Explain where semantic ownership is already strong, where it is partial, and where hidden co-ownership risks still remain.

## What is already true
The system has a real single-owner direction:
- the policy-core path in `intent_service` is the intended semantic owner
- typed `semantic_decision.v1` exists
- current practical truth does not prove a second semantic owner

## What is not yet fully true
Single ownership is not yet complete in the strong architectural sense.
Why:
- planner and executor still reconstruct semantic-adjacent artifacts
- legacy modules still influence continuity and visible responses
- fact composition can still broaden grounded requests downstream

## Important distinction
`practical truth` and `architecture truth` are different questions.

Practical truth today says:
- current evidence does not prove a second semantic owner

Architecture truth still says:
- multiple downstream layers remain too semantically heavy
- so single-owner invariants are not yet fully compiled into the whole system

## Main residual risks
1. post-owner semantic reconstruction in planner/executor
2. continuity logic split across canonical state and compatibility carriers
3. fact reply broadening after valid owner grounding
4. legacy webhook modules preserving domain-specific side behavior

## Why earlier analysis still failed to govern implementation
The repo already knew semantic ownership was incomplete, but that finding lived mainly in hotspot docs and target-decision materials. It was not yet converted into one external-facing explanation with concrete anti-repeat rules for future implementers.

## Key evidence anchors
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/ledgers/SEMANTIC_OWNER_MAP.md`
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/files/app_services_intent_service.md`
- `docs/system_forensics/files/app_core_turn_planner.md`
- `docs/system_forensics/files/app_core_turn_executor.md`
