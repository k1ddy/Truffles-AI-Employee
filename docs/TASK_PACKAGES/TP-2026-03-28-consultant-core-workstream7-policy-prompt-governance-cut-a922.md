# TP-2026-03-28-consultant-core-workstream7-policy-prompt-governance-cut-a922

## Title / Goal
Create the next governed control-plane owner for `Workstream 7` by moving policy-core prompt asset loading and fallback prompt ownership out of `intent_service.py` into one versioned prompt snapshot owner.

## Canon Refs
- `STATE.md` — active program truth (`Workstream 7 open`)
- `docs/system_forensics/final/IMPLEMENTATION_PROGRAM.md` — `Workstream 7 — Minimum Control Plane`
- `docs/system_forensics/files/app_services_intent_service.md`

## One Web Search (mandatory before implementation)
- Query: `site:martinfowler.com "Separating Configuration from Use" dependency injection`
- Date/time: `2026-03-28T20:52:00+05:00`
- Opened sources:
  - `https://martinfowler.com/articles/injection.html`
- High-signal source quality:
  - Martin Fowler primary-source article describing the principle that service configuration must be separated from service use.
- Found reusable idea:
  - keep configuration assets and assembly in a separate owner and make the runtime consumer read the prepared result instead of embedding configuration and fallback content inline.
- Reuse / integrate / build decision:
  - `integrate`
- Why:
  - the repo already stores the live prompt in `prompts/llm_policy_core.md`; the missing W7 piece is a governed prompt snapshot owner so the runtime gateway stops carrying fallback prompt content and asset-loading policy itself.
- Rejected options:
  - leave `POLICY_CORE_PROMPT_FALLBACK` in `intent_service.py` and only add comments: rejected because that preserves product vocabulary in the runtime hotspot.
  - rewrite `_build_policy_core_messages(...)` in the same block: rejected because this block is about prompt asset ownership, not message transport.

## Root Cause (mandatory)
### Symptom
`intent_service.py` still owns policy-core prompt asset loading and fallback prompt content, so prompt/instruction growth remains inside the runtime owner gateway.

### Minimal Reproduction
1. `rg -n "POLICY_CORE_PROMPT_FALLBACK|_load_policy_core_prompt|POLICY_CORE_PROMPT_PATH" truffles-api/app/services/intent_service.py`
2. Inspect `prompts/llm_policy_core.md` and compare it to the inline fallback constant.
3. Observe that runtime consumer code still embeds prompt asset policy and product instruction text.

### Evidence
- `truffles-api/app/services/intent_service.py`
- `prompts/llm_policy_core.md`
- `docs/system_forensics/files/app_services_intent_service.md`

### Five Whys
1. Why is `Workstream 7` still open after context and vocabulary snapshot cuts?
   - Because prompt asset ownership is still in `intent_service.py`.
2. Why is that a problem?
   - Because prompt/instruction growth still requires editing the runtime owner gateway.
3. Why is `_load_policy_core_prompt()` the right seam?
   - Because it is the single live entrypoint that loads the owner prompt and chooses fallback behavior.
4. Why move fallback too?
   - Because fallback prompt text is still product vocabulary and still grows in the runtime hotspot.
5. Why add a versioned snapshot owner?
   - Because W7 requires runtime to consume governed assets/snapshots instead of embedding assembly/configuration in the consumer.

### Root Cause Statement
The next W7 blocker is that policy-core prompt asset loading and fallback prompt content are still embedded in `intent_service.py`, so owner prompt growth remains a runtime-hotspot code change instead of a governed prompt asset change.

### Fix Mechanism
Add a versioned policy prompt snapshot service, move policy-core prompt path/fallback/cache ownership there, switch `intent_service.py` to consume the prepared prompt snapshot, and freeze the new boundary with focused tests and guards.

## Invariant
- No change to the loaded policy-core prompt text on the happy path.
- No change to `_build_policy_core_messages(...)` output shape.
- No change to owner call behavior beyond prompt ownership extraction.

## Scope
- New versioned policy prompt snapshot owner.
- Move prompt path/fallback/cache ownership out of `intent_service.py`.
- Keep `_load_policy_core_prompt()` only as a thin compatibility delegate or remove it if tests are updated safely.
- Focused deterministic tests and architecture guards.

## Out of Scope
- Message transport changes.
- Controller/plan prompt governance.
- Prompt text rewrites.

## Touch-list
- `truffles-api/app/services/policy_prompt_snapshot_service.py`
- `truffles-api/app/services/intent_service.py`
- `truffles-api/tests/test_intent.py`
- `truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `STATE.md`
- `STRUCTURE.md`

## Plan
1. Add versioned policy prompt snapshot models and loader helpers.
2. Move policy-core prompt path/fallback/cache ownership there.
3. Switch `intent_service.py` to consume the snapshot owner.
4. Update focused tests and architecture guards.
5. Run deterministic checks and update repo truth.

## DoD
- Versioned policy prompt snapshot object exists.
- `intent_service.py` no longer owns `POLICY_CORE_PROMPT_FALLBACK` or policy-core prompt cache/path selection.
- Focused deterministic tests are green.
- Repo truth updated.

## Work Mode
- `implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/policy_prompt_snapshot_service.py truffles-api/app/services/intent_service.py truffles-api/tests/test_intent.py truffles-api/tests/architecture/test_legacy_freeze_guard.py`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/test_intent.py -k "policy_core_prompt"`
- `PYTHONPATH=truffles-api pytest -q truffles-api/tests/architecture/test_legacy_freeze_guard.py -k "policy_prompt_snapshot_owner or policy_core_prompt_load_uses_snapshot_owner"`
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
- No message format changes.
- No controller/plan prompt scope creep.

## Risks / Blockers
- `test_intent.py` currently imports `_load_policy_core_prompt` from `intent_service.py`; keep a safe compatibility surface.
- Prompt file path resolution must remain repo-root aware.

## Residual Architecture Debt (mandatory)
### Current residuals accepted in this block
- Controller and plan prompt ownership remain inline in `intent_service.py`.
- Prompt text content itself remains a repo asset and is not versioned per tenant in this block.

### Why not in this block
- This block is only about policy-core prompt ownership extraction.

### Risk if deferred
- W7 advances, but prompt/instruction changes for policy-core would still leak into the runtime hotspot.

### Linked follow-up Task Package(s)
- `TP-2026-03-28-consultant-core-workstream7-controller-plan-prompt-governance-cut-a922.md` (planned)

### Expiry / trigger to stop deferral
- Stop deferral if policy-core prompt text or fallback is edited directly in `intent_service.py`.

## Next-block Contract (mandatory)
### Next block objective
Move remaining controller/plan prompt ownership behind governed assets so prompt growth stops living in `intent_service.py` by default.

### First deterministic check command
`rg -n "CONTROLLER_PROMPT_FALLBACK|PLAN_PROMPT_FALLBACK|_load_controller_prompt|_load_plan_prompt" truffles-api/app/services/intent_service.py`

### Blocked-by conditions
- This block must first land with green focused prompt tests and guards.

### Owner role for closure
- Brain / Top Architect
