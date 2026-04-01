# TP-2026-03-24 Consultant Core Pending Booking Continuity Terminal Handoff Authority Reset Structural Implementation A922

## Title/goal
Delete the live pending booking continuity gap that still lets the touched family fall through `terminal_owner_unresolved`, by restoring one canonical booking reactivation authority from centralized dialog-state continuity and deleting the dead duplicate owner defs that still shadow the same family in `reasoning_core.py`.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-booking-pending-handoff-authority-reset-closure-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r49/{summary.json,brief.md,responses.jsonl,runtime_state.json}`

## One web search (mandatory before implementation)
- **Query (exact):** `site:stately.ai/docs XState history states guards official docs`
- **Date/time (local):** `2026-03-24 12:18 +0500`
- **Sources opened (from this query):** `https://stately.ai/docs/eventless-transitions`, `https://stately.ai/docs/history-states`
- **Found ready-made solutions:** official Stately docs describe two relevant state-machine primitives: history states remember the last active child state when a parent state is re-entered, and guarded eventless transitions run automatically as soon as the enabling condition holds. That maps directly to this family: pending resume should restore the last booking collect contract from centralized state, and terminal fallback should stay only as the post-exhaustion guard path.
- **Decision:** `build`
- **Why:** we do not need to integrate XState into runtime; we need to reuse the state-machine principle to make the existing canonical owner treat pending booking continuity as a remembered state with a guarded automatic re-entry, before terminal handoff fallback is even eligible.
- **Rejected options:** integrate a new state-machine runtime; keep the old `terminal_owner_unresolved` explicit handoff seam as a normal route; add another local semantic branch beside the old seam; use replay as discovery before deleting the seam.

## Root cause (mandatory)
- **Symptom:** fresh closure replay `r49` still fails on `LLM-QUAL-a922-go2f-seed19-r49-002-09-489e4e` and `LLM-QUAL-a922-go2f-seed19-r49-002-10-674439`; the pending turn still exits through `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved`, and the follow-up promotions turn still escapes through `turn_planner.safe_info_fact.v1` while booking continuity still expects progress.
- **Minimal reproduction:** inspect dialog `2` turn `9` and turn `10` in `/tmp/booking_quality/a922-go2f-seed19-r49/responses.jsonl`, then trace the live owner chain in `truffles-api/app/services/reasoning_core.py:12596` through `truffles-api/app/services/reasoning_core.py:12874`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r49/responses.jsonl`
  - `/tmp/booking_quality/a922-go2f-seed19-r49/runtime_state.json`
  - `truffles-api/app/services/reasoning_core.py:4323`
  - `truffles-api/app/services/reasoning_core.py:5682`
  - `truffles-api/app/services/reasoning_core.py:7846`
  - `truffles-api/app/services/reasoning_core.py:12596`
  - `truffles-api/app/services/reasoning_core.py:12781`
  - `truffles-api/app/services/reasoning_core.py:12794`
  - `truffles-api/app/services/reasoning_core.py:12807`
  - `truffles-api/app/services/reasoning_core.py:12820`
  - `truffles-api/app/services/reasoning_core.py:12862`
  - `truffles-api/app/services/reasoning_core.py:12874`
  - `truffles-api/app/core/booking_prompt_owner.py:490`
  - `truffles-api/app/core/dialog_state_service.py:1323`
- **Five Whys:**
  1. Why does turn `002-09` still hand off? Because pending booking reactivation can still return `None`, so the runtime reaches the terminal unresolved explicit handoff fallback.
  2. Why can pending reactivation still return `None`? Because the reactivation owner still calls the canonical booking prompt owner without reconstructing the booking collect contract from centralized dialog-state continuity.
  3. Why is centralized continuity required here? Because the pending/handoff family already stores booking resume state in `DialogStateService`, but the owner path still behaves as if the family has no remembered booking state when the live snapshot is sparse.
  4. Why does turn `002-10` then escape through `safe_info_fact`? Because after turn `002-09` falls out of booking reactivation, `conversation_snapshot.booking_active` and the expected reply projection are no longer active, so info routing becomes the normal path.
  5. Why is another replay or micro-fix wrong? Because the live runtime still contains the same old fallback authority and dead duplicate owner defs, so replay would only surface more rows without reducing the overlap.
- **Root cause statement:** the touched pending booking continuity family still lacks one executable re-entry authority that restores the remembered booking collect contract from centralized dialog-state continuity before terminal fallback, and `reasoning_core.py` still carries dead duplicate owner defs on the same family path.
- **Fix mechanism:** make pending booking reactivation derive its boundary contract from centralized dialog-state continuity, feed that contract into the canonical booking prompt owner before fallback, and delete the dead duplicate info / booking verification / specialist follow-up owner defs that still shadow the family in `reasoning_core.py`.

## Reuse-first plan (mandatory)
- Internal reuse:
  - `decision_router._derive_pending_booking_resume_boundary_payload(...)`
  - `DialogStateService.derive_pending_booking_resume_boundary_payload(...)`
  - `resolve_llm_booking_prompt_candidate(...)`
  - `_resolve_turn_planner_pending_booking_reactivation_candidate(...)`
  - `_finalize_turn_planner_owner_cutover(...)`
- External reuse:
  - `https://stately.ai/docs/eventless-transitions`
  - `https://stately.ai/docs/history-states`
