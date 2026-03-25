# TP-2026-03-22 — Consultant Core Demo Salon Main Canary Turn 8 Booking Interrupt Exact-Time Progression Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN8-BOOKING-INTERRUPT-EXACT-TIME-PROGRESSION-RUNTIME-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN11-CHECK-BOOKING-REFERENCE-CONTINUITY-CANARY-REPLAY-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-canary-replay-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN8-BOOKING-INTERRUPT-EXACT-TIME-PROGRESSION-CANARY-REPLAY-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Implement one bounded runtime-family repair for fresh canary turn `8` (`Я хочу записаться на 10 утра в субботу.`). The fix is admissible only if the live non-frozen booking-interrupt prompt owner restores exact-time progression on the active `datetime` question, advances the collect contract to `name`, and leaves proof/oracle/frozen-router surfaces untouched.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-canary-replay-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-debug-cadence-reset-and-shadow-def-guard-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-debug-cadence-reset-and-shadow-def-guard-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`
- `/tmp/booking_quality/a922-check-booking-proof-r17/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r17/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r17/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r17/manual_audit.json`
- `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`

## FACT pre-check (before implementation)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn8-booking-interrupt-exact-time-progression-runtime-implementation-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn8-booking-interrupt-exact-time-progression-runtime-implementation-a922.md`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
  - `truffles-api/app/services/reasoning_core.py`
  - `truffles-api/tests/test_reasoning_core.py`
- `Baseline commands`:
  - `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r17/responses.jsonl').open(encoding='utf-8') if line.strip()]
for idx in [7, 8, 9]:
    row = next(r for r in rows if r.get('turn_index') == idx)
    print(idx, row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('booking_slots'), row.get('booking_progressed'))
    print(json.dumps(row.get('decision_meta') or {}, ensure_ascii=False, indent=2))
PY`
  - `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r17/trace_bundle.jsonl').open(encoding='utf-8') if line.strip()]
row = next(r for r in rows if r.get('turn_index') == 8)
print(json.dumps(row.get('decision_trace') or [], ensure_ascii=False, indent=2))
PY`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '5550,5860p;10370,10615p'`
  - `nl -ba truffles-api/tests/test_reasoning_core.py | sed -n '7482,7655p;14753,14931p'`
- `FACT findings`:
  - `/tmp/booking_quality/a922-check-booking-proof-r17/responses.jsonl` turn `8` keeps `expected_reply_type=time`, preserves only `booking_slots.datetime='в субботу'`, and records `booking_progressed=false` after the user provides explicit exact time (`10 утра`).
  - The locked scenario contract in `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json` expects turn `8` to advance to `reply_type=name` with a `question_contract` trace carrying `expected_reply_type=name`; the current replay does not satisfy that progress contract.
  - The live later duplicate `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)` in `truffles-api/app/services/reasoning_core.py:9573` / `10348-10615` does not apply `_apply_turn_planner_exact_time_progression_override(...)` when evaluating active booking-interrupt exact-time fills.
  - The earlier shadowed duplicate `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)` in `truffles-api/app/services/reasoning_core.py:4819` / `5594-5853` still contains the missing exact-time progression logic for the same owner family, including projected-state progression, post-merge reapplication, trace evidence, and `booking_payload_override`.
  - Existing deterministic tests already prove adjacent contracts for slot-constraint preservation and question-like exact-time progression, but there is no focused regression for the direct booking-interrupt exact-time fill that surfaced on `r17` turn `8`.
- `Detected drift (docs vs code)`:
  - active canon still points to the replay block; once this runtime family lands, canon must promote the implementation block and set the next non-negotiable move to guarded replay.

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa forms from text requested slot exact value follow-up site:rasa.com/docs`
- **Date/time (local):** `2026-03-22T18:13:00+05:00`
- **Sources opened (from this query):**
  - `https://legacy-docs-oss.rasa.com/docs/rasa/forms/`
- **Source quality:** vendor documentation / primary source.
- **Existing solutions found:** requested-slot progression should remain anchored to the currently requested slot, and once user text fills that slot exactly, the form should advance to the next slot instead of reopening the same slot-constraint follow-up.
- **Decision:** `reuse/integrate`
  - reuse the repo's existing `_apply_turn_planner_exact_time_progression_override(...)`, earliest-missing-slot contract, and booking prompt finalization path
  - integrate the missing exact-time progression logic into the live later duplicate booking-prompt owner only
  - do not build a new proof/oracle bridge for this family
- **Rejected options:**
  - second web query
  - frozen-router edits
  - proof/oracle weakening first
  - phrase hardcode for booking-interrupt wording

