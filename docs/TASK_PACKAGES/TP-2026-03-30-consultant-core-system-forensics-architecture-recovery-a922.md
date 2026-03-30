# TP-2026-03-30-consultant-core-system-forensics-architecture-recovery-a922

## Название / цель
Остановить reactive patch-loop как default путь consultant-core practical closure и выпустить self-contained system-forensics corpus для внешних исследователей. Цель блока: объяснить систему уровнями выше и одновременно глубоко, зафиксировать точный current-state verdict, перечислить архитектурные блокеры и anti-patterns, и опубликовать target architecture + migration program, чтобы следующие реализации были mechanism-first и production-oriented, а не symptom-first.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `TECH.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`
- `docs/runbooks/BOOKING_CONFIRM_VERIFY.md`
- `docs/TASK_PACKAGES/TP-2026-03-09-p1.6o60a-remaining-closure-architecture-verdict-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-09-p1.6o60b-remaining-closure-owner-matrix-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o79-executable-interaction-core-redesign-reset-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o81-machine-readable-owner-matrix-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o82-persisted-interaction-state-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o83-owner-resolver-m27-vertical-slice-a1.md`
- `docs/REPORTS/2026-03-30-consultant-core-r35f-human-semantic-audit-a922.md`

## One web search (mandatory before implementation)
- Query: `site:arc42.org architecture documentation runtime view building block view quality scenarios official`
- Date/time (local): `2026-03-30 13:36 +05`
- Sources opened:
  - `https://canvas.arc42.org/downloads/architecture-inception-canvas.pdf`
- Source quality:
  - official arc42 material / primary source
- Ready solutions found:
  - architecture material for external readers must separate system purpose, quality goals, building blocks, runtime flows, risks, and migration concerns rather than mixing them into one bug log;
  - narrative architecture evidence is most useful when it explains both current behavior and the desired target shape.
- Decision (`reuse/integrate/build`): `reuse + integrate`
  - reuse the repo's prior forensic corpus, owner-matrix work, practical-closure audits, and state canon;
  - integrate them into one self-contained external-research packet instead of another local runtime fix.
- Rejected options:
  - continue publishing only task-local RCA docs;
  - let external researchers infer architecture only from narrow family TPs;
  - continue implementation before the external-facing architecture corpus exists.

## Invariant
- Do not claim product-green or practical closure.
- Do not reopen the second-semantic-owner overclaim.
- Do not treat the current dirty worktree as closure evidence.
- Do not ship new runtime phrase-hardcodes or scenario patches from this block.
- Keep current practical truth `r35f` unchanged.

## Scope
- Create `docs/system_forensics/` as the canonical external-research corpus.
- Explain the product contract, runtime architecture, semantic ownership model, interaction architecture, fact architecture, boundary/degrade behavior, pack/runtime separation, code topology, failure-family atlas, anti-pattern catalog, target architecture, and migration program.
- Publish one system-level verdict and one external-research packet that are self-contained for readers without repo/runtime access.
- Update active canon/truth docs so the next admissible work starts from this corpus rather than from another direct runtime patch.

## Out of scope
- New product runtime behavior fixes.
- Fresh replay runs.
- Human-semantic truth updates beyond preserving `r35f` as current truth.
- Deleting or refactoring the existing runtime in this block.
- Replacing the existing owner-matrix / interaction-state implementation in this block.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-system-forensics-architecture-recovery-a922.md`
- `docs/REPORTS/2026-03-30-consultant-core-system-forensics-architecture-recovery-a922.md`
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/GLOSSARY.md`
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
- `STATE.md`
- `STRUCTURE.md`
- `docs/PRACTICAL_CLOSURE_ADDENDUM.md`

## Plan
1. Re-anchor the block to the earlier architecture-verdict / owner-matrix / redesign-reset corpus.
2. Build one self-contained system-forensics index for external researchers.
3. Publish deep narrative audits by architectural axis, not by scenario.
4. Publish one system verdict and one target architecture / migration program.
5. Sync active canon so future practical work must start from the system-forensics corpus.

