# Report — 2026-03-24 Consultant Core Pending Booking Reentry Booking Prompt Authority Reset Structural Implementation A922

## Scope executed
- moved touched booking reentry authority to `booking_prompt_owner` before the old direct-owner info / explicit-handoff seams
- centralized artifact fast-path continuity sync inside `_finalize_turn_planner_owner_cutover(...)`
- persisted booking payload on the same service-grounded promotions tool-reply path
- deleted two dead duplicate top-level defs from `reasoning_core.py`
- added focused deterministic regressions and ran duplicate / architecture guards

## FACT / INFERENCE / UNKNOWN
| Type | Statement | Evidence |
| --- | --- | --- |
| FACT | `booking_prompt_owner` now executes before touched catalog/info direct-owner seams in the main chain. | `truffles-api/app/services/reasoning_core.py:12053`, `truffles-api/app/services/reasoning_core.py:12119`, `truffles-api/app/services/reasoning_core.py:12132` |
| FACT | `_finalize_turn_planner_owner_cutover(...)` now applies centralized continuity sync on the artifact fast path through `DialogStateService.build_expected_reply_context_sync_result(...)` instead of letting that path skip expected-reply persistence. | `truffles-api/app/services/reasoning_core.py:4273`, `truffles-api/app/services/reasoning_core.py:4324` |
| FACT | The service-grounded promotions interrupt path now computes the contract and passes booking payload persistence into the centralized finalizer. | `truffles-api/app/services/reasoning_core.py:6968`, `truffles-api/app/services/reasoning_core.py:7160` |
| FACT | The dead earlier `_try_handle_turn_planner_safe_catalog_fact_owner_cutover(...)` and `_try_handle_turn_planner_safe_service_query_fact_owner_cutover(...)` top-level defs are gone; duplicate debt is now `19` duplicate top-level names across `138` defs / `119` unique names. | `truffles-api/app/services/reasoning_core.py:5134`, `truffles-api/app/services/reasoning_core.py:5221`, `truffles-api/tests/architecture/test_no_duplicate_core_defs.py:9` |
| FACT | Focused deterministic regressions prove touched booking reentry now preempts explicit handoff and service-grounded promotions preserves `expected_reply_type=time`. | `truffles-api/tests/test_reasoning_core.py:7388`, `truffles-api/tests/test_reasoning_core.py:7830`, `truffles-api/tests/test_reasoning_core.py:8397`, `truffles-api/tests/test_reasoning_core.py:18212` |
| INFERENCE | The touched family now has one executable continuity authority before old explicit handoff or later info fallback can win, so the next honest move is one fresh closure replay. | focused deterministic evidence below |
| UNKNOWN | A fresh replay has not yet been run after this structural block, so live closure of `r52` is not yet proven. | no new replay artifact in this block |

## Exact authority map
### Old path
1. Touched booking reentry could still reach old direct-owner seams before `booking_prompt_owner`.
2. Even when service-grounded promotions answered through `catalog.service_query`, the artifact fast path did not sync `expected_reply_type` or persist booking payload.
3. Once continuity was lost, row `002-09` could still fall into explicit handoff and row `002-10` could still fall into `safe_info_fact`.

### Target path
1. `booking_prompt_owner` now executes before the touched catalog/info seams in the direct-owner chain.
2. Service-grounded promotions tool replies persist continuity through `_finalize_turn_planner_owner_cutover(...)` -> `DialogStateService.build_expected_reply_context_sync_result(...)`.
3. Booking payload is persisted on that same path.
4. Old explicit handoff and later info fallback stay behind canonical owner exhaustion.

## Exact delete-list executed
- Deleted the old direct-owner ordering that let touched booking reentry miss `booking_prompt_owner` before catalog/info seams. Evidence: `truffles-api/app/services/reasoning_core.py:12053`, `truffles-api/app/services/reasoning_core.py:12119`, `truffles-api/app/services/reasoning_core.py:12132`.
- Deleted the artifact fast-path continuity-loss seam by centralizing context sync in `_finalize_turn_planner_owner_cutover(...)`. Evidence: `truffles-api/app/services/reasoning_core.py:4273`, `truffles-api/app/services/reasoning_core.py:4324`.
- Deleted the dead earlier `_try_handle_turn_planner_safe_catalog_fact_owner_cutover(...)` and `_try_handle_turn_planner_safe_service_query_fact_owner_cutover(...)` duplicate defs; the surviving executable defs remain only at `truffles-api/app/services/reasoning_core.py:5134` and `truffles-api/app/services/reasoning_core.py:5221`.

## Exact lines proving the old seam is gone or unreachable for the touched family
- `booking_prompt_owner` now runs before touched catalog/info seams: `truffles-api/app/services/reasoning_core.py:12053` before `truffles-api/app/services/reasoning_core.py:12119` and `truffles-api/app/services/reasoning_core.py:12132`.
- Fast-path continuity sync now happens centrally on artifact finalization: `truffles-api/app/services/reasoning_core.py:4273`-`truffles-api/app/services/reasoning_core.py:4324`.
- Service-grounded promotions now carry the resolved contract and booking payload into the centralized finalizer: `truffles-api/app/services/reasoning_core.py:6968`-`truffles-api/app/services/reasoning_core.py:7168`.
- The touched regressions fail if explicit handoff or missing continuity returns: `truffles-api/tests/test_reasoning_core.py:7388`, `truffles-api/tests/test_reasoning_core.py:8397`, `truffles-api/tests/test_reasoning_core.py:18212`.

## Deterministic validation
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py` -> `pass`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_booking_reentry_preempts_explicit_handoff_without_boundary_payload or answers_service_grounded_promotions_interrupt_and_advances_to_time or booking_prompt_owner_reactivates_pending_collect_without_active_booking_snapshot or booking_prompt_owner_answers_promotions_interrupt_and_resumes_time_collect or pending_boundary_promotions_interrupt or explicit_handoff_owner or terminal_unresolved or pending_ack_continuity_family_clears_pending_before_terminal_unresolved"` -> `19 passed, 196 deselected`
- `pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py` -> `1 passed`
- `pytest -q truffles-api/tests/architecture` -> `19 passed`
- `python3 scripts/build_agent_packet.py` -> regenerated `docs/_generated/AGENT_PACKET.md` and `docs/_generated/AGENT_PACKET.json`
- `python3 scripts/build_agent_packet.py --check` -> `OK`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py` -> `1 passed`
- `SESSION_AGENT=a922 scripts/session_check.sh` -> `Session OK`
- `git diff --check` -> `pass`

## Focused evidence
- `truffles-api/tests/test_reasoning_core.py:18212` proves touched booking reentry preempts explicit handoff without boundary payload.
- `truffles-api/tests/test_reasoning_core.py:7388` proves service-grounded promotions now advances to `expected_reply_type=time`.
- `truffles-api/tests/test_reasoning_core.py:7830` and `truffles-api/tests/test_reasoning_core.py:8397` prove the broader promotions continuity family still defers to booking continuity.
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py:9` proves duplicate executable debt went down in the same block.

## Truth after implementation
- Touched booking reentry no longer bypasses `booking_prompt_owner` before the nearby direct-owner seams.
- Service-grounded promotions tool replies no longer skip centralized continuity sync on the normal path.
- Duplicate executable debt is lower than before this block.
- No replay was opened in this block.

## What is not yet proven
- Fresh runtime closure on the `r52` family remains unproven until one new closure replay runs.
- Broader residual fallback families outside this touched block may still exist.

## Next admissible move
- `run_one_fresh_closure_replay_only_after_pending_booking_reentry_booking_prompt_authority_reset_evidence`
