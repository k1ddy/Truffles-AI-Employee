# TP-2026-03-30-consultant-core-primary-deep-system-audit-a922

## Название / цель
Перезапустить consultant-core system forensics в правильном порядке: сначала провести новый первичный глубокий аудит реальной системы по главным механизмам, и только потом считать external packet пригодным для передачи внешним исследователям. Цель блока: исправить ложное ощущение готовности внешнего пакета, зафиксировать что текущий packet пока является scaffold/draft, и начать публиковать новые repo-backed deep-audit документы по реальному устройству системы.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/WORK_METHOD.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- `docs/system_forensics/final/SYSTEM_FINAL_ANALYSIS.md`
- `docs/system_forensics/final/RESEARCH_BRIEF.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-system-forensics-architecture-recovery-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-external-research-corpus-deepening-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-machine-readable-research-companion-a922.md`

## One web search (mandatory before implementation)
- Query: `site:c4model.com software architecture documentation context container component official`
- Date/time (local): `2026-03-30 10:12 +0500`
- Sources opened:
  - `https://c4model.com/diagrams/code`
- Source quality:
  - official C4 model documentation / primary source
- Ready solutions found:
  - outside-facing architecture explanation should separate system/context/container/component levels instead of collapsing everything into code-level detail;
  - code-level detail is optional and should be used only where it helps tell an important story;
  - long-lived architecture material should start from higher-level system views before diving into internal implementation specifics.
- Decision (`reuse/integrate/build`): `reuse + integrate + deepen`
  - reuse the existing forensic archive and newly created packet scaffold;
  - integrate the existing archive into a corrected deep-audit program;
  - deepen the corpus with new system-level mechanism audits before any external handoff is treated as authoritative.
- Rejected options:
  - continue polishing the packet scaffold before doing the primary audit;
  - treat old narrative material as equivalent to fresh primary research;
  - resume runtime implementation before the fresh deep audit exists.

## Invariant
- Do not change runtime behavior.
- Do not run a new practical replay.
- Do not change practical truth (`r35f`).
- Do not claim the external packet is final or researcher-ready until the new primary deep audit exists.
- Do not hide the earlier ordering mistake.

## Scope
- Correct misleading packet framing in canon and top-level system-forensics docs.
- Publish the first new primary deep-audit documents from fresh repo inspection.
- Start with the highest-leverage system views:
  - system context and live control paths
  - state/truth carriers
  - fact/runtime seam
- Record the remaining deep-audit backlog explicitly.

## Out of scope
- Runtime fixes.
- Product replay/human audit.
- Declaring the external packet complete.
- Completing every deep-audit area in one block.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-primary-deep-system-audit-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-primary-deep-system-audit-a922.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- `docs/system_forensics/artifact_index.json`
- `docs/system_forensics/PRIMARY_DEEP_AUDIT_PROGRAM.md`
- `docs/system_forensics/SYSTEM_CONTEXT_DEEP_AUDIT.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`

## Plan
1. Correct the misleading top-level framing: packet scaffold, not final research handoff.
2. Re-read the live code and existing forensic archive for three system-level deep-audit tracks.
3. Publish fresh deep-audit docs with exact file-backed evidence and architectural conclusions.
4. Record which deep-audit areas remain open.
5. Stop there; no runtime work in this block.

## Root cause (mandatory)
### Symptom
The repo now contains a normalized external packet scaffold, but it was being treated as if it were already suitable for external researchers even though a fresh primary deep audit had not been completed first.

### Minimal reproduction
1. Read the recent packet docs and notice they imply outside readiness.
2. Ask whether the author has actually re-audited the live system end-to-end at mechanism level.
3. Observe that the packet was largely structured from normalization of older material plus local summaries, not from a new primary deep audit covering all main mechanisms.

### Evidence
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- `STATE.md`
- live repo files inspected in this block

### Five Whys
1. Why is the packet misleading? Because it suggests outside-readiness before the fresh primary audit exists.
2. Why did that happen? Because packet structuring started before the new deep mechanism-level research was completed.
3. Why is that dangerous? Because outside researchers would receive a packet that looks authoritative without being backed by enough fresh first-hand analysis.
4. Why would that repeat old mistakes? Because earlier truthful but incomplete material already proved that packaging without a strong governing audit still allowed bad implementations.
5. Why fix this now? Because continuing packet polish before primary research would compound the misunderstanding.

