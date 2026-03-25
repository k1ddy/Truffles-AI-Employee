# TP-2026-03-24 Consultant Core Pending Booking Reentry Booking Prompt Authority Reset Structural Implementation A922

## Title/goal
Delete the live booking reentry overlap that still lets the touched family fall into explicit handoff before canonical booking continuity, and delete the tool-reply fast-path continuity gap that still drops `expected_reply_type=time` on service-grounded promotions follow-ups.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-reentry-booking-prompt-authority-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-post-cancel-rebooking-continuity-handoff-info-authority-reset-closure-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r52/{summary.json,brief.md,manual_audit.json,responses.jsonl,scenarios.json}`

## One web search (mandatory before implementation)
- **Query (exact):** `site:stately.ai/docs transition priority guarded transitions order`
- **Date/time (local):** `2026-03-24 17:38 +0500`
- **Sources opened (from this query):** `https://stately.ai/docs/transitions`
- **Found ready-made solutions:** Stately documents ordered transitions where earlier guarded transitions must win before fallback/default transitions. That matches this block exactly: booking continuity must sit before explicit handoff and info fallback, and the default fast path must preserve the state needed for the next guarded turn.
- **Decision:** `build`
- **Why:** the repo already has the canonical typed seams (`TurnPlanner`, `DialogStateService`, `booking_prompt_owner`). The missing work is authority order and centralized state sync, not a new framework.
- **Rejected options:** replay-first discovery, a local row-specific branch in `reasoning_core.py`, legacy expected-reply helper writes, or leaving duplicate executable defs alive while claiming structural progress.

## Root cause (mandatory)
- **Symptom:** fresh closure replay `r52` is `infra_valid=true` but `semantic_valid=false`; row `002-09` still exits through explicit handoff with `terminal_owner_unresolved`, and row `002-10` still exits through `safe_info_fact` while continuity should still own `expected_reply_type=time`.
- **Minimal reproduction:** `/tmp/booking_quality/a922-go2f-seed19-r52/responses.jsonl` rows `LLM-QUAL-a922-go2f-seed19-r52-002-09-c14afa` and `LLM-QUAL-a922-go2f-seed19-r52-002-10-733e03`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r52/{summary.json,brief.md,manual_audit.json,responses.jsonl,scenarios.json}`
  - `truffles-api/app/services/reasoning_core.py:12053`
  - `truffles-api/app/services/reasoning_core.py:12119`
  - `truffles-api/app/services/reasoning_core.py:12132`
  - `truffles-api/app/services/reasoning_core.py:4273`
  - `truffles-api/app/services/reasoning_core.py:6968`
  - `truffles-api/app/services/reasoning_core.py:7160`
  - `truffles-api/tests/test_reasoning_core.py:7388`
  - `truffles-api/tests/test_reasoning_core.py:7830`
  - `truffles-api/tests/test_reasoning_core.py:8397`
  - `truffles-api/tests/test_reasoning_core.py:18212`
- **Five Whys:**
  1. Why did row `002-09` still hand off? Because pending booking reentry could still hit old direct-owner seams before `booking_prompt_owner`.
  2. Why was `booking_prompt_owner` still losing authority? Because the direct-owner chain still evaluated catalog/info/handoff seams ahead of it on the touched family.
  3. Why did row `002-10` still lose continuity after a service-grounded promotions answer? Because the artifact fast path in `_finalize_turn_planner_owner_cutover(...)` did not perform centralized continuity sync before send/save.
  4. Why is that enough to re-open `safe_info_fact`? Because once `expected_reply_type` and booking payload are not persisted, the next booking follow-up no longer has a live contract to suppress info fallback.
  5. Why is replay-first invalid here? Because both seams were still normal execution paths until code deleted them or made them unreachable.
- **Root cause statement:** the touched family still had split execution authority: booking reentry could bypass `booking_prompt_owner` before old direct-owner seams, and tool-reply artifact finalization could bypass `DialogStateService` continuity sync, so continuity was not authoritative across the family.
- **Fix mechanism:** move `booking_prompt_owner` earlier in the direct-owner chain, centralize continuity sync plus booking payload persistence inside `_finalize_turn_planner_owner_cutover(...)`, and delete dead duplicate defs from the touched owner family.

## Reuse-first plan (mandatory)
- Internal reuse:
  - `DialogStateService.build_expected_reply_context_sync_result(...)`
  - `_finalize_turn_planner_owner_cutover(...)`
  - `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)`
  - `resolve_tool_expected_reply_contract(...)`
- External reuse:
  - `https://stately.ai/docs/transitions`
- Why not reinvent the wheel: the repo already has the correct typed owner and continuity seams; the defect is their order and a fast-path bypass.

## Invariant
Do not touch frozen routers. Do not add semantic regex/phrase branching in `reasoning_core.py`. Do not reintroduce legacy expected-reply helper writes. Do not open a new replay in this block.

## Scope
- make `booking_prompt_owner` the first executable authority for touched booking reentry turns
- centralize service-grounded promotions tool-reply continuity sync on the artifact fast path
- persist booking payload on that same path
- delete dead duplicate executable defs in `reasoning_core.py`
- add focused deterministic regressions and publish canon evidence

## Out of scope
- new replay
- frozen-file edits
- broader residual families outside the touched booking reentry / promotions continuity chain
- prod rollout

