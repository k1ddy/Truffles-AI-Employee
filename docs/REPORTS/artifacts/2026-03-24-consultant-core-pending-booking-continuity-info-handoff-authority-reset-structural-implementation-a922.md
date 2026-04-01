# Report — 2026-03-24 Consultant Core Pending Booking Continuity Info Handoff Authority Reset Structural Implementation A922

## Scope executed
- restored pending booking continuity from centralized dialog-state boundary state inside `_build_conversation_snapshot(...)`
- precomputed the same pending booking boundary before the direct-owner chain and used it to defer generic info plus non-explicit explicit handoff edges
- replaced the touched normal-path expected-reply writer with direct `DialogStateService.build_expected_reply_context_sync_result(...)`
- deleted dead early greeting-family duplicate defs from `truffles-api/app/services/reasoning_core.py`
- ran focused deterministic tests plus architecture, packet, session, and diff guards

## FACT / INFERENCE / UNKNOWN
| Type | Statement | Evidence |
| --- | --- | --- |
| FACT | `_build_conversation_snapshot(...)` now restores touched booking continuity from centralized pending boundary state before live routing decisions reuse the snapshot. | `truffles-api/app/services/reasoning_core.py:702`, `truffles-api/app/services/reasoning_core.py:777`, `truffles-api/app/services/reasoning_core.py:786` |
| FACT | The direct-owner chain now derives one pending boundary payload up front, defers `safe_info_fact`, gates non-explicit explicit handoff, and skips terminal unresolved explicit handoff while that boundary is active. | `truffles-api/app/services/reasoning_core.py:12541`, `truffles-api/app/services/reasoning_core.py:12569`, `truffles-api/app/services/reasoning_core.py:12583`, `truffles-api/app/services/reasoning_core.py:12849` |
| FACT | The touched normal-path expected-reply writer no longer depends on `context_manager_router._set_expected_reply_context(...)`; it now uses direct `DialogStateService` sync and records the same trace/meta/session-memory side effects. | `truffles-api/app/services/reasoning_core.py:4998`, `truffles-api/app/services/reasoning_core.py:5003`, `truffles-api/tests/test_reasoning_core.py:17570`, `truffles-api/tests/test_reasoning_core.py:17782` |
| FACT | Dead early greeting-family duplicate defs were deleted, reducing duplicate debt to `22` duplicate top-level names across `141` defs / `119` unique names. | `truffles-api/app/services/reasoning_core.py:4255`, `truffles-api/app/services/reasoning_core.py:5261`, `truffles-api/tests/architecture/test_no_duplicate_core_defs.py:9` |
| INFERENCE | The touched pending booking / info / handoff family now has one deterministic guarded authority chain before fallback, so the next honest move is a single closure replay instead of another local runtime branch. | `truffles-api/tests/test_reasoning_core.py:8154`, `truffles-api/tests/test_reasoning_core.py:17570`, `docs/ACTIVE_PROGRAM.md:18` |
| UNKNOWN | A fresh closure replay has not been run in this block, so live closure for `r50` rows `002-09` and `002-10` is not yet proven on runtime parity. | `/tmp/booking_quality/a922-go2f-seed19-r50/responses.jsonl`, no new replay artifact in this block |

## Exact authority map
### Old path
1. `safe_info_fact` could execute before pending booking continuity owners because it only self-suppressed on a sparse live snapshot gate. Evidence: `truffles-api/app/services/reasoning_core.py:5641`.
2. Early explicit handoff still sat ahead of the pending booking continuity stack. Evidence: `truffles-api/app/services/reasoning_core.py:12583`.
3. Only after those seams did runtime reach the pending continuity owners. Evidence: `truffles-api/app/services/reasoning_core.py:12771`, `truffles-api/app/services/reasoning_core.py:12784`, `truffles-api/app/services/reasoning_core.py:12797`, `truffles-api/app/services/reasoning_core.py:12810`.
4. If those owners returned `None`, runtime reopened explicit handoff through terminal unresolved fallback. Evidence: `truffles-api/app/services/reasoning_core.py:12849`.
5. The touched normal finalize path still relied on the legacy expected-reply helper for continuity writes. Previous block evidence: `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-info-handoff-authority-decision-a922.md`.

### Target path
1. Snapshot construction and live turn handling both derive centralized pending booking boundary state before touched routing decisions. Evidence: `truffles-api/app/services/reasoning_core.py:777`, `truffles-api/app/services/reasoning_core.py:12541`.
2. If that boundary is active, `safe_info_fact` returns `None` and generic info cannot win ahead of booking continuity. Evidence: `truffles-api/app/services/reasoning_core.py:5666`.
3. While that boundary is active, non-explicit explicit handoff also returns `None`; only direct human-request / frustration / reschedule reasons may bypass continuity. Evidence: `truffles-api/app/services/reasoning_core.py:5416`, `truffles-api/app/services/reasoning_core.py:5426`, `truffles-api/app/services/reasoning_core.py:12583`.
4. The pending continuity owner stack then executes before terminal fallback, and terminal unresolved explicit handoff is skipped for the touched family. Evidence: `truffles-api/app/services/reasoning_core.py:12771`, `truffles-api/app/services/reasoning_core.py:12810`, `truffles-api/app/services/reasoning_core.py:12849`.
5. On the touched normal path, expected-reply persistence is written directly by `DialogStateService.build_expected_reply_context_sync_result(...)`. Evidence: `truffles-api/app/services/reasoning_core.py:5003`.

