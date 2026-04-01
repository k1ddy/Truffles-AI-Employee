# TP-2026-03-28-consultant-core-workstream7-policy-snapshot-governance-cut-a922

## Title / Goal
Create the first governed policy snapshot boundary for `Workstream 7` by moving routing-policy and resolved policy-pack compilation out of `webhook/policy.py` into one versioned control-plane owner, so runtime reads compiled snapshots instead of rebuilding policy state from scattered constants and override helpers.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 6 done`, program `open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 7 — Minimum Control Plane`
- `docs/system_forensics/files/app_routers_webhook_policy.md`
- `docs/system_forensics/files/app_services_reasoning_core.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com feature toggles release toggles configuration`
- Date/time: `2026-03-28T19:12:00+05:00`
- Opened sources:
  - `https://martinfowler.com/articles/feature-toggles.html?r=prd-ffs`
- High-signal source quality:
  - Martin Fowler primary-source article describing separation between toggle/router decisions and core code, plus preference for explicit configuration layers.
- Found reusable idea:
  - keep decision/configuration in a dedicated router/config layer and inject the resolved decision into runtime callsites instead of coupling branch logic to every consumer.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo already has registry/runtime override data sources; the missing piece is a compiled snapshot owner instead of ad hoc reads from `policy.py`.
- Rejected options:
  - directly rewriting all policy text-detection logic into manifests in one block: rejected because it is too wide for the first W7 cut.
  - starting with tool execution branching in `tool_registry_service.py`: rejected because `policy.py` is the more concentrated governance hotspot and gives a cleaner first cut.

## Root Cause (mandatory)
### Symptom
`truffles-api/app/routers/webhook/policy.py` still owns routing-matrix reads plus policy-pack/config/registry/runtime override compilation locally, and active runtime consumers read that mixed helper warehouse instead of a versioned compiled snapshot.

### Minimal Reproduction
1. `rg -n "_get_routing_policy\(|_resolve_runtime_policy_overrides\(|_resolve_registry_policy_overrides\(|_apply_runtime_policy_overrides\(|_apply_registry_policy_overrides\(|_get_policy_pack\(" truffles-api/app/routers/webhook/policy.py truffles-api/app/services/reasoning_core.py`
2. Inspect `policy.py` and observe local routing-matrix, runtime override, registry override, and policy-pack merge logic.
3. Observe `reasoning_core.py` reading routing through `_get_routing_policy(...)` instead of a compiled governance artifact.

### Evidence
- `truffles-api/app/routers/webhook/policy.py`
- `truffles-api/app/services/reasoning_core.py`
- focused deterministic tests/guards for policy runtime behavior

### Five Whys
1. Why is Workstream 7 still open after W1-W6?
   - Because runtime still grows through scattered policy constants and helper-local override compilation.
2. Why is that a problem?
   - Because policy growth still happens by editing runtime code paths instead of one governed object.
3. Why start with policy snapshot instead of all registries at once?
   - Because `policy.py` is the densest remaining governance hotspot and already has explicit registry/runtime data inputs.
4. Why not leave wrappers in `policy.py` and only document them?
   - Because that keeps compilation authority local to the legacy helper warehouse.
5. Why add a versioned snapshot?
   - Because W7 requires registry/control objects that are explicit, versioned, and consumable by runtime without re-deriving them ad hoc.

### Root Cause Statement
The first W7 blocker is that routing-policy and resolved policy-pack state are still compiled inside `webhook/policy.py` from constants, config, runtime capabilities, and registry overrides instead of coming from one versioned governance snapshot owner.

### Fix Mechanism
Add a new policy snapshot service with versioned routing/policy-pack artifacts, move compilation there, switch runtime callsites to consume the snapshots, and freeze the new boundary with focused tests and architecture guards.

## Invariant
- No change to current policy-pack resolution semantics.
- No change to hard-law override rules.
- No change to active routing behavior for known conversation states.

## Scope
- New versioned policy snapshot owner service.
- `policy.py` routing/policy-pack wrappers delegated to that owner.
- `reasoning_core.py` routing read switched to snapshot owner.
- Focused tests and architecture guards.

## Out of Scope
- Full manifest-driven rewrite of policy keyword/section logic.
- Tool registry demotion.
- Workstream 8 trace/canary work.

## Touch-list
- `truffles-api/app/services/policy_snapshot_service.py`
- `truffles-api/app/routers/webhook/policy.py`
- `truffles-api/app/routers/webhook/runtime_primitives.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_policy_handler_runtime.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Add versioned routing/policy-pack snapshot models and compile helpers.
2. Delegate policy-pack and routing reads in `policy.py` to the snapshot owner.
3. Switch `reasoning_core.py` routing read to the snapshot owner.
4. Update focused runtime tests.
5. Add architecture guards proving `policy.py` no longer owns override compilation.
6. Run focused deterministic checks and update repo truth.

## DoD
- Versioned policy snapshot objects exist.
- Runtime routing/policy-pack reads use compiled snapshots instead of local `policy.py` override-compilation logic.
- Focused deterministic tests are green.
- Repo truth updated.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/policy_snapshot_service.py truffles-api/app/routers/webhook/policy.py truffles-api/app/routers/webhook/runtime_primitives.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_policy_handler_runtime.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_policy_handler_runtime.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_reasoning_core.py -k "routing_policy or conversation_snapshot"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "policy_runtime_snapshot_owner or reasoning_core_routing_reads_compiled_policy_snapshot"`
- `git diff --check`

## Evidence
- Focused deterministic outputs
- Updated architecture guard
- `STATE.md` entry for this family

## Release Safety
- Local worktree only
- No rollout / no deploy in this block
- Rollback: revert touched files in this worktree

## Rollback
- Revert touched files.

## No-go
- No broad policy rewrite.
- No new semantic hardcode in core.
- No change to user-visible policy copy unless contract tests require it.

## Risks / Blockers
- `policy.py` is large; move only snapshot-compile ownership in this block.
- Existing tests monkeypatch `policy.py` internals; they need targeted retargeting, not broad rewrites.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Policy text/keyword detection remains in `policy.py`.
- Tool registry and context-recipe governance remain outside this block.

### Why not in this block
- They are separate W7 families after the first snapshot owner extraction.

### Risk if deferred
- W7 starts correctly, but runtime still has later governance hotspots beyond routing/policy-pack compilation.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream7-tool-registry-governance-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if new policy growth is added through `policy.py` constants or override helpers instead of the snapshot owner.

## Next-block Contract (mandatory)
### Next block objective
Move tool/workflow registry reads behind the same minimum-control-plane pattern so runtime tool additions stop requiring core branching by default.

### First deterministic check command
`rg -n "TOOL_ACTIONS|CALENDAR_TOOL_ACTIONS|CATALOG_TOOL_ACTIONS|resolve_tool_certification_decision|is_tool_action\(" truffles-api/app/services/tool_registry_service.py truffles-api/app/core/turn_executor.py`

### Blocked-by conditions
- This block must first land with green focused policy snapshot tests and guards.

### Owner role for closure
- Brain / Top Architect
