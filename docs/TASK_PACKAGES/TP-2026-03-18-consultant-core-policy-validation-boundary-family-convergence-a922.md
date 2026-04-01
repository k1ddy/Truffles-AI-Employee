# TP-2026-03-18-consultant-core-policy-validation-boundary-family-convergence-a922

## Goal
Delete the frozen policy-validation reply family from `truffles-api/app/routers/webhook/decision.py` by converging the `clarify`, `booking_prompt`, and `pending_question_guidance` contract-validation degrade paths into one narrow non-frozen boundary owner surface.

## Canon refs
- `STATE.md` NOW: timeout owner-boundary application family convergence
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-timeout-owner-boundary-application-family-convergence-a922.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after targeted policy-validation runtime checks plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- Query: `site:refactoring.com/catalog "Move Function" "Form Template Method"`
- Date/time: `2026-03-18 15:03:00 +05`
- Opened sources:
  - `https://refactoring.com/catalog/moveFunction.html`
  - `https://refactoring.com/catalog/formTemplateMethod.html`
- Source quality:
  - high-signal / primary-style source: Martin Fowler refactoring catalog pages
- Found ready-made solutions:
  - `Move Function`: move behavior to the module that owns the invariant and repeated coordination flow
  - `Form Template Method`: consolidate methods that perform the same ordered steps with mode-specific differences
- Decision: `reuse + build`
  - build one narrow `policy_validation_boundary_service.py` owner surface
  - keep the repeated policy-validation reply family out of frozen `decision.py`
  - reuse existing router hooks and messages instead of introducing another generic runtime layer
- Rejected variants:
  - leave the three nested functions in `decision.py`: rejected because the live boundary family would remain frozen
  - fold this family into `boundary_validator.py` or `turn_executor.py` immediately: rejected because this block is still legacy-runtime response orchestration, not typed `TurnResult` assembly
  - add a local helper wrapper in `decision.py`: rejected because it would rename the seam without deleting the old authority

## Root cause (mandatory)
- Symptom:
  - frozen `decision.py` still owns three live contract-validation degrade responders: `_send_policy_validation_clarify(...)`, `_send_policy_validation_collect_prompt(...)`, `_send_policy_validation_pending_question_guidance(...)`
- Minimal reproduction:
  - `rg -n "def _send_policy_validation_(clarify|collect_prompt|pending_question_guidance)|_apply_policy_guard_override\(|policy_core_degrade_reason = f\"policy_validation:" truffles-api/app/routers/webhook/decision.py`
- Evidence:
  - `decision.py:12202`, `decision.py:12284`, `decision.py:12387` implement the family inline
  - all three functions repeat the same ordered steps: mark degraded policy state, mutate `llm_policy_core_meta`, update decision metadata, apply guard override, emit trace/meta, send reply, commit, return `WebhookResponse`
  - the only real delta is response mode: clarify vs booking prompt vs pending-question guidance
- Five Whys:
  1. Why is `decision.py` still a boundary hotspot? Because contract-validation degrade response authority still lives there.
  2. Why is that a family rather than isolated helpers? Because three responders share the same ordered boundary workflow with mode-specific deltas.
  3. Why is that a problem now? Because new policy-validation behavior can still accrete in the frozen router instead of a bounded owner surface.
  4. Why has it survived previous blocks? Because earlier boundary work targeted timeout-owner paths, not contract-validation degrade responders.
  5. Why can it be moved now? Because the family already has a stable shared skeleton and bounded call sites.
- Root cause statement:
  - The policy-validation boundary family is still split because its common degrade workflow remains embedded as three frozen nested responders instead of one non-frozen owner surface with mode-specific branches.
- Fix mechanism:
  - move the family into a narrow service that owns the shared degrade workflow and mode-specific deltas
  - delete the three frozen responder bodies from `decision.py`
  - reduce call sites to owner-surface invocation with shared hooks

## Invariant
- `decision.py` must lose live policy-validation boundary authority, not gain another local helper forest.
- No semantic post-hoc rewrite may be introduced.
- `state_service.py` must not become a landing zone for this family.
- Runtime trace/meta/question-contract behavior must remain unchanged for covered scenarios.

## Scope
- Converge the policy-validation response family into one non-frozen owner surface
- Delete the three frozen responder bodies from `decision.py`
- Update only directly impacted tests/docs

