# TP-2026-03-22 — Consultant Core Demo Salon Main Canary Turn 9 Grounded Datetime Reschedule Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-GROUNDED-DATETIME-RESCHEDULE-RUNTIME-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN8-BOOKING-INTERRUPT-EXACT-TIME-PROGRESSION-CANARY-REPLAY-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn8-booking-interrupt-exact-time-progression-canary-replay-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-GROUNDED-DATETIME-RESCHEDULE-CANARY-REPLAY-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Implement one bounded runtime-family repair for fresh canary turn `9` (`Могу ли я изменить время на 11 утра?`). The fix is admissible only if the live non-frozen runtime updates grounded `booking.datetime` from `10:00` to `11:00` while the collect contract stays on `name`, and leaves proof/oracle/frozen-router surfaces untouched.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn8-booking-interrupt-exact-time-progression-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn8-booking-interrupt-exact-time-progression-canary-replay-a922.md`
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
- `/tmp/booking_quality/a922-check-booking-proof-r18/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r18/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r18/trace_bundle.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r18/manual_audit.json`
- `/tmp/booking_quality/a922-weekend-slot-constraint-dialog-sanitized-r10.json`

## FACT pre-check (before implementation)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-grounded-datetime-reschedule-runtime-implementation-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-grounded-datetime-reschedule-runtime-implementation-a922.md`
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
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r18/responses.jsonl').open(encoding='utf-8') if line.strip()]
for idx in [8, 9, 11, 13]:
    row = next(r for r in rows if r.get('turn_index') == idx)
    print(idx, row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('booking_slots'))
    print(json.dumps(row.get('decision_meta') or {}, ensure_ascii=False, indent=2))
PY`
  - `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r18/trace_bundle.jsonl').open(encoding='utf-8') if line.strip()]
row = next(r for r in rows if r.get('turn_index') == 9)
print(json.dumps(row.get('decision_trace') or [], ensure_ascii=False, indent=2))
PY`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '800,930p;10450,10640p;13056,13120p'`
  - `nl -ba truffles-api/tests/test_reasoning_core.py | sed -n '15090,15280p'`
- `FACT findings`:
  - `/tmp/booking_quality/a922-check-booking-proof-r18/responses.jsonl` proves turn `8` is repaired: runtime now asks for `name` and persists `booking_slots.datetime='в субботу 10:00'` with `expected_reply_time_progression_override=true`.
  - The same artifact surfaces turn `9` as the next runtime bug: the user changes the time to `11 утра`, runtime keeps `expected_reply_type=name`, but leaves `booking_slots.datetime='в субботу 10:00'` and emits no exact-time progression meta.
  - `/tmp/booking_quality/a922-check-booking-proof-r18/manual_audit.json` keeps `winner=contract`; HQ1 `handoff_miss` is advisory proof debt, not the root runtime defect.
  - In `truffles-api/app/services/reasoning_core.py`, `_restore_turn_planner_snapshot_datetime_if_message_echo(...)` already repairs raw message echo contamination, but the grounded reschedule path still needs an explicit exact-time replacement while `reply_slot == name`.
  - `_apply_turn_planner_exact_time_progression_override(...)` is the existing repo helper for exact-time progression, but before this block it did not replace an already-grounded exact time like `в субботу 10:00` with a new exact time like `11:00`.
  - The semantic booking recovery branch around `truffles-api/app/services/reasoning_core.py:13069-13093` is the live non-frozen continuity owner for this family; it already applies name progression while `reply_slot == name`, but it must also update grounded datetime before finalizing the same collect step.
  - Existing deterministic tests cover adjacent exact-time and check-booking contracts, but there is no focused regression for `turn 9` style grounded reschedule while `name` remains pending.
- `Detected drift (docs vs code)`:
  - active canon still points to the turn-8 implementation block; once this family lands, canon must promote turn-9 implementation as the active block and set the next non-negotiable move to guarded replay.

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa forms change previously filled slot while another requested slot site:rasa.com/docs`
- **Date/time (local):** `2026-03-22T12:35:00+05:00`
- **Sources opened (from this query):**
  - `https://rasa.com/docs/rasa/forms/`
