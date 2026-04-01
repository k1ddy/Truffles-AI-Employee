# TP-2026-03-30-consultant-core-external-packet-contracts-and-turn-walkthrough-a922

## Title / purpose
Close the two remaining outside-packet blockers by publishing self-contained root-level summaries of the four typed runtime contracts and one end-to-end worked turn walkthrough. Then rerun the packet readiness review and decide whether the consultant-core corpus is now actually ready for external researchers.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/PRIMARY_DEEP_AUDIT_PROGRAM.md`
- `docs/system_forensics/PRIMARY_DEEP_AUDIT_CONTRADICTION_REVIEW.md`
- `docs/system_forensics/EXTERNAL_PACKET_READINESS_REVIEW.md`
- `docs/system_forensics/RUNTIME_ARCHITECTURE.md`
- `docs/system_forensics/STATE_AND_TRUTH_CARRIERS_AUDIT.md`
- `docs/system_forensics/FACT_RUNTIME_DEEP_AUDIT.md`
- `docs/system_forensics/BOUNDARY_DEGRADE_DEEP_AUDIT.md`
- `docs/system_forensics/QUALITY_EVALUATOR_DEEP_AUDIT.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/TURN_JOURNAL_V1.md`
- `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
- `docs/REPORTS/2026-03-30-consultant-core-primary-deep-audit-contradiction-resolution-a922.md`

## One web search (mandatory before implementation)
- Query: `site:docs.arc42.org runtime view walkthrough architecture documentation interfaces`
- Date/time (local): `2026-03-30 17:11:00 +0500`
- Sources opened:
  - `https://docs.arc42.org/section-6/`
- Source quality:
  - official arc42 documentation / primary source
- Ready solutions found:
  - runtime-view docs should describe concrete behavior and interactions of the building blocks as scenarios;
  - one representative runtime scenario can be enough if it maps activities clearly to the responsible building blocks;
  - sequence-style or numbered textual walkthroughs are acceptable if they stay explicit about component responsibilities.
- Decision (`reuse/integrate/build`): `reuse + integrate + build`
  - reuse the archive contract docs and fresh deep audits as the evidence base;
  - integrate them into self-contained root-level summaries aimed at outside readers;
  - build one explicit worked runtime scenario that maps the real turn to the current building blocks.
- Rejected options:
  - keep forcing outside readers into archive-only contract docs;
  - keep readiness blocked after the named blockers are explicitly addressed;
  - jump to runtime implementation before outside reviewers can read one self-contained packet.

## Invariant
- Do not change runtime behavior.
- Do not run a new practical replay.
- Do not change practical truth (`r35f`).
- Do not overstate product or architecture closure.
- If the packet still is not ready after this block, say so explicitly.

## Scope
- Publish self-contained root-level summaries for:
  - `SemanticDecisionV1`
  - `BindingPlanV1`
  - `TurnJournalV1`
  - `ConversationProjectionV1`
- Publish one worked end-to-end runtime turn walkthrough.
- Rerun and update the packet readiness review.
- Sync packet/canon/manifests to the reviewed result.

## Out of scope
- Runtime implementation.
- New target-architecture decision.
- External researcher feedback intake itself.
- Product replay/human audit.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-external-packet-contracts-and-turn-walkthrough-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-external-packet-contracts-and-turn-walkthrough-a922.md`
- `docs/system_forensics/SEMANTIC_DECISION_CONTRACT.md`
- `docs/system_forensics/BINDING_PLAN_CONTRACT.md`
- `docs/system_forensics/TURN_JOURNAL_CONTRACT.md`
- `docs/system_forensics/CONVERSATION_PROJECTION_CONTRACT.md`
- `docs/system_forensics/END_TO_END_TURN_WALKTHROUGH.md`
- `docs/system_forensics/PRIMARY_DEEP_AUDIT_PROGRAM.md`
- `docs/system_forensics/PRIMARY_DEEP_AUDIT_CONTRADICTION_REVIEW.md`
- `docs/system_forensics/EXTERNAL_PACKET_READINESS_REVIEW.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/MIGRATION_PROGRAM.md`
- `docs/system_forensics/EVIDENCE_MAP.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- `docs/system_forensics/artifact_index.json`
- `docs/system_forensics/module_inventory.json`
- `docs/system_forensics/failure_family_registry.json`
- `docs/system_forensics/runtime_path_registry.json`
- `STATE.md`
- `STRUCTURE.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`

