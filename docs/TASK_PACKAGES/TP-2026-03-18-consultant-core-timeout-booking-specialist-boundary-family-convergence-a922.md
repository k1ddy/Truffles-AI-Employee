# TP-2026-03-18-consultant-core-timeout-booking-specialist-boundary-family-convergence-a922

## Goal
Delete the frozen timeout booking specialist boundary family from `truffles-api/app/routers/webhook/decision.py` by converging the timeout specialist-followup and timeout master-info-interrupt paths into one narrow non-frozen owner surface.

## Canon refs
- `STATE.md` NOW: consultant core timeout non-booking recovery boundary family convergence
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-nonbooking-recovery-boundary-family-convergence-a922.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after targeted timeout booking specialist runtime checks plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- Query: `site:refactoring.com/catalog "Move Function" "Consolidate Duplicate Conditional Fragments"`
- Date/time: `2026-03-18 10:53:15 +0500`
- Opened sources:
  - `https://refactoring.com/catalog/`
  - `https://refactoring.com/catalog/moveFunction.html`
  - `https://refactoring.com/catalog/consolidateDuplicateConditionalFragments.html`
- Source quality:
  - high-signal / primary-style source: Martin Fowler refactoring catalog pages
- Found ready-made solutions:
  - `Move Function`: move bounded timeout booking specialist response ownership out of frozen `decision.py` into one dedicated service
  - `Consolidate Duplicate Conditional Fragments`: keep slot-specific guard detection in the caller while converging the repeated booking-state / trace / meta / send / commit fragments into one owner surface
- Decision: `reuse + build`
  - build one narrow timeout booking specialist boundary owner surface
  - reuse existing router hooks, booking interrupt handler, booking context writers, expected-reply writers, and trace/meta writers
- Rejected variants:
  - extend `policy_timeout_recovery_boundary_service.py`: rejected because that service now owns non-booking timeout recovery replies and this family is booking-safe continuity/interrupt ownership
  - extend `timeout_owner_boundary_service.py`: rejected for now because this family owns specialist-followup and booking-interrupt behavior beyond the timeout owner-boundary application contract
  - keep the four timeout specialist / master-info bodies inline in frozen `decision.py`: rejected because live boundary authority would remain frozen
  - add a local helper in `decision.py`: rejected because it would rename the seam without deleting it

## Root cause (mandatory)
- Symptom:
  - frozen `decision.py` still owns the timeout booking specialist-followup and timeout master-info-interrupt family
- Minimal reproduction:
  - `rg -n "policy_core_timeout_specialist_followup|policy_core_timeout_master_info_interrupt|timeout_specialist_followup|timeout_master_info_interrupt|booking_collect_specialist_followup|booking_interrupt_master_info" truffles-api/app/routers/webhook/decision.py`
- Evidence:
  - `decision.py:15279-15751` contains four live timeout specialist / interrupt responders
  - the family repeats one authority skeleton: prepare booking state, preserve expected-reply continuity when needed, apply policy guard override, emit trace/meta, send or delegate interrupt response, commit, return
  - the real delta is bounded: missing slot (`datetime` vs `name`), specialist payload shape, active-question relation, and whether the response is direct prompt or booking-interrupt info reply
- Five Whys:
  1. Why is `decision.py` still a boundary hotspot? Because timeout booking specialist-followup and master-info-interrupt authority still lives there.
  2. Why is it one family? Because both timeout specialist-followup and master-info-interrupt paths preserve the same booking-safe specialist target contract under timeout degrade.
  3. Why is that a problem now? Because new timeout booking specialist behavior can still accrete in frozen `decision.py`.
  4. Why did the previous timeout block not remove it? Because that block targeted non-booking timeout recovery replies, not booking-safe specialist followup / interrupt ownership.
  5. Why can it move now? Because detection remains bounded in the caller while the response-authority skeleton is stable and already covered by targeted tests.
- Root cause statement:
  - The timeout booking specialist boundary family is still split because its shared booking-state / trace / meta / response ownership remains embedded in frozen `decision.py` instead of one non-frozen owner surface.
- Fix mechanism:
  - move the timeout booking specialist family into one narrow owner service
  - delete the frozen response bodies from `decision.py`
  - reduce the call sites to owner-surface invocation with shared hooks and an explicit interrupt hook

## Invariant
- `decision.py` must lose live timeout booking specialist boundary authority, not gain another local helper forest.
- `policy_timeout_recovery_boundary_service.py` must remain non-booking only.
- `state_service.py` must not grow.
- Existing timeout specialist-followup / master-info-interrupt trace/meta/context semantics must remain unchanged for covered scenarios.

## Scope
- Converge timeout specialist-followup and timeout master-info-interrupt response ownership into one non-frozen service
- Delete the four frozen timeout specialist / interrupt response bodies from `decision.py`
- Update only directly impacted tests/docs

