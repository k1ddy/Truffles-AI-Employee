# TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-broader-residual-family-bundle-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CONVERGENCE-BROADER-RESIDUAL-FAMILY-BUNDLE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CONVERGENCE-BROADER-RESIDUAL-FAMILY-POST-IMPLEMENTATION-AUDIT-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-broader-residual-family-post-implementation-audit-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TERMINAL-CLOSURE-ACCEPTANCE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute one terminal implementation bundle over the remaining live fallback family. This block must remove the main-path fallback from `truffles-api/app/services/reasoning_core.py` into frozen `decision.py`, converge the whole remaining residual family onto existing non-frozen owner surfaces, and forbid any further seam farming as the primary strategy.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-broader-residual-family-post-implementation-audit-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:** high-signal primary architecture guidance from Martin Fowler / Danilo Sato.
- **Reuse rule for this block:** reused from the active terminal convergence chain; no second query is allowed or needed.
- **Existing solutions found:** stop bounded seam farming once the residual family is fully rooted; then do one package-level owner replacement bundle that removes the live ingress fallback instead of adding another bypass.
- **Decision:** `reuse/integrate`
  - reuse the already-landed owner services and typed `turn_planner` / `turn_executor` surfaces
  - do not add a second query or a new transport helper/wrapper
- **Rejected options:**
  - second web query
  - another bounded seam-only bundle
  - new wrapper/helper around legacy ingress
  - widening into frozen `booking.py` or `pending.py`

## Root cause (mandatory)
- **Symptom:** after the last `_try_handle_turn_planner_safe_*` owner cutover returns `None`, active ingress still falls through to `decision_router._handle_webhook_payload(...)`, so frozen `decision.py` remains the live semantic / continuity / boundary authority on the main runtime path.
- **Minimal reproduction:**
  1. `rg -n "decision_router\._handle_webhook_payload|timeout_specialist_followup|PolicyTimeoutBookingSpecialistBoundaryRuntimeInput|_build_policy_core_rescue_timing_context|llm_policy_core" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_reasoning_core.py`
  2. `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '12888,13051p'`
  3. `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '12462,12545p;14120,14480p;14866,15040p;15106,15349p;15432,15756p;19373,19481p'`
  4. `nl -ba truffles-api/app/core/turn_planner.py | sed -n '94,225p'`
  5. `nl -ba truffles-api/app/core/turn_executor.py | sed -n '499,700p'`
- **Evidence:** repo truth shows the live fallback at `truffles-api/app/services/reasoning_core.py:13039-13051`, the surviving residual family at `truffles-api/app/routers/webhook/decision.py:12462-12545`, `:14120-14480`, `:14866-15040`, `:15106-15349`, `:15432-15756`, and `:19373-19481`, partial owner coverage in existing non-frozen boundary services, and incomplete non-frozen end-to-end ownership for the legacy semantic rescue path plus terminal tool-reply / reschedule orchestration.
- **Five Whys:**
  1. Why does live fallback still exist? Because `reasoning_core` has no complete non-frozen terminal path after `_try_handle_turn_planner_safe_semantic_arbitration_owner_cutover(...)` at `truffles-api/app/services/reasoning_core.py:13026-13037`.
  2. Why is that a problem? Because unresolved turns still execute inside frozen `decision.py`, which keeps mixed semantic, continuity, and boundary authority live.
  3. Why not delete the fallback call immediately? Because the remaining family still requires complete non-frozen semantic planning and terminal owner execution for those turns.
  4. Why not keep killing one seam at a time? Because that preserves the same mixed fallback architecture and normalizes `partial` as steady state.
  5. Why is one terminal bundle admissible now? Because the audit proved the entire residual family is rooted behind a single live fallback seam and the required owner destinations already exist in non-frozen surfaces.
