# TP-2026-03-30-consultant-core-external-research-corpus-deepening-a922

## Название / цель
Довести `docs/system_forensics/` до self-contained external-research corpus, пригодного для исследователей без доступа к рантайму и чату. Цель блока: не чинить runtime, а глубоко перепаковать и нормализовать уже собранный forensic материал так, чтобы он объяснял систему уровнями выше и одновременно достаточно глубоко для внешней архитектурной помощи.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/WORK_METHOD.md`
- `docs/system_forensics/final/RESEARCH_BRIEF.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/TASK_PACKAGES/TP-2026-03-26-consultant-core-system-forensics-foundation-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-27-consultant-core-target-decision-and-execution-program-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-system-forensics-architecture-recovery-a922.md`

## One web search (mandatory before implementation)
- Query: `site:docs.arc42.org stakeholder quality requirements building block runtime view architecture documentation`
- Date/time (local): `2026-03-30 09:25 +0500`
- Sources opened:
  - `https://docs.arc42.org/section-5/`
- Source quality:
  - official arc42 documentation / primary source
- Ready solutions found:
  - external-facing architecture documentation must separate purpose, quality concerns, building blocks, runtime flows, and risks instead of collapsing them into one progress narrative;
  - documentation meant for outside review must provide clear reading order and explicit stakeholder framing, not only internal hotspot logs.
- Decision (`reuse/integrate/build`): `reuse + integrate + deepen`
  - reuse the existing `files/`, `ledgers/`, and `final/` forensic archive;
  - integrate it into one executive packet at the root of `docs/system_forensics/`;
  - deepen the corpus where earlier external-facing docs were truthful but too fragmented, not self-contained, or not explicit enough about historical mistakes and anti-repeat rules.
- Rejected options:
  - continue treating `docs/system_forensics/final/*` alone as sufficient for outside readers;
  - continue shipping only task-local practical-closure reports for external review;
  - start architecture implementation before the external-research packet is corrected.

## Invariant
- Do not change product runtime behavior.
- Do not run a new practical replay.
- Do not claim product-green or practical closure.
- Do not reopen the second-semantic-owner overclaim.
- Keep `r35f` as the current practical truth.

## Scope
- Audit the current `docs/system_forensics/` corpus as an external-research packet.
- Correct missing top-level executive documents referenced by canon but absent in this worktree.
- Separate executive packet from detailed evidence archive.
- Make the corpus explicitly explain why earlier external-facing analyses still allowed bad implementations.
- Sync canon docs so future work reads the corrected corpus instead of relying on fragmented internal memory.

## Out of scope
- New runtime fixes.
- New deterministic code tests unrelated to doc integrity.
- New quality replay or human-semantic rerun.
- Replacing the existing `files/`, `ledgers/`, or `final/` archive with a new forensic method.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-external-research-corpus-deepening-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-external-research-corpus-deepening-a922.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/WORK_METHOD.md`
- `docs/system_forensics/GLOSSARY.md`
- `docs/system_forensics/PRODUCT_CONTRACT.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
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
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Audit the current corpus for external-research gaps: missing files, mixed narratives, unresolved references, and anti-repeat blind spots.
2. Publish the missing executive packet at the root of `docs/system_forensics/`.
3. Reframe `INDEX.md` so outside readers can distinguish executive packet from detailed evidence archive.
4. Explicitly document why earlier external-facing analyses were insufficient even when they were directionally truthful.
5. Sync `STATE.md` and `STRUCTURE.md` so the corrected corpus becomes canonical.

## Root cause (mandatory)
### Symptom
The repo already contains a broad forensic archive and an external research packet, but the top-level corpus in this worktree is still not ready for outside researchers as one self-contained guide.

### Minimal reproduction
1. Read `docs/PRACTICAL_CLOSURE_ADDENDUM.md` and note that canon already references `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`, `TARGET_ARCHITECTURE.md`, `MIGRATION_PROGRAM.md`, `EVIDENCE_MAP.md`, and `QUALITY_GOVERNANCE_AUDIT.md`.
2. Inspect `docs/system_forensics/` in this worktree and observe that the root-level executive files are absent even though the references exist.
3. Read `docs/system_forensics/INDEX.md`, `docs/system_forensics/final/RESEARCH_BRIEF.md`, and `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`.
4. Observe that the archive is rich, but mixed: hotspot archive, research prompt, target decision, and practical-closure recovery narrative are not yet normalized into one external-reading packet.

### Evidence
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/WORK_METHOD.md`
- `docs/system_forensics/final/RESEARCH_BRIEF.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/final/TARGET_DECISION.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `STATE.md`

### Five Whys
1. Why is the corpus still not ready for external researchers? Because the executive packet is incomplete at the root level.
2. Why is the executive packet incomplete? Because the old archive and the new practical-closure recovery narrative were not fully consolidated in this worktree.
3. Why does that matter? Because outside readers should not have to infer architecture from three different forensic layers and chat memory.
4. Why did earlier external-facing analysis still fail to prevent bad implementation? Because truth existed, but it was fragmented, asymmetrical, and not yet a governing self-contained contract.
5. Why fix this before new runtime work? Because otherwise future implementation will again overfit symptoms while the architecture explanation remains ambiguous.

