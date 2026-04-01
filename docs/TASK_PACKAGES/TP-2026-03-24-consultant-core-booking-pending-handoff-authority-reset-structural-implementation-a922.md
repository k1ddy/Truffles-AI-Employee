# TP-2026-03-24 Consultant Core Booking Pending Handoff Authority Reset Structural Implementation A922

## Title/goal
Delete the surviving booking/pending/handoff overlap that still lets the touched family fall out of `booking_prompt_owner` and into terminal explicit handoff fallback. The block makes one executable semantic owner for the pending booking reactivation contour, one continuity writer for its expected-reply state, and proves that replay is no longer the development driver for this family.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-demo-salon-seed19-r46-initial-booking-owner-reset-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-demo-salon-seed19-r46-initial-booking-owner-reset-runtime-implementation-a922.md`
- CA_ID `a922-go2f-seed19-r47-booking-pending-handoff-authority-reset-structural-family`

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org Python execution model name binding function definition`
- **Date/time (local):** `2026-03-24 09:16 +05:00`
- **Sources opened (from this query):** `https://docs.python.org/3.11/reference/executionmodel.html`
- **Found ready-made solutions:** the official Python execution model documents that top-level function definitions are name-binding operations. The later binding owns the live global name, so earlier duplicate defs are dead authority and should be deleted instead of preserved behind a ledger.
- **Decision:** `reuse` the Python execution-model fact as the justification for deleting dead duplicate owner defs instead of maintaining parallel executable seams in `reasoning_core.py`.
- **Why:** the touched family still depended on shadowed owner history plus a live terminal fallback seam. Deleting dead defs is required to reduce real authority overlap rather than merely documenting it.
- **Rejected options:** keep duplicate defs and add another local branch; continue replay-first and classify the next surfaced row; move the fix into frozen routers; weaken acceptance or downgrade the handoff fallback to a silent shortcut.

## Root cause (mandatory)
- **Symptom:** non-canonical partial replay `r47` surfaces a strict failure at `LLM-QUAL-a922-go2f-seed19-r47-002-09-5cf37a`: user asks `На какое время лучше записаться?`, expected booking collect continuity, actual path exits through `terminal_owner_unresolved` handoff.
- **Minimal reproduction:** inspect `/tmp/booking_quality/a922-go2f-seed19-r47/responses.jsonl` for `LLM-QUAL-a922-go2f-seed19-r47-002-09-5cf37a`, then trace the touched family through `truffles-api/app/services/reasoning_core.py` from `handle_webhook_payload(...)` into `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r47/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r47/runtime_state.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r47/responses.jsonl`
  - `truffles-api/app/services/reasoning_core.py:4706`
  - `truffles-api/app/services/reasoning_core.py:5292`
  - `truffles-api/app/services/reasoning_core.py:7442`
  - `truffles-api/app/services/reasoning_core.py:8230`
  - `truffles-api/app/services/reasoning_core.py:8411`
  - `truffles-api/app/services/reasoning_core.py:12681`
  - `truffles-api/app/services/reasoning_core.py:13203`
  - `truffles-api/app/services/reasoning_core.py:13245`
  - `truffles-api/app/core/booking_prompt_owner.py:406`
  - `truffles-api/app/routers/webhook/context_manager.py:292`
  - `truffles-api/tests/test_reasoning_core.py:17267`
  - `truffles-api/tests/architecture/test_no_duplicate_core_defs.py:9`
- **Five Whys:**
  1. Why did the touched replay row hand off instead of continuing booking collect? Because `booking_prompt_owner` returned `None` before it attempted a semantic collect candidate for a pending conversation with no active booking snapshot.
  2. Why did `booking_prompt_owner` return `None`? Because the live gate required `conversation_snapshot.booking_active` or `current_goal == "booking"` before building a candidate.
  3. Why was that gate wrong for this family? Because pending booking reactivation is still a booking continuity contour even when the snapshot is stale or incomplete.
  4. Why did the runtime escalate instead of recovering? Because the touched family still had no single executable authority for semantic routing plus continuity; once the gate returned `None`, the path could continue toward terminal explicit handoff fallback.
  5. Why did the old seam survive so long? Because duplicate top-level defs and legacy expected-reply sync helpers let the runtime preserve old authority history inside `reasoning_core.py` instead of forcing one canonical path.
- **Root cause statement:** the touched family failed because pending booking reactivation was not owned by one executable booking authority. `reasoning_core.py` still combined stale booking-entry gating, duplicated owner history, and a terminal explicit handoff fallback that remained reachable when continuity was incomplete.
- **Fix mechanism:** add one canonical pending booking reactivation candidate owner in `booking_prompt_owner.py`, route the touched family through it before any terminal fallback, keep expected-reply sync on the allowed continuity writer path `context_manager.py` backed by `DialogStateService`, and delete the dead duplicate top-level defs that preserved old owner overlap.

