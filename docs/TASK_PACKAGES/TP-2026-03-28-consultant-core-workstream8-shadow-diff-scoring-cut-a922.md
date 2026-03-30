# TP-2026-03-28-consultant-core-workstream8-shadow-diff-scoring-cut-a922

## Title / Goal
Add structured shadow diff scoring over `RuntimeTraceContractV1` so proof tooling can quantify `owner -> binding -> action -> state` drift by canonical JSON-pointer paths instead of only hashing flat `decision_meta` / `decision_trace` summaries.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 8 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 8 — Observability, Proof, and Release Gates`
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-workstream8-runtime-trace-contract-cut-a922.md`
- `AGENTS.md` — one-web-search / root-cause / evidence gates

## One Web Search (mandatory before implementation)
- Query: `RFC 6901 JSON Pointer IETF`
- Date/time: `2026-03-28T22:41:00+05:00`
- Opened sources:
  - `https://datatracker.ietf.org/doc/html/rfc6901`
- High-signal source quality:
  - Official IETF standards-track specification for JSON Pointer, which gives the canonical path syntax needed to express machine-readable diff locations inside nested JSON trace contracts.
- Found reusable idea:
  - Emit diff evidence at stable JSON-pointer paths so mismatches are addressable, comparable, and safe to aggregate in proof tooling.
- Reuse / integrate / build decision:
  - `integrate + build`
- Why:
  - Reuse the RFC pointer syntax directly; build repo-local scoring because the existing shadow replay tool compares hashes only and does not score canonical trace-contract drift.
- Rejected options:
  - keep hash-only replay comparison: rejected because it reports mismatch/no-mismatch but not where or how severe the drift is.
  - invent ad hoc path strings: rejected because W8 needs a standard machine-readable pointer syntax.

## Root Cause (mandatory)
### Symptom
`Workstream 8` still lacks shadow diff scoring even after `RuntimeTraceContractV1` exists, so proof tooling cannot quantify or localize transition drift.

### Minimal Reproduction
1. Inspect `ops/shadow_replay.py`.
2. Observe that `_summarize_bundle(...)` reduces bundles to compacted `decision_meta` hashes and trace signatures only.
3. Observe that `_build_report(...)` can only emit `ok` / `mismatch` based on meta/trace hashes and has no runtime-trace scoring or pointer-level mismatch output.

### Evidence
- `ops/shadow_replay.py`
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md`
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-workstream8-runtime-trace-contract-cut-a922.md`

### Five Whys
1. Why is W8 still open after the trace-contract cut?
   - Because the repo still cannot score runtime trace drift.
2. Why is that a problem?
   - Because proof remains binary and narrative: hashes differ, but the tooling cannot say which transition drifted.
3. Why doesn’t the current shadow replay help enough?
   - Because it only compares compacted meta hashes and flattened stage signatures.
4. Why use JSON-pointer paths?
   - Because the trace contract is nested JSON, and pointer syntax gives stable machine-readable diff locations.
5. Why is this the right next block?
   - Because `shadow diff scoring exists` is the next explicit W8 completion criterion after the trace contract itself exists.

### Root Cause Statement
The proof lane still treats shadow replay as a hash comparison over compacted flat payloads, so it cannot score or localize drift in the new canonical runtime trace contract.

### Fix Mechanism
Extend `ops/shadow_replay.py` to extract `runtime_trace_contract`, flatten it into RFC 6901 JSON-pointer paths, compute weighted section scores across owner/binding/action/state transitions, and report pointer-level mismatches; add deterministic tests for the scorer and report output.

## Invariant
- Existing shadow replay hash comparison stays intact.
- No runtime control-path behavior changes.
- No changes to trace retention or production message metadata semantics.

## Scope
- `RuntimeTraceContractV1` shadow diff scoring in proof tooling.
- Pointer-level mismatch reporting in `ops/shadow_replay.py`.
- Deterministic tests for scorer + report output.

## Out of Scope
- Release gate standardization.
- Canary rollout policy.
- Broad changes in `ops/diagnose.py` bundle generation.
- Legacy webhook trace emitters.

## Touch-list
- `ops/shadow_replay.py`
- `tests/test_shadow_replay.py`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-workstream8-shadow-diff-scoring-cut-a922.md`

## Plan
1. Add `runtime_trace_contract` extraction helpers in `ops/shadow_replay.py`.
2. Add JSON-pointer flattening and weighted shadow diff scoring for owner/binding/action/state sections.
3. Extend the report output with score + mismatch pointers.
4. Add deterministic tests for scoring and report rendering.
5. Update repo truth if the focused envelope stays green.

## DoD
- Shadow replay can score `runtime_trace_contract` drift.
- Report includes score and pointer-level mismatch evidence.
- Deterministic tests cover both scoring and rendered report output.
- Repo truth updated.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile ops/shadow_replay.py tests/test_shadow_replay.py`
- `pytest -q tests/test_shadow_replay.py`
- `git diff --check`

## Evidence
- New shadow diff scoring logic
- Deterministic tests for score + report
- Updated `STATE.md` entry

## Release Safety
- Local worktree only
- No deploy / no rollout in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert touched files.

## No-go
- No runtime-path behavior changes.
- No replacement of existing hash comparison; scoring must be additive.
- No W8 release-gate standardization in this block.

## Risks / Blockers
- Existing trace bundles may not always contain `runtime_trace_contract`; the scorer must degrade explicitly without crashing.
- Pointer flattening must treat missing values and container/list paths deterministically or the score will be noisy.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Standardized canary/go-no-go/rollback evidence still does not exist.
- Legacy proof tooling outside `ops/shadow_replay.py` still reads flat trace/meta surfaces.

### Why not in this block
- This block only closes the shadow-diff criterion.

### Risk if deferred
- W8 proof remains binary and still requires manual narrative inspection of mismatches.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream8-release-gates-standardization-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral immediately if replay/go-no-go decisions start using the new trace contract without any score-based comparison.

## Next-block Contract (mandatory)
### Next block objective
Standardize `canary / go-no-go / rollback` evidence so W8 closure is fully machine-readable.

### First deterministic check command
`rg -n "go-no-go|rollback|canary|runtime_trace_contract|shadow_score" ops scripts docs truffles-api/tests tests -S`

### Blocked-by conditions
- Shadow diff scoring block must be green and repo truthfully updated.

### Owner role for closure
- Brain / Top Architect
