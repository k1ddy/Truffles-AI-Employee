# Fact Architecture Audit

## Purpose
Explain the main unresolved structural gap: fact selection, composition, and rendering still do not have one governing executable contract.

## Current product symptom
The practical truth `r35f` is no longer visibly failing on parking grounding, but still shows weak fact over-composition:
- the asked fact is grounded correctly
- adjacent branch facts can still be added too broadly

This is evidence for one broader gap, not a standalone parking bug.

## Current runtime shape
Owner-side grounding can already narrow the request.
But downstream fact rendering still widens scope through legacy helpers.

Direct evidence in code:
- `truffles-api/app/services/demo_salon_knowledge.py:612` builds combined location/hours/parking replies
- `truffles-api/app/services/demo_salon_knowledge.py:3001` routes `location`, `hours`, and `parking` through that combined reply path
- `truffles-api/app/routers/webhook/info.py:877`
- `truffles-api/app/routers/webhook/info.py:889`
- `truffles-api/app/routers/webhook/info.py:1513`
- `truffles-api/app/routers/webhook/info.py:1648`
- `truffles-api/app/routers/webhook/info.py:2297`
- `truffles-api/app/routers/webhook/info.py:2514`

## Broken invariant
If the user requests one grounded fact, runtime should not widen into sibling facts unless an explicit composition contract allows it.

## What is missing
There is no fact-side equivalent of the interaction-side contract stack.
Missing pieces:
- canonical fact ids and aliases
- allowed standalone vs composite response policy
- emitted fact-scope contract
- resolver/renderer separation
- traceable requested-refs to emitted-refs mapping

## Why earlier analysis was insufficient
The repo already knew there was a parking/location residue.
What it did not yet publish clearly enough was that this residue reveals a missing system-level fact contract, not just a weak scenario family.

## Required external-research question
What is the right fact-side machine-readable artifact and renderer contract that mirrors the interaction-side discipline without introducing a second semantic owner?

## Key evidence anchors
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/REPORTS/2026-03-30-consultant-core-r35f-human-semantic-audit-a922.md`
- `docs/system_forensics/files/app_routers_webhook_info.md`
- `truffles-api/app/services/demo_salon_knowledge.py`
- `truffles-api/app/routers/webhook/info.py`
