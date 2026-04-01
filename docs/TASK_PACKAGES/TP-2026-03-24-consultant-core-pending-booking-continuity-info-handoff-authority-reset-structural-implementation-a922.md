# TP-2026-03-24 Consultant Core Pending Booking Continuity Info Handoff Authority Reset Structural Implementation A922

## Title/goal
Delete the live pending booking continuity overlap that still lets the touched family route through `safe_info_fact` or explicit handoff before canonical booking continuity exhausts, and move touched continuity writes onto direct `DialogStateService` sync instead of the legacy expected-reply helper path.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-info-handoff-authority-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-closure-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r50/{summary.json,brief.md,responses.jsonl,trace_bundle.jsonl}`

## One web search (mandatory before implementation)
- **Query (exact):** `XState transition order guarded transitions higher priority official`
- **Date/time (local):** `2026-03-24 13:59:48 +0500`
- **Sources opened (from this query):** `https://stately.ai/docs/guards`
- **Found ready-made solutions:** the official guards reference documents priority-based guarded transitions: the first matching guarded edge wins, and fallback transitions stay after those guards. That matches the structural need here: pending booking continuity must guard the touched family before generic info or handoff fallback edges are eligible.
- **Decision:** `build`
- **Why:** the runtime already has the canonical booking continuity owner and centralized dialog-state boundary payloads; the block should reuse those seams and reorder the authority, not add a new state-machine runtime.
- **Rejected options:** another replay-first iteration; another local semantic branch in `reasoning_core.py`; leaving `safe_info_fact` or `terminal_owner_unresolved` as the normal touched-family route; keeping legacy expected-reply helper calls as the touched continuity writer.

## Root cause (mandatory)
- **Symptom:** fresh closure replay `r50` is `infra_valid=true` but `semantic_valid=false`; dialog `2` turn `9` still exits through `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved`, and turn `10` still exits through `turn_planner.safe_info_fact.v1` while booking continuity should still own the next slot.
- **Minimal reproduction:** `/tmp/booking_quality/a922-go2f-seed19-r50/responses.jsonl` rows `LLM-QUAL-a922-go2f-seed19-r50-002-09-48c6ab` and `LLM-QUAL-a922-go2f-seed19-r50-002-10-4439b1`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r50/{summary.json,brief.md,responses.jsonl,trace_bundle.jsonl}`
  - `truffles-api/app/services/reasoning_core.py:5132`
  - `truffles-api/app/services/reasoning_core.py:5154`
  - `truffles-api/app/services/reasoning_core.py:5697`
  - `truffles-api/app/services/reasoning_core.py:12596`
  - `truffles-api/app/services/reasoning_core.py:12609`
  - `truffles-api/app/services/reasoning_core.py:12862`
  - `truffles-api/app/services/reasoning_core.py:12874`
  - `truffles-api/app/core/booking_prompt_owner.py:500`
  - `truffles-api/app/core/dialog_state_service.py:872`
  - `truffles-api/app/core/dialog_state_service.py:1323`
- **Five Whys:**
  1. Why does turn `002-09` still hand off? Because the touched family can still reach the explicit handoff owner while pending booking continuity is active.
  2. Why can explicit handoff still win? Because the early explicit handoff edge remains executable before the canonical continuity owner fully asserts authority, and the terminal fallback edge still exists for the same family.
  3. Why does turn `002-10` then route through `safe_info_fact`? Because the early info owner only defers when the sparse live snapshot says `booking_active + reply_slot in {service,time}`, not when centralized pending booking boundary state still owns continuity.
  4. Why is continuity still weak enough to drift? Because touched finalize still depends on `context_manager_router._set_expected_reply_context(...)` instead of making `DialogStateService.build_expected_reply_context_sync_result(...)` the direct writer on the normal path.
  5. Why is replay-first invalid here? Because the old info/handoff seams are still executable, so another replay would only surface more rows without deleting the overlap.
- **Root cause statement:** the touched pending booking family still lacks one executable guarded authority chain before generic info and explicit handoff seams, and touched continuity persistence is still externally owned by the legacy expected-reply helper instead of direct `DialogStateService` sync.
- **Fix mechanism:** derive the centralized pending booking boundary once per turn, make `safe_info_fact` and non-explicit handoff edges defer when that boundary is active, bypass the terminal explicit handoff fallback for the touched family, replace touched finalize helper calls with direct `DialogStateService` sync, and delete at least one dead duplicate-family block from `reasoning_core.py` so duplicate debt goes down rather than being re-ledgered.

## Reuse-first plan (mandatory)
- Internal reuse:
  - `DialogStateService.derive_pending_booking_resume_boundary_payload(...)`
  - `resolve_pending_booking_reactivation_candidate(...)`
  - `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)`
  - `DialogStateService.build_expected_reply_context_sync_result(...)`
  - `context_manager_router._set_conversation_context(...)`
- External reuse:
  - `https://stately.ai/docs/guards`
