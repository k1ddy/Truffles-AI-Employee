# Report — 2026-03-24 Consultant Core Pending Post Cancel Rebooking Continuity Handoff Info Authority Reset Structural Implementation A922

## Scope executed
- made pending booking boundary derivation infer the next missing booking slot from active booking state when explicit expected-reply metadata is absent
- kept the existing direct-owner chain, but fed it the inferred boundary so generic info and non-explicit handoff now defer before canonical booking continuity exhausts
- deleted one dead duplicate semantic-arbitration top-level def from `truffles-api/app/services/reasoning_core.py`
- added focused deterministic regressions and ran the duplicate guard

## FACT / INFERENCE / UNKNOWN
| Type | Statement | Evidence |
| --- | --- | --- |
| FACT | `DialogStateService.derive_pending_booking_resume_boundary_payload(...)` now infers the resume slot from active booking state when explicit expected-reply metadata is missing. | `truffles-api/app/core/dialog_state_service.py:1369`, `truffles-api/app/core/dialog_state_service.py:1464` |
| FACT | The direct-owner chain still computes `pending_booking_resume_boundary_payload` before info/handoff routing, so the inferred boundary now reaches the existing deferral gates without adding a new semantic branch. | `truffles-api/app/services/reasoning_core.py:3893`, `truffles-api/app/services/reasoning_core.py:12127`, `truffles-api/app/services/reasoning_core.py:12155`, `truffles-api/app/services/reasoning_core.py:12169` |
| FACT | `safe_info_fact` remains blocked while the inferred boundary exists, and terminal unresolved explicit handoff still stays behind the `pending_booking_resume_boundary_payload is None` guard. | `truffles-api/app/services/reasoning_core.py:5227`, `truffles-api/app/services/reasoning_core.py:5252`, `truffles-api/app/services/reasoning_core.py:12435` |
| FACT | The dead earlier `_try_handle_turn_planner_safe_semantic_arbitration_owner_cutover(...)` top-level def is gone; duplicate debt is now `21` duplicate top-level names across `140` defs / `119` unique names. | `truffles-api/app/services/reasoning_core.py:8421`, `truffles-api/tests/architecture/test_no_duplicate_core_defs.py:9` |
| FACT | Focused deterministic regressions prove the touched family now reactivates booking continuity before semantic handoff and still defers promotions interrupts correctly. | `truffles-api/tests/test_dialog_state_service.py:700`, `truffles-api/tests/test_reasoning_core.py:8154`, `truffles-api/tests/test_reasoning_core.py:17369`, `truffles-api/tests/test_reasoning_core.py:17570` |
| INFERENCE | The touched family now has one executable authority chain before semantic/terminal handoff or later info fallback, so the next honest move is a single closure replay. | focused deterministic evidence above |
| UNKNOWN | A fresh replay has not yet been run after this structural block, so live closure of `r51` is not yet proven. | no new replay artifact in this block |

## Exact authority map
### Old path
1. If explicit expected-reply metadata and `booking.last_question` were missing, pending booking boundary derivation returned `None` even when booking state was still active.
2. Without that boundary, early explicit handoff and later terminal unresolved handoff remained eligible.
3. Once continuity was lost, the promo follow-up could exit through `safe_info_fact`.

### Target path
1. Active booking state itself can now infer the missing resume slot and expected reply for pending booking continuity.
2. The existing boundary payload is still computed before the direct-owner chain.
3. Existing info and handoff gates now see that inferred boundary and defer accordingly.
4. Canonical booking continuity owners still execute on the existing path; no new semantic owner branch was added.

## Exact delete-list executed
- Deleted the old dependency on explicit expected-reply metadata as the only way to derive pending booking boundary state. Evidence: `truffles-api/app/core/dialog_state_service.py:1365`-`truffles-api/app/core/dialog_state_service.py:1375`.
- Deleted the dead earlier `_try_handle_turn_planner_safe_semantic_arbitration_owner_cutover(...)` top-level def from `truffles-api/app/services/reasoning_core.py`; the surviving executable def is now only at `truffles-api/app/services/reasoning_core.py:8421`.
- Kept the touched-family early explicit-handoff and terminal-handoff seams behind the existing `pending_booking_resume_boundary_payload is None` gates. Evidence: `truffles-api/app/services/reasoning_core.py:12169`-`truffles-api/app/services/reasoning_core.py:12183`, `truffles-api/app/services/reasoning_core.py:12435`.
- Kept `safe_info_fact` behind the same inferred boundary. Evidence: `truffles-api/app/services/reasoning_core.py:5252`.

## Exact lines proving the old seam is gone or unreachable for the touched family
- Boundary inference from active booking gap: `truffles-api/app/core/dialog_state_service.py:1369`-`truffles-api/app/core/dialog_state_service.py:1375` and `truffles-api/app/core/dialog_state_service.py:1464`-`truffles-api/app/core/dialog_state_service.py:1475`.
- Boundary payload is still precomputed before the direct-owner chain: `truffles-api/app/services/reasoning_core.py:12127`-`truffles-api/app/services/reasoning_core.py:12133`.
- `safe_info_fact` now defers whenever that inferred boundary exists: `truffles-api/app/services/reasoning_core.py:5252`-`truffles-api/app/services/reasoning_core.py:5253`.
- Non-explicit early handoff stays behind the same boundary guard: `truffles-api/app/services/reasoning_core.py:12169`-`truffles-api/app/services/reasoning_core.py:12183`.
- Terminal unresolved explicit handoff remains unreachable while the inferred boundary exists: `truffles-api/app/services/reasoning_core.py:12435`.
- The dead duplicate semantic-arbitration def is removed: surviving executable definition only at `truffles-api/app/services/reasoning_core.py:8421`.

## Deterministic validation
- `python3 -m py_compile truffles-api/app/core/dialog_state_service.py truffles-api/app/services/reasoning_core.py truffles-api/tests/test_dialog_state_service.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py` -> `pass`
- `pytest -q truffles-api/tests/test_dialog_state_service.py -k "pending_resume_boundary"` -> `2 passed, 56 deselected`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_prompt_owner_reactivates_pending_post_cancel_rebooking_state or infers_post_cancel_rebooking_boundary_before_semantic_handoff or pending_boundary_promotions_interrupt or explicit_handoff_owner or terminal_unresolved"` -> `17 passed, 196 deselected`
- `pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py` -> `1 passed`

## Focused evidence
- `truffles-api/tests/test_dialog_state_service.py:700` proves boundary inference now works from active booking state alone.
- `truffles-api/tests/test_reasoning_core.py:17570` proves post-cancel rebooking reactivates booking continuity before semantic handoff when explicit expected-reply metadata is absent.
- `truffles-api/tests/test_reasoning_core.py:8154` proves the later promo interrupt still defers to booking continuity.
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py:9` proves duplicate executable debt went down in the same block.

## Truth after implementation
- The touched post-cancel rebooking family no longer depends on explicit expected-reply metadata to derive continuity.
- The touched family now reaches the existing boundary guards before info fallback or handoff fallback can win.
- Duplicate executable debt is lower than before this block.
- No replay was opened in this block.

## What is not yet proven
- Fresh runtime closure on the `r51` artifact remains unproven until one new closure replay runs.
- Broader residual `terminal_owner_unresolved` families outside this touched family may still exist.

## Next admissible move
- `run_one_fresh_closure_replay_only_after_pending_post_cancel_rebooking_continuity_handoff_info_authority_reset_evidence`
