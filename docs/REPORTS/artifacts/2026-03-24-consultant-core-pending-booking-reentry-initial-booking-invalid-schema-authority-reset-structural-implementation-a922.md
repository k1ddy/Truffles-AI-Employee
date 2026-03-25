# Consultant Core Pending Booking Reentry Initial Booking Invalid Schema Authority Reset Structural Implementation A922

## Result
- Structural block landed without replay.
- The touched family now exhausts initial booking ownership before early explicit handoff, and recoverable `invalid_schema` collect payloads now stay on the canonical booking prompt path.

## Scope
- move initial booking ownership ahead of early explicit handoff for the no-snapshot booking-entry family
- recover reusable invalid-schema collect payloads inside canonical booking prompting
- keep continuity writes on the existing booking prompt finalizer path
- reduce touched duplicate debt again

## FACT / INFERENCE / UNKNOWN
| Type | Statement | Evidence |
| --- | --- | --- |
| FACT | `initial_booking_prompt_owner` now runs before early explicit handoff in the direct-owner chain. | `truffles-api/app/services/reasoning_core.py:12058`, `truffles-api/app/services/reasoning_core.py:12085` |
| FACT | Recoverable `invalid_schema` booking collect payloads now reuse a shared policy-validation booking recovery helper and return a canonical booking prompt candidate instead of `None`. | `truffles-api/app/services/policy_validation_boundary_service.py:121`, `truffles-api/app/core/booking_prompt_owner.py:286`, `truffles-api/app/core/booking_prompt_owner.py:504` |
| FACT | Initial booking invalid-schema recovery now emits explicit guard observability instead of falling into terminal handoff. | `truffles-api/app/services/reasoning_core.py:8255` |
| FACT | The dead earlier `_should_accept_turn_planner_service_query_result(...)` duplicate def is deleted, reducing duplicate debt to `18` duplicate top-level names across `137` defs / `119` unique names. | `truffles-api/app/services/reasoning_core.py`, `truffles-api/tests/architecture/test_no_duplicate_core_defs.py` |
| FACT | Focused deterministic coverage is green: `18 passed, 199 deselected`; duplicate guard is green. | local test output from this block |
| INFERENCE | The old `r53` failure family is structurally cut over enough for one closure replay; replay-first discovery remains invalid. | deterministic proofs above |
| UNKNOWN | Whether rows `002-10` and `003-02` disappear completely once the fresh closure replay runs, or whether a smaller downstream continuity family remains. | no post-fix replay exists yet |

## Exact Authority Reset
### Old path
1. `booking_prompt_owner` could not claim the no-snapshot touched family.
2. Early explicit handoff executed before `initial_booking_prompt_owner`.
3. Recoverable `invalid_schema` booking collect payloads returned `None` and fell through.

### New path
1. `booking_prompt_owner` still claims live snapshot / pending-boundary turns first.
2. `initial_booking_prompt_owner` now executes before early explicit handoff for the touched no-snapshot family.
3. `resolve_llm_booking_prompt_candidate(...)` now converts recoverable `invalid_schema` booking collect payloads into the same canonical collect candidate used by the booking prompt owner.
4. `_finalize_turn_planner_owner_cutover(...)` remains the continuity writer for the touched family.

## Delete-First Evidence
- Early explicit handoff is no longer ahead of initial booking ownership for this family:
  - `truffles-api/app/services/reasoning_core.py:12058`
  - `truffles-api/app/services/reasoning_core.py:12085`
- Invalid-schema collect recovery no longer returns `None` for the touched family:
  - reusable recovery helper: `truffles-api/app/services/policy_validation_boundary_service.py:121`
  - candidate extraction: `truffles-api/app/core/booking_prompt_owner.py:286`
  - invalid-schema branch: `truffles-api/app/core/booking_prompt_owner.py:504`
- Initial booking observability now records invalid-schema recovery instead of silent fallthrough:
  - `truffles-api/app/services/reasoning_core.py:8255`
- Dead touched duplicate removed:
  - surviving executable `_should_accept_turn_planner_service_query_result(...)`: `truffles-api/app/services/reasoning_core.py:3944`

## Tests
- `python3 -m py_compile truffles-api/app/core/booking_prompt_owner.py truffles-api/app/services/reasoning_core.py truffles-api/app/services/policy_validation_boundary_service.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py` -> `pass`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_booking_reentry_preempts_explicit_handoff_without_boundary_payload or pending_invalid_schema_reactivation_keeps_booking_prompt or initial_booking_owner_recovers_invalid_schema_before_terminal_handoff or answers_service_grounded_promotions_interrupt_and_advances_to_time or explicit_handoff_owner or terminal_unresolved"` -> `18 passed, 199 deselected`
- `pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py` -> `1 passed`

## Evidence
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/booking_prompt_owner.py`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
