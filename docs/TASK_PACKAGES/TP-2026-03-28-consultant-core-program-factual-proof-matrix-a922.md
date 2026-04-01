# TP-2026-03-28-consultant-core-program-factual-proof-matrix-a922

## Title / Goal
Produce a full factual proof matrix for consultant-core recovery that does not rely only on deterministic tests: code audit, active proof-artifact audit, and explicit limits of what remains unproven without broader realistic runtime acceptance.

## Canon Refs
- `STATE.md`
- `STRUCTURE.md`
- `AGENTS.md`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- completed Workstream 1–8 Task Packages in `docs/TASK_PACKAGES/`

## One Web Search (mandatory before implementation)
- `n/a` — closure/evidence audit only; no new implementation or external design choice.

## Root Cause (mandatory)
### Symptom
The program is marked `done`, but there is no single saved factual proof matrix that explains what is proven by code facts, what is proven by runtime artifacts, and what still depends on deterministic guards or broader realistic acceptance.

### Minimal Reproduction
1. Inspect `STATE.md`.
2. Observe many bounded closure entries, but no one consolidated factual proof artifact spanning all workstreams.
3. Observe that without such a matrix, review falls back to narrative or scattered test references.

### Evidence
- `STATE.md`
- `STRUCTURE.md`
- completed Workstream 1–8 code surfaces
- proof/release tooling artifacts

### Five Whys
1. Why is an extra proof matrix needed after completion?
   - Because closure entries are distributed by workstream/family.
2. Why is that a problem?
   - Because it is harder to evaluate what is proven by structure versus by runtime artifacts.
3. Why not rely only on deterministic tests?
   - Because the question is specifically about factual proof beyond tests.
4. Why use code audit plus artifact audit?
   - Because together they show both structural authority removal and executable proof outputs.
5. Why save it now?
   - Because this is the cleanest point to freeze a full repo-backed closure explanation.

### Root Cause Statement
The repo has closure evidence by block, but not one consolidated factual proof matrix that distinguishes code proof, artifact proof, and remaining proof limits.

### Fix Mechanism
Create a saved closure audit that maps each workstream to concrete code facts, concrete generated artifacts where available, and explicit proof limits beyond deterministic tests.

## Invariant
- No runtime behavior changes.
- No architectural claims stronger than repo evidence.
- Unknowns are stated explicitly.

## Scope
- Code audit for Workstreams 1–8.
- Runtime/proof artifact audit for the active proof lane.
- One saved factual proof report.

## Out of Scope
- New implementation work.
- New acceptance runs.
- Reopening any closed workstream.

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-program-factual-proof-matrix-a922.md`
- `docs/REPORTS/artifacts/2026-03-28-consultant-core-program-factual-proof-matrix-a922.md`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Save this TP.
2. Collect code-fact evidence for Workstreams 1–8.
3. Generate/inspect active proof-lane artifacts (`shadow_replay`, `release_gate`).
4. Write one saved factual proof report with explicit proof limits.
5. Update repo truth.

## DoD
- Saved report exists.
- Each workstream has code facts and artifact facts or an explicit statement that artifact proof is indirect/limited.
- Proof limits without deterministic tests are stated explicitly.

## Work Mode
- `closure`

## Checks
- `python3 ops/shadow_replay.py --input <tmp_base> --shadow <tmp_shadow> --output <tmp_report>`
- `scripts/quality_chain_controller.sh bootstrap --mode full ...`
- `git diff --check`

## Evidence
- Saved factual proof report.
- Generated proof artifacts referenced from the report.
- Updated `STATE.md`.

## Rollback
- Revert touched doc files.

## No-go
- No new architecture claims without code/artifact evidence.
- No substitution of narrative for repo-backed facts.

## Risks / Blockers
- Artifact proof for some workstreams is indirect because the final runtime artifacts mostly prove the end-state, not each intermediate migration step separately.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Full realistic acceptance proof is still a separate evidence layer from this factual closure audit.

### Why not in this block
- This block is a saved factual audit, not a new quality run.

### Risk if deferred
- Review falls back to scattered state entries and memory.

### Linked follow-up Task Package(s)
- none

### Expiry / trigger to stop deferral
- n/a

## Next-block Contract (mandatory)
### Next block objective
Handoff / merge-closeout only, unless new repo evidence disproves current closure.

### First deterministic check command
`rg -n "Workstream [1-8]|factual proof matrix|release_gate|runtime_trace_contract|shadow_score" docs/REPORTS/artifacts STATE.md STRUCTURE.md -S`

### Blocked-by conditions
- Missing saved report or unsourced claims.

### Owner role for closure
- Brain / Top Architect
