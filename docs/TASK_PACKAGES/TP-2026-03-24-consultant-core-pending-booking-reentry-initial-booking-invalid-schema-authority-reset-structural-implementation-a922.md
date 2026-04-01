# TP-2026-03-24 Consultant Core Pending Booking Reentry Initial Booking Invalid Schema Authority Reset Structural Implementation A922

## Title/goal
Delete the two live booking reentry seams surfaced by `r53`: move pending initial booking ownership ahead of early explicit handoff, and recover the touched family's reusable `invalid_schema` collect payload before the same fallback seam can fire.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-reentry-booking-prompt-authority-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-reentry-booking-prompt-authority-reset-closure-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r53/{summary.json,brief.md,manual_audit.json,responses.jsonl,scenarios.json,failure_families.json}`

## One web search (mandatory before implementation)
- Query: `Pydantic validation errors official docs`
- Date/time: `2026-03-24 19:07 +05`
- Opened sources:
  - `https://docs.pydantic.dev/latest/errors/errors/`
- Found reusable solution:
  - official Pydantic guidance treats validation errors as structured boundary data with machine-readable `errors()`, `error_count()`, `json()`, `loc`, and `type`, so recovery should consume validated error/payload structure instead of inventing text heuristics.
- Decision: `integrate`
  - reuse the existing local boundary surface in `truffles-api/app/services/policy_validation_boundary_service.py` and keep recovery driven by structured invalid-schema payload data, not by new phrase logic.
- Rejected alternatives:
  - `build`: adding a new ad-hoc invalid-schema parser in `reasoning_core.py` would violate delete-first / reuse-first.
  - `reuse as-is`: calling the frozen `decision.py` flow directly is not allowed and would reintroduce frozen authority overlap.
- Source quality:
  - high-signal official documentation: `docs.pydantic.dev`

