# TP-2026-03-23 Consultant Core Demo Salon Seed19 R29 Initial Booking Handoff Regression Runtime Implementation A922

## Title/goal
Repair the bounded initial-booking timeout regression so dialog `1`, turn `1` returns to the `booking_prompt` collect contract instead of falling through to explicit handoff / terminal unresolved when policy-core times out.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r29-initial-booking-handoff-regression-runtime-decision-a922.md`
- CA_ID `a922-go2f-seed19-r29-initial-booking-handoff-regression-family`

## One web search (mandatory before implementation)
- **Query (exact):** `site:platform.openai.com/docs retry timeout best practices API`
- **Date/time (local):** `2026-03-23 15:00 +05:00`
- **Sources opened (from this query):** `https://platform.openai.com/docs/guides/rate-limits`
- **Found ready-made solutions:** official OpenAI guidance treats timeout/rate-limit failures as transient and recommends bounded retry/backoff behavior instead of treating them as permanent semantic failures.
- **Decision:** `build` a bounded runtime timeout-recovery path on the executable initial-booking owner.
- **Why:** the repo already has deterministic booking parsing and prompt-generation primitives; the missing piece is a safe degraded fallback when policy-core times out before initial booking collect is seeded.
- **Rejected options:** replay/proof relaxation, frozen-router edits, accepting explicit handoff as valid for initial booking timeout turns.

## Root cause (mandatory)
- **Symptom:** truthful replay `r29` fails on dialog `1`, turn `1` because the first booking request escalates through `turn_planner_safe_explicit_handoff_owner` instead of returning `booking_prompt` / `collect`.
- **Minimal reproduction:** inspect `LLM-QUAL-a922-go2f-seed19-r29-001-01-5279e4` in `/tmp/booking_quality/a922-go2f-seed19-r29/responses.jsonl`; the row shows `action='escalate'`, `tool_action='handoff'`, and `reason_code='terminal_owner_unresolved'`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r29/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r29/manual_audit.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r29/responses.jsonl`
  - `truffles-api/app/services/reasoning_core.py:7144`
  - `truffles-api/app/services/reasoning_core.py:7507`
  - `truffles-api/app/services/reasoning_core.py:11881`
- **Five Whys:**
  - Why does the turn fail strict replay? The runtime returns handoff metadata instead of the locked collect contract.
  - Why does runtime hand off? The executable later booking-prompt candidate resolver returns `None`, so owner routing falls through to explicit handoff / terminal unresolved.
  - Why does that resolver return `None`? `route_llm_policy_core(...)` times out and the resolver has no bounded recovery for fresh initial-booking requests without an active snapshot.
  - Why is no recovery available? Existing exact-time/name recovery helpers operate on active booking continuity, not on the first booking turn.
  - Why is this runtime rather than proof drift? `r29` is `infra_valid=true`, the baseline replay for the same locked row was previously strict-green, and the mismatch is entirely in live owner routing.
- **Root cause statement:** on a fresh initial-booking entry turn, policy-core timeout leaves the executable later booking-prompt candidate resolver without a bounded degraded collect candidate, so the owner chain falls through to explicit handoff / terminal unresolved instead of seeding initial booking collect.
- **Fix mechanism:** add a bounded timeout-recovery helper that reuses existing deterministic booking parsing to recover only the safe initial collect envelope (`datetime` or `name` with grounded `service`), wire it into the executable later candidate resolver, and preserve observability with trace/meta evidence.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `decision_router._is_booking_request(...)`
  - `decision_router._update_booking_from_messages(...)`
  - `decision_router._first_missing_booking_slot(...)`
  - existing `_next_booking_prompt(...)` / `_build_turn_planner_safe_booking_prompt_decision(...)`
- **External reuse:**
  - `https://platform.openai.com/docs/guides/rate-limits`
- **Why not reinvent the wheel:** the runtime already knows how to parse booking requests and generate the correct bounded collect prompt; the fix is to reuse those primitives during timeout degrade instead of adding a new semantic bridge.

## Invariant
Do not weaken proof gates, do not touch frozen routers, and do not reinterpret the initial booking turn as acceptable handoff.

