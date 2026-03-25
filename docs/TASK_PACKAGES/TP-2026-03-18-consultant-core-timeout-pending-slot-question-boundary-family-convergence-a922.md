# TP-2026-03-18-consultant-core-timeout-pending-slot-question-boundary-family-convergence-a922

## Goal
Delete the frozen timeout pending-slot-question boundary family from `truffles-api/app/routers/webhook/decision.py` by converging that live timeout-degrade response body into the existing non-frozen timeout-degrade boundary owner surface.

## Canon refs
- `STATE.md` NOW: consultant core invalid-schema service-grounded booking boundary family convergence
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-degrade-retry-boundary-family-convergence-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-invalid-schema-service-grounded-booking-boundary-family-convergence-a922.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after targeted timeout pending-slot-question runtime checks plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- Query: `site:refactoring.com/catalog "Move Function" "Parameterize Function" "Form Template Method"`
- Date/time: `2026-03-18 earlier in-session; exact timestamp not retained in the session summary (GAP)`
- Opened sources:
  - `https://refactoring.com/catalog/moveFunction.html`
- Source quality:
  - high-signal / primary-style source: Martin Fowler refactoring catalog
- Found ready-made solutions:
  - `Move Function`: move the remaining timeout pending-slot-question response authority out of frozen `decision.py`
- Decision: `reuse + integrate`
  - reuse `truffles-api/app/services/policy_timeout_degrade_boundary_service.py` as the existing timeout-degrade boundary owner
  - integrate the pending-slot-question reply variant there as a bounded mode layered on top of the already-converged retry-count / retry-limit path
- Rejected variants:
  - create another timeout pending-slot-question owner service: rejected because it would split one timeout-degrade family across two owners
  - move this family into `policy_validation_boundary_service.py`: rejected because this is `timeout_degrade`, not `contract_validation_failure`
  - move this family into `timeout_owner_boundary_service.py`: rejected because this is not owner-resolution / matched-expected-reply logic
  - keep the response body inline in frozen `decision.py`: rejected because live boundary authority would remain frozen
  - add another local helper in `decision.py`: rejected because it would rename the seam without deleting it

## Root cause (mandatory)
- Symptom:
  - frozen `decision.py` still owns the timeout pending-slot-question response body after the timeout-degrade retry family was already moved into `policy_timeout_degrade_boundary_service.py`
- Minimal reproduction:
  - `rg -n "timeout_pending_slot_question|booking_slot_guidance|handle_policy_timeout_degrade_boundary\(|PolicyTimeoutDegradeBoundaryRuntimeInput\(|PolicyTimeoutDegradeBoundaryRuntimeHooks\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- Evidence:
  - `decision.py:15666-15746` still performs expected-reply continuity, guard override, trace/meta writes, send, commit, and return inline for the timeout pending-slot-question reply path
  - the preceding retry-limit / retry-count logic at `decision.py:15543-15577` already exits through `policy_timeout_degrade_boundary_service.py`
  - this leaves the same timeout-degrade family split between the existing owner surface and the frozen router
- Five Whys:
  1. Why is `decision.py` still a boundary hotspot here? Because the timeout pending-slot-question reply continuation still lives inline there.
  2. Why is this the same family as the moved timeout-degrade retry block? Because it is the success-path continuation after the same row-scoped timeout retry contract.
  3. Why is that a problem? Because timeout-degrade ownership remains split between the non-frozen retry owner and a frozen reply body.
  4. Why did the previous timeout-degrade block not remove it? Because it converged retry-limit / retry-count authority first and left the reply continuation inline.
  5. Why can it move now? Because the remaining delta is bounded to expected-reply continuity plus reply trace/meta/send behavior after retry registration.
- Root cause statement:
  - Timeout pending-slot-question remains split because the timeout-degrade owner surface stops after retry bookkeeping while the bounded reply continuation still executes inline in frozen `decision.py`.
- Fix mechanism:
  - parameterize `policy_timeout_degrade_boundary_service.py` with a bounded `pending_slot_question` mode
  - pass the already-registered retry count into that mode instead of re-running retry bookkeeping
  - delete the frozen inline timeout pending-slot-question response body from `decision.py`

## Invariant
- `decision.py` must lose the live timeout pending-slot-question response authority, not gain another wrapper layer.
- `policy_timeout_degrade_boundary_service.py` must stay bounded to timeout-degrade retry/reply ownership and must not absorb unrelated booking continuity or planner semantics.
- `state_service.py` must not grow.
- Existing timeout pending-slot-question trace/meta/expected-reply behavior must remain unchanged for covered scenarios.

## Scope
- Converge the timeout pending-slot-question reply family into `policy_timeout_degrade_boundary_service.py`
- Delete the frozen inline timeout pending-slot-question response body from `decision.py`
- Update only directly impacted tests/docs

## Out of scope
- Timeout active-name time-availability followup family
- Non-timeout booking slot guidance families
- Timeout owner-boundary resolution families
- Proof bundle / multi-pack correctness claims
- `booking.py` changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-pending-slot-question-boundary-family-convergence-a922.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
1. Reuse `policy_timeout_degrade_boundary_service.py` instead of creating another timeout owner service.
2. Add only the bounded hook/input fields needed for the pending-slot-question continuation after retry registration.
3. Keep trigger detection and retry-intent selection in frozen `decision.py`, but move the response-authority body out of the frozen file.
4. Reuse the existing targeted timeout pending-slot-question tests as the acceptance set.
5. Update repo truth only after the frozen timeout pending-slot-question response body is actually deleted or unreachable.

## Plan
1. Author and register this TP.
2. Extend `policy_timeout_degrade_boundary_service.py` with a bounded `pending_slot_question` mode that consumes the retry count from the existing retry owner call.
3. Delete the frozen timeout pending-slot-question response body from `decision.py` and replace it with owner-surface invocation.
4. Run targeted timeout pending-slot-question runtime checks and required guards.
5. Record evidence in `STATE.md` only if the old live seam is actually deleted or unreachable.

## DoD
- `decision.py` no longer owns the live timeout pending-slot-question response body
- the timeout pending-slot-question path exits through `policy_timeout_degrade_boundary_service.py`
- targeted timeout pending-slot-question tests stay green
- required guards stay green
- `STATE.md` records the deleted/unreachable old seam with evidence

## Checks
- `python3 -m py_compile truffles-api/app/services/policy_timeout_degrade_boundary_service.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_degraded_timeout_pending_slot_question_keeps_resume_contract truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_degraded_timeout_pending_slot_question_survives_basic_info_lock_hours_signal truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_timeout_pending_slot_question_uses_row_scoped_retry_budget truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_timeout_pending_slot_question_uses_row_scoped_limit`
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
  - the frozen timeout pending-slot-question body is deleted from `decision.py`
  - targeted timeout pending-slot-question scenarios pass
  - required architecture/session guards pass
- Rollback:
  - revert this block's changes to `policy_timeout_degrade_boundary_service.py`, `decision.py`, and affected docs
  - rerun the targeted timeout pending-slot-question tests plus guard set
- Rollback verification:
  - `pytest -q truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_degraded_timeout_pending_slot_question_keeps_resume_contract truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_degraded_timeout_pending_slot_question_survives_basic_info_lock_hours_signal truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_timeout_pending_slot_question_uses_row_scoped_retry_budget truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_timeout_pending_slot_question_uses_row_scoped_limit`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`

