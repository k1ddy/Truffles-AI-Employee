# TP-2026-03-18-consultant-core-proof-black-box-completion-package-a922

## Goal
Delete or bypass the remaining proof-path rewrite authority across `scripts/booking_dialog_scenarios.py` and `ops/diagnose.py` so the proof lane becomes observer/oracle only: scenario normalization / expect-repair ownership must converge onto one existing non-runtime owner surface, while `ops/diagnose.py` remains black-box audit/status logic instead of a second semantic repair lane.

## Canon refs
- `STATE.md` NOW: consultant core `debounce_buffer_owner_convergence` runtime family convergence
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-master-residual-ledger-stop-line-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-debounce-buffer-owner-convergence-package-a922.md`
- `docs/_generated/AGENT_PACKET.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after the proof-path targeted lane plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `site:refactoring.com/catalog "Split Phase" "Separate Query from Modifier"`
- **Date/time (local):** `2026-03-18 17:23:24 +0500`
- **Sources opened (from this query):**
  - `https://refactoring.com/catalog/splitPhase.html`
  - `https://refactoring.com/catalog/separateQueryFromModifier.html`
- **Source quality:**
  - high-signal / primary-style source: Martin Fowler refactoring catalog pages
- **Found ready-made solutions:**
  - `Split Phase`: separate scenario synthesis from contract normalization / repair so one stage builds candidate dialogs and another stage applies deterministic proof-contract normalization
  - `Separate Query from Modifier`: keep black-box audit/status logic observational and move expectation repair / rewrite authority out of the reporting path
- **Decision:** `reuse + integrate`
  - reuse the existing `truffles-api/app/services/llm_quality_contracts.py` owner surface for booking-scenario normalization, expectation merge, and post-coverage repair semantics instead of creating a new proof service
  - reuse the existing `truffles-api/app/services/scenario_contract_compiler.py` for machine-readable contract compilation where booking-scenario expectation compilation is already shared
  - keep `ops/diagnose.py` as the proof observer/oracle owner and remove any remaining scenario-rewrite authority from the script path rather than moving observer logic into runtime code
- **Rejected options:**
  - leave `_sanitize_llm_turns(...)` and post-coverage repair orchestration split inside `scripts/booking_dialog_scenarios.py`: rejected because the old proof authority seam stays live
  - create a new `proof_black_box_service.py`: rejected because the existing `llm_quality_contracts.py` surface already owns most extracted proof helpers
  - move proof rewrite governance into runtime/core files: rejected because proof must stay outside runtime ownership
  - combine this package with `multi_pack_acceptance`: rejected because that would hide whether black-box excision actually happened

## Root cause (mandatory)
- **Symptom:** the proof lane still repairs/normalizes scenario expectations post-hoc and still carries rewrite-governance semantics in a mixed way, so proof is not yet strictly black-box observer/oracle only.
- **Minimal reproduction:**
  - `nl -ba scripts/booking_dialog_scenarios.py | sed -n '80,100p;1629,1965p;2098,2120p' && printf '\n===OPS===\n' && nl -ba ops/diagnose.py | sed -n '890,900p;1110,1120p;6357,6565p'`
- **Evidence:**
  - `scripts/booking_dialog_scenarios.py:89`, `scripts/booking_dialog_scenarios.py:90`, `scripts/booking_dialog_scenarios.py:91`, `scripts/booking_dialog_scenarios.py:92`, and `scripts/booking_dialog_scenarios.py:93` still keep the proof script wired directly to rewrite/repair/merge helpers
  - `scripts/booking_dialog_scenarios.py:1629` still owns `_sanitize_llm_turns(...)`, which orchestrates tag normalization, expect overrides, followup rewrites, expectation merges, stateful pending-question context, and management-tag carryover inline in the generator path
  - `scripts/booking_dialog_scenarios.py:1760`, `scripts/booking_dialog_scenarios.py:1763`, and `scripts/booking_dialog_scenarios.py:1766` still mutate proof expectations inline in the script path for check-booking, reschedule, and orphan pending-question followups
  - `scripts/booking_dialog_scenarios.py:2103` and `scripts/booking_dialog_scenarios.py:2110` still keep thin but live wrappers around post-coverage repair and expectation merge instead of making the script purely generator/adapter
  - `ops/diagnose.py:6357` through `ops/diagnose.py:6565` still carries rewrite-governance counters/budget blocking semantics in the proof auditor, so any remaining proof rewrite semantics must be explicit machine-readable observation rather than a second repair lane
  - `truffles-api/app/services/llm_quality_contracts.py` already owns most extracted proof helpers (`merge_booking_scenario_expectations(...)`, `repair_booking_scenario_post_coverage_dialogs(...)`, the normalization family, and contract-sanitizer functions), so the truthful destination already exists