## Root cause (mandatory)
### Symptom
The repo contains many truthful family-level audits and bounded fixes, but the resulting implementation quality still drifts toward local repairs, and the existing documentation is not yet a self-contained architectural explanation for external researchers.

### Minimal reproduction
1. Read `docs/TASK_PACKAGES/TP-2026-03-09-p1.6o60a-remaining-closure-architecture-verdict-a1.md` and `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o79-executable-interaction-core-redesign-reset-a1.md`.
2. Compare those architecture-level conclusions with the later practical family TPs in `docs/TASK_PACKAGES/TP-2026-03-29-consultant-core-*.md` and `docs/TASK_PACKAGES/TP-2026-03-30-consultant-core-*.md`.
3. Inspect the current runtime topology around `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/info.py`, `truffles-api/app/services/demo_salon_knowledge.py`, `truffles-api/app/services/owner_resolver.py`, `truffles-api/app/routers/webhook/context_manager.py`, and `truffles-api/app/routers/webhook/session_memory.py`.
4. Observe that interaction-side architecture has partial structural solutions, while fact-side architecture still lacks a comparable executable contract and the codebase still invites local patching.

### Evidence
- `docs/TASK_PACKAGES/TP-2026-03-09-p1.6o60a-remaining-closure-architecture-verdict-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-09-p1.6o60b-remaining-closure-owner-matrix-a1.md`
- `docs/TASK_PACKAGES/TP-2026-03-12-p1.6o79-executable-interaction-core-redesign-reset-a1.md`
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
- `truffles-api/app/services/owner_resolver.py`
- `truffles-api/app/services/demo_salon_knowledge.py`
- `docs/REPORTS/2026-03-30-consultant-core-r35f-human-semantic-audit-a922.md`
- `STATE.md`

### Five Whys
1. Why do local fixes keep reappearing? Because the system still lacks one fully governing executable architecture across all product paths.
2. Why is the architecture not fully governing? Because only part of the mined architecture became machine-readable and executable; fact-side behavior still relies on broad helpers and pack-specific rendering logic.
3. Why are external-facing docs insufficient? Because they were written mostly as task-local truth and family evidence, not as a self-contained system explanation.
4. Why did that matter? Because later implementation could still regress into local patching even while earlier architectural docs were directionally correct.
5. Why must this be fixed before more product work? Because without a complete architecture-and-forensics corpus, future researchers and implementers will keep rediscovering problems locally instead of repairing the shared mechanisms.

### Root cause statement
The consultant-core lane has strong forensic evidence and partial architecture recovery, but the architecture contract remains uneven: interaction mechanisms are only partially compiled into runtime, fact mechanisms are still largely undocumented and non-executable, and the documentation corpus is not yet self-contained enough to govern future implementation or external research. As a result, truthful audits coexist with implementation drift back into local repairs.

### Fix mechanism
- publish a self-contained system-forensics corpus;
- explain current runtime architecture and debt by mechanism, not by scenario;
- make target architecture and migration order explicit;
- block future product implementation from skipping this corpus.

## DoD
- `docs/system_forensics/` exists and is indexed in `STRUCTURE.md`.
- External researchers can read the corpus without repo access and understand product contract, runtime architecture, major architectural debts, target architecture, and migration order.
- The corpus explicitly explains why earlier narrow fixes were insufficient.
- `STATE.md` and `docs/PRACTICAL_CLOSURE_ADDENDUM.md` keep `r35f` as truth but redirect the next admissible work to the system-forensics / architecture-recovery program.
- No new product-quality claim is made.

