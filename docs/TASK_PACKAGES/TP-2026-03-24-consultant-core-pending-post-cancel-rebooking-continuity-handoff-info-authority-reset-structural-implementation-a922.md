# TP-2026-03-24 Consultant Core Pending Post Cancel Rebooking Continuity Handoff Info Authority Reset Structural Implementation A922

## Title/goal
Delete the live post-cancel rebooking overlap that still lets the touched family fall into explicit handoff or later info fallback before canonical booking continuity exhausts, and reduce duplicate executable debt in the same block.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-post-cancel-rebooking-continuity-handoff-info-authority-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-info-handoff-authority-reset-closure-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r51/{summary.json,brief.md,manual_audit.json,responses.jsonl,scenarios.json,failure_families.json}`

## One web search (mandatory before implementation)
- **Query (exact):** `site:stately.ai/docs state machine guard order fallback transition`
- **Date/time (local):** `2026-03-24 15:12 +0500`
- **Sources opened (from this query):** `https://stately.ai/docs/guards`, `https://stately.ai/docs/transitions`
- **Found ready-made solutions:** Stately's official docs describe guarded transitions as ordered checks where the first satisfied guard wins, and the default/fallback transition stays last. That matches this block directly: pending booking continuity must become the earlier guard, while explicit handoff and info fallback remain later/default edges.
- **Decision:** `build`
- **Why:** the repo already has the canonical booking owner and centralized dialog-state boundary payload. The correct move is to reuse those seams and make the fallback path unreachable for the touched family, not introduce another state-machine layer.
- **Rejected options:** replay-first discovery, a new semantic branch in `reasoning_core.py`, leaving `safe_info_fact` / `terminal_owner_unresolved` reachable on the touched family, or keeping duplicate executable defs alive while claiming structural progress.

## Root cause (mandatory)
- **Symptom:** fresh closure replay `r51` is `infra_valid=true` but `semantic_valid=false`; dialog `2` turn `8` already loses booking continuity, turn `9` exits through explicit handoff with `terminal_owner_unresolved`, and turn `10` exits through `safe_info_fact` while booking continuity should still own the next slot.
- **Minimal reproduction:** `/tmp/booking_quality/a922-go2f-seed19-r51/responses.jsonl` rows `LLM-QUAL-a922-go2f-seed19-r51-002-08-97382a`, `LLM-QUAL-a922-go2f-seed19-r51-002-09-c838ba`, and `LLM-QUAL-a922-go2f-seed19-r51-002-10-b85502`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r51/{summary.json,brief.md,manual_audit.json,responses.jsonl,scenarios.json,failure_families.json}`
  - `truffles-api/app/core/dialog_state_service.py:1369`
  - `truffles-api/app/services/reasoning_core.py:3893`
  - `truffles-api/app/services/reasoning_core.py:5227`
  - `truffles-api/app/services/reasoning_core.py:8421`
  - `truffles-api/app/services/reasoning_core.py:12127`
  - `truffles-api/app/services/reasoning_core.py:12435`
  - `truffles-api/tests/test_dialog_state_service.py:700`
  - `truffles-api/tests/test_reasoning_core.py:17369`
  - `truffles-api/tests/test_reasoning_core.py:17570`
- **Five Whys:**
  1. Why did turn `002-08` hand off instead of reactivating booking collect? Because pending continuity had no executable boundary payload when `current_goal` / expected-reply fields were already missing.
  2. Why did boundary payload stay absent? Because the boundary builder only trusted explicit `expected_reply_type`, `booking.last_question`, or session-memory last-question type.
  3. Why did explicit handoff then stay reachable? Because early/terminal handoff guards only defer when that boundary payload exists.
  4. Why did turn `002-10` then go through `safe_info_fact`? Because once the boundary payload is absent, the info owner no longer self-suppresses.
  5. Why is replay-first invalid here? Because the same structural overlap remains executable until continuity becomes the first satisfied guard.
- **Root cause statement:** post-cancel rebooking continuity was still modeled as an optional projection instead of a derived boundary from the active booking state itself, so explicit handoff and info fallback remained reachable before canonical booking continuity exhausted.
- **Fix mechanism:** infer the pending booking resume slot from the active booking payload when explicit expected-reply metadata is missing, precompute that boundary before the direct-owner chain, and delete one dead semantic-arbitration duplicate def so duplicate executable debt is reduced in the same block.

## Reuse-first plan (mandatory)
- Internal reuse:
  - `DialogStateService.derive_pending_booking_resume_boundary_payload(...)`
  - `resolve_pending_booking_reactivation_candidate(...)`
  - `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)`
  - `_try_handle_turn_planner_safe_info_owner_cutover(...)`
  - `_try_handle_turn_planner_safe_explicit_handoff_owner_cutover(...)`
- External reuse:
  - `https://stately.ai/docs/guards`
  - `https://stately.ai/docs/transitions`