- **Source quality:** vendor documentation / primary source.
- **Existing solutions found:** conversation state must tolerate users correcting already-captured information while another follow-up question remains active; the system should update the corrected slot and continue the current collection step instead of discarding the correction.
- **Decision:** `reuse/integrate/build`
  - reuse the repo's exact-time progression helper and semantic booking recovery path
  - integrate grounded-datetime replacement into the name-pending recovery lane
  - build only the missing runtime continuity patch and deterministic regression; do not widen into proof/oracle or frozen-router work
- **Rejected options:**
  - second web query
  - frozen-router edits
  - proof/oracle weakening first
  - phrase hardcode for reschedule wording

## Root cause (mandatory)
- **Symptom:** truthful replay `r18` remains semantic-red because turn `9` keeps stale `booking_slots.datetime='в субботу 10:00'` after the user explicitly changes the time to `11 утра`, even though the collect contract correctly stays on `name`.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/a922-check-booking-proof-r18/responses.jsonl` turns `8` and `9`
  2. confirm turn `8` grounds `booking.datetime='в субботу 10:00'` and advances to `expected_reply_type=name`
  3. confirm turn `9` user text (`Могу ли я изменить время на 11 утра?`) still yields `expected_reply_type=name` but preserves `booking_slots.datetime='в субботу 10:00'`
  4. inspect `_apply_turn_planner_exact_time_progression_override(...)` at `truffles-api/app/services/reasoning_core.py:830-923`
  5. confirm the pre-fix helper does not replace an already-grounded exact time with a new exact-time token
  6. inspect the semantic booking recovery path at `truffles-api/app/services/reasoning_core.py:13069-13110` and confirm the `reply_slot == name` lane applies name progression without first repairing grounded datetime reschedule continuity
- **Evidence:**
  - `/tmp/booking_quality/a922-check-booking-proof-r18/responses.jsonl`
  - `/tmp/booking_quality/a922-check-booking-proof-r18/trace_bundle.jsonl`
  - `/tmp/booking_quality/a922-check-booking-proof-r18/manual_audit.json`
  - `truffles-api/app/services/reasoning_core.py:830-923`
  - `truffles-api/app/services/reasoning_core.py:13069-13110`
  - `truffles-api/tests/test_reasoning_core.py:15104`
- **Five Whys:**
  1. Why does turn `9` keep stale `10:00`? Because the continuity owner asks for `name` correctly but never rewrites grounded `booking.datetime` to the new exact time.
  2. Why is the grounded datetime not rewritten? Because the exact-time progression helper used in this family did not replace an already-grounded exact time.
  3. Why does the name-pending recovery lane not repair it elsewhere? Because the semantic booking recovery path applies explicit-name progression while `reply_slot == name`, but pre-fix it did not run exact-time progression first.
  4. Why was that gap not caught earlier? Because turn `8` had to be repaired first before replay could surface the grounded reschedule family independently.
  5. Why does replay still look partially green? Because current strict/oracle surfaces do not flag the stale-datetime regression as a turn failure even when runtime state is wrong.
- **Root cause statement:** after turn `8` grounds `booking.datetime='в субботу 10:00'`, the live name-pending recovery lane does not replace that grounded exact time when the user reschedules to `11 утра`; the existing exact-time helper also needs to support grounded exact-time replacement instead of only filling missing time.
- **Fix mechanism:** extend `_apply_turn_planner_exact_time_progression_override(...)` to replace already-grounded exact times, restore snapshot datetime before that override when message parsing echoes raw text, and run the same exact-time progression inside the `reply_slot == name` semantic booking recovery lane before name progression finalizes.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `_restore_turn_planner_snapshot_datetime_if_message_echo(...)`
  - `_apply_turn_planner_exact_time_progression_override(...)`
  - `_apply_turn_planner_explicit_name_progression_override(...)`
  - `_build_exact_time_progression_trace_payload(...)`
  - existing adjacent exact-time / check-booking tests in `truffles-api/tests/test_reasoning_core.py`
- **External reuse:**
  - official Rasa forms requested-slot guidance only
- **Why not reinvent the wheel:**
  - the repo already owns exact-time progression semantics and trace payload helpers; this block only restores grounded reschedule continuity on the live name-pending owner path.

## Work mode (mandatory)
- `Mode`: `implementation`
- `Why this mode`: this block changes live non-frozen runtime code and deterministic regressions for one bounded runtime family
- `Family handled in this block`: `grounded datetime reschedule while expected_reply_type=name`
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
- do not remove or silently grow duplicate defs; work only in the live non-frozen owner path
- do not add phrase-hardcoded branching for reschedule wording
- do not claim acceptance closure from this block alone

## Scope
- repair the live turn-9 grounded reschedule continuity so the new exact time survives while the collect contract stays on `name`
- preserve grounded `booking.datetime` as `в субботу 11:00` on the repaired owner path
- add focused deterministic regression coverage for the surfaced grounded-datetime reschedule family
- sync canon/session/packet to the implementation block and move the next step to guarded replay

## Out of scope
- guarded llm-quality replay itself
- `ops/diagnose.py` or oracle changes
- duplicate-def cleanup beyond acknowledging the live later definition
- edits to `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`
- multi-pack acceptance or open-world closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-grounded-datetime-reschedule-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-grounded-datetime-reschedule-runtime-implementation-a922.md`
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
1. Publish this implementation TP and promote canon/session references from turn-8 replay to this runtime family.
2. Extend exact-time progression so grounded exact times can be replaced, not only filled from missing `datetime`.
3. Repair the live semantic booking recovery path so exact-time reschedule progression runs before explicit-name continuation while `reply_slot == name`.
4. Add focused deterministic regression coverage for the surfaced grounded-datetime reschedule family.
5. Run focused regressions and mandatory governance checks.
6. Hand off the next move as guarded replay on the same locked canary family.

