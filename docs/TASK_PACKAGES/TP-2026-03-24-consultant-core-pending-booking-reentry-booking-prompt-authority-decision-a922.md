# TP-2026-03-24 Consultant Core Pending Booking Reentry Booking Prompt Authority Decision A922

## Title/goal
Classify the failed `r53` closure replay into one exact delete-first authority map for the pending booking reentry / booking-prompt family, so the next runtime block deletes the live initial-booking bypass and invalid-schema reactivation seams instead of reopening replay-first mode.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-reentry-booking-prompt-authority-reset-closure-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r53/{summary.json,brief.md,manual_audit.json,responses.jsonl,scenarios.json,failure_families.json}`

## Root cause (mandatory)
- **Symptom:** fresh closure replay `r53` is `infra_valid=true` but `semantic_valid=false`; rows `002-09`, `003-01`, and `006-01` still exit through explicit handoff with `terminal_owner_unresolved`, while rows `002-10` and `003-02` still answer promo/price facts without preserving the booking follow-up contract.
- **Minimal reproduction:** `/tmp/booking_quality/a922-go2f-seed19-r53/responses.jsonl` rows `LLM-QUAL-a922-go2f-seed19-r53-002-09-bf0a7d`, `002-10-864323`, `003-01-f32c28`, `003-02-a02bfb`, `006-01-0835dc`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r53/{summary.json,brief.md,manual_audit.json,responses.jsonl,scenarios.json,failure_families.json}`
  - current code map from `truffles-api/app/services/reasoning_core.py:6457`, `truffles-api/app/services/reasoning_core.py:12095`, `truffles-api/app/services/reasoning_core.py:12307`, `truffles-api/app/core/booking_prompt_owner.py:284`, `truffles-api/app/services/policy_validation_boundary_service.py`, `truffles-api/app/routers/webhook/decision.py:14342`
- **Five Whys:**
  1. Why did rows `003-01` and `006-01` still hand off? Because pending-state initial booking entry still missed canonical booking ownership before early explicit handoff.
  2. Why did initial booking entry miss canonical ownership? Because `booking_prompt_owner` still returns `None` when `conversation_snapshot is None`, and `initial_booking_prompt_owner` still sits later in the chain than early explicit handoff.
  3. Why did row `002-09` still hand off? Because pending service-choice reactivation still depends on `resolve_llm_booking_prompt_candidate(...)`, which currently rescues only timeout/deadline failures and drops recoverable `invalid_schema` collect payloads.
  4. Why did rows `002-10` and `003-02` still lose booking continuity? Because the collect contract was never restored on the prior turn, so later promo/price interrupts ran through generic fact owners without a live `expected_reply_type=time` contract.
  5. Why is replay-first invalid here? Because the same old explicit-handoff seam stays executable until both booking-entry owners run before handoff and invalid-schema reactivation gets a canonical boundary recovery.
- **Root cause statement:** the touched family still has split authority on pending-state booking entry: initial booking entry can still bypass canonical booking ownership before early explicit handoff, and pending service-choice reactivation still drops recoverable `invalid_schema` collect payloads because turn-planner has no reused policy-validation boundary path for them.
- **Fix mechanism:** move `initial_booking_prompt_owner` ahead of early explicit handoff on the pending booking entry family, and reuse the existing non-frozen policy-validation boundary recovery path so pending booking reactivation can turn recoverable `invalid_schema` collect payloads into canonical booking prompts before the same handoff seam.

## Invariant
Do not run another replay. Do not add phrase/regex semantic branching. Do not add new semantic branches to `reasoning_core.py` outside extraction/delegation/order changes. Do not touch frozen routers.

## Scope
- classify the surviving `r53` family from artifact plus code
- map the exact current authority chain for pending initial-booking bypass + invalid-schema reactivation loss
- map the exact canonical target chain and delete-list for one structural block
- switch canon from the failed closure replay to the existing delete-first decision block

## Out of scope
- runtime implementation
- new replay
- frozen-file edits
- acceptance promotion

## Touch-list
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-reentry-booking-prompt-authority-reset-closure-replay-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-reentry-booking-prompt-authority-decision-a922.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Freeze the failed `r53` closure truth with exact artifact evidence.
2. Map the old chain that still lets pending initial booking entry bypass canonical booking ownership before early explicit handoff.
3. Map the invalid-schema reactivation seam that still drops recoverable collect payloads before canonical booking prompting.
4. Switch canon back to this delete-first decision block and lock one structural next move.

