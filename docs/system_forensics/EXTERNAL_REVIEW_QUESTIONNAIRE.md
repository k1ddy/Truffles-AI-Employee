# External Review Questionnaire

## Purpose
Give outside researchers one explicit response contract so they can return architecture help in a comparable, decision-ready format.

## Response rules
- Answer by question ID (`Q1`..`Q10`).
- Separate `current-state diagnosis` from `target-state recommendation`.
- Mark low-confidence claims explicitly.
- Prefer evidence-backed criticism over broad rewrite rhetoric.
- Include tradeoffs and migration consequences, not only ideal-state diagrams.

## Required output sections
1. current-state diagnosis
2. architecture options
3. recommended target architecture
4. migration program
5. salvage/delete map
6. quality governance program
7. unknowns and risks

## Questions
### Q1. Current-state diagnosis
What is the simplest accurate architecture description of the system today, including runtime spine, legacy mesh, and main authority seams?
Expected answer:
- one-paragraph diagnosis
- top three authority seams
- main evidence references
Suggested inputs:
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`

### Q2. Semantic ownership assessment
Is the single semantic owner direction viable as the governing architecture, and what exact constraints are needed so deterministic layers do not become a second owner?
Expected answer:
- viability verdict
- required constraints
- failure modes if constraints are ignored
Suggested inputs:
- `docs/system_forensics/SEMANTIC_OWNERSHIP_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`

### Q3. Fact-side architecture
What fact-side architecture object is missing today, and what should replace the current mixed fact selection/composition/rendering behavior?
Expected answer:
- missing contract diagnosis
- recommended fact-side components
- migration entry slice
Suggested inputs:
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_AUDIT.md`

### Q4. State and truth carriers
How should semantic state, pending-question continuity, and projections be normalized so multiple truth carriers stop fighting each other?
Expected answer:
- canonical state model
- projection rules
- what to delete or demote
Suggested inputs:
- `docs/system_forensics/INTERACTION_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/ledgers/TRUTH_CARRIER_MATRIX.md`

### Q5. Boundary and degrade authority
What should the deterministic boundary be allowed to do, and what should it be forbidden from doing?
Expected answer:
- allowed actions
- forbidden actions
- observability requirements
Suggested inputs:
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`

### Q6. Module salvage and deletion
Which live modules are salvageable, adapter-only, or delete candidates, and in what order should they be treated?
Expected answer:
- salvage list
- adapter-only list
- delete-candidate list
- ordering rationale
Suggested inputs:
- `docs/system_forensics/module_inventory.json`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`

### Q7. Migration program critique
Is the current migration order realistic, and what should be reordered, split, or added?
Expected answer:
- phase critique
- revised ordering if needed
- blocked-by dependencies
Suggested inputs:
- `docs/system_forensics/MIGRATION_PROGRAM.md`
- `docs/system_forensics/runtime_path_registry.json`

### Q8. Quality governance
What additional governance, acceptance, or evidence rules are needed so future work does not regress into patch-loop behavior?
Expected answer:
- missing governance rules
- recommended machine-readable evidence
- review process changes
Suggested inputs:
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- `docs/system_forensics/failure_family_registry.json`

### Q9. Unknowns and research gaps
What important unknowns remain even after reading this packet, and what repo/runtime evidence would reduce them?
Expected answer:
- unknown list
- why each unknown matters
- best next evidence for each
Suggested inputs:
- `docs/system_forensics/EVIDENCE_MAP.md`
- `docs/system_forensics/artifact_index.json`

### Q10. First implementation slice recommendation
Assuming no rewrite fantasy, what should the first architecture-recovery implementation slice be, and what must it prove?
Expected answer:
- slice choice
- why first
- proof plan
- rollback and risk notes
Suggested inputs:
- `docs/system_forensics/TARGET_ARCHITECTURE.md`
- `docs/system_forensics/MIGRATION_PROGRAM.md`
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`

## Machine-readable companion
- `docs/system_forensics/external_review_questionnaire.json`
- `docs/system_forensics/artifact_index.json`
- `docs/system_forensics/module_inventory.json`
- `docs/system_forensics/failure_family_registry.json`
- `docs/system_forensics/runtime_path_registry.json`
- `docs/system_forensics/glossary.json`