## Root cause (mandatory)
- **Symptom:** fresh closure replay `r53` stayed `semantic_valid=false`; rows `002-09`, `003-01`, and `006-01` still hand off with `terminal_owner_unresolved`, and rows `002-10` plus `003-02` still answer promo/price facts without preserving booking continuity.
- **Minimal reproduction:** `/tmp/booking_quality/a922-go2f-seed19-r53/responses.jsonl` rows `LLM-QUAL-a922-go2f-seed19-r53-002-09-bf0a7d`, `002-10-864323`, `003-01-f32c28`, `003-02-a02bfb`, and `006-01-0835dc`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r53/{summary.json,brief.md,manual_audit.json,responses.jsonl,scenarios.json,failure_families.json}`
  - `truffles-api/app/services/reasoning_core.py:6457`
  - `truffles-api/app/services/reasoning_core.py:12095`
  - `truffles-api/app/services/reasoning_core.py:12307`
  - `truffles-api/app/core/booking_prompt_owner.py:284`
  - `truffles-api/app/services/policy_validation_boundary_service.py`
- **Five Whys:**
  1. Why do `003-01` and `006-01` still hand off? Because pending initial booking entry can still miss canonical booking ownership before early explicit handoff.
  2. Why can it miss canonical ownership? Because `booking_prompt_owner` still exits when `conversation_snapshot is None`, and `initial_booking_prompt_owner` still runs later than early explicit handoff.
  3. Why does `002-09` still hand off? Because pending reactivation still depends on `resolve_llm_booking_prompt_candidate(...)`, which only rescues timeout/deadline failures and drops recoverable `invalid_schema` collect payloads.
  4. Why do `002-10` and `003-02` still lose continuity? Because the booking collect contract was never restored on the prior turn, so promo/price owners run without an active `expected_reply_type=time` contract.
  5. Why is replay-first still invalid? Because the same old explicit-handoff seam stays executable until both booking-entry ownership and invalid-schema recovery are cut over structurally.
- **Root cause statement:** the touched family still has split authority: pending initial booking entry reaches early explicit handoff before exhausting initial booking ownership, and pending reactivation drops recoverable `invalid_schema` collect payloads instead of converting them into canonical booking prompting through a reusable validation boundary.
- **Fix mechanism:** reorder the direct-owner chain so initial booking prompting runs before early explicit handoff for the touched family, extract reusable invalid-schema collect recovery away from ad-hoc timeout-only handling, and route the recovered collect contract through the existing canonical booking prompt finalizer plus `DialogStateService` continuity writer.

## Invariant
- No new replay in this block.
- No frozen-file edits.
- No phrase/regex semantic branching.
- No new semantic branch in `truffles-api/app/services/reasoning_core.py`; only owner ordering, extraction, delegation, deletion, and observability.

## Scope
- move touched initial booking ownership ahead of early explicit handoff
- recover reusable invalid-schema booking collect payloads for pending reactivation
- keep continuity writes on the canonical booking prompt finalizer path
- reduce touched duplicate debt again before any next replay

## Out of scope
- new acceptance replay
- unrelated hotspot cleanup
- frozen router changes
- prod floor work

## Touch-list
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/booking_prompt_owner.py`
- `truffles-api/app/services/policy_validation_boundary_service.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-reentry-initial-booking-invalid-schema-authority-reset-structural-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-reentry-initial-booking-invalid-schema-authority-reset-structural-implementation-a922.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Exact current authority chain
1. `booking_prompt_owner` runs early, but `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)` returns `None` when `conversation_snapshot is None` at `truffles-api/app/services/reasoning_core.py:6457`.
2. Early explicit handoff still executes at `truffles-api/app/services/reasoning_core.py:12095` before `_try_handle_turn_planner_safe_initial_booking_prompt_owner_cutover(...)` is reached at `truffles-api/app/services/reasoning_core.py:12307`.
3. `resolve_pending_booking_reactivation_candidate(...)` delegates to `resolve_llm_booking_prompt_candidate(...)`, but that function only rescues timeout/deadline failures at `truffles-api/app/core/booking_prompt_owner.py:284`.
4. Recoverable `invalid_schema` collect payloads therefore return `None` and fall through to the same explicit handoff seam.
5. Promo/price follow-ups then execute through `safe_info_fact` / `safe_service_query_fact` without restored booking continuity.

## Exact canonical target authority chain
1. `booking_prompt_owner` keeps first claim on live pending-boundary turns with an active snapshot.
2. `initial_booking_prompt_owner` executes before early explicit handoff whenever the touched family has no live snapshot.
3. `resolve_llm_booking_prompt_candidate(...)` converts recoverable `invalid_schema` booking collect payloads into the same canonical collect contract used by the booking prompt owner.
4. `_finalize_turn_planner_owner_cutover(...)` remains the single continuity writer for the touched family.
5. Early explicit handoff and terminal unresolved fallback stay unreachable until both booking-entry owners and invalid-schema recovery are exhausted.

## Exact delete-list
- Move `_try_handle_turn_planner_safe_initial_booking_prompt_owner_cutover(...)` ahead of the early explicit handoff call in the direct-owner chain.
- Delete the timeout-only assumption in `resolve_llm_booking_prompt_candidate(...)` by extracting a reusable invalid-schema collect recovery path.
- Make `terminal_owner_unresolved` unreachable for touched pending booking reentry before canonical owner exhaustion.
- Delete the dead earlier `_should_accept_turn_planner_service_query_result(...)` top-level helper from `truffles-api/app/services/reasoning_core.py` while this family is open.

## Exact continuity writes to centralize
- `expected_reply_type`
- `expected_reply_reason`
- `booking.service`
- `booking.datetime`
- `booking.last_question`
- service-hint continuity for service-grounded booking reentry

## Exact fallback edges that must not be normal path
- `turn_planner.safe_explicit_handoff_owner.v1` before `initial_booking_prompt_owner` exhaustion on pending initial booking entry
- `turn_planner.safe_explicit_handoff_owner.v1` before invalid-schema collect recovery exhaustion on pending reactivation
- `turn_planner.safe_info_fact.v1` / `turn_planner.safe_service_query_fact.v1` while the touched family still owns `expected_reply_type=time`

## Plan (1..N)
1. Extract reusable invalid-schema collect recovery away from timeout-only fallback in `booking_prompt_owner`.
2. Reorder the direct-owner chain so initial booking ownership runs before early explicit handoff for the no-snapshot touched family.
3. Delete one dead duplicate touched helper in `reasoning_core.py`.
4. Add focused regressions for initial booking preemption, invalid-schema reactivation recovery, and downstream continuity preservation.
5. Publish structural evidence and switch canon only after deterministic checks are green.

## DoD
- touched initial booking entry can no longer reach early explicit handoff before initial booking owner exhaustion
- recoverable invalid-schema pending reactivation emits a canonical booking prompt instead of `None`
- continuity writes still go through the canonical booking prompt finalizer path
- touched duplicate debt is reduced, not only ledgered
- focused tests and required guards are green

## Work mode (mandatory)
`implementation`

## Checks
- `python3 -m py_compile truffles-api/app/core/booking_prompt_owner.py truffles-api/app/services/reasoning_core.py truffles-api/app/services/policy_validation_boundary_service.py truffles-api/tests/test_reasoning_core.py truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_booking_reentry_preempts_explicit_handoff_without_boundary_payload or pending_invalid_schema_reactivation_keeps_booking_prompt or initial_booking_owner_recovers_invalid_schema_before_terminal_handoff or answers_service_grounded_promotions_interrupt_and_advances_to_time or explicit_handoff_owner or terminal_unresolved"`
- `pytest -q truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- `git diff --check`

## Evidence
- deterministic test output
- updated canon docs
- structural report with exact lines proving old seams are gone or unreachable

## Release safety (mandatory for non-doc changes)
- **Strategy:** local structural cutover only; no replay or prod rollout in this block.
- **Go/no-go signals:** focused deterministic tests and architecture/session guards must all pass.
- **Rollback:** revert the touched files to the pre-block decision state.
- **Post-release monitoring window:** not applicable until a later closure replay.

## Rollback
Revert the touched files if the block leaves early explicit handoff reachable or breaks the canonical booking prompt path.

## No-go
- no new replay
- no frozen-file edits
- no new semantic branch in `reasoning_core.py`
- no local promo/price hardcode to mask missing booking continuity

## Risks/blockers
- `invalid_schema` payload recovery depends on `route_llm_policy_core(...)` still surfacing a payload dict; if that payload disappears on the local runtime, the block must stop and downgrade to a documented GAP
- downstream promo/price rows may still expose a smaller follow-up family after both seams are removed

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** broader duplicate debt and other non-touched owner overlaps remain in `reasoning_core.py`.
- **Why not in this block:** this block is intentionally bounded to the `r53` pending booking reentry family.
- **Risk if deferred:** future agents could still reopen adjacent families, but not this exact initial-booking / invalid-schema seam if the block lands correctly.
- **Linked follow-up Task Package(s):** one closure replay block after deterministic proof.
- **Expiry/trigger to stop deferral:** before any next replay.

## Next-block contract (mandatory)
- **Next block objective:** run exactly one fresh closure replay after the touched initial-booking and invalid-schema seams are proven unreachable.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k "initial_booking_owner_recovers_invalid_schema_before_terminal_handoff or pending_invalid_schema_reactivation_keeps_booking_prompt or explicit_handoff_owner or terminal_unresolved"`
- **Blocked-by conditions:** touched seams still reachable, duplicate debt not reduced, or deterministic checks not green.
- **Owner role for closure:** Brain / Top Architect
