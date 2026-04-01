# TP-2026-03-30-consultant-core-primary-deep-audit-contradiction-resolution-a922

## Title / purpose
Run the first post-audit consolidation pass over the new consultant-core research corpus: compare the fresh primary deep-audit layer against older archive synthesis/program docs, resolve contradictions explicitly, and decide whether the external packet is actually ready for outside researchers. This block is still doc-only; it exists to stop misleading archive-go-signal behavior before any runtime architecture implementation resumes.

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
- `docs/system_forensics/BOUNDARY_DEGRADE_DEEP_AUDIT.md`
- `docs/system_forensics/PACK_RUNTIME_SEPARATION_DEEP_AUDIT.md`
- `docs/system_forensics/CODE_TOPOLOGY_DEEP_AUDIT.md`
- `docs/system_forensics/QUALITY_EVALUATOR_DEEP_AUDIT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/final/RESEARCH_BRIEF.md`
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/NEXT_AGENT_FULL_PROMPT.md`
- `docs/system_forensics/final/EXTERNAL_RESEARCH_PROMPT.md`

## One web search (mandatory before implementation)
- Query: `site:docs.arc42.org architecture documentation review checklist consistency completeness risks`
- Date/time (local): `2026-03-30 16:03:00 +0500`
- Sources opened:
  - `https://docs.arc42.org/tips/11-3/`
- Source quality:
  - official arc42 documentation / primary source
- Ready solutions found:
  - architecture review must check consistency, completeness, and known risks explicitly instead of assuming that older synthesis stays valid forever;
  - documentation should expose contradictions and review results, not only final preferred direction;
  - review artifacts should distinguish what is stable, what is provisional, and what is blocked.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the fresh primary deep-audit docs as the first-hand evidence base;
  - integrate older archive synthesis only after explicit contradiction review;
  - build two new governing docs: a contradiction review and an external-readiness review.
- Rejected options:
  - treat the archive `final/` program docs as silently still governing;
  - keep the packet status frozen at `scaffold_pending_primary_deep_audit` after all seven deep tracks already exist;
  - send the outside packet before archive contradictions and readiness gaps are written down.

## Invariant
- Do not change runtime behavior.
- Do not run a new practical replay.
- Do not change practical truth (`r35f`).
- Do not call the packet ready unless the review really justifies it.
- Do not leave archive docs in a state where they still silently instruct direct implementation from an obsolete worktree.

## Scope
- Compare the seven fresh deep-audit docs against the older `final/` synthesis/program layer.
- Record explicit contradictions and their resolution.
- Demote archive docs that still imply direct implementation, frozen target certainty, or obsolete worktree instructions.
- Publish one explicit external-packet readiness review with pass/fail criteria.
- Sync canon/scaffold status to the reviewed result.

## Out of scope
- Runtime implementation.
- Product replay/human audit.
- New target-architecture decision.
- Closing the remaining outside-readiness blockers if the review finds them.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-primary-deep-audit-contradiction-resolution-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-primary-deep-audit-contradiction-resolution-a922.md`
- `docs/system_forensics/PRIMARY_DEEP_AUDIT_CONTRADICTION_REVIEW.md`
- `docs/system_forensics/EXTERNAL_PACKET_READINESS_REVIEW.md`
- `docs/system_forensics/PRIMARY_DEEP_AUDIT_PROGRAM.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md`
- `docs/system_forensics/EVIDENCE_MAP.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/TARGET_ARCHITECTURE.md`
- `docs/system_forensics/MIGRATION_PROGRAM.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- `docs/system_forensics/WORK_METHOD.md`
- `docs/system_forensics/artifact_index.json`
- `docs/system_forensics/module_inventory.json`
- `docs/system_forensics/failure_family_registry.json`
- `docs/system_forensics/runtime_path_registry.json`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/final/RESEARCH_BRIEF.md`
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/NEXT_AGENT_FULL_PROMPT.md`
- `docs/system_forensics/final/EXTERNAL_RESEARCH_PROMPT.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`

