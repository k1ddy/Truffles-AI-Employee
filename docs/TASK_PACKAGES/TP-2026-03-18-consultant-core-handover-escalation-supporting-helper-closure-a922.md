# TP-2026-03-18-consultant-core-handover-escalation-supporting-helper-closure-a922

## Goal
Delete the remaining live handover-support helper seam from `truffles-api/app/services/escalation_service.py` so the handover owner family no longer depends on owner-specific helper authority outside `truffles-api/app/services/handover_owner_service.py`.

## Canon refs
- `STATE.md` NOW: handover owner convergence, state-service helper collapse, frozen compat seam reduction
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-owner-convergence-implementation-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-state-service-handover-helper-collapse-implementation-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-frozen-compat-seam-reduction-a922.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after targeted runtime checks plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- Query: `site:refactoring.com/catalog "Separate Query from Modifier" "Move Function"`
- Date/time: `2026-03-18 09:17:43 +05`
- Opened sources:
  - `https://refactoring.com/catalog/`
  - `https://refactoring.com/catalog/separateQueryFromModifier.html`
  - `https://refactoring.com/catalog/moveFunction.html`
- Source quality:
  - high-signal / primary-style source: Martin Fowler refactoring catalog pages
- Found ready-made solutions:
  - `Move Function`: move behavior to the module that has the data and invariants it actually serves
  - `Separate Query from Modifier`: split state mutation / side effects from read helpers so callers do not depend on mixed command+query surfaces
- Decision: `integrate + build`
  - reuse the existing handover helper implementations and tests
  - move owner-specific live bodies into `handover_owner_service.py`
  - keep `escalation_service.py` only as compatibility/support surface where external imports still require old names
- Rejected variants:
  - leave owner helpers in `escalation_service.py` and add more wrappers: rejected because old split authority remains live
  - broad rewrite of all telegram routing and webhook handover code: rejected because this block targets one residual family only

## Root cause (mandatory)
- Symptom:
  - `truffles-api/app/services/handover_owner_service.py` still imports owner-specific helper bodies from `truffles-api/app/services/escalation_service.py`
  - `escalation_service.py` still contains live handover meta/query/topic/notification helper authority
- Minimal reproduction:
  - `rg -n "_build_handover_meta|_get_latest_user_message|_get_recent_user_messages|_build_simulated_topic_id|get_active_handover|get_or_create_topic|send_telegram_notification" truffles-api/app/services/handover_owner_service.py truffles-api/app/services/escalation_service.py`
- Evidence:
  - `handover_owner_service.py` imports `_build_handover_meta`, `_get_latest_user_message`, `_get_recent_user_messages`, `_build_simulated_topic_id`, `get_active_handover`, `get_or_create_topic`, and `send_telegram_notification` from `escalation_service.py`
  - `escalation_service.py` still defines those live bodies
- Five Whys:
  1. Why is the owner family not fully converged? Because owner runtime still depends on helpers hosted in `escalation_service.py`.
  2. Why do those helpers remain there? Because earlier blocks optimized for bounded deletions before family closure.
  3. Why is that a problem now? Because `escalation_service.py` still acts as a live authority host for handover materialization and notification details.
  4. Why can this reintroduce the old architecture? Because future handover changes can land in the mixed support file instead of the owner surface.
  5. Why has that not been eliminated already? Because external compatibility imports and tests still referenced the old module path.
- Root cause statement:
  - The residual split exists because owner-specific handover behavior was moved only partially; the canonical owner path still reuses live helper bodies from a mixed legacy support module.
- Fix mechanism:
  - move owner-specific helper implementations into `handover_owner_service.py`
  - convert `escalation_service.py` to thin compatibility wrappers for any still-needed external imports
  - preserve `resolve_telegram_routing` and `get_telegram_credentials` as support-only functions outside the owner surface

## Invariant
- No new handover authority may land in `state_service.py`.
- No semantic invention/reset may happen after planner.
- Frozen `decision.py`, `booking.py`, and `pending.py` must not become broader authority surfaces.
- `handover_owner_service.py` must not absorb unrelated console/webhook business logic.

## Scope
- Collapse the residual owner-specific helper cluster out of `escalation_service.py`
- Keep compatibility for existing external imports where necessary
- Update tests and docs for the new owner/support boundary