## Checks
- `python3 - <<'PY'\nfrom pathlib import Path\nroot = Path('docs/system_forensics')\nrequired = [\n    'INDEX.md',\n    'GLOSSARY.md',\n    'SYSTEM_VERDICT.md',\n    'PRODUCT_CONTRACT.md',\n    'RUNTIME_ARCHITECTURE.md',\n    'SEMANTIC_OWNERSHIP_AUDIT.md',\n    'INTERACTION_ARCHITECTURE_AUDIT.md',\n    'FACT_ARCHITECTURE_AUDIT.md',\n    'BOUNDARY_DEGRADE_AUDIT.md',\n    'PACK_RUNTIME_SEPARATION_AUDIT.md',\n    'CODE_TOPOLOGY_AUDIT.md',\n    'FAILURE_FAMILY_ATLAS.md',\n    'ANTI_PATTERN_CATALOG.md',\n    'TARGET_ARCHITECTURE.md',\n    'MIGRATION_PROGRAM.md',\n    'EVIDENCE_MAP.md',\n    'QUALITY_GOVERNANCE_AUDIT.md',\n    'EXTERNAL_RESEARCH_PACKET.md',\n]\nmissing = [name for name in required if not (root / name).exists()]\nif missing:\n    raise SystemExit(f'missing: {missing}')\nprint('system_forensics_docs_ok')\nPY`
- `git diff --check`

## Evidence
- this TP
- `docs/REPORTS/2026-03-30-consultant-core-system-forensics-architecture-recovery-a922.md`
- `docs/system_forensics/*`
- updated `STATE.md`
- updated `STRUCTURE.md`
- updated `docs/PRACTICAL_CLOSURE_ADDENDUM.md`

## Rollback
- Remove `docs/system_forensics/`.
- Remove the TP/report.
- Revert the doc-only canon updates in `STATE.md`, `STRUCTURE.md`, and `docs/PRACTICAL_CLOSURE_ADDENDUM.md`.

## No-go
- Do not resume product runtime patching from this block.
- Do not claim the system is now architecturally fixed.
- Do not write only narrative opinions without exact runtime/code references.
- Do not let the new corpus become another local bug diary.

## Risks / blockers
- The corpus can still become shallow if it only rephrases old TPs without synthesizing system-level mechanisms.
- Fact-side architecture is less mature than interaction-side architecture, so that audit must remain explicit about uncertainty and missing artifacts.
- The current worktree contains unfinished runtime changes from prior blocks; this block must not reinterpret them as accepted architecture work.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- The runtime is still not refactored to the target architecture.
- Fact-side machine-readable contract artifacts do not yet exist.
- `decision.py` remains a god-file.
- The current practical truth remains only `human-semantic amber`, not green.

### Why not in this block
This block is the governing analysis and architecture-recovery publication step. Mixing it with runtime migration would reduce clarity and repeat the earlier mistake of patching while the architecture narrative is still incomplete.

### Risk if deferred
Future implementation will continue to overfit surfaced families, and external researchers will still lack a complete, trustworthy explanation of the system.

### Linked follow-up Task Package(s)
- Next TP must be the first implementation wave of the architecture-recovery program, not another direct family patch.
- The expected first implementation wave is `fact architecture contract materialization`.

### Expiry / trigger to stop deferral
- Stop deferral before any new product runtime fix.
- Stop deferral immediately if another implementation attempt is proposed without citing `docs/system_forensics/`.

## Next-block contract (mandatory)
### Next block objective
Materialize the first missing shared mechanism from the new corpus: `fact architecture contract materialization`.

### First deterministic check command
`python3 - <<'PY'\nfrom pathlib import Path\nassert Path('docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md').exists()\nassert Path('docs/system_forensics/TARGET_ARCHITECTURE.md').exists()\nassert Path('docs/system_forensics/MIGRATION_PROGRAM.md').exists()\nprint('forensics_prereqs_ok')\nPY`

### Blocked-by conditions
- `docs/system_forensics/` corpus incomplete
- current truth/canon not synced to the new program
- fact architecture still not framed as `broken invariant + shared mechanism`

### Owner role for closure
Brain / Top Architect