### Root cause statement
The consultant-core repo already has a broad forensic archive, but the archive is not yet normalized into one self-contained external-research corpus in this consolidation worktree: canon points to missing executive documents, earlier research materials are still layered inconsistently, and the corpus does not yet make the historical mistakes and anti-repeat rules explicit enough to govern future architecture work.

### Fix mechanism
- create the missing top-level executive packet;
- redefine `docs/system_forensics/INDEX.md` around external readers first and archive detail second;
- document earlier external-analysis failure modes and anti-repeat rules explicitly;
- sync canon so this corrected packet becomes the required starting point.

## DoD
- All canon-referenced top-level `docs/system_forensics/*.md` files exist in this worktree.
- `docs/system_forensics/INDEX.md` clearly separates executive packet from evidence archive.
- The corpus explicitly explains what earlier external-facing analyses got right, what they missed, and why later implementations still drifted.
- `STATE.md` records this as a doc-only external-research deepening block with current practical truth unchanged.
- `STRUCTURE.md` registers the new TP/report and the new executive-packet docs.

## Checks
- `python3 - <<'PY'\nfrom pathlib import Path\nroot = Path('docs/system_forensics')\nrequired = [\n    'INDEX.md',\n    'WORK_METHOD.md',\n    'GLOSSARY.md',\n    'PRODUCT_CONTRACT.md',\n    'SYSTEM_VERDICT.md',\n    'RUNTIME_ARCHITECTURE.md',\n    'SEMANTIC_OWNERSHIP_AUDIT.md',\n    'INTERACTION_ARCHITECTURE_AUDIT.md',\n    'FACT_ARCHITECTURE_AUDIT.md',\n    'BOUNDARY_DEGRADE_AUDIT.md',\n    'PACK_RUNTIME_SEPARATION_AUDIT.md',\n    'CODE_TOPOLOGY_AUDIT.md',\n    'FAILURE_FAMILY_ATLAS.md',\n    'ANTI_PATTERN_CATALOG.md',\n    'TARGET_ARCHITECTURE.md',\n    'MIGRATION_PROGRAM.md',\n    'EVIDENCE_MAP.md',\n    'QUALITY_GOVERNANCE_AUDIT.md',\n    'EXTERNAL_RESEARCH_PACKET.md',\n]\nmissing = [name for name in required if not (root / name).exists()]\nif missing:\n    raise SystemExit(f'missing: {missing}')\nprint('external_research_corpus_ok')\nPY`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-30-consultant-core-external-research-corpus-deepening-a922.md`
- updated `docs/system_forensics/*`
- updated `STATE.md`
- updated `STRUCTURE.md`

## Rollback
- Remove the new executive packet docs under `docs/system_forensics/`.
- Remove the new TP/report.
- Revert the doc-only canon updates in `STATE.md` and `STRUCTURE.md`.

## No-go
- Do not start runtime implementation from this block.
- Do not treat the existence of broad docs as proof they are already external-ready.
- Do not silently preserve broken canon references to missing docs.
- Do not collapse the detailed archive into shallow summary prose.

## Risks / blockers
- The corpus may remain too internal if the executive docs only paraphrase old ledgers without explaining architecture and failure modes.
- The root-level executive packet may conflict with older `final/*` language if we do not separate “executive packet” from “legacy archive”.
- Practical-closure and earlier governance-lock/system-forensics lines may use different vocabulary; the deepening block must normalize terminology instead of hiding the mismatch.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- No runtime architecture is fixed by this block.
- The detailed archive still reflects multiple historical phases.
- Product truth remains `r35f` and still is not green.

### Why not in this block
This block is still part of the external-research preparation layer. It exists to make future architecture work legible and disciplined, not to begin the implementation wave.

### Risk if deferred
Outside researchers will continue to read an inconsistent packet, and internal implementation will again restart from partial memory instead of the corrected corpus.

### Linked follow-up Task Package(s)
- next implementation TP after this deepening block should still be the first architecture-recovery runtime slice, but only after the corpus is complete and reviewed
- expected implementation topic remains `fact architecture contract materialization`

### Expiry / trigger to stop deferral
- stop deferral before any new runtime implementation starts
- stop deferral if canon again references missing root-level system-forensics docs

## Next-block contract (mandatory)
### Next block objective
Complete the external-research packet and then, only after review, open the first architecture-recovery implementation slice against the corrected corpus.

### First deterministic check command
`python3 - <<'PY'\nfrom pathlib import Path\nfor name in ['docs/system_forensics/INDEX.md', 'docs/system_forensics/TARGET_ARCHITECTURE.md', 'docs/system_forensics/EVIDENCE_MAP.md', 'docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md']:\n    assert Path(name).exists(), name\nprint('external_packet_prereqs_ok')\nPY`

### Blocked-by conditions
- missing root-level executive docs
- mixed archive/executive narratives not yet normalized
- `STATE.md` and `STRUCTURE.md` not yet synced

### Owner role for closure
Brain / Top Architect
