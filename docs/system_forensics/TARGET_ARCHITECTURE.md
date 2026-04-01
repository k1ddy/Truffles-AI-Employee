# Target Architecture

## Purpose
Describe the intended end state in terms useful to external researchers and future implementers.

## Current leading direction
The current leading internal direction is still the same broad target recorded in the older forensic program:
- `Governed Semantic Kernel + Durable Action Plane`

This document re-expresses that direction as the current leading target hypothesis for external-facing review. It is not the final unchallengeable answer yet.

## Main layers
1. `semantic kernel`
   - one hot-path semantic owner artifact per turn
   - typed semantic decision, not raw prompt prose as the production contract
2. `binding boundary`
   - deterministic binding from meaning to capabilities/tools/facts
   - explicit degrade and validation, not hidden semantic repair
3. `canonical state layer`
   - turn journal plus conversation projection plus pending-question continuity
4. `fact architecture layer`
   - fact manifest, resolver, renderer, emitted-scope contract
5. `control plane`
   - capability, tool, policy, and lifecycle governance
6. `offline improvement plane`
   - evals, simulation, research, and optional multi-agent experimentation outside the hot path

## Main invariants
- one semantic owner per turn
- one canonical semantic state
- one explicit control path for runtime execution
- packs as data, not core branching
- deterministic layers validate or degrade, but do not become a second owner
- all important decisions remain observable and auditable

## Biggest current asymmetry
Interaction-side contracts already have typed artifacts.
Fact-side contracts do not.
That is why the leading candidate for the first architecture-recovery implementation slice still points to `fact architecture contract materialization` once the remaining outside-readiness blockers are closed.

## Evidence anchors
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/TURN_JOURNAL_V1.md`
- `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
