# TP-2026-03-18-consultant-core-continuity-broader-collapse-package-a922

## Goal
Delete or bypass the remaining broader continuity family that is still split across frozen `truffles-api/app/routers/webhook/pending.py`, `truffles-api/app/services/state_service.py`, and `truffles-api/app/routers/webhook/session_memory.py` by converging snapshot / restore / reset / re-entry / pending-boundary continuity ownership into `truffles-api/app/core/dialog_state_service.py` plus one bounded coordinator surface, without turning `state_service.py` into a new god-file.

## Canon refs
- `STATE.md` NOW: consultant core `semantic_arbitration_residual` runtime family convergence
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-master-residual-ledger-stop-line-audit-a922.md`
- `docs/_generated/AGENT_PACKET.md`

## Branch / worktree
- Branch: `feat/2026-03-15-consultant-core-governance-lock-a922`
- Worktree: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- Base ref: `main`
- Merge policy: merge only after the targeted continuity runtime lane plus required guards are green
- Cleanup: Brain / Top Architect after merge

## One web search (mandatory before implementation)
- **Query (exact):** `site:refactoring.com/catalog "Move Function" "Extract Class" "Split Phase"`
- **Date/time (local):** `2026-03-18 14:32:48 +0500`
- **Sources opened (from this query):**
  - `https://refactoring.com/catalog/moveFunction.html`
  - `https://refactoring.com/catalog/extractClass.html`
  - `https://refactoring.com/catalog/splitPhase.html`
- **Source quality:**
  - high-signal / primary-style source: Martin Fowler refactoring catalog pages
- **Found ready-made solutions:**
  - `Move Function`: continuity mutation should live with the module that owns continuity invariants instead of being spread across router helpers and transport gates
  - `Extract Class`: if a host starts mixing transport policy, continuity mutation, and replay wiring, isolate one bounded coordinator instead of letting the host become the new hotspot
  - `Split Phase`: separate pending transport gating from continuity state mutation / restore / reset / re-entry projection so the runtime stops re-deriving the same continuity state in multiple places
- **Decision:** `reuse + integrate`
  - reuse `truffles-api/app/core/dialog_state_service.py` as the canonical owner for pending-resume snapshot / restore payloads, expected-reply/session-memory normalization, re-entry payloads, handover confirmation payloads, and canonical state projections
  - reuse the existing `truffles-api/app/services/state_service.py` family as the only candidate bounded coordinator for pending-resume boundary activation, reset-with-trace preservation, and pending continuity wiring
  - keep `truffles-api/app/routers/webhook/pending.py` and `truffles-api/app/routers/webhook/session_memory.py` as transport-facing thin delegates only if the old live continuity authority actually dies
- **Rejected options:**
  - new `truffles-api/app/services/continuity_service.py`: rejected because it would become a second continuity hotspot beside `DialogStateService` and `state_service.py`
  - pushing continuity ownership into `pending.py` or `session_memory.py`: rejected because that preserves split authority and keeps frozen/live router helpers as owners
  - growing `state_service.py` into a transport-plus-continuity god-file: rejected because the package must converge ownership, not move the mixed hotspot
  - pushing continuity semantics into public entrypoints or boundary/materialization owners: rejected because continuity ownership is distinct from ingress compatibility and boundary validation
  - audit-only churn without runtime cutover: rejected because the old live continuity seams would remain authoritative

## Root cause (mandatory)
- **Symptom:**
  - pending resume / reset / re-entry / session-memory continuity remains split across three owner surfaces
  - frozen `pending.py` still performs live pending ack / no-handover reset / close / SLA / confirmation continuity state transitions
  - `session_memory.py` still performs live reset and expected-reply clearing mutations
  - `state_service.py` already owns part of the same resume / restore / boundary family, so continuity is materially fragmented instead of converged