## Out of scope
- Broader boundary-owner closure beyond this contract-validation family
- Timeout boundary family changes
- Handover family changes
- Proof bundle / multi-pack correctness claims
- `booking.py` changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-policy-validation-boundary-family-convergence-a922.md`
- `STRUCTURE.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_message_endpoint.py`
- any directly impacted targeted tests only if required

## Reuse-first plan (mandatory)
1. Reuse the existing runtime hooks already exercised by `decision.py` instead of inventing new state/write APIs.
2. Build one narrow `policy_validation_boundary_service.py` that owns the shared degrade workflow and mode-specific deltas.
3. Reuse direct call sites in `decision.py` with shared hooks binding; do not keep frozen responder bodies.
4. Reuse existing message-endpoint tests that already cover clarify, collect-prompt, and pending-question-guidance branches.
5. Update `docs/ACTIVE_PROGRAM.md` after the block so repo truth stops pointing at stale Block Z.

## Plan
1. Author and register this TP.
2. Implement `policy_validation_boundary_service.py` with shared runtime input/hooks and a single entrypoint for the three modes.
3. Delete the three responder bodies from frozen `decision.py` and replace call sites with owner-surface invocation.
4. Update targeted tests only if import/patch points require it.
5. Run targeted policy-validation runtime checks and required guards.
6. Record evidence in `STATE.md` only if an old live seam is actually deleted or unreachable.

## DoD
- `decision.py` no longer defines `_send_policy_validation_clarify(...)`, `_send_policy_validation_collect_prompt(...)`, or `_send_policy_validation_pending_question_guidance(...)`
- the policy-validation degrade reply family is owned by one non-frozen service surface
- targeted clarify / collect-prompt / pending-question-guidance tests stay green
- required guards stay green
- `STATE.md` records the deleted/unreachable old seam with evidence

## Checks
- `python3 -m py_compile truffles-api/app/services/policy_validation_boundary_service.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_rejects_invalid_action_without_normalization truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_collect_slot_order_invalid_degrades_to_datetime_prompt truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_collect_slot_order_invalid_time_window_uses_slot_constraint_guidance truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_semantic_temporal_scope_missing_preserves_pending_slot_guidance truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_service_query_non_service_refs_routes_to_info truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_info_without_pack_refs_clarifies_instead_of_deriving_from_text truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_handoff_policy_blocked_uses_safe_reply`
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
  - frozen responder bodies are deleted from `decision.py`
  - targeted policy-validation scenarios pass
  - required architecture/session guards pass
- Rollback:
  - revert this block's changes to `policy_validation_boundary_service.py`, `decision.py`, affected tests/docs
  - rerun the targeted policy-validation tests plus guard set
- Rollback verification:
  - `pytest -q truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_rejects_invalid_action_without_normalization truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_collect_slot_order_invalid_degrades_to_datetime_prompt truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_collect_slot_order_invalid_time_window_uses_slot_constraint_guidance truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_semantic_temporal_scope_missing_preserves_pending_slot_guidance`
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`

## Evidence
- updated TP + `STRUCTURE.md`
- diff showing deletion of the three frozen responder bodies and the new owner-surface service
- green targeted policy-validation tests + required guards
- `STATE.md` entry with the deleted/unreachable seam

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted policy-validation/runtime checks.

## No-go
- Do not add another frozen wrapper family in `decision.py`.
- Do not move unrelated timeout, booking, or handover flows into the new service.
- Do not use regex/phrase hardcode as a shortcut for policy-validation handling.
- Do not claim consultant correctness/proof closure beyond this block.

## Risks / blockers
- The service needs many runtime hooks; if that becomes a generic god-surface rather than one narrow family, stop with `GAP`.
- The pending-question-guidance branch must preserve `booking_slot_guidance` trace/meta semantics exactly.
- If this move only renames the family while keeping the live authority in `decision.py`, the block does not count as progress.

## Token / run budget (mandatory for expensive suites)
- Cheap deterministic gate first: `python3 -m py_compile`
- Targeted policy-validation runtime tests next
- Full required guard set only after targeted runtime checks pass
- Stop condition: if two consecutive iterations fail without new structural evidence, stop and return to RCA instead of grinding tests

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- broader `boundary_owner` closure is still incomplete after this family
- `docs/SOURCE_OF_TRUTH.yaml` may still legitimately keep `decision.py` in `boundary_owner.current_primary_files` until more boundary families die

### Why not in this block
- this block targets one concrete family with repeated frozen authority
- broader boundary closure needs a separate family ledger instead of scope creep here

### Risk if deferred
- new contract-validation degrade behavior could continue landing in frozen `decision.py`

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-boundary-owner-next-family-selection-a922` (to be authored only if this block lands)

### Expiry/trigger to stop deferral
- stop deferral if new policy-validation reply logic lands in frozen `decision.py`

## Next-block contract (mandatory)
### Next block objective
- classify and select the next real `boundary_owner` residual family after policy-validation reply authority leaves frozen `decision.py`

### First deterministic check command
- `rg -n "def _send_policy_validation_|timeout_owner_boundary|booking_slot_guidance|contract_validation_failure|apply_policy_guard_override\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/policy_validation_boundary_service.py truffles-api/app/services/timeout_owner_boundary_service.py`

### Blocked-by conditions
- this block does not delete/unreach the three frozen responder bodies
- targeted policy-validation tests or required guards fail
- the new service becomes a generic mixed hotspot instead of one narrow family owner

### Owner role for closure
- Brain / Top Architect
