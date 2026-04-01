# TP-2026-03-18-consultant-core-handover-owner-convergence-implementation-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-HANDOVER-OWNER-CONVERGENCE-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-PENDING-ESCALATION-NOTIFICATION-FROZEN-REWORK-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-escalation-notification-frozen-rework-implementation-a922.md`, `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-HANDOVER-OWNER-CONVERGENCE-POST-WAIVER-AUDIT-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Execute the destination-correction partial rewrite for the handover/escalation owner family. This block must converge active handover reuse, pending escalation create-notify, and manager lifecycle transitions into one non-frozen owner surface so `reasoning_core.py` stops assembling the flow directly, `state_service.py` stops being the default landing zone, and frozen `decision.py` loses its remaining live handover read/resolve seam.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-17-consultant-core-pending-escalation-notification-frozen-rework-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-17-consultant-core-architecture-truth-audit-a922.md`
- `docs/_generated/AGENT_PACKET.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/escalation_service.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/webhook.py`

## FACT pre-check (before implementation)
- `Baseline commands`:
  - `sed -n '8388,8478p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '19880,20035p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '23590,23640p' truffles-api/app/routers/webhook/decision.py`
  - `sed -n '2665,2765p' truffles-api/app/services/reasoning_core.py`
  - `sed -n '1240,1645p' truffles-api/app/services/state_service.py`
  - `sed -n '960,1035p' truffles-api/app/services/escalation_service.py`
  - `rg -n "from app.services.state_service import .*manager_|from app.services.state_service import escalate_to_pending|state_manager_(take|reassign|resolve|return|reopen)|manager_(take|reassign|resolve|return|reopen)\\(" truffles-api/app`
  - `rg -n "get_active_handover\\(|_reuse_active_handover\\(|_create_pending_escalation_with_notification\\(|escalate_to_pending\\(|send_telegram_notification\\(" truffles-api/app/routers/webhook/decision.py truffles-api/app/services/reasoning_core.py truffles-api/app/services/state_service.py truffles-api/app/services/escalation_service.py truffles-api/app/webhook.py`
- `FACT findings`:
  - `truffles-api/app/services/reasoning_core.py:2679-2752` still directly assembles the active-handover lookup, reuse/create branch, escalation metric, notification dispatch, and trace payload for the explicit handoff owner path.
  - `truffles-api/app/services/state_service.py:695-1617` still owns `_reuse_active_handover(...)`, `_create_pending_escalation_with_notification(...)`, `escalate_to_pending(...)`, and `manager_take/reassign/resolve/return/reopen(...)`, so the handover family keeps landing in the mixed state module.
  - `truffles-api/app/services/escalation_service.py:428`, `:789`, and `:968-1022` still own active-handover lookup, Telegram notification transport, and a duplicate `escalate_conversation(...)` orchestration path.
  - frozen `truffles-api/app/routers/webhook/decision.py:19919` still performs a direct active-handover existence check, and frozen `truffles-api/app/routers/webhook/decision.py:23619-23621` still performs direct `get_active_handover(...)` plus `manager_resolve(...)` in the rejection path.
  - non-frozen operator/runtime entrypoints still import manager lifecycle APIs from `state_service.py` in `truffles-api/app/routers/console.py`, `truffles-api/app/routers/telegram_webhook.py`, `truffles-api/app/routers/calendar.py`, `truffles-api/app/services/manager_message_service.py`, `truffles-api/app/services/reminder_service.py`, and `truffles-api/app/webhook.py`.
  - current repo truth already proves bounded seam deletions, but the surviving handover family still spans `reasoning_core.py`, `state_service.py`, `escalation_service.py`, and frozen `decision.py`, so the program is still in mixed-authority shape for this family.

## One web search (mandatory before implementation)
- **Query (exact):** `site:refactoring.com/catalog "Extract Class" "Move Function"`
- **Date/time (local):** `2026-03-18 08:31 +0500`
- **Why this query is precise:** the correction block needs a primary-source refactoring pattern for moving one cohesive lifecycle family out of a growing mixed module and away from direct callsite duplication.
- **Sources opened (from this query):**
  - `Catalog of Refactorings` — `https://refactoring.com/catalog/`
  - `Move Function` — `https://refactoring.com/catalog/moveFunction.html`