## Plan
1. Re-derive the four typed runtime contracts from the archive contracts plus live code anchors.
2. Publish self-contained root-level summaries aimed at outside researchers.
3. Publish one worked end-to-end turn walkthrough using a real `r35f` turn and the live runtime spine.
4. Update the readiness review and packet status.
5. Stop there; no implementation starts in this block.

## Root cause (mandatory)
### Symptom
The packet had fresh system-level analysis and a reviewed archive, but it still was not self-contained for outside readers because core typed contracts and one concrete runtime scenario still lived mostly in archive or repo-only detail.

### Minimal reproduction
1. Start with `docs/system_forensics/INDEX.md` and the root packet docs.
2. Ask what exactly `SemanticDecisionV1`, `BindingPlanV1`, `TurnJournalV1`, and `ConversationProjectionV1` are, without opening `final/` docs.
3. Ask how one real turn traverses owner, binding, state, fact behavior, boundary/degrade, and trace/meta.
4. Observe that the root packet previously failed both questions.

### Evidence
- `docs/system_forensics/EXTERNAL_PACKET_READINESS_REVIEW.md`
- `docs/system_forensics/final/SEMANTIC_DECISION_V1.md`
- `docs/system_forensics/final/BINDING_PLAN_V1.md`
- `docs/system_forensics/final/TURN_JOURNAL_V1.md`
- `docs/system_forensics/final/CONVERSATION_PROJECTION_V1.md`
- `truffles-api/app/core/semantic_decision.py`
- `truffles-api/app/core/binding_plan.py`
- `truffles-api/app/core/turn_journal.py`
- `truffles-api/app/core/conversation_projection.py`
- `/tmp/booking_quality/a922-practical-proof-20260330-r35f/responses.jsonl`
- `/tmp/booking_quality/a922-practical-proof-20260330-r35f/trace_bundle.jsonl`

### Five Whys
1. Why was the packet still not ready? Because key contracts and one representative runtime scenario were not self-contained at the root layer.
2. Why did that matter? Because outside researchers are supposed to work without repo access.
3. Why couldn't they do that yet? Because they still had to open archive-only contract docs or infer the runtime flow from several deep audits.
4. Why is that a problem for architecture help? Because without clear contract summaries and one worked scenario, reviewers can misread where authority lives.
5. Why fix it now? Because these were the last explicit blockers named by the readiness review.

### Broken invariant
A packet cannot be called outside-ready if its core runtime contract objects and one representative runtime scenario are not self-contained at the root layer.

### Shared mechanism
External-packet self-containment for outside architecture review.

### Why this surfaced family belongs to that mechanism
This is not a problem in one missing Markdown file. It is the packet-completeness mechanism: outside readers need both object-level contract summaries and scenario-level runtime understanding.

### Open-world envelope expected to improve after the fix
- outside researchers can understand the typed contract stack without archive digging;
- outside researchers can reason about one real runtime turn without repo access;
- future implementation can wait on structured external review instead of restarting from partial memory.

### Root cause statement
The packet had broad system analysis but still lacked the two final self-containment pieces that outside architecture review depends on: compact root-level contract summaries and one explicit end-to-end runtime scenario.

### Fix mechanism
- add root-level typed contract summaries;
- add one worked runtime walkthrough;
- rerun the readiness review and update packet status accordingly.

## DoD
- New root-level docs exist:
  - `docs/system_forensics/SEMANTIC_DECISION_CONTRACT.md`
  - `docs/system_forensics/BINDING_PLAN_CONTRACT.md`
  - `docs/system_forensics/TURN_JOURNAL_CONTRACT.md`
  - `docs/system_forensics/CONVERSATION_PROJECTION_CONTRACT.md`
  - `docs/system_forensics/END_TO_END_TURN_WALKTHROUGH.md`
- `EXTERNAL_PACKET_READINESS_REVIEW.md` is rerun and explicitly states whether the packet is ready.
- Packet/manifests/canon use one consistent reviewed status.
- `STATE.md` records the result with `r35f` unchanged.
- `STRUCTURE.md` registers the new docs and TP/report.

