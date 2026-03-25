# TP-2026-03-18-consultant-core-continuity-broader-collapse-targeted-frozen-waiver-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-CONTINUITY-BROADER-COLLAPSE-TARGETED-FROZEN-WAIVER-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-CONTINUITY-BROADER-COLLAPSE-TARGETED-FROZEN-WAIVER-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-continuity-broader-collapse-targeted-frozen-waiver-decision-a922.md`
- `UNLOCKS`: `author_public_entrypoint_materialization_contract_package_tp_from_master_residual_ledger`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Implement the targeted frozen-waiver runtime cut for `continuity_broader_collapse`. Delete or bypass the old continuity authority that still lives in frozen `pending.py` and non-frozen `session_memory.py` by converging reset / pending-resume / re-entry / handover-confirmation continuity ownership into `DialogStateService` plus one bounded coordinator in `state_service.py`, without moving transport routing into a new hotspot.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-continuity-broader-collapse-package-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-continuity-broader-collapse-targeted-frozen-waiver-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/core/dialog_state_service.py`

## One web search (mandatory before implementation)
- **Query (exact):** `site:martinfowler.com "Move Function" "Split Phase"`
- **Date/time (local):** `2026-03-18 14:54:47 +0500`
- **Sources opened (from this query):**
  - `https://refactoring.com/catalog/moveFunction.html`
  - `https://refactoring.com/catalog/splitPhase.html`
- **Source quality:**
  - high-signal primary refactoring guidance from Martin Fowler
- **Existing solutions found:**
  - `Move Function`: move behavior to the module that owns the data/invariants instead of leaving it beside the callsite
  - `Split Phase`: separate continuity mutation/projection from transport send/commit so the frozen wrapper can remain thin without keeping the authority
- **Decision:** `reuse/integrate`
  - reuse `DialogStateService` for canonical payload mutations
  - reuse `state_service.py` for the bounded runtime coordinator
  - keep `pending.py` and `session_memory.py` only as delegates/triggers
- **Rejected options:**
  - create a new `continuity_service.py`
  - push send/commit transport ownership into `state_service.py`
  - move only `session_memory.py` and count it as package closure
  - widen the waiver into `manager_active` or unrelated pending transport branches

## Root cause (mandatory)
- **Symptom:** continuity ownership remains split across frozen `pending.py`, `state_service.py`, and `session_memory.py`, so the old continuity family is still live.
- **Minimal reproduction:**
  1. Inspect `truffles-api/app/routers/webhook/pending.py:112` and confirm handover-confirmation cleanup / re-entry / trace/meta decisions still live there.
  2. Inspect `truffles-api/app/routers/webhook/pending.py:399` and confirm no-handover reset, pending close, pending ack restore, and pending SLA state mutation still live there.
  3. Inspect `truffles-api/app/routers/webhook/session_memory.py:72`, `truffles-api/app/routers/webhook/session_memory.py:150`, and `truffles-api/app/routers/webhook/session_memory.py:227` and confirm session-memory reset trigger / mutation / expected-reply clearing still live there.
  4. Inspect `truffles-api/app/services/state_service.py` and `truffles-api/app/core/dialog_state_service.py` and confirm the canonical continuity owner primitives already exist there.
- **Evidence:**
  - frozen callsites in `decision.py` into `_handle_pending_gate(...)` and `_handle_handover_confirmation_gate(...)`
  - residual continuity branches in `pending.py`
  - live reset / clear helpers in `session_memory.py`
  - existing restore / projection / re-entry primitives in `DialogStateService` and `state_service.py`
- **Five Whys:**
  1. Why is continuity still partial? Because old live continuity mutation remains in router helpers.
  2. Why is that a problem? Because pending reset / resume / re-entry state is decided in multiple modules.
  3. Why not leave frozen `pending.py` as the owner? Because it mixes transport entrypoint code with continuity mutation and is already on the residual ledger.
  4. Why not move everything into a new service? Because that would create another continuity hotspot instead of converging onto the existing owner surfaces.
  5. Why is `DialogStateService` plus bounded `state_service.py` the truthful destination? Because the canonical payload/projection/re-entry primitives and pending-resume coordinator family already live there.
