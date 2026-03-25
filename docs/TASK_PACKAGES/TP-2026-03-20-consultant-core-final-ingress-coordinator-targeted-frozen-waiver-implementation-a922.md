# TP-2026-03-20-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TARGETED-FROZEN-WAIVER-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-TARGETED-FROZEN-WAIVER-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-FINAL-INGRESS-COORDINATOR-NEXT-RESIDUAL-FAMILY-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute one exact-scope targeted frozen-waiver runtime bundle on the surviving final ingress/coordinator families in frozen `decision.py`. The block is admissible only if at least one old live authority seam inside the rooted waiver scope becomes deleted or unreachable without a new wrapper/helper and without widening beyond the declared families.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/LEGACY_SUNSET.yaml`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-implementation-a922.md`
  - `docs/LEGACY_SUNSET.yaml`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
  - `truffles-api/tests/test_consultant_core_runtime_contracts.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_dialog_state_service.py`
- `Baseline commands`:
  - `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '6974,7000p'`
  - `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '1216,1320p;12478,12545p;15590,15625p;19313,19445p'`
  - `rg -n "build_collect_owner_booking_payload|build_expected_reply_context_sync_result|build_tool_reply_owner_cutover_payload|build_tool_reply_owner_decision|handle_policy_timeout_degrade_boundary" truffles-api/app/core/dialog_state_service.py truffles-api/app/core/turn_executor.py truffles-api/app/core/turn_planner.py truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- `FACT findings`:
  - live fallback still reaches frozen `decision.py` through `truffles-api/app/services/reasoning_core.py:6980` and `truffles-api/app/services/reasoning_core.py:6992`.
  - remaining live frozen families are still rooted at `truffles-api/app/routers/webhook/decision.py:1216-1320`, `truffles-api/app/routers/webhook/decision.py:12478-12545`, `truffles-api/app/routers/webhook/decision.py:15590-15625`, and `truffles-api/app/routers/webhook/decision.py:19313-19445`.
  - existing owner surfaces already cover the rooted family primitives:
    - `DialogStateService` owns canonical booking payload and expected-reply context materialization.
    - `policy_timeout_degrade_boundary_service` already owns timeout retry / pending-slot-question boundary response mechanics.
    - `TurnPlanner`, `TurnExecutor`, and `BoundaryValidator` already own typed policy / artifact / boundary contracts for the surviving tool-reply contour.
  - the first owner-complete deletable seam inside this bundle is the direct timeout/degrade degraded-collect booking-state mutation rooted at `truffles-api/app/routers/webhook/decision.py:15590-15625`; it still mutates `booking.active`, `booking.started_at`, `booking.last_question`, and then wires expected-reply state from frozen ingress.
  - broader policy-core payload extraction at `decision.py:12478-12545` is still larger and must not be reopened unless earlier rooted seams remain exact and admissible.

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Parallel Change" "Strangler Fig Application" legacy ingress coordinator`
- **Date/time (local):** `2026-03-19 17:18 +0500`
- **Sources opened (from this query):**
  - `https://martinfowler.com/bliki/ParallelChange.html`
  - `https://martinfowler.com/bliki/StranglerFigApplication.html`
- **Source quality:**
  - high-signal / primary architecture guidance from Martin Fowler / Danilo Sato
- **Reuse rule for this block:**
  - reused from the parent waiver-decision block; no second query is allowed or needed
- **Existing solutions found:**
  - route one live authority slice to the new owner first, then contract the legacy coordinator and only continue while the old slice actually dies
- **Decision:** `reuse/integrate`
  - reuse `DialogStateService`, `policy_timeout_degrade_boundary_service`, `TurnPlanner`, `TurnExecutor`, and `BoundaryValidator`
  - no new compatibility wrapper/helper
- **Rejected options:**
  - second web query
  - new ingress compatibility layer around `decision.py`
  - widening into unrelated `booking.py`, `pending.py`, or proof-path work

