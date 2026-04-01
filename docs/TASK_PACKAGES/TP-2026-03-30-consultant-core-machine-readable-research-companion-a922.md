# TP-2026-03-30-consultant-core-machine-readable-research-companion-a922

## Название / цель
Добавить machine-readable companion к уже опубликованному external-research corpus, чтобы внешние исследователи могли читать не только narrative docs, но и стабильные JSON-реестры модулей, runtime-paths, failure families и формализованный questionnaire для возврата рекомендаций.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/WORK_METHOD.md`
- `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md`
- `docs/system_forensics/EVIDENCE_MAP.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-system-forensics-architecture-recovery-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-external-research-corpus-deepening-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-external-research-corpus-deepening-a922.md`

## One web search (mandatory before implementation)
- Query: `site:json-schema.org learn json schema object required properties arrays documentation`
- Date/time (local): `2026-03-30 10:17 +0500`
- Sources opened:
  - `https://json-schema.org/understanding-json-schema/reference/object`
- Source quality:
  - official JSON Schema documentation / primary source
- Ready solutions found:
  - machine-readable artifacts are most useful when each object has stable named properties instead of free-form blobs;
  - explicit property sets and controlled extra fields reduce ambiguity for downstream consumers;
  - required keys should be obvious and repeated across records so readers can compare artifacts mechanically.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the corrected executive packet and archive evidence;
  - integrate them into stable JSON registries and one explicit review questionnaire;
  - build the minimal machine-readable companion that external researchers can parse without source access.
- Rejected options:
  - keep the packet narrative-only;
  - expect outside researchers to reconstruct registries from Markdown;
  - jump to runtime implementation before the external packet has a structured response contract.

## Invariant
- Do not change product runtime behavior.
- Do not run a new practical replay.
- Do not change current practical truth (`r35f`).
- Do not reopen old product-family RCA from this block.
- Keep this block doc-only and external-research-focused.

## Scope
- Publish stable JSON companion artifacts for the external-research packet.
- Add an explicit external review questionnaire in Markdown and JSON.
- Sync the root system-forensics docs so the new companion is first-class, not hidden.
- Record the new packet in canon.

## Out of scope
- Runtime fixes.
- New deterministic product tests.
- New replay or human-semantic audit.
- Inventing fake certainty for unresolved architecture questions.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-machine-readable-research-companion-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-machine-readable-research-companion-a922.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/WORK_METHOD.md`
- `docs/system_forensics/GLOSSARY.md`
- `docs/system_forensics/EVIDENCE_MAP.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md`
- `docs/system_forensics/artifact_index.json`
- `docs/system_forensics/module_inventory.json`
- `docs/system_forensics/failure_family_registry.json`
- `docs/system_forensics/runtime_path_registry.json`
- `docs/system_forensics/glossary.json`
- `docs/system_forensics/EXTERNAL_REVIEW_QUESTIONNAIRE.md`
- `docs/system_forensics/external_review_questionnaire.json`
- `STATE.md`
- `STRUCTURE.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`

## Plan
1. Define the minimal machine-readable companion set external researchers need.
2. Publish the JSON registries and questionnaire.
3. Update the root packet docs so they reference the new companion explicitly.
4. Sync canon (`STATE.md`, `STRUCTURE.md`, addendum) with the new doc-only block.
5. Run JSON/integrity checks and stop there.

## Root cause (mandatory)
### Symptom
The external-research corpus is now self-contained for human readers, but it is still mostly narrative. Outside researchers still lack stable machine-readable registries and a response contract, so they would have to rebuild inventories and question lists manually.

### Minimal reproduction
1. Read `docs/system_forensics/INDEX.md` and `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md`.
2. Observe that the packet explains what to read, but does not yet ship JSON registries for modules, paths, families, or glossary.
3. Observe that the packet requests help, but does not yet provide one structured questionnaire or response schema at the root level.
4. Compare this with the stated goal: make the corpus usable for outside researchers without chat archaeology.

### Evidence
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md`
- `docs/system_forensics/EVIDENCE_MAP.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-external-research-corpus-deepening-a922.md`

### Five Whys
1. Why is the packet still weaker than it should be for external researchers? Because it is still narrative-first.
2. Why does that matter? Because outside researchers need stable structured inputs for comparison, not only prose.
3. Why were earlier external analyses easier to misread or underuse? Because the repo did not provide one normalized machine-readable companion.
4. Why does that increase implementation risk? Because future readers may again rebuild partial mental models instead of consuming one governed packet.
5. Why fix this before runtime work? Because the stated goal is outside-ready architecture research, not another internal-only note set.

