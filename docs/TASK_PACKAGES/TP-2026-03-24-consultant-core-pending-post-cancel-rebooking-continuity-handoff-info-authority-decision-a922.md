# TP-2026-03-24 Consultant Core Pending Post Cancel Rebooking Continuity Handoff Info Authority Decision A922

## Title/goal
Classify the failed `r51` closure replay into one exact delete-first authority map for the pending post-cancel rebooking continuity family, so the next runtime block deletes the live semantic/terminal handoff seam and the later info fallback seam instead of reopening replay-first or another hotspot patch.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-info-handoff-authority-reset-structural-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-info-handoff-authority-reset-structural-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-info-handoff-authority-reset-closure-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r51/{summary.json,brief.md,manual_audit.json,responses.jsonl,scenarios.json,failure_families.json}`

## Root cause (mandatory)
- **Symptom:** fresh closure replay `r51` is `infra_valid=true` but `semantic_valid=false`; dialog `2` turn `9` still exits through `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved`, and turn `10` still exits through `turn_planner.safe_info_fact.v1` while booking continuity should still own the next question.
- **Minimal reproduction:** `/tmp/booking_quality/a922-go2f-seed19-r51/responses.jsonl` rows `LLM-QUAL-a922-go2f-seed19-r51-002-08-97382a`, `LLM-QUAL-a922-go2f-seed19-r51-002-09-c838ba`, and `LLM-QUAL-a922-go2f-seed19-r51-002-10-b85502`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r51/{summary.json,brief.md,manual_audit.json,responses.jsonl,scenarios.json,failure_families.json}`
  - `truffles-api/app/services/reasoning_core.py:8173`
  - `truffles-api/app/services/reasoning_core.py:7081`
  - `truffles-api/app/services/reasoning_core.py:9938`
  - `truffles-api/app/services/reasoning_core.py:12849`
  - `truffles-api/app/services/reasoning_core.py:5641`
  - `truffles-api/app/core/booking_prompt_owner.py:94`
  - `truffles-api/app/core/booking_prompt_owner.py:500`
  - `truffles-api/tests/test_reasoning_core.py:17369`
- **Five Whys:**
  1. Why does closure still fail on turn `002-09`? Because the post-cancel rebooking turn still reaches explicit handoff instead of a booking collect owner.
  2. Why does explicit handoff still win? Because the live pending reentry turn has no projected booking contract (`current_goal` / expected reply / boundary) before semantic arbitration and terminal fallback become eligible.
  3. Why does the canonical collect owner not reactivate first? Because the live turn does not pass the narrow verification-envelope gate in `safe_check_booking_prompt_owner`, and the later booking prompt reactivation path still lacks enough projected booking seed to claim authority before semantic handoff.
  4. Why does the next promo turn then go to `safe_info_fact`? Because once the booking question contract is absent, the promo/info owner is no longer suppressed by continuity state.
  5. Why is replay-first invalid here? Because the same live overlap between missing reentry continuity and old handoff/info seams is still executable on the normal path.
- **Root cause statement:** pending post-cancel rebooking continuity is still not projected/executable early enough on the live pending turn, so semantic arbitration handoff and terminal explicit handoff remain normal routes before canonical booking reactivation, and the follow-up promo turn then exits through `safe_info_fact` after the booking contract is already gone.
- **Fix mechanism:** define the exact old-vs-target authority chain for pending post-cancel rebooking reentry, the exact delete/unreachability list for semantic/terminal handoff plus later info fallback, and the continuity fields that must be restored before the next structural implementation block.

## Invariant
Do not run another replay. Do not add another local semantic branch in `truffles-api/app/services/reasoning_core.py`. Do not claim closure while post-cancel rebooking still routes through explicit handoff or later info fallback before canonical booking continuity exhausts.

