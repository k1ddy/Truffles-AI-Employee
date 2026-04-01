# Consultant Core System Verdict

## Executive summary
## Packet status
- status: `ready_for_external_handoff`
- meaning: this verdict is now part of an outside-ready packet; that packet is ready to send, but runtime implementation still remains paused pending external review intake or explicit waiver

Consultant-core is not architecturally random. It has meaningful recovery work, real typed semantic artifacts, strong audit discipline, and a clear product contract. But the architecture is still incomplete and asymmetrical. Interaction-side contracts advanced much further than fact-side contracts, while legacy webhook topology and broad helper surfaces still invite local repairs.

## Current practical truth
- current product truth remains `a922-practical-proof-20260330-r35f`
- `infra_valid=true`
- `semantic_valid=false`
- `human_semantic_valid=false`
- visible product residue: `fact over-composition on location/parking replies`

## What is structurally healthy
1. Product outcomes are explicit: `FACT`, `COLLECT`, `HANDOFF`.
2. The repo distinguishes structural closure from practical closure.
3. Human semantic audit is first-class evidence.
4. Typed runtime contracts already exist:
   - `semantic_decision.v1`
   - `binding_plan.v1`
   - `turn_journal.v1`
   - `conversation_projection.v1`
5. The active runtime spine is now identifiable and narrower than the old webhook monolith.

## What is structurally weak
1. Fact selection/composition/rendering still lack one fully governing contract.
2. Boundary/degrade logic still carries too much meaning-preserving and meaning-shaping responsibility.
3. Legacy webhook modules remain live as compatibility authority surfaces.
4. Data and behavior are still mixed in parts of pack/info composition.
5. Earlier research and forensics were truthful but too fragmented to prevent renewed patch-loop behavior.

## Main architectural blockers
1. Missing fact-side executable architecture
2. Boundary/degrade overreach
3. Legacy orchestration topology that still exposes many live authority seams
4. Mixed archive that previously made outside review and future implementation too dependent on session memory

## Outside-handoff status
The two previously named packet blockers are closed:
1. the packet now contains self-contained root-level summaries of the four typed runtime contracts
2. the packet now contains a self-contained end-to-end turn walkthrough

## Why earlier external-facing analysis was insufficient
1. It was spread across many documents with different audiences and historical phases.
2. It explained system truth well, but did not always act as one governing implementation contract.
3. It was stronger on interaction-side failures than on fact-side architecture.
4. It did not make anti-repeat rules explicit enough for future implementers.

## Required response
Use the fresh deep-audit docs plus the root-level packet together as the current research scaffold.
Treat the older `files/`, `ledgers/`, and `final/` trees as the evidence archive behind them.
The packet is now strong enough for outside handoff. Do not confuse that with product closure or architecture completion.
