# TP-2026-03-18-consultant-core-timeout-nonbooking-recovery-boundary-family-convergence-a922

## Goal
Delete the frozen timeout non-booking recovery reply family from `truffles-api/app/routers/webhook/decision.py` by converging the timeout style-reference need-media path, timeout pack fact fallback path, and timeout services-overview info fallback path into one narrow non-frozen boundary owner surface.

## Canon refs
- `STATE.md` NOW: consultant core timeout-degrade retry boundary family convergence
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-degrade-retry-boundary-family-convergence-a922.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after targeted timeout recovery runtime checks plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- Query: `site:refactoring.com/catalog "Extract Function" "Replace Nested Conditional with Guard Clauses"`
- Date/time: `2026-03-18 16:34:00 +05`
- Opened sources:
  - `https://refactoring.com/catalog/extractFunction.html`
  - `https://refactoring.com/catalog/replaceNestedConditionalWithGuardClauses.html`
- Source quality:
  - high-signal / primary-style source: Martin Fowler refactoring catalog pages
- Found ready-made solutions:
  - `Extract Function`: move a repeated boundary-response workflow into one named owner surface with explicit inputs
  - `Replace Nested Conditional with Guard Clauses`: keep the caller as a sequence of explicit detection guards while pushing repeated response authority out of the hotspot
- Decision: `reuse + build`
  - build one narrow `policy_timeout_recovery_boundary_service.py` owner surface for the timeout non-booking recovery family
  - reuse existing router hooks, context writers, and trace/meta writers instead of inventing new runtime infrastructure
- Rejected variants:
  - extend `policy_timeout_degrade_boundary_service.py` with this reply family immediately: rejected because that would mix retry-budget orchestration with recovery-reply ownership
  - keep the three reply bodies inline in frozen `decision.py`: rejected because live boundary authority would remain frozen
  - add a local helper in `decision.py`: rejected because it would rename the seam without deleting it

## Root cause (mandatory)
- Symptom:
  - frozen `decision.py` still owns three timeout non-booking recovery responders: style-reference need-media, pack fact fallback, and services-overview info fallback
- Minimal reproduction:
  - `rg -n "policy_core_timeout_(style_reference_need_media|fact_fallback|info_fallback)|timeout_(style_reference_need_media|fact_fallback|info_fallback)" truffles-api/app/routers/webhook/decision.py`
- Evidence:
  - `decision.py:15032-15324` implements the three responders inline
  - all three branches repeat the same ordered boundary workflow: context mutation when needed, policy guard override, trace/meta emission, send, commit, return
  - the real delta is recovery mode and payload shape, not the surrounding runtime contract
- Five Whys:
  1. Why is `decision.py` still a boundary hotspot? Because timeout recovery reply authority still lives there.
  2. Why is this a family instead of isolated branches? Because the three branches share one response-authority skeleton with bounded mode-specific deltas.
  3. Why is that a problem now? Because new timeout recovery behavior can still accrete in frozen `decision.py`.
  4. Why did the previous timeout block not remove it? Because it targeted retry-budget / clarify-limit authority, not non-booking recovery replies.
  5. Why can it move now? Because detection remains bounded in the caller while the reply-authority skeleton is already stable.
- Root cause statement:
  - The timeout non-booking recovery family is still split because its shared response-authority workflow remains embedded in frozen `decision.py` instead of one non-frozen owner surface with mode-specific deltas.
- Fix mechanism:
  - move the family into a narrow service that owns the shared response workflow and mode-specific deltas
  - delete the three frozen reply bodies from `decision.py`
  - reduce call sites to owner-surface invocation with shared hooks

## Invariant
- `decision.py` must lose live timeout recovery reply authority, not gain another local helper forest.
- `policy_timeout_degrade_boundary_service.py` must not become a timeout god-file.
- `state_service.py` must not grow.
- Existing timeout recovery trace/meta/context semantics must remain unchanged for covered scenarios.

## Scope
- Converge timeout style-reference need-media, pack fact fallback, and services-overview info fallback into one non-frozen owner surface
- Delete the three frozen reply bodies from `decision.py`
- Update only directly impacted tests/docs

