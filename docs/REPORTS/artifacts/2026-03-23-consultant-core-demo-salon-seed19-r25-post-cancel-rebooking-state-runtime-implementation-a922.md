# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R25 Post-Cancel Rebooking State Runtime Implementation A922

## Scope
Bounded runtime repair for the post-cancel rebooking continuity defect surfaced by `r25` on dialog `2`, turn `8`.

## Changes Landed
- Added `_restore_turn_planner_collect_owner_bot_active_state(...)` in `truffles-api/app/services/reasoning_core.py:7465` so executable collect owners can reactivate `bot_active` before writing a new collect contract while stale pending/handover continuity survives.
- Applied that helper on the executable later booking collect owner path in `truffles-api/app/services/reasoning_core.py:10196` and recorded trace/meta evidence for `pending_collect_resume_boundary`.
- Applied the same helper on the executable later check-booking collect owner path in `truffles-api/app/services/reasoning_core.py:11305` so adjacent collect reentry keeps the same continuity contract.
- Added regression `truffles-api/tests/test_reasoning_core.py:16617` covering full `handle_webhook_payload(...)` reentry from `pending` with active handover preservation.

## Root Cause Locked Before Code
The executable booking collect owner could win the turn while the live conversation still carried stale `pending` / handover continuity, but it never reactivated the conversation before writing the new collect question contract. The row therefore kept `conversation_state='pending'` even though the collect action and expected-reply contract were already correct.

## Deterministic Evidence
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "post_cancel_rebooking_state or booking_prompt_owner_restores_snapshot_service_for_post_verification_reschedule or safe_check_booking_prompt_owner_bypasses_frozen_delegate or safe_check_booking_prompt_owner_repairs_repeated_reference_continuity_from_snapshot"`
- Result: `4 passed, 198 deselected`

## Outcome
The bounded non-frozen runtime fix is landed locally. The next admissible move is one fresh replay on the locked seed-`19` scenarios to verify that dialog `2`, turn `8` now exits `pending` and to classify the first surviving blocker after `r25`.
