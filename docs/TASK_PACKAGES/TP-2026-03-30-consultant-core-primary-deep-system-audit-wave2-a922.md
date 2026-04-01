# TP-2026-03-30-consultant-core-primary-deep-system-audit-wave2-a922

## Title / purpose
Continue the primary deep consultant-core audit after wave 1 and close the remaining research blind spots: boundary/degrade authority, pack/runtime separation, code topology/authority concentration, and quality/evaluator architecture. The goal of this block is to reach fresh repo-backed first-pass coverage for all seven audit tracks without turning the work back into packet-polish or runtime fixes.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/PRIMARY_DEEP_AUDIT_PROGRAM.md`
- `docs/system_forensics/SYSTEM_CONTEXT_DEEP_AUDIT.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_AUDIT.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md`
- `docs/system_forensics/EVIDENCE_MAP.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-primary-deep-system-audit-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-primary-deep-system-audit-a922.md`

## One web search (mandatory before implementation)
- Query: `site:docs.arc42.org risks technical debt quality requirements architecture documentation`
- Date/time (local): `2026-03-30 10:26:31 +0500`
- Sources opened:
  - `https://docs.arc42.org/section-11/`
- Source quality:
  - official arc42 documentation / primary source
- Ready solutions found:
  - architecture research should explicitly list risks and technical debt, not hide them inside narrative prose;
  - the documentation set should organize known problems by priority and by mitigating measures;
  - research should cover source code, interfaces, processes, and data, not only one visible symptom family.
- Decision (`reuse/integrate/build`): `reuse + integrate + deepen`
  - reuse the first-wave deep audit and existing forensic archive;
  - integrate the remaining tracks into the same primary deep-audit layer;
  - deepen the packet only through fresh repo-backed findings, not through more scaffold polish.
- Rejected options:
  - continue treating the executive packet as if it were the research itself;
  - jump into runtime implementation before tracks 4..7 have a fresh first pass;
  - publish outside-facing material while boundary/topology/quality architecture are still only implied.

## Invariant
- Do not change runtime behavior.
- Do not run a new practical replay.
- Do not change practical truth (`r35f`).
- Do not claim outside-handoff readiness.
- Do not use one surfaced family as a substitute for a full system mechanism audit.

## Scope
- Publish the remaining four first-pass primary deep-audit documents.
- Re-derive them from live repo inspection, not from chat memory.
- Sync the packet scaffold so readers are sent to the new deep docs first.
- Keep the packet status as `scaffold_pending_primary_deep_audit` until a later readiness review.

## Out of scope
- Runtime implementation.
- Product replay/human audit.
- Final external-readiness claim.
- Full contradiction-resolution pass against every older archive document.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-primary-deep-system-audit-wave2-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-primary-deep-system-audit-wave2-a922.md`
- `docs/system_forensics/PRIMARY_DEEP_AUDIT_PROGRAM.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md`
- `docs/system_forensics/EVIDENCE_MAP.md`
- `docs/system_forensics/artifact_index.json`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_AUDIT.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_DEEP_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- `docs/system_forensics/CODE_TOPOLOGY_DEEP_AUDIT.md`
- `docs/system_forensics/QUALITY_EVALUATOR_DEEP_AUDIT.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`

## Plan
1. Re-inspect live code and existing forensic archive for tracks 4..7.
2. Publish four new deep-audit docs with exact file-backed evidence.
3. Update the primary-deep-audit program and packet scaffold reading order.
4. Record that all seven audit tracks now have first-pass coverage, while readiness still stays open.
5. Stop there; no runtime work in this block.

## Root cause (mandatory)
### Symptom
After wave 1, the packet had a better structure, but the deep audit still lacked fresh first-hand coverage for boundary/degrade authority, pack/runtime separation beyond the first fact pass, code topology/authority concentration, and quality/evaluator architecture.

### Minimal reproduction
1. Read `INDEX.md` and `EXTERNAL_RESEARCH_PACKET.md` after wave 1.
2. Notice that only three primary deep-audit docs existed.
3. Ask whether the remaining four architecture tracks had been re-derived from the repo with the same first-hand depth.
4. Observe that they had only executive scaffold docs, not fresh primary deep-audit documents.

### Evidence
- `docs/system_forensics/PRIMARY_DEEP_AUDIT_PROGRAM.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_AUDIT.md`
- `docs/system_forensics/CODE_TOPOLOGY_AUDIT.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- live repo files inspected in this block

### Five Whys
1. Why was the packet still insufficient? Because tracks 4..7 existed only as executive summaries.
2. Why is that a problem? Because external readers would still be missing fresh first-hand explanations of the hardest architecture layers.
3. Why do those layers matter most? Because they explain why good audits still allowed bad implementations and why local patching keeps recurring.
4. Why could this repeat old mistakes? Because the missing tracks are exactly where runtime authority, topology debt, and evaluator drift hide.
5. Why fix this now? Because packet readiness cannot be judged honestly until all seven tracks have comparable fresh coverage.

### Broken invariant
The external scaffold must not outpace the fresh primary deep audit that justifies it.

### Shared mechanism
Primary deep system audit before packet readiness.

### Why this surfaced family belongs to that mechanism
The issue is not a wording gap in one document. It is another order-of-work gap: the deep audit had not yet covered all governing system layers.