- **Minimal reproduction:**
  - `rg -n "_handle_handover_confirmation_gate|_get_pending_resume|_set_pending_resume|_reset_context_preserving_trace|_capture_pending_resume_context|_restore_pending_resume_context|_build_pending_resume_snapshot_payload|_prepare_pending_handoff_resume_boundary_restore|_resolve_resolved_handoff_resume_boundary_restore|_resolve_pending_resume_boundary_activation|_resolve_pending_resume_session_memory_policy|_should_reset_session_memory|_reset_session_memory|_clear_session_memory_expected_reply" truffles-api/app/routers/webhook/pending.py truffles-api/app/services/state_service.py truffles-api/app/routers/webhook/session_memory.py`
  - `rg -n "project_expected_reply_projections|clear_session_memory_expected_reply|touch_session_memory_payload|sync_context_manager_expected_reply_state|build_expected_reply_context_sync_result|capture_pending_resume_payload|restore_pending_resume_payload|derive_pending_resume_reason|derive_pending_booking_resume_boundary_payload|clear_context_manager_carryover_family|set_context_handover_confirmation|set_context_re_entry_required|clear_context_re_entry_required" truffles-api/app/core/dialog_state_service.py`
- **Evidence:**
  - frozen `truffles-api/app/routers/webhook/pending.py:112` still owns handover-confirmation continuity cleanup and trace/meta decisions around confirmation state reuse / clear / commit
  - frozen `truffles-api/app/routers/webhook/pending.py:421`, `truffles-api/app/routers/webhook/pending.py:482`, and `truffles-api/app/routers/webhook/pending.py:510` still own no-handover reset, pending close, and pending ack restore / trace / reply continuity decisions
  - frozen `truffles-api/app/routers/webhook/pending.py:678` still owns pending SLA continuity state updates and trace/meta writes
  - `truffles-api/app/services/state_service.py:299`, `truffles-api/app/services/state_service.py:454`, `truffles-api/app/services/state_service.py:472`, `truffles-api/app/services/state_service.py:553`, `truffles-api/app/services/state_service.py:638`, `truffles-api/app/services/state_service.py:697`, and `truffles-api/app/services/state_service.py:792` already own overlapping reset / snapshot / restore / boundary / session-memory policy continuity responsibilities
  - `truffles-api/app/routers/webhook/session_memory.py:72`, `truffles-api/app/routers/webhook/session_memory.py:150`, and `truffles-api/app/routers/webhook/session_memory.py:227` still own live session-memory reset trigger / mutation / expected-reply clearing continuity behavior
  - `truffles-api/app/core/dialog_state_service.py:385`, `truffles-api/app/core/dialog_state_service.py:495`, `truffles-api/app/core/dialog_state_service.py:573`, `truffles-api/app/core/dialog_state_service.py:708`, `truffles-api/app/core/dialog_state_service.py:847`, `truffles-api/app/core/dialog_state_service.py:1103`, `truffles-api/app/core/dialog_state_service.py:1157`, `truffles-api/app/core/dialog_state_service.py:1223`, `truffles-api/app/core/dialog_state_service.py:1298`, `truffles-api/app/core/dialog_state_service.py:1755`, and `truffles-api/app/core/dialog_state_service.py:2623` already expose the canonical payload/projection primitives that make a second continuity owner unnecessary
  - repo truth in `docs/REPORTS/artifacts/2026-03-18-consultant-core-master-residual-ledger-a922.md` already marks the preferred destination as `DialogStateService` plus one bounded coordinator
- **Five Whys:**
  1. Why is continuity collapse still partial? Because snapshot / restore / reset / re-entry / session-memory continuity mutation is still shared by `pending.py`, `state_service.py`, and `session_memory.py`.
  2. Why is the family still shared? Because earlier bounded cuts moved primitives into `DialogStateService` and some coordinator logic into `state_service.py`, but the broader pending gates and reset/session-memory mutations were left live.
  3. Why can't `pending.py` remain the owner? Because it is frozen and mixes transport gating with continuity mutation, trace/meta, and reply commitments.
  4. Why can't `session_memory.py` remain the owner? Because reset / expected-reply clearing are continuity mutations, not standalone lexical ownership, and they already overlap with `DialogStateService` semantics.
  5. Why is `DialogStateService` plus one bounded coordinator the truthful destination? Because `DialogStateService` already owns the canonical projection, snapshot, restore, and re-entry payload primitives, while `state_service.py` already hosts the residual pending-resume boundary coordinator family; converging there reuses existing continuity owners instead of creating another hotspot.
- **Root cause statement:**
  - continuity ownership is still fragmented because the runtime moved some continuity primitives into `DialogStateService` and some coordinator behavior into `state_service.py`, but left live pending ack / reset / close / SLA / confirmation mutations in frozen `pending.py` and live reset / expected-reply clearing mutations in `session_memory.py`, so the same continuity family is still decided in multiple modules.
