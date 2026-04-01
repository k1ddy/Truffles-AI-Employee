# External Research Packet

## Purpose
Tell outside researchers what this corpus is for, how to read it, and what kind of help is actually needed.

## Current status
- status: `ready_for_external_handoff`
- this packet is now self-contained enough to send outside on its own
- runtime implementation still remains paused until external review is received or explicitly waived


## What researchers should read first
1. `docs/system_forensics/PRIMARY_DEEP_AUDIT_PROGRAM.md`
2. `docs/system_forensics/SYSTEM_CONTEXT_DEEP_AUDIT.md`
3. `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
4. `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
5. `docs/system_forensics/BOUNDARY_DEGRADE_DEEP_AUDIT.md`
6. `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
7. `docs/system_forensics/CODE_TOPOLOGY_DEEP_AUDIT.md`
8. `docs/system_forensics/QUALITY_EVALUATOR_DEEP_AUDIT.md`
9. `docs/system_forensics/PRIMARY_DEEP_AUDIT_CONTRADICTION_REVIEW.md`
10. `docs/system_forensics/EXTERNAL_PACKET_READINESS_REVIEW.md`
11. `docs/system_forensics/INDEX.md`
12. `docs/system_forensics/PRODUCT_CONTRACT.md`
13. `docs/system_forensics/SYSTEM_VERDICT.md`
14. `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
15. `docs/system_forensics/SEMANTIC_DECISION_CONTRACT.md`
16. `docs/system_forensics/BINDING_PLAN_CONTRACT.md`
17. `docs/system_forensics/TURN_JOURNAL_CONTRACT.md`
18. `docs/system_forensics/CONVERSATION_PROJECTION_CONTRACT.md`
19. `docs/system_forensics/END_TO_END_TURN_WALKTHROUGH.md`
20. `docs/system_forensics/TARGET_ARCHITECTURE.md`
21. `docs/system_forensics/MIGRATION_PROGRAM.md`
22. `docs/system_forensics/EVIDENCE_MAP.md`

This list is now an admissible outside-handoff reading order.


## Machine-readable companion
These files exist so external reviewers can parse the packet mechanically instead of reconstructing inventories from prose.
- `docs/system_forensics/artifact_index.json`
- `docs/system_forensics/module_inventory.json`
- `docs/system_forensics/failure_family_registry.json`
- `docs/system_forensics/runtime_path_registry.json`
- `docs/system_forensics/glossary.json`
- `docs/system_forensics/EXTERNAL_REVIEW_QUESTIONNAIRE.md`
- `docs/system_forensics/external_review_questionnaire.json`

## Current outside-send status
The previously named blockers are closed:
1. self-contained root-level summaries now exist for `SemanticDecisionV1`, `BindingPlanV1`, `TurnJournalV1`, and `ConversationProjectionV1`
2. a self-contained end-to-end turn walkthrough now exists
3. archived prompts remain archive-only even though the packet is now ready

## What we want from researchers
1. challenge the current architecture honestly
2. validate or replace the current target architecture if needed
3. propose a stronger fact-side architecture contract
4. explain how to shrink boundary/degrade authority safely
5. propose a realistic migration order, not a rewrite fantasy
6. identify which legacy modules are salvage, adapter-only, or delete candidates

## What earlier external-facing analysis got right
- it correctly identified broad architecture debt
- it already pushed the repo toward governance, observability, and migration realism

## What earlier external-facing analysis got wrong or left incomplete
- it was too fragmented
- it assumed too much internal context
- it did not clearly separate archive evidence from executive packet
- it did not make anti-repeat rules explicit enough

## What not to optimize for
- better wording without architecture change
- one more local runtime branch
- “smartness” without observability and governance
- recommendations that ignore migration reality

## Required output from researchers
Use the questionnaire by question ID (`Q1`..`Q10`).

- current-state diagnosis
- alternative architecture options
- trade-off matrix
- recommended target architecture
- governance model
- migration program
- first extraction block
- salvage/delete map
- residual unknowns

## Supporting archive
Detailed evidence remains in:
- `docs/system_forensics/files/`
- `docs/system_forensics/ledgers/`
- `docs/system_forensics/final/`

Do not send `docs/system_forensics/final/EXTERNAL_RESEARCH_PROMPT.md` or `docs/system_forensics/final/NEXT_AGENT_FULL_PROMPT.md` as if they were current packet material. Use the root-level packet plus questionnaire instead.