### Open-world envelope expected to improve after the fix
- external researchers will receive fresh repo-backed first-pass coverage for all major architecture layers;
- future implementation blocks can cite a concrete deep audit instead of extrapolating from one weak family;
- the packet will become a truthful scaffold for outside review instead of a partial summary.

### Root cause statement
Wave 1 corrected the order of work but still left four major system layers without fresh primary deep-audit coverage. That meant the scaffold looked broader than the actual first-hand analysis behind it.

### Fix mechanism
- publish fresh first-pass deep audits for tracks 4..7;
- update the scaffold to point to those docs first;
- keep readiness explicitly open until a later contradiction-resolution and final packet review.

## DoD
- Four new deep-audit docs exist for tracks 4..7.
- `PRIMARY_DEEP_AUDIT_PROGRAM.md` states that tracks 1..7 now have fresh first-pass coverage.
- `INDEX.md`, `EXTERNAL_RESEARCH_PACKET.md`, `EVIDENCE_MAP.md`, and `artifact_index.json` point to the new docs.
- `STATE.md` records the wave-2 deep audit as doc-only truth with `r35f` unchanged.
- `STRUCTURE.md` registers the new TP/report and deep docs.

## Checks
- `python3 - <<'PY'`
  `from pathlib import Path`
  `required = [`
  `    'docs/system_forensics/BOUNDARY_DEGRADE_DEEP_AUDIT.md',`
  `    'docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md',`
  `    'docs/system_forensics/CODE_TOPOLOGY_DEEP_AUDIT.md',`
  `    'docs/system_forensics/QUALITY_EVALUATOR_DEEP_AUDIT.md',`
  `]`
  `for path in required:`
  `    assert Path(path).exists(), path`
  `print('primary_deep_audit_wave2_docs_ok')`
  `PY`
- `python3 - <<'PY'`
  `import json`
  `from pathlib import Path`
  `payload = json.loads(Path('docs/system_forensics/artifact_index.json').read_text())`
  `primary = payload.get('primary_deep_audit_entrypoints') or []`
  `required = {`
  `    'docs/system_forensics/BOUNDARY_DEGRADE_DEEP_AUDIT.md',`
  `    'docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md',`
  `    'docs/system_forensics/CODE_TOPOLOGY_DEEP_AUDIT.md',`
  `    'docs/system_forensics/QUALITY_EVALUATOR_DEEP_AUDIT.md',`
  `}`
  `assert required.issubset(set(primary)), primary`
  `assert payload.get('packet_status') == 'scaffold_pending_primary_deep_audit'`
  `print('primary_deep_audit_wave2_manifest_ok')`
  `PY`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-30-consultant-core-primary-deep-system-audit-wave2-a922.md`
- new deep-audit docs under `docs/system_forensics/`
- synced packet scaffold and canon references

## Rollback
- Remove the four new deep-audit docs and their TP/report.
- Revert scaffold/index/evidence-map updates.
- Restore the prior first-wave-only audit program state.

## No-go
- Do not claim external readiness in this block.
- Do not start runtime architecture implementation from these docs yet.
- Do not overwrite practical truth.
- Do not collapse the new deep docs back into one summary note.

## Risks / blockers
- The new deep docs can still become too shallow if they only restate earlier archive conclusions.
- Contradictions with older archive material are still possible and require a later explicit pass.
- The evaluator/governance stack is large enough that summarization can easily miss real control surfaces.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- Packet status remains scaffold.
- Final contradiction-resolution and readiness review remain open.
- No runtime mechanism has been repaired yet.

### Why not in this block
This block only completes first-pass primary research coverage for the remaining tracks.

### Risk if deferred
The team would again confuse packet completeness with research completeness and would lack a trustworthy basis for outside review.

### Linked follow-up Task Package(s)
- next doc-only block: contradiction-resolution plus external-readiness review over the full primary deep audit;
- only after that may the first architecture-recovery implementation wave start.

### Expiry / trigger to stop deferral
- stop deferral before any outside handoff is called ready;
- stop deferral before any runtime architecture-recovery implementation begins.

## Next-block contract (mandatory)
### Next block objective
Run the final primary-deep-audit consolidation pass: reconcile contradictions with older archive docs, re-derive the executive packet from the now-complete primary deep audit, and decide whether the external packet is actually researcher-ready.

### First deterministic check command
`python3 - <<'PY'`
`from pathlib import Path`
`for path in [`
`    'docs/system_forensics/SYSTEM_CONTEXT_DEEP_AUDIT.md',`
`    'docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md',`
`    'docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md',`
`    'docs/system_forensics/BOUNDARY_DEGRADE_DEEP_AUDIT.md',`
`    'docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md',`
`    'docs/system_forensics/CODE_TOPOLOGY_DEEP_AUDIT.md',`
`    'docs/system_forensics/QUALITY_EVALUATOR_DEEP_AUDIT.md',`
`]:`
`    assert Path(path).exists(), path`
`print('primary_deep_audit_all_tracks_present')`
`PY`

### Blocked-by conditions
- any track 1..7 missing a fresh first-pass deep doc;
- packet scaffold still misstates readiness;
- canon/index/artifact manifest out of sync.

### Owner role for closure
Brain / Top Architect
