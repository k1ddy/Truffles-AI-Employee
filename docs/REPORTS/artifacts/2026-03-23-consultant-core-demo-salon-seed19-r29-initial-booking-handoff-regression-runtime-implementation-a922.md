# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R29 Initial Booking Handoff Regression Runtime Implementation A922

## Scope
Bounded runtime repair for the initial-booking timeout regression surfaced by truthful replay `r29` on dialog `1`, turn `1`.

## Changes Landed
- Extended the executable later `_resolve_turn_planner_safe_llm_booking_prompt_candidate(...)` in `truffles-api/app/services/reasoning_core.py:7144` with `allow_timeout_recovery=True` support so policy-core `timeout` / `deadline_exceeded` can recover bounded initial booking collect instead of returning `None`.
- Added `_resolve_turn_planner_safe_initial_booking_timeout_collect_candidate(...)` in `truffles-api/app/services/reasoning_core.py:7507`; it reuses existing deterministic booking parsing and only recovers safe initial collect envelopes with grounded `service`.
- Updated the executable later `_try_handle_turn_planner_safe_initial_booking_prompt_owner_cutover(...)` in `truffles-api/app/services/reasoning_core.py:11881` to opt into timeout recovery, seed booking state from the recovered parser output, and emit observability fields `policy_core_mode=degraded_fallback`, `policy_core_degrade_reason=policy_error:timeout`, and `policy_core_guard_recovery=initial_booking_parser`.
- Added deterministic regressions in `truffles-api/tests/test_reasoning_core.py:8454` and `truffles-api/tests/test_reasoning_core.py:16921` covering both helper-level timeout recovery and the full `handle_webhook_payload(...)` path.

## Root Cause Locked Before Code
On a fresh initial-booking turn, the executable later booking-prompt candidate resolver had no bounded degraded fallback when `route_llm_policy_core(...)` timed out. That left the owner chain without a collect candidate, so the turn fell through to explicit handoff / terminal unresolved instead of seeding the same safe booking collect contract already known to the runtime.

## Deterministic Evidence
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "initial_booking_timeout or booking_prompt_candidate_recovers_initial_booking_timeout or post_cancel_rebooking_state or booking_prompt_owner_restores_snapshot_service_for_post_verification_reschedule or safe_check_booking_prompt_owner_bypasses_frozen_delegate or safe_check_booking_prompt_owner_repairs_repeated_reference_continuity_from_snapshot"`
- Result: `5 passed, 199 deselected`

## Partial Live Evidence
- Interrupted replay `/tmp/booking_quality/a922-go2f-seed19-r38` is now explicitly audited as non-canonical (`stop_reason=signal_15`, `dialogs_seen=2/10`).
- Before interruption, dialog `1` turns `1..15` were strict-green in `/tmp/booking_quality/a922-go2f-seed19-r38/responses.jsonl`.
- The original first blocker is repaired on that partial live evidence: dialog `1`, turn `1` now returns `booking_prompt` / `collect` with `expected_reply_type=time` and trace stage `turn_planner_safe_booking_prompt_owner` instead of explicit handoff.

## Outcome
The bounded non-frozen runtime fix is landed locally and deterministic coverage is green. Truthful closure is still pending because `r38` was interrupted and remains non-canonical; the next admissible move is one fresh replay on canonical runtime parity to classify the first surviving blocker after dialog `1` initial-booking repair.
