# Migration Program

## Purpose
Translate the target architecture into a realistic migration order that reduces authority seams instead of just moving files.

## Phase 0
Finish the external-research packet and make it outside-ready.
This phase is now complete.

## Phase 1
Run outside review intake.
Goal:
- send the outside-ready packet
- collect structured questionnaire answers
- update the executive packet with accepted corrections or challenges
- decide whether the current leading target direction still holds

## Phase 2
Freeze the executive architecture contract and its anti-repeat rules after outside review.
Goal:
- future implementation must cite the governing executive docs, not just hotspot analyses

## Phase 3
Materialize the missing fact-side architecture contract.
Goal:
- canonical fact ids
- standalone/composite policy
- emitted fact scope contract
- fact resolver and renderer seam

## Phase 4
Constrict boundary/degrade authority.
Goal:
- preserve owner meaning without semantic repair drift

## Phase 5
Continue draining live authority from legacy webhook compatibility modules.
Goal:
- reduce `decision.py`, `response.py`, `booking.py`, `info.py`, `context_manager.py` from live mixed-authority hotspots to bounded adapters or delete candidates

## Phase 6
Deduplicate operational caller surfaces where compatibility seams still stay alive for admin/service/worker/console paths.

## Phase 7
Re-run practical proof and human audit against the repaired shared mechanisms, not against one local patch at a time.

## First implementation slice after outside review intake
Leading candidate: `fact architecture contract materialization`

## Why this order
The biggest open product residue and the biggest missing architecture object point to the same gap:
- fact selection / composition / rendering

That makes it the highest-leverage next implementation topic once the outside packet has been reviewed by external researchers or explicitly waived.