- Why not reinvent the wheel: the platform already has centralized pending resume state and a canonical booking owner; the block should reconnect them and delete dead seams, not introduce a second continuity system.

## Invariant
Do not touch frozen routers. Do not add semantic hardcode or a new fallback branch in `truffles-api/app/services/reasoning_core.py`. Do not run replay before the touched family is deterministic and the old terminal fallback seam is unreachable for that family.

## Scope
- canonical pending booking reactivation from centralized dialog-state continuity
- delete dead duplicate top-level owner defs tied to the touched family path
- focused regressions proving canonical owner inputs and explicit handoff unreachability for the touched family
- canon/report updates for the new structural block

## Out of scope
- new replay
- prod rollout
- unrelated duplicate-def families outside the touched owner path
- frozen file changes

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-structural-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-structural-implementation-a922.md`
- `truffles-api/app/core/booking_prompt_owner.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Add one canonical pending booking reactivation seed path in `booking_prompt_owner.py` that restores the remembered booking collect contract from centralized dialog-state continuity before calling the canonical LLM booking owner.
2. Delete the dead duplicate top-level defs for `_try_handle_turn_planner_safe_info_owner_cutover`, `_try_handle_turn_planner_safe_booking_verification_owner_cutover`, and `_try_handle_turn_planner_safe_specialist_followup_owner_cutover` from `reasoning_core.py`.
3. Add focused regressions that prove the touched pending family enters the canonical owner path and does not fall through explicit handoff fallback.
4. Run deterministic checks and then switch canon from the decision block to this implementation block.

## Exact Current Authority Chain
1. Runtime owner selection still enters the direct-owner chain in `truffles-api/app/services/reasoning_core.py:12596` through `truffles-api/app/services/reasoning_core.py:12874`.
2. The touched pending family reaches `truffles-api/app/services/reasoning_core.py:7846`, where `_resolve_turn_planner_pending_booking_reactivation_candidate(...)` may still return `None`.
3. If reactivation fails, the path continues through `booking_verification` (`truffles-api/app/services/reasoning_core.py:12781`), `check_booking_prompt` (`truffles-api/app/services/reasoning_core.py:12794`), `specialist_followup` (`truffles-api/app/services/reasoning_core.py:12807`), and `booking_prompt_owner` (`truffles-api/app/services/reasoning_core.py:12820`).
4. When all of those return `None`, runtime builds `PolicyCoreRouteSnapshot(... reason='terminal_owner_unresolved' ...)` at `truffles-api/app/services/reasoning_core.py:12862` and re-enters `turn_planner.safe_explicit_handoff_owner.v1` at `truffles-api/app/services/reasoning_core.py:12874`.
5. The later follow-up info turn is then free to route through `truffles-api/app/services/reasoning_core.py:5682` because booking continuity is no longer projected as active.

## Exact Canonical Target Authority Chain
1. Pending booking turns first derive their resume boundary from centralized dialog-state continuity via `DialogStateService` / `decision_router._derive_pending_booking_resume_boundary_payload(...)`.
2. That boundary payload feeds `resolve_pending_booking_reactivation_candidate(...)` in `truffles-api/app/core/booking_prompt_owner.py:490`, which then calls `resolve_llm_booking_prompt_candidate(...)` with the restored booking goal and expected reply contract.
3. The touched family returns through `truffles-api/app/services/reasoning_core.py:7846` into the canonical booking prompt owner finalize path, which already writes continuity through `DialogStateService`.
4. Only after canonical owner exhaustion may terminal fallback remain available, and it must be unreachable for the touched family contract.