### Broken invariant
No external-research handoff should be treated as authoritative before a fresh primary deep audit explains the real system in enough detail.

### Shared mechanism
Primary deep system audit before packet publication.

### Why this surfaced family belongs to that mechanism
The problem is not one wrong sentence. It is the ordering error: external-facing packet construction started before the new primary audit was done.

### Open-world envelope expected to improve after the fix
- external readers will get documents grounded in fresh primary analysis, not only normalized archive prose;
- future internal implementation will cite deep mechanism audits instead of restarting from packet scaffolding;
- misleading “research-ready” claims will be replaced with explicit readiness gates.

### Root cause statement
The current consultant-core external packet was normalized and structured before a fresh primary deep audit of the live system had been completed. That inverted the correct order: the packet started to look authoritative even though the underlying system explanation had not yet been re-derived in full from the repo.

### Fix mechanism
- explicitly demote the current packet to scaffold/draft status;
- start the new primary deep audit with fresh repo-backed documents;
- only after those audits exist should the packet be treated as an external handoff candidate.

## DoD
- Top-level packet docs no longer imply external-ready status without the fresh primary audit.
- A new primary deep-audit program doc exists and states what remains open.
- At least three fresh deep-audit docs are published from direct repo inspection.
- `STATE.md` records the correction as a doc-only truth update with `r35f` unchanged.
- `STRUCTURE.md` registers the new TP/report and deep-audit docs.

## Checks
- `python3 - <<'PY'
from pathlib import Path
required = [
    'docs/system_forensics/PRIMARY_DEEP_AUDIT_PROGRAM.md',
    'docs/system_forensics/SYSTEM_CONTEXT_DEEP_AUDIT.md',
    'docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md',
    'docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md',
]
for path in required:
    assert Path(path).exists(), path
print('primary_deep_audit_docs_ok')
PY`
- `python3 - <<'PY'
import json
from pathlib import Path
payload = json.loads(Path('docs/system_forensics/artifact_index.json').read_text())
assert payload.get('packet_status') == 'scaffold_pending_primary_deep_audit'
print('packet_status_scaffold_ok')
PY`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-30-consultant-core-primary-deep-system-audit-a922.md`
- fresh deep-audit docs under `docs/system_forensics/`
- updated top-level packet docs and canon

## Rollback
- Remove the new primary deep-audit docs.
- Remove the new TP/report.
- Revert the packet framing/canon corrections.

## No-go
- Do not keep implying the packet is already final.
- Do not treat scaffold JSON registries as a substitute for primary research.
- Do not start runtime implementation in this block.
- Do not silently preserve the ordering mistake.

## Risks / blockers
- The audit scope is too large for one block, so explicit backlog tracking is mandatory.
- Existing archive docs are still useful, but they must not be mistaken for a complete fresh re-derivation.
- If deep-audit docs stay shallow, this block will not fix the real problem.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- The external packet remains a scaffold after this block, not a final handoff.
- Several deep-audit domains will still remain open after the first wave.
- No runtime architecture has changed.

### Why not in this block
This block only restarts the research in the correct order and publishes the first fresh deep-audit slices.

### Risk if deferred
The team will continue confusing packet formatting with actual system research, and future external handoff will remain untrustworthy.

### Linked follow-up Task Package(s)
- next deep-audit waves should cover boundary/degrade, pack/runtime separation, code topology, and quality/evaluator architecture at the same first-hand depth
- runtime architecture-recovery work remains blocked until the primary deep audit reaches a usable threshold

### Expiry / trigger to stop deferral
- stop deferral before any outside handoff is called ready
- stop deferral before any architecture-recovery runtime slice starts

## Next-block contract (mandatory)
### Next block objective
Continue the primary deep audit with the next mechanism layers: boundary/degrade authority, pack/runtime separation, code topology, and quality/evaluator governance.

### First deterministic check command
`python3 - <<'PY'
from pathlib import Path
for path in [
    'docs/system_forensics/PRIMARY_DEEP_AUDIT_PROGRAM.md',
    'docs/system_forensics/SYSTEM_CONTEXT_DEEP_AUDIT.md',
    'docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md',
    'docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md',
]:
    assert Path(path).exists(), path
print('primary_deep_audit_prereqs_ok')
PY`

### Blocked-by conditions
- packet still framed as final external handoff
- new deep-audit docs missing or shallow
- canon not synced

### Owner role for closure
Brain / Top Architect
