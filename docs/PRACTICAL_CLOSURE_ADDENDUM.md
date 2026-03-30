# PRACTICAL CLOSURE ADDENDUM

## Purpose
This addendum corrects the closure model for the consultant-core program.

The prior `W1-W8` closeout can stand as a **structural/contract** claim where supported by code, contracts, guards, and deterministic evidence. It must not be interpreted as automatic proof of **product-ready practical behavior**.

## Correction Summary
1. `structural/contract complete` and `product/practical complete` are different claims.
2. Current evidence does **not** prove a second semantic owner.
3. Current evidence does prove that practical quality remains open because of surfaced failure families in live replay and human audit.
4. Future closure claims must be made against explicit closure layers, not against one overloaded `done` label.

## Current Truth (2026-03-30)
- Active practical truth is replay `a922-practical-proof-20260330-r35f` plus its full human semantic audit.
- `infra_valid=true`
- `semantic_valid=false`
- `human_semantic_valid=false`
- Full human audit verdict:
  - dialogs `8 pass / 2 weak / 0 fail`
  - turns `13 pass / 2 weak / 0 fail`
- Surfaced fail blocker families on the visible human-semantic path:
  - none
- Surfaced weak residual families:
  - fact over-composition on location/parking replies
- Secondary contract/oracle residues:
  - booking-verification confirm follow-up override residue (`dialog 9 / turn 2`)
  - oracle/evaluator taxonomy drift on otherwise acceptable fact/handoff turns
- Shared mechanisms behind the surfaced weak families:
  - fact selection / fact composition
- Interpretation:
  - these families do not disprove the single semantic owner invariant
  - the previously open `owner-side booking service grounding regression` family remains closed on `r35f`
  - the previously open `collect->commit transition when required booking slots are already complete` family remains closed on `r35f`
  - the previously open `booking datetime continuity loss under policy-core degrade` family remains closed on `r35f`
  - the previously open `live check-booking collect/fallback residue` family remains closed on `r35f`: `dialog 9 / turns 1-2` stay on the correct missing identity/reference slot and no longer re-ask temporal information
  - the scoped `booking verification confirm recovery under degraded invalid_schema` family remains closed on `r35f`: `dialog 9 / turn 2` still preserves `booking_verification_mode=confirm` on the visible path and asks only for name/phone
  - the re-opened `parking owner-grounding` family is now closed on `r35f`: `dialog 6 / turn 1` again surfaces the parking fact on the visible path because owner grounding now keeps `pack_refs=["parking"]`
  - `dialog 5 / turn 1` and `dialog 6 / turn 1` still remain broader than needed because the fact reply over-composes adjacent branch facts
  - `dialog 7 / turn 1` no longer re-surfaces as a weak/fail turn on the current truth, but this block does not claim a separate media-family closure
  - a trace-visible residual still exists on `dialog 2 / turn 5` (`appointment_skip_reason=datetime_parse_failed` before transparent handoff), but it is not the current practical blocker because the visible response remains product-acceptable
  - `dialog 9 / turn 2` still carries a secondary contract residue (`handoff_not_allowed` -> collect override), but the visible reply remains acceptable and confirm-aware
  - practical blockers must now be understood and fixed at the shared-mechanism level, not as isolated domain scenarios
  - practical/product closure still remains open because the run is human-semantic amber rather than green and the deterministic contract lane is still red

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
Before any new product runtime implementation after `r35f`, the consultant-core lane must start from the self-contained corpus in `docs/system_forensics/`.

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
If product work continues after the system-forensics publication block, the next implementation block is no longer a direct weak-family patch. It starts with the first architecture-recovery implementation wave: `fact architecture contract materialization`, using `fact over-composition on location/parking replies` only as evidence for the missing shared mechanism `fact selection / fact composition`. The admissible starting bundle is therefore the full-path RCA contract above plus the workflow-hardening artifacts (`manual_audit_workspace.*`, `family_registry.json`, `judge_conflicts.jsonl`, `llm-quality-trends`) plus the new system-forensics corpus (`docs/system_forensics/FACT_ARCHITECTURE_AUDIT.md`, `TARGET_ARCHITECTURE.md`, `MIGRATION_PROGRAM.md`, `EVIDENCE_MAP.md`, `QUALITY_GOVERNANCE_AUDIT.md`).
