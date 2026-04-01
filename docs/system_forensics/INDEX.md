# Consultant Core System Forensics Index

Status: `open`
Baseline snapshot: `8fb6eb23` at `2026-03-30`

## Purpose
This directory is the scaffold for the future self-contained external-research and architecture-recovery packet for consultant-core.

It now has three layers:
- `primary deep-audit layer` with fresh first-hand system research
- `executive packet scaffold` for outside readers and future implementers, including the machine-readable companion
- `evidence archive` for deep repo-backed verification

## Readiness status
Current status: `ready_for_external_handoff`

What this means:
- the packet has completed first-pass deep audit, contradiction review, and self-containment closure;
- the packet is now ready for outside-research handoff;
- runtime implementation is still paused pending external review intake or explicit waiver.

## What this index fixes
Earlier consultant-core forensics were directionally strong but still hard to use from the outside because:
- the archive was broad but mixed across several historical phases
- the top-level packet was incomplete in this worktree
- canon already referenced executive docs that did not yet exist here
- truth, target architecture, and implementation program were not cleanly separated for external readers

This index corrects that by making the reading order explicit.

## Reading order for external researchers
0. `docs/system_forensics/PRIMARY_DEEP_AUDIT_PROGRAM.md`
1. `docs/system_forensics/SYSTEM_CONTEXT_DEEP_AUDIT.md`
2. `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
3. `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
4. `docs/system_forensics/BOUNDARY_DEGRADE_DEEP_AUDIT.md`
5. `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
6. `docs/system_forensics/CODE_TOPOLOGY_DEEP_AUDIT.md`
7. `docs/system_forensics/QUALITY_EVALUATOR_DEEP_AUDIT.md`
8. `docs/system_forensics/PRIMARY_DEEP_AUDIT_CONTRADICTION_REVIEW.md`
9. `docs/system_forensics/EXTERNAL_PACKET_READINESS_REVIEW.md`
10. `docs/system_forensics/PRODUCT_CONTRACT.md`
11. `docs/system_forensics/SYSTEM_VERDICT.md`
12. `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
13. `docs/system_forensics/SEMANTIC_DECISION_CONTRACT.md`
14. `docs/system_forensics/BINDING_PLAN_CONTRACT.md`
15. `docs/system_forensics/TURN_JOURNAL_CONTRACT.md`
16. `docs/system_forensics/CONVERSATION_PROJECTION_CONTRACT.md`
17. `docs/system_forensics/END_TO_END_TURN_WALKTHROUGH.md`
18. `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
19. `docs/system_forensics/INTERACTION_ARCHITECTURE_AUDIT.md`
20. `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
21. `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
22. `docs/system_forensics/PACK_RUNTIME_SEPARATION_AUDIT.md`
23. `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
24. `docs/system_forensics/FAILURE_FAMILY_ATLAS.md`
25. `docs/system_forensics/ANTI_PATTERN_CATALOG.md`
26. `docs/system_forensics/TARGET_ARCHITECTURE.md`
27. `docs/system_forensics/MIGRATION_PROGRAM.md`
28. `docs/system_forensics/EVIDENCE_MAP.md`
29. `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
30. `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md`
31. `docs/system_forensics/GLOSSARY.md`

## Primary deep-audit layer
- `PRIMARY_DEEP_AUDIT_PROGRAM.md`
- `SYSTEM_CONTEXT_DEEP_AUDIT.md`
- `STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `FACT_RUNTIME_DEEP_AUDIT.md`
- `BOUNDARY_DEGRADE_DEEP_AUDIT.md`
- `PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- `CODE_TOPOLOGY_DEEP_AUDIT.md`
- `QUALITY_EVALUATOR_DEEP_AUDIT.md`
- `PRIMARY_DEEP_AUDIT_CONTRADICTION_REVIEW.md`

## Executive packet
- `PRODUCT_CONTRACT.md`
- `SYSTEM_VERDICT.md`
- `RUNTIME_ARCHITECTURE.md`
- `SEMANTIC_DECISION_CONTRACT.md`
- `BINDING_PLAN_CONTRACT.md`
- `TURN_JOURNAL_CONTRACT.md`
- `CONVERSATION_PROJECTION_CONTRACT.md`
- `END_TO_END_TURN_WALKTHROUGH.md`
- `SEMANTIC_OWNERSHIP_AUDIT.md`
- `INTERACTION_ARCHITECTURE_AUDIT.md`
- `FACT_ARCHITECTURE_AUDIT.md`
- `BOUNDARY_DEGRADE_AUDIT.md`
- `PACK_RUNTIME_SEPARATION_AUDIT.md`
- `CODE_TOPOLOGY_AUDIT.md`
- `FAILURE_FAMILY_ATLAS.md`
- `ANTI_PATTERN_CATALOG.md`
- `TARGET_ARCHITECTURE.md`
- `MIGRATION_PROGRAM.md`
- `EVIDENCE_MAP.md`
- `QUALITY_GOVERNANCE_AUDIT.md`
- `EXTERNAL_PACKET_READINESS_REVIEW.md`
- `EXTERNAL_RESEARCH_PACKET.md`
- `GLOSSARY.md`


## Machine-readable companion
These artifacts let outside researchers parse the packet without rebuilding inventories by hand.

- `docs/system_forensics/artifact_index.json`
- `docs/system_forensics/module_inventory.json`
- `docs/system_forensics/failure_family_registry.json`
- `docs/system_forensics/runtime_path_registry.json`
- `docs/system_forensics/authority_registry.json`
- `docs/system_forensics/compatibility_carrier_inventory.json`
- `docs/system_forensics/dead_surface_registry.json`
- `docs/system_forensics/legacy_caller_surface.json`
- `docs/system_forensics/governance_delta.json`
- `contracts/runtime/fact_manifest.v1.jsonschema`
- `contracts/runtime/fact_contract.v1.jsonschema`
- `docs/system_forensics/glossary.json`
- `docs/system_forensics/EXTERNAL_REVIEW_QUESTIONNAIRE.md`
- `docs/system_forensics/external_review_questionnaire.json`

## Evidence archive
The deeper archive remains canonical evidence behind the executive packet.

### Method
- `docs/system_forensics/WORK_METHOD.md`
- `docs/system_forensics/TEMPLATE_FILE_ANALYSIS.md`

### Hotspot analyses
- `docs/system_forensics/files/`
  - per-file deep analyses of runtime, webhook, state, boundary, and test hotspots

### Cross-cut ledgers
- `docs/system_forensics/ledgers/`
  - control paths
  - semantic owner map
  - truth carriers
  - state surfaces
  - deterministic rewrites
  - cutover dependencies
  - salvageable components
  - do-not-repeat rules

### Older final synthesis and research program archive
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/final/RESEARCH_BRIEF.md`
- `docs/system_forensics/final/RESEARCH_SOURCE_PACK.md`
- `docs/system_forensics/final/RESEARCH_OUTPUT_SCHEMA.md`
- `docs/system_forensics/final/EXTERNAL_RESEARCH_PROMPT.md`
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/TURN_JOURNAL_V1.md`
- `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
- `docs/system_forensics/final/NEXT_AGENT_FULL_PROMPT.md`

## Current governing conclusion
Use the primary deep-audit layer first.
Use the contradiction review and readiness review next.
Use the contract summaries and worked walkthrough as the bridge from deep audit to outside review.
Use the archive third as evidence depth and historical hypothesis material.
Do not start new architecture implementation from chat memory, from one surfaced family, from one archive prompt, or from one hotspot doc alone.