## FACT / INFERENCE / UNKNOWN
- **FACT:** `r47` is non-canonical forensic evidence only; `summary.json` records `infra_valid=true`, `semantic_valid=false`, and `stop_reason=signal_2`.
- **FACT:** the first surfaced strict failure is `LLM-QUAL-a922-go2f-seed19-r47-002-09-5cf37a`, which exits with `reason_code=terminal_owner_unresolved` and `owner_cutover=turn_planner.safe_explicit_handoff_owner.v1`.
- **FACT:** the touched family now has a canonical pending-reactivation helper at `truffles-api/app/core/booking_prompt_owner.py:406`, a single live `_finalize_turn_planner_owner_cutover(...)` at `truffles-api/app/services/reasoning_core.py:5292`, and reduced duplicate debt (`29` duplicate names across `148` top-level defs / `119` unique names).
- **INFERENCE:** the primary live defect was execution-model overlap, not another isolated replay row. If the touched family stayed on the old gate, more replay rows would keep surfacing without deleting the authority seam.
- **UNKNOWN:** whether `LLM-QUAL-a922-go2f-seed19-r47-002-10-02252e` is the same family continuation or a separate booking-to-info continuity split. This block does not overclaim that classification.

## Exact current authority chain
1. `truffles-api/app/services/reasoning_core.py:12681` `handle_webhook_payload(...)` drives owner cutover order.
2. The touched family reaches `truffles-api/app/services/reasoning_core.py:13203` `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)`.
3. Before this block, the owner returned `None` when neither `conversation_snapshot.booking_active` nor `current_goal == "booking"` was true.
4. The family then remained exposed to later fallback owners and finally to terminal explicit handoff fallback at `truffles-api/app/services/reasoning_core.py:13245` via `terminal_handoff_snapshot`.
5. Expected-reply persistence on the booking owner finalize path still routed through legacy helper `context_manager_router._set_expected_reply_context(...)` instead of one explicit `DialogStateService` sync owner.

## Exact canonical target authority chain
1. `truffles-api/app/services/reasoning_core.py:12681` `handle_webhook_payload(...)` still calls `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)` before terminal fallback.
2. `truffles-api/app/services/reasoning_core.py:8229` now resolves pending reactivation through `_resolve_turn_planner_pending_booking_reactivation_candidate(...)`.
3. `truffles-api/app/services/reasoning_core.py:4769` delegates that work to `truffles-api/app/core/booking_prompt_owner.py:406` `resolve_pending_booking_reactivation_candidate(...)`.
4. The owner finalizes through the single live `truffles-api/app/services/reasoning_core.py:5292` `_finalize_turn_planner_owner_cutover(...)`.
5. Expected-reply continuity now stays on `truffles-api/app/routers/webhook/context_manager.py:292` `_set_expected_reply_context(...)`, which calls `DialogStateService.build_expected_reply_context_sync_result(...)` before mutating conversation state.
6. The touched family returns from booking owner cutover before `truffles-api/app/services/reasoning_core.py:13245` terminal explicit handoff fallback can become the normal path.

## Exact delete-list
- Delete the dead duplicate top-level defs from `truffles-api/app/services/reasoning_core.py`:
  - `_is_turn_planner_safe_explicit_handoff_candidate`
  - `_build_turn_planner_owner_trace_payload`
  - `_finalize_turn_planner_owner_cutover`
  - `_try_handle_turn_planner_safe_explicit_handoff_owner_cutover`
  - `_try_handle_turn_planner_safe_check_booking_prompt_owner_cutover`
- Delete legacy expected-reply authority for the touched owner path by removing direct `context_manager_router._set_expected_reply_context(...)` calls from the live `_finalize_turn_planner_owner_cutover(...)` flow.
- Delete the stale pending-reactivation gate as the deciding authority for this family by making the owner call canonical pending reactivation candidate resolution instead of returning `None` immediately.

## Exact continuity writes to centralize
- `expected_reply_type`
- `expected_reply_reason`
- canonical dialog-state projection into conversation context
- `question_contract` trace entry
- `re_entry` clear side effect when required
- session-memory `question_set` update for the touched family
- booking payload persistence remains on `DialogStateService.set_context_booking_payload(...)` inside the same owner finalize path

## Exact fallback edges that must no longer be normal path
- `truffles-api/app/services/reasoning_core.py:13245` `terminal_handoff_snapshot = PolicyCoreRouteSnapshot(...)`
- `truffles-api/app/services/reasoning_core.py:5854` `_try_handle_turn_planner_safe_explicit_handoff_owner_cutover(...)` when reached from `terminal_owner_unresolved`
- `REASONING_CORE_TERMINAL_UNRESOLVED_REASON` as the touched family exit reason
- legacy `context_manager_router._set_expected_reply_context(...)` for touched-family owner finalize

## Reuse-first plan (mandatory)
- Internal reuse: keep `TurnPlanner`, `DialogStateService`, `_finalize_turn_planner_owner_cutover(...)`, `resolve_llm_booking_prompt_candidate(...)`, and the existing booking owner finalize flow.
- External reuse: `https://docs.python.org/3.11/reference/executionmodel.html`
- Why not reinvent the wheel: the work is owner deletion/delegation, not a new booking runtime.

