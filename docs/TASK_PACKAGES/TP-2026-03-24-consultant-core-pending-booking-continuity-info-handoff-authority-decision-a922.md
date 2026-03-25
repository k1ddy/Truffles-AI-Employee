# TP-2026-03-24 Consultant Core Pending Booking Continuity Info Handoff Authority Decision A922

## Title/goal
Classify the failed `r50` closure replay into one exact delete-first authority map for the broader pending booking continuity / info / handoff family, so the next runtime block removes the still-live old seams instead of reopening replay-first or another hotspot micro-fix.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-structural-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-structural-implementation-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-closure-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-closure-replay-a922.md`

## Root cause (mandatory)
- **Symptom:** fresh closure replay `r50` is `infra_valid=true` but `semantic_valid=false`; pending booking turns still exit through `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved`, and the next promo turn still exits through `turn_planner.safe_info_fact.v1` while booking continuity still expects `time`.
- **Minimal reproduction:** `/tmp/booking_quality/a922-go2f-seed19-r50/responses.jsonl` rows `LLM-QUAL-a922-go2f-seed19-r50-002-09-48c6ab` and `LLM-QUAL-a922-go2f-seed19-r50-002-10-4439b1`.
- **Evidence:** `/tmp/booking_quality/a922-go2f-seed19-r50/{summary.json,brief.md,manual_audit.json,responses.jsonl,trace_bundle.jsonl}` plus the live authority chain in `truffles-api/app/services/reasoning_core.py`, `truffles-api/app/core/booking_prompt_owner.py`, and `truffles-api/app/core/dialog_state_service.py`.
- **Five Whys:**
  1. Why did closure fail? Because the touched family can still route through explicit handoff or info owners before canonical booking continuity takes authority.
  2. Why can that still happen after the structural reset? Because `safe_info_fact` and early explicit handoff still run before the pending booking continuity owner stack.
  3. Why does the next promo turn bypass booking progress? Because `safe_info_fact` only defers on `conversation_snapshot.booking_active` with `reply_slot in {service,time}`, not on the centralized pending booking boundary payload.
  4. Why is continuity still weak enough to drift? Because finalize still writes expected-reply state through legacy `context_manager_router._set_expected_reply_context(...)` before `DialogStateService.build_collect_owner_state(...)` becomes authoritative.
  5. Why is replay-first invalid here? Because the old info/handoff seams are still executable on the normal path, so another replay would only surface more rows without deleting overlap.
- **Root cause statement:** the broader pending booking continuity family still has no single executable authority before `safe_info_fact` and `safe_explicit_handoff_owner`, and continuity persistence is still split between legacy context-manager writes and DialogStateService projections.
- **Fix mechanism:** define the exact old-vs-target authority chain, exact delete/unreachability list, exact continuity fields to centralize, and the first deterministic check for the follow-up structural implementation block.

## Invariant
Do not run a new replay. Do not add another local semantic branch in `truffles-api/app/services/reasoning_core.py`. Do not claim closure while the touched family can still route through `safe_info_fact` or `safe_explicit_handoff_owner` before canonical booking continuity exhausts.

## Scope
- classify `r50` failure rows and the still-live explicit-handoff / info-owner cluster
- map exact current authority chain with line references
- map exact canonical target authority chain
- define exact delete-list and continuity centralization list for the follow-up runtime block

## Out of scope
- runtime implementation
- new replay
- acceptance promotion
- changes to frozen files

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-info-handoff-authority-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-closure-replay-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Freeze the failed closure truth for `r50` with exact artifact evidence.
2. Classify the failed turns and the broader explicit-handoff / info-owner cluster from artifacts plus code.
3. Write the exact delete-first authority map for the next structural block.
4. Switch canon to the decision block so the next agent cannot reopen replay-first mode.

## Exact Current Authority Chain
1. The live main path still executes `safe_info_fact` at `truffles-api/app/services/reasoning_core.py:12596` before early explicit handoff at `truffles-api/app/services/reasoning_core.py:12609` and before `pending_ack` at `truffles-api/app/services/reasoning_core.py:12621`.
2. The pending booking continuity owner stack only comes later:
   - `booking_verification`: `truffles-api/app/services/reasoning_core.py:12781`
   - `check_booking_prompt`: `truffles-api/app/services/reasoning_core.py:12794`
   - `specialist_followup`: `truffles-api/app/services/reasoning_core.py:12807`
   - `booking_prompt_owner`: `truffles-api/app/services/reasoning_core.py:12820`
3. The canonical pending reactivation seam sits inside `truffles-api/app/core/booking_prompt_owner.py:500`; it restores boundary continuity from `truffles-api/app/core/dialog_state_service.py:1323` through `truffles-api/app/core/booking_prompt_owner.py:94`, but only after the runtime reaches the later booking owner call.
4. If those owners all return `None`, the runtime still builds `terminal_handoff_snapshot` at `truffles-api/app/services/reasoning_core.py:12862` and re-enters `turn_planner.safe_explicit_handoff_owner.v1` at `truffles-api/app/services/reasoning_core.py:12874`.
5. Live `safe_info_fact` only self-suppresses when `conversation_snapshot.booking_active` and `reply_slot in {service,time}` still hold at `truffles-api/app/services/reasoning_core.py:5697`-`truffles-api/app/services/reasoning_core.py:5704`.
6. Turn-planner finalize still writes expected-reply state through legacy `context_manager_router._set_expected_reply_context(...)` at `truffles-api/app/services/reasoning_core.py:5132` / `truffles-api/app/services/reasoning_core.py:5154`, while `DialogStateService.build_collect_owner_state(...)` only follows at `truffles-api/app/services/reasoning_core.py:5146`.

## Exact Canonical Target Authority Chain
1. Pending booking continuity must be decided before `safe_info_fact` and before any explicit-handoff owner call whenever the centralized boundary payload says booking continuity is active.
2. The touched family must resolve through `DialogStateService.derive_pending_booking_resume_boundary_payload(...)` at `truffles-api/app/core/dialog_state_service.py:1323` and then through `booking_prompt_owner.resolve_pending_booking_reactivation_candidate(...)` at `truffles-api/app/core/booking_prompt_owner.py:500` before any fallback owner is considered.
3. `safe_info_fact` must defer whenever the pending booking boundary payload or canonical dialog-state projections still own the next booking question, not only when a sparse live snapshot happens to preserve `reply_slot`.
4. `safe_explicit_handoff_owner` remains valid only for explicit human/frustration/reschedule-reference families, not for unresolved booking continuity on the touched family.
5. Continuity writes for the touched family must become DialogStateService-owned first, with legacy context-manager expected-reply writes removed or made unreachable on the normal path.

## Exact Delete-List
- Make the touched-family early explicit-handoff edge at `truffles-api/app/services/reasoning_core.py:12609` unreachable.
- Make the touched-family terminal fallback edge `truffles-api/app/services/reasoning_core.py:12862` -> `truffles-api/app/services/reasoning_core.py:12874` unreachable.
- Replace the narrow `safe_info_fact` continuity gate at `truffles-api/app/services/reasoning_core.py:5697`-`truffles-api/app/services/reasoning_core.py:5704` so touched booking continuity is evaluated from the centralized boundary payload, not only `conversation_snapshot.reply_slot`.
- Remove touched-family dependence on legacy expected-reply writes at `truffles-api/app/services/reasoning_core.py:5132` and `truffles-api/app/services/reasoning_core.py:5154` as the normal continuity writer.

## Exact Continuity Writes To Centralize
- `expected_reply_type`
- `expected_reply_reason`
- `pending_resume.expected_reply_type`
- `pending_resume.expected_reply_reason`
- `booking.last_question`
- `context_manager.current_goal`
- `session_memory.last_question_type`
- `session_memory.interaction_owner`
- `session_memory.interaction_resume_slot`

## Exact Fallback Edges That Must Not Be Normal Path
- `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved`
- `turn_planner.safe_info_fact.v1` while pending booking continuity still owns `service_choice` or `time`

## DoD
- the failed closure is published truthfully with exact artifact evidence
- the current authority chain and target chain are written with exact line references
- the delete-list is exact enough that the next agent can implement without reopening replay-first mode
- the next block contract names one structural implementation family and its first deterministic check

## Work mode (mandatory)
`forensic`

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r50 --status done --strict-artifacts`
- `python3 - <<'PY'
from pathlib import Path
import json, collections
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-go2f-seed19-r50/responses.jsonl').read_text().splitlines() if line.strip()]
explicit=[r for r in rows if (r.get('decision_meta') or {}).get('consultant_core_runtime',{}).get('owner_cutover')=='turn_planner.safe_explicit_handoff_owner.v1']
reasons=collections.Counter((r.get('decision_meta') or {}).get('consultant_core_runtime',{}).get('reason_code') for r in explicit)
assert reasons['terminal_owner_unresolved']==24, reasons
print({'explicit_count': len(explicit), 'terminal_owner_unresolved': reasons['terminal_owner_unresolved']})
PY`
- `python3 scripts/build_agent_packet.py --check`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`

## Evidence
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-closure-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r50/{summary.json,brief.md,manual_audit.json,responses.jsonl,trace_bundle.jsonl}`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/booking_prompt_owner.py`
- `truffles-api/app/core/dialog_state_service.py`
- `truffles-api/app/core/turn_planner.py`
- `truffles-api/app/core/boundary_validator.py`

## Release safety (mandatory for non-doc changes)
- **Strategy:** docs/governance only; no runtime code changes.
- **Go/no-go signals:** canon reflects the failed closure truth and the next structural block is precise.
- **Rollback:** revert the docs/test packet changes.
- **Post-release monitoring window:** not applicable.

## Rollback
Revert the new decision canon if the authority map or artifact facts are wrong.

## No-go
- no new replay
- no runtime micro-fix in `truffles-api/app/services/reasoning_core.py`
- no closure claim while the touched family can still route through `safe_info_fact` or `safe_explicit_handoff_owner` before canonical booking continuity exhausts

## Risks/blockers
- the artifact does not directly reveal whether row `002-09` used the early or terminal explicit-handoff invocation edge
- the exact snapshot field missing on row `002-10` is runtime-data dependent and not directly materialized in the artifact
- `truffles-api/app/core/boundary_validator.py` remains pass-through debt and is not addressed in this decision block

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** live old seams still exist; boundary authority is still residual debt; global duplicate debt remains.
- **Why not in this block:** this block is decision-only.
- **Risk if deferred:** future agents can reopen replay-first mode or add another local branch next to the same seams.
- **Linked follow-up Task Package(s):** `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-info-handoff-authority-reset-structural-implementation-a922.md`
- **Expiry/trigger to stop deferral:** before any next runtime edit or replay.

## Next-block contract (mandatory)
- **Next block objective:** execute one delete-first structural implementation that makes the touched family unreachable from early/terminal explicit handoff and from `safe_info_fact` until canonical booking continuity is exhausted.
- **First deterministic check command:** `python3 - <<'PY'
from pathlib import Path
import json, collections
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-go2f-seed19-r50/responses.jsonl').read_text().splitlines() if line.strip()]
explicit=[r for r in rows if (r.get('decision_meta') or {}).get('consultant_core_runtime',{}).get('owner_cutover')=='turn_planner.safe_explicit_handoff_owner.v1']
reasons=collections.Counter((r.get('decision_meta') or {}).get('consultant_core_runtime',{}).get('reason_code') for r in explicit)
assert reasons['terminal_owner_unresolved']==24, reasons
print({'explicit_count': len(explicit), 'terminal_owner_unresolved': reasons['terminal_owner_unresolved']})
PY`
- **Blocked-by conditions:** missing delete-first implementation TP, missing one precise web search before code, or inability to prove touched-family seam unreachability.
- **Owner role for closure:** Brain / Top Architect