## Out of scope
- Broad telegram routing redesign
- Proof bundle / multi-pack consultant correctness claims
- `booking.py` changes
- Full deletion of frozen `decision.py` internal self-use wrappers

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-escalation-supporting-helper-closure-a922.md`
- `STRUCTURE.md`
- `STATE.md`
- `truffles-api/app/services/handover_owner_service.py`
- `truffles-api/app/services/escalation_service.py`
- `truffles-api/tests/test_escalation_media_contract.py`
- `truffles-api/tests/test_escalation_handover_context.py`
- any directly impacted targeted tests only if required by import/patch-path changes

## Reuse-first plan (mandatory)
1. Reuse existing helper bodies and move owner-specific live implementations into `handover_owner_service.py`.
2. Keep `resolve_telegram_routing` and `get_telegram_credentials` in `escalation_service.py` as support-only functions.
3. Replace moved functions in `escalation_service.py` with thin compatibility wrappers only where external imports still require the old path.
4. Update tests to patch/assert against the new live owner surface when the old module becomes compatibility-only.
5. Verify that `handover_owner_service.py` no longer imports owner-specific helper bodies from `escalation_service.py`.

## Plan
1. Author and register this TP.
2. Move the residual owner-specific helper bodies from `escalation_service.py` into `handover_owner_service.py`.
3. Leave only compatibility wrappers in `escalation_service.py` for any still-needed external imports.
4. Update tests/import patch points to follow the live owner surface.
5. Run targeted runtime checks and required guards.
6. Record evidence in `STATE.md` only if an old live seam is actually deleted or unreachable.

## DoD
- `handover_owner_service.py` no longer imports owner-specific helper bodies from `escalation_service.py`
- the old live owner-specific helper seam in `escalation_service.py` is deleted or reachable only through thin compatibility wrappers
- no new mixed helper landing zone appears
- targeted tests and required guards are green
- `STATE.md` records the deleted/unreachable old seam with evidence

## Checks
- `python3 -m py_compile truffles-api/app/services/handover_owner_service.py truffles-api/app/services/escalation_service.py truffles-api/tests/test_escalation_media_contract.py truffles-api/tests/test_escalation_handover_context.py`
- `pytest -q truffles-api/tests/test_escalation_media_contract.py truffles-api/tests/test_escalation_handover_context.py`
- `pytest -q truffles-api/tests/test_state_service.py -k 'handover or pending_resume or escalation or manager_'`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'explicit_handoff_owner'`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'legacy_handover_adapter or test_escalation_reuses_active_handover or provider_unavailable_human_request_pending_resume_timeout_resume_boundary_after_manager_resolve'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Release safety (mandatory for non-doc changes)
- Rollout strategy: local-only code and guard validation in this worktree before any merge; no prod rollout claim in this block
- Go/no-go signals:
  - no direct owner-helper imports from `handover_owner_service.py` to moved `escalation_service.py` bodies
  - targeted handover notification/runtime tests pass
  - required architecture/session guards pass
- Rollback:
  - revert this block's changes to `handover_owner_service.py`, `escalation_service.py`, and affected tests/docs
  - re-run the targeted handover tests plus guard set
- Rollback verification:
  - `pytest -q truffles-api/tests/test_escalation_media_contract.py truffles-api/tests/test_escalation_handover_context.py`
  - `pytest -q truffles-api/tests/test_state_service.py -k 'handover or pending_resume or escalation or manager_'`

## Evidence
- updated TP + `STRUCTURE.md`
- diff showing owner-specific helper bodies moved out of `escalation_service.py`
- `rg` evidence proving `handover_owner_service.py` no longer imports the moved helpers from `escalation_service.py`
- green targeted tests + required guards
- `STATE.md` entry with the deleted/unreachable seam

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted handover/runtime checks.

## No-go
- Do not broaden frozen `decision.py` wrappers.
- Do not move non-handover console or webhook logic into `handover_owner_service.py`.
- Do not add a new helper facade that leaves old live bodies in `escalation_service.py`.
- Do not claim correctness/proof closure beyond this owner-family block.

## Risks / blockers
- Compatibility wrappers may create import cycles if `handover_owner_service.py` keeps top-level imports from `escalation_service.py`.
- Existing tests patching `app.services.escalation_service.*` may need to be redirected to the live owner module.
- If the helper split cannot be collapsed without new mixed authority or cycle-heavy indirection, stop and publish `GAP`.

## Token / run budget (mandatory for expensive suites)
- Cheap deterministic gate first: `python3 -m py_compile` + targeted `pytest` for escalation/handover files
- Medium suites next: `test_state_service.py`, `test_reasoning_core.py`, targeted `test_message_endpoint.py`, `test_consultant_core_runtime_contracts.py`
- Full required guard set only after targeted runtime checks pass
- Stop condition: if two consecutive iterations fail without new structural evidence, stop and return to RCA instead of grinding tests

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- frozen `decision.py` still keeps internal self-use handover wrappers
- support-only routing helpers remain in `escalation_service.py`

### Why not in this block
- frozen internal seam reduction is a separate waiver-governed block
- routing support is still shared by non-owner consumers and does not need to move if it stays support-only

### Risk if deferred
- if frozen self-use wrappers or support-only helpers start absorbing owner logic again, family closure will regress

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-handover-frozen-internal-self-use-classification-a922` (to be authored only if this block lands)

### Expiry/trigger to stop deferral
- stop deferral if new handover authority lands in `escalation_service.py` or if frozen wrappers gain new behavior beyond compatibility/self-use

## Next-block contract (mandatory)
### Next block objective
- classify and, if admissible, further narrow the remaining frozen internal self-use seam in `truffles-api/app/routers/webhook/decision.py` once non-frozen handover helper authority is fully converged

### First deterministic check command
- `rg -n "def get_active_handover|def _reuse_active_handover|def _create_pending_escalation_with_notification|resolve_active_handover_rejection|send_telegram_notification" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/handover_owner_service.py truffles-api/app/services/escalation_service.py`

### Blocked-by conditions
- this block does not delete/unreach the live helper seam in `escalation_service.py`
- compatibility wrappers require another mixed helper host
- targeted handover tests or required guards fail

### Owner role for closure
- Brain / Top Architect