## Evidence
- updated TP + `STRUCTURE.md`
- diff showing deletion of the frozen timeout pending-slot-question body and reuse of the existing timeout-degrade owner surface
- green targeted timeout pending-slot-question tests + required guards
- `STATE.md` entry with the deleted/unreachable seam

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted timeout pending-slot-question/runtime checks.

## No-go
- Do not create a second timeout-degrade boundary owner for the same family.
- Do not fold timeout active-name time-availability followup or generic booking continuity into this block.
- Do not add another frozen wrapper family in `decision.py`.
- Do not claim consultant correctness/proof closure beyond this block.

## Risks / blockers
- If `policy_timeout_degrade_boundary_service.py` starts absorbing broader booking continuity or active-name availability followup orchestration, the block is drifting.
- If the move requires dialog-state/session-memory synchronization beyond the bounded pending-slot-question reply contract, stop with `GAP` instead of forcing reuse.
- If this move only wraps the inline timeout pending-slot-question path while live authority stays in `decision.py`, the block does not count as progress.

## Token / run budget (mandatory for expensive suites)
- Cheap deterministic gate first: `python3 -m py_compile`
- Targeted timeout pending-slot-question runtime tests next
- Full required guard set only after targeted runtime checks pass
- Stop condition: if two consecutive iterations fail without new structural evidence, stop and return to RCA instead of grinding tests

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- timeout active-name time-availability followup and other residual boundary families remain after this timeout pending-slot-question block
- broader booking continuity ownership still remains outside this block

### Why not in this block
- this block targets one concrete timeout-degrade reply continuation with a bounded delta over the existing timeout-degrade owner surface
- active-name time-availability followup carries additional dialog-state/session-memory coordination and needs separate owner classification

### Risk if deferred
- timeout-degrade boundary ownership remains split between frozen `decision.py` and the non-frozen timeout-degrade owner surface

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-boundary-owner-next-family-selection-a922` (to be authored only if this block lands)

### Expiry/trigger to stop deferral
- stop deferral if more timeout pending-slot-question logic lands in frozen `decision.py`

## Next-block contract (mandatory)
### Next block objective
- classify and select the next real `boundary_owner` residual family after timeout pending-slot-question authority leaves frozen `decision.py`

### First deterministic check command
- `rg -n "timeout_pending_slot_question|booking_slot_guidance|timeout_active_name_time_availability_followup|booking_time_availability_followup" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/policy_timeout_degrade_boundary_service.py`

### Blocked-by conditions
- this block does not delete/unreach the frozen timeout pending-slot-question body
- targeted timeout pending-slot-question tests or required guards fail
- the existing timeout-degrade owner surface becomes a mixed hotspot instead of a bounded timeout family owner

### Owner role for closure
- Brain / Top Architect
