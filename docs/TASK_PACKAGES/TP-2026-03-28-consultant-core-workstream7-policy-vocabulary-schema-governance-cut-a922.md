# TP-2026-03-28-consultant-core-workstream7-policy-vocabulary-schema-governance-cut-a922

## Title / Goal
Create the next governed control-plane owner for `Workstream 7` by moving policy-core semantic vocabulary and response-schema compilation out of `intent_service.py` into one versioned snapshot owner.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 7 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 7 — Minimum Control Plane`
- `docs/system_forensics/files/app_services_intent_service.md`

## One Web Search (mandatory before implementation)
- Query: `site:json-schema.org enum reusable schema definitions`
- Date/time: `2026-03-28T20:37:00+05:00`
- Opened sources:
  - `https://json-schema.org/`
- High-signal source quality:
  - Official JSON Schema project site documenting schema composition and centralized schema ownership rather than ad hoc per-consumer enum duplication.
- Found reusable idea:
  - keep shared vocabulary and schema fragments in one owner so consumers build schemas from the same governed source instead of repeating enum sets inline.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo already has one policy-core owner gateway; the missing W7 piece is a governed vocabulary/schema snapshot so semantic vocabulary growth stops happening inside `intent_service.py`.
- Rejected options:
  - leave `_build_policy_core_response_format(...)` in `intent_service.py` and only share a constants tuple: rejected because that preserves schema authority in the runtime hotspot.
  - move prompt fallback text in the same block: rejected because this block is about governed schema/vocabulary ownership, not prompt extraction.

## Root Cause (mandatory)
### Symptom
Changing policy-core semantic vocabulary still requires editing `intent_service.py` because the response-format enums and semantic-contract allowlists are duplicated inline inside `_build_policy_core_response_format(...)` and `_normalize_policy_core_memory_profile(...)`.

### Minimal Reproduction
1. `rg -n "_build_policy_core_response_format|subject_kind|capability|temporal_scope|resolution_mode|pending_question_act|pending_question_target|active_question_relation" truffles-api/app/services/intent_service.py`
2. Inspect `_build_policy_core_response_format(...)` and `_normalize_policy_core_memory_profile(...)`.
3. Observe that the same vocabulary sets are duplicated in both places.

### Evidence
- `truffles-api/app/services/intent_service.py`
- `docs/system_forensics/files/app_services_intent_service.md`

### Five Whys
1. Why is `Workstream 7` still open after policy/tool/context snapshot cuts?
   - Because policy-core semantic vocabulary growth still lives in `intent_service.py`.
2. Why is that a problem?
   - Because adding or changing contract vocabulary still requires editing the runtime owner gateway directly.
3. Why is the response-format builder the right seam?
   - Because it is the live schema authority consumed by the owner call.
4. Why also move semantic-contract allowlists?
   - Because they duplicate the same vocabulary and can drift from the response schema.
5. Why add a versioned snapshot owner?
   - Because W7 requires compiled registry/policy/context/schema surfaces to be governed outside consumer hotspots.

### Root Cause Statement
The next W7 blocker is that policy-core semantic vocabulary and response-schema fragments are still duplicated inline in `intent_service.py`, so schema/vocabulary growth remains a runtime-hotspot edit instead of a governed compiled snapshot change.

### Fix Mechanism
Add a versioned policy vocabulary/schema snapshot service, move the shared enum surface there, switch `intent_service.py` to build response format and semantic-contract allowlists from that owner, and freeze the boundary with focused tests and guards.

## Invariant
- No change to the current policy-core schema surface.
- No change to allowed semantic-contract values.
- No change to owner output validation behavior.

## Scope
- New versioned policy vocabulary/schema snapshot owner.
- Move policy-core response-format compilation out of `intent_service.py`.
- Move semantic-contract allowlists out of `intent_service.py`.
- Switch tests/guards to the new owner.

## Out of Scope
- Prompt fallback extraction.
- Controller legacy vocabulary extraction.
- Memory-profile structure changes beyond shared allowlists.

## Touch-list
- `truffles-api/app/services/policy_vocabulary_snapshot_service.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Add versioned policy vocabulary snapshot models and schema helpers.
2. Move shared policy-core enum vocabulary there.
3. Switch `intent_service.py` response-format building and semantic-contract normalization to the snapshot owner.
4. Update focused tests and architecture guards.
5. Run deterministic checks and update repo truth.

## DoD
- Versioned policy vocabulary snapshot object exists.
- `intent_service.py` no longer owns `_build_policy_core_response_format(...)`.
- Semantic-contract allowlists no longer live inline in `intent_service.py`.
- Focused deterministic tests are green.
- Repo truth updated.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/policy_vocabulary_snapshot_service.py truffles-api/app/services/intent_service.py truffles-api/tests/test_intent.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "policy_vocabulary_snapshot_owner or policy_core_response_format_uses_snapshot_owner"`
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
- No schema shape changes beyond ownership extraction.
- No silent semantic vocabulary additions.

## Risks / Blockers
- `test_intent.py` imports `_build_policy_core_response_format` directly today; move callers carefully.
- Keep response-format output byte-for-byte compatible for current tests.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Prompt fallback text still lives in `intent_service.py`.
- Controller legacy vocabulary remains inline.

### Why not in this block
- This block is only about policy-core schema/vocabulary ownership.

### Risk if deferred
- W7 advances, but owner prompt/schema growth could still leak through the remaining inline vocabulary surfaces.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream7-policy-prompt-governance-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if new policy-core semantic enum values are added directly in `intent_service.py`.

## Next-block Contract (mandatory)
### Next block objective
Move remaining policy-core prompt fallback and instruction payload growth behind governed assets so owner-gateway code stops carrying product vocabulary by default.

### First deterministic check command
`rg -n "POLICY_CORE_PROMPT_FALLBACK|Не используй|subject_kind values|capability values" truffles-api/app/services/intent_service.py`

### Blocked-by conditions
- This block must first land with green focused schema/vocabulary tests and guards.

### Owner role for closure
- Brain / Top Architect
