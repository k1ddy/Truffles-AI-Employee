# REPORT — 2026-03-23 Consultant Core Demo Salon Seed19 R23 Pending Reschedule Handoff Runtime Implementation A922

## Scope
Bounded runtime repair for the fresh `r23` blocker on dialog `2`, turn `9` (`На какое время лучше записаться?`).

## Truth fixed in this block
- Local direct policy-core probe for the surfaced turn produced a service-collect payload, not a handoff payload.
- The payload was being rejected by `_resolve_turn_planner_safe_llm_booking_prompt_candidate(...)` because it carried stale temporal follow-up metadata from the prior time discussion:
  - `capability=live_availability`
  - `resolution_mode=ask_about_requested_slot`
  - `pending_question_target=time`
  - `active_question_relation=ask_about_requested_slot`
- Once that candidate was rejected, the live owner chain fell through to terminal fallback and synthesized `policy_core_guard` / `handoff`.

## Implementation
- Updated the live booking-prompt candidate gate in `truffles-api/app/services/reasoning_core.py` to accept the bounded service-missing collect envelope when policy core echoes stale temporal follow-up metadata but `next_question=service` still matches the earliest missing booking slot.
- Mirrored the same normalization in the earlier duplicate helper definition so shadowed source does not immediately drift from the live helper body.
- Added deterministic regressions:
  - `truffles-api/tests/test_reasoning_core.py:8381`
  - `truffles-api/tests/test_reasoning_core.py:8454`

## Checks
- `python3 -m py_compile truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "stale_time_followup or keeps_temporal_booking_followup_when_service_still_missing or restores_snapshot_service_for_post_verification_reschedule or repeated_reference_continuity_from_snapshot"` → `4 passed`
- `python3 scripts/build_agent_packet.py` → `OK`
- `python3 scripts/build_agent_packet.py --check` → `OK`
- `python3 scripts/semantic_bridge_growth_guard.py` → `OK`
- `python3 scripts/continuity_writer_guard.py` → `OK`
- `python3 scripts/legacy_freeze_guard.py` → `OK`
- `python3 scripts/arch_guard.py` → `OK`
- `pytest -q truffles-api/tests/architecture` → `19 passed`
- `git diff --check` → `pass`
- `SESSION_AGENT=a922 scripts/session_check.sh` → `Session OK`

## Notes
- An exploratory broad selector (`-k "pending_reschedule or booking_prompt_owner or terminal_owner_unresolved"`) opened unrelated pre-existing/stale reds outside this family. It was not used as closure evidence for this block.
- Frozen routers stayed untouched.

## Next move
- `rerun_consultant_core_demo_salon_seed19_r23_pending_reschedule_handoff_canary_replay`
