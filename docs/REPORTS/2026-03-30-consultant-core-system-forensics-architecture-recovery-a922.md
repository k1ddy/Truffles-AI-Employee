# 2026-03-30 Consultant-Core System Forensics And Architecture Recovery (a922)

## Scope
Publish the first self-contained system-forensics corpus for consultant-core so future work is governed by architecture-level analysis instead of reactive family patching.

## Outcome
- Status: `done`
- Practical truth: unchanged (`r35f` remains current truth)
- Product closure: still `open`
- New governing next block: `fact architecture contract materialization`

## What changed
1. Created `docs/system_forensics/` as the canonical external-research corpus.
2. Published self-contained documents for product contract, runtime architecture, semantic ownership, interaction architecture, fact architecture, boundary/degrade behavior, pack/runtime separation, code topology, failure-family atlas, anti-patterns, target architecture, migration, and the external-research packet.
3. Re-anchored the current consultant-core lane to the older architecture-verdict / owner-matrix / redesign-reset work instead of continuing the local patch loop as the default path.
4. Preserved current practical truth `r35f` while changing the next admissible work from direct family patching to architecture-recovery implementation.

## What did not change
- No product runtime behavior changed in this block.
- No fresh replay was run.
- No human-semantic verdict changed.
- No product-green claim was made.

## New canonical corpus
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/PRODUCT_CONTRACT.md`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/INTERACTION_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_AUDIT.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/FAILURE_FAMILY_ATLAS.md`
- `docs/system_forensics/ANTI_PATTERN_CATALOG.md`
- `docs/system_forensics/TARGET_ARCHITECTURE.md`
- `docs/system_forensics/MIGRATION_PROGRAM.md`
- `docs/system_forensics/EVIDENCE_MAP.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md`
- `docs/system_forensics/GLOSSARY.md`

## Governing conclusion
The earlier practical lane correctly mined many failure families and partially recovered the interaction architecture, but the system still lacks a fully governing architecture across fact rendering/composition, boundary/degrade, and orchestration topology. The new corpus is intended to make those gaps explicit and actionable for both internal and external researchers.

## Checks
- required `docs/system_forensics/*` presence check -> `system_forensics_docs_ok`
- `git diff --check`