## Out of scope
- Timeout booking recovery families
- Timeout retry-budget / clarify-limit family
- Handover or continuity changes
- Proof bundle / multi-pack correctness claims
- `booking.py` changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-nonbooking-recovery-boundary-family-convergence-a922.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/app/services/policy_timeout_recovery_boundary_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
1. Reuse existing context/trace/meta writers from the router via explicit hooks instead of creating new state APIs.
2. Build one narrow `policy_timeout_recovery_boundary_service.py` that owns the shared response-authority workflow for the three timeout non-booking recovery modes.
3. Keep detection in `decision.py` as explicit guards, but move the send/commit/return authority out of the frozen file.
4. Reuse existing style-reference and services-overview timeout tests; add one targeted fact-fallback test because that branch has no direct coverage yet.
5. Update repo truth only after the old frozen reply bodies are actually deleted/unreachable.

## Plan
1. Author and register this TP.
2. Implement `policy_timeout_recovery_boundary_service.py` with shared runtime input/hooks and one entrypoint for the three modes.
3. Delete the frozen reply bodies from `decision.py` and replace them with owner-surface invocation.
4. Add or update only directly impacted tests.
5. Run targeted timeout recovery runtime checks and required guards.
6. Record evidence in `STATE.md` only if an old live seam is actually deleted or unreachable.

## DoD
- `decision.py` no longer owns the live timeout style-reference need-media / fact-fallback / info-fallback reply bodies
- the timeout non-booking recovery family is owned by one non-frozen service surface
- targeted timeout recovery tests stay green
- required guards stay green
- `STATE.md` records the deleted/unreachable old seam with evidence

## Checks
- `python3 -m py_compile truffles-api/app/services/policy_timeout_recovery_boundary_service.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_timeout_style_reference_uses_need_media_prompt truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_degraded_timeout_pack_fact_fallback_uses_reply truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_degraded_timeout_services_overview_uses_info_fallback`
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
  - the three timeout non-booking recovery reply bodies are deleted from `decision.py`
  - targeted timeout recovery scenarios pass
  - required architecture/session guards pass
- Rollback:
  - revert this block's changes to `policy_timeout_recovery_boundary_service.py`, `decision.py`, affected tests/docs
  - rerun the targeted timeout recovery tests plus guard set
- Rollback verification:
  - `pytest -q truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_timeout_style_reference_uses_need_media_prompt truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_degraded_timeout_services_overview_uses_info_fallback`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`

## Evidence
- updated TP + `STRUCTURE.md`
- diff showing deletion of the three frozen reply bodies and the new owner-surface service
- green targeted timeout recovery tests + required guards
- `STATE.md` entry with the deleted/unreachable seam

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted timeout recovery/runtime checks.

## No-go
- Do not fold booking timeout recovery or retry-budget families into this block.
- Do not add another frozen wrapper family in `decision.py`.
- Do not move unrelated pack or style-reference semantics into a generic mixed helper.
- Do not claim consultant correctness/proof closure beyond this block.

## Risks / blockers
- If the new service starts owning timeout detection instead of bounded response authority, the block is drifting.
- If fact fallback needs broader pack-resolution ownership instead of bounded reply authority, stop with `GAP`.
- If this move only wraps the branches while live authority stays in `decision.py`, the block does not count as progress.

## Token / run budget (mandatory for expensive suites)
- Cheap deterministic gate first: `python3 -m py_compile`
- Targeted timeout recovery runtime tests next
- Full required guard set only after targeted runtime checks pass
- Stop condition: if two consecutive iterations fail without new structural evidence, stop and return to RCA instead of grinding tests

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- broader timeout booking recovery families remain after this non-booking recovery block
- `boundary_owner` still remains partial after this block

### Why not in this block
- this block targets one concrete timeout reply family with stable non-booking recovery invariants
- booking-followup and interrupt families require a separate owner ledger

### Risk if deferred
- new timeout recovery reply behavior can continue landing in frozen `decision.py`

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-boundary-owner-next-family-selection-a922` (to be authored only if this block lands)

### Expiry/trigger to stop deferral
- stop deferral if new timeout non-booking recovery logic lands in frozen `decision.py`

## Next-block contract (mandatory)
### Next block objective
- classify and select the next real `boundary_owner` residual family after timeout non-booking recovery authority leaves frozen `decision.py`

### First deterministic check command
- `rg -n "policy_core_timeout_(style_reference_need_media|fact_fallback|info_fallback|specialist_followup|master_info_interrupt)|timeout_(style_reference_need_media|fact_fallback|info_fallback|specialist_followup|master_info_interrupt)" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/policy_timeout_recovery_boundary_service.py`

### Blocked-by conditions
- this block does not delete/unreach the three frozen timeout recovery reply bodies
- targeted timeout recovery tests or required guards fail
- the new service becomes a mixed timeout hotspot instead of one narrow family owner

### Owner role for closure
- Brain / Top Architect
