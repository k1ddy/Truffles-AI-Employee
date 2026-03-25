# Report — 2026-03-24 Consultant Core Demo Salon Seed19 R46 Initial Booking Owner Reset Runtime Implementation A922

## Scope executed
- Created one canonical non-frozen booking-prompt candidate owner at `truffles-api/app/core/booking_prompt_owner.py:86`.
- Reduced the touched shadowed runtime debt in `truffles-api/app/services/reasoning_core.py`:
  - the live `_resolve_turn_planner_safe_llm_booking_prompt_candidate(...)` is now a thin wrapper at `truffles-api/app/services/reasoning_core.py:5578`
  - the dead duplicate `_resolve_turn_planner_safe_llm_booking_prompt_candidate(...)` body is deleted
  - the dead duplicate `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)` body is deleted
  - the dead duplicate `_try_handle_turn_planner_safe_initial_booking_prompt_owner_cutover(...)` body is deleted
- The fresh initial booking owner envelope is now booking-only on the canonical path:
  - `info_refs=[]` on fresh entry remains
  - `consult_refs=[]` is now applied on the same bounded fresh-entry path
  - explicit `max_tokens_override=160` remains scoped to that same path via `truffles-api/app/services/reasoning_core.py:183`
- Updated the duplicate-def guard ledger in `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`.
- Recorded the new canonical module in `STRUCTURE.md:116`.

## Deterministic validation
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_prompt_candidate or initial_booking_owner_recovers_timeout_before_terminal_handoff or service_only_timeout_before_terminal_handoff"` -> `7 passed, 202 deselected`
- `pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py` -> `1 passed`
- `python3 -m py_compile truffles-api/app/core/booking_prompt_owner.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py` -> `pass`
- `git diff --check` -> `pass`

## Focused evidence
- New focused service-only booking-only envelope regression:
  - `truffles-api/tests/test_reasoning_core.py:8752`
- New end-to-end service-only timeout recovery regression:
  - `truffles-api/tests/test_reasoning_core.py:17407`
- Probe artifacts:
  - `/tmp/booking_quality/a922-go2f-seed19-r46/initial_booking_owner_reset_service_only_probe.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r46/initial_booking_owner_reset_service_only_policy_core_raw_probe.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r46/initial_booking_owner_reset_service_only_detailed_probe.json`

## Truth after implementation
- The old shadowed authority is reduced for this family: the touched initial-booking owner family no longer keeps duplicate top-level defs for the live booking-prompt candidate / initial-owner / booking-owner surfaces.
- Fresh service-only initial booking entry is now routed through one canonical non-frozen owner module instead of duplicated `reasoning_core.py` bodies.
- The service-only local raw policy-core probe now shows booking-contract outputs when the model responds successfully, with `next_question='datetime'`, `open_questions=['datetime']`, and no pack/risk refs.
- The detailed probe also proves the old `timeout` shape is no longer the only local outcome on this path; current volatility now includes `invalid_json` responses from policy-core while the canonical owner stays contract-valid on successful responses.

## What is not yet proven
- Closure is not yet proven on the live replay surface.
- The detailed local probe still shows non-deterministic `invalid_json` failures on the service-only message, so another runtime replay is required to classify whether:
  - the old `r46` timeout/degraded row is closed, or
  - the family has truthfully changed shape into a different surviving blocker.

## Next admissible move
- `rerun_consultant_core_demo_salon_seed19_r46_initial_booking_owner_reset_canary_replay_to_completion`
