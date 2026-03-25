# TP-2026-03-18-consultant-core-invalid-schema-specialist-boundary-family-convergence-a922

## Goal
Delete the frozen invalid-schema specialist-followup boundary family from `truffles-api/app/routers/webhook/decision.py` by converging that live response body into the existing non-frozen specialist boundary owner surface.

## Canon refs
- `STATE.md` NOW: consultant core timeout booking specialist boundary family convergence
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-booking-specialist-boundary-family-convergence-a922.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after targeted invalid-schema specialist runtime checks plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- Query: `site:refactoring.com/catalog "Move Function" "Parameterize Function"`
- Date/time: `2026-03-18 10:53:15 +0500`
- Opened sources:
  - `https://refactoring.com/catalog/`
  - `https://refactoring.com/catalog/moveFunction.html`
  - `https://refactoring.com/catalog/parameterizeFunction.html`
- Source quality:
  - high-signal / primary-style source: Martin Fowler refactoring catalog pages
- Found ready-made solutions:
  - `Move Function`: move the remaining invalid-schema specialist-followup authority out of frozen `decision.py`
  - `Parameterize Function`: reuse the existing specialist boundary owner by parameterizing guard reason, trace decision, metadata owner, and recovery tags instead of cloning another specialist service
- Decision: `reuse + integrate`
  - reuse `truffles-api/app/services/policy_timeout_booking_specialist_boundary_service.py` as the existing specialist owner surface
  - integrate invalid-schema specialist-followup into that owner by parameterizing the already-shared specialist-followup contract
- Rejected variants:
  - create a second specialist-followup owner service just for invalid-schema: rejected because it would re-split the same specialist boundary family
  - keep `_maybe_send_invalid_schema_specialist_followup_response(...)` inline in frozen `decision.py`: rejected because live specialist boundary authority would remain frozen
  - add another local helper in `decision.py`: rejected because it would rename the seam without deleting it

## Root cause (mandatory)
- Symptom:
  - frozen `decision.py` still owns the invalid-schema specialist-followup response body through `_maybe_send_invalid_schema_specialist_followup_response(...)`
- Minimal reproduction:
  - `rg -n "policy_core_invalid_schema_specialist_followup|invalid_schema_specialist_followup|booking_specialist_followup" truffles-api/app/routers/webhook/decision.py`
- Evidence:
  - `decision.py:14216-14373` still performs booking-state prep, expected-reply continuity, guard override, trace/meta writes, send, commit, return inline
  - that body reuses the same specialist-followup shape already moved for timeout paths: specialist target, `booking_specialist_followup` pending-question trace, booking prompt send, and continuity preservation for the missing slot
  - the real delta versus the existing owner surface is bounded to guard reason, recovery tag, and trigger preconditions
- Five Whys:
  1. Why is `decision.py` still a boundary hotspot? Because invalid-schema specialist-followup authority still lives there.
  2. Why is that still part of the same family? Because it emits the same specialist-followup booking contract as the timeout specialist owner surface.
  3. Why is that a problem now? Because specialist boundary ownership is still split between frozen `decision.py` and the non-frozen owner service.
  4. Why did the previous block not remove it? Because it targeted timeout specialist-followup and timeout master-info-interrupt only.
  5. Why can it move now? Because the existing owner surface already proves the specialist-followup response contract and only needs bounded parameterization.
- Root cause statement:
  - Invalid-schema specialist-followup remains split because the same specialist response contract still has one frozen inline implementation instead of a parameterized call into the existing specialist owner surface.
- Fix mechanism:
  - parameterize the existing specialist owner surface for specialist-followup reason/trace/meta variants
  - move `_maybe_send_invalid_schema_specialist_followup_response(...)` authority into that owner surface
  - delete the frozen inline response body from `decision.py`

## Invariant
- `decision.py` must lose live invalid-schema specialist-followup boundary authority, not gain another helper layer.
- The existing specialist owner surface must stay bounded to specialist-followup / master-info specialist family behavior.
- `state_service.py` must not grow.
- Existing invalid-schema specialist-followup trace/meta/context semantics must remain unchanged for covered scenarios.

## Scope
- Converge invalid-schema specialist-followup into the existing specialist boundary owner surface
- Delete the frozen invalid-schema specialist-followup response body from `decision.py`
- Update only directly impacted tests/docs

## Out of scope
- Timeout specialist family behavior changes beyond bounded parameterization
- Generic booking specialist-followup family in the normal planner path
- Invalid-schema families outside specialist followup
- Proof bundle / multi-pack correctness claims
- `booking.py` changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-invalid-schema-specialist-boundary-family-convergence-a922.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/app/services/policy_timeout_booking_specialist_boundary_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
1. Reuse the existing specialist owner surface instead of creating another service.
2. Parameterize specialist-followup guard reason, trace decision, metadata owner, and recovery tags so timeout and invalid-schema variants can share one owner flow.
3. Keep invalid-schema trigger detection in `decision.py`, but move the response-authority body out of the frozen file.
4. Reuse the existing invalid-schema specialist tests as the acceptance set.
5. Update repo truth only after the frozen invalid-schema specialist-followup body is actually deleted or unreachable.