## Scope
- classify the surviving `r51` failure family from artifact plus code
- map the exact current authority chain for pending post-cancel rebooking continuity collapse
- map the exact canonical target chain and delete-list for the next structural block
- switch canon from the failed closure replay to the new delete-first decision block

## Out of scope
- runtime implementation
- new replay
- frozen-file edits
- acceptance promotion

## Touch-list
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-info-handoff-authority-reset-closure-replay-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-post-cancel-rebooking-continuity-handoff-info-authority-decision-a922.md`
- `STATE.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Freeze the failed `r51` closure truth with exact artifact evidence.
2. Map the pending post-cancel rebooking family from the first live continuity collapse turn through the strict failures.
3. Write the exact delete-first authority map for the next structural implementation block.
4. Switch canon to this decision block so the next agent cannot reopen replay-first mode.

## Exact Current Authority Chain
1. Dialog `2` turn `8` already shows the live family entering `pending` without projected booking contract (`current_goal=None`, no expected reply) and exiting through `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=semantic_arbitration_needs_manager`.
2. `safe_check_booking_prompt_owner` only activates when `_looks_like_booking_verification_request(message_text)` succeeds at `truffles-api/app/services/reasoning_core.py:8173`-`truffles-api/app/services/reasoning_core.py:8181`, so the post-cancel rebooking utterance `Когда я могу записаться снова?` never reaches this owner.
3. `safe_booking_prompt_owner` tries to reactivate collect continuity after `_restore_turn_planner_collect_owner_bot_active_state(...)` at `truffles-api/app/services/reasoning_core.py:7081` and after pending reactivation seed construction at `truffles-api/app/core/booking_prompt_owner.py:94` / `truffles-api/app/core/booking_prompt_owner.py:500`, but the live turn still falls through before any collect owner reply is produced.
4. Semantic arbitration then routes `needs_manager` straight into explicit handoff at `truffles-api/app/services/reasoning_core.py:9938`-`truffles-api/app/services/reasoning_core.py:9960`.
5. When the next booking follow-up still lacks continuity, terminal unresolved explicit handoff remains reachable at `truffles-api/app/services/reasoning_core.py:12849`-`truffles-api/app/services/reasoning_core.py:12875`.
6. Once the question contract is missing, `safe_info_fact` remains executable for the promo follow-up at `truffles-api/app/services/reasoning_core.py:5641`-`truffles-api/app/services/reasoning_core.py:5667` and from the direct-owner chain at `truffles-api/app/services/reasoning_core.py:12569`-`truffles-api/app/services/reasoning_core.py:12580`.

## Exact Canonical Target Authority Chain
1. A pending post-cancel rebooking utterance must derive a canonical booking reentry seed before semantic arbitration or terminal fallback can claim authority.
2. That seed must restore `bot_active` via `manager_resolve(... preserve_context=True)` or equivalent state transition, and must preserve `current_goal='booking'` plus the expected booking question contract through `DialogStateService`.
3. The family must then resolve through the canonical booking continuity owners (`check_booking_prompt_owner` or `booking_prompt_owner`) before any handoff edge is eligible.
4. Only explicit human-request / frustration / reschedule-reference handoff reasons may still bypass continuity.
5. `safe_info_fact` must remain deferred while the reactivated booking question contract still owns the next slot.

## Exact Delete-List
- Make the semantic-arbitration explicit-handoff edge at `truffles-api/app/services/reasoning_core.py:9950` unreachable for the pending post-cancel rebooking family.
- Make the terminal explicit-handoff fallback edge `truffles-api/app/services/reasoning_core.py:12849` -> `truffles-api/app/services/reasoning_core.py:12875` unreachable for the same family.
- Remove the live gap that lets turn `002-08` bypass both canonical reentry owners just because it is not a narrow verification-envelope message.
- Keep `safe_info_fact` at `truffles-api/app/services/reasoning_core.py:5641` and `truffles-api/app/services/reasoning_core.py:12569` from becoming the normal follow-up path while rebooking continuity is still active.