### Broken invariant
External-research packet should be self-contained for both human reading and structured downstream consumption.

### Shared mechanism
External packet normalization and response-contract materialization.

### Why this surfaced family belongs to that mechanism
The weakness is not one missing sentence. It is the absence of stable registries and a standard review response contract across the entire packet.

### Open-world envelope expected to improve after the fix
- outside researchers can consume the packet without source access;
- different reviewers can return comparable outputs;
- future internal work can point to one machine-readable packet instead of reconstructing state from prose.

### Root cause statement
The corrected executive packet solved the human-readable side of the external-research problem, but the consultant-core corpus still lacked a machine-readable companion and a formal questionnaire. That left the packet narrative-heavy and still too dependent on manual reconstruction for structured outside review.

### Fix mechanism
- publish JSON registries for artifacts, modules, runtime paths, failure families, and glossary;
- add a formal external review questionnaire in Markdown and JSON;
- wire these artifacts into the root packet and canon.

## DoD
- The machine-readable companion files exist and parse as valid JSON.
- The root packet explicitly references the new JSON artifacts and questionnaire.
- `STATE.md` records the block as doc-only with practical truth unchanged.
- `STRUCTURE.md` registers the new TP/report and machine-readable files.
- No runtime behavior or product truth claims changed.

## Checks
- `python3 - <<'PY'
import json
from pathlib import Path
required = [
    'docs/system_forensics/artifact_index.json',
    'docs/system_forensics/module_inventory.json',
    'docs/system_forensics/failure_family_registry.json',
    'docs/system_forensics/runtime_path_registry.json',
    'docs/system_forensics/glossary.json',
    'docs/system_forensics/external_review_questionnaire.json',
]
for path in required:
    json.loads(Path(path).read_text())
print('external_machine_companion_ok')
PY`
- `python3 - <<'PY'
from pathlib import Path
for path in [
    'docs/system_forensics/EXTERNAL_REVIEW_QUESTIONNAIRE.md',
    'docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md',
    'docs/system_forensics/INDEX.md',
]:
    assert Path(path).exists(), path
print('external_review_packet_ok')
PY`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-30-consultant-core-machine-readable-research-companion-a922.md`
- new machine-readable artifacts under `docs/system_forensics/`
- updated root packet docs
- updated `STATE.md`
- updated `STRUCTURE.md`

## Rollback
- Remove the new JSON artifacts and questionnaire.
- Remove the new TP/report.
- Revert the doc-only root-packet/canon references added in this block.

## No-go
- Do not start runtime implementation from this block.
- Do not invent fake numeric scores or unsupported architecture certainty.
- Do not treat machine-readable artifacts as replacing the narrative packet.
- Do not add ad hoc JSON blobs without stable keys and explicit purpose.

## Risks / blockers
- The registries can become stale snapshots if future doc blocks do not keep them synced.
- Outside researchers may still want more repo-level detail, so the companion must point back to archive evidence rather than pretending to be exhaustive.
- Without a review questionnaire, even good structured artifacts would still yield incomparable reviewer outputs.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- No runtime architecture changed.
- The machine-readable companion is still a documentation snapshot, not an executable contract.
- Practical truth remains `r35f` and product closure remains open.

### Why not in this block
This block is still external-research preparation. It exists to make outside review structured and comparable before any new architecture implementation wave.

### Risk if deferred
Future external feedback will remain inconsistent, and internal teams may again overfit local symptoms instead of working from one structured packet.

### Linked follow-up Task Package(s)
- next doc-only follow-up can be an external-review dry run or consistency pass against one zero-context reviewer
- next runtime implementation remains blocked behind the architecture-recovery lane and still points to `fact architecture contract materialization`

### Expiry / trigger to stop deferral
- stop deferral before any outside review is requested without the questionnaire and machine companion
- stop deferral if the new registries drift from the root packet or canon references

## Next-block contract (mandatory)
### Next block objective
Use the full external-research packet plus machine-readable companion to perform a dry-run reviewer pass or, if review is complete, open the first architecture-recovery implementation slice from the governed packet.

### First deterministic check command
`python3 - <<'PY'
import json
from pathlib import Path
for path in ['docs/system_forensics/artifact_index.json', 'docs/system_forensics/module_inventory.json', 'docs/system_forensics/external_review_questionnaire.json']:
    json.loads(Path(path).read_text())
print('external_machine_packet_prereqs_ok')
PY`

### Blocked-by conditions
- missing or invalid JSON companion artifacts
- questionnaire not referenced from the root packet
- `STATE.md` / `STRUCTURE.md` not synced

### Owner role for closure
Brain / Top Architect