- **Five Whys:**
  1. Why is proof still not black-box only? Because `scripts/booking_dialog_scenarios.py` still runs a large in-script sanitization/rewrite orchestration before scenarios become proof artifacts.
  2. Why does the script still own that orchestration? Because earlier blocks extracted many helper families but left the top-level sanitize flow and wrapper seam inside the script.
  3. Why is that a problem now? Because proof semantics can still change by editing the generator script instead of one explicit proof-contract owner surface.
  4. Why is `ops/diagnose.py` still in the residual set? Because it still tracks rewrite-governance budgets and reason families, so the package must prove the auditor is only observing explicit audit artifacts and not becoming a second semantic rewrite lane.
  5. Why is `truffles-api/app/services/llm_quality_contracts.py` the truthful destination? Because it already owns the extracted scenario-contract helper family, already exposes repair/merge contracts, and can absorb the remaining sanitize orchestration without moving proof authority into runtime files or inventing another wrapper layer.
- **Root cause statement:** proof black-box ownership remains mixed because `scripts/booking_dialog_scenarios.py` still orchestrates scenario normalization / expect repair inline while `ops/diagnose.py` separately reasons about rewrite-governance semantics, instead of one explicit proof-contract owner surface feeding a pure observer/oracle path.
- **Fix mechanism:**
  - move the remaining scenario sanitize / expect-repair orchestration out of `scripts/booking_dialog_scenarios.py` into the existing `truffles-api/app/services/llm_quality_contracts.py` owner surface
  - reduce `scripts/booking_dialog_scenarios.py` to scenario synthesis, media/CLI plumbing, and thin adapter calls into the proof-contract owner
  - keep `ops/diagnose.py` observer-only by consuming explicit machine-readable proof/rewrite audit artifacts and failure-family data, not by carrying a second scenario rewrite lane

## Invariant
- proof path must stay outside runtime/core ownership; no changes may move this package into `truffles-api/app/routers/webhook/*`, `truffles-api/app/services/reasoning_core.py`, or `truffles-api/app/services/state_service.py`
- `ops/diagnose.py` may remain the observer/oracle/status owner, but it must not become a second scenario-rewrite or expectation-repair owner
- `scripts/booking_dialog_scenarios.py` must not remain a mixed generator + rewrite owner after the runtime block
- no new proof helper forest and no new proof-specific service layer counts as progress
- if the remaining sanitize flow cannot converge into existing `truffles-api/app/services/llm_quality_contracts.py` without turning it into a new god-file, stop and publish `GAP`

## Scope
- publish one package-level implementation plan for the residual `proof_black_box_completion` family
- converge remaining scenario normalization / expect-repair authority onto one explicit non-runtime proof-contract owner surface
- reduce `scripts/booking_dialog_scenarios.py` to generator/adapter responsibilities
- keep `ops/diagnose.py` on the observer/oracle side only
- update only directly impacted proof-path tests/docs/contracts for this family

## Out of scope
- `multi_pack_acceptance`
- any runtime `/webhook` ownership work
- any frozen-file work in `decision.py`, `booking.py`, or `pending.py`
- acceptance-chain execution across `beauty`, `clinic_or_dental`, and `generic_service`
- any claim of final consultant correctness or platform closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-proof-black-box-completion-package-a922.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/app/services/llm_quality_contracts.py`
- `truffles-api/app/services/scenario_contract_compiler.py`
- `scripts/booking_dialog_scenarios.py`
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/test_booking_quality_response_guard.py`
- `truffles-api/tests/test_booking_quality_expectation_sanitizer.py`
- `truffles-api/tests/test_booking_quality_scenario_contract_gate.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/services/llm_quality_contracts.py` existing booking-scenario normalization, expectation merge, sanitizer, and post-coverage repair functions
  - `truffles-api/app/services/scenario_contract_compiler.py` existing machine-readable expectation compiler
  - `scripts/booking_dialog_scenarios.py` existing CLI/data/media scaffolding
  - `ops/diagnose.py` existing observer/oracle status lane, failure-family reporting, and quality gating
  - `truffles-api/tests/test_booking_dialog_scenarios_script.py`
  - `truffles-api/tests/test_booking_quality_status_gate.py`
  - `truffles-api/tests/test_booking_quality_response_guard.py`