- Why not reinvent the wheel: the existing dialog-state boundary seam and canonical booking owner already model the touched continuity contract; the block should reconnect them and delete overlap, not create another owner.

## Invariant
Do not touch frozen routers. Do not add semantic regex/phrase branching in `truffles-api/app/services/reasoning_core.py`. Do not run replay. Do not leave `safe_info_fact` or explicit handoff as the normal touched-family route.

## Scope
- make centralized pending booking boundary authoritative over early info/handoff seams
- make terminal explicit handoff fallback unreachable for the touched family
- make touched finalize use direct `DialogStateService` expected-reply sync instead of the legacy helper call path
- reduce duplicate executable def debt in `reasoning_core.py`
- add focused regressions and publish canon evidence

## Out of scope
- new replay
- frozen router edits
- unrelated owner families outside the touched pending booking / info / handoff chain
- prod rollout

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-info-handoff-authority-reset-structural-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-info-handoff-authority-reset-structural-implementation-a922.md`
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
1. Compute one centralized pending booking boundary payload before the direct-owner chain and use it to defer touched `safe_info_fact` and non-explicit handoff edges.
2. Remove touched-family dependence on the legacy expected-reply helper inside `_finalize_turn_planner_owner_cutover(...)` by applying direct `DialogStateService` sync plus the same trace/meta side effects.
3. Delete one dead duplicate-family block from `reasoning_core.py` so duplicate executable debt is reduced in the same block.
4. Add focused regressions for pending-boundary info deferral and for touched continuity sync without legacy helper calls.
5. Run deterministic checks and switch canon from the decision block to this implementation block.

## Exact Current Authority Chain
1. The direct-owner chain still executes `safe_info_fact` at `truffles-api/app/services/reasoning_core.py:12596` before early explicit handoff at `truffles-api/app/services/reasoning_core.py:12609`.
2. `safe_info_fact` only defers when `conversation_snapshot.booking_active` and `reply_slot in {service,time}` still hold at `truffles-api/app/services/reasoning_core.py:5697`-`truffles-api/app/services/reasoning_core.py:5704`.
3. The touched continuity owner stack only comes later at `truffles-api/app/services/reasoning_core.py:12781`, `truffles-api/app/services/reasoning_core.py:12794`, `truffles-api/app/services/reasoning_core.py:12807`, and `truffles-api/app/services/reasoning_core.py:12820`.
4. If those owners still return `None`, runtime builds the terminal unresolved snapshot at `truffles-api/app/services/reasoning_core.py:12862` and re-enters explicit handoff at `truffles-api/app/services/reasoning_core.py:12874`.
5. On the normal touched finalize path, expected-reply sync still routes through `context_manager_router._set_expected_reply_context(...)` at `truffles-api/app/services/reasoning_core.py:5132` and `truffles-api/app/services/reasoning_core.py:5154`.

## Exact Canonical Target Authority Chain
1. Live turn handling derives one centralized pending booking boundary payload before the direct-owner chain.
2. If that boundary is active, generic info must defer and only explicit user-request/frustration/reschedule handoff reasons may still bypass continuity.
3. The touched family then resolves through the existing booking continuity owners, culminating in `booking_prompt_owner` and its pending reactivation seam.
4. Touched expected-reply persistence is written directly by `DialogStateService.build_expected_reply_context_sync_result(...)` and then applied to conversation state/trace/meta.
5. `terminal_owner_unresolved` explicit handoff is no longer eligible while the touched pending booking boundary is active.

## Exact Delete-list
- Make the touched-family early explicit-handoff edge at `truffles-api/app/services/reasoning_core.py:12609` unreachable.
- Make the touched-family terminal fallback edge `truffles-api/app/services/reasoning_core.py:12862` -> `truffles-api/app/services/reasoning_core.py:12874` unreachable.
- Replace the narrow `safe_info_fact` continuity gate at `truffles-api/app/services/reasoning_core.py:5697`-`truffles-api/app/services/reasoning_core.py:5704` with centralized pending-boundary authority.
- Remove touched-family dependence on legacy expected-reply writes at `truffles-api/app/services/reasoning_core.py:5132` and `truffles-api/app/services/reasoning_core.py:5154`.
- Delete one dead duplicate-family block from `truffles-api/app/services/reasoning_core.py` so duplicate count is reduced, not just ledgered.

## Exact Continuity Writes To Centralize
- `expected_reply_type`
- `expected_reply_reason`
- `context_manager.current_goal`
- `session_memory.last_question_type`
- `session_memory.interaction_owner`
- `session_memory.interaction_resume_slot`
- `session_memory.unanswered_questions_count`

## Exact Fallback Edges That Must Not Be Normal Path
- `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved`
- `turn_planner.safe_info_fact.v1` while pending booking continuity still owns `service_choice` or `time`

## DoD
- touched pending booking continuity defers generic info and non-explicit handoff before canonical owner exhaustion
- touched finalize path no longer calls `context_manager_router._set_expected_reply_context(...)`
- duplicate executable def debt is reduced in `reasoning_core.py`
- focused deterministic tests are green
- canon points to this implementation block and truthfully records the structural change

## Work mode (mandatory)
`implementation`

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_collect_reactivation or pending_collect_reactivation_without_active_booking_snapshot or pending_boundary_promotions_interrupt or promotions_interrupt_and_resumes_time_collect or explicit_handoff_owner or terminal_unresolved"`
- `pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `git diff --check`

## Evidence
- focused pytest output
- `python3 -m py_compile` output
- packet build/check output
- architecture guard output
- `git diff --check` output
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-info-handoff-authority-reset-structural-implementation-a922.md`

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only structural block; no prod rollout in this block.
- **Go/no-go signals:** touched family no longer reaches info/handoff fallback in deterministic coverage, finalize no longer uses the legacy expected-reply helper, duplicate debt is lower, and guards are green.
- **Rollback:** revert the touched non-frozen files in this worktree if any deterministic check fails.
- **Post-release monitoring window:** not applicable until the later closure replay.