## Root cause (mandatory)
- **Symptom:** `semantic_owner`, `continuity_owner`, and `boundary_owner` remain partial because live final-ingress authority still sits inside frozen `decision.py`.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/services/reasoning_core.py:6980` and `:6992` and confirm live fallback still enters frozen `decision.py`.
  2. Inspect `truffles-api/app/routers/webhook/decision.py:15590-15625` and confirm degraded booking collect still mutates booking continuity from frozen ingress.
  3. Inspect `truffles-api/app/routers/webhook/decision.py:19313-19445` and confirm tool-reply boundary/result finalization still exits from frozen ingress.
  4. Inspect `truffles-api/app/routers/webhook/decision.py:1216-1320` and `:12478-12545` and confirm expected-reply/session-memory fallback plus policy route/payload extraction still live there.
  5. Inspect `truffles-api/app/core/dialog_state_service.py`, `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`, `truffles-api/app/core/turn_planner.py`, and `truffles-api/app/core/turn_executor.py` and confirm owner primitives already exist.
- **Evidence:**
  - explicit fallback into frozen `decision.py`
  - exact rooted family ranges above
  - owner primitives already present in non-frozen surfaces
- **Five Whys:**
  1. Why are owners still partial? Because live ingress still enters frozen `decision.py`.
  2. Why does that still matter after many cutovers? Because surviving rooted families still mutate continuity and boundary state there.
  3. Why can this block proceed truthfully? Because the target owner primitives already exist for the declared rooted families.
  4. Why not solve this with a wrapper/helper? Because that would move the mixed hotspot instead of deleting it.
  5. Why start with the timeout/degrade degraded-collect seam? Because it is the narrowest rooted slice where old inline mutation is still live while its owner surface already exists.
- **Root cause statement:** the surviving blocker is not lack of owner surfaces; it is remaining live authority in frozen `decision.py` over rooted continuity/boundary families that have not yet been reduced to owner invocation only.
- **Fix mechanism:**
  - switch canon to this implementation TP
  - execute the exact rooted runtime bundle in owner-complete order
  - count progress only when an old live seam in `decision.py` actually dies

## Old authority seam to delete (mandatory)
- **Primary target seam:** direct degraded-collect booking-state mutation in `truffles-api/app/routers/webhook/decision.py:15590-15625`.
- **Permitted follow-on seams in the same block only if the primary cut stays exact and admissible:**
  - fact-guard + tool-reply boundary/result family in `truffles-api/app/routers/webhook/decision.py:19313-19445`
  - expected-reply/session-memory fallback family in `truffles-api/app/routers/webhook/decision.py:1216-1320`
  - policy-core route/rescue/payload extraction family in `truffles-api/app/routers/webhook/decision.py:12478-12545`
- **Non-admissible outcomes:**
  - no old seam dies
  - a new wrapper/helper is introduced
  - authority merely moves into a new mixed hotspot

## Invariant
- no new wrapper/helper counted as progress
- no scope growth beyond `decision.py:1216-1320`, `12478-12545`, `15590-15625`, and `19313-19445`
- no reopen of `booking.py`, `pending.py`, or proof-path work
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` are fully closed from this block alone
- no claim of green `L2` or final acceptance closure

## Scope
- switch active canon to this implementation TP
- delete or bypass at least one old live authority seam inside the exact rooted waiver scope
- use only existing owner surfaces plus bounded extensions inside:
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/app/core/turn_planner.py`
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/core/boundary_validator.py`
  - `truffles-api/app/core/turn_executor.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- add focused regressions and sync canon/state/session only if the old seam really dies

## Out of scope
- `truffles-api/app/routers/webhook/booking.py`
- `truffles-api/app/routers/webhook/pending.py`
- `ops/diagnose.py`
- unrelated `decision.py` branches outside the exact rooted ranges
- acceptance or dev `L2` reruns in this block

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-20-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-implementation-a922.md`
- `docs/LEGACY_SUNSET.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/boundary_validator.py`
- `truffles-api/app/core/turn_executor.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/policy_timeout_degrade_boundary_service.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_dialog_state_service.py`

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `DialogStateService.build_collect_owner_booking_payload(...)`
  - `DialogStateService.set_context_booking_payload(...)`
  - `DialogStateService.build_expected_reply_context_sync_result(...)`
  - `handle_policy_timeout_degrade_boundary(...)`
  - `TurnPlanner.build_tool_reply_owner_decision(...)`
  - `TurnExecutor.build_tool_reply_owner_cutover_payload(...)`
  - `BoundaryValidator` / `TurnExecutor` typed boundary artifacts
- **External reuse:**
  - Martin Fowler `Parallel Change`
  - Martin Fowler `Strangler Fig Application`
- **Why not reinvent the wheel:**
  - the target owner primitives already exist; this block must only delete the live frozen authority that still bypasses them

## Plan (1..N)
1. Publish this implementation TP and switch canon/session metadata to it.
2. Update the scoped `decision.py` waiver in `docs/LEGACY_SUNSET.yaml` for the exact rooted implementation lines touched by this block.
3. Execute the primary cut: delete the direct degraded-collect booking-state mutation authority rooted at `decision.py:15590-15625` by routing it through existing owner surfaces.
4. Only if the block remains exact and owner-complete, continue to the next residual rooted family inside the same implementation TP.
5. Add focused regressions for the deleted seam.
6. Run deterministic checks and required guards.
7. Sync canon/state/session with the truthful runtime result and explicitly name the surviving residual family, if any.

