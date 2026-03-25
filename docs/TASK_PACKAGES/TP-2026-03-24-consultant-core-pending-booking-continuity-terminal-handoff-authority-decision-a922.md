# TP-2026-03-24 Consultant Core Pending Booking Continuity Terminal Handoff Authority Decision A922

## Title/goal
Classify the failed `r49` closure replay into one exact delete-first authority map for the broader pending booking continuity / terminal handoff family, so the next runtime block removes the live old seam instead of iterating another replay-first micro-fix.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-booking-pending-handoff-authority-reset-closure-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-booking-pending-handoff-authority-reset-closure-replay-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-booking-pending-handoff-authority-reset-structural-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-booking-pending-handoff-authority-reset-structural-implementation-a922.md`

## Root cause (mandatory)
- **Symptom:** fresh closure replay `r49` is `infra_valid=true` but `semantic_valid=false`; pending booking turns still exit through `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved`, and a follow-up promotions turn exits through `turn_planner.safe_info_fact.v1` while booking continuity still expects `time`.
- **Minimal reproduction:** `/tmp/booking_quality/a922-go2f-seed19-r49/responses.jsonl` rows `LLM-QUAL-a922-go2f-seed19-r49-002-09-489e4e` and `LLM-QUAL-a922-go2f-seed19-r49-002-10-674439`.
- **Evidence:** `/tmp/booking_quality/a922-go2f-seed19-r49/{summary.json,brief.md,manual_audit.json,responses.jsonl}` plus live code paths in `truffles-api/app/services/reasoning_core.py`.
- **Five Whys:**
  1. Why did closure fail? Because the touched family still reaches `terminal_owner_unresolved` explicit handoff and then loses booking continuity on the next info turn.
  2. Why does it still reach that fallback? Because the canonical pending booking owners can still all return `None` before the terminal unresolved handoff snapshot is built.
  3. Why does the next info turn bypass booking progress? Because live `safe_info_fact` only defers when `conversation_snapshot.booking_active` and `reply_slot in {service,time}` are still present.
  4. Why is that continuity not authoritative? Because pending/handoff re-entry still depends on distributed state projection instead of one central pending booking continuity authority.
  5. Why is replay-first wrong here? Because the old seam is still alive in executable runtime, so another replay would only surface more rows without deleting the overlap.
- **Root cause statement:** the broader pending booking/check/cancel/resume family still has no single executable authority before `terminal_owner_unresolved`, and continuity is still weak enough that `safe_info_fact` can become the normal path after pending/handoff drift.
- **Fix mechanism:** define the exact current-vs-target authority chain, exact delete/unreachability list, exact continuity fields to centralize, and the first deterministic check for the follow-up structural implementation block.

## Invariant
Do not run a new replay. Do not add another local semantic branch in `reasoning_core.py`. Do not call closure success while `terminal_owner_unresolved` remains reachable on the touched family.

## Scope
- classify `r49` failure rows and the broader `terminal_owner_unresolved` cluster
- map exact current authority chain with line references
- map exact canonical target authority chain
- define exact delete-list and continuity centralization list for the follow-up runtime block

## Out of scope
- runtime implementation
- new replay
- acceptance promotion
- changes to frozen files

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-booking-pending-handoff-authority-reset-closure-replay-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `STATE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Freeze the failed closure truth: `r47` non-canonical, `r48` invalid preflight, `r49` fresh closure replay.
2. Classify the failed turns and the broader explicit-handoff cluster from artifacts plus code.
3. Write the exact delete-first authority map for the next structural block.
4. Switch canon to the decision block so the next agent cannot reopen replay-first mode.

## Exact Current Authority Chain
1. Main runtime owner chain still runs in `truffles-api/app/services/reasoning_core.py:12992` through `truffles-api/app/services/reasoning_core.py:13257`.
2. Early explicit handoff owner is still callable at `truffles-api/app/services/reasoning_core.py:12992`, before `pending_ack` at `truffles-api/app/services/reasoning_core.py:13004` and before pending booking owners.
3. Pending booking family owners currently sit at:
   - `booking_verification`: `truffles-api/app/services/reasoning_core.py:13164`
   - `check_booking_prompt`: `truffles-api/app/services/reasoning_core.py:13177`
   - `specialist_followup`: `truffles-api/app/services/reasoning_core.py:13190`
   - `booking_prompt_owner`: `truffles-api/app/services/reasoning_core.py:13203`
4. When those owners all return `None`, the runtime builds `PolicyCoreRouteSnapshot(... reason='terminal_owner_unresolved' ...)` at `truffles-api/app/services/reasoning_core.py:13245` and immediately re-enters `turn_planner.safe_explicit_handoff_owner.v1` at `truffles-api/app/services/reasoning_core.py:13257`.
5. Live `safe_info_fact` sits at `truffles-api/app/services/reasoning_core.py:6065` and only self-suppresses when `conversation_snapshot.booking_active` and `reply_slot in {service,time}` are both still present (`truffles-api/app/services/reasoning_core.py:6081`).