## Exact delete-list executed
- Replaced the narrow `safe_info_fact` continuity gate with centralized pending-boundary authority at `truffles-api/app/services/reasoning_core.py:5666`.
- Made the touched-family non-explicit early explicit-handoff path unreachable by gating it at both the helper and the direct-owner callsite. Evidence: `truffles-api/app/services/reasoning_core.py:5426`, `truffles-api/app/services/reasoning_core.py:12583`.
- Made the touched-family terminal unresolved explicit handoff unreachable whenever the pending booking boundary is active. Evidence: `truffles-api/app/services/reasoning_core.py:12849`.
- Removed touched-family dependence on the legacy expected-reply helper by switching `_finalize_turn_planner_owner_cutover(...)` to direct `DialogStateService` sync. Evidence: `truffles-api/app/services/reasoning_core.py:4998`.
- Deleted dead early greeting-family duplicate defs so duplicate debt dropped in the same block instead of being re-ledgered. Surviving defs: `truffles-api/app/services/reasoning_core.py:4255`, `truffles-api/app/services/reasoning_core.py:5261`.

## Exact lines proving the old seam is gone or unreachable for the touched family
- Pending boundary is restored into the runtime snapshot: `truffles-api/app/services/reasoning_core.py:777`-`truffles-api/app/services/reasoning_core.py:798`.
- Pending boundary is precomputed before the direct-owner chain: `truffles-api/app/services/reasoning_core.py:12541`-`truffles-api/app/services/reasoning_core.py:12547`.
- `safe_info_fact` now immediately defers when the pending boundary exists: `truffles-api/app/services/reasoning_core.py:5666`-`truffles-api/app/services/reasoning_core.py:5667`.
- Non-explicit early explicit handoff now defers while the pending boundary exists: `truffles-api/app/services/reasoning_core.py:5426`-`truffles-api/app/services/reasoning_core.py:5429`, `truffles-api/app/services/reasoning_core.py:12583`-`truffles-api/app/services/reasoning_core.py:12610`.
- Terminal unresolved explicit handoff is skipped while the pending boundary exists: `truffles-api/app/services/reasoning_core.py:12849`-`truffles-api/app/services/reasoning_core.py:12875`.
- Touched normal-path expected-reply sync now uses direct `DialogStateService` writes, and the regression asserts the legacy helper is not called on this path: `truffles-api/app/services/reasoning_core.py:4998`-`truffles-api/app/services/reasoning_core.py:5056`, `truffles-api/tests/test_reasoning_core.py:17782`-`truffles-api/tests/test_reasoning_core.py:17788`.

## Deterministic validation
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py truffles-api/tests/architecture/test_arch_guard_packet.py` -> `pass`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_boundary_promotions_interrupt or promotions_interrupt_and_resumes_time_collect or info_owner_defers_active_service_hours_interrupt_to_booking_prompt_owner or booking_prompt_owner_reactivates_pending_collect_without_active_booking_snapshot or explicit_handoff_owner or terminal_unresolved"` -> `18 passed, 194 deselected`
- `pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py` -> `1 passed`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py` -> `1 passed`
- `pytest -q truffles-api/tests/architecture` -> `19 passed`
- `python3 scripts/build_agent_packet.py` -> regenerated `docs/_generated/AGENT_PACKET.md` and `docs/_generated/AGENT_PACKET.json`
- `python3 scripts/build_agent_packet.py --check` -> `OK`
- `SESSION_AGENT=a922 scripts/session_check.sh` -> `Session OK`
- `git diff --check` -> `pass`

## Focused evidence
- `truffles-api/tests/test_reasoning_core.py:8154` proves the promotions interrupt path now defers to booking continuity when pending booking boundary state still owns the next slot.
- `truffles-api/tests/test_reasoning_core.py:17570` proves pending collect reactivation now goes through the booking prompt owner with boundary-projected continuity and without the legacy expected-reply helper.
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py:9` proves the duplicate ledger was reduced rather than silently grown.
- `truffles-api/tests/architecture/test_arch_guard_packet.py:31` proves canon now points to this structural block and to the closure-only next move.

## Truth after implementation
- The touched pending booking / info / handoff family no longer uses old `safe_info_fact` or non-explicit explicit handoff fallback as the normal path in deterministic coverage.
- The touched terminal unresolved explicit-handoff seam is unreachable while pending booking continuity is active.
- Touched normal-path continuity writes now go through `DialogStateService`.
- Duplicate executable debt in `reasoning_core.py` is lower than before this block.
- No replay was opened in this block.

## What is not yet proven
- Fresh runtime closure for `r50` is not yet proven; this block deliberately stopped at deterministic structural evidence.
- Broader residual `terminal_owner_unresolved` families outside this touched boundary may still exist and must be classified from fresh closure evidence, not guessed.

## Next admissible move
- `run_one_fresh_closure_replay_only_after_pending_booking_continuity_info_handoff_authority_reset_evidence`
