# TP-2026-03-19-consultant-core-acceptance-preflight-l2-preflight-clear-state-contamination-family-package-a922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-ACCEPTANCE-PREFLIGHT-L2-PREFLIGHT-CLEAR-STATE-CONTAMINATION-FAMILY-PACKAGE-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-ACCEPTANCE-PREFLIGHT-L2-FROZEN-BOOKING-HANDOVER-REUSE-TARGETED-FROZEN-WAIVER-IMPLEMENTATION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-targeted-frozen-waiver-implementation-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-ACCEPTANCE-PREFLIGHT-L2-PREFLIGHT-CLEAR-STATE-CONTAMINATION-FAMILY-CLOSURE-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Lock the surviving `r23` blocker to one preflight-clear / reset-before-dialog state-contamination family. The block must prove why the fresh guarded rerun no longer fails on booking `hooks` yet still starts dialog 1 against stale continuity, converge the fix path onto one non-frozen owner family, and fail closed if the only truthful repair requires frozen `decision.py` edits, manual DB cleanup, or another compatibility seam.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-targeted-frozen-waiver-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/LEGACY_SUNSET.yaml`
- `ops/diagnose.py`
- `truffles-api/app/routers/webhook/decision.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r23/summary.json`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r23/brief.md`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r23/manual_audit.md`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r23/manual_audit.json`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r23/responses.jsonl`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r23/trace_bundle.jsonl`
- `/tmp/booking_quality/l2-acceptance-preflight-a922-r23/run_manifest.json`

## FACT pre-check (before implementation)
- `Impacted code/contracts/docs`:
  - `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-preflight-clear-state-contamination-family-package-a922.md`
  - `ops/diagnose.py`
  - `truffles-api/app/routers/webhook/session_memory.py`
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - `truffles-api/tests/test_state_service.py`
  - `truffles-api/tests/test_booking_quality_status_gate.py`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `STATE.md`
  - `STRUCTURE.md`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `python3 - <<'PY'