- **Root cause statement:** the remaining continuity family is blocked by live reset / resume / confirmation authority still embedded in router helpers; the destination owner already exists, but the old family will not die until the frozen waiver scope is reduced to thin delegation and `session_memory.py` no longer mutates continuity state directly.
- **Fix mechanism:**
  - add bounded continuity coordinator surfaces in `state_service.py`
  - add canonical context mutation helpers in `DialogStateService`
  - reduce waiver-scoped `pending.py` and `session_memory.py` helpers to thin delegates/triggers only

## Invariant
- `state_service.py` must not become a transport-plus-continuity hotspot.
- `decision.py` edits, if any, must stay inside the exact waiver scope defined by the decision TP.
- `pending.py` and `session_memory.py` may survive only as thin delegates/triggers.
- No new continuity service or wrapper forest.
- No claim of full closure beyond the continuity family in scope.

## Scope
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/core/dialog_state_service.py`
- waiver-scoped continuity functions in `truffles-api/app/routers/webhook/pending.py`
- continuity helpers in `truffles-api/app/routers/webhook/session_memory.py`
- directly impacted tests and canon/session files if the old seam actually dies

## Out of scope
- `booking.py`
- broader `decision.py` semantic flows beyond the locked waiver scope
- pending transport forwarding / media forwarding
- `manager_active` path unless runtime proves inseparable
- public entrypoint materialization, debounce, proof-path, or multi-pack acceptance work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-continuity-broader-collapse-targeted-frozen-waiver-implementation-a922.md`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/routers/webhook/pending.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_pending_pack_lexicons.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_consultant_core_runtime_contracts.py` if ownership contracts change
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `STRUCTURE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Reuse-first plan (mandatory)
- Internal reuse:
  - `DialogStateService` for canonical handover-confirmation, re-entry, session-memory reset, and expected-reply clearing payload mutations
  - `state_service.py` for pending-resume restore, pending-ack restore, pending-close/no-handover reset, and pending-SLA coordination
  - existing pending-resume / continuity tests for targeted regressions where old authority moves
- External reuse:
  - Martin Fowler `Move Function`
  - Martin Fowler `Split Phase`
- Keep `pending.py` and `session_memory.py` as delegating transport/trigger wrappers only.

## Plan (1..N)
1. Add canonical continuity helpers to `DialogStateService` for session-memory reset and expected-reply clearing context updates.
2. Add bounded coordinator result/hook surfaces in `state_service.py` for handover-confirmation and pending-gate continuity decisions.
3. Reduce waiver-scoped `pending.py` functions to thin delegates that apply send/commit transport only.
4. Reduce `session_memory.py` helpers to thin delegates/triggers over the owner surfaces.
5. Add targeted tests for the new owner surfaces and the thinned wrappers.
6. Run targeted continuity tests, then the required guards and architecture/session checks.
7. Sync canon/session/state only if the old live continuity family becomes deleted or unreachable.

## DoD
- old continuity mutation authority is deleted or unreachable in waiver-scoped `pending.py`
- `session_memory.py` no longer owns live reset / expected-reply clearing mutation authority
- `DialogStateService` plus bounded `state_service.py` are the surviving owner surfaces
- no waiver scope expansion occurred
- targeted continuity tests pass
- required packet/guard/architecture/session checks pass
- canon/state/session are synced only if the block is admissible

