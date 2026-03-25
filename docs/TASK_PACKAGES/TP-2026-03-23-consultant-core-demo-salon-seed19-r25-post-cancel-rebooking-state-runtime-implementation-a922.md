# TP-2026-03-23 Consultant Core Demo Salon Seed19 R25 Post-Cancel Rebooking State Runtime Implementation A922

## Title/goal
Repair the bounded post-cancel rebooking continuity defect so a valid collect reply on dialog `2`, turn `8` restores `bot_active` instead of preserving stale `pending` state.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-runtime-decision-a922.md`
- CA_ID `a922-go2f-seed19-r25-post-cancel-rebooking-state-family`

## One web search (mandatory before implementation)
- **Query (exact):** `site:stately.ai XState state machine reenter active state after transient pending handoff collect dialogue`
- **Date/time (local):** `2026-03-23 14:04 +05:00`
- **Sources opened (from this query):** `https://stately.ai/docs/inspection`
- **Found ready-made solutions:** Stately's inspection docs distinguish transient microsteps from the final snapshot and recommend observing the settled snapshot after all transitions are applied.
- **Decision:** `build` via local continuity repair on the executable owner chain.
- **Why:** the repo already has the needed state-transition primitives (`manager_resolve(..., preserve_context=True)` and `transition_state(...)`); the defect is that the collect owner never applies them when it re-enters booking flow from `pending`.
- **Rejected options:** proof/oracle changes, frozen-router edits, leaving `pending` as a tolerated transient state for collect rows.

## Root cause (mandatory)
- **Symptom:** replay `r25` reaches dialog `2`, turn `8` with a correct `booking_prompt` collect reply, but strict audit still fails because `conversation_state='pending'` instead of `bot_active`.
- **Minimal reproduction:** inspect `LLM-QUAL-a922-go2f-seed19-r25-002-08-a600b7` in `/tmp/booking_quality/a922-go2f-seed19-r25/responses.jsonl`; the row shows `action='booking_prompt'`, `expected_reply_type='service_choice'`, and stale `pending` continuity.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r25/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r25/manual_audit.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r25/responses.jsonl`
  - `truffles-api/app/services/reasoning_core.py:10095`
  - `truffles-api/app/services/reasoning_core.py:11179`
  - `truffles-api/app/services/state_service.py:1081`
  - `truffles-api/app/services/handover_owner_service.py:1457`
- **Five Whys:**
  - Why does the row fail strict audit? The row finishes with `conversation_state='pending'`.
  - Why does the state stay pending? The collect owner writes the new question contract but never reactivates the conversation.
  - Why is reactivation missing? `reasoning_core.py` reuses collect owners in `pending` conversations without resolving active handover or forcing `bot_active` first.
  - Why does that happen specifically here? Post-cancel rebooking re-enters booking flow after a handoff family, so stale pending continuity is still present when the collect owner runs.
  - Why is this a runtime bug rather than proof drift? `r25` is already `infra_valid=true`, the row action/meta are correct, and only the live continuity state violates the scenario contract.
- **Root cause statement:** the executable booking collect owner path re-enters booking flow from `pending` without restoring `bot_active`, so the final turn snapshot keeps stale handoff continuity even after a valid collect reply wins.
- **Fix mechanism:** add a bounded pending-to-bot-active collect reentry helper in non-frozen `reasoning_core.py`, apply it before collect-owner context writes, and lock the behavior with deterministic regressions.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `manager_resolve(..., preserve_context=True)` in `truffles-api/app/services/handover_owner_service.py`
  - `transition_state(...)` and pending continuity contracts in `truffles-api/app/services/state_service.py`
  - existing collect owner tests in `truffles-api/tests/test_reasoning_core.py`
- **External reuse:**
  - `https://stately.ai/docs/inspection`
- **Why not reinvent the wheel:** the runtime already has the correct state-transition primitives; the fix is to reuse them in the collect owner instead of inventing a second pending-clear path.

## Invariant
Do not weaken proof tooling, do not reopen frozen routers, and do not change the product reply surface for the post-cancel rebooking turn.

## Scope
Non-frozen collect-owner continuity in `reasoning_core.py`, plus deterministic regression coverage.

## Out of scope
Replay tooling, oracle thresholds, acceptance lock/full runs, and duplicate-def cleanup outside the executable later collect owner.

## Touch-list
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-runtime-implementation-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Add a bounded helper that restores `bot_active` when a booking collect owner re-enters from `pending`.
2. Apply that helper only on the executable later booking collect owners before they mutate expected-reply/context.
3. Add deterministic regression(s) for post-cancel rebooking continuity with active handover preservation.
4. Rerun focused tests and then the required guard stack before replay handoff.

## DoD
- post-cancel rebooking collect path no longer leaves `conversation.state='pending'`;
- deterministic regression proves the live owner path restores `bot_active` while keeping the collect reply contract;
- no frozen router file changed.

## Work mode (mandatory)
`implementation`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` during implementation; replay is deferred to the next closure block.
- **Max focused deterministic reruns:** `2` before stop-the-line and RCA refresh.
- **Stop condition:** if the focused regression or any mandatory guard fails without new evidence, stop and repair the runtime fix/TP contract before any replay.

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "post_cancel_rebooking_state or booking_prompt_owner_restores_snapshot_service_for_post_verification_reschedule or safe_check_booking_prompt_owner_bypasses_frozen_delegate or safe_check_booking_prompt_owner_repairs_repeated_reference_continuity_from_snapshot"`

## Evidence
- code diff in `truffles-api/app/services/reasoning_core.py`
- deterministic proof in `truffles-api/tests/test_reasoning_core.py`
- follow-up replay artifact from the next closure block

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only bounded runtime repair in non-frozen owner paths before any replay or acceptance lane reuse.
- **Go/no-go signals:** focused deterministic suite green; guard stack green; frozen routers untouched.
- **Rollback:** revert the bounded collect reentry helper and its paired regressions if replay or guards regress.
- **Post-release monitoring window:** no release rollout in this block; monitor only the next fresh local replay and strict audit artifact.

## Rollback
Rollback: revert the bounded collect reentry helper and its paired regressions.

## No-go
- no proof-layer edits first
- no frozen router edits
- no silent acceptance of `pending` as a collect-state success

## Risks/blockers
- `reasoning_core.py` still has shadowed duplicate defs; the fix must stay on the executable later owner path only.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** duplicate top-level defs in `reasoning_core.py` remain structural debt; downstream replay blockers after `r25` remain unknown until closure replay.
- **Why not in this block:** the admissible scope is the live post-cancel collect continuity defect, not broader duplicate cleanup.
- **Risk if deferred:** later families can still surface adjacent continuity issues on the same hotspot.
- **Linked follow-up Task Package(s):** `TP-2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-canary-replay-a922.md`
- **Expiry/trigger to stop deferral:** if the runtime fix touches a shadowed earlier def or replay surfaces another collect-state mismatch on the same owner name, duplicate cleanup becomes mandatory before more runtime edits.

## Next-block contract (mandatory)
- **Next block objective:** rerun the seed-`19` replay on fresh runtime parity and classify the first surviving blocker after the post-cancel rebooking state repair.
- **First deterministic check command:** `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r26 --status done --strict-artifacts`
- **Blocked-by conditions:** stale local runtime; failing focused regressions; unaudited replay artifact.
- **Owner role for closure:** Brain / Top Architect
