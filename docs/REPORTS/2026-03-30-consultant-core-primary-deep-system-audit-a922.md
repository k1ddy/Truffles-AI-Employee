# 2026-03-30 Consultant-Core Primary Deep System Audit (a922)

## Scope
Correct the ordering mistake in the system-forensics program and publish the first fresh primary deep-audit documents before any external-research packet is treated as authoritative.

## Outcome
- Status: `in_progress_first_wave`
- Practical truth: unchanged (`r35f` remains current truth)
- Product closure: still `open`
- Runtime behavior: unchanged

## What changed
1. Explicitly demoted the current external packet from implied outside-ready status to scaffold/draft status pending a fresh primary deep audit.
2. Published a new governing program doc:
   - `docs/system_forensics/PRIMARY_DEEP_AUDIT_PROGRAM.md`
3. Published first-wave fresh deep-audit docs:
   - `docs/system_forensics/SYSTEM_CONTEXT_DEEP_AUDIT.md`
   - `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
   - `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
4. Synced canon so future work reads these as the required next research layer rather than assuming packet completeness.

## Governing conclusion
The earlier packet work was useful as scaffolding, but it was done in the wrong order for a trustworthy external handoff. The system now has a corrected rule: first complete the fresh primary deep audit, then treat the packet as a real external-research deliverable.

## Remaining audit backlog
- boundary/degrade deep audit
- pack/runtime separation deep audit beyond the first fact-side slice
- code topology/authority concentration deep audit
- quality/evaluator architecture deep audit
- final external-readiness review

## Checks
- `primary_deep_audit_docs_ok`
- `packet_status_scaffold_ok`
- `git diff --check`
