# TP-2026-03-28-consultant-core-workstream8-release-gates-standardization-cut-a922

## Title / Goal
Standardize machine-readable `canary / go-no-go / rollback` evidence in the acceptance chain so release decisions no longer live only in mutable chain state, markdown briefs, and ad hoc rollback artifacts.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 8 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 8 — Observability, Proof, and Release Gates`
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-workstream8-runtime-trace-contract-cut-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-workstream8-shadow-diff-scoring-cut-a922.md`
- `AGENTS.md` — one-web-search / root-cause / evidence gates

## One Web Search (mandatory before implementation)
- Query: `Google SRE canary releases rollback evidence`
- Date/time: `2026-03-28T23:22:00+05:00`
- Opened sources:
  - `https://sre.google/workbook/canarying-releases/`
- High-signal source quality:
  - Google SRE Workbook primary-source guidance on canary evaluation, release-process integration, and rollback on bad canaries.
- Found reusable idea:
  - Canary value comes from integrating evaluation into the release process and reacting automatically when the canary is bad.
- Reuse / integrate / build decision:
  - `integrate + build`
- Why:
  - Reuse the release-process principle from SRE; build a repo-local machine-readable evidence contract because the current chain only exposes scattered state/brief/rollback artifacts.
- Rejected options:
  - keep relying on chain state + markdown brief only: rejected because it is not one standardized release-evidence artifact.
  - add manual checklist only: rejected because W8 requires machine-readable proof.

## Root Cause (mandatory)
### Symptom
`Workstream 8` still lacks standardized machine-readable release evidence even though canary/rollback mechanics already exist.

### Minimal Reproduction
1. Inspect `scripts/quality_chain_controller.sh`.
2. Observe that finalize/rollback decisions are spread across mutable chain state, `brief_for_next_agent.md`, `summary.json`, and `rollback.json`.
3. Observe there is no single versioned artifact that says `decision=go|hold|no_go|rollback`, with the evidence pointers needed for release handoff.

### Evidence
- `scripts/quality_chain_controller.sh`
- `truffles-api/tests/test_booking_quality_chain_controller.py`
- `docs/TASK_PACKAGES/TP-2026-03-02-p13-canary-rollback-full-closure-a1.md`

### Five Whys
1. Why is W8 still open after trace contract and shadow scoring?
   - Because release evidence is still not standardized.
2. Why is that a problem?
   - Because go/no-go/rollback decisions remain distributed across several files and one mutable chain-state payload.
3. Why doesn’t the current chain controller close this already?
   - Because it records state transitions, but not one canonical release-gate artifact.
4. Why is one artifact necessary?
   - Because release/proof handoff must be machine-readable and deterministic, not reconstructed from multiple surfaces.
5. Why is this the right next block?
   - Because it closes the last explicit W8 criterion after trace contract and shadow scoring already exist.

### Root Cause Statement
The acceptance chain has executable canary/rollback mechanics, but it does not emit one standardized machine-readable release-gate artifact that captures the decision and its supporting evidence.

### Fix Mechanism
Add a versioned `release_gate_evidence` contract and have `scripts/quality_chain_controller.sh` emit `release_gate.json` on finalize/rollback with normalized decision, reason, rollback state, and evidence paths; cover it with deterministic chain-controller tests.

## Invariant
- Existing chain-state transitions remain intact.
- Existing rollback behavior remains intact.
- No runtime-core behavior changes.

## Scope
- Standardized machine-readable release-gate artifact for quality chain steps.
- Deterministic tests for canonical/full and canary-rollback evidence emission.
- Repo truth updates.

## Out of Scope
- Changing canary thresholds.
- Running live quality chains.
- Broad `ops/diagnose.py` audit redesign.
- Production rollout automation outside the existing chain controller.

## Touch-list
- `contracts/runtime/release_gate_evidence.v1.jsonschema`
- `scripts/quality_chain_controller.sh`
- `truffles-api/tests/test_booking_quality_chain_controller.py`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-workstream8-release-gates-standardization-cut-a922.md`

## Plan
1. Add a versioned release-gate evidence contract.
2. Make the quality chain controller emit `release_gate.json` for finalize/rollback outcomes.
3. Add focused deterministic tests for canonical promote evidence and canary rollback evidence.
4. Update repo truth if the focused envelope stays green.

## DoD
- One machine-readable `release_gate.json` artifact exists for chain finalize/rollback outcomes.
- Artifact includes normalized decision + evidence pointers.
- Deterministic tests cover canonical and rollback paths.
- Repo truth updated.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/tests/test_booking_quality_chain_controller.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_booking_quality_chain_controller.py -k "release_gate or rollback"`
- `bash -n scripts/quality_chain_controller.sh`
- `git diff --check`

## Evidence
- `release_gate.json` contract + writer
- Deterministic chain-controller tests
- Updated `STATE.md` entry

## Release Safety
- Local worktree only
- No deploy / no rollout in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert touched files.

## No-go
- No manual-only evidence path.
- No weakening of existing canary rollback behavior.
- No runtime-core changes.

## Risks / Blockers
- Existing tests may assume chain artifacts are limited to state + rollback + brief.
- Canonical release artifact must not drift from existing chain-state semantics.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Release-gate artifact may still point to shadow-score evidence indirectly rather than embedding scored JSON.

### Why not in this block
- This block standardizes the release decision artifact itself.

### Risk if deferred
- Shadow-score integration into release evidence may still require manual correlation.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream8-closeout-proof-pass-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral immediately if release decisions need to consume shadow-score fields directly.

## Next-block Contract (mandatory)
### Next block objective
Run `Workstream 8` closeout proof and decide whether shadow-score evidence must be embedded directly into the release-gate contract before honest closure.

### First deterministic check command
`rg -n "release_gate|shadow_score|rollback_executed|runtime_trace_contract" scripts ops truffles-api/tests tests contracts -S`

### Blocked-by conditions
- Release-gate artifact writer or focused tests red.

### Owner role for closure
- Brain / Top Architect