- **Source quality:** primary refactoring catalog from Martin Fowler.
- **Existing solutions found:** move cohesive lifecycle behavior into the module that has the strongest ownership over that family, and collapse scattered callsite logic into one explicit surface instead of keeping duplicated orchestration next to callers.
- **Decision:** `reuse/integrate` — introduce one dedicated `handover_owner_service.py` and move the live handover lifecycle bodies there by reusing existing transition, pending-resume, topic, and notification primitives instead of extending `state_service.py` or inventing another wrapper forest.
- **Rejected options:**
  - keep growing `state_service.py` as the handover landing zone
  - add a thin facade while leaving `reasoning_core.py`, `state_service.py`, and frozen `decision.py` as live owners
  - broad rewrite of unrelated frozen booking/pending families in the same block

## Root cause (mandatory)
- **Symptom:** the repo deleted several isolated handover seams, but the handover/escalation family still has no single live owner.
- **Minimal reproduction:**
  1. inspect `truffles-api/app/services/reasoning_core.py:2679-2752` and confirm the explicit handoff owner path still assembles lookup, reuse/create, notify, and tracing inline.
  2. inspect `truffles-api/app/services/state_service.py:695-1617` and confirm the same family still owns reuse, create-notify, and every manager lifecycle transition there.
  3. inspect `truffles-api/app/services/escalation_service.py:968-1022` and confirm a second orchestration path still exists beside transport/query helpers.
  4. inspect `truffles-api/app/routers/webhook/decision.py:19919` and `truffles-api/app/routers/webhook/decision.py:23619-23621` and confirm frozen direct handover read/resolve behavior still exists.
  5. inspect `rg -n "from app.services.state_service import .*manager_|from app.services.state_service import escalate_to_pending" truffles-api/app` and confirm multiple non-frozen entrypoints still land directly in `state_service.py`.
- **Evidence:** current code still splits handover authority across planner/runtime, state mutation, transport, and frozen compatibility seams.
- **Five Whys:**
  1. Why did previous blocks not converge the family? Because they deleted one repeated seam at a time from frozen `decision.py`.
  2. Why did the authority keep surviving? Because each seam moved to the nearest non-frozen file instead of a lifecycle owner module.
  3. Why did `state_service.py` become the landing zone? Because it already had transition and pending-resume helpers, so each bounded cut reused it opportunistically.
  4. Why is `reasoning_core.py` still mixed? Because there is still no single handover lifecycle API for planner-owned escalation turns.
  5. Why is this now a stop-the-line issue? Because continuing seam farming would only rename the old architecture and leave live ownership split across the same family.
- **Root cause statement:** the handover/escalation family is still organized by local proximity of helpers, not by lifecycle ownership, so live authority remains split across `reasoning_core.py`, `state_service.py`, `escalation_service.py`, and frozen `decision.py`.
- **Fix mechanism:** create one dedicated handover owner surface outside frozen files, move the live lifecycle bodies there, reroute non-frozen callers to that owner surface, and reduce frozen callsites to bounded owner-surface invocation only under a scoped waiver.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - keep generic transition primitives (`transition_state(...)`, `force_state(...)`) in `truffles-api/app/services/state_service.py`
  - reuse pending-resume helpers already extracted in `truffles-api/app/services/state_service.py` and `truffles-api/app/core/dialog_state_service.py`
  - reuse Telegram topic/notification transport helpers already present in `truffles-api/app/services/escalation_service.py`
  - reuse existing `_legacy` compatibility surface so frozen `booking.py` / `pending.py` can keep indirect compatibility while the owner body moves
- **External reuse:** Martin Fowler refactoring catalog guidance for `Extract Class` / `Move Function`
- **Why not build from scratch:** the repo already has the required transport, transition, and pending-resume primitives; the missing piece is ownership convergence, not new functionality.

## Invariant
- no `truffles-api/app/routers/webhook/booking.py` edits
- no new semantic hardcode
- no consultant-correctness claim beyond targeted deterministic/runtime-family proof
- `handover_owner_service.py` must stay lifecycle-scoped; it must not become a new generic god-file
- a new helper that leaves old live owners in `reasoning_core.py`, `state_service.py`, and frozen `decision.py` does not count as progress

## Scope
- create `truffles-api/app/services/handover_owner_service.py` as the single runtime owner surface for:
  - active handover lookup/reuse
  - pending escalation create-reopen-notify
  - manager take/reassign/resolve/return/reopen
  - handover state transitions and transport side effects