## Root cause (mandatory)
- **Symptom:** truthful replay `r17` remains semantic-red because turn `8` keeps `expected_reply_type=time`, preserves only `booking_slots.datetime='в субботу'`, and records `booking_progressed=false` after explicit exact-time input during active booking-interrupt recovery.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/a922-check-booking-proof-r17/responses.jsonl` turns `7` and `8`
  2. confirm turn `7` leaves the conversation in booking-interrupt follow-up with `expected_reply_type=time` and `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу'}`
  3. confirm turn `8` user text (`Я хочу записаться на 10 утра в субботу.`) still yields `expected_reply_type=time`, `booking_progressed=false`, and `pending_question_act=slot_constraint`
  4. inspect the live later duplicate `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)` at `truffles-api/app/services/reasoning_core.py:10375-10615`
  5. confirm it computes projected progress without `_apply_turn_planner_exact_time_progression_override(...)` and therefore treats the explicit time as still-missing `datetime`
  6. compare with the earlier shadowed duplicate at `truffles-api/app/services/reasoning_core.py:5594-5853` and confirm the exact-time progression logic exists there but is absent from the live later duplicate
- **Evidence:**
  - `/tmp/booking_quality/a922-check-booking-proof-r17/responses.jsonl`
  - `/tmp/booking_quality/a922-check-booking-proof-r17/trace_bundle.jsonl`
  - `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`
  - `truffles-api/app/services/reasoning_core.py:5594-5853`
  - `truffles-api/app/services/reasoning_core.py:10375-10615`
- **Five Whys:**
  1. Why does turn `8` stall on `time`? Because the live owner still thinks `datetime` is the first missing booking slot after processing the exact-time user reply.
  2. Why does it still think `datetime` is missing? Because its projected short-circuit state only uses `_update_booking_from_messages(...)`, which leaves `datetime='в субботу'` on this booking-interrupt wording.
  3. Why is the exact-time merge not applied? Because the live later duplicate omitted the `_apply_turn_planner_exact_time_progression_override(...)` branch that exists in the earlier shadowed duplicate.
  4. Why was that omission possible? Because `reasoning_core.py` still carries duplicate top-level owner handlers, so the earlier implementation can diverge from the later live definition.
  5. Why does this matter on the canary? Because fail-fast closure already repaired turns `9`, `11`, and `13`, so the remaining threshold breach now depends on this exact continuity hole.
- **Root cause statement:** the live later duplicate booking-prompt owner dropped the exact-time progression override for active booking-interrupt `datetime` replies, so explicit exact times never advance the merged booking state before missing-slot selection.
- **Fix mechanism:** port the exact-time progression branch from the earlier shadowed duplicate into the live later duplicate only: apply the override to the projected short-circuit state, reapply it after live booking-state merge for the owner route, attach trace/meta evidence, and persist `booking_payload_override` when progression succeeds.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `_apply_turn_planner_exact_time_progression_override(...)`
  - `_build_exact_time_progression_trace_payload(...)`
  - `decision_router._update_booking_from_messages(...)`
  - `decision_router._first_missing_booking_slot(...)`
  - `_finalize_turn_planner_owner_cutover(...)`
  - existing slot-constraint and exact-time progression tests in `truffles-api/tests/test_reasoning_core.py`
- **External reuse:**
  - official Rasa forms requested-slot guidance only
- **Why not reinvent the wheel:**
  - the repo already owns exact-time progression semantics and trace payload helpers; this block only restores the live booking-interrupt owner to that existing contract.

## Work mode (mandatory)
- `Mode`: `implementation`
- `Why this mode`: this block changes live non-frozen runtime code and deterministic regressions for one bounded runtime family
- `Family handled in this block`: `active booking-interrupt direct exact-time fill that currently re-asks for time instead of progressing to name`
- `Closure artifact expected from this mode`: focused deterministic green + canon sync to implementation; guarded replay stays next

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `18`
- `Code dominance`: `single_runtime_family`
- `Override token`: `none`
- `Why this profile fits`:
  - the block is one bounded runtime repair with focused regressions and canon sync; it is not a replay/closure block.

## Invariant
- do not edit frozen webhook routers
- do not weaken judge / threshold / acceptance gates
- do not remove or silently grow duplicate defs; work only in the live later duplicate
- do not add phrase-hardcoded branching for booking-interrupt wording
- do not claim acceptance closure from this block alone

