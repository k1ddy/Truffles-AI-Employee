# TP-2026-03-18-consultant-core-timeout-active-name-time-followup-boundary-family-convergence-a922

## Goal
Delete the frozen timeout active-name time-availability followup boundary family from `truffles-api/app/routers/webhook/decision.py` by converging that live timeout-degrade continuity+reply body into one narrow non-frozen owner surface.

## Canon refs
- `STATE.md` NOW: consultant core timeout pending-slot-question boundary family convergence
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-pending-slot-question-boundary-family-convergence-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-booking-specialist-boundary-family-convergence-a922.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after targeted timeout active-name time-followup runtime checks plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- Query: `site:refactoring.com/catalog "Move Function" "Extract Function" "Form Template Method"`
- Date/time: `2026-03-18 11:41:04 +0500`
- Opened sources:
  - `https://refactoring.com/catalog/moveFunction.html`
  - `https://refactoring.com/catalog/extractFunction.html`
  - `https://refactoring.com/catalog/formTemplateMethod.html`
- Source quality:
  - high-signal / primary-style source: Martin Fowler refactoring catalog
- Found ready-made solutions:
  - `Move Function`: move the remaining timeout active-name time-followup authority out of frozen `decision.py`
  - `Extract Function`: isolate the bounded continuity+reply workflow from the larger degraded-collect branch
  - `Form Template Method`: preserve the repeated boundary workflow shape (continuity sync -> guard/trace/meta -> reply/send) behind one narrow owner surface
- Decision: `build narrow owner surface`
  - do not expand `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`, because that service currently owns retry bookkeeping and simple reply continuations, while this family also owns canonical-dialog-state and session-memory synchronization
  - build one narrow owner surface for the timeout booking time-followup family so the continuity-heavy reply path leaves frozen `decision.py` without turning an existing service into a god-file
- Rejected variants:
  - expand `policy_timeout_degrade_boundary_service.py`: rejected because it would mix retry bookkeeping and continuity-heavy followup orchestration in one growing timeout service
  - expand `policy_timeout_booking_specialist_boundary_service.py`: rejected because this family is about time availability followup, not specialist followup/interrupt ownership
  - expand `timeout_owner_boundary_service.py`: rejected because this family is not owner-resolution / matched-expected-reply boundary application
  - keep the response body inline in frozen `decision.py`: rejected because live boundary authority would remain frozen
  - add another local helper in `decision.py`: rejected because it would rename the seam without deleting it

## Root cause (mandatory)
- Symptom:
  - frozen `decision.py` still owns the timeout active-name time-availability followup response body
- Minimal reproduction:
  - `rg -n "timeout_active_name_time_availability_followup|booking_time_availability_followup|_sync_canonical_dialog_state|_sync_session_memory_interaction_state|_build_active_name_time_availability_followup_response" truffles-api/app/routers/webhook/decision.py truffles-api/app/services`
- Evidence:
  - `decision.py:15717-15864` still performs expected-reply continuity, canonical dialog-state sync, session-memory sync/update, guard override, trace/meta writes, response build, consult-return merge, send, commit, and return inline
  - this family is bounded and already has targeted proof surface in `truffles-api/tests/test_message_endpoint.py::test_timeout_active_name_time_availability_followup_keeps_name_resume`
  - existing timeout owner surfaces do not currently own this exact continuity-heavy followup workflow
- Five Whys:
  1. Why is `decision.py` still a boundary hotspot? Because timeout active-name time-availability followup still lives inline there.
  2. Why is this a distinct family instead of another micro-seam? Because the branch owns one coherent continuity+reply workflow with one acceptance contour and one recovery identity.
  3. Why is that a problem now? Because `boundary_owner` still remains split between non-frozen timeout owner surfaces and frozen `decision.py` for this live family.
  4. Why can the existing retry owner not absorb it safely? Because this branch also coordinates canonical dialog-state and session-memory followup continuity, which is a different ownership weight than retry bookkeeping.
  5. Why is a narrow new owner surface justified? Because the family is bounded, continuity-heavy, and not truthfully reusable inside the existing timeout owner modules without creating a mixed hotspot.
- Root cause statement:
  - Timeout active-name time-followup remains split because its continuity-heavy reply workflow still executes inline in frozen `decision.py`, and no existing non-frozen timeout owner surface truthfully owns that exact family.
- Fix mechanism:
  - build one narrow timeout booking time-followup boundary owner surface outside frozen files
  - move the inline continuity+reply body into that service behind explicit runtime hooks/input
  - delete the frozen inline response body from `decision.py`

## Invariant
- `decision.py` must lose the live timeout active-name time-followup response authority, not gain another wrapper layer.
- The new owner surface must stay bounded to this followup family; it must not absorb generic booking continuity or unrelated timeout branches.
- `state_service.py` must not grow.
- Existing timeout active-name time-followup trace/meta/context/session-memory semantics must remain unchanged for covered scenarios.

## Scope
- Converge the timeout active-name time-availability followup family into one narrow non-frozen owner surface
- Delete the frozen inline timeout active-name time-followup response body from `decision.py`
- Update only directly impacted tests/docs

