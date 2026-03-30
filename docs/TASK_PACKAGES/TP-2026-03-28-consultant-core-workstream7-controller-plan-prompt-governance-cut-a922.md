# TP-2026-03-28-consultant-core-workstream7-controller-plan-prompt-governance-cut-a922

## Title / Goal
Create the next governed control-plane owner for `Workstream 7` by moving controller/plan prompt asset loading and fallback ownership out of `intent_service.py` into one versioned prompt snapshot owner.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 7 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 7 — Minimum Control Plane`
- `docs/system_forensics/files/app_services_intent_service.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com "Separating Configuration from Use" dependency injection`
- Date/time: `2026-03-28T21:00:00+05:00`
- Opened sources:
  - `https://martinfowler.com/articles/injection.html`
- High-signal source quality:
  - Martin Fowler primary-source article describing the principle that service configuration must be separated from service use.
- Found reusable idea:
  - keep asset configuration/loading in a separate owner and let consumers read prepared snapshots instead of embedding path/fallback/cache policy inline.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo still keeps controller/plan prompt assets inline in `intent_service.py`; the missing W7 piece is one governed owner for those remaining prompt assets.
- Rejected options:
  - remove the loaders entirely: rejected because a safe compatibility delegate is lower-risk than deleting exported functions in the same block.
  - fold controller/plan into `policy_prompt_snapshot_service.py`: rejected for this block because controller/plan remain a separate retired compatibility lane and should stay isolated.

## Root Cause (mandatory)
### Symptom
`intent_service.py` still owns controller/plan prompt path/fallback/cache policy, so prompt asset growth for the retired compatibility lane still lives in the runtime hotspot.

### Minimal Reproduction
1. `rg -n "CONTROLLER_PROMPT_FALLBACK|PLAN_PROMPT_FALLBACK|CONTROLLER_PROMPT_PATH|PLAN_PROMPT_PATH|_CONTROLLER_PROMPT_CACHE|_PLAN_PROMPT_CACHE|_load_controller_prompt|_load_plan_prompt" truffles-api/app/services/intent_service.py`
2. Observe that these assets and caches still live inline in `intent_service.py`.
3. Observe that no governed snapshot owner exists for those remaining prompt assets.

### Evidence
- `truffles-api/app/services/intent_service.py`
- `prompts/intent_classifier.md`
- `prompts/llm_plan.md`
- `docs/system_forensics/files/app_services_intent_service.md`

### Five Whys
1. Why is `Workstream 7` still open after policy prompt governance?
   - Because controller/plan prompt assets still live in `intent_service.py`.
2. Why is that a problem?
   - Because even retired compatibility prompt growth still requires edits in the runtime hotspot.
3. Why move both together?
   - Because they are the only remaining prompt asset loaders still owned by `intent_service.py`.
4. Why keep delegates instead of deleting the functions?
   - Because exported compatibility surfaces can stay stable while ownership moves out.
5. Why add a snapshot owner?
   - Because W7 requires runtime and compatibility consumers to read governed assets instead of embedding configuration/use inline.

### Root Cause Statement
The next W7 blocker is that controller/plan prompt path, fallback, and cache policy still live inline in `intent_service.py`, so remaining prompt asset growth still depends on editing the runtime hotspot instead of one governed prompt owner.

### Fix Mechanism
Add a versioned controller/plan prompt snapshot service, move path/fallback/cache ownership there, switch `_load_controller_prompt()` and `_load_plan_prompt()` to thin delegates, and freeze the new boundary with focused guards and deterministic checks.

## Invariant
- No change to current controller/plan prompt text on the happy path.
- No change to compatibility delegate return values.
- No change to policy-core prompt ownership from the previous block.

## Scope
- New versioned controller/plan prompt snapshot owner.
- Move controller/plan prompt path/fallback/cache ownership out of `intent_service.py`.
- Keep `_load_controller_prompt()` and `_load_plan_prompt()` as thin delegates.
- Focused deterministic checks and guards.

## Out of Scope
- Policy-core prompt ownership.
- Prompt text rewrites.
- Legacy controller/plan behavioral revival.

## Touch-list
- `truffles-api/app/services/controller_plan_prompt_snapshot_service.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Add versioned controller/plan prompt snapshot models and loader helpers.
2. Move path/fallback/cache ownership there.
3. Switch `intent_service.py` delegates to the snapshot owner.
4. Add focused architecture guards.
5. Run deterministic checks and update repo truth.

## DoD
- Versioned controller/plan prompt snapshot objects exist.
- `intent_service.py` no longer owns controller/plan prompt fallback/path/cache state.
- Focused deterministic checks are green.
- Repo truth updated.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/controller_plan_prompt_snapshot_service.py truffles-api/app/services/intent_service.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "controller_plan_prompt_snapshot_owner or controller_plan_prompt_loaders_use_snapshot_owner"`
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
- No prompt text rewrite.
- No revival of retired controller/plan paths.
- No policy-core prompt scope creep.

## Risks / Blockers
- No direct tests currently import these loaders; rely on architecture guards and py_compile.
- Keep prompt-dir resolution repo-root aware.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Controller and plan behavioral code still exist as retired compatibility surfaces.
- Prompt assets are still repo files, not per-tenant governed data.

### Why not in this block
- This block is only about finishing prompt asset ownership extraction.

### Risk if deferred
- Remaining prompt asset edits would still leak into `intent_service.py`.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream7-closeout-proof-pass-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if controller/plan prompt fallback/path/cache is edited directly in `intent_service.py`.

## Next-block Contract (mandatory)
### Next block objective
Run factual W7 closeout proof and determine whether any remaining governed-growth seam still blocks honest completion.

### First deterministic check command
`rg -n "PROMPT_FALLBACK|PROMPT_PATH|_PROMPT_CACHE|snapshot_service" truffles-api/app/services/intent_service.py truffles-api/app/services`

### Blocked-by conditions
- This block must first land with green focused guards.

### Owner role for closure
- Brain / Top Architect