import json
from pathlib import Path
rows = [json.loads(line) for line in Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r23/responses.jsonl').read_text().splitlines()]
for row in rows:
    print(row['message_id'], row['conversation_id'], row['conversation_state'], row['turn_text'])
PY`
  - `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -Atqc "SELECT m.conversation_id, m.role, m.created_at, COALESCE(m.metadata->>'messageId',''), LEFT(COALESCE(m.content,''),120) FROM messages m JOIN conversations c ON c.id = m.conversation_id JOIN users u ON u.id = c.user_id WHERE c.client_id = 'c839d5dd-65be-4733-a5d2-72c9f70707f0' AND u.remote_jid = '77000000001@s.whatsapp.net' AND m.created_at >= '2026-03-19 11:08:30+00' ORDER BY m.created_at ASC LIMIT 40;"`
  - `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -Atqc "SELECT jsonb_pretty(metadata) FROM messages WHERE metadata->>'messageId' = 'LLM-QUAL-RESET-l2-acceptance-preflight-a922-r23-c783f6';"`
  - `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -Atqc "SELECT id, state, jsonb_pretty(context) FROM conversations WHERE id IN ('1ad3e42e-05bd-4d90-9ec6-6e027204a267','7c02e2dd-35c4-428b-8425-3167a9ba9c9e');"`
  - `rg -n "_fetch_latest_conversation_state|_send_session_reset|_reset_dialog_state|_should_reset_session_memory|_reset_session_memory_context" ops/diagnose.py truffles-api/app/routers/webhook/decision.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/services/state_service.py`
- `FACT findings`:
  - `/tmp/booking_quality/l2-acceptance-preflight-a922-r23/responses.jsonl` proves the old frozen booking `hooks` seam is gone, but dialog `1` still splits across two live conversations: turn `LLM-QUAL-l2-acceptance-preflight-a922-r23-001-01-35ba08` runs on conversation `7c02e2dd-35c4-428b-8425-3167a9ba9c9e` with `conversation_state="bot_active"`, while turn `LLM-QUAL-l2-acceptance-preflight-a922-r23-001-02-a8bed5` snaps to conversation `1ad3e42e-05bd-4d90-9ec6-6e027204a267` and fails with `expected_state_mismatch` plus `expected_reply_mismatch` in `conversation_state="pending"`.
  - the message timeline in `chatbot.messages` shows the reset hook itself landed on the stale conversation before dialog turn `1`: `LLM-QUAL-RESET-l2-acceptance-preflight-a922-r23-c783f6` hit `1ad3e42e-05bd-4d90-9ec6-6e027204a267` at `2026-03-19 11:09:27+00`, dialog turn `1` then used `7c02e2dd-35c4-428b-8425-3167a9ba9c9e` at `11:09:51+00`, and dialog turn `2` returned to `1ad3e42e-05bd-4d90-9ec6-6e027204a267` at `11:10:12+00`.
  - the reset message metadata proves the reset hook did not clear state; it was semantically routed through the old booking/handoff path: `decision_meta.action="escalate"`, `decision_meta.tool_decision="branch_missing"`, `turn_outcome.reason_code="calendar_book_slot_branch_missing_handoff"`, and the assistant reply was the handoff text rather than a reset acknowledgement.
  - the stale continuity is live inside both conversation contexts, not only in proof artifacts. Conversation `1ad3...` still carries `expected_reply_type="name"`, `expected_reply_reason="booking_prompt"`, `session_memory.interaction_owner="question_contract:booking_prompt"`, and old `booking_commit` / `booking_interrupt` traces. Conversation `7c02...` still carries stale booking state (`booking.active=true`, `booking.service="Маникюр"`, `appointment_id` present) plus an old simulation marker `simulation.id="l2-acceptance-preflight-a922-r11"`.
  - `ops/diagnose.py:_reset_dialog_state()` currently treats reset success as "latest conversation was `bot_active` and `_send_session_reset(...)` returned a payload". It does not verify that the reset message stayed on the intended conversation, produced a reset contract, or actually cleared booking/question-contract continuity before the dialog starts.
  - `truffles-api/app/services/state_service.py:_reset_session_memory_context()` is the existing non-frozen continuity owner surface for explicit reset semantics, while `truffles-api/app/routers/webhook/decision.py` remains frozen. Any truthful fix that cannot stay within `ops/diagnose.py` plus non-frozen continuity surfaces must stop and publish `GAP` instead of reopening frozen `decision.py` implicitly.
- `Detected drift (docs vs code)`:
  - the previous implementation block correctly claimed deletion of the frozen booking `hooks` seam, but its narrative evidence for `r23` over-credited `runtime_state.json`; the stronger repo truth comes from `responses.jsonl`, `messages`, reset-message metadata, and live `conversations.context` for `1ad3...` and `7c02...`.

## One web search (mandatory before implementation)
- **Query (exact):** `PostgreSQL ORDER BY LIMIT official docs`
- **Date/time (local):** `2026-03-19T16:41:53+05:00`
- **Sources opened (from this query):**
  - `https://www.postgresql.org/files/documentation/pdf/9.6/postgresql-9.6-A4.pdf`
- **Source quality:**
  - high-signal / primary source: official PostgreSQL documentation
- **Existing solutions found:**
  - PostgreSQL documents that `LIMIT` should be paired with an `ORDER BY` that constrains row order, but sorted-row selection still only identifies result order; it does not prove any higher-level postcondition such as “this conversation is now cleared.”
- **Decision:** `integrate`
  - keep the latest-conversation query deterministic, but do not treat `ORDER BY ... LIMIT 1` as proof that reset-before-dialog succeeded; implementation must validate the reset postcondition explicitly.
- **Rejected options:**
  - rerun-only loop without code change
  - manual DB cleanup / trace cleanup as evidence harvesting
  - phrase-hardcode or silent fallback that hides contamination without clearing it
  - frozen `decision.py` edits without a separate waiver decision

## Root cause (mandatory)
- **Symptom:** fresh guarded rerun `l2-acceptance-preflight-a922-r23` stops after two rows because dialog `1` re-enters stale continuity despite `--reset-before-dialog`; turn `2` lands in `pending` on an old conversation and violates the expected `booking_interrupt` contract.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/l2-acceptance-preflight-a922-r23/responses.jsonl` and confirm dialog `1` uses conversation `7c02...` on turn `1` and conversation `1ad3...` on turn `2`.
  2. inspect `chatbot.messages` for `remote_jid='77000000001@s.whatsapp.net'` since `2026-03-19 11:08:30+00` and confirm the reset hook `LLM-QUAL-RESET-l2-acceptance-preflight-a922-r23-c783f6` hit `1ad3...` before dialog turn `1` started.
  3. inspect the reset message metadata and confirm it produced `calendar_book_slot_branch_missing_handoff` instead of a reset acknowledgement.
  4. inspect `chatbot.conversations.context` for `1ad3...` and `7c02...` and confirm stale booking / question-contract / session-memory payloads remain live.
  5. inspect `ops/diagnose.py:_fetch_latest_conversation_state`, `_send_session_reset`, and `_reset_dialog_state` plus `truffles-api/app/services/state_service.py:_reset_session_memory_context`.
- **Evidence:**
  - `r23` response rows `LLM-QUAL-l2-acceptance-preflight-a922-r23-001-01-35ba08` and `LLM-QUAL-l2-acceptance-preflight-a922-r23-001-02-a8bed5`
  - reset message `LLM-QUAL-RESET-l2-acceptance-preflight-a922-r23-c783f6`
  - the `messages` timeline query for `77000000001@s.whatsapp.net`
  - live `conversations.context` for `1ad3e42e-05bd-4d90-9ec6-6e027204a267` and `7c02e2dd-35c4-428b-8425-3167a9ba9c9e`
  - source code in `ops/diagnose.py`, `truffles-api/app/routers/webhook/session_memory.py`, and `truffles-api/app/services/state_service.py`
- **Five Whys:**
  1. Why did dialog `1` fail on turn `2`? Because the turn was routed onto stale conversation `1ad3...`, which still carried pending booking/question-contract state.
  2. Why was `1ad3...` still eligible after `--reset-before-dialog`? Because the reset hook itself was processed as a normal inbound text on that stale conversation and produced a handoff, not a clear-state acknowledgement.
  3. Why did the suite continue anyway? Because `_reset_dialog_state()` only checks that `_send_session_reset(...)` returned and does not validate that the reset outcome actually cleared continuity on the conversation that will receive the next dialog turns.
  4. Why can stale continuity recapture the dialog? Because reset-before-dialog authority is split: proof-path orchestration in `ops/diagnose.py` decides when to send the reset text, while continuity clear semantics live elsewhere, and there is no single postcondition that binds them together.
  5. Why is this the next admissible family? Because the old booking `hooks` seam is already dead, and `r23` localizes the remaining blocker to one reset-before-dialog contamination contour rather than transport, observer, billing, or the deleted frozen booking caller family.
- **Root cause statement:** reset-before-dialog currently relies on `ORDER BY last_message_at DESC LIMIT 1` plus a plain inbound reset message, but it never proves that the selected conversation is actually clean afterward. The reset text can be semantically hijacked by stale booking/handoff state on the chosen conversation, and `_reset_dialog_state()` still starts the next dialog without verifying cleared continuity or stable conversation identity.
- **Fix mechanism:**
  - make `ops/diagnose.py` own an explicit reset-before-dialog postcondition: same conversation identity (or an explicitly accepted new one), cleared continuity signal, and no stale pending/handoff carryover before the first dialog turn starts
  - converge the clear semantics onto existing non-frozen continuity owners (`session_memory.py` / `state_service.py`) instead of adding a new compatibility seam
  - if the only truthful path requires frozen `truffles-api/app/routers/webhook/decision.py` edits or any manual data surgery, stop and publish `GAP`

## Old authority seam to delete (mandatory)
- **FACT:** the target seam is the unchecked reset-before-dialog authority in `ops/diagnose.py:_reset_dialog_state()`, which currently treats “reset message sent” as sufficient proof of a clean conversation.
- **FACT:** this seam remains live because `r23` shows the reset message itself can route through stale booking/handoff continuity and still allow the next dialog to bounce across old conversations.
- **INFERENCE:** the block is admissible only if the old proof-path heuristic becomes unreachable and reset-before-dialog is governed by one explicit clear-state postcondition without adding a wrapper/helper or reopening frozen `decision.py` by stealth.

## FACT vs INFERENCE verdict
- **FACT:** the old frozen booking `hooks` seam is already dead.
- **FACT:** the surviving `r23` blocker is a different family centered on preflight-clear/reset-before-dialog contamination.
- **FACT:** current repo truth proves the contamination with artifact rows plus live DB state, not with a green rerun.
- **INFERENCE:** the likely fix can stay in `ops/diagnose.py` plus non-frozen continuity owners, but the block must fail closed if implementation proves otherwise.
- **Decision:** switch canon from the completed frozen-waiver implementation block to this new contamination-family package.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `ops/diagnose.py:_fetch_latest_conversation_state`
  - `ops/diagnose.py:_send_session_reset`
  - `ops/diagnose.py:_reset_dialog_state`
  - `truffles-api/app/routers/webhook/session_memory.py:_reset_session_memory`
  - `truffles-api/app/services/state_service.py:_reset_session_memory_context`
  - existing message-endpoint and state-service test suites
- **External reuse:**
  - official PostgreSQL docs on `ORDER BY` + `LIMIT` semantics
- **Why not reinvent the wheel:**
  - the repo already has a continuity-reset owner surface; the missing piece is enforcing a clear postcondition in the proof-path preflight, not inventing another reset API or compatibility bridge.

## Execution profile (mandatory for non-doc blocks)
- **TP mode:** `implementation`
- **Doc touch budget (files):** `24`
- **Code dominance:** `mixed`
- **Override token:** `acceptance-preflight-preflight-clear-state-contamination-family`
- **Why this profile fits:** the next block is a bounded implementation on proof-path orchestration plus non-frozen continuity surfaces, with one guarded rerun as the only expensive validation.

## Invariant
- no transport / billing / observer reopening
- no manual DB cleanup, trace cleanup, or evidence harvesting
- no new wrapper/helper or new reset-only compatibility seam
- no phrase/regex hardcode in core as the fix
- no frozen `truffles-api/app/routers/webhook/decision.py` edits in this block; if that becomes necessary, stop and publish `GAP`
- exactly one fresh non-acceptance `L2` rerun after deterministic gates

## Scope
- prove the `r23` blocker as one reset-before-dialog contamination family
- adjust `ops/diagnose.py` preflight-clear orchestration so reset success is a verified contract, not a best-effort message send
- reuse existing non-frozen continuity reset owners to clear stale booking/question-contract/session-memory carryover for the selected conversation
- add focused regressions
- run one fresh guarded dev-lane `L2` rerun and strict audit
- sync canon/session/state with the truthful result

## Out of scope
- any change to `truffles-api/app/routers/webhook/booking.py`
- transport / billing / observer work
- acceptance closure claims
- more than one fresh rerun
- frozen `truffles-api/app/routers/webhook/decision.py` edits without a separate waiver / `GAP`
- any manual runtime data cleanup as a substitute for code

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-preflight-clear-state-contamination-family-package-a922.md`
- `ops/diagnose.py`
- `truffles-api/app/routers/webhook/session_memory.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STATE.md`
- `STRUCTURE.md`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Re-run the deterministic `r23` probes and DB queries so the contamination seam is locked to exact conversations, messages, and code surfaces.
2. Rework `ops/diagnose.py:_reset_dialog_state()` so reset-before-dialog verifies a clean postcondition instead of trusting a sent reset message.
3. Reuse `session_memory.py` / `state_service.py` continuity reset semantics so explicit reset clears stale booking/question-contract carryover on the conversation chosen for the next dialog.
4. Add focused regressions for reset-before-dialog conversation identity and clear-state behavior.
5. Run deterministic checks and required packet/guard/session gates.
6. Run exactly one fresh guarded dev-lane `L2` rerun and strict audit.
7. Publish either a truthful narrower residual family or a truthful green dev-lane `L2` summary, then sync canon.

## DoD
- the old unchecked reset-before-dialog authority seam in `ops/diagnose.py` is deleted/unreachable
- reset-before-dialog now requires a validated clear-state postcondition before dialog `1` starts
- no new wrapper/helper or frozen `decision.py` edit was used
- focused regressions pass
- exactly one fresh guarded dev-lane `L2` rerun exists and is strict-audited
- canon/session/state reflect the truthful result of the block

## Checks
- `python3 - <<'PY'
import json
from pathlib import Path
rows = [json.loads(line) for line in Path('/tmp/booking_quality/l2-acceptance-preflight-a922-r23/responses.jsonl').read_text().splitlines()]
for row in rows:
    print(row['message_id'], row['conversation_id'], row['conversation_state'], row['turn_text'])
PY`
- `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -Atqc "SELECT m.conversation_id, m.role, m.created_at, COALESCE(m.metadata->>'messageId',''), LEFT(COALESCE(m.content,''),120) FROM messages m JOIN conversations c ON c.id = m.conversation_id JOIN users u ON u.id = c.user_id WHERE c.client_id = 'c839d5dd-65be-4733-a5d2-72c9f70707f0' AND u.remote_jid = '77000000001@s.whatsapp.net' AND m.created_at >= '2026-03-19 11:08:30+00' ORDER BY m.created_at ASC LIMIT 40;"`
- `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -Atqc "SELECT jsonb_pretty(metadata) FROM messages WHERE metadata->>'messageId' = 'LLM-QUAL-RESET-l2-acceptance-preflight-a922-r23-c783f6';"`
- `python3 -m py_compile ops/diagnose.py truffles-api/app/routers/webhook/session_memory.py truffles-api/app/services/state_service.py truffles-api/tests/test_message_endpoint.py truffles-api/tests/test_state_service.py truffles-api/tests/test_booking_quality_status_gate.py`
- `pytest -q truffles-api/tests/test_state_service.py -k 'session_memory or pending_resume or explicit_reset'`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k 'session_reset or booking_interrupt or pending_resume'`
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py -k 'run_completion_gap or calendar_intent_missing or state'`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`
- one fresh guarded rerun command under the local runtime, followed by `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/l2-acceptance-preflight-a922-r24 --status done --strict-artifacts`

## Evidence
- exact `r23` response rows showing dialog `1` crossing `7c02...` -> `1ad3...`
- exact reset-message metadata for `LLM-QUAL-RESET-l2-acceptance-preflight-a922-r23-c783f6`
- exact `messages` / `conversations.context` DB evidence for stale continuity
- focused test output
- one fresh guarded rerun directory and strict audit
- canon/session/state naming which old seam died or, if still red, the narrower residual family

## Token / run budget (mandatory for expensive suites)
- **Max fresh non-acceptance `L2` runs:** `1`
- **Max full runs:** `0`
- **Cheap deterministic gates first:** artifact probe + DB evidence + focused pytest + packet/guard/session checks
- **Stop condition:** if the truthful fix requires frozen `decision.py`, manual data cleanup, a new wrapper/helper, or a second fresh rerun, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded local change to proof-path reset orchestration plus non-frozen continuity owners, followed by one guarded dev-lane rerun
- **Go/no-go signals:**
  - reset-before-dialog validates a clear-state postcondition
  - no frozen `decision.py` edit was needed
  - focused regressions pass
  - the single fresh rerun is strict-audited before any claim
- **Rollback:** revert `ops/diagnose.py`, continuity-owner, and test changes, then rerun deterministic checks
- **Post-release monitoring window:** only through the single fresh rerun and strict audit for this block

## Rollback
1. Revert this block's runtime/test/doc changes.
2. Re-run deterministic checks.
3. Restore canon/session/state to the previous truthful block if the implementation is rejected.

## No-go
- no rerun-only progress claim
- no hidden manual reset/DB cleanup
- no new reset wrapper/helper
- no frozen `decision.py` edit without a separate waiver decision
- no claim that `semantic_owner`, `continuity_owner`, or `boundary_owner` are fully closed from this block

## Risks / blockers
- the contamination seam may still terminate in frozen `decision.py`, in which case this block must stop and publish `GAP`
- proof-path orchestration and runtime continuity may both need bounded edits; if the surface spills beyond the touch-list, the block is invalid
- the single fresh rerun can surface a second residual family after contamination is cleared

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `semantic_owner`, `continuity_owner`, and `boundary_owner` remain partial after this package.
- the frozen `decision.py` boundary remains live and must not be edited in this block without a separate waiver.

### Why not in this block
- this block is only allowed to delete the reset-before-dialog contamination seam. Broader owner closure would require additional package-level work and likely frozen-family governance.

### Risk if deferred
- every future guarded `L2` rerun can be polluted by stale conversation continuity, which makes acceptance evidence non-canonical and obscures the next real runtime seam.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-19-consultant-core-acceptance-preflight-l2-frozen-booking-handover-reuse-targeted-frozen-waiver-implementation-a922.md`
- follow-up TP to be authored only if this block exposes a narrower post-contamination residual or a frozen-only `GAP`

### Expiry/trigger to stop deferral
- stop deferral immediately if implementation proves the only truthful repair requires frozen `decision.py` edits or if the fresh rerun still shows conversation-id split after deterministic reset validation changes.

## Next-block contract (mandatory)
### Next block objective
- `implement_acceptance_preflight_l2_preflight_clear_state_contamination_family_closure_bundle`

### First deterministic check command
- `docker exec -i truffles_postgres_1 psql -U n8n -d chatbot -Atqc "SELECT m.conversation_id, m.role, m.created_at, COALESCE(m.metadata->>'messageId',''), LEFT(COALESCE(m.content,''),120) FROM messages m JOIN conversations c ON c.id = m.conversation_id JOIN users u ON u.id = c.user_id WHERE c.client_id = 'c839d5dd-65be-4733-a5d2-72c9f70707f0' AND u.remote_jid = '77000000001@s.whatsapp.net' AND m.created_at >= '2026-03-19 11:08:30+00' ORDER BY m.created_at ASC LIMIT 40;"`

### Blocked-by conditions
- frozen `truffles-api/app/routers/webhook/decision.py` becomes the only truthful fix surface
- the fix requires manual runtime data cleanup
- the fix requires more than one fresh rerun or any new compatibility seam

### Owner role for closure
- `Hands` for bounded implementation + `Brain/Top Architect` for truthful closure decision