## Plan
1. Compare older archive claims against the fresh seven-track deep audit and root-level packet scaffold.
2. Publish one contradiction-review doc with explicit resolutions and archive-doc disposition.
3. Publish one outside-readiness review doc with pass/fail criteria and remaining blockers.
4. Demote/archive-mark the misleading `final/` docs that still imply direct implementation or obsolete worktree usage.
5. Sync packet status, reading order, machine-readable manifest, and canon references to the reviewed result.
6. Stop there; no runtime work starts in this block.

## Root cause (mandatory)
### Symptom
The consultant-core corpus now has a wide fresh deep audit, but older archive synthesis/program docs still contain stronger claims than the new audit supports: direct-implementation go-signals, frozen target certainty, and obsolete worktree instructions.

### Minimal reproduction
1. Read the fresh primary deep-audit docs and `PRIMARY_DEEP_AUDIT_PROGRAM.md`.
2. Then read `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`, `TARGET_DECISION.md`, `IMPLEMENTATION_PROGRAM.md`, and `NEXT_AGENT_FULL_PROMPT.md`.
3. Notice that the archive layer still says broad analysis is done, direct implementation can proceed, and an older worktree prompt should be used.
4. Compare that with the new scaffold, which says the packet is not yet ready for outside handoff and implementation must stay blocked until the research corpus is trustworthy.

### Evidence
- `docs/system_forensics/PRIMARY_DEEP_AUDIT_PROGRAM.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/system_forensics/final/NEXT_AGENT_FULL_PROMPT.md`
- `docs/system_forensics/final/EXTERNAL_RESEARCH_PROMPT.md`

### Five Whys
1. Why is the packet still misleading? Because older archive docs still carry stronger go-signal claims than the fresh primary deep audit allows.
2. Why did that happen? Because archive synthesis was written before the current corrected order-of-work and was never explicitly demoted after the deep-audit reset.
3. Why is that dangerous? Because readers can mistake archive target/program docs for current governing instructions.
4. Why does that matter now? Because the whole point of the new corpus is to prevent future implementation from starting from partial memory, obsolete prompts, or premature architecture certainty.
5. Why fix it in a dedicated block? Because contradiction-resolution and readiness review are themselves governance mechanisms; without them the new packet would repeat the same truthful-but-fragmented failure mode as before.

### Broken invariant
The outside-research packet and archive layer must not disagree about whether direct implementation or external handoff is currently allowed.

### Shared mechanism
Research-corpus governance: contradiction-resolution plus packet-readiness review.

### Why the surfaced family belongs to that mechanism
This is not a wording problem in one file. It is a corpus-governance problem where archive synthesis, target hypothesis, implementation program, and operational prompts drifted out of sync with the new deep-audit order.

### Open-world envelope expected to improve after the fix
- future internal readers will not restart implementation from obsolete prompts or frozen archive assumptions;
- external researchers will receive a packet that separates current truth, target hypothesis, archive evidence, and blocked claims clearly;
- the next architecture-recovery implementation wave will start only after the remaining self-contained documentation gaps are explicit.

### Root cause statement
The consultant-core forensic archive accumulated truthful architecture synthesis over time, but after the order-of-work reset it was not explicitly reconciled with the fresh primary deep audit. That left contradictory go-signals in the corpus: the new packet said “research first, readiness later,” while older archive docs still said “analysis finished, implementation may proceed now.”

### Fix mechanism
- publish an explicit contradiction review;
- publish an explicit outside-readiness review;
- demote archive docs that still imply direct implementation or obsolete worktree usage;
- update packet status and canon to the reviewed result.

## DoD
- `docs/system_forensics/PRIMARY_DEEP_AUDIT_CONTRADICTION_REVIEW.md` exists and lists the resolved contradictions.
- `docs/system_forensics/EXTERNAL_PACKET_READINESS_REVIEW.md` exists and gives a clear readiness verdict plus blockers.
- Archive docs that still implied direct implementation or old worktree instructions are explicitly marked as archive-only and non-governing.
- Root-level packet docs and machine-readable manifests use the reviewed packet status consistently.
- `STATE.md` records the contradiction-resolution/readiness result as doc-only truth with `r35f` unchanged.
- `STRUCTURE.md` registers the new TP/report and review docs.

