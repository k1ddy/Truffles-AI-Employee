# Report — 2026-03-24 Consultant Core Booking Pending Handoff Authority Reset Structural Implementation A922

## Scope executed
- Added canonical pending booking reactivation candidate owner at `truffles-api/app/core/booking_prompt_owner.py:406`.
- Routed the touched pending booking contour through `truffles-api/app/services/reasoning_core.py:8229` so `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)` no longer returns `None` immediately when `booking_active=false` and `current_goal` is absent.
- Kept touched expected-reply sync on the allowed continuity writer path: the single live `_finalize_turn_planner_owner_cutover(...)` at `truffles-api/app/services/reasoning_core.py:5292` now routes through `truffles-api/app/routers/webhook/context_manager.py:292`, which applies `DialogStateService.build_expected_reply_context_sync_result(...)` for the touched owner path.
- Deleted the dead duplicate top-level defs for the touched family from `truffles-api/app/services/reasoning_core.py` and reduced the duplicate-def ledger in `truffles-api/tests/architecture/test_no_duplicate_core_defs.py:9`.
- Updated canon docs so future agents inherit the delete-first structural block instead of replay-first continuation.

## FACT / INFERENCE / UNKNOWN
| Type | Item |
|---|---|
| FACT | `r47` remains non-canonical forensic evidence only: `/tmp/booking_quality/a922-go2f-seed19-r47/summary.json` records `infra_valid=true`, `semantic_valid=false`, and `stop_reason=signal_2`. |
| FACT | The touched failure row is `LLM-QUAL-a922-go2f-seed19-r47-002-09-5cf37a`; its `decision_meta` exits with `reason_code=terminal_owner_unresolved` and `owner_cutover=turn_planner.safe_explicit_handoff_owner.v1`. |
| FACT | The touched family now resolves pending booking reactivation through `truffles-api/app/services/reasoning_core.py:4769` -> `truffles-api/app/core/booking_prompt_owner.py:406` before the live booking owner finalizes. |
| FACT | The live owner finalize path now keeps expected-reply continuity on the allowed writer `truffles-api/app/routers/webhook/context_manager.py:292`, invoked from `truffles-api/app/services/reasoning_core.py:5515` and `:5537`. |
| FACT | Duplicate debt is reduced to `29` duplicate top-level names across `148` defs / `119` unique names in `truffles-api/app/services/reasoning_core.py`. |
| INFERENCE | The primary blocker was execution-model overlap in booking/pending/handoff authority, not another row-level replay symptom. |
| UNKNOWN | Whether `LLM-QUAL-a922-go2f-seed19-r47-002-10-02252e` is the same family continuation or a separate info/continuity split remains intentionally unclaimed. |

## Authority map
### Old path
1. `truffles-api/app/services/reasoning_core.py:12681` `handle_webhook_payload(...)` reaches `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)`.
2. Before this block, the touched family could exit early when no active booking snapshot or `current_goal="booking"` was present.
3. The contour then remained exposed to later owner attempts and terminal fallback at `truffles-api/app/services/reasoning_core.py:13245` `terminal_handoff_snapshot = PolicyCoreRouteSnapshot(...)`.
4. Expected-reply continuity on the live owner finalize path still depended on legacy helper `context_manager_router._set_expected_reply_context(...)`.

### Target path
1. `truffles-api/app/services/reasoning_core.py:13203` still invokes `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)` before terminal fallback.
2. `truffles-api/app/services/reasoning_core.py:8229` now calls `_resolve_turn_planner_pending_booking_reactivation_candidate(...)`.
3. `truffles-api/app/services/reasoning_core.py:4769` delegates to `truffles-api/app/core/booking_prompt_owner.py:406` `resolve_pending_booking_reactivation_candidate(...)`.
4. The owner finalizes through the single live `_finalize_turn_planner_owner_cutover(...)` at `truffles-api/app/services/reasoning_core.py:5292`.
5. Continuity writes go through `truffles-api/app/routers/webhook/context_manager.py:292` `_set_expected_reply_context(...)`, which uses `DialogStateService.build_expected_reply_context_sync_result(...)`.
6. The touched family now returns a booking owner response before terminal explicit handoff fallback at `truffles-api/app/services/reasoning_core.py:13245` can become its normal route.

## Delete-list executed
- Removed the earlier dead duplicate defs from `truffles-api/app/services/reasoning_core.py`:
  - `_is_turn_planner_safe_explicit_handoff_candidate`
  - `_build_turn_planner_owner_trace_payload`
  - `_finalize_turn_planner_owner_cutover`
  - `_try_handle_turn_planner_safe_explicit_handoff_owner_cutover`
  - `_try_handle_turn_planner_safe_check_booking_prompt_owner_cutover`
- Removed touched live finalize-path dependency on direct `context_manager_router._set_expected_reply_context(...)`.
- Removed the stale pending-reactivation gate as the deciding authority for the touched family by resolving a canonical candidate instead of returning `None` immediately.

## Old seam unreachability proof for the touched family
- Booking owner still runs before the terminal fallback in `handle_webhook_payload(...)`: `truffles-api/app/services/reasoning_core.py:13203` precedes `truffles-api/app/services/reasoning_core.py:13245`.
- The touched family now has a canonical pending-reactivation branch at `truffles-api/app/services/reasoning_core.py:8229`; it adds `pending_collect_reactivation` trace/meta at `truffles-api/app/services/reasoning_core.py:8411`.
- Deterministic regression `truffles-api/tests/test_reasoning_core.py:17267` proves the touched pending contour returns `Turn planner safe booking prompt owner sent`, sets `pending_collect_reactivation=true`, and fails the test if:
  - terminal explicit handoff owner is called,
  - legacy `context_manager_router._set_expected_reply_context(...)` is called.
- That regression therefore proves the touched family no longer uses the old explicit-handoff fallback seam or the old expected-reply writer seam as its normal route.

## Deterministic validation
- `python3 -m py_compile truffles-api/app/core/booking_prompt_owner.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py truffles-api/tests/architecture/test_arch_guard_packet.py` -> `pass`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_collect_reactivation or post_cancel_rebooking_state or explicit_handoff_owner or terminal_unresolved"` -> `15 passed, 195 deselected`
- `pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py` -> `1 passed`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py` -> `1 passed`
- `python3 scripts/build_agent_packet.py` -> regenerated `docs/_generated/AGENT_PACKET.md` and `docs/_generated/AGENT_PACKET.json`
- `python3 scripts/build_agent_packet.py --check` -> `build_agent_packet: OK`
- `SESSION_AGENT=a922 scripts/session_check.sh` -> `Session OK`
- `git diff --check` -> `pass`

## Truth after implementation
- The touched booking/pending/handoff family no longer relies on the old gate that required `booking_active` or `current_goal="booking"` before attempting semantic collect recovery.
- The touched family now has one executable semantic owner for pending booking reactivation and one explicit expected-reply continuity writer in the live finalize path.
- The old duplicate-def authority for the touched family is reduced in reality, not only ledgered.
- Replay is no longer the development driver for this family; the next replay is closure-only.

## What is not yet proven
- One fresh replay is still required to close the touched family on live runtime evidence.
- This block does not classify `r47` row `002-10` beyond `UNKNOWN`.
- Broader duplicate debt and the global terminal fallback seam still exist outside the touched family.

## Next admissible move
- `run_one_fresh_closure_replay_only_after_booking_pending_handoff_authority_reset_evidence`