## DoD
- at least one old live authority seam inside the rooted waiver scope is deleted or unreachable
- no new wrapper/helper or widened hotspot exists
- `legacy_freeze_guard.py` passes with the exact scoped waiver
- focused runtime regressions pass
- required packet/guard/architecture/session checks pass
- canon/state/session truthfully name the dead seam and the surviving residual family

## Checks
- `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '6974,7000p'`
- `nl -ba truffles-api/app/routers/webhook/decision.py | sed -n '1216,1320p;12478,12545p;15590,15625p;19313,19445p'`
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py truffles-api/app/services/reasoning_core.py truffles-api/app/core/turn_planner.py truffles-api/app/core/dialog_state_service.py truffles-api/app/core/boundary_validator.py truffles-api/app/core/turn_executor.py truffles-api/app/services/state_service.py truffles-api/app/services/policy_timeout_degrade_boundary_service.py truffles-api/tests/test_consultant_core_runtime_contracts.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/test_dialog_state_service.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'pending_soft_pass_timeout_booking_resume_boundary or tool_reply_without_evidence_clarifies or list_slots_missing_slot_pending_question_preserves_interaction_evidence'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py -k 'tool_reply or policy_timeout or owner_cutover'`
- `pytest -q truffles-api/tests/test_dialog_state_service.py -k 'booking_payload or expected_reply'`
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
- diff proving the dead frozen seam is no longer live in `decision.py`
- exact scoped waiver entry in `docs/LEGACY_SUNSET.yaml`
- focused test output for the deleted seam
- green required guards and architecture/session checks
- canon/session/state naming the surviving residual family truthfully

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Cheap deterministic gates first:** `rg` + `py_compile`
- **Focused tests before full guards:** timeout/tool-reply/dialog-state subsets only
- **Stop condition:** if the implementation needs a new wrapper/helper, broadens outside the rooted families, or fails to kill an old seam, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local exact-scope runtime convergence only; no acceptance/dev rerun in this block
- **Go/no-go signals:**
  - the targeted old seam is deleted or unreachable
  - `legacy_freeze_guard.py` passes with the exact waiver
  - focused regressions and required guards pass
- **Rollback:** revert code/doc changes for this block and rerun focused checks
- **Post-release monitoring window:** until the next rooted residual family is selected

## Rollback
1. Revert this block's code and doc changes.
2. Rerun the focused checks.
3. Rerun required packet/guard/architecture/session checks.

## No-go
- no helper wrapper counted as progress
- no widening beyond the declared rooted families
- no proof-path or acceptance detour in place of seam deletion
- no claim that the whole final ingress/coordinator story is closed after this block

## Risks / blockers
- the primary seam may prove inseparable from a larger rooted family; if so, stop and reopen scope truthfully instead of widening silently
- moving guard/send/transport concerns into a new mixed hotspot invalidates the block
- `docs/LEGACY_SUNSET.yaml` must stay exact; blanket waiver growth is invalid

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - live `/webhook` fallback still enters frozen `decision.py`
  - surviving rooted families still remain at `1216-1320`, `12478-12545`, `15590-15625`, and `19313-19445` until individually deleted
  - `semantic_owner`, `continuity_owner`, and `boundary_owner` remain partial until the remaining live ingress authority is retired
- **Why not in this block:**
  - this block is constrained to the exact rooted waiver scope and may only count progress if an old seam actually dies
- **Risk if deferred:**
  - the program drifts back into proof-path symptom work while live ingress authority remains untouched
- **Linked follow-up Task Package(s):**
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-final-ingress-coordinator-targeted-frozen-waiver-decision-a922.md`
- **Expiry/trigger to stop deferral:**
  - immediately if this implementation cannot kill an old seam without widening

## Next-block contract (mandatory)
- **Next block objective:** target the next surviving rooted family inside final ingress/coordinator closure only after the current block truthfully proves one old seam died
- **First deterministic check command:** `rg -n "decision_router\._handle_webhook_payload|_handle_webhook_payload\(|TurnOutcome\(|TurnOutcomeObservability\(" truffles-api/app/services/reasoning_core.py truffles-api/app/routers/webhook/decision.py`
- **Blocked-by conditions:** if no old seam dies, if a new wrapper/helper is required, or if the scope broadens outside the rooted families, stop and publish `GAP`
- **Owner role for closure:** `Top Architect`