## Checks
- `python3 - <<'PY'`
  `from pathlib import Path`
  `required = [`
  `    'docs/system_forensics/SEMANTIC_DECISION_CONTRACT.md',`
  `    'docs/system_forensics/BINDING_PLAN_CONTRACT.md',`
  `    'docs/system_forensics/TURN_JOURNAL_CONTRACT.md',`
  `    'docs/system_forensics/CONVERSATION_PROJECTION_CONTRACT.md',`
  `    'docs/system_forensics/END_TO_END_TURN_WALKTHROUGH.md',`
  `]`
  `for path in required:`
  `    assert Path(path).exists(), path`
  `print('external_packet_contract_docs_ok')`
  `PY`
- `python3 - <<'PY'`
  `import json`
  `from pathlib import Path`
  `payload = json.loads(Path('docs/system_forensics/artifact_index.json').read_text())`
  `assert payload.get('packet_status') == 'ready_for_external_handoff', payload.get('packet_status')`
  `assert payload.get('external_readiness_review', {}).get('status') == 'ready'`
  `assert not payload.get('external_readiness_review', {}).get('remaining_blockers')`
  `print('external_packet_ready_manifest_ok')`
  `PY`
- `python3 - <<'PY'`
  `from pathlib import Path`
  `index = Path('docs/system_forensics/INDEX.md').read_text()`
  `packet = Path('docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md').read_text()`
  `for needle in [`
  `    'docs/system_forensics/SEMANTIC_DECISION_CONTRACT.md',`
  `    'docs/system_forensics/BINDING_PLAN_CONTRACT.md',`
  `    'docs/system_forensics/TURN_JOURNAL_CONTRACT.md',`
  `    'docs/system_forensics/CONVERSATION_PROJECTION_CONTRACT.md',`
  `    'docs/system_forensics/END_TO_END_TURN_WALKTHROUGH.md',`
  `]:`
  `    assert needle in index, needle`
  `    assert needle in packet, needle`
  `print('external_packet_contract_links_ok')`
  `PY`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-30-consultant-core-external-packet-contracts-and-turn-walkthrough-a922.md`
- the five new root-level docs
- updated readiness review and packet manifests

## Rollback
- Remove the five new docs plus TP/report.
- Restore the prior not-ready readiness review and packet status.
- Revert canon/manifests to the previous reviewed-not-ready state.

## No-go
- Do not claim product-green or architecture completion.
- Do not restart runtime implementation in this block.
- Do not hide the difference between packet readiness and architecture correctness.

## Risks / blockers
- The packet can become outside-ready while the architecture still remains deeply unfinished.
- A worked scenario can accidentally overfit to one turn if it is not explicit about the general skeleton versus current residue.
- Outside-ready packet status can be misread as permission to code immediately; the canon must prevent that.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- The architecture is still unfinished even if the packet becomes ready.
- Product/practical closure remains open.
- External review has not yet been received.

### Why not in this block
This block only closes the packet self-containment gaps.

### Risk if deferred
Outside researchers would still lack the contract and runtime clarity needed to help effectively.

### Linked follow-up Task Package(s)
- next doc/process block: external review intake and synthesis into the executive packet
- only after that, or after explicit owner waiver, may the first runtime architecture-recovery implementation wave start

### Expiry / trigger to stop deferral
- stop deferral before restarting runtime implementation;
- stop deferral once outside review is received or explicitly waived.

## Next-block contract (mandatory)
### Next block objective
Use the now-ready external packet to run structured outside review, collect answers via the questionnaire, and update the packet with accepted challenges or corrections before any runtime architecture work resumes.

### First deterministic check command
`python3 - <<'PY'`
`from pathlib import Path`
`for path in [`
`    'docs/system_forensics/SEMANTIC_DECISION_CONTRACT.md',`
`    'docs/system_forensics/BINDING_PLAN_CONTRACT.md',`
`    'docs/system_forensics/TURN_JOURNAL_CONTRACT.md',`
`    'docs/system_forensics/CONVERSATION_PROJECTION_CONTRACT.md',`
`    'docs/system_forensics/END_TO_END_TURN_WALKTHROUGH.md',`
`]:`
`    assert Path(path).exists(), path`
`print('external_packet_ready_docs_present')`
`PY`

### Blocked-by conditions
- packet status not consistent across root docs and machine-readable artifacts;
- readiness review still not `ready`;
- questionnaire or machine-readable companion missing.

### Owner role for closure
Brain / Top Architect