- **External reuse:**
  - Martin Fowler `Split Phase` and `Separate Query from Modifier` guidance from the single mandatory query above
- **Why this reuse mix is truthful:**
  - the existing `llm_quality_contracts.py` surface already owns most extracted proof semantics, so the remaining sanitize flow belongs there
  - the existing `ops/diagnose.py` path already owns proof observation and failure-family status gating, so it should stay observer-only rather than absorb more rewrite logic
  - reusing these owner surfaces deletes mixed authority instead of inventing another proof layer

## Plan
1. Publish and register this package-level TP, then switch canon to it.
2. Inventory the remaining live proof-authority seams in `scripts/booking_dialog_scenarios.py` and classify them as generator plumbing vs scenario-contract rewrite ownership.
3. Converge the remaining `_sanitize_llm_turns(...)` orchestration and its rewrite / expect-repair branches into the existing `truffles-api/app/services/llm_quality_contracts.py` owner surface.
4. Reduce `scripts/booking_dialog_scenarios.py` to generator/adapter calls, keeping only randomness, text/media generation, CLI plumbing, and owner-surface invocation.
5. Verify `ops/diagnose.py` remains observer/oracle only; if any rewrite-governance semantics still depend on in-script scenario reinterpretation, convert them to explicit machine-readable proof audit inputs rather than another repair lane.
6. Tighten targeted proof-path tests so the surviving owners are explicit and the generator script no longer owns post-hoc rewrite semantics.
7. Run the targeted proof-path lane plus required guards.
8. Record evidence in `STATE.md` only if the old proof rewrite authority seam is actually deleted or unreachable.

## DoD
- one explicit non-runtime owner surface (`truffles-api/app/services/llm_quality_contracts.py`) owns booking-scenario normalization / expect-repair semantics for this package
- `scripts/booking_dialog_scenarios.py` no longer owns the remaining sanitize / expect-repair orchestration as live authority
- `ops/diagnose.py` remains observer/oracle only for rewrite-budget / failure-family reporting and does not add a second scenario-rewrite lane
- targeted proof-path tests pass
- required architecture/session guards pass
- `STATE.md` records the deleted/unreachable old proof-authority seam with evidence

## Checks
- `nl -ba scripts/booking_dialog_scenarios.py | sed -n '80,100p;1629,1965p;2098,2120p' && printf '\n===OPS===\n' && nl -ba ops/diagnose.py | sed -n '890,900p;1110,1120p;6357,6565p'`
- `python3 -m py_compile truffles-api/app/services/llm_quality_contracts.py truffles-api/app/services/scenario_contract_compiler.py scripts/booking_dialog_scenarios.py ops/diagnose.py truffles-api/tests/test_booking_dialog_scenarios_script.py truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_response_guard.py truffles-api/tests/test_booking_quality_expectation_sanitizer.py truffles-api/tests/test_booking_quality_scenario_contract_gate.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py -k 'merge_expectations or repair_post_coverage_orphan_pending_question_turns or sanitize'`
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k 'rewrite_reason_missing or semantic_intent_override_reason_missing or post_llm_semantic_rewrite_budget_exceeded or keyword_override_budget_exceeded'`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- `pytest -q truffles-api/tests/test_booking_quality_expectation_sanitizer.py`
- `pytest -q truffles-api/tests/test_booking_quality_scenario_contract_gate.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- updated TP plus canon sync in `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_PROGRAM.md`, `docs/_generated/AGENT_PACKET.md`, and `docs/_generated/AGENT_PACKET.json`
- diff showing the old proof rewrite family reduced to one surviving proof-contract owner surface plus generator-only script boundaries
- green targeted proof-path lane plus required guards
- `STATE.md` entry naming the deleted/unreachable old proof-authority seam

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Cheap deterministic gates first:** hotspot line scan plus `python3 -m py_compile`
- **Targeted lane next:** proof script, proof status gate, expectation-sanitizer, and scenario-contract tests only
- **Stop condition:** if implementation requires a new proof service layer, keeps `_sanitize_llm_turns(...)` as mixed script authority, or makes `ops/diagnose.py` a second scenario-repair owner, stop and return to RCA instead of growing wrappers
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only proof-path validation in this worktree before any merge; no prod rollout claim in this block
- **Go/no-go signals:**
  - `scripts/booking_dialog_scenarios.py` is generator/adapter only for this family
  - `truffles-api/app/services/llm_quality_contracts.py` is the sole surviving proof-contract rewrite owner
  - `ops/diagnose.py` remains observer/oracle only
  - targeted proof-path tests pass
  - required architecture/session guards pass
