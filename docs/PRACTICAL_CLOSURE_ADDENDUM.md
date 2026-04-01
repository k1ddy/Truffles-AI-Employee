# PRACTICAL CLOSURE ADDENDUM

Status override (2026-03-30): while `docs/RECOVERY_EXECUTION_LOCK.yaml` is active, this document is behavioral-history evidence only and is not the governing control layer for the active program. The governing base for active execution is `r35f + Consultant Core Legacy Drain And Proof Closure`. Any `r36*`, consult/media, or booking-manage runtime/RCA material below must be treated as drift residue unless and until a later explicit owner/architect waiver advances beyond the current block.

## Purpose
This addendum corrects the closure model for the consultant-core program.

The prior `W1-W8` closeout can stand as a **structural/contract** claim where supported by code, contracts, guards, and deterministic evidence. It must not be interpreted as automatic proof of **product-ready practical behavior**.

## Correction Summary
1. `structural/contract complete` and `product/practical complete` are different claims.
2. Current evidence does **not** prove a second semantic owner.
3. Current evidence does prove that practical quality remains open because of surfaced failure families in live replay and human audit.
4. Future closure claims must be made against explicit closure layers, not against one overloaded `done` label.

## Current Truth (2026-03-30)
- Active practical truth is replay `a922-practical-proof-20260330-r36g` plus its full human semantic audit.
- `infra_valid=true`
- `semantic_valid=false`
- `human_semantic_valid=false`
- Full human audit verdict:
  - dialogs `8 pass / 1 weak / 1 fail`
  - visible practical improvement: `dialog 7 / turn 1` is now green for `consult/media cue continuity`
  - surfaced visible fail turns: `dialog 9 / turns 1-2`
  - secondary weak residue: `dialog 2 / turns 4-5`
- Surfaced fail blocker families on the visible human-semantic path:
  - `booking-manage temporal clue grounding / follow-up continuity`
- Secondary contract/oracle/evaluator residues:
  - `oracle contract / taxonomy alignment` (`dialog 2 / turn 4`)
  - `replay harness / evaluator isolation` (`dialog 2 / turn 5`)
  - `judge_eval_conflict` (`2`)
- Shared mechanisms behind the surfaced weak families:
  - `booking-manage temporal clue grounding / follow-up continuity`
  - `oracle contract / taxonomy alignment`
  - `replay harness / evaluator isolation`
- Interpretation:
  - root-first implementation sequence `1..10` remains materially complete repo-side on the touched canary envelope
  - the bounded `consult/media` fix is now proven improved on the practical path
  - `r36g` disproves any product-ready interpretation of that structural completion because the booking-manage family remains live
  - practical blockers must still be understood and fixed at the shared-mechanism level, not as isolated turns
  - cross-run trend evidence now proves `consult/media cue continuity` dropped out of the product bucket, but canonical regression claims remain blocked because baseline `r35f` is non-canonical for comparison
  - practical/product closure remains open because both the deterministic contract lane and the full human semantic lane are still red

## Closure Layers (mandatory)
### 1. `structural_complete`
The architecture cut exists in code.
- ownership boundaries are moved
- live authority seams are removed or bounded
- contracts/schemas/guards exist

### 2. `contract_complete`
The implementation passes deterministic boundary proof.
- schemas validate
- deterministic tests/guards are green
- trace/meta/reason-code contracts hold

### 3. `practical_behavior_complete`
The implementation survives frozen current-head replay on the real runtime path.
- current-head replay is valid
- blocker failure families are closed
- runtime behavior matches the intended mechanism-level contract

### 4. `human_semantic_complete`
A full turn-by-turn human semantic audit is green.
- each dialog reviewed
- each turn reviewed
- dialog and turn verdicts recorded
- failure families explicitly recorded as `0` or explained

### Product-ready claim
A product-ready or general `green` claim is allowed only when all four layers are satisfied.

## Practical Proof Model
Deterministic fitness functions are necessary but not sufficient.

Rationale:
- architectural fitness functions are useful because they enforce governance continuously and early
- they do not replace domain responsibility or behavioral validation
- practical closure therefore needs both automated governance and explicit human-semantic proof

## Mandatory RCA / Debug Contract
Every surfaced failure family must have one exact path map before code changes start.

### Mechanism-first interpretation (mandatory)
Failure families are evidence labels, not final implementation units.

For every surfaced family, RCA must additionally name:
1. one broken invariant
2. one shared mechanism
3. why the surfaced turns belong to that same mechanism
4. one open-world envelope expected to improve after the fix

Examples:
- `dialog 2 / turn 5` is not a valid fix unit by itself; the admissible unit is `collect->commit transition when required booking slots are already complete`
- `check-booking` is not automatically a special-case runtime branch; it is usually evidence for `booking-manage grounding / continuity`
- `parking` is not a special-case fact branch; it is evidence for `fact selection / fact composition`

### Required path map
1. user input
2. semantic owner output
3. validation / guard outcome
4. boundary fallback or degrade branch, if any
5. final response / action / state
6. trace/meta evidence
7. layer classification

### Allowed layer classifications
- `owner_error`
- `boundary_fallback_error`
- `fact_composition_error`
- `oracle_or_evaluator_error`
- `infra_or_runtime_failure`