## Exact Continuity Writes To Centralize
- `current_goal`
- `expected_reply_type`
- `expected_reply_reason`
- `pending_resume.expected_reply_type`
- `pending_resume.expected_reply_reason`
- `booking.active`
- `booking.last_question`
- `session_memory.last_question_type`
- `session_memory.interaction_owner`
- `session_memory.interaction_resume_slot`

## Exact Fallback Edges That Must Not Be Normal Path
- `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=semantic_arbitration_needs_manager` on pending post-cancel rebooking turns
- `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved` on the same family
- `turn_planner.safe_info_fact.v1` while post-cancel rebooking continuity still owns the next booking slot

## DoD
- the failed closure is published truthfully with exact `r51` evidence
- the current-vs-target authority map is precise enough for one structural implementation block
- the delete-list makes the next block delete-first, not replay-first
- canon points to this decision block and the next admissible move is structural, not replay

## Work mode (mandatory)
`forensic`

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r51 --status done --strict-artifacts`
- `python3 - <<'PY'
import json, collections
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-go2f-seed19-r51/responses.jsonl').read_text().splitlines() if line.strip()]
explicit=[r for r in rows if ((r.get('decision_meta') or {}).get('consultant_core_runtime') or {}).get('owner_cutover')=='turn_planner.safe_explicit_handoff_owner.v1']
reasons=collections.Counter(((r.get('decision_meta') or {}).get('consultant_core_runtime') or {}).get('reason_code') for r in explicit)
assert reasons['terminal_owner_unresolved']==23, reasons
print({'explicit_count': len(explicit), 'terminal_owner_unresolved': reasons['terminal_owner_unresolved']})
PY`
- `python3 scripts/build_agent_packet.py --check`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`

## Evidence
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-info-handoff-authority-reset-closure-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r51/{summary.json,brief.md,manual_audit.json,responses.jsonl,scenarios.json,failure_families.json}`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/booking_prompt_owner.py`
- `truffles-api/tests/test_reasoning_core.py`

## Release safety (mandatory for non-doc changes)
- **Strategy:** docs/governance only; no runtime code changes in this block.
- **Go/no-go signals:** canon reflects the failed closure truth and the next structural block is precise.
- **Rollback:** revert the doc/test packet changes.
- **Post-release monitoring window:** not applicable.

## Rollback
Revert the new closure/decision canon if any artifact fact or authority-map line is wrong.

## No-go
- no new replay
- no runtime micro-fix in `truffles-api/app/services/reasoning_core.py`
- no closure claim while post-cancel rebooking still routes through explicit handoff or later info fallback before canonical booking continuity exhausts

## Risks/blockers
- the artifact exposes the continuity loss clearly but does not itself reveal which upstream writer dropped the booking contract before turn `002-08`
- the surviving degraded fallback threshold on dialogs `6` and `8` remains residual runtime debt outside this decision block
- `boundary_validator.py` remains pass-through residual debt and is not addressed here

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** live old seams still exist; degraded-fallback threshold debt remains; global duplicate debt remains.
- **Why not in this block:** this block is decision-only.
- **Risk if deferred:** future agents can reopen replay-first mode or add another local branch around the same post-cancel rebooking seams.
- **Linked follow-up Task Package(s):** one structural implementation block after one precise web search.
- **Expiry/trigger to stop deferral:** before any next runtime edit or replay.

## Next-block contract (mandatory)
- **Next block objective:** execute one delete-first structural implementation that makes pending post-cancel rebooking continuity authoritative before semantic handoff, terminal handoff, and later info fallback.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_prompt_owner_reactivates_pending_post_cancel_rebooking_state or pending_boundary_promotions_interrupt or explicit_handoff_owner or terminal_unresolved"`
- **Blocked-by conditions:** missing structural TP, missing one precise web search before code, or inability to prove the touched-family handoff/info seams are unreachable.
- **Owner role for closure:** Brain / Top Architect