## Invariant
Do not touch frozen routers. Do not add semantic hardcode in `reasoning_core.py`. Do not reopen replay before structural deletion/unreachability is proven. Do not weaken thresholds or acceptance gates.

## Scope
- touched booking/pending/handoff family only
- pending booking reactivation semantic owner cutover
- continuity writer centralization for the touched owner finalize path
- duplicate-def reduction for the touched family
- deterministic proof that terminal explicit handoff fallback is not the normal path for the touched family

## Out of scope
- classifying `r47` row `002-10` as same-family vs new-family beyond what code and artifact boundaries prove
- full replay closure
- prod floor remediation
- frozen-router extraction
- unrelated duplicate-def families in `reasoning_core.py`

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-booking-pending-handoff-authority-reset-structural-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-booking-pending-handoff-authority-reset-structural-implementation-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `STATE.md`
- `truffles-api/app/core/booking_prompt_owner.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Add one canonical pending booking reactivation candidate owner in `booking_prompt_owner.py`.
2. Route the touched family through that owner inside `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)` before terminal fallback.
3. Centralize touched-family expected-reply sync through `DialogStateService` in the live `_finalize_turn_planner_owner_cutover(...)`.
4. Delete the dead duplicate owner defs for the touched family from `reasoning_core.py` and reduce the explicit duplicate ledger.
5. Add deterministic regression coverage that fails if the touched family falls through terminal explicit handoff or legacy expected-reply helper seams.
6. Publish the canon update so future agents inherit delete-first authority reset instead of replay-first mode.

## DoD
- touched pending booking reactivation goes through one canonical owner path before any terminal fallback
- touched expected-reply sync in the live owner finalize path goes through the allowed continuity writer `truffles-api/app/routers/webhook/context_manager.py`
- touched dead duplicate defs are removed from `reasoning_core.py`
- duplicate-def count is reduced in reality and reflected in the architecture guard ledger
- focused deterministic tests prove the canonical owner path and the old seam unreachability for the touched family
- canon docs point future agents at this structural block instead of replay-first continuation

## Work mode (mandatory)
`implementation`

## Checks
- `python3 -m py_compile truffles-api/app/core/booking_prompt_owner.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py truffles-api/tests/architecture/test_arch_guard_packet.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_collect_reactivation or post_cancel_rebooking_state or explicit_handoff_owner or terminal_unresolved"`
- `pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `git diff --check`

## Evidence
- focused pytest output for the touched family and architecture guards
- `python3 -m py_compile` output
- `python3 scripts/build_agent_packet.py` / `--check` output
- `SESSION_AGENT=a922 scripts/session_check.sh` output
- exact code lines cited in this TP/report
- `/tmp/booking_quality/a922-go2f-seed19-r47/{summary.json,runtime_state.json,responses.jsonl}` as non-canonical forensic evidence only

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only structural implementation; no prod rollout in this block.
- **Go/no-go signals:** touched-family terminal fallback is unreachable under deterministic regression, duplicate debt is reduced, and canon docs no longer point agents back to replay-first continuation.
- **Rollback:** revert the touched non-frozen files in this worktree.
- **Post-release monitoring window:** not applicable until one fresh replay closure runs.

## Rollback
Revert the touched non-frozen files and restore the previous active block canon if deterministic checks fail.

## No-go
- no frozen-router edits
- no new semantic branch in `reasoning_core.py`
- no replay before structural proof
- no threshold weakening
- no silent fallback or ledger-only duplicate reduction

## Risks/blockers
- `LLM-QUAL-a922-go2f-seed19-r47-002-10-02252e` remains intentionally unclassified beyond `UNKNOWN`
- broader duplicate debt still remains in `reasoning_core.py`
- prod floor degradation remains outside this block

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** broader duplicate-def debt remains in `reasoning_core.py`; the terminal fallback seam still exists globally as a guard path; `r47` row `002-10` continuity classification remains open; prod floor remains degraded.
- **Why not in this block:** the owner requirement is one structural block for the touched booking/pending/handoff family only.
- **Risk if deferred:** if the broader duplicate debt or global fallback seam stays unaddressed too long, future families can still surface from the same hotspot even though this touched family is reset.
- **Linked follow-up Task Package(s):** one fresh closure replay block after this structural proof; then any new family TP only if the replay surfaces a genuinely different blocker.
- **Expiry/trigger to stop deferral:** immediate after the next fresh replay; if the touched family still reaches terminal fallback, the structural claim fails and the block must reopen.

## Next-block contract (mandatory)
- **Next block objective:** run exactly one fresh replay as closure, not discovery, after this structural evidence package is accepted.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_collect_reactivation or post_cancel_rebooking_state or explicit_handoff_owner or terminal_unresolved"`
- **Blocked-by conditions:** any regression in the touched-family tests, stale packet/source-of-truth canon, duplicate-def guard failure, or evidence that the touched family can still reach `terminal_owner_unresolved` before booking owner exhaustion.
- **Owner role for closure:** Brain / Top Architect
