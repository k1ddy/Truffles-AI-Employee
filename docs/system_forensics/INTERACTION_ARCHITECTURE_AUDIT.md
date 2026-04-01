# Interaction Architecture Audit

## Purpose
Explain the parts of the architecture that are already closer to an executable contract for turn meaning and continuity.

## Stronger side of the current architecture
Interaction-side architecture is the most advanced part of the recovery effort.

Repo-backed artifacts already exist for:
- `semantic_decision.v1`
- `binding_plan.v1`
- `turn_journal.v1`
- `conversation_projection.v1`
- `pending_question_contract`
- interaction owner matrix plus resolver surfaces:
  - `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
  - `truffles-api/app/services/owner_resolver.py`

## What this means
The system already has a believable path toward:
- one per-turn semantic owner artifact
- one canonical conversation projection
- one typed continuity contract
- one explicit binding boundary

## Why this side is only partial
1. live runtime and compatibility layers still coexist
2. planner/executor remain semantically thicker than the target end state
3. continuity state still has compatibility bridges and projections
4. older webhook modules still host live interaction behavior

## Architectural implication
Interaction-side work is not wasted.
It is the main proof that broad architecture recovery is possible.
But it is also not enough by itself, because fact-side architecture never reached the same maturity.

## Anti-repeat lesson
Earlier work showed how to build typed interaction contracts, but later implementation still drifted because those lessons were not mirrored on the fact side and were not externalized into one governing packet.

## Key evidence anchors
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/TURN_JOURNAL_V1.md`
- `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
- `docs/system_forensics/files/app_core_turn_planner.md`
- `docs/system_forensics/files/app_core_dialog_state_service.md`