## Plan
1. Author and register this TP.
2. Parameterize `policy_timeout_booking_specialist_boundary_service.py` for specialist-followup variants.
3. Delete the frozen invalid-schema specialist-followup response body from `decision.py` and replace it with owner-surface invocation.
4. Update only directly impacted tests if patch points move.
5. Run targeted invalid-schema specialist runtime checks and required guards.
6. Record evidence in `STATE.md` only if an old live seam is actually deleted or unreachable.

## DoD
- `decision.py` no longer owns the live invalid-schema specialist-followup response body
- the invalid-schema specialist-followup path exits through the existing non-frozen specialist owner surface
- targeted invalid-schema specialist tests stay green
- required guards stay green
- `STATE.md` records the deleted/unreachable old seam with evidence

## Checks
- `python3 -m py_compile truffles-api/app/services/policy_timeout_booking_specialist_boundary_service.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_invalid_schema_specialist_followup_keeps_time_collect truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_invalid_schema_question_like_named_specialist_followup_keeps_time_collect truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_invalid_schema_booking_request_specialist_followup_uses_branch_catalog_match truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_invalid_schema_booking_request_specialist_followup_uses_unique_branch_first_name_match`
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
  - the frozen invalid-schema specialist-followup body is deleted from `decision.py`
  - targeted invalid-schema specialist scenarios pass
  - required architecture/session guards pass
- Rollback:
  - revert this block's changes to `policy_timeout_booking_specialist_boundary_service.py`, `decision.py`, affected tests/docs
  - rerun the targeted invalid-schema specialist tests plus guard set
- Rollback verification:
  - `pytest -q truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_invalid_schema_specialist_followup_keeps_time_collect truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_invalid_schema_question_like_named_specialist_followup_keeps_time_collect`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`

## Evidence
- updated TP + `STRUCTURE.md`
- diff showing deletion of the frozen invalid-schema specialist-followup body and parameterization of the existing owner surface
- green targeted invalid-schema specialist tests + required guards
- `STATE.md` entry with the deleted/unreachable seam

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted invalid-schema specialist/runtime checks.

## No-go
- Do not create a second specialist boundary service for the same family.
- Do not fold generic planner specialist followup or unrelated invalid-schema families into this block.
- Do not add another frozen wrapper family in `decision.py`.
- Do not claim consultant correctness/proof closure beyond this block.

## Risks / blockers
- If parameterizing the owner surface starts to absorb unrelated planner or invalid-schema behavior, the block is drifting.
- If invalid-schema specialist-followup cannot be expressed as a bounded parameterized variant of the existing owner surface, stop with `GAP` instead of cloning logic.
- If the move only wraps `_maybe_send_invalid_schema_specialist_followup_response(...)` while live authority stays in `decision.py`, the block does not count as progress.

## Token / run budget (mandatory for expensive suites)
- Cheap deterministic gate first: `python3 -m py_compile`
- Targeted invalid-schema specialist runtime tests next
- Full required guard set only after targeted runtime checks pass
- Stop condition: if two consecutive iterations fail without new structural evidence, stop and return to RCA instead of grinding tests

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- generic planner specialist followup families remain after this invalid-schema block
- broader `boundary_owner` remains partial after this block

### Why not in this block
- this block targets one concrete invalid-schema specialist variant with the same already-proven specialist-followup contract
- planner-owned specialist families require a separate owner ledger

### Risk if deferred
- specialist boundary ownership remains split between frozen `decision.py` and the non-frozen owner surface

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-boundary-owner-next-family-selection-a922` (to be authored only if this block lands)

### Expiry/trigger to stop deferral
- stop deferral if new specialist-followup invalid-schema logic lands in frozen `decision.py`

## Next-block contract (mandatory)
### Next block objective
- classify and select the next real `boundary_owner` residual family after invalid-schema specialist-followup authority leaves frozen `decision.py`

### First deterministic check command
- `rg -n "policy_core_invalid_schema_specialist_followup|booking_specialist_followup|booking_specialist_availability_followup|booking_time_availability_followup|master_info_interrupt" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/policy_timeout_booking_specialist_boundary_service.py`

### Blocked-by conditions
- this block does not delete/unreach the frozen invalid-schema specialist-followup body
- targeted invalid-schema specialist tests or required guards fail
- the existing owner surface becomes a mixed hotspot instead of a bounded specialist family owner

### Owner role for closure
- Brain / Top Architect