## Rollback
Revert the touched non-frozen files in this worktree and restore the previous duplicate guard allowances if deterministic proof fails.

## No-go
- no frozen-file edits
- no replay before deterministic proof
- no new semantic hardcode in `reasoning_core.py`
- no hidden fallback around touched info/handoff authority
- no threshold weakening or oracle downgrade

## Risks/blockers
- if the centralized pending boundary is absent from the live conversation for some turns, the block must report that residual gap instead of inventing a new branch
- deleting dead duplicate defs must stay bounded to shadowed code only
- the broader residual `terminal_owner_unresolved` cluster may still contain a second family after this touched block lands

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** broader duplicate debt remains in `reasoning_core.py`; `boundary_validator.py` remains pass-through; closure replay is still pending.
- **Why not in this block:** this block is bounded to pending booking continuity info/handoff authority only.
- **Risk if deferred:** future agents can still reopen replay-first mode or revive another local info/handoff branch around the same family.
- **Linked follow-up Task Package(s):** one fresh closure replay after deterministic proof; then another delete-first family only if residual closure evidence demands it.
- **Expiry/trigger to stop deferral:** before any new replay or any new semantic owner branch on the touched family.

## Next-block contract (mandatory)
- **Next block objective:** run one fresh closure replay only after deterministic proof that pending booking continuity now owns the touched family before info/handoff fallback.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_collect_reactivation or pending_collect_reactivation_without_active_booking_snapshot or pending_boundary_promotions_interrupt or promotions_interrupt_and_resumes_time_collect or explicit_handoff_owner or terminal_unresolved"`
- **Blocked-by conditions:** any failure in focused tests, duplicate guard, packet guard, or inability to prove the touched-family info/handoff seams are unreachable.
- **Owner role for closure:** Brain / Top Architect