- **Fix mechanism:**
  - converge continuity mutation and payload semantics onto `DialogStateService`
  - keep only one bounded non-frozen coordinator for pending-resume boundary, reset-with-trace preservation, and pending continuity wiring
  - reduce `pending.py` and `session_memory.py` to thin transport/trigger delegates only if the old live continuity authority becomes deleted or unreachable
  - if the remaining frozen `pending.py` branches cannot be made unreachable without creating a new mixed hotspot, stop and publish `GAP`

## Invariant
- Continuity ownership must shrink to one family, not just change file names.
- `DialogStateService` remains the canonical payload/projection owner.
- `state_service.py` must not grow into the new mixed transport-plus-continuity hotspot.
- Frozen `truffles-api/app/routers/webhook/pending.py` must not be edited for this package; admissible progress must come from truthful bypass or non-frozen coordinator convergence.
- If the truthful destination requires a new continuity god-file or leaves live continuity mutation split across `pending.py`, `state_service.py`, and `session_memory.py`, stop and publish `GAP`.

## Scope
- Introduce one package-level implementation plan for the remaining `continuity_broader_collapse` family
- Converge pending-resume snapshot / restore / boundary activation / session-memory policy / reset-with-trace preservation into `DialogStateService` plus one bounded coordinator
- Delete or bypass live continuity mutation authority from frozen `pending.py` and `session_memory.py`
- Update only directly impacted continuity tests/docs/contracts for this family

## Out of scope
- `public_entrypoint_materialization_contract`
- `debounce_buffer_owner_convergence`
- `proof_black_box_completion`
- `multi_pack_acceptance`
- semantic owner cutover beyond already-landed `semantic_arbitration_residual`
- public ingress compatibility cleanup beyond continuity family needs
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/booking.py`

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-continuity-broader-collapse-package-a922.md`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_pending_pack_lexicons.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- any directly impacted continuity docs/tests only if required

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `truffles-api/app/core/dialog_state_service.py`
  - `truffles-api/app/services/state_service.py`
  - existing pending-resume helpers already delegating to `DialogStateService`
  - existing session-memory payload helpers already delegating to `DialogStateService`
  - existing pending / message endpoint regressions that already prove resume-boundary behavior
- **External reuse:**
  - Martin Fowler refactoring guidance for `Move Function`, `Extract Class`, and `Split Phase`, limited to the single mandatory query above
- **Why this reuse mix is truthful:**
  - the canonical continuity primitives already exist in `DialogStateService`
  - the residual bounded coordinator family already exists in `state_service.py`
  - reusing those owners deletes split authority instead of inventing another continuity layer
  - `pending.py` and `session_memory.py` can only count as survivors if they become thin delegates rather than continuity owners

## Plan
1. Publish and register this package-level TP, then switch canon to it.
2. Map the residual continuity family into exact `DialogStateService` payload/projection responsibilities versus bounded coordinator responsibilities.
3. Prove whether the existing `state_service.py` family can remain a bounded coordinator without becoming a new mixed hotspot; if not, stop and publish `GAP` instead of inventing wrapper churn.
4. Implement the runtime convergence so pending-resume restore / boundary activation / reset / re-entry / session-memory clearing no longer remain live continuity authority in frozen `pending.py` or `session_memory.py`.
5. Add or tighten targeted continuity regression coverage around pending resume, reset, session-memory clearing, and pending boundary traces/meta.
6. Run the targeted continuity runtime lane plus required guards and any contract lane required by ownership-surface changes.
7. Record evidence in `STATE.md` only if the old live continuity seam is actually deleted or unreachable.