### Rule
If the exact live path is unknown, the block is `BLOCKED` for implementation.

## No Scenario Patch Rule
Scenario IDs or individual turns are never the real fix unit.

Allowed fix unit:
- one repeatable failure family translated into one broken shared mechanism with one root-cause statement and one layer owner

Forbidden fix unit:
- `dialog 9 / turn 1` as a standalone patch target
- phrase-hardcode for one surfaced wording unless it is part of an explicit resolver/pack contract
- domain-labeled branches like `if check_booking ...`, `if parking ...`, or per-service branches used as semantic control in core

## Behavioral Done Gate
A behavioral block is `done` only after all of the following:
1. focused deterministic tests are green
2. frozen or current-head replay is rerun
3. full human semantic audit is completed
4. `STATE.md` is updated with the new practical truth
5. remaining residual families are named explicitly
6. the handoff states which shared mechanism was repaired and which residual mechanisms remain open

## Debug Evidence Gate
Any behavioral handoff must include the minimum debug bundle:
- `summary.json`
- `responses.jsonl`
- `trace_bundle.jsonl`
- `manual_audit.md`
- `manual_audit.json`
- `manual_audit_workspace.md`
- `manual_audit_workspace.json`
- `family_registry.json`
- `judge_conflicts.jsonl`
- exact command used
- exact failing family name
- exact broken invariant
- exact shared mechanism
- exact layer classification

## Workflow Hardening Gate
Before the next product-family block, the quality workflow must already separate mechanism-level product debt from oracle/evaluator/infra residue.

Mandatory workflow artifacts for every audited run:
1. turn workspace:
   - `manual_audit_workspace.md`
   - `manual_audit_workspace.json`
2. family backlog routing:
   - `family_registry.json`
3. judge calibration export:
   - `judge_conflicts.jsonl`
4. cross-run comparison:
   - `python3 ops/diagnose.py llm-quality-trends --run-dir <runA> --run-dir <runB> ...`

Rule:
- the next RCA block may not start from `summary.json` alone
- the first parking RCA pass must explicitly use the workspace, family registry, judge conflicts, and trend output
- these artifacts harden the workflow only; they do not change the current product truth by themselves

## System Forensics Gate
Before any new product runtime implementation after `r36c`, the consultant-core lane must start from the self-contained corpus in `docs/system_forensics/` plus the full `r36c` artifact bundle.

Status note: the doc-only external-research corpus deepening block completed the previously missing root-level executive packet in this consolidation worktree; the references below are now real files rather than forward declarations.

Supporting note: the external packet now also has a machine-readable companion and a structured review questionnaire under `docs/system_forensics/`, but the packet is still only a scaffold until the fresh primary deep audit reaches usable coverage; this remains research-preparation evidence only and does not change product truth.

Primary deep-audit note: the packet self-containment blockers are now also closed by `docs/system_forensics/{SEMANTIC_DECISION_CONTRACT.md,BINDING_PLAN_CONTRACT.md,TURN_JOURNAL_CONTRACT.md,CONVERSATION_PROJECTION_CONTRACT.md,END_TO_END_TURN_WALKTHROUGH.md}`. The current reviewed verdict is now `ready_for_external_handoff`: outside review may start, but runtime architecture implementation should still remain paused until that review is received or explicitly waived.

Required governing references:
- `docs/system_forensics/INDEX.md`
- `docs/system_forensics/SYSTEM_VERDICT.md`
- `docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`
- `docs/system_forensics/TARGET_ARCHITECTURE.md`
- `docs/system_forensics/MIGRATION_PROGRAM.md`
- `docs/system_forensics/EVIDENCE_MAP.md`
- `docs/system_forensics/QUALITY_GOVERNANCE_AUDIT.md`
- `docs/system_forensics/EXTERNAL_RESEARCH_PACKET.md`

Rule:
- future implementation may not treat the next weak family as the whole design unit;
- future implementation must cite the governing system-forensics document being repaired;
- future implementation must state which machine-readable contract or executable mechanism is being materialized;
- future implementation must explain how it avoids repeating the earlier external-analysis failure mode where truthful but fragmented docs still allowed local repairs.

## Truth Update Rule
- `STATE.md` may record structural completion separately from practical completion.
- `STRUCTURE.md` must list any new canonical closure document or correction report.
- A previous structural `done` claim is not a lie by default; it is incomplete if practical closure has not yet been proven.
- When such a mismatch is discovered, the canon must be corrected explicitly rather than hidden.

## Next Operating Rule
Root-first implementation sequence `1..10` is no longer the active blocker. The bounded `consult/media cue continuity` fix is now proven improved on the practical path by `r36g`.

Required follow-up order:
1. freeze and accept the exact live path for `booking-manage temporal clue grounding / follow-up continuity` on `r36g`;
2. only after that, open one bounded implementation block for that mechanism;
3. keep `oracle contract / taxonomy alignment` and evaluator residue separate unless fresh evidence proves they are the same mechanism.

Rule:
- no new runtime implementation starts from `dialog 9` as a standalone scenario patch;
- each follow-up must name the shared mechanism, broken invariant, open-world envelope, and exact live path before code;
- no consult/media regression is admissible after `r36g` without new replay evidence.
