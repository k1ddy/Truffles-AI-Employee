# TP-2026-03-28-consultant-core-workstream8-closeout-proof-pass-a922

## Title / Goal
Run the final deterministic closeout proof for `Workstream 8 — Observability, Proof, and Release Gates` and only mark it done if canonical trace, shadow diff scoring, and standardized release-gate evidence are all machine-checked.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 8 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 8 — Observability, Proof, and Release Gates`
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-workstream8-runtime-trace-contract-cut-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-workstream8-shadow-diff-scoring-cut-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-workstream8-release-gates-standardization-cut-a922.md`

## One Web Search (mandatory before implementation)
- `n/a` — closure-only proof pass; no new design research or external implementation choice in this block.

## Root Cause (mandatory)
### Symptom
`Workstream 8` still cannot close honestly until there is one deterministic proof pass that covers all three required observability/proof/release artifacts together.

### Minimal Reproduction
1. Verify `RuntimeTraceContractV1` exists and is emitted on the active path.
2. Verify `ops/shadow_replay.py` scores runtime-trace drift.
3. Verify the quality chain emits machine-readable `release_gate.json` evidence.
4. Observe that without an aggregate closeout proof, closure still depends on narrative state updates.

### Evidence
- `truffles-api/app/core/runtime_trace_contract.py`
- `ops/shadow_replay.py`
- `scripts/quality_chain_controller.sh`
- deterministic tests listed below

### Five Whys
1. Why is W8 still open after the last implementation cuts?
   - Because closure has not been proven as one deterministic envelope.
2. Why is that needed?
   - Because W8 is about proof and release gates, not only individual code additions.
3. Why are the prior focused tests not enough by themselves?
   - Because they prove each family locally, but not the workstream as an integrated contract.
4. Why use architecture guards here?
   - Because they freeze the presence of the new proof/release artifacts at the repo boundary.
5. Why is this the right final step?
   - Because all implementation families are already in place; only workstream closeout remains.

### Root Cause Statement
`Workstream 8` still lacks one final machine-checked closeout envelope spanning active-path trace contracts, shadow diff scoring, and standardized release-gate evidence.

### Fix Mechanism
Add aggregate deterministic guards and run the final focused closeout envelope; then update repo truth and close the workstream only if everything stays green.

## Invariant
- No runtime behavior changes.
- No weakening of existing proof/release checks.
- Closure remains deterministic-only in this block.

## Scope
- Aggregate W8 architecture guards.
- Final focused deterministic closeout envelope.
- Repo truth update.

## Out of Scope
- New runtime features.
- New release thresholds.
- Live acceptance runs.

## Touch-list
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-workstream8-closeout-proof-pass-a922.md`

## Plan
1. Add aggregate W8 closeout guards.
2. Run the focused deterministic proof envelope.
3. Update repo truth and close `Workstream 8` only if green.

## DoD
- Aggregate guards prove W8 artifacts exist and are wired into hotspots.
- Focused deterministic closeout envelope is green.
- `STATE.md` truthfully marks `Workstream 8` done.

## Work Mode
- `closure`

## Checks
- `python3 -m py_compile truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "runtime_trace_contract or turn_result_trace"`
- `pytest -q tests/test_shadow_replay.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_chain_controller.py -k "release_gate or rollback"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "workstream8"`
- `git diff --check`

## Evidence
- Aggregate W8 guards
- Focused deterministic closeout outputs
- Updated `STATE.md` entry

## Release Safety
- Local worktree only
- No deploy / no rollout in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert touched files.

## No-go
- No premature `done` without the full focused proof envelope.
- No narrative-only closure.

## Risks / Blockers
- A stale guard may expose residual drift that still needs one more implementation cut.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- none if closure passes

### Why not in this block
- n/a

### Risk if deferred
- n/a

### Linked follow-up Task Package(s)
- none

### Expiry / trigger to stop deferral
- n/a

## Next-block Contract (mandatory)
### Next block objective
Program closeout synthesis beyond `Workstream 8`, if required by Brain / Top Architect.

### First deterministic check command
`rg -n "Workstream 8|runtime_trace_contract|release_gate_evidence|shadow_score" STATE.md STRUCTURE.md truffles-api/tests/architecture/test_legacy_freeze_guard.py`

### Blocked-by conditions
- Any red check in the closeout envelope.

### Owner role for closure
- Brain / Top Architect