## Scope
Non-frozen timeout-degraded initial booking collect recovery in `reasoning_core.py`, plus deterministic regression coverage.

## Out of scope
Replay tooling, oracle thresholds, acceptance lock/full runs, and duplicate-def cleanup outside the executable later initial-booking owner path.

## Touch-list
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r29-initial-booking-handoff-regression-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r29-initial-booking-handoff-regression-runtime-implementation-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Add a bounded timeout-recovery helper for fresh initial-booking requests that can safely derive the next collect slot from deterministic parsing only.
2. Wire that helper into the executable later `_resolve_turn_planner_safe_llm_booking_prompt_candidate(...)` when policy-core returns `timeout` / `deadline_exceeded`.
3. Preserve observability through `policy_core_mode`, `policy_core_degrade_reason`, `policy_core_guard_recovery`, and `policy_core_guard` trace payloads.
4. Add deterministic helper-level and full `handle_webhook_payload(...)` regressions.
5. Rerun focused tests, then hand off to a fresh replay closure block.

## DoD
- initial booking timeout no longer falls through to explicit handoff / terminal unresolved on the executable later owner path;
- deterministic regressions prove the recovered reply is still `booking_prompt` with the expected follow-up slot;
- no frozen router file changed.

## Work mode (mandatory)
`implementation`

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0` during implementation; replay is deferred to the next closure block.
- **Max focused deterministic reruns:** `2` before stop-the-line and RCA refresh.
- **Stop condition:** if focused regressions or required guards fail without new evidence, stop and repair the bounded runtime fix before replay.

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "initial_booking_timeout or booking_prompt_candidate_recovers_initial_booking_timeout or post_cancel_rebooking_state or booking_prompt_owner_restores_snapshot_service_for_post_verification_reschedule or safe_check_booking_prompt_owner_bypasses_frozen_delegate or safe_check_booking_prompt_owner_repairs_repeated_reference_continuity_from_snapshot"`

## Evidence
- code diff in `truffles-api/app/services/reasoning_core.py`
- deterministic proof in `truffles-api/tests/test_reasoning_core.py`
- partial replay evidence in `/tmp/booking_quality/a922-go2f-seed19-r38/{responses.jsonl,trace_bundle.jsonl,manual_audit.json}`
- follow-up truthful replay artifact from the next closure block

## Release safety (mandatory for non-doc changes)
- **Strategy:** local-only bounded runtime repair in non-frozen owner paths before any replay or acceptance lane reuse.
- **Go/no-go signals:** focused deterministic suite green; guard stack green; frozen routers untouched.
- **Rollback:** revert the bounded timeout-recovery helper and paired regressions if replay or guards regress.
- **Post-release monitoring window:** no release rollout in this block; monitor only the next fresh local replay and strict audit artifact.

## Rollback
Rollback: revert the bounded timeout-recovery helper and paired regressions.

## No-go
- no proof-layer edits first
- no frozen-router edits
- no silent acceptance of initial booking handoff on policy timeout

## Risks/blockers
- `reasoning_core.py` still carries shadowed duplicate defs; the implementation must stay on the executable later owner path and not rely on the earlier duplicate body.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** duplicate top-level defs in `reasoning_core.py` remain structural debt; truthful classification of the next blocker is still pending because replay `r38` was interrupted after dialog `1`.
- **Why not in this block:** admissible scope is the bounded initial-booking timeout family only.
- **Risk if deferred:** adjacent dialog-`2` replay families can still surface after dialog `1` is repaired.
- **Linked follow-up Task Package(s):** `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r29-initial-booking-handoff-regression-canary-replay-a922.md`
- **Expiry/trigger to stop deferral:** if the next truthful replay still falls through on the same owner name or the executable path cannot be isolated from a shadowed earlier def.

## Next-block contract (mandatory)
- **Next block objective:** run one fresh replay on canonical runtime parity and classify the first surviving blocker after the bounded initial-booking timeout repair.
- **First deterministic check command:** `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r39 --status done --strict-artifacts`
- **Blocked-by conditions:** stale local runtime, failing focused regressions, or an unaudited/incomplete replay artifact.
- **Owner role for closure:** Brain / Top Architect