## Exact Current Authority Chain
1. The direct-owner chain calls `booking_prompt_owner` early, but that owner immediately returns `None` when `conversation_snapshot is None` at `truffles-api/app/services/reasoning_core.py:6457`.
2. Early explicit handoff still runs at `truffles-api/app/services/reasoning_core.py:12095` before `initial_booking_prompt_owner` is reached at `truffles-api/app/services/reasoning_core.py:12307`, so pending initial booking entry rows (`003-01`, `006-01`) still fall into `turn_planner.safe_explicit_handoff_owner.v1`.
3. For pending reactivation rows like `002-09`, `_resolve_turn_planner_pending_booking_reactivation_candidate(...)` at `truffles-api/app/services/reasoning_core.py:3697` still delegates to `resolve_pending_booking_reactivation_candidate(...)`, which in turn depends on `resolve_llm_booking_prompt_candidate(...)`.
4. `resolve_llm_booking_prompt_candidate(...)` only rescues `timeout` / `deadline_exceeded` at `truffles-api/app/core/booking_prompt_owner.py:284`; recoverable `invalid_schema` collect payloads return `None`, so the touched turn falls through to the same early explicit handoff seam.
5. Once those turns miss booking ownership, later promo/price interrupts (`002-10`, `003-02`) execute through `safe_info_fact` / `safe_service_query_fact` without the booking continuity contract.

## Exact Canonical Target Authority Chain
1. Pending initial booking entry must reach canonical booking prompting before any explicit-handoff fallback.
2. Pending booking reactivation must reuse a canonical policy-validation recovery path when the semantic owner returns a recoverable `invalid_schema` collect payload.
3. The touched family must restore `expected_reply_type`, `expected_reply_reason`, and booking continuity before any promo/price interrupt can answer.
4. Old explicit handoff must stay unreachable until both booking-entry owners and boundary recovery are exhausted.

## Exact Delete-List
- Make early explicit handoff unreachable for pending initial booking entry by moving `initial_booking_prompt_owner` ahead of `truffles-api/app/services/reasoning_core.py:12095`.
- Make the current `conversation_snapshot is None` bypass non-fatal for touched booking entry by routing pending initial booking entry through canonical booking prompting before handoff fallback.
- Make recoverable `invalid_schema` pending reactivation stop returning `None` out of `resolve_llm_booking_prompt_candidate(...)`; reuse the existing non-frozen boundary recovery surface instead of falling into explicit handoff.
- Remove at least one dead duplicate top-level touched helper while this family is open, so duplicate executable debt goes down again before any future replay.

## Exact Continuity Writes To Centralize
- `expected_reply_type`
- `expected_reply_reason`
- `booking.service`
- `booking.datetime`
- `booking.last_question`
- service-hint continuity for service-grounded booking entry

## Exact Fallback Edges That Must Not Be Normal Path
- `turn_planner.safe_explicit_handoff_owner.v1` on pending initial booking entry before initial booking owner exhaustion
- `turn_planner.safe_explicit_handoff_owner.v1` on pending service-choice reactivation before boundary recovery exhaustion
- `turn_planner.safe_info_fact.v1` / `turn_planner.safe_service_query_fact.v1` while the touched booking contract still owns `expected_reply_type=time`

## DoD
- failed closure is published truthfully with exact `r53` evidence
- current-vs-target authority map is precise enough for one structural implementation block
- delete-list makes the next block delete-first, not replay-first
- canon points back to this decision block with one exact next move

## Work mode (mandatory)
`forensic`

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r53 --status done --strict-artifacts`
- `python3 scripts/build_agent_packet.py --check`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`

## Evidence
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-reentry-booking-prompt-authority-reset-closure-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r53/{summary.json,brief.md,manual_audit.json,responses.jsonl,scenarios.json,failure_families.json}`

## Release safety (mandatory for non-doc changes)
- **Strategy:** docs/governance only; no runtime code changes in this block.
- **Go/no-go signals:** canon reflects the failed closure truth and the next structural block is precise.
- **Rollback:** revert the doc/packet changes.
- **Post-release monitoring window:** not applicable.

## Rollback
Revert the new closure/decision canon if any artifact fact or authority-map line is wrong.

## No-go
- no new replay
- no runtime micro-fix in `truffles-api/app/services/reasoning_core.py`
- no closure claim while old pending booking entry / invalid-schema reactivation seams remain reachable

## Risks/blockers
- `r53` proves the family boundary is wider than `r52`, but still the same family; a fresh closure replay is still required after seam deletion to know whether another downstream family remains
- broader residual duplicate debt remains outside this bounded family

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** live old seams still exist; broader duplicate debt remains.
- **Why not in this block:** this block is decision-only.
- **Risk if deferred:** future agents can reopen replay-first mode or patch promo/price turns locally without deleting the live booking-entry overlap.
- **Linked follow-up Task Package(s):** one structural implementation block after one precise web search.
- **Expiry/trigger to stop deferral:** before any next runtime edit or replay.

## Next-block contract (mandatory)
- **Next block objective:** execute one delete-first structural implementation that (a) moves pending initial booking entry ahead of early explicit handoff and (b) reuses the existing policy-validation boundary recovery path so recoverable `invalid_schema` pending reactivation still emits a canonical booking prompt.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_initial_booking_preempts_explicit_handoff or pending_booking_reentry_preempts_explicit_handoff_without_boundary_payload or pending_invalid_schema_reactivation_keeps_booking_prompt or answers_service_grounded_promotions_interrupt_and_advances_to_time or explicit_handoff_owner or terminal_unresolved"`
- **Blocked-by conditions:** missing structural TP, missing one precise web search before code, or inability to prove the touched-family seams are unreachable.
- **Owner role for closure:** Brain / Top Architect
