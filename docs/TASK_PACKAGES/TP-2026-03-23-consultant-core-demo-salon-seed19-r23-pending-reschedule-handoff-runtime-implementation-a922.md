# TP-2026-03-23 Consultant Core Demo Salon Seed19 R23 Pending Reschedule Handoff Runtime Implementation A922

## Title/goal
Repair the `r23` pending reschedule follow-up runtime family so the turn `На какое время лучше записаться?` stays in booking collect instead of falling through to terminal handoff.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r23-pending-reschedule-handoff-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r23-pending-reschedule-handoff-runtime-decision-a922.md`

## Invariant
Do not reopen proof tooling or acceptance gates; fix the bounded runtime continuity contract in non-frozen code only.

## Scope
- bounded runtime repair in `reasoning_core.py`
- deterministic regressions for the surfaced failure family
- canon/session sync after the fix

## Out of scope
- proof tooling changes
- acceptance threshold changes
- frozen router edits
- unrelated shadow-def cleanup beyond the touched live path

## Touch-list (files/tables)
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r23-pending-reschedule-handoff-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r23-pending-reschedule-handoff-runtime-implementation-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan
1. Normalize the exact family boundary in the live booking-prompt candidate path.
2. Repair the candidate gate so stale temporal follow-up metadata does not eject a service-missing collect turn into terminal fallback.
3. Add deterministic regressions for the normalized contract and for the full `handle_webhook_payload(...)` path.
4. Run focused tests plus guard stack.
5. Sync canon and set the next replay closure move.

## DoD
- the live booking-prompt path accepts the surfaced service-missing follow-up family
- deterministic regressions cover the helper gate and end-to-end owner path
- guard stack is green
- canon points at the replay closure move, not another proof block

## Work mode (mandatory)
- `Mode`: `implementation`
- `Why this mode`: `r23` already proved the blocker is runtime, so the next admissible move is a bounded code repair with deterministic evidence.
- `Family handled in this block`: `seed19 r23 pending reschedule handoff runtime family`
- `Closure artifact expected from this mode`: deterministic regressions + implementation report + canon sync to replay closure

## One web search (mandatory before implementation)
- **Query (exact):** `site:rasa.com/docs/rasa/forms unhappy path slot filling interruption`
- **Date/time (local):** `2026-03-23 10:40 +05:00`
- **Sources opened (from this query):** `https://legacy-docs-oss.rasa.com/docs/rasa/forms/`
- **Source quality:** `official documentation / primary source`
- **Existing solutions found:** active slot-collection loops should either keep the requested-slot contract active after interruptions or deactivate explicitly; they should not silently fall through to a generic fallback path.
- **Decision:** `reuse the continuity principle, build a bounded normalization in the runtime candidate gate`
- **Reuse / integrate / build decision:** `build` — the repo already has the booking collect owner; the missing piece is a local normalization that accepts contract-aligned service collect payloads even when policy-core echoes stale temporal follow-up metadata.
- **Rejected options:** `reopening proof tooling`, `adding phrase-specific regex handoff exceptions`, `routing through frozen webhook owners`

## Reuse-first plan (mandatory)
- Internal reuse:
  - `_resolve_turn_planner_safe_llm_booking_prompt_candidate(...)`
  - `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)`
  - existing booking prompt regressions around service-missing follow-ups
- External reuse:
  - `https://legacy-docs-oss.rasa.com/docs/rasa/forms/`
- Why not reinvent the wheel:
  - the booking prompt owner already owns the correct runtime surface; only the candidate validation is too strict for this family.

## Root cause (mandatory)
- Symptom: fresh replay `r23` stops on dialog `2`, turn `9` with `policy_core_guard` / `handoff` instead of `booking_prompt` / `service_choice`.
- Minimal reproduction:
  - replay artifact row `LLM-QUAL-a922-go2f-seed19-r23-002-09-6f3a38`
  - direct local probe of `route_llm_policy_core("На какое время лучше записаться?", ...)` with `expected_reply_type=service_choice` and `slot_state={"datetime": "2023-10-03T16:00:00Z"}`
- Evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r23/responses.jsonl`
  - `/tmp/booking_quality/a922-go2f-seed19-r23/manual_audit.json`
  - local direct probe output showing raw payload:
    - `next_question=service`
    - `capability=live_availability`
    - `resolution_mode=ask_about_requested_slot`
    - `pending_question_target=time`
    - `active_question_relation=ask_about_requested_slot`
  - `truffles-api/app/services/reasoning_core.py`
- Five Whys:
  1. Why does the replay stop on turn `9`? The runtime emits terminal handoff instead of booking collect.
  2. Why does terminal handoff fire? Every earlier runtime owner returns `None`.
  3. Why does the booking-prompt owner return `None`? `_resolve_turn_planner_safe_llm_booking_prompt_candidate(...)` rejects the candidate.
  4. Why is the candidate rejected? Policy core returns a service-collect payload that is contract-aligned on `next_question=service`, but the helper rejects it because it also carries stale temporal follow-up metadata (`live_availability`, `ask_about_requested_slot`, `pending_question_target=time`).
  5. Why does that become a handoff? Once the collect candidate is rejected, the live owner chain falls through to `terminal_owner_unresolved`, which then synthesizes `policy_core_guard` handoff.
- Root cause statement: the live booking-prompt candidate gate is too strict for service-missing reschedule follow-up turns and rejects a contract-aligned service-collect payload when policy core echoes temporal follow-up metadata from the previous time discussion.
- Fix mechanism: normalize/allow this bounded service-missing collect envelope in the booking-prompt candidate path so the collect owner can keep the `service_choice` contract instead of falling into terminal fallback.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0`
- Max replay runs: `0` before deterministic green
- Stop condition: if focused regressions do not prove the normalized gate, stop and re-check RCA before any new replay

## Release safety (mandatory for non-doc changes)
- Strategy: `local-only runtime repair followed by guarded replay; no production rollout in this block`
- Go/no-go signals: focused regressions green; guard stack green; no frozen-router edits
- Rollback: revert the bounded `reasoning_core.py` and regression edits if replay disproves the fix
- Post-release monitoring window: `n/a in implementation block`

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_reschedule or booking_prompt_owner or terminal_owner_unresolved"`
- `python3 scripts/build_agent_packet.py`
- `python3 scripts/build_agent_packet.py --check`
- `python3 scripts/semantic_bridge_growth_guard.py`
- `python3 scripts/continuity_writer_guard.py`
- `python3 scripts/legacy_freeze_guard.py`
- `python3 scripts/arch_guard.py`
- `pytest -q truffles-api/tests/architecture`
- `git diff --check`
- `SESSION_AGENT=a922 scripts/session_check.sh`

## Evidence
- focused pytest output
- updated TP/report pair
- canon/session sync
- next replay command recorded in docs

## Rollback
Revert the bounded runtime candidate normalization and its regressions.

## No-go
- no frozen router edits
- no proof-tool changes first
- no phrase hardcode for the surfaced user text
- no acceptance-gate weakening

## Risks/blockers
- `reasoning_core.py` still contains duplicate top-level defs; touch only the live later definition path.
- The family may hide an additional downstream blocker that only a replay can surface after deterministic green.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- duplicate top-level defs remain in `reasoning_core.py`
- downstream rows after dialog `2`, turn `9` remain unclassified until replay

### Why not in this block
This block is bounded to the service-missing collect gate; shadow-def cleanup is a separate family.

### Risk if deferred
A later family could still surface another continuity defect after replay.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r23-pending-reschedule-handoff-canary-replay-a922.md`

### Expiry/trigger to stop deferral
After the deterministic fix lands; the next replay must either close or surface the next family.

## Next-block contract (mandatory)
### Next block objective
Replay the exact seed19 scenario set on a fresh runtime and confirm the `r23` blocker is closed.

### First deterministic check command
`pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_reschedule or booking_prompt_owner or terminal_owner_unresolved"`

### Blocked-by conditions
Focused regressions red; stale local runtime; disagreement that the surfaced blocker is still runtime.

### Owner role for closure
Brain / Top Architect
