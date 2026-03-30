# TP-2026-03-28-consultant-core-workstream7-context-recipe-governance-cut-a922

## Title / Goal
Create the third governed control-plane owner for `Workstream 7` by moving policy-core allowed-context compilation and context-card recipes out of `intent_service.py` into one versioned context snapshot owner.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 7 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 7 — Minimum Control Plane`
- `docs/system_forensics/files/app_services_intent_service.md`
- `docs/system_forensics/files/app_routers_webhook_policy.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com inversion of decision feature toggle configuration context object`
- Date/time: `2026-03-28T20:14:00+05:00`
- Opened sources:
  - `https://martinfowler.com/articles/feature-toggles.html?r=prd-ffs`
- High-signal source quality:
  - Martin Fowler / Thoughtworks primary-source article covering `De-coupling decision points from decision logic`, `Inversion of Decision`, and structured configuration owned outside consumer code.
- Found reusable idea:
  - compile context/config decisions once in a dedicated owner and inject resolved decisions into runtime consumers instead of letting each consumer grow local defaults and helper branches.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo already has runtime capability, policy-pack, and tool-registry sources; the missing W7 piece is one compiled context-recipe snapshot owner for policy-core allowed refs/cards/tool surface.
- Rejected options:
  - leave `_build_policy_core_allowed_context(...)` in `intent_service.py` and only document it: rejected because that preserves growth authority in the owner gateway.
  - rewrite prompt/message building together with context governance: rejected because this block is about control-plane extraction, not owner transport refactor.

## Root Cause (mandatory)
### Symptom
Adding or changing policy-core context inputs still requires editing `intent_service.py` because default info refs, generic tool actions, consult-card loading, and capability/policy card recipes are compiled locally inside `_build_policy_core_allowed_context(...)`.

### Minimal Reproduction
1. `rg -n "_build_policy_core_allowed_context|_build_policy_core_policy_cards|_build_policy_core_capability_cards|_load_policy_core_consult_catalog|_POLICY_CORE_DEFAULT_INFO_REFS|_POLICY_CORE_GENERIC_TOOL_ACTIONS" truffles-api/app/services/intent_service.py`
2. Inspect `route_llm_policy_core(...)` and observe it calling the local builder directly.
3. Observe that the compiled `allowed` and `context` owner envelope still depends on local helper branching in `intent_service.py`.

### Evidence
- `truffles-api/app/services/intent_service.py`
- `docs/system_forensics/files/app_services_intent_service.md`

### Five Whys
1. Why is `Workstream 7` still open after policy and tool snapshot cuts?
   - Because the owner input context recipe still grows inside `intent_service.py`.
2. Why is that a problem?
   - Because new default refs, cards, or allowed tool surface changes still require editing a core owner gateway hotspot.
3. Why is `_build_policy_core_allowed_context(...)` the right seam?
   - Because it is the single compilation point for owner-visible refs, tool surface, and context cards.
4. Why not leave it in `intent_service.py`?
   - Because that would keep growth authority in the runtime consumer instead of a governed compiled snapshot.
5. Why add a versioned snapshot owner?
   - Because W7 requires runtime to consume compiled registry/policy/context snapshots rather than rebuild context ad hoc.

### Root Cause Statement
The third W7 blocker is that policy-core allowed-context and context-card recipes are still assembled locally inside `intent_service.py`, so context growth remains a runtime hotspot change instead of a governed compiled snapshot change.

### Fix Mechanism
Add a versioned policy-context snapshot service, move default refs/generic actions/card recipe/catalog assembly into that owner, switch `intent_service.py` to consume the compiled snapshot, and freeze the new boundary with focused tests and guards.

## Invariant
- No change to currently allowed policy-core tool actions, info refs, or consult refs.
- No change to capability/policy/consult card payloads currently sent to the owner.
- No change to prompt/message transport behavior outside context ownership.

## Scope
- New versioned policy-context snapshot owner.
- Move policy-core allowed-context compilation out of `intent_service.py`.
- Move default info refs and generic tool actions out of `intent_service.py`.
- Switch `route_llm_policy_core(...)` to read the compiled snapshot.
- Focused deterministic tests and architecture guards.

## Out of Scope
- Response-format enum extraction.
- Prompt fallback text extraction.
- Memory-profile normalization changes.
- Booking/runtime execution changes.

## Touch-list
- `truffles-api/app/services/policy_context_snapshot_service.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/app/core/policy_tool_projector.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Add versioned policy-context snapshot models and compile helpers.
2. Move default refs, generic tool actions, card recipes, and consult catalog loading to that owner.
3. Switch `intent_service.py` to consume the compiled snapshot for `allowed` and `context` payloads.
4. Add focused tests and architecture guards.
5. Run deterministic checks and update repo truth.

## DoD
- Versioned policy-context snapshot object exists.
- `intent_service.py` no longer owns local policy-core allowed-context compilation helpers.
- Default info refs and generic tool actions no longer live in `intent_service.py`.
- Focused deterministic tests are green.
- Repo truth updated.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/policy_context_snapshot_service.py truffles-api/app/services/intent_service.py truffles-api/app/core/policy_tool_projector.py truffles-api/tests/test_intent.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "policy_core_assembles_manifest_scoped_dynamic_context or policy_core_honors_explicit_booking_only_context_envelope"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k "tool_registry_snapshot or binding_plan or tool_action"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "policy_core_context_snapshot_owner or policy_core_allowed_context_uses_compiled_context_snapshot"`
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
- No broad prompt rewrite.
- No new runtime branching for policy-core context recipes.
- No silent change to allowed context surface.

## Risks / Blockers
- Existing tests assert exact order/content of `allowed` and `context` payloads; preserve that order.
- Avoid importing `intent_service.py` back into the snapshot owner; keep the dependency one-way.
- Full `test_intent.py` can surface active-path projector regressions even when the governance change is confined to owner context assembly; keep projector behavior contract-stable.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Response-format enums and fallback prompt text still live in `intent_service.py`.
- Memory-profile normalization still lives in `intent_service.py`.

### Why not in this block
- This block is about context-recipe governance, not owner schema/prompt extraction.

### Risk if deferred
- W7 advances, but some policy-core vocabulary still remains in the owner gateway.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream7-capability-schema-governance-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if new policy-core refs/cards/actions are added directly in `intent_service.py`.

## Next-block Contract (mandatory)
### Next block objective
Move remaining policy-core vocabulary ownership (response-format enums / capability schema surface) behind governed registry data so the owner gateway stops hardcoding semantic vocabulary growth by default.

### First deterministic check command
`rg -n "_build_policy_core_response_format|CONTROLLER_ALLOWED_|_POLICY_CORE_" truffles-api/app/services/intent_service.py`

### Blocked-by conditions
- This block must first land with green focused snapshot tests and guards.

### Owner role for closure
- Brain / Top Architect
