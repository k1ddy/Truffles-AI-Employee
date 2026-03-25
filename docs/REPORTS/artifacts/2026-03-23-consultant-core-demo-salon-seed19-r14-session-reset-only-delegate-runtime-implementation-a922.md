# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R14 Session Reset Only Delegate Runtime Implementation A922

## Outcome
- Landed a bounded non-frozen runtime repair for exact reset-only control traffic.
- `reasoning_core.py` now recognizes exact reset-only messages and delegates them to the existing session-memory reset contract instead of letting the direct explicit-handoff owner consume them.
- The explicit-handoff owner now defers exact reset-only messages on both duplicated owner definitions.

## Code
- `truffles-api/app/services/reasoning_core.py`
  - imported `_is_session_reset_only_message`
  - added `_is_turn_planner_session_reset_only_message(...)`
  - added `_try_handle_turn_planner_safe_session_reset_only_delegate(...)`
  - inserted the reset-only delegate before the greeting/info/explicit-handoff owner chain
  - taught both explicit-handoff owner defs to defer exact reset-only control messages
- `truffles-api/tests/test_reasoning_core.py`
  - added direct defer regression for explicit-handoff owner
  - added full-path regression proving reset-only control traffic delegates past the owner shortcut

## Deterministic Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "session_reset_only_message or pending_ack_continuity_family_clears_pending_before_terminal_unresolved or explicit_handoff_owner_family_defers_pending_ack or greeting_owner_family_defers_pending_ack"` -> `5 passed, 194 deselected`

## Resulting Truth
- The old runtime blocker is closed locally: exact reset-only messages are no longer treated as explicit-handoff turns on the live non-frozen path.
- Fresh replay is still required to decide whether anything survives downstream on the seed-`19` canary path.
