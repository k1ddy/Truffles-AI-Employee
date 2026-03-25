# TP-2026-03-18-consultant-core-invalid-schema-service-grounded-booking-boundary-family-convergence-a922

## Goal
Delete the frozen invalid-schema service-grounded booking boundary family from `truffles-api/app/routers/webhook/decision.py` by converging that live response body into an existing non-frozen contract-validation boundary owner surface.

## Canon refs
- `STATE.md` NOW: consultant core invalid-schema specialist boundary family convergence
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-policy-validation-boundary-family-convergence-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-invalid-schema-specialist-boundary-family-convergence-a922.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after targeted invalid-schema service-grounded booking runtime checks plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- Query: `site:refactoring.com/catalog "Move Function" "Parameterize Function"`
- Date/time: `2026-03-18 11:15:23 +0500`
- Opened sources:
  - `https://refactoring.com/catalog/`
  - `https://refactoring.com/catalog/moveFunction.html`
  - `https://refactoring.com/catalog/parameterizeFunction.html`
- Source quality:
  - high-signal / primary-style source: Martin Fowler refactoring catalog pages
- Found ready-made solutions:
  - `Move Function`: move the remaining invalid-schema service-grounded booking authority out of frozen `decision.py`
  - `Parameterize Function`: reuse the existing contract-validation boundary owner by parameterizing the bounded booking-prompt variant instead of creating another owner service
- Decision: `reuse + integrate`
  - reuse `truffles-api/app/services/policy_validation_boundary_service.py` as the existing contract-validation boundary owner surface
  - integrate invalid-schema service-grounded booking into that owner by adding a bounded service-grounded booking mode
- Rejected variants:
  - create another invalid-schema booking boundary service: rejected because it would split the same contract-validation family across multiple owners
  - move this family into timeout recovery or timeout specialist owners: rejected because this is `contract_validation_failure`, not timeout-driven boundary logic
  - keep `_maybe_send_invalid_schema_service_grounded_booking_response(...)` inline in frozen `decision.py`: rejected because live boundary authority would remain frozen
  - add another local helper in `decision.py`: rejected because it would rename the seam without deleting it

## Root cause (mandatory)
- Symptom:
  - frozen `decision.py` still owns the invalid-schema service-grounded booking response body through `_maybe_send_invalid_schema_service_grounded_booking_response(...)`
- Minimal reproduction:
  - `rg -n "def _maybe_send_invalid_schema_service_grounded_booking_response|policy_core_invalid_schema_service_grounded_booking|service_query_source" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/policy_validation_boundary_service.py`
- Evidence:
  - `decision.py:14315-14435` still performs service query selection, booking-state mutation, service-hint mutation, expected-reply continuity, guard override, trace/meta writes, send, commit, and return inline
  - that body is another contract-validation degrade booking-prompt path, not a timeout family
  - the real delta versus the existing policy-validation owner surface is bounded to `service_query`, `service_query_source`, service-hint write, and recovery identifiers
- Five Whys:
  1. Why is `decision.py` still a boundary hotspot? Because invalid-schema service-grounded booking authority still lives there.
  2. Why is that part of the same family as policy-validation ownership? Because it is another `contract_validation_failure` degrade path that produces a booking prompt with the same guard/trace/send workflow.
  3. Why is that a problem now? Because contract-validation boundary ownership is still split between frozen `decision.py` and `policy_validation_boundary_service.py`.
  4. Why did the previous blocks not remove it? Because they targeted policy-validation reply family, timeout families, and invalid-schema specialist-followup only.
  5. Why can it move now? Because the remaining delta is bounded and reusable inside the existing contract-validation owner surface.
- Root cause statement:
  - Invalid-schema service-grounded booking remains split because one contract-validation booking-prompt variant still has a frozen inline implementation instead of a bounded mode inside the existing non-frozen validation boundary owner surface.
- Fix mechanism:
  - parameterize `policy_validation_boundary_service.py` with a bounded `service_grounded_booking` mode and service-hint hook
  - move `_maybe_send_invalid_schema_service_grounded_booking_response(...)` authority into that owner surface
  - delete the frozen inline response body from `decision.py`

## Invariant
- `decision.py` must lose live invalid-schema service-grounded booking boundary authority, not gain another helper layer.
- `policy_validation_boundary_service.py` must stay bounded to contract-validation degrade behavior; no timeout or planner semantics may be imported into it.
- `state_service.py` must not grow.
- Existing invalid-schema service-grounded booking trace/meta/context semantics must remain unchanged for covered scenarios.

## Scope
- Converge invalid-schema service-grounded booking into the existing contract-validation boundary owner surface
- Delete the frozen invalid-schema service-grounded booking response body from `decision.py`
- Update only directly impacted tests/docs