## Checks
- `python3 - <<'PY'`
  `from pathlib import Path`
  `required = [`
  `    'docs/system_forensics/PRIMARY_DEEP_AUDIT_CONTRADICTION_REVIEW.md',`
  `    'docs/system_forensics/EXTERNAL_PACKET_READINESS_REVIEW.md',`
  `]`
  `for path in required:`
  `    assert Path(path).exists(), path`
  `print('primary_deep_audit_contradiction_docs_ok')`
  `PY`
- `python3 - <<'PY'`
  `import json`
  `from pathlib import Path`
  `payload = json.loads(Path('docs/system_forensics/artifact_index.json').read_text())`
  `assert payload.get('packet_status') == 'reviewed_not_ready_for_external_handoff', payload.get('packet_status')`
  `primary = set(payload.get('primary_deep_audit_entrypoints') or [])`
  `assert 'docs/system_forensics/PRIMARY_DEEP_AUDIT_CONTRADICTION_REVIEW.md' in primary`
  `assert payload.get('external_readiness_review', {}).get('status') == 'not_ready'`
  `print('external_packet_review_manifest_ok')`
  `PY`
- `python3 - <<'PY'`
  `from pathlib import Path`
  `checks = {`
  `    'docs/system_forensics/final/TARGET_DECISION.md': 'archived target hypothesis',`
  `    'docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md': 'archive-only implementation hypothesis',`
  `    'docs/system_forensics/final/NEXT_AGENT_FULL_PROMPT.md': 'do not use this prompt as the current starting brief',`
  `    'docs/system_forensics/final/EXTERNAL_RESEARCH_PROMPT.md': 'do not send this archived prompt as the current outside packet',`
  `}`
  `for path, needle in checks.items():`
  `    text = Path(path).read_text()`
  `    assert needle in text, path`
  `print('archive_demotions_ok')`
  `PY`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-30-consultant-core-primary-deep-audit-contradiction-resolution-a922.md`
- `docs/system_forensics/PRIMARY_DEEP_AUDIT_CONTRADICTION_REVIEW.md`
- `docs/system_forensics/EXTERNAL_PACKET_READINESS_REVIEW.md`
- synced packet/canon/archive docs

## Rollback
- Remove the two new review docs and their TP/report.
- Restore prior packet status and archive notes.
- Revert canon/scaffold changes related to contradiction-resolution and readiness review.

## No-go
- Do not claim runtime architecture closure.
- Do not restart implementation in this block.
- Do not call the packet ready if the review still finds self-contained gaps.
- Do not silently leave old worktree/branch instructions active inside archive prompts.

## Risks / blockers
- The packet may still fail readiness even after contradictions are resolved.
- The remaining blockers may require another doc-only block, not runtime work.
- Archive demotion must be careful not to erase historically useful hypotheses.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- Outside packet may still remain not-ready after review.
- Root-level docs may still lack some self-contained contract detail even after contradiction-resolution.
- Runtime architecture remains unrepaired.

### Why not in this block
This block only resolves corpus-governance contradictions and judges readiness. It does not write the next missing deep explanatory docs.

### Risk if deferred
The team or outside readers could again start from obsolete instructions, over-frozen target assumptions, or archive claims that outpace the actual packet quality.

### Linked follow-up Task Package(s)
- if readiness fails: next doc-only block for the exact remaining packet blockers;
- only after packet readiness closes: first architecture-recovery implementation wave.

### Expiry / trigger to stop deferral
- stop deferral before any external handoff;
- stop deferral before any runtime architecture-recovery implementation starts.

## Next-block contract (mandatory)
### Next block objective
If the readiness review still says `not_ready`, close the exact remaining outside-packet blockers before any implementation resumes. Expected first candidates: self-contained typed contract summaries and one end-to-end turn walkthrough.

### First deterministic check command
`python3 - <<'PY'`
`from pathlib import Path`
`for path in [`
`    'docs/system_forensics/PRIMARY_DEEP_AUDIT_CONTRADICTION_REVIEW.md',`
`    'docs/system_forensics/EXTERNAL_PACKET_READINESS_REVIEW.md',`
`]:`
`    assert Path(path).exists(), path`
`print('external_packet_review_docs_present')`
`PY`

### Blocked-by conditions
- contradiction review missing;
- readiness review missing;
- packet status still inconsistent across root docs and machine-readable manifests.

### Owner role for closure
Brain / Top Architect