## DoD
- pending-resume snapshot / restore / boundary activation / session-memory policy continuity no longer remains split across `pending.py`, `state_service.py`, and `session_memory.py`
- frozen `pending.py` no longer owns live pending ack restore or no-handover reset continuity authority for this family
- `session_memory.py` no longer owns live reset / expected-reply clearing continuity authority for this family
- the truthful destination is `DialogStateService` plus one bounded coordinator, not a new continuity service or a larger `state_service.py` hotspot
- targeted continuity runtime tests pass
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` passes if ownership boundary contracts change
- required architecture/session guards pass
- `STATE.md` records the deleted/unreachable old continuity seam with evidence

## Checks
- `rg -n "_handle_handover_confirmation_gate|_get_pending_resume|_set_pending_resume|_reset_context_preserving_trace|_capture_pending_resume_context|_restore_pending_resume_context|_build_pending_resume_snapshot_payload|_prepare_pending_handoff_resume_boundary_restore|_resolve_resolved_handoff_resume_boundary_restore|_resolve_pending_resume_boundary_activation|_resolve_pending_resume_session_memory_policy|_should_reset_session_memory|_reset_session_memory|_clear_session_memory_expected_reply" truffles-api/app/routers/webhook/pending.py truffles-api/app/services/state_service.py truffles-api/app/routers/webhook/session_memory.py`
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/services/state_service.py truffles-api/app/routers/webhook/session_memory.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_state_service.py truffles-api/tests/test_pending_pack_lexicons.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/test_dialog_state_service.py -k 'captures_pending_resume_payload or restores_pending_resume_payload or derives_pending_resume_boundary_payload or build_expected_reply_context_sync_result or reset_session_memory or sync_session_memory_interaction_state'`
- `pytest -q truffles-api/tests/test_state_service.py -k 'capture_pending_resume_context or restore_pending_resume_context or build_pending_resume_snapshot_payload or restore_pending_resume_payload or prepare_pending_handoff_resume_boundary_restore or resolve_resolved_handoff_resume_boundary_restore or resolve_pending_resume_boundary_activation or resolve_pending_resume_session_memory_policy or preserve_context_restores_pending_resume_snapshot'`
- `pytest -q truffles-api/tests/test_pending_pack_lexicons.py -k 'pending_ack_reuses_owner_restore_without_legacy_reentry_writer or pending_sla_collect_only_sets_runtime_mode'`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'reuse_active_handover_captures_interaction_state_in_pending_resume or pending_handoff_pricing_interrupt_preserves_time_followup or pending_soft_pass_timeout_booking_resume_boundary or provider_unavailable_human_request_pending_resume_restores_resolved_bot_active_boundary'`
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

## Evidence
- updated TP plus canon sync in `docs/SOURCE_OF_TRUTH.yaml`, `docs/ACTIVE_PROGRAM.md`, `docs/_generated/AGENT_PACKET.md`, and `docs/_generated/AGENT_PACKET.json`
- diff showing the deleted or bypassed old continuity seams and the surviving owner surfaces
- green targeted continuity runtime lane plus required guards
- `STATE.md` entry that names the deleted/unreachable old continuity seam

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `1`
- **Cheap deterministic gates first:** the continuity split `rg` above plus `python3 -m py_compile`
- **Targeted lane next:** the focused `test_dialog_state_service.py`, `test_state_service.py`, `test_pending_pack_lexicons.py`, and `test_message_endpoint.py` selections above
- **Contract lane after targeted pass:** `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` when ownership-surface contracts change
- **Stop condition:** if two consecutive iterations fail without new structural evidence that the old continuity family actually shrank, stop and return to RCA instead of grinding runs
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only runtime validation in this worktree before any merge; no prod rollout claim in this block
- **Go/no-go signals:**
  - the residual continuity hotspots no longer remain live authority across `pending.py`, `state_service.py`, and `session_memory.py`
  - the targeted continuity runtime selections pass
  - `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` passes if ownership contracts changed
  - required architecture/session guards pass
- **Rollback:**
  - revert this block's continuity-owner file changes plus synced docs
  - rerun the targeted continuity runtime selections and `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py` if ownership contracts changed
- **Rollback verification:**
  - `pytest -q truffles-api/tests/test_state_service.py -k 'restore_pending_resume_context or resolve_pending_resume_boundary_activation or resolve_resolved_handoff_resume_boundary_restore or resolve_pending_resume_session_memory_policy'`
  - `pytest -q truffles-api/tests/test_message_endpoint.py -k 'pending_handoff_pricing_interrupt_preserves_time_followup or pending_soft_pass_timeout_booking_resume_boundary or provider_unavailable_human_request_pending_resume_restores_resolved_bot_active_boundary'`
- **Post-release monitoring window:** first post-merge continuity block only; do not advance to the next package if the deleted continuity family reappears across multiple owners

## Rollback
- Revert the files in the touch-list for this block and rerun the targeted continuity/runtime checks.

## No-go
- Do not create a new `continuity_service.py` or wrapper forest.
- Do not grow `state_service.py` into a transport-plus-continuity god-file.
- Do not keep continuity mutation split across `pending.py`, `state_service.py`, and `session_memory.py` and count that as progress.
- Do not edit frozen `truffles-api/app/routers/webhook/pending.py`; admissible progress must come from truthful bypass or non-frozen convergence.
- Do not move continuity ownership into public entrypoints or boundary/materialization owners.
- Do not claim full continuity closure, consultant correctness, or full runtime retirement from this block.

## Risks / blockers
- The frozen `pending.py` pending-close / pending-ack / handover-confirmation / SLA branches may still require live transport decisions, so the runtime package must prove which parts are continuity ownership versus unavoidable transport entrypoint logic.
- `state_service.py` is already large; if the package can only land by adding another mixed cluster there, the block is invalid.
- `session_memory.py` contains deterministic reset trigger helpers; if those helpers still co-decide mutation instead of becoming thin triggers, the family is not converged.
- If making the frozen pending branches unreachable requires editing the frozen file or moving transport semantics into the coordinator, the block must stop as `GAP`.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- this is still a doc-only package block; the runtime convergence under this TP remains open
- `public_entrypoint_materialization_contract`, `debounce_buffer_owner_convergence`, `proof_black_box_completion`, and `multi_pack_acceptance` remain open after this block
- pending transport forwarding / manager-active routing remains outside this continuity package

### Why not in this block
- this block only locks the truthful package destination and stop conditions for broader continuity collapse
- public entrypoint compatibility, debounce ownership, proof-path excision, and multi-pack acceptance are separate package families
- pure pending transport forwarding is not the same as continuity ownership

### Risk if deferred
- pending resume / reset / re-entry semantics remain fragmented across three modules
- frozen `pending.py` remains a live continuity owner and new drift can accrete there
- session-memory reset behavior can continue to diverge from canonical continuity payloads

### Linked follow-up Task Package(s)
- `TP-2026-03-18-consultant-core-continuity-broader-collapse-package-a922.md` (this package; runtime implementation phase)
- `TP-2026-03-18-consultant-core-public-entrypoint-materialization-contract-package-a922.md` (to be authored when the ordered backlog reaches it)

### Expiry/trigger to stop deferral
- stop deferral if any new continuity mutation lands outside `DialogStateService` plus the bounded coordinator
- stop deferral if `state_service.py` starts absorbing new transport-specific pending branches
- stop deferral if frozen `pending.py` or `session_memory.py` gain new continuity authority while this package is still open

## Next-block contract (mandatory)
### Next block objective
- implement the `continuity_broader_collapse` runtime family convergence defined by this TP and delete or bypass the old pending-resume / reset / session-memory continuity authority so it no longer remains live across frozen `pending.py`, `state_service.py`, and `session_memory.py`

### First deterministic check command
- `rg -n "_handle_handover_confirmation_gate|_get_pending_resume|_set_pending_resume|_reset_context_preserving_trace|_capture_pending_resume_context|_restore_pending_resume_context|_build_pending_resume_snapshot_payload|_prepare_pending_handoff_resume_boundary_restore|_resolve_resolved_handoff_resume_boundary_restore|_resolve_pending_resume_boundary_activation|_resolve_pending_resume_session_memory_policy|_should_reset_session_memory|_reset_session_memory|_clear_session_memory_expected_reply" truffles-api/app/routers/webhook/pending.py truffles-api/app/services/state_service.py truffles-api/app/routers/webhook/session_memory.py`

### Blocked-by conditions
- inability to keep the truthful destination inside `DialogStateService` plus one bounded coordinator surface
- any proposal that creates a new continuity service/wrapper forest or a larger `state_service.py` hotspot
- any implementation that leaves live continuity mutation split across `pending.py`, `state_service.py`, and `session_memory.py`
- any implementation that requires editing frozen `truffles-api/app/routers/webhook/pending.py` instead of making the old seam unreachable through non-frozen ownership convergence

### Owner role for closure
- Brain / Top Architect
