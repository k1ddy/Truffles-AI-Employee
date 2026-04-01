# TP-2026-03-28-consultant-core-workstream7-closeout-proof-pass-a922

## Title / Goal
Run the factual closeout proof for `Workstream 7` by freezing the phase-1 governance surfaces with deterministic fitness guards and only mark `Workstream 7` done if the governed snapshot owners fully cover the remaining growth seams.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 7 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 7 — Minimum Control Plane`
- `AGENTS.md` — proof/evidence / one-web-search / root-cause gates

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com "architectural fitness function"`
- Date/time: `2026-03-28T21:34:00+05:00`
- Opened sources:
  - `https://martinfowler.com/articles/fitness-functions-data-products.html`
- High-signal source quality:
  - Thoughtworks / Martin Fowler primary architecture source on using automated fitness functions to enforce governance rules and evaluate whether implementation stays close to stated design objectives.
- Found reusable idea:
  - W7 closeout should be expressed as automated governance assertions over the phase-1 snapshot surfaces instead of a narrative claim.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo already has architecture guards; the missing step is to promote W7 completion criteria into a bounded deterministic proof envelope.
- Rejected options:
  - mark W7 done based only on the accumulated narrative in `STATE.md`: rejected because W7 is specifically about governed growth and needs fitness-style proof.
  - broaden this into W8 trace/release work: rejected because W7 closeout should stay on phase-1 control-plane ownership only.

## Root Cause (mandatory)
### Symptom
`Workstream 7` is still `open` even after the recent snapshot-owner cuts because there is no single deterministic closeout proof showing that all phase-1 governance surfaces are snapshot-backed and that runtime hotspots no longer own those growth seams.

### Minimal Reproduction
1. Read the current `STATE.md` top entries for W7.
2. Observe that each bounded cut is green individually, but there is no closeout TP or aggregate proof pass yet.
3. Inspect `truffles-api/tests/architecture/test_legacy_freeze_guard.py` and note that W7 guards exist per seam but not as one closeout envelope.

### Evidence
- `STATE.md`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- W7 TP files under `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-workstream7-*.md`

### Five Whys
1. Why is W7 not closed yet?
   - Because the repo has seam-by-seam evidence but no closeout proof envelope.
2. Why is that a problem?
   - Because completion still depends on narrative synthesis instead of machine-checked governance proof.
3. Why are architecture guards the right tool?
   - Because W7 is about preventing runtime-core growth through branching, which is best enforced by fitness-style boundary assertions.
4. Why not wait until W8?
   - Because W7 has its own completion criteria and should close as soon as phase-1 control-plane ownership is proven.
5. Why is this now the honest next block?
   - Because the last remaining W7 implementation seam — capability registry ownership — has already been cut in the previous block.

### Root Cause Statement
The remaining W7 blocker is proof debt: phase-1 governance owners now exist in code, but the repo still lacks one deterministic closeout envelope that proves runtime hotspots consume snapshot owners instead of owning governance growth themselves.

### Fix Mechanism
Add explicit W7 closeout guards that assert the phase-1 snapshot owners exist and that the former hotspot files (`policy.py`, `intent_service.py`, `policy_tool_projector.py`, `capability_manifest_service.py`) only consume those governed owners, then run the combined deterministic envelope and update repo truth.

## Invariant
- No behavior changes.
- No new runtime logic.
- No weakening of existing guards.

## Scope
- W7 closeout architecture guards.
- Focused deterministic closeout envelope.
- Repo truth update if and only if the closeout envelope stays green.

## Out of Scope
- `Workstream 8` trace/release gates.
- New governance owners.
- Broad refactors in runtime code.

## Touch-list
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`
- `docs/TASK_PACKAGES/TP-2026-03-28-consultant-core-workstream7-closeout-proof-pass-a922.md`

## Plan
1. Add W7 closeout guards for phase-1 snapshot-owner existence and hotspot consumption.
2. Run the focused deterministic closeout envelope.
3. If green, mark `Workstream 7` done in repo truth.

## DoD
- W7 closeout guards exist.
- Focused deterministic closeout envelope is green.
- `STATE.md` truthfully marks `Workstream 7` done.
- Repo truth updated.

## Work Mode
- `closure`

## Checks
- `python3 -m py_compile truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_policy_handler_runtime.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_tool_registry_snapshot_service.py truffles-api/tests/test_capability_registry_snapshot_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_capability_manifest_service.py truffles-api/tests/test_tool_capability_manifest.py truffles-api/tests/test_tool_protocol_gate.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py -k "routing_policy or conversation_snapshot"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "workstream7_phase1_snapshot_owners_exist or workstream7_runtime_hotspots_use_governed_snapshot_owners or capability_registry_snapshot_owner or capability_manifest_service_uses_snapshot_owner or policy_runtime_snapshot_owner or tool_registry_snapshot_owner or policy_core_context_snapshot_owner or policy_vocabulary_snapshot_owner or policy_prompt_snapshot_owner or controller_plan_prompt_snapshot_owner"`
- `git diff --check`

## Evidence
- Focused deterministic outputs
- New W7 closeout guards
- `STATE.md` closeout entry

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert touched files.

## No-go
- No premature `done` if any closeout guard fails.
- No W8 trace/release work in this block.
- No narrative-only close claim.

## Risks / Blockers
- Existing architecture guard file has unrelated historical residues; keep the closeout proof on a targeted subset.
- If the aggregate guard finds another live governance seam, W7 stays `open` and the next block must cut that seam instead of forcing closeout.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- W8 observability / proof / release gates remain open.
- Some snapshot owners still use code-seeded defaults rather than external data assets.

### Why not in this block
- This block only proves W7 phase-1 ownership.

### Risk if deferred
- W7 would remain narrative-only and could regress without one aggregate governance proof envelope.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream8-trace-contract-proof-plane-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral immediately if any new policy/tool/capability/context growth is added back into runtime hotspots instead of snapshot owners.

## Next-block Contract (mandatory)
### Next block objective
Start `Workstream 8` by freezing the trace contract across owner / binding / action / state transitions.

### First deterministic check command
`rg -n "decision_trace|trace contract|policy_core_mode|binding_plan|conversation_projection|turn_journal" truffles-api/app truffles-api/tests`

### Blocked-by conditions
- W7 closeout proof must be green and truthfully marked `done`.

### Owner role for closure
- Brain / Top Architect
