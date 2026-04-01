# TP-2026-03-18-consultant-core-timeout-degrade-retry-boundary-family-convergence-a922

## Goal
Delete the frozen timeout-degrade retry/clarify/handoff family from `truffles-api/app/routers/webhook/decision.py` by converging the generic timeout clarify path and the booking timeout retry-limit path into one narrow non-frozen boundary owner surface.

## Canon refs
- `STATE.md` NOW: consultant core policy-validation boundary family convergence
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-policy-validation-boundary-family-convergence-a922.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after targeted timeout-degrade runtime checks plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- Query: `site:refactoring.com/catalog "Consolidate Duplicate Conditional Fragments" "Extract Function"`
- Date/time: `2026-03-18 16:19:00 +05`
- Opened sources:
  - `https://refactoring.com/catalog/slideStatements.html`
  - `https://refactoring.com/catalog/extractFunction.html`
- Source quality:
  - high-signal / primary-style source: Martin Fowler refactoring catalog pages
- Found ready-made solutions:
  - `Consolidate Duplicate Conditional Fragments` / `Slide Statements`: move repeated side effects out of duplicated branches so branch deltas become explicit
  - `Extract Function`: lift a bounded repeated flow into one named owner surface with stable parameters
- Decision: `reuse + build`
  - build one narrow `policy_timeout_degrade_boundary_service.py` owner surface for the timeout-degrade retry family
  - reuse existing router hooks, trace/meta writers, and clarify-escalation helper instead of inventing new runtime infrastructure
- Rejected variants:
  - extend `timeout_owner_boundary_service.py` with all timeout fallback branches immediately: rejected because that would mix owner-boundary resolution with retry-budget / clarify-escalation orchestration
  - leave the duplicated retry blocks in frozen `decision.py`: rejected because the live boundary family would remain frozen
  - add another local helper in `decision.py`: rejected because it would rename the seam without deleting the old authority

## Root cause (mandatory)
- Symptom:
  - frozen `decision.py` still owns duplicated timeout-degrade retry authority for both generic clarify fallback and booking collect fallback
- Minimal reproduction:
  - `rg -n "timeout_retry_intent|timeout_retry_reason|timeout_retry_path|timeout_retry_limit_decision|timeout_retry_limit_reason|timeout_clarify_limit|timeout_clarify|timeout_booking_limit|timeout_booking_collect|_handle_clarify_limit_escalation\\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/timeout_owner_boundary_service.py`
- Evidence:
  - `decision.py:15320` implements generic timeout clarify retry / limit escalation inline
  - `decision.py:15988` implements booking timeout retry / limit escalation inline with the same retry-budget skeleton and mode-specific trace/meta delta
  - both branches repeat the same ordered steps: read retry state, decide exhausted vs continue, write clarify-attempt or clarify-limit metadata, apply guard override, emit trace/meta, and either escalate or continue
- Five Whys:
  1. Why is `decision.py` still a boundary hotspot? Because timeout-degrade retry authority still lives there.
  2. Why is this a family instead of isolated branches? Because the generic and booking paths share one retry-budget / handoff skeleton with only mode-specific trace/result deltas.
  3. Why is that a problem now? Because timeout fallback behavior can still grow inside frozen `decision.py` after previous boundary cuts.
  4. Why did earlier blocks not remove it? Because previous timeout work targeted owner-boundary collect application, not retry/clarify authority.
  5. Why can it move now? Because the family boundary is stable: both paths are already keyed by `timeout_degrade` and rely on the same retry counter contract.
- Root cause statement:
  - The timeout-degrade retry family is still split because its retry-budget / clarify-limit / handoff workflow remains embedded in frozen `decision.py` instead of one non-frozen owner surface with generic-vs-booking mode deltas.
- Fix mechanism:
  - move the shared timeout-degrade retry family into a narrow service
  - delete the duplicated frozen retry blocks from `decision.py`
  - reduce frozen call sites to owner-surface invocation plus downstream branch-specific continuation

## Invariant
- `decision.py` must lose live timeout-degrade retry authority, not gain another local wrapper forest.
- `timeout_owner_boundary_service.py` must not become a mixed timeout god-file.
- `state_service.py` must not grow.
- Existing timeout trace/meta/retry-budget semantics must stay unchanged for covered scenarios.

## Scope
- Converge the generic timeout clarify retry path into one non-frozen owner surface
- Converge the booking timeout retry / limit path into the same owner surface
- Delete the duplicated frozen retry blocks from `decision.py`
- Update only directly impacted tests/docs