- move live handover lifecycle bodies out of `truffles-api/app/services/state_service.py`
- remove or reduce duplicate orchestration in `truffles-api/app/services/escalation_service.py`
- reroute `truffles-api/app/services/reasoning_core.py` and non-frozen operator/runtime entrypoints to the new owner surface
- under scoped waiver, reduce frozen `truffles-api/app/routers/webhook/decision.py` direct read/resolve seams to owner-surface invocation only
- add/update tests and architecture checks for the converged owner surface

## Out of scope
- full rewrite of frozen `booking.py`
- full rewrite of frozen `pending.py`
- proof-path or multi-pack closure
- broad transport rewrite inside Telegram adapters
- product-level behavior proof bundle beyond the targeted family checks for this block

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-18-consultant-core-handover-owner-convergence-implementation-a922.md`
- `docs/LEGACY_SUNSET.yaml`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `truffles-api/app/services/handover_owner_service.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/escalation_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/routers/telegram_webhook.py`
- `truffles-api/app/routers/calendar.py`
- `truffles-api/app/services/manager_message_service.py`
- `truffles-api/app/services/reminder_service.py`
- `truffles-api/app/webhook.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/_legacy.py`
- `truffles-api/tests/test_handover_owner_service.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_telegram_webhook.py`
- `truffles-api/tests/test_manager_message_rbac.py`
- `truffles-api/tests/test_console_cases_helpers.py`
- `truffles-api/tests/test_console_inbox_macros.py`
- `truffles-api/tests/test_calendar_noshow_followup_router.py`
- `truffles-api/tests/test_reminders.py`
- `truffles-api/tests/architecture/`

## Plan (1..N)
1. Add `truffles-api/app/services/handover_owner_service.py` and move the live handover lifecycle bodies there.
2. Reduce `truffles-api/app/services/state_service.py` to generic transition/pending-resume primitives only; remove the live handover entrypoints from that file.
3. Remove or reduce duplicate orchestration in `truffles-api/app/services/escalation_service.py` so transport/query helpers are supporting primitives, not a second owner.
4. Switch `truffles-api/app/services/reasoning_core.py` and the non-frozen operator/runtime entrypoints to the new owner surface.
5. Under scoped waiver, reduce frozen `decision.py` direct `get_active_handover(...)` and `manager_resolve(...)` seams plus compatibility wrappers to bounded owner-surface invocation only.
6. Update test patch points and add owner-surface coverage.
7. Sync canon/session/state artifacts and rerun the required checks.

## DoD
- `truffles-api/app/services/reasoning_core.py` no longer directly imports or assembles `get_active_handover`, `_reuse_active_handover`, `escalate_to_pending`, or `send_telegram_notification`
- `truffles-api/app/services/state_service.py` no longer owns the live handover lifecycle entrypoints (`_reuse_active_handover`, `_create_pending_escalation_with_notification`, `escalate_to_pending`, `manager_take`, `manager_reassign`, `manager_resolve`, `manager_return`, `manager_reopen`)
- `truffles-api/app/services/escalation_service.py` no longer owns duplicate `escalate_conversation(...)` orchestration
- frozen `truffles-api/app/routers/webhook/decision.py` no longer directly owns the rejection-path `get_active_handover(...)` + `manager_resolve(...)` seam, and its remaining handover hooks are bounded owner-surface invocations only
- targeted runtime/operator tests and governance checks are green

## Checks
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `pytest -q truffles-api/tests/test_state_service.py -k 'handover or pending_resume or escalation or manager_'`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k 'explicit_handoff_owner'`
- `pytest -q truffles-api/tests/test_consultant_core_runtime_contracts.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'human_request_bypasses_active_booking_flow_and_escalates or llm_policy_core_reschedule_missing_reference_availability_phrase_escalates_to_handoff or booking_verification_creates_handover_when_none_active or style_reference_photo_escalates_during_booking_flow or provider_unavailable_human_request_pending_resume_timeout_resume_boundary_after_manager_resolve'`
- `pytest -q truffles-api/tests/test_telegram_webhook.py -k 'resolve_uses_preserve_context or simulation_resolve_uses_preserve_context'`
- `pytest -q truffles-api/tests/test_manager_message_rbac.py`
- `pytest -q truffles-api/tests/test_console_cases_helpers.py -k 'reassign or reopen'`
- `pytest -q truffles-api/tests/test_console_inbox_macros.py -k 'take or reopen'`
- `pytest -q truffles-api/tests/test_calendar_noshow_followup_router.py -k 'reopen'`
- `pytest -q truffles-api/tests/test_reminders.py -k 'manager_resolve'`

