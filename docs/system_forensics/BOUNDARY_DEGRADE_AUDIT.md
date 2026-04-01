# Boundary And Degrade Audit

Fresh primary deep-audit companion: `docs/system_forensics/BOUNDARY_DEGRADE_DEEP_AUDIT.md`

## Purpose
Explain where deterministic logic behaves as a proper boundary and where it still holds too much semantic authority.

## What is already good
- boundary logic is observable
- reason codes and trace/meta exist
- practical audits can often reconstruct exact fallback paths

## What remains problematic
1. boundary stages still sometimes reshape continuity instead of only validating it
2. degrade logic remains too close to semantic routing in some legacy paths
3. acceptability of the visible reply can hide deterministic contract debt underneath

## Why this matters
If degrade becomes the normal place where meaning is repaired, the architecture silently grows a second semantic router even when current human-visible behavior looks acceptable.

## Current external-research question
How strict should the boundary contract be so it preserves owner meaning, stays observable, and still gives safe fallback behavior?

## Key evidence anchors
- `docs/system_forensics/ledgers/DETERMINISTIC_REWRITE_LEDGER.md`
- `docs/system_forensics/files/app_core_turn_executor.md`
- `docs/system_forensics/files/app_routers_webhook_response.md`
- `docs/system_forensics/files/app_routers_webhook_guards.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