## Out of scope
- Broader timeout fact fallback / style-reference / info-fallback paths
- Broader boundary-owner closure beyond this retry family
- Handover family changes
- Continuity family changes
- Proof bundle / multi-pack correctness claims
- `booking.py` changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-degrade-retry-boundary-family-convergence-a922.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
1. Reuse existing retry-budget state from `_get_clarify_attempt_state(...)` via a service hook instead of creating new persistence.
2. Reuse `_handle_clarify_limit_escalation(...)` for the actual escalation side effect; do not fork another escalation runtime path.
3. Build one narrow `policy_timeout_degrade_boundary_service.py` that owns the duplicated retry/clarify/handoff workflow.
4. Reuse existing message-endpoint tests covering timeout booking collect, pending-slot guidance, and timeout booking limit before adding new tests.
5. Update repo truth only after the old frozen retry blocks are actually deleted/unreachable.

## Plan
1. Author and register this TP.
2. Implement `policy_timeout_degrade_boundary_service.py` with shared runtime input/hooks for generic clarify and booking retry modes.
3. Delete the duplicated retry blocks from frozen `decision.py` and replace them with owner-surface invocation.
4. Update targeted tests only if import/patch points require it.
5. Run targeted timeout-degrade runtime checks and required guards.
6. Record evidence in `STATE.md` only if an old live seam is actually deleted or unreachable.

## DoD
- `decision.py` no longer owns the duplicated timeout-degrade retry blocks at the current generic clarify and booking retry sites
- the timeout-degrade retry family is owned by one non-frozen service surface
- targeted timeout-degrade runtime tests stay green
- required guards stay green
- `STATE.md` records the deleted/unreachable old seam with evidence

## Checks
- `python3 -m py_compile truffles-api/app/services/policy_timeout_degrade_boundary_service.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_degraded_timeout_without_attempt_still_uses_clarify truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_degraded_timeout_booking_request_wins_over_info_query_heuristic truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_degraded_timeout_pending_slot_question_keeps_resume_contract truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_timeout_pending_slot_question_uses_row_scoped_retry_budget truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_timeout_pending_slot_question_uses_row_scoped_limit truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_degraded_timeout_booking_safe_second_hit_escalates`
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
  - duplicated timeout-degrade retry blocks are deleted from `decision.py`
  - targeted timeout-degrade scenarios pass
  - required architecture/session guards pass
- Rollback:
  - revert this block's changes to `policy_timeout_degrade_boundary_service.py`, `decision.py`, affected tests/docs
  - rerun the targeted timeout-degrade tests plus guard set
- Rollback verification:
  - `pytest -q truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_degraded_timeout_pending_slot_question_keeps_resume_contract truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_timeout_pending_slot_question_uses_row_scoped_limit`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`

## Evidence
- updated TP + `STRUCTURE.md`
- diff showing deletion of the two frozen timeout-degrade retry blocks and the new owner-surface service
- green targeted timeout-degrade tests + required guards
- `STATE.md` entry with the deleted/unreachable seam

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted timeout-degrade/runtime checks.

## No-go
- Do not turn `timeout_owner_boundary_service.py` into a mixed retry/escalation/fallback grab-bag.
- Do not add another frozen wrapper family in `decision.py`.
- Do not move unrelated timeout fact fallback, style-reference, or booking-followup flows into this service.
- Do not claim consultant correctness/proof closure beyond this block.

## Risks / blockers
- The booking timeout path has downstream prompt-building branches; if the service cannot own the retry family without dragging all booking response assembly into a mixed file, stop with `GAP`.
- If this move only wraps the duplicated blocks while live authority stays in `decision.py`, the block does not count as progress.
- Repo-truth updates will require synchronized packet/test expectation changes after the block lands.

## Token / run budget (mandatory for expensive suites)
- Cheap deterministic gate first: `python3 -m py_compile`
- Targeted timeout-degrade runtime tests next
- Full required guard set only after targeted runtime checks pass
- Stop condition: if two consecutive iterations fail without new structural evidence, stop and return to RCA instead of grinding tests

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- broader timeout fallback families remain after this retry block
- `boundary_owner` still remains partial after this block

### Why not in this block
- this block targets one concrete repeated retry family with stable timeout-degrade invariants
- broader timeout fallback and booking-followup ownership require a separate family ledger

### Risk if deferred
- new timeout retry / clarify behavior can continue landing in frozen `decision.py`

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-boundary-owner-next-family-selection-a922` (to be authored only if this block lands)

### Expiry/trigger to stop deferral
- stop deferral if new timeout retry logic lands in frozen `decision.py`

## Next-block contract (mandatory)
### Next block objective
- classify and select the next real `boundary_owner` residual family after timeout-degrade retry authority leaves frozen `decision.py`

### First deterministic check command
- `rg -n "timeout_degrade|timeout_owner_boundary|policy_validation|_handle_clarify_limit_escalation\\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/policy_timeout_degrade_boundary_service.py truffles-api/app/services/timeout_owner_boundary_service.py`

### Blocked-by conditions
- this block does not delete/unreach the duplicated frozen timeout retry blocks
- targeted timeout-degrade tests or required guards fail
- the new service becomes a mixed timeout hotspot instead of one narrow family owner

### Owner role for closure
- Brain / Top Architect