## Evidence
- new `truffles-api/app/services/handover_owner_service.py` with the converged lifecycle surface
- `rg` evidence that `reasoning_core.py` no longer imports split handover primitives and `state_service.py` no longer owns the removed lifecycle entrypoints
- frozen `decision.py` diff showing the direct handover read/resolve seam reduced to owner-surface invocation only
- targeted runtime/operator test results
- updated packet/canon/session/state artifacts

## Rollback
1. Revert `handover_owner_service.py` and all caller migrations.
2. Restore previous handover lifecycle bodies in `state_service.py` / `escalation_service.py` if the owner convergence fails.
3. Restore the scoped waiver in `docs/LEGACY_SUNSET.yaml`.
4. Regenerate packet and rerun targeted checks.

## No-go
- no `booking.py` edits
- no continuation of seam farming inside `state_service.py`
- no second orchestration surface beside `handover_owner_service.py`
- no proof/eval semantic rewrite used as acceptance evidence
- no weakened quality gates or targeted-green-only correctness claim

## Risks / blockers
- frozen `decision.py` changes still require a scoped waiver even though the owner body lives outside frozen files
- many tests patch legacy import points (`state_manager_*`, `_legacy`, `decision_router._reuse_active_handover`), so patch-point migration must stay bounded and explicit
- `truffles-api/app/webhook.py` still carries older direct handover paths and must either migrate in this block or remain explicit residual debt
- if the new owner surface starts absorbing unrelated conversation logic, the block recreates the same god-file problem under a new name and must stop

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only partial rewrite with bounded freeze waiver on `decision.py`
- **Go/no-go signals:** `reasoning_core.py` no longer assembles the split flow; `state_service.py` no longer owns the lifecycle entrypoints; frozen direct read/resolve seam is reduced; targeted runtime/operator suites are green
- **Rollback:** revert service extraction, caller migrations, waiver lines, and test patch-point changes
- **Post-release monitoring window:** local deterministic/runtime checks only for this block; no acceptance `lock -> replay -> canary -> full` claim yet

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** targeted family tests plus governance checks only
- **Stop condition:** if the block cannot make `reasoning_core.py` and `state_service.py` non-owners without leaving a second live owner surface, stop with `GAP`
- **Escalation path:** `Top Architect`

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** frozen compatibility wrappers may still remain in `decision.py`; indirect legacy callers in frozen `booking.py` / `pending.py` still exist through `_legacy`; proof-path and multi-pack closure remain open
- **Why not in this block:** the correction target is owner convergence for the handover family, not full consultant closure
- **Risk if deferred:** `state_service.py` keeps accreting mixed handover logic, `reasoning_core.py` keeps bypassing typed owner convergence, and frozen `decision.py` keeps live read/resolve seams
- **Linked follow-up Task Package(s):** `TP-2026-03-18-consultant-core-handover-owner-convergence-post-waiver-audit-a922` (to be authored after runtime evidence), `TP-2026-03-18-consultant-core-proof-bundle-gated-acceptance-a922` (only after owner convergence lands)
- **Expiry/trigger to stop deferral:** before any next consultant-core handover/escalation change or correctness claim

## Next-block contract (mandatory)
- **Next block objective:** run the post-waiver audit and prove that the old mixed handover authority family is deleted or unreachable outside the new owner surface
- **First deterministic check command:** `rg -n "get_active_handover_service|send_telegram_notification|escalate_to_pending|_reuse_active_handover|manager_(take|reassign|resolve|return|reopen)" truffles-api/app/services/reasoning_core.py truffles-api/app/services/state_service.py truffles-api/app/services/escalation_service.py truffles-api/app/routers/webhook/decision.py truffles-api/app/webhook.py`
- **Blocked-by conditions:** if `reasoning_core.py`, `state_service.py`, or frozen `decision.py` still retain live handover lifecycle bodies after the rewrite, stop with `GAP`
- **Owner role for closure:** `Top Architect`
