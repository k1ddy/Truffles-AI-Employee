# TP-2026-03-28-consultant-core-workstream7-tool-registry-snapshot-governance-cut-a922

## Title / Goal
Create the second governed control-plane owner for `Workstream 7` by moving declared tool-action registry metadata and binding-affordance rules out of scattered runtime constants in `tool_registry_service.py`, `policy_tool_projector.py`, and `intent_service.py` into one versioned snapshot owner.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 7 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 7 — Minimum Control Plane`
- `docs/system_forensics/files/app_services_tool_registry_service.md`
- `docs/system_forensics/files/app_core_policy_tool_projector.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com inversion of decision configuration`
- Date/time: `2026-03-28T19:44:00+05:00`
- Opened sources:
  - `https://martinfowler.com/articles/feature-toggles.html?r=prd-ffs`
- High-signal source quality:
  - Martin Fowler primary-source article describing inversion of decision, centralized decision objects, and configuration separated from consumer code.
- Found reusable idea:
  - keep decision/configuration in one dedicated decision owner and inject resolved decisions into consumers, instead of letting each consumer hold its own local routing/config constants.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo already has tool registry/certification/protocol services; the missing piece is one compiled tool-registry snapshot owner for declared action surface and binding-affordance metadata.
- Rejected options:
  - broad rewrite of `execute_tool_action(...)`: rejected because this block is about governance extraction, not execution rewrite.
  - leaving projector affordance sets in `policy_tool_projector.py` and only documenting them: rejected because that preserves scattered growth authority.

## Root Cause (mandatory)
### Symptom
Adding or changing a tool action still requires edits in several runtime files because declared tool actions, default registry lists, policy-core allowed tool surface, and binding-affordance rules are scattered across `tool_registry_service.py`, `tool_certification_service.py`, `policy_tool_projector.py`, and `intent_service.py`.

### Minimal Reproduction
1. `rg -n "TOOL_ACTIONS|CALENDAR_TOOL_ACTIONS|CATALOG_TOOL_ACTIONS|_SERVICE_QUERY_TOOL_ACTIONS|_SPECIALIST_TOOL_ACTIONS|_BOOKING_REF_TOOL_ACTIONS|_BOOKING_CUSTOMER_TOOL_ACTIONS|_POLICY_INFO_TOOL_ACTION_MAP" truffles-api/app/services/tool_registry_service.py truffles-api/app/services/tool_certification_service.py truffles-api/app/core/policy_tool_projector.py`
2. Inspect `intent_service.py` and observe `_build_policy_core_allowed_context(...)` reading declared tool actions from `tool_registry_service.TOOL_ACTIONS`.
3. Observe projector binding rules and tool registry declaration authority living in different files.

### Evidence
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/services/tool_certification_service.py`
- `truffles-api/app/core/policy_tool_projector.py`
- `truffles-api/app/services/intent_service.py`

### Five Whys
1. Why is Workstream 7 still open after the policy snapshot cut?
   - Because tool/workflow growth still happens through scattered runtime constants instead of one governed object.
2. Why is that a problem?
   - Because new tool surface still requires editing several runtime hotspots.
3. Why start with declared tool actions and binding affordances?
   - Because those are the densest remaining governance duplicates affecting planner/projector/executor ingress.
4. Why not start by rewriting `execute_tool_action(...)`?
   - Because execution authority is already bounded; the remaining governance problem is declaration and selection metadata.
5. Why add a versioned snapshot?
   - Because W7 requires runtime to consume governed compiled snapshots instead of rebuilding registry state ad hoc.

### Root Cause Statement
The second W7 blocker is that declared tool-action registry data and binding-affordance rules are still duplicated across projector, tool-registry, certification, and policy-core allowed-context code, so runtime growth still depends on editing multiple code paths instead of one governed registry snapshot.

### Fix Mechanism
Add a versioned tool-registry snapshot service, move declared action lists and binding-affordance metadata there, switch projector/intent/tool-registry/certification readers to that owner, and freeze the new boundary with focused deterministic tests and architecture guards.

## Invariant
- No change to currently allowed tool actions.
- No change to binding arg projection semantics for existing actions.
- No change to execution branching inside `execute_tool_action(...)`.

## Scope
- New versioned tool-registry snapshot owner.
- Projector reads binding-affordance metadata from the snapshot owner.
- Policy-core allowed tool surface reads declared tool actions from the snapshot owner.
- Tool registry / certification services stop owning the default action list locally.
- Focused deterministic tests and guards.

## Out of Scope
- Full rewrite of `execute_tool_action(...)`.
- Workflow engine/runtime changes.
- Context recipe governance.

## Touch-list
- `truffles-api/app/services/tool_registry_snapshot_service.py`
- `truffles-api/app/services/tool_registry_service.py`
- `truffles-api/app/services/tool_certification_service.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/core/policy_tool_projector.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_tool_certification_service.py`
- `truffles-api/tests/test_tool_registry_snapshot_service.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Add versioned tool-registry snapshot models and compile helpers.
2. Move declared tool-action lists and binding-affordance metadata to the snapshot owner.
3. Switch `policy_tool_projector.py` to consume snapshot-owned binding metadata.
4. Switch `intent_service.py`, `tool_registry_service.py`, and `tool_certification_service.py` to consume snapshot-owned declared actions.
5. Update focused tests and add architecture guards.
6. Run deterministic checks and update repo truth.

## DoD
- Versioned tool-registry snapshot objects exist.
- Projector no longer owns local tool-affordance rule sets.
- Declared tool action surface no longer lives as duplicated default lists across runtime files.
- Focused deterministic tests are green.
- Repo truth updated.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/tool_registry_snapshot_service.py truffles-api/app/services/tool_registry_service.py truffles-api/app/services/tool_certification_service.py truffles-api/app/services/intent_service.py truffles-api/app/core/policy_tool_projector.py truffles-api/tests/test_tool_registry_snapshot_service.py truffles-api/tests/test_tool_certification_service.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_tool_registry_snapshot_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_tool_certification_service.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "tool_registry_snapshot or binding_plan or tool_action"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "policy_core_assembles_manifest_scoped_dynamic_context or policy_core_binding_plan_resolves_info_capability_to_executable_tool"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "tool_registry_snapshot_owner or policy_tool_projector_binding_rules_use_snapshot_owner or policy_core_allowed_context_reads_declared_tool_actions_from_snapshot_owner"`
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
- No broad rewrite of execution behavior.
- No new runtime branching for tool declarations.
- No silent change to allowed tool action surface.

## Risks / Blockers
- Existing runtime tests patch `tool_registry_service` directly; retarget carefully without widening the block.
- Keep `execute_tool_action(...)` behavior unchanged; only governance ownership moves.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- `execute_tool_action(...)` still contains per-tool execution branching.
- Workflow refs remain future-facing in binding plan but are not introduced here.

### Why not in this block
- This block is about governed registry declaration/selection metadata, not execution choreography.

### Risk if deferred
- W7 advances, but execution path simplification still remains for later control-plane work.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream7-context-recipe-governance-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if new tool actions or binding arg rules are added outside the snapshot owner.

## Next-block Contract (mandatory)
### Next block objective
Move context-recipe / policy-core allowed context compilation behind the same minimum-control-plane pattern so runtime context growth stops requiring local helper branching by default.

### First deterministic check command
`rg -n "_build_policy_core_allowed_context|capability_cards|consult_cards|policy_cards|memory_profile" truffles-api/app/services/intent_service.py truffles-api/app/services/policy_snapshot_service.py`

### Blocked-by conditions
- This block must first land with green focused snapshot tests and guards.

### Owner role for closure
- Brain / Top Architect