- Why not reinvent the wheel: the repo already has the correct continuity/state primitives; the missing work is guard ordering and boundary inference, not a new owner runtime.

## Invariant
Do not touch frozen routers. Do not add semantic regex/phrase branching in `truffles-api/app/services/reasoning_core.py`. Do not run replay. Do not leave explicit handoff or `safe_info_fact` as the normal touched-family route.

## Scope
- make pending booking boundary inferable from active booking state even when expected-reply metadata is missing
- use that boundary to keep early info and non-explicit handoff seams unreachable for the touched family
- keep terminal unresolved handoff unreachable while that boundary is active
- reduce duplicate executable def debt in `reasoning_core.py`
- add focused deterministic regressions and publish canon evidence

## Out of scope
- new replay
- frozen-file edits
- broader residual families outside the touched post-cancel rebooking / handoff / info chain
- prod rollout

## Touch-list
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_dialog_state_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-post-cancel-rebooking-continuity-handoff-info-authority-reset-structural-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-post-cancel-rebooking-continuity-handoff-info-authority-reset-structural-implementation-a922.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Make the boundary builder infer the pending booking resume slot from active booking state when explicit expected-reply metadata is absent.
2. Reuse that inferred boundary in the existing direct-owner chain so info fallback and non-explicit handoff stay unreachable for the touched family.
3. Delete one dead duplicate semantic-arbitration top-level def from `reasoning_core.py` so duplicate debt is reduced in the same block.
4. Add focused deterministic tests that prove inferred boundary ownership before semantic handoff.
5. Run focused checks and switch canon from the decision block to this structural implementation block.

## Exact Current Authority Chain
1. Turn `002-08` already reaches `pending` without projected booking contract and can continue into semantic handoff or later fallback.
2. Before this block, `derive_pending_booking_resume_boundary_payload(...)` returned `None` unless it found explicit expected-reply metadata, `booking.last_question`, or session-memory `last_question_type`.
3. Early info and non-explicit handoff edges defer only when `pending_booking_resume_boundary_payload` exists on the live turn.
4. If canonical booking owners still return `None`, terminal unresolved explicit handoff becomes the fallback.

## Exact Canonical Target Authority Chain
1. Active booking state itself becomes enough to infer a pending booking boundary and resume slot.
2. That boundary is derived before the direct-owner chain and passed into the existing info/handoff gates.
3. Generic info and non-explicit handoff defer while the inferred boundary is active.
4. Canonical booking continuity owners execute before semantic or terminal fallback.
5. Terminal unresolved explicit handoff remains unreachable while the inferred boundary is active.

## Exact Delete-list
- Delete the old dependency on explicit expected-reply metadata as the only way to materialize pending booking boundary state.
- Delete the dead earlier `_try_handle_turn_planner_safe_semantic_arbitration_owner_cutover(...)` top-level def from `truffles-api/app/services/reasoning_core.py`.
- Make the touched-family early explicit-handoff edge unreachable at `truffles-api/app/services/reasoning_core.py:12169`-`truffles-api/app/services/reasoning_core.py:12190` whenever the inferred boundary exists.
- Make the touched-family terminal explicit-handoff fallback unreachable at `truffles-api/app/services/reasoning_core.py:12435`-`truffles-api/app/services/reasoning_core.py:12448` whenever the inferred boundary exists.
- Keep `safe_info_fact` from becoming the normal follow-up path for the touched family by deferring it whenever that boundary exists.

