# TP-2026-03-28-consultant-core-workstream7-capability-registry-snapshot-governance-cut-a922

## Title / Goal
Create the remaining phase-1 governed control-plane owner for `Workstream 7` by moving capability-policy compilation out of `capability_manifest_service.py` into one versioned capability registry snapshot owner.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 7 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 7 — Minimum Control Plane`
- `AGENTS.md` — task package / one-web-search / root-cause gates

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com "Published Interface" configuration object`
- Date/time: `2026-03-28T21:22:00+05:00`
- Opened sources:
  - `https://martinfowler.com/bliki/PublishedInterface.html`
- High-signal source quality:
  - Martin Fowler primary architecture source on separating a published interface from internal implementation so downstream callers stop depending on ad hoc internals.
- Found reusable idea:
  - keep compatibility readers on a stable published interface, but move the real ownership and change surface behind a narrower governed implementation boundary.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo already has stable compatibility callers of `capability_manifest_service.py`; the missing W7 cut is to move actual capability-policy compilation behind a versioned snapshot owner while keeping the compatibility interface thin.
- Rejected options:
  - leave capability-policy compilation in `capability_manifest_service.py` and only add more comments: rejected because runtime growth would still happen in the compatibility consumer.
  - merge this into `tool_registry_snapshot_service.py`: rejected because capability-policy decisions and tool registry metadata are separate governance surfaces.

## Root Cause (mandatory)
### Symptom
`Workstream 7` is still missing a true phase-1 capability registry object because `capability_manifest_service.py` still compiles tool protocol policy, fact-scope policy, handoff policy, and their env/runtime fallback rules inline.

### Minimal Reproduction
1. `rg -n "get_runtime_capabilities|TOOL_POLICY_ENFORCEMENT|TOOL_PROTOCOL_DENY_BY_DEFAULT|allowed_fact_scopes|handoff_policy" truffles-api/app/services/capability_manifest_service.py`
2. Inspect `resolve_tool_protocol_decision(...)`, `resolve_fact_scope_decision(...)`, and `resolve_handoff_policy_decision(...)`.
3. Observe that the compatibility service still owns raw runtime/env interpretation instead of reading a versioned compiled snapshot.

### Evidence
- `truffles-api/app/services/capability_manifest_service.py`
- `truffles-api/app/services/capabilities_runtime.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/services/policy_context_snapshot_service.py`

### Five Whys
1. Why is `Workstream 7` not honestly closable yet?
   - Because one phase-1 governance surface is still missing: capability policy / protocol compilation.
2. Why is that a problem?
   - Because capability growth still requires editing a live compatibility service instead of a governed snapshot owner.
3. Why is `capability_manifest_service.py` the blocker?
   - Because it directly reads runtime capability payloads and env toggles and turns them into active decisions.
4. Why is that different from a compatibility shim?
   - Because the decision logic itself still lives there, so published callers depend on its internal branching.
5. Why add a versioned snapshot owner now?
   - Because W7 completion requires phase-1 registry objects to exist and runtime to read compiled snapshots instead of ad hoc constants/branching.

### Root Cause Statement
The remaining W7 blocker is that capability-policy compilation still lives inline in `capability_manifest_service.py`, so runtime capability / protocol growth still depends on ad hoc compatibility-service branching instead of a versioned capability registry snapshot owner.

### Fix Mechanism
Add a versioned capability registry snapshot service that compiles fact-scope policy, handoff policy, and tool-protocol policy from runtime capabilities plus bounded env gates, then switch `capability_manifest_service.py` and live consumers to read that snapshot while freezing the old service as a thin published interface.

## Invariant
- No behavior change to current fact-scope, handoff-policy, or tool-protocol decisions.
- No change to current deny-by-default semantics.
- No change to the public return shapes of `resolve_*` compatibility helpers.

## Scope
- Add a versioned capability registry snapshot owner.
- Move capability-policy compilation out of `capability_manifest_service.py`.
- Keep `capability_manifest_service.py` as a thin compatibility interface.
- Update focused tests and architecture guards.

## Out of Scope
- DB schema changes for capabilities or policy versions.
- Broad refactor of `tool_registry_service.py` execution logic.
- `Workstream 7` closeout proof pass.

## Touch-list
- `truffles-api/app/services/capability_registry_snapshot_service.py`
- `truffles-api/app/services/capability_manifest_service.py`
- `truffles-api/app/services/policy_context_snapshot_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/tests/test_capability_manifest_service.py`
- `truffles-api/tests/test_tool_protocol_gate.py`
- `truffles-api/tests/test_tool_capability_manifest.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Add versioned capability registry snapshot models and builder helpers.
2. Move raw runtime/env capability-policy compilation there.
3. Switch `capability_manifest_service.py` to thin snapshot-backed wrappers.
4. Update live readers and focused tests/guards.
5. Run deterministic checks and update repo truth.

## DoD
- Versioned capability registry snapshot object exists.
- `capability_manifest_service.py` no longer owns raw runtime/env capability-policy compilation.
- Live capability-policy readers use the snapshot-backed interface.
- Focused deterministic tests are green.
- Repo truth updated.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/capability_registry_snapshot_service.py truffles-api/app/services/capability_manifest_service.py truffles-api/app/services/policy_context_snapshot_service.py truffles-api/app/services/tool_registry_service.py truffles-api/tests/test_capability_manifest_service.py truffles-api/tests/test_tool_capability_manifest.py truffles-api/tests/test_tool_protocol_gate.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_capability_manifest_service.py truffles-api/tests/test_tool_capability_manifest.py truffles-api/tests/test_tool_protocol_gate.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "capability_registry_snapshot_owner or capability_manifest_service_uses_snapshot_owner"`
- `git diff --check`

## Evidence
- Focused deterministic outputs
- Updated architecture guards
- `STATE.md` entry for this family

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert touched files.

## No-go
- No change to the meaning of tool-protocol enforcement toggles.
- No new runtime branching in `tool_registry_service.py`.
- No broad capability schema redesign.

## Risks / Blockers
- Existing tests import compatibility helpers directly; keep those helpers stable.
- `policy_context_snapshot_service.py` depends on capability decisions; preserve its behavior byte-for-byte.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- `Workstream 7` closeout proof is still separate.
- Tool registry entries are still code-seeded inside the snapshot owner.

### Why not in this block
- This block is only about the missing capability registry object.

### Risk if deferred
- W7 would still lack one phase-1 registry object, so growth through capability-policy branching could return in compatibility services.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream7-closeout-proof-pass-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if another capability-policy or tool-protocol branch is added directly in `capability_manifest_service.py`.

## Next-block Contract (mandatory)
### Next block objective
Run a factual W7 closeout proof pass and verify that phase-1 capability/tool/policy/context governance surfaces are all snapshot-backed and guarded.

### First deterministic check command
`rg -n "get_runtime_capabilities|TOOL_POLICY_ENFORCEMENT|TOOL_PROTOCOL_DENY_BY_DEFAULT" truffles-api/app/services/capability_manifest_service.py`

### Blocked-by conditions
- This block must first land with green focused capability-policy tests and architecture guards.

### Owner role for closure
- Brain / Top Architect