- **Root cause statement:** the main ingress still lacks one complete non-frozen owner path for the whole residual family: `truffles-api/app/core/turn_planner.py` does not yet absorb the remaining legacy semantic rescue / plan path at `decision.py:12462-12545`, and `truffles-api/app/core/turn_executor.py` plus `truffles-api/app/services/reasoning_core.py` do not yet own the remaining terminal tool-reply / reschedule orchestration at `decision.py:19373-19481`, so `reasoning_core.py:13039-13051` remains live.
- **Fix mechanism:** extend `turn_planner`, `turn_executor`, and `reasoning_core` over the remaining residual family using the existing non-frozen boundary services; then remove the fallback invocation at `truffles-api/app/services/reasoning_core.py:13039-13051` and prove closure with focused runtime regressions plus mandatory governance checks.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing owner-cutover chain in `truffles-api/app/services/reasoning_core.py`
  - existing typed `PolicyDecision` / `TurnPlanner` surfaces in `truffles-api/app/core/turn_planner.py`
  - existing typed tool-reply owner execution in `truffles-api/app/core/turn_executor.py`
  - existing `_finalize_tool_reply_owner_execution(...)` in `truffles-api/app/services/reasoning_core.py`
  - existing `handle_policy_validation_boundary(...)` in `truffles-api/app/services/policy_validation_boundary_service.py`
  - existing `handle_policy_timeout_recovery_boundary(...)` in `truffles-api/app/services/policy_timeout_recovery_boundary_service.py`
  - existing `handle_policy_timeout_degrade_boundary(...)` in `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
  - existing `handle_policy_timeout_booking_specialist_boundary(...)` in `truffles-api/app/services/policy_timeout_booking_specialist_boundary_service.py`
  - existing `handle_policy_timeout_booking_time_followup_boundary(...)` in `truffles-api/app/services/policy_timeout_booking_time_followup_boundary_service.py`
  - existing `handle_policy_core_guard_orchestration(...)` in `truffles-api/app/services/policy_core_guard_orchestration_service.py`
  - existing `resolve_and_apply_timeout_owner_boundary(...)` in `truffles-api/app/services/timeout_owner_boundary_service.py`
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:** the necessary owner surfaces already exist; the gap is owner completeness and main-path routing, not missing primitives.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Runtime scope:** one terminal closure bundle over the whole remaining rooted residual family behind `reasoning_core.py:13039-13051`
- **Doc touch budget (files):** `30`
- **Why this profile fits:** the truthful next move is the final owner replacement bundle, not another bounded seam deletion or another audit loop.

## Invariant
- no edits to frozen `truffles-api/app/routers/webhook/decision.py`
- no edits to frozen `truffles-api/app/routers/webhook/booking.py`
- no edits to frozen `truffles-api/app/routers/webhook/pending.py`
- no new helper/wrapper around legacy ingress
- no second web query
- no claim of final acceptance without the required runtime / quality evidence
- no counting bounded seam farming as progress after this block is active

## Scope
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- block/canon sync docs for this implementation block

## Out of scope
- frozen `decision.py`, `booking.py`, or `pending.py` edits
- new helper/wrapper creation
- doc-only audit loops as substitute for runtime closure
- `L2` / open-world acceptance claims without the required evidence actually run

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-broader-residual-family-bundle-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-terminal-convergence-broader-residual-family-post-implementation-audit-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSION_INDEX.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Extend `turn_planner.py` to cover the remaining legacy semantic rescue / plan path that still survives behind `decision.py:12462-12545`.
2. Extend `turn_executor.py` plus `reasoning_core.py` so the remaining terminal tool-reply / reschedule orchestration no longer depends on `decision.py:19373-19481`.
3. Route the residual boundary families in `reasoning_core.py` through the already-landed non-frozen owner services and delete the fallback invocation at `truffles-api/app/services/reasoning_core.py:13039-13051`.
4. Add focused regressions proving the remaining family no longer reaches `decision_router._handle_webhook_payload(...)` and preserves decision trace / decision meta / continuity evidence.
5. Sync canon and rerun mandatory checks.

## DoD
- no reachable runtime fallback from `truffles-api/app/services/reasoning_core.py` into frozen `decision.py`
- `truffles-api/app/routers/webhook/decision.py` no longer acts as live semantic / continuity / boundary authority on the main runtime path
- `semantic_owner`, `continuity_owner`, and `boundary_owner` are no longer partial for the main path covered by this program
- focused runtime regressions plus mandatory guards are green
- if this block is used to claim program-final closure, the required runtime / quality evidence is prepared and attached; otherwise final acceptance stays explicitly open

## Checks
- `rg -n "decision_router\._handle_webhook_payload|timeout_specialist_followup|PolicyTimeoutBookingSpecialistBoundaryRuntimeInput|_build_policy_core_rescue_timing_context|llm_policy_core" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py truffles-api/tests/test_reasoning_core.py`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '12888,13051p'`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '12462,12545p;14120,14480p;14866,15040p;15106,15349p;15432,15756p;19373,19481p'`
- `nl -ba truffles-api/app/core/turn_planner.py | sed -n '94,225p'`
- `nl -ba truffles-api/app/core/turn_executor.py | sed -n '499,700p'`
- `python3 -m py_compile truffles-api/app/core/turn_planner.py truffles-api/app/core/turn_executor.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'semantic_service_query_fact_rescue or timeout_services_overview_fallback or timeout_specialist_followup_owner or timeout_active_name_time_collect_owner or timeout_pending_slot_question or reschedule_guard_handoff'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k 'tool_reply_owner_decision or tool_reply_owner_state or tool_reply_owner_cutover_payload or explicit_handoff_owner_cutover_artifact'`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'collect_service_info_interrupt_routes_to_catalog_service_query or list_slots_missing_slot_pending_question_preserves_interaction_evidence or tool_reply_without_evidence_clarifies'`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- runtime diff in `truffles-api/app/core/turn_planner.py`
- runtime diff in `truffles-api/app/core/turn_executor.py`
- runtime diff in `truffles-api/app/services/reasoning_core.py`
- focused regressions proving the main path no longer reaches `decision_router._handle_webhook_payload(...)`
- green governance/session checks after the cut

