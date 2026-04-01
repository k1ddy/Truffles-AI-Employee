# TP-2026-03-23 Consultant Core Demo Salon Seed19 R29 Initial Booking Handoff Regression Runtime Decision A922

## Title/goal
Classify the fresh `r29` first blocker and lock the next bounded runtime family after the truthful replay surfaced an initial-booking handoff regression before the old post-cancel rebooking turn.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-canary-replay-a922.md`
- CA_ID `a922-go2f-seed19-r29-initial-booking-handoff-regression-family`

## One web search (mandatory before implementation)
- **Query (exact):** `site:stately.ai/docs XState transition guards fallback event routing state machine`
- **Date/time (local):** `2026-03-23 14:26 +05:00`
- **Sources opened (from this query):** `https://stately.ai/docs/transitions`
- **Found ready-made solutions:** Stately documents that transition selection checks the deepest active states first, then parent states, and that targetless/self transitions preserve active child state while targeted/re-entering transitions can re-resolve state.
- **Decision:** `build` a bounded runtime family decision from local owner-routing evidence.
- **Why:** the surfaced blocker is an owner-routing regression inside existing runtime handlers; no external package replaces that repo-specific authority chain.
- **Rejected options:** proof/oracle patching, replay threshold changes, frozen-router edits.

## Root cause (mandatory)
- **Symptom:** truthful replay `r29` now fails on dialog `1`, turn `1`, where the initial booking request escalates to handoff instead of entering the booking collect path.
- **Minimal reproduction:** inspect `LLM-QUAL-a922-go2f-seed19-r29-001-01-5279e4` in `/tmp/booking_quality/a922-go2f-seed19-r29/responses.jsonl`; the row shows `decision_meta.action='escalate'`, `tool_action='handoff'`, `reason_code='terminal_owner_unresolved'`, and trace stage `turn_planner_safe_explicit_handoff_owner`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r29/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r29/manual_audit.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r29/brief.md`
  - `/tmp/booking_quality/a922-go2f-seed19-r29/responses.jsonl`
  - `/tmp/booking_quality/a922-go2f-seed19-r25/responses.jsonl`
  - `truffles-api/app/services/reasoning_core.py:8481`
  - `truffles-api/app/services/reasoning_core.py:10136`
  - `truffles-api/app/services/reasoning_core.py:15628`
- **Five Whys:**
  - Why does strict replay fail? The row violates the expected meta/trace contract for an initial booking collect turn.
  - Why is the meta/trace wrong? Runtime creates handoff through `turn_planner_safe_explicit_handoff_owner` with `reason_code='terminal_owner_unresolved'`.
  - Why does that owner win on the first booking turn? The booking entry path falls through without producing the expected `booking_prompt` collect contract.
  - Why is this not a stale replay artifact? `r29` is `infra_valid=true`, strict artifacts are complete, and stale `r26`/`r27`/`r28` artifacts were manually audited and excluded first.
  - Why is this runtime, not proof drift? The same locked scenario was strict-green on dialog `1`, turn `1` in `/tmp/booking_quality/a922-go2f-seed19-r25/responses.jsonl`, so the mismatch is in owner routing, not in the oracle.
- **Root cause statement:** the fresh initial-booking entry path regresses into explicit handoff / terminal unresolved instead of landing on the booking collect owner, so the first user booking turn now violates the locked `booking_prompt` contract on truthful replay evidence.
- **Fix mechanism:** trace the executable booking entry routing against the duplicated `booking_prompt` / `explicit_handoff` owner surfaces, then restore bounded initial-booking collect ownership on the live non-frozen path with deterministic regression coverage before replaying again.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing initial booking prompt contract in `/tmp/booking_quality/a922-go2f-seed19-r25/responses.jsonl`
  - executable owner handlers in `truffles-api/app/services/reasoning_core.py`
  - deterministic replay oracle already locked in `/tmp/booking_quality/a922-go2f-seed19/scenarios.json`
- **External reuse:**
  - `https://stately.ai/docs/transitions`
- **Why not reinvent the wheel:** the repo already has the correct collect contract and owner handlers; the work is to restore the correct owner selection, not to add a new workflow layer.

## Invariant
Do not weaken replay/proof gates, do not touch frozen routers, and do not reinterpret the initial booking turn as an acceptable handoff.

## Scope
Truthful runtime-family classification only.

## Out of scope
- implementation changes before the family boundary is locked
- proof/preflight gate relaxation
- acceptance `lock/full` work

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r25-post-cancel-rebooking-state-canary-replay-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r29-initial-booking-handoff-regression-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r29-initial-booking-handoff-regression-runtime-decision-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Audit stale replay attempts (`r26`/`r27`/`r28`) so they cannot pollute manual-audit gating.
2. Run one truthful fresh replay on canonical runtime parity.
3. Compare the fresh failing row against the prior strict-green baseline row for the same scenario turn.
4. Lock the next admissible family in the runtime layer only if the mismatch remains on fresh replay evidence.

## DoD
- stale/non-canonical replay attempts are explicitly excluded
- fresh replay `r29` is strict-audited
- the next admissible blocker is classified as runtime/proof with a bounded next move

## Work mode (mandatory)
`closure`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` in this decision block.
- **Max replay runs:** `1` truthful fresh replay after stale-artifact audit.
- **Stop condition:** if the fresh replay is still infra-invalid, stop and classify the new blocker before any runtime code.

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r29 --status done --strict-artifacts`

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r26/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r27/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r28/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r29/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r29/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r29/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r29/responses.jsonl`

## Release safety (mandatory for non-doc changes)
- **Strategy:** no production rollout in this decision block; classify only and keep replay runtime local on `127.0.0.1:18186`.
- **Go/no-go signals:** fresh replay artifact is strictly audited; stale attempts are explicitly excluded; no code changes are made in this block.
- **Rollback:** revert nothing; this block is evidence-only.
- **Post-release monitoring window:** not applicable; no release activity occurs in this block.

## Rollback
Rollback: not applicable; no implementation changes are made in this block.

## No-go
- no new runtime patch before family classification
- no proof/oracle threshold edits
- no frozen-router edits

## Risks/blockers
- `booking_prompt` and `explicit_handoff` owner names remain duplicated in `reasoning_core.py`, so any implementation block must stay on the executable later def only or open duplicate cleanup first.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** shadowed duplicate owner defs remain unresolved; post-cancel rebooking turn `8` is now downstream until the new first blocker is closed.
- **Why not in this block:** this block classifies the new first blocker only.
- **Risk if deferred:** repeated owner-routing regressions can keep surfacing earlier turns and hide downstream closure status.
- **Linked follow-up Task Package(s):** `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r29-initial-booking-handoff-regression-runtime-implementation-a922.md`
- **Expiry/trigger to stop deferral:** immediate; the next code block must either repair this owner-routing family or open duplicate cleanup if the executable path cannot be isolated cleanly.

## Next-block contract (mandatory)
- **Next block objective:** repair the bounded runtime regression so a fresh initial booking request returns to the `booking_prompt` collect contract instead of escalating through `terminal_owner_unresolved`.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_reasoning_core.py -k "initial_booking or booking_prompt_owner"`
- **Blocked-by conditions:** duplicate-def cleanup becomes mandatory if the live executable path cannot be isolated; replay/runtime parity must remain truthful.
- **Owner role for closure:** Brain / Top Architect