## Out of scope
- Non-timeout specialist followup families
- Invalid-schema specialist followup families
- Timeout retry-budget / clarify-limit family
- Timeout non-booking recovery family
- Proof bundle / multi-pack correctness claims
- `booking.py` changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-booking-specialist-boundary-family-convergence-a922.md`
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
1. Reuse existing booking context, expected-reply, trace, meta, and send helpers from the router via explicit hooks instead of creating new state APIs.
2. Build one narrow `policy_timeout_booking_specialist_boundary_service.py` that owns the timeout specialist-followup / master-info-interrupt response workflow.
3. Keep detection in `decision.py` as explicit guards, but move the response-authority skeleton out of the frozen file.
4. Reuse existing timeout specialist and master-info interrupt tests as the acceptance set.
5. Update repo truth only after the old frozen specialist / interrupt bodies are actually deleted or unreachable.

## Plan
1. Author and register this TP.
2. Implement `policy_timeout_booking_specialist_boundary_service.py` with bounded runtime input/hooks for timeout specialist followup and timeout master-info interrupt.
3. Delete the frozen timeout specialist / interrupt response bodies from `decision.py` and replace them with owner-surface invocation.
4. Update only directly impacted tests if patch points move.
5. Run targeted timeout specialist runtime checks and required guards.
6. Record evidence in `STATE.md` only if an old live seam is actually deleted or unreachable.

## DoD
- `decision.py` no longer owns the live timeout specialist-followup / master-info-interrupt response bodies
- the timeout booking specialist boundary family is owned by one non-frozen service surface
- targeted timeout specialist tests stay green
- required guards stay green
- `STATE.md` records the deleted/unreachable old seam with evidence

## Checks
- `python3 -m py_compile truffles-api/app/services/policy_timeout_booking_specialist_boundary_service.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_timeout_specialist_followup_keeps_time_collect truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_timeout_master_info_interrupt_keeps_time_collect_for_generic_specialist_change truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_timeout_active_name_specialist_followup_keeps_name_collect truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_timeout_master_info_interrupt_resumes_name_collect`
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
  - the four timeout specialist / interrupt response bodies are deleted from `decision.py`
  - targeted timeout specialist scenarios pass
  - required architecture/session guards pass
- Rollback:
  - revert this block's changes to `policy_timeout_booking_specialist_boundary_service.py`, `decision.py`, affected tests/docs
  - rerun the targeted timeout specialist tests plus guard set
- Rollback verification:
  - `pytest -q truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_timeout_specialist_followup_keeps_time_collect truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_timeout_master_info_interrupt_keeps_time_collect_for_generic_specialist_change`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`

## Evidence
- updated TP + `STRUCTURE.md`
- diff showing deletion of the four frozen timeout specialist / interrupt bodies and the new owner-surface service
- green targeted timeout specialist tests + required guards
- `STATE.md` entry with the deleted/unreachable seam

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted timeout specialist/runtime checks.

## No-go
- Do not fold invalid-schema specialist followup or generic booking interrupt families into this block.
- Do not add another frozen wrapper family in `decision.py`.
- Do not move unrelated specialist semantics into a generic mixed helper.
- Do not claim consultant correctness/proof closure beyond this block.

## Risks / blockers
- If the new service starts owning timeout detection instead of bounded response authority, the block is drifting.
- If the interrupt branch cannot be converged without re-hosting `_handle_booking_interrupt(...)` semantics in the new service, stop with `GAP`.
- If this move only wraps the branches while live authority stays in `decision.py`, the block does not count as progress.

## Token / run budget (mandatory for expensive suites)
- Cheap deterministic gate first: `python3 -m py_compile`
- Targeted timeout specialist runtime tests next
- Full required guard set only after targeted runtime checks pass
- Stop condition: if two consecutive iterations fail without new structural evidence, stop and return to RCA instead of grinding tests

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- invalid-schema specialist followup families remain after this timeout booking specialist block
- broader `boundary_owner` remains partial after this block

### Why not in this block
- this block targets one concrete timeout booking specialist family with stable followup / interrupt invariants
- invalid-schema and broader booking interrupt families require separate owner ledgers

### Risk if deferred
- new timeout booking specialist behavior can continue landing in frozen `decision.py`

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-boundary-owner-next-family-selection-a922` (to be authored only if this block lands)

### Expiry/trigger to stop deferral
- stop deferral if new timeout specialist or master-info interrupt logic lands in frozen `decision.py`

## Next-block contract (mandatory)
### Next block objective
- classify and select the next real `boundary_owner` residual family after timeout booking specialist authority leaves frozen `decision.py`

### First deterministic check command
- `rg -n "policy_core_timeout_specialist_followup|policy_core_timeout_master_info_interrupt|policy_core_invalid_schema_specialist_followup|invalid_schema_specialist_followup|booking_specialist_followup" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/policy_timeout_booking_specialist_boundary_service.py`

### Blocked-by conditions
- this block does not delete/unreach the four frozen timeout specialist / interrupt response bodies
- targeted timeout specialist tests or required guards fail
- the new service becomes a mixed timeout hotspot instead of one narrow family owner

### Owner role for closure
- Brain / Top Architect