## Exact Canonical Target Authority Chain
1. Pending booking/check/cancel/resume turns must resolve through one canonical booking continuity owner stack before any `terminal_owner_unresolved` fallback exists on the path.
2. The canonical booking reactivation seam already exists in `truffles-api/app/core/booking_prompt_owner.py:406`; the next block must make the broader pending family reach that authority instead of falling through to `truffles-api/app/services/reasoning_core.py:13245`.
3. Continuity writes for the touched family must remain centralized on `truffles-api/app/routers/webhook/context_manager.py:292` -> `truffles-api/app/core/dialog_state_service.py:872` and become sufficient to protect subsequent info turns.
4. `turn_planner.safe_info_fact.v1` must not be a normal path while pending booking continuity still owns `expected_reply_type=service` or `expected_reply_type=time`.
5. `turn_planner.safe_explicit_handoff_owner.v1` remains valid only for explicit human/frustration/reschedule-missing-reference families, not for `terminal_owner_unresolved` on the touched family.

## Exact Delete-List
- Make the touched-family terminal fallback edge `truffles-api/app/services/reasoning_core.py:13245` -> `truffles-api/app/services/reasoning_core.py:13257` unreachable.
- Remove touched-family dependence on the distributed `conversation_snapshot.booking_active/reply_slot` absence that currently lets `truffles-api/app/services/reasoning_core.py:6065` answer `safe_info_fact` during active booking continuity.
- Remove any touched-family path where `booking_verification`, `check_booking_prompt`, `specialist_followup`, and `booking_prompt_owner` all return `None` before continuity reactivation is attempted.

## Exact Continuity Writes To Centralize
- `expected_reply_type`
- `expected_reply_reason`
- `pending_resume.expected_reply_type`
- `pending_resume.expected_reply_reason`
- `interaction_owner`
- `interaction_resume_slot`
- `last_question_type`
- `unanswered_questions_count`

## Exact Fallback Edges That Must Not Be Normal Path
- `turn_planner.safe_explicit_handoff_owner.v1` with `reason_code=terminal_owner_unresolved`
- `turn_planner.safe_info_fact.v1` while booking continuity still expects `service` or `time`

## DoD
- the closure failure is published truthfully with exact artifact evidence
- the current authority chain and target chain are written with exact line references
- the delete-list is exact enough that the next agent can implement without reopening replay-first mode
- the next block contract names one structural implementation family and its first deterministic check

## Work mode (mandatory)
`forensic`

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r49 --status done --strict-artifacts`
- `python3 - <<'PY'\nfrom pathlib import Path\nimport json, collections\nrows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-go2f-seed19-r49/responses.jsonl').read_text().splitlines()]\nexplicit=[r for r in rows if (r.get('decision_meta') or {}).get('consultant_core_runtime',{}).get('owner_cutover')=='turn_planner.safe_explicit_handoff_owner.v1']\nreasons=collections.Counter((r.get('decision_meta') or {}).get('consultant_core_runtime',{}).get('reason_code') for r in explicit)\nassert reasons['terminal_owner_unresolved']==24, reasons\nprint({'explicit_count': len(explicit), 'terminal_owner_unresolved': reasons['terminal_owner_unresolved']})\nPY`
- `python3 scripts/build_agent_packet.py --check`
- `pytest -q truffles-api/tests/architecture/test_arch_guard_packet.py`

## Evidence
- `docs/REPORTS/artifacts/2026-03-24-consultant-core-booking-pending-handoff-authority-reset-closure-replay-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r49/{summary.json,brief.md,manual_audit.json,responses.jsonl}`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/app/core/booking_prompt_owner.py`
- `truffles-api/app/routers/webhook/context_manager.py`
- `truffles-api/app/core/dialog_state_service.py`

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
- no closure claim while `terminal_owner_unresolved` remains reachable on the touched family

## Risks/blockers
- the `24` `terminal_owner_unresolved` rows may still split into multiple executable subfamilies inside the broader pending cluster
- `truffles-api/app/core/boundary_validator.py` remains pass-through debt and is not addressed here

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** live runtime seam still exists; boundary authority is still residual debt; global duplicate debt remains.
- **Why not in this block:** this block is decision-only.
- **Risk if deferred:** future agents could reopen replay-first mode or ship another local branch next to the same seam.
- **Linked follow-up Task Package(s):** `docs/TASK_PACKAGES/TP-2026-03-24-consultant-core-pending-booking-continuity-terminal-handoff-authority-reset-structural-implementation-a922.md`
- **Expiry/trigger to stop deferral:** before any next runtime edit or replay.

## Next-block contract (mandatory)
- **Next block objective:** execute one delete-first structural implementation that makes `terminal_owner_unresolved` unreachable for the touched family and preserves booking continuity across info turns.
- **First deterministic check command:** `python3 - <<'PY'\nfrom pathlib import Path\nimport json, collections\nrows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-go2f-seed19-r49/responses.jsonl').read_text().splitlines()]\nexplicit=[r for r in rows if (r.get('decision_meta') or {}).get('consultant_core_runtime',{}).get('owner_cutover')=='turn_planner.safe_explicit_handoff_owner.v1']\nreasons=collections.Counter((r.get('decision_meta') or {}).get('consultant_core_runtime',{}).get('reason_code') for r in explicit)\nassert reasons['terminal_owner_unresolved']==24, reasons\nprint({'explicit_count': len(explicit), 'terminal_owner_unresolved': reasons['terminal_owner_unresolved']})\nPY`
- **Blocked-by conditions:** missing delete-first implementation TP, missing one precise web search before code, or inability to prove touched-family seam unreachability.
- **Owner role for closure:** Brain / Top Architect