## Rollback
1. Revert `truffles-api/app/core/turn_planner.py`, `truffles-api/app/core/turn_executor.py`, `truffles-api/app/services/reasoning_core.py`, and test changes from this block.
2. Revert the canon sync docs.
3. Regenerate the packet and rerun checks.

## Release safety (mandatory for non-doc changes)
- **Strategy:** one terminal non-frozen runtime bundle; no rollout beyond local validation in this block.
- **Go/no-go signals:** fallback at `truffles-api/app/services/reasoning_core.py:13039-13051` is gone or provably unreachable, focused regressions preserve continuity / trace evidence, mandatory guards are green, and no frozen files changed.
- **Rollback:** revert `turn_planner.py`, `turn_executor.py`, `reasoning_core.py`, related tests, and canon sync docs; regenerate packet; rerun checks.
- **Post-release monitoring window:** if this block lands, the only truthful next move is required closure evidence / acceptance, not another bounded seam bundle.

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** deterministic fallback scans, focused runtime regressions, focused runtime contracts, focused `test_message_endpoint.py`, then mandatory governance/session checks.
- **Stop condition:** if terminal closure still requires a new wrapper/helper, frozen widening, or another bounded seam bundle, stop and publish the blocker instead of claiming progress.
- **Escalation path:** `Top Architect`

## No-go
- counting another bounded seam-only cut as valid progress
- new helper/wrapper growth around `decision.py`
- widening into frozen `booking.py` / `pending.py`
- any new audit-only loop used to avoid the runtime closure
- claiming completion while `reasoning_core.py:13039-13051` still routes into `decision_router._handle_webhook_payload(...)`

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- no live `reasoning_core -> decision_router._handle_webhook_payload(...)` fallback remains on the main runtime path after this block
- final program acceptance evidence / quality path remains outside this runtime block
- frozen `decision.py` remains as a legacy example and direct legacy test surface, not as main-path authority

### Why not in this block
- this block is the runtime closure itself; the remaining work is acceptance evidence and canon proof, not another runtime seam cut

### Risk if deferred
- final acceptance cannot be claimed truthfully
- future regressions could silently reopen the deleted fallback unless closure evidence keeps asserting unreachability

### Linked follow-up Task Package(s)
- required closure evidence / acceptance package after fallback removal

### Expiry/trigger to stop deferral
- stop deferral immediately if anyone reopens `reasoning_core -> decision_router._handle_webhook_payload(...)`, reintroduces frozen main-path authority, or claims final acceptance without the required evidence.

## Next-block contract (mandatory)
### Next block objective
- prepare the required closure evidence / acceptance path for `beauty`, `clinic_or_dental`, and `generic_service` without reopening runtime closure work.

### First deterministic check command
- `rg -n "decision_router\._handle_webhook_payload|terminal_owner_unresolved" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/public_entrypoint_contract.py truffles-api/app/routers/webhook/outbox.py truffles-api/app/services/console_consultant_verification.py`

### Blocked-by conditions
- invalid multi-pack acceptance preflight
- missing valid judge / API key for the required quality lane
- inability to preserve the deleted fallback proof while preparing acceptance evidence

### Owner role for closure
- `Top Architect`