## Out of scope
- Timeout pending-slot-question family
- Timeout specialist followup / master-info-interrupt family
- Generic degraded collect / reschedule-handoff family
- Proof bundle / multi-pack correctness claims
- `booking.py` changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-active-name-time-followup-boundary-family-convergence-a922.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/app/services/policy_timeout_booking_time_followup_boundary_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
1. Reuse the existing continuity/runtime hook primitives already present in `decision.py` (`_set_expected_reply_context`, `_sync_canonical_dialog_state`, `_sync_session_memory_interaction_state`, `_record_session_memory_update`) instead of inventing new continuity infrastructure.
2. Build one narrow owner surface only for this family because existing timeout owner surfaces are not a truthful destination.
3. Keep trigger detection in frozen `decision.py`, but move the live continuity+reply body out of the frozen file.
4. Reuse the existing targeted timeout active-name time-followup test as the acceptance set.
5. Update repo truth only after the frozen timeout active-name time-followup body is actually deleted or unreachable.

## Plan
1. Author and register this TP.
2. Create a narrow `policy_timeout_booking_time_followup_boundary_service.py` owner surface with explicit runtime hooks/input for this family.
3. Delete the frozen timeout active-name time-followup response body from `decision.py` and replace it with owner-surface invocation.
4. Run targeted timeout active-name time-followup runtime checks and required guards.
5. Record evidence in `STATE.md` only if the old live seam is actually deleted or unreachable.

## DoD
- `decision.py` no longer owns the live timeout active-name time-followup response body
- the timeout active-name time-followup path exits through `policy_timeout_booking_time_followup_boundary_service.py`
- targeted timeout active-name time-followup tests stay green
- required guards stay green
- `STATE.md` records the deleted/unreachable old seam with evidence

## Checks
- `python3 -m py_compile truffles-api/app/services/policy_timeout_booking_time_followup_boundary_service.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py::test_timeout_active_name_time_availability_followup_keeps_name_resume`
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
  - the frozen timeout active-name time-followup body is deleted from `decision.py`
  - targeted timeout active-name time-followup scenario passes
  - required architecture/session guards pass
- Rollback:
  - revert this block's changes to `policy_timeout_booking_time_followup_boundary_service.py`, `decision.py`, and affected docs
  - rerun the targeted timeout active-name time-followup tests plus guard set
- Rollback verification:
  - `pytest -q truffles-api/tests/test_message_endpoint.py::test_timeout_active_name_time_availability_followup_keeps_name_resume`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`

## Evidence
- updated TP + `STRUCTURE.md`
- diff showing deletion of the frozen timeout active-name time-followup body and cutover to the narrow owner surface
- green targeted timeout active-name time-followup tests + required guards
- `STATE.md` entry with the deleted/unreachable seam

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted timeout active-name time-followup/runtime checks.

## No-go
- Do not expand `policy_timeout_degrade_boundary_service.py` into a continuity-heavy timeout god-file.
- Do not fold generic degraded collect / reschedule-handoff or specialist branches into this block.
- Do not add another frozen wrapper family in `decision.py`.
- Do not claim consultant correctness/proof closure beyond this block.

## Risks / blockers
- If the new owner surface starts absorbing unrelated timeout families, the block is drifting.
- If the move requires broader continuity-owner refactoring instead of a bounded service extraction, stop with `GAP` instead of forcing the cut.
- If this move only wraps the inline timeout active-name time-followup path while live authority stays in `decision.py`, the block does not count as progress.

## Token / run budget (mandatory for expensive suites)
- Cheap deterministic gate first: `python3 -m py_compile`
- Targeted timeout active-name time-followup runtime test next
- Full required guard set only after targeted runtime checks pass
- Stop condition: if two consecutive iterations fail without new structural evidence, stop and return to RCA instead of grinding tests

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- other residual `boundary_owner` families remain after this timeout active-name time-followup block
- broader degraded collect / handoff orchestration still remains outside this block

### Why not in this block
- this block targets one concrete continuity-heavy timeout followup family with one acceptance contour
- degraded collect / handoff requires separate family classification and likely different owner destination

### Risk if deferred
- boundary ownership remains split because frozen `decision.py` still hosts a live continuity-heavy timeout followup family

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-boundary-owner-next-family-selection-a922` (to be authored only if this block lands)

### Expiry/trigger to stop deferral
- stop deferral if more timeout active-name time-followup logic lands in frozen `decision.py`

## Next-block contract (mandatory)
### Next block objective
- classify and select the next real `boundary_owner` residual family after timeout active-name time-followup authority leaves frozen `decision.py`

### First deterministic check command
- `rg -n "timeout_active_name_time_availability_followup|booking_time_availability_followup|degraded_collect_reschedule_handoff|policy_core_degraded_collect_guard" truffles-api/app/routers/webhook/decision.py truffles-api/app/services`

### Blocked-by conditions
- this block does not delete/unreach the frozen timeout active-name time-followup body
- targeted timeout active-name time-followup tests or required guards fail
- the new owner surface grows beyond this bounded family

### Owner role for closure
- Brain / Top Architect