## Out of scope
- Invalid-schema specialist-followup family changes beyond already-landed cutover
- Timeout boundary families
- Generic planner booking-prompt owner paths in `reasoning_core`
- Proof bundle / multi-pack correctness claims
- `booking.py` changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-invalid-schema-service-grounded-booking-boundary-family-convergence-a922.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
1. Reuse `policy_validation_boundary_service.py` instead of creating another invalid-schema owner service.
2. Add only the bounded hook/input fields needed for service-grounded booking: service hint write plus service-query metadata.
3. Keep invalid-schema trigger detection in `decision.py`, but move the response-authority body out of the frozen file.
4. Reuse the existing targeted invalid-schema service-grounded booking test as the acceptance set.
5. Update repo truth only after the frozen invalid-schema service-grounded booking body is actually deleted or unreachable.

## Plan
1. Author and register this TP.
2. Extend `policy_validation_boundary_service.py` with a bounded `service_grounded_booking` mode plus the minimum extra hook/input fields.
3. Delete the frozen invalid-schema service-grounded booking response body from `decision.py` and replace it with owner-surface invocation.
4. Update only directly impacted tests if patch points move.
5. Run targeted invalid-schema service-grounded booking runtime checks and required guards.
6. Record evidence in `STATE.md` only if an old live seam is actually deleted or unreachable.

## DoD
- `decision.py` no longer owns the live invalid-schema service-grounded booking response body
- the invalid-schema service-grounded booking path exits through `policy_validation_boundary_service.py`
- targeted invalid-schema service-grounded booking tests stay green
- required guards stay green
- `STATE.md` records the deleted/unreachable old seam with evidence

## Checks
- `python3 -m py_compile truffles-api/app/services/policy_validation_boundary_service.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_invalid_schema_booking_request_with_service_hint_uses_datetime_prompt`
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
  - the frozen invalid-schema service-grounded booking body is deleted from `decision.py`
  - targeted invalid-schema service-grounded booking scenario passes
  - required architecture/session guards pass
- Rollback:
  - revert this block's changes to `policy_validation_boundary_service.py`, `decision.py`, affected tests/docs
  - rerun the targeted invalid-schema service-grounded booking tests plus guard set
- Rollback verification:
  - `pytest -q truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_invalid_schema_booking_request_with_service_hint_uses_datetime_prompt`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`

## Evidence
- updated TP + `STRUCTURE.md`
- diff showing deletion of the frozen invalid-schema service-grounded booking body and reuse of the existing validation owner surface
- green targeted invalid-schema service-grounded booking tests + required guards
- `STATE.md` entry with the deleted/unreachable seam

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted invalid-schema service-grounded booking/runtime checks.

## No-go
- Do not create a second contract-validation boundary owner for the same family.
- Do not fold timeout or planner booking-prompt ownership into this block.
- Do not add another frozen wrapper family in `decision.py`.
- Do not claim consultant correctness/proof closure beyond this block.

## Risks / blockers
- If `policy_validation_boundary_service.py` starts absorbing generic planner booking-prompt behavior, the block is drifting.
- If the move requires timeout-specific hooks or specialist-specific branching inside the validation owner surface, stop with `GAP` instead of forcing reuse.
- If this move only wraps `_maybe_send_invalid_schema_service_grounded_booking_response(...)` while live authority stays in `decision.py`, the block does not count as progress.

## Token / run budget (mandatory for expensive suites)
- Cheap deterministic gate first: `python3 -m py_compile`
- Targeted invalid-schema service-grounded booking runtime test next
- Full required guard set only after targeted runtime checks pass
- Stop condition: if two consecutive iterations fail without new structural evidence, stop and return to RCA instead of grinding tests

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- other residual `boundary_owner` families remain after this invalid-schema service-grounded booking block
- broader generic booking-prompt ownership still remains outside this block

### Why not in this block
- this block targets one concrete contract-validation booking-prompt variant with a bounded delta over the existing validation owner surface
- broader booking-prompt ownership requires a separate owner ledger

### Risk if deferred
- contract-validation boundary ownership remains split between frozen `decision.py` and the non-frozen validation owner surface

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-boundary-owner-next-family-selection-a922` (to be authored only if this block lands)

### Expiry/trigger to stop deferral
- stop deferral if new invalid-schema booking-prompt logic lands in frozen `decision.py`

## Next-block contract (mandatory)
### Next block objective
- classify and select the next real `boundary_owner` residual family after invalid-schema service-grounded booking authority leaves frozen `decision.py`

### First deterministic check command
- `rg -n "policy_core_invalid_schema_service_grounded_booking|invalid_schema_service_grounded_booking|policy_validation:|timeout_degrade|booking_prompt" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/policy_validation_boundary_service.py`

### Blocked-by conditions
- this block does not delete/unreach the frozen invalid-schema service-grounded booking body
- targeted invalid-schema service-grounded booking tests or required guards fail
- the existing validation owner surface becomes a mixed hotspot instead of a bounded contract-validation family owner

### Owner role for closure
- Brain / Top Architect