## Touch-list
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-reentry-booking-prompt-authority-reset-structural-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-reentry-booking-prompt-authority-reset-structural-implementation-a922.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Move `booking_prompt_owner` earlier in the touched direct-owner chain so pending booking reentry reaches canonical continuity before old info / explicit handoff seams.
2. Centralize artifact fast-path continuity sync and booking payload persistence inside `_finalize_turn_planner_owner_cutover(...)`.
3. Delete the dead earlier duplicate defs for the touched catalog/service-query owner family.
4. Add focused regressions for booking reentry preemption and service-grounded promotions continuity.
5. Run deterministic checks and switch canon to this structural implementation block.

## Exact Current Authority Chain
1. Before this block, the touched direct-owner chain checked info / explicit handoff before `booking_prompt_owner`, so booking reentry could still miss canonical continuity.
2. Service-grounded promotions already used `catalog.service_query`, but the artifact fast path returned before `DialogStateService` synced `expected_reply_type` and booking payload into context.
3. Old explicit handoff stayed reachable for row `002-09`, and `safe_info_fact` stayed reachable for row `002-10`.

## Exact Canonical Target Authority Chain
1. `booking_prompt_owner` executes before touched info / explicit-handoff seams.
2. Service-grounded promotions tool replies preserve continuity through `_finalize_turn_planner_owner_cutover(...)` -> `DialogStateService.build_expected_reply_context_sync_result(...)`.
3. Booking payload for the reactivated flow is persisted on the same path.
4. Old explicit handoff and later info fallback remain unreachable until canonical owner exhaustion.

## Exact Delete-list
- Delete the old direct-owner ordering that let touched booking reentry reach catalog/info/handoff seams before `booking_prompt_owner`.
- Delete the artifact fast-path continuity-loss seam in `_finalize_turn_planner_owner_cutover(...)`.
- Delete the dead earlier `_try_handle_turn_planner_safe_catalog_fact_owner_cutover(...)` and `_try_handle_turn_planner_safe_service_query_fact_owner_cutover(...)` top-level defs.

## Exact Continuity Writes To Centralize
- `expected_reply_type`
- `expected_reply_reason`
- `booking.service`
- `booking.last_question`
- question/session-memory sync produced by `DialogStateService`

## Exact Fallback Edges That Must Not Be Normal Path
- `turn_planner.safe_explicit_handoff_owner.v1` for touched booking reentry turns before canonical owner exhaustion
- `turn_planner.safe_info_fact.v1` for the touched service-grounded promotions follow-up while booking continuity still owns the next slot

## DoD
- touched booking reentry reaches `booking_prompt_owner` before old direct-owner seams
- service-grounded promotions tool replies persist `expected_reply_type=time` and booking payload through the centralized continuity writer
- duplicate executable debt is reduced in `reasoning_core.py`
- focused deterministic tests are green
- canon points to this implementation block and the next admissible move is one closure replay

## Work mode (mandatory)
`implementation`

## Checks
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_booking_reentry_preempts_explicit_handoff_without_boundary_payload or answers_service_grounded_promotions_interrupt_and_advances_to_time or booking_prompt_owner_reactivates_pending_collect_without_active_booking_snapshot or booking_prompt_owner_answers_promotions_interrupt_and_resumes_time_collect or pending_boundary_promotions_interrupt or explicit_handoff_owner or terminal_unresolved or pending_ack_continuity_family_clears_pending_before_terminal_unresolved"`
- `pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `pytest -q truffles-api/tests/architecture`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `git diff --check`

## Evidence
- focused pytest output
- `python3 -m py_compile` output
- packet build/check output
- architecture/session guard output
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-reentry-booking-prompt-authority-reset-structural-implementation-a922.md`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only structural block; no prod rollout in this block.
- **Go/no-go signals:** touched reentry reaches canonical owner first, tool-reply continuity sync persists `expected_reply_type=time` plus booking payload, duplicate debt is lower, and guards are green.
- **Rollback:** revert the touched non-frozen files in this worktree if any deterministic check fails.
- **Post-release monitoring window:** not applicable until the later closure replay.

## Rollback
Revert the touched non-frozen files in this worktree and restore the duplicate guard ledger if deterministic proof fails.

## No-go
- no frozen-file edits
- no replay before deterministic proof
- no new semantic hardcode in `reasoning_core.py`
- no legacy helper fallback in the normal path
- no duplicate-debt ledger growth without deletion

## Risks/blockers
- broader residual terminal handoff families may still remain after this block and must be classified only from fresh closure evidence
- this block depends on the current typed seams staying canonical; future local branches around them would re-open the same family

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** broader duplicate debt remains in `reasoning_core.py`; replay closure is still pending; `boundary_validator.py` remains pass-through debt.
- **Why not in this block:** this block is bounded to booking reentry / service-grounded promotions continuity authority only.
- **Risk if deferred:** future agents could still revive the same class of bug by adding a local branch around the touched family.
- **Linked follow-up Task Package(s):** one fresh closure replay after deterministic proof; then another delete-first family only if fresh closure evidence surfaces a different blocker.
- **Expiry/trigger to stop deferral:** before any new replay or any new hotspot branch on the touched family.

## Next-block contract (mandatory)
- **Next block objective:** run one fresh closure replay only after deterministic proof that touched booking reentry now resolves through canonical continuity and that service-grounded promotions preserves the next-slot contract.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_booking_reentry_preempts_explicit_handoff_without_boundary_payload or answers_service_grounded_promotions_interrupt_and_advances_to_time or booking_prompt_owner_answers_promotions_interrupt_and_resumes_time_collect or pending_boundary_promotions_interrupt or explicit_handoff_owner or terminal_unresolved"`
- **Blocked-by conditions:** any failure in focused tests, duplicate guard, packet guard, or inability to prove the touched-family seams are unreachable.
- **Owner role for closure:** Brain / Top Architect
