# TP-2026-03-18-consultant-core-timeout-owner-boundary-application-family-convergence-a922

## Goal
Delete the duplicated timeout owner-boundary resolve/derive/apply seam from frozen `truffles-api/app/routers/webhook/decision.py` by converging that boundary-application family into the existing non-frozen `truffles-api/app/services/timeout_owner_boundary_service.py` owner surface.

## Canon refs
- `STATE.md` NOW: handover frozen internal self-use classification
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-timeout-boundary-frozen-waiver-implementation-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-timeout-boundary-residual-audit-a922.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after targeted timeout-boundary runtime checks plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- Query: `site:refactoring.com/catalog "Move Function" "Extract Function"`
- Date/time: `2026-03-18 14:07:00 +05`
- Opened sources:
  - `https://refactoring.com/catalog/moveFunction.html`
- Source quality:
  - high-signal / primary-style source: Martin Fowler refactoring catalog
- Found ready-made solutions:
  - `Move Function`: move behavior to the module that owns the invariant and the main data dependencies
- Decision: `reuse + integrate`
  - reuse the existing `truffles-api/app/services/timeout_owner_boundary_service.py`
  - move the live timeout-boundary coordinator logic there instead of inventing another owner module
  - keep frozen `decision.py` as a bounded caller that supplies runtime context/hooks only
- Rejected variants:
  - add another local helper in `decision.py`: rejected because old boundary authority would remain frozen and live
  - create a brand-new boundary owner module parallel to `timeout_owner_boundary_service.py`: rejected because the owner surface already exists and this would fragment the family again
  - leave pending-question derivation in `decision.py`: rejected because the duplicated boundary-application family would remain split across frozen and non-frozen files

## Root cause (mandatory)
- Symptom:
  - frozen `decision.py` still owns the live timeout boundary resolve/derive/apply flow in two branches
  - the same file still owns `_derive_timeout_owner_boundary_pending_question_contract(...)`
- Minimal reproduction:
  - `rg -n "resolve_timeout_owner_boundary\(|apply_timeout_owner_boundary_resolution\(|TimeoutOwnerBoundaryRuntimeHooks\(|_derive_timeout_owner_boundary_pending_question_contract\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/timeout_owner_boundary_service.py`
- Evidence:
  - `decision.py:14802`, `decision.py:14818`, and `decision.py:14842` still do pending resume timeout boundary resolution and application inline
  - `decision.py:15140`, `decision.py:15159`, `decision.py:15166`, and `decision.py:15179` still do the generic timeout boundary resolution, pending-question derivation, and application inline
  - `decision.py:1014` still defines `_derive_timeout_owner_boundary_pending_question_contract(...)`
  - `timeout_owner_boundary_service.py` currently owns only apply-time mechanics, not the coordinator path that decides whether and how a timeout boundary is materialized
- Five Whys:
  1. Why is `decision.py` still a boundary hotspot? Because timeout boundary runtime resolution and application still happen inline there.
  2. Why does that matter now? Because `boundary_owner.current_primary_files` still includes frozen `decision.py` and this family repeats a mixed coordinator pattern in two branches.
  3. Why was the seam not removed earlier? Because earlier blocks only deleted the state/meta/send subclusters and left the broader coordinator path behind.
  4. Why is that insufficient? Because future boundary behavior can still accrete in the frozen router instead of the existing owner service.
  5. Why is the owner service not already authoritative? Because it was introduced as an apply helper, not yet as the family coordinator.
- Root cause statement:
  - The timeout owner-boundary family is still split because `timeout_owner_boundary_service.py` owns only the apply subroutine while frozen `decision.py` still decides resolution, pending-question derivation, and branch-specific execution inline.
- Fix mechanism:
  - move the live timeout boundary coordinator path into `timeout_owner_boundary_service.py`
  - delete `_derive_timeout_owner_boundary_pending_question_contract(...)` from `decision.py`
  - reduce both frozen timeout-boundary branches to owner-surface invocation plus commit/response handling

## Invariant
- `decision.py` must lose live boundary authority, not gain another local wrapper forest.
- No semantic invention/reset may happen after planner.
- `state_service.py` must not become a fallback landing zone for boundary logic.
- The existing timeout-boundary runtime behavior, trace/meta contract, and prompts must remain unchanged.

## Scope
- Converge the timeout owner-boundary application family into `timeout_owner_boundary_service.py`
- Delete the local pending-question derivation helper from frozen `decision.py`
- Shrink both frozen timeout-boundary branches to owner-surface calls
- Update only directly impacted tests/docs

## Out of scope
- Broader boundary family closure outside the timeout owner-boundary application path
- Handover family changes
- `booking.py` changes
- Proof bundle / multi-pack correctness claims
- `boundary_validator.py` redesign

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-owner-boundary-application-family-convergence-a922.md`
- `STRUCTURE.md`
- `STATE.md`
- `truffles-api/app/services/timeout_owner_boundary_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- any directly impacted targeted tests only if required