## Exact Continuity Writes To Centralize
- `booking.last_question`
- `expected_reply_type`
- `pending_resume.expected_reply_type`
- `session_memory.last_question_type`
- `current_goal` when the booking boundary is reconstructed

## Exact Fallback Edges That Must Not Be Normal Path
- `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=semantic_arbitration_needs_manager` on touched rebooking turns
- `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved` on the same family
- `turn_planner.safe_info_fact.v1` while post-cancel rebooking continuity still owns the next booking slot

## DoD
- active booking state is enough to derive the pending booking boundary for the touched family
- deterministic tests prove touched rebooking stays on the canonical booking owner before semantic handoff
- duplicate executable def debt is reduced in `reasoning_core.py`
- focused deterministic tests are green
- canon points to this implementation block and the next admissible move is one closure replay, not another runtime patch

## Work mode (mandatory)
`implementation`

## Checks
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `pytest -q truffles-api/tests/test_dialog_state_service.py -k "pending_resume_boundary"`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_prompt_owner_reactivates_pending_post_cancel_rebooking_state or infers_post_cancel_rebooking_boundary_before_semantic_handoff or pending_boundary_promotions_interrupt or explicit_handoff_owner or terminal_unresolved"`
- `pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/architecture`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `git diff --check`

## Evidence
- focused pytest output
- `python3 -m py_compile` output
- packet build/check output
- architecture/session guard output
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-post-cancel-rebooking-continuity-handoff-info-authority-reset-structural-implementation-a922.md`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only structural block; no prod rollout in this block.
- **Go/no-go signals:** inferred boundary exists for the touched family, explicit handoff/info fallback stay unreachable in focused deterministic coverage, duplicate debt is lower, and guards are green.
- **Rollback:** revert the touched non-frozen files in this worktree if any deterministic check fails.
- **Post-release monitoring window:** not applicable until the later closure replay.

## Rollback
Revert the touched non-frozen files in this worktree and restore the duplicate guard ledger if deterministic proof fails.

## No-go
- no frozen-file edits
- no replay before deterministic proof
- no new semantic hardcode in `reasoning_core.py`
- no workaround fallback in the normal path
- no duplicate-debt ledger growth without deletion

## Risks/blockers
- if the active booking payload is stale or already absent, the inferred boundary will still be unavailable and the next move must stay evidence-first
- broader residual `terminal_owner_unresolved` families may still remain after this block and must be classified only from fresh closure evidence
- the touched family still depends on truthful policy-core collect behavior after continuity is reactivated

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** broader duplicate debt remains in `reasoning_core.py`; replay closure is still pending; `boundary_validator.py` remains pass-through debt.
- **Why not in this block:** this block is bounded to post-cancel rebooking continuity / handoff / info authority only.
- **Risk if deferred:** future agents could still reopen replay-first mode or reintroduce a local fallback branch around the same family.
- **Linked follow-up Task Package(s):** one fresh closure replay after deterministic proof; then another delete-first family only if fresh closure evidence still surfaces a different blocker.
- **Expiry/trigger to stop deferral:** before any new replay or any new hotspot branch on the touched family.

## Next-block contract (mandatory)
- **Next block objective:** run one fresh closure replay only after deterministic proof that post-cancel rebooking continuity now owns the touched family before info/handoff fallback.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_prompt_owner_reactivates_pending_post_cancel_rebooking_state or infers_post_cancel_rebooking_boundary_before_semantic_handoff or pending_boundary_promotions_interrupt or explicit_handoff_owner or terminal_unresolved"`
- **Blocked-by conditions:** any failure in focused tests, duplicate guard, packet guard, or inability to prove the touched-family seams are unreachable.
- **Owner role for closure:** Brain / Top Architect