- **Rollback:**
  - revert this block's changes to the touched proof files plus synced docs
  - rerun the targeted proof-path lane and required guards
- **Rollback verification:**
  - `pytest -q truffles-api/tests/test_booking_dialog_scenarios_script.py -k 'merge_expectations or repair_post_coverage_orphan_pending_question_turns'`
  - `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k 'rewrite_reason_missing or post_llm_semantic_rewrite_budget_exceeded'`
  - `pytest -q truffles-api/tests/test_booking_quality_response_guard.py`
- **Post-release monitoring window:** first post-merge proof/acceptance block only; do not advance to `multi_pack_acceptance` if the proof lane still needs in-script post-hoc rewrite authority

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted proof-path/runtime checks.

## No-go
- Do not move this package into runtime/core ownership.
- Do not leave `_sanitize_llm_turns(...)` as a live mixed authority seam in `scripts/booking_dialog_scenarios.py` and count that as progress.
- Do not create a new proof service layer before exhausting the existing `truffles-api/app/services/llm_quality_contracts.py` owner surface.
- Do not turn `ops/diagnose.py` into a second semantic rewrite or expectation-repair engine.
- Do not combine this package with `multi_pack_acceptance`.
- Do not claim consultant correctness, proof closure across all profiles, or full platform closure from this block.

## Risks / blockers
- `truffles-api/app/services/llm_quality_contracts.py` already owns many extracted helpers; if the remaining sanitize flow cannot fit there without creating a new god-file, the package may need a truthful `GAP` instead of forced convergence.
- `ops/diagnose.py` rewrite-governance status logic may still depend on audit shapes that are coupled to the current script path; if that contract is not explicit enough, the package may need one bounded audit-contract extraction rather than direct inline rewiring.
- the proof script has a large existing test surface; patch-point churn alone does not count as progress unless the old proof authority seam dies.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `multi_pack_acceptance` remains open after this package
- broader open-world closure evidence across `beauty`, `clinic_or_dental`, and `generic_service` remains outside this block
- `ops/diagnose.py` still remains the proof observer/oracle owner after this package; only rewrite authority should move out of mixed surfaces

### Why not in this block
- this package only deletes the remaining mixed proof rewrite authority
- multi-pack acceptance would hide whether proof actually became black-box observer/oracle only

### Risk if deferred
- proof can keep repairing or reinterpreting scenario contracts post-hoc instead of exposing true runtime regressions
- acceptance evidence remains easier to overfit because the generator script still owns semantic cleanup authority
- the final `multi_pack_acceptance` block would start from non-black-box proof infrastructure

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-multi-pack-acceptance-package-a922` (ordered later)

### Expiry/trigger to stop deferral
- stop deferral if any new scenario rewrite / expectation repair lands in `scripts/booking_dialog_scenarios.py` or `ops/diagnose.py` before this package is implemented

## Next-block contract (mandatory)
### Next block objective
- implement the `proof_black_box_completion` runtime/proof family convergence defined by this TP and delete or bypass the remaining mixed proof rewrite authority

### First deterministic check command
- `nl -ba scripts/booking_dialog_scenarios.py | sed -n '80,100p;1629,1965p;2098,2120p' && printf '\n===OPS===\n' && nl -ba ops/diagnose.py | sed -n '890,900p;1110,1120p;6357,6565p'`

### Blocked-by conditions
- inability to converge the remaining sanitize / expect-repair flow into the existing `truffles-api/app/services/llm_quality_contracts.py` surface without creating a new god-file
- any implementation that leaves `_sanitize_llm_turns(...)` as live mixed authority in `scripts/booking_dialog_scenarios.py`
- any implementation that makes `ops/diagnose.py` a second scenario-rewrite or expectation-repair owner
- any implementation that requires folding `multi_pack_acceptance` into this package to look green

### Owner role for closure
- Brain / Top Architect