## Scope
- repair the live turn-8 booking-prompt owner so booking-interrupt exact-time fills advance the collect contract from `time` to `name`
- preserve grounded `booking.datetime` as exact time on the repaired owner path
- add focused deterministic regression coverage for the surfaced booking-interrupt exact-time family
- sync canon/session/packet to the implementation block and move the next step to guarded replay

## Out of scope
- guarded llm-quality replay itself
- `ops/diagnose.py` or oracle changes
- duplicate-def cleanup beyond acknowledging the live later definition
- edits to `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`
- multi-pack acceptance or open-world closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn8-booking-interrupt-exact-time-progression-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn8-booking-interrupt-exact-time-progression-runtime-implementation-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`

## Plan (1..N)
1. Publish this implementation TP and promote canon/session references from the replay block to this runtime family.
2. Repair the live later duplicate `_try_handle_turn_planner_safe_booking_prompt_owner_cutover(...)` without touching frozen routers or duplicate counts.
3. Restore exact-time progression both for projected missing-slot calculation and for the live merged booking state before finalizing the prompt.
4. Add focused deterministic regression coverage for the surfaced booking-interrupt exact-time family.
5. Run focused regressions and mandatory governance checks.
6. Hand off the next move as guarded replay on the same locked canary family.

## DoD
- active canon points to this implementation TP
- turn `8` exact-time fill advances the active booking flow to `expected_reply_type=name`
- grounded `booking_slots.datetime` is preserved as exact time through the repaired owner path
- focused reasoning-core regressions pass
- mandatory packet / guard / architecture / session checks pass
- next non-negotiable move becomes guarded replay on the same canary family

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_prompt_owner_preserves_time_slot_constraint_after_pricing_interrupt or booking_prompt_owner_repairs_booking_interrupt_exact_time_progression or semantic_booking_prompt_merges_question_like_exact_time_progression or check_booking_prompt_owner"`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn8-booking-interrupt-exact-time-progression-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn8-booking-interrupt-exact-time-progression-runtime-implementation-a922.md`
- focused pytest output from the checks above
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** focused deterministic regressions only; guarded replay stays in the next block
- **Stop condition:** if the repair requires frozen-router edits, duplicate-def cleanup outside the live owner, or oracle weakening, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded non-frozen runtime cut plus focused regressions, then mandatory guards
- **Go/no-go signals:** new turn-8 regression passes, adjacent booking-prompt/check-booking continuity tests stay green, architecture/session guards stay green
- **Rollback:** revert `reasoning_core.py`, `test_reasoning_core.py`, TP/report/canon sync; regenerate packet; rerun guards
- **Post-release monitoring window:** next block must be guarded replay on the same canary family before any proof-lane tightening

## Rollback
1. Revert the non-frozen runtime/test changes.
2. Revert this TP/report/canon sync.
3. Rebuild packet and rerun the mandatory checks.

## No-go
- no frozen-router edits
- no second web query
- no proof/oracle patch first
- no phrase hardcodes for booking-interrupt phrasing
- no new acceptance claim without replay evidence

## Risks / blockers
- the owner lives inside a duplicate-def hotspot, so the repair must stay on the later live definition only
- replay may surface only proof debt or a new downstream family after the turn-8 stall is removed
- acceptance remains open until the same canary replay reruns on fresh runtime

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:`
  - duplicate defs remain in `truffles-api/app/services/reasoning_core.py`; only the live later definition is repaired here
  - guarded replay for the repaired turn-8 family is still pending
  - proof debt on turns `6`, `9`, and `11` remains unresolved until post-fix replay reclassification
- `Why not in this block:`
  - this block only lands the bounded runtime family plus deterministic regression
- `Risk if deferred:`
  - without replay, the repo still lacks truthful canary evidence that the turn-8 stall is gone on the real artifact lane
- `Linked follow-up Task Package(s):`
  - `rerun_consultant_core_demo_salon_turn8_booking_interrupt_exact_time_progression_canary_replay`
- `Expiry/trigger to stop deferral:`
  - stop deferral before any oracle tightening, acceptance claim, or new downstream runtime TP

## Next-block contract (mandatory)
- `Next block objective:`
  - rerun the locked canary replay on a refreshed local runtime and reclassify any remaining semantic red only after turn `8` is truthfully rechecked on the artifact lane
- `First deterministic check command:`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r17 --status done --strict-artifacts`
- `Blocked-by conditions:`
  - focused deterministic regression is not green
  - architecture/session guards fail
  - local runtime is stale relative to the worktree
- `Owner role for closure:`
  - `Hands`, reviewed by `Brain` / `Top Architect`
