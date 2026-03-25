# Report — 2026-03-24 Consultant Core Pending Booking Continuity Terminal Handoff Authority Reset Structural Implementation A922

## Scope executed
- Added centralized pending booking reactivation seeding in `truffles-api/app/core/booking_prompt_owner.py:94`.
- Routed `resolve_pending_booking_reactivation_candidate(...)` through that seed path in `truffles-api/app/core/booking_prompt_owner.py:490` so the canonical booking owner now receives a restored booking goal plus expected-reply contract before fallback.
- Kept the touched runtime entry on the existing non-frozen delegation seam in `truffles-api/app/services/reasoning_core.py:4323` and the pending reactivation callsite in `truffles-api/app/services/reasoning_core.py:7846`.
- Deleted the dead earlier duplicate top-level defs for:
  - `_try_handle_turn_planner_safe_info_owner_cutover`
  - `_try_handle_turn_planner_safe_booking_verification_owner_cutover`
  - `_try_handle_turn_planner_safe_specialist_followup_owner_cutover`
- Updated the duplicate-def guard ledger in `truffles-api/tests/architecture/test_no_duplicate_core_defs.py:9`.
- Added focused regressions in `truffles-api/tests/test_reasoning_core.py:58` and `truffles-api/tests/test_reasoning_core.py:17363`.

## FACT / INFERENCE / UNKNOWN
| Type | Statement | Evidence |
| --- | --- | --- |
| FACT | Pending booking reactivation now restores its seed from centralized dialog-state resume payloads before calling the canonical LLM booking owner. | `truffles-api/app/core/booking_prompt_owner.py:94`, `truffles-api/app/core/booking_prompt_owner.py:500` |
| FACT | The touched runtime path still enters pending reactivation before the terminal fallback chain. | `truffles-api/app/services/reasoning_core.py:7846`, `truffles-api/app/services/reasoning_core.py:12862` |
| FACT | The dead earlier duplicate defs for info owner, booking verification owner, and specialist follow-up owner are deleted. | `truffles-api/app/services/reasoning_core.py:5682`, `truffles-api/app/services/reasoning_core.py:6943`, `truffles-api/app/services/reasoning_core.py:8471` |
| FACT | Duplicate debt is reduced to `26` duplicate top-level names across `144` defs / `118` unique names. | local AST count on `truffles-api/app/services/reasoning_core.py` |
| FACT | Focused deterministic tests are green and explicit handoff fallback is blocked in the touched pending reactivation regression by assertion if reached. | `truffles-api/tests/test_reasoning_core.py:17363`, focused pytest output |
| INFERENCE | For the touched family, `terminal_owner_unresolved` is no longer the first available route once centralized continuity exists, because pending reactivation now reconstructs the booking collect contract before the fallback branch. | `truffles-api/app/core/booking_prompt_owner.py:94`, `truffles-api/tests/test_reasoning_core.py:17363` |
| UNKNOWN | Whether the broader residual `24` `terminal_owner_unresolved` rows in `r49` collapse entirely after one closure replay or still split into a second executable family outside this touched path. | requires one fresh closure replay after deterministic proof |

## Exact authority map
### Old path
1. Pending family entered `truffles-api/app/services/reasoning_core.py:7846`.
2. `resolve_pending_booking_reactivation_candidate(...)` could return `None` without restoring centralized continuity.
3. Runtime then continued through `booking_verification`, `check_booking_prompt`, `specialist_followup`, and `booking_prompt_owner` until terminal fallback at `truffles-api/app/services/reasoning_core.py:12862`.
4. The next info turn could then route through `safe_info_fact` because booking continuity was no longer projected as active.

### Target path
1. Pending family enters `truffles-api/app/services/reasoning_core.py:7846`.
2. `truffles-api/app/core/booking_prompt_owner.py:94` rebuilds the remembered booking boundary from centralized dialog-state continuity.
3. `truffles-api/app/core/booking_prompt_owner.py:500` calls the canonical booking owner with restored `current_goal='booking'` and the expected-reply contract.
4. The touched family returns through the existing booking prompt owner finalize path, which already writes continuity through `DialogStateService`.
5. Terminal explicit handoff fallback stays only as post-exhaustion guard logic outside the touched family path.

## Exact delete-list executed
- Deleted the dead earlier top-level `_try_handle_turn_planner_safe_info_owner_cutover` body from `truffles-api/app/services/reasoning_core.py`.
- Deleted the dead earlier top-level `_try_handle_turn_planner_safe_booking_verification_owner_cutover` body from `truffles-api/app/services/reasoning_core.py`.
- Deleted the dead earlier top-level `_try_handle_turn_planner_safe_specialist_followup_owner_cutover` body from `truffles-api/app/services/reasoning_core.py`.

## Exact lines proving the old seam is gone or unreachable for the touched family
- Centralized reactivation seed: `truffles-api/app/core/booking_prompt_owner.py:94`
- Canonical pending reactivation call with restored booking goal: `truffles-api/app/core/booking_prompt_owner.py:500`
- Runtime callsite before later owners and terminal fallback: `truffles-api/app/services/reasoning_core.py:7846`
- Terminal fallback still exists only after owner exhaustion: `truffles-api/app/services/reasoning_core.py:12862`
- Focused regression that fails if the touched family reaches explicit handoff fallback: `truffles-api/tests/test_reasoning_core.py:17363`

## Deterministic validation
- `python3 -m py_compile truffles-api/app/core/booking_prompt_owner.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py` -> `pass`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_booking_reactivation_candidate or pending_collect_reactivation or post_cancel_rebooking_state or promotions_interrupt_and_resumes_time_collect or explicit_handoff_owner or terminal_unresolved"` -> `17 passed, 194 deselected`
- `pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py` -> `1 passed`

## Focused evidence
- Direct boundary-restoration regression: `truffles-api/tests/test_reasoning_core.py:58`
- Touched-family runtime regression with explicit handoff fallback blocked by assertion: `truffles-api/tests/test_reasoning_core.py:17363`
- Existing continuity follow-up proof kept green: `truffles-api/tests/test_reasoning_core.py:7584`

## Truth after implementation
- The touched pending booking family now has one canonical reactivation seed path before fallback.
- The old touched-family duplicate debt is reduced again instead of only being re-ledgered.
- No replay was opened in this block.

## What is not yet proven
- Closure on the live `r49` family is not yet proven.
- The broader residual `terminal_owner_unresolved` cluster still needs one fresh replay as closure evidence.

## Next admissible move
- `run_one_fresh_closure_replay_only_after_pending_booking_continuity_terminal_handoff_authority_reset_evidence`