## Exact Delete-list
- Delete the dead earlier top-level defs for `_try_handle_turn_planner_safe_info_owner_cutover` in `truffles-api/app/services/reasoning_core.py`.
- Delete the dead earlier top-level defs for `_try_handle_turn_planner_safe_booking_verification_owner_cutover` in `truffles-api/app/services/reasoning_core.py`.
- Delete the dead earlier top-level defs for `_try_handle_turn_planner_safe_specialist_followup_owner_cutover` in `truffles-api/app/services/reasoning_core.py`.
- Make the touched-family `truffles-api/app/services/reasoning_core.py:12862` -> `truffles-api/app/services/reasoning_core.py:12874` edge unreachable by restoring canonical booking continuity before the path can exhaust.

## Exact Continuity Writes To Centralize
- `expected_reply_type`
- `expected_reply_reason`
- `pending_resume.expected_reply_type`
- `pending_resume.expected_reply_reason`
- `interaction_owner`
- `interaction_resume_slot`
- `last_question_type`
- `unanswered_questions_count`

## Exact Fallback Edges That Must Not Be Normal Path
- `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved`
- `turn_planner.safe_info_fact.v1` while booking continuity still owns the next slot

## DoD
- pending booking reactivation uses centralized dialog-state continuity before calling the canonical booking owner
- the touched pending family no longer reaches explicit handoff fallback in focused deterministic coverage
- the dead duplicate defs for the touched family path are deleted and the duplicate guard count is reduced
- focused deterministic checks are green
- canon points to this implementation block and truthfully records the structural change

## Work mode (mandatory)
`implementation`

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_booking_reactivation_candidate or pending_collect_reactivation or post_cancel_rebooking_state or promotions_interrupt_and_resumes_time_collect or explicit_handoff_owner or terminal_unresolved"`
- `pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `python3 -m py_compile truffles-api/app/core/booking_prompt_owner.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `git diff --check`

## Evidence
- focused pytest output
- `python3 -m py_compile` output
- `python3 scripts/build_agent_packet.py --check` output
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py` output
- `git diff --check` output
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-structural-implementation-a922.md`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only structural implementation; no prod rollout in this block.
- **Go/no-go signals:** pending reactivation reaches canonical owner deterministically, explicit handoff fallback is unreachable in focused tests, duplicate debt is reduced, and all guards are green.
- **Rollback:** revert the touched non-frozen files in this worktree if any deterministic check fails.
- **Post-release monitoring window:** not applicable until closure replay.

## Rollback
Revert the touched non-frozen files in this worktree and restore the previous duplicate guard allowances if the canonical reactivation path does not hold.

## No-go
- no frozen-router edits
- no replay before deterministic proof
- no new semantic branch in `truffles-api/app/services/reasoning_core.py`
- no threshold weakening or hidden degrade metadata
- no new normal-path fallback around `terminal_owner_unresolved`

## Risks/blockers
- some of the broader `24` `terminal_owner_unresolved` rows may still belong to a second subfamily after this touched family is deleted
- if live continuity data is absent from both live context and `pending_resume`, this block must stop at deterministic proof and report the residual gap instead of inventing new semantics

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** later replay closure is still required; `boundary_validator.py` remains pass-through debt; unrelated duplicate families remain in `reasoning_core.py`.
- **Why not in this block:** this block is bounded to the pending booking continuity / terminal handoff family only.
- **Risk if deferred:** future agents could reintroduce replay-first symptom work or keep normalizing through terminal fallback.
- **Linked follow-up Task Package(s):** one fresh closure replay after deterministic proof; then next delete-first family if any `terminal_owner_unresolved` rows remain.
- **Expiry/trigger to stop deferral:** before any new replay or before any new runtime branch is added on the same family.

## Next-block contract (mandatory)
- **Next block objective:** run one fresh closure replay only after deterministic proof that the touched family no longer executes through the old explicit handoff fallback seam.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_booking_reactivation_candidate or pending_collect_reactivation or post_cancel_rebooking_state or promotions_interrupt_and_resumes_time_collect or explicit_handoff_owner or terminal_unresolved"`
- **Blocked-by conditions:** any failure in focused tests, duplicate guard, packet guard, or inability to prove the touched-family fallback edge is unreachable.
- **Owner role for closure:** Brain / Top Architect