## Checks
- `rg -n "_handle_pending_gate|_handle_handover_confirmation_gate|_should_reset_session_memory|_reset_session_memory|_clear_session_memory_expected_reply" truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/pending.py truffles-api/app/routers/webhook/session_memory.py`
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/services/state_service.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/routers/webhook/pending.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_state_service.py truffles-api/tests/test_pending_pack_lexicons.py truffles-api/tests/test_message_endpoint.py`
- `pytest -q truffles-api/tests/test_dialog_state_service.py -k 'session_memory or re_entry or handover_confirmation'`
- `pytest -q truffles-api/tests/test_state_service.py -k 'pending_resume or continuity or handover_confirmation or pending_gate'`
- `pytest -q truffles-api/tests/test_pending_pack_lexicons.py -k 'pending_ack or pending_sla_collect_only or pending_close or handover_confirmation'`
- targeted `pytest -q truffles-api/tests/test_message_endpoint.py -k 'pending_handoff_pricing_interrupt_preserves_time_followup or pending_soft_pass_timeout_booking_resume_boundary or provider_unavailable_human_request_pending_resume_restores_resolved_bot_active_boundary'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` if ownership contracts changed
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
- diff showing old continuity authority removed or reduced to delegation only
- targeted test output covering pending ack / reset / SLA / handover-confirmation and session-memory reset/clear
- green required guards and architecture/session checks
- canon/session updates naming the deleted/unreachable seam

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0` new llm-quality/full acceptance runs; this block is bounded to targeted pytest lanes plus required deterministic guards.
- **Cheap deterministic gates first:** `rg` + `py_compile`
- **Targeted suites before full required guards:** dialog-state/state-service/pending/message subsets
- **Contract lane:** `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` only if ownership surface changes materially
- **Stop condition:** stop immediately if the implementation requires widening into `manager_active`, unrelated pending transport/media branches, or `decision.py` edits outside the exact waiver scope
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only runtime convergence block; no rollout until required checks pass
- **Go/no-go signals:**
  - old continuity authority in `pending.py` and `session_memory.py` is gone or only delegating
  - targeted continuity tests pass
  - all required packet/guard/architecture/session checks pass
- **Rollback:** revert the owner-surface and wrapper changes, rerun targeted continuity tests and required guards
- **Post-release monitoring window:** first post-merge continuity block only; do not advance backlog if the deleted family reappears across multiple owners

## Rollback
1. Revert this block's code and doc changes.
2. Rerun targeted continuity tests.
3. Rerun required packet/guard/architecture/session checks.

## No-go
- no new `continuity_service.py`
- no wrapper forest counted as progress
- no transport send/commit ownership moved into `state_service.py`
- no silent waiver widening
- no claim that continuity is closed if the old router authority still decides reset / resume / confirmation behavior

## Risks / blockers
- pending transport and continuity mutation are interleaved, so the coordinator contract must stay narrow
- if `manager_active` or unrelated transport branches become necessary, the block must stop as `GAP`
- if `state_service.py` starts deciding transport reply policy instead of continuity state, the block is invalid

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:**
  - continuity routing entrypoints still survive in frozen `decision.py` and `pending.py`
  - public entrypoint materialization, debounce owner convergence, proof black-box completion, and multi-pack acceptance remain open
- **Why not in this block:**
  - this block is only for the targeted continuity family under the exact waiver scope
- **Risk if deferred:**
  - continuity mutation can drift again across router helpers and owner surfaces
- **Linked follow-up Task Package(s):**
  - `author_public_entrypoint_materialization_contract_package_tp_from_master_residual_ledger`
- **Expiry/trigger to stop deferral:**
  - stop if any new continuity mutation lands outside `DialogStateService` or the bounded coordinator before backlog advances

## Next-block contract (mandatory)
- **Next block objective:** author the next package TP for `public_entrypoint_materialization_contract` from the master residual ledger
- **First deterministic check command:** `rg -n "message.py:|decision_core.py:|provider_gateway.py:|webhook.py" -n docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md docs/SOURCE_OF_TRUTH.yaml`
- **Blocked-by conditions:**
  - this block fails to prove the old continuity family died
  - required guards or targeted continuity tests fail
  - waiver scope had to expand beyond the decision TP
- **Owner role for closure:** `Top Architect`