## DoD
- active canon points to this implementation TP
- turn `9` exact-time reschedule keeps the collect contract on `name`
- grounded `booking_slots.datetime` is updated to `в субботу 11:00` through the repaired owner path
- focused reasoning-core regressions pass
- mandatory packet / guard / architecture / session checks pass
- next non-negotiable move becomes guarded replay on the same canary family

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "updates_grounded_datetime_while_name_pending or semantic_booking_prompt_merges_question_like_exact_time_progression or booking_prompt_owner_repairs_booking_interrupt_exact_time_progression or check_booking_prompt_owner"`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-grounded-datetime-reschedule-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-grounded-datetime-reschedule-runtime-implementation-a922.md`
- focused pytest output from the checks above
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** focused deterministic regressions only; guarded replay stays in the next block
- **Stop condition:** if the repair requires frozen-router edits, duplicate-def cleanup outside the live owner, or oracle weakening, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded non-frozen runtime cut plus focused regressions, then mandatory guards
- **Go/no-go signals:** new turn-9 regression passes, adjacent exact-time and check-booking continuity tests stay green, architecture/session guards stay green
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
- no phrase hardcodes for grounded reschedule phrasing
- no new acceptance claim without replay evidence

## Risks / blockers
- the owner lives inside a duplicate-def hotspot, so the repair must stay on the live path only
- replay may surface only proof debt or a new downstream family after the turn-9 reschedule regression is removed
- acceptance remains open until the same canary replay reruns on fresh runtime

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:`
  - duplicate defs remain in `truffles-api/app/services/reasoning_core.py`; only the live non-frozen path is repaired here
  - guarded replay for the repaired turn-9 family is still pending
  - proof debt on turns `6`, `9`, and `11` remains unresolved until post-fix replay reclassification
- `Why not in this block:`
  - this block only lands the bounded runtime family plus deterministic regression
- `Risk if deferred:`
  - without replay, the repo still lacks truthful canary evidence that grounded reschedule continuity is repaired on the real artifact lane
- `Linked follow-up Task Package(s):`
  - `rerun_consultant_core_demo_salon_turn9_grounded_datetime_reschedule_canary_replay`
- `Expiry/trigger to stop deferral:`
  - stop deferral before any oracle tightening, acceptance claim, or new downstream runtime TP

## Next-block contract (mandatory)
- `Next block objective:`
  - rerun the locked canary replay on a refreshed local runtime and reclassify any remaining semantic red only after turn `9` grounded datetime reschedule is truthfully rechecked on the artifact lane
- `First deterministic check command:`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r18 --status done --strict-artifacts`
- `Blocked-by conditions:`
  - focused deterministic regression is not green
  - architecture/session guards fail
  - local runtime is stale relative to the worktree
- `Owner role for closure:`
  - `Hands`, reviewed by `Brain` / `Top Architect`