## Reuse-first plan (mandatory)
1. Reuse the existing `TimeoutOwnerBoundaryInput`, `resolve_timeout_owner_boundary(...)`, and `apply_timeout_owner_boundary_resolution(...)` contracts.
2. Extend `timeout_owner_boundary_service.py` with the missing coordinator logic and pending-question derivation so the family stays in one owner surface.
3. Reuse one local `TimeoutOwnerBoundaryRuntimeHooks(...)` binding inside `decision.py` instead of re-assembling hooks in two branches.
4. Keep branch-specific override payloads in the caller only where they are truly branch-specific.
5. Verify the old inline frozen coordinator seam is deleted/unreachable, not merely wrapped.

## Plan
1. Author and register this TP.
2. Extend `timeout_owner_boundary_service.py` with a high-level timeout-boundary execution entrypoint that resolves, derives any pending-question contract, and applies the boundary.
3. Delete `_derive_timeout_owner_boundary_pending_question_contract(...)` from frozen `decision.py` and replace both inline coordinator branches with owner-surface calls.
4. Update/add targeted tests only where the changed family needs direct coverage.
5. Run targeted timeout-boundary checks and required guards.
6. Record evidence in `STATE.md` only if an old live boundary seam is actually deleted or unreachable.

## DoD
- `decision.py` no longer contains `_derive_timeout_owner_boundary_pending_question_contract(...)`
- the duplicated inline timeout boundary resolve/derive/apply flow is deleted from both frozen branches and replaced by owner-surface invocation
- `timeout_owner_boundary_service.py` becomes the live owner surface for timeout-boundary coordination
- targeted timeout-boundary runtime tests and required guards are green
- `STATE.md` records the deleted/unreachable old seam with evidence

## Checks
- `python3 -m py_compile truffles-api/app/services/timeout_owner_boundary_service.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'timeout_owner_boundary or timeout_booking_interrupt_resume_boundary or pending_soft_pass_timeout_booking_resume_boundary'`
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
  - frozen `decision.py` no longer owns the timeout boundary coordinator body
  - timeout-boundary targeted tests pass
  - required architecture/session guards pass
- Rollback:
  - revert this block's changes to `timeout_owner_boundary_service.py`, `decision.py`, affected tests, and docs
  - rerun the targeted timeout-boundary tests plus guard set
- Rollback verification:
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k 'timeout_owner_boundary or timeout_booking_interrupt_resume_boundary or pending_soft_pass_timeout_booking_resume_boundary'`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`

## Evidence
- updated TP + `STRUCTURE.md`
- diff showing the deleted frozen inline coordinator seam and the new owner-surface entrypoint
- green targeted timeout-boundary runtime tests + required guards
- `STATE.md` entry with the deleted/unreachable seam

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted timeout-boundary/runtime checks.

## No-go
- Do not broaden `decision.py` with more timeout-boundary local helpers.
- Do not move unrelated planner, booking, or handover logic into `timeout_owner_boundary_service.py`.
- Do not introduce a new middle-layer service parallel to `timeout_owner_boundary_service.py`.
- Do not claim consultant correctness/proof closure beyond this owner-family block.

## Risks / blockers
- Frozen `decision.py` still provides nested runtime hooks; if the coordinator cannot be moved without leaking more router internals into the service, the block must stop with `GAP`.
- Pending-question derivation must preserve the existing `pending_question_*` trace/meta contract exactly.
- If the new owner-surface entrypoint only wraps the old inline branches without deleting them, the block does not count as progress.

## Token / run budget (mandatory for expensive suites)
- Cheap deterministic gate first: `python3 -m py_compile`
- Targeted runtime suite next: timeout-boundary selections from `test_message_endpoint.py` plus `test_consultant_core_runtime_contracts.py`
- Full required guard set only after targeted runtime checks pass
- Stop condition: if two consecutive iterations fail without new structural evidence, stop and return to RCA instead of grinding tests

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- broader `boundary_owner` family outside the timeout owner-boundary application path still remains partially frozen
- `docs/SOURCE_OF_TRUTH.yaml` may still need a broader boundary-owner update after this block if other frozen boundary seams remain

### Why not in this block
- this block targets one concrete deletable family: timeout boundary coordination and application
- broader boundary closure needs a separate family ledger instead of re-expanding scope here

### Risk if deferred
- remaining frozen boundary seams can still attract new behavior if the owner family is not tracked block-by-block

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-boundary-owner-next-family-selection-a922` (to be authored only if this block lands)

### Expiry/trigger to stop deferral
- stop deferral if any new boundary logic lands in frozen `decision.py` outside thin owner-surface invocation

## Next-block contract (mandatory)
### Next block objective
- classify and select the next real `boundary_owner` residual family after timeout owner-boundary coordination leaves frozen `decision.py`

### First deterministic check command
- `rg -n "timeout_owner_boundary|boundary_override|boundary_state_source|apply_policy_guard_override" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/timeout_owner_boundary_service.py truffles-api/app/core/boundary_validator.py`

### Blocked-by conditions
- this block does not delete/unreach the duplicated frozen timeout-boundary coordinator seam
- targeted timeout-boundary tests or required guards fail
- the service entrypoint becomes just another wrapper while frozen logic remains live

### Owner role for closure
- Brain / Top Architect
