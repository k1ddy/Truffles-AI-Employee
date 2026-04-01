# TP-2026-03-22 — Consultant Core Demo Salon Main Canary Turn 11 Check-Booking Reference Continuity Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN11-CHECK-BOOKING-REFERENCE-CONTINUITY-RUNTIME-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEBUG-CADENCE-RESET-AND-SHADOW-DEF-GUARD-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-debug-cadence-reset-and-shadow-def-guard-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN11-CHECK-BOOKING-REFERENCE-CONTINUITY-CANARY-REPLAY-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Implement one bounded runtime-family repair for fresh canary turn `11` (`Подтвердите, пожалуйста, запись на маникюр.`). The fix is admissible only if the live non-frozen check-booking reference collect owner preserves grounded reference continuity from active booking/snapshot state, keeps the effective missing slot on the earliest missing reference slot, and leaves acceptance/oracle/frozen-router surfaces untouched.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-decision-a922.md`
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
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
- `/tmp/booking_quality/a922-check-booking-proof-r16/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r16/manual_audit.json`

## FACT pre-check (before implementation)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md`
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
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl').open(encoding='utf-8') if line.strip()]
for idx in [10, 11]:
    row = next(r for r in rows if r.get('turn_index') == idx)
    print(idx, row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('booking_slots'), row.get('evaluation'))
    print(json.dumps(row.get('decision_meta') or {}, ensure_ascii=False, indent=2))
PY`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '9460,9520p;10583,10790p'`
  - `nl -ba truffles-api/tests/test_reasoning_core.py | sed -n '9518,10125p'`
- `FACT findings`:
  - `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl` turn `11` still emits `check_booking_prompt`, but rewrites the active missing slot from `name` to `service`, drops grounded `booking_slots.datetime`, and fails strict state/reply checks.
  - The live owner is the later duplicate `_try_handle_turn_planner_safe_check_booking_prompt_owner_cutover` in `truffles-api/app/services/reasoning_core.py:10583`; this name is explicitly recorded in the shadow-def ledger and must be treated as duplicate-risk work.
  - The check-booking prompt owner currently derives `booking_last_question` straight from `llm_candidate["collect_slot"]` and builds slot values from the live conversation booking context, but it does not restore missing `service/datetime` from `conversation_snapshot` before finalizing the effective reference prompt.
  - The adjacent booking-verification fact owner already rehydrates `service`/`datetime` from `conversation_snapshot` before deciding whether the booking reference is complete; the prompt owner does not.
  - Existing reasoning-core tests already prove the happy reference-continuity path (`expected_reply_type=name`, grounded `datetime` preserved), but there is no deterministic guard for the stale `service_choice` / dropped-`datetime` repeated verification family.
- `Detected drift (docs vs code)`:
  - active canon still points to the meta-block; once this runtime family lands, canon must promote the implementation block and set the next non-negotiable move to guarded replay.

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa forms requested_slot preserve requested slot repeated user reply site:rasa.com docs`
- **Date/time (local):** `2026-03-22T11:04:37+05:00`
- **Sources opened (from this query):**
  - `https://rasa.com/docs/rasa/forms/`
- **Source quality:** vendor documentation / primary source.
- **Existing solutions found:** the active requested slot should remain tied to the first empty slot, and form progression should continue from grounded slot state rather than reopening unrelated slot collection.
- **Decision:** `reuse/integrate`
  - reuse the repo's existing booking-state merge and earliest-missing-slot contracts
  - integrate snapshot-backed continuity repair into the live check-booking prompt owner only
  - do not build a new proof/oracle bridge for this family
- **Rejected options:**
  - second web query
  - frozen-router edits
  - proof/oracle weakening first
  - phrase hardcode for `подтвердите запись` wording

## Root cause (mandatory)
- **Symptom:** truthful replay `r16` fails at turn `11` because repeated booking verification rewrites `expected_reply_type` from `name` to `service_choice` and drops grounded `booking_slots.datetime='в субботу 11:00'`.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl` turn `10` and confirm the prompt ends with `expected_reply_type=name` plus grounded `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 11:00'}`
  2. inspect turn `11` on the same artifact and confirm the next verification follow-up keeps the same text reply but changes runtime state to `expected_reply_type=service_choice` and `booking_slots={'service': 'Маникюр'}`
  3. inspect the live duplicate owner at `truffles-api/app/services/reasoning_core.py:10583`
  4. confirm it trusts `llm_candidate["collect_slot"]` as the effective collect slot and never rehydrates missing snapshot-grounded `service/datetime` before finalizing the reference prompt
  5. compare with `truffles-api/app/services/reasoning_core.py:9460-9520` and confirm the adjacent booking-verification owner already uses `conversation_snapshot` to recover reference continuity for gating
- **Evidence:**
  - `/tmp/booking_quality/a922-check-booking-proof-r16/summary.json`
  - `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl`
  - `/tmp/booking_quality/a922-check-booking-proof-r16/manual_audit.json`
  - `truffles-api/app/services/reasoning_core.py:9460-9520`
  - `truffles-api/app/services/reasoning_core.py:10583-10790`
  - `truffles-api/tests/test_reasoning_core.py:9518-10125`
- **Five Whys (or equivalent):**
  1. Why does turn `11` fail strict continuity? Because the owner asks for `service` instead of preserving the already grounded missing reference slot `name`.
  2. Why does it ask for `service`? Because the live owner accepts `llm_candidate["collect_slot"]` as final and does not normalize it back to the earliest missing slot after state recovery.
  3. Why is grounded `datetime` lost? Because the owner builds final slot values from live conversation booking state only, even when snapshot continuity still carries `booking_datetime_value`.
  4. Why is this a runtime bug, not proof debt? Because the contradiction is on structured contract fields (`expected_reply_type`, `booking_slots`), and deterministic repo tests already define the correct check-booking continuity behavior.
  5. Why is the fix bounded? Because the repo already has snapshot-grounding and earliest-missing-slot logic; the missing work is only wiring them into the live check-booking prompt owner.
- **Root cause statement:** the live duplicate check-booking prompt owner reconstructs reference collection from `llm_candidate` plus partial live booking context instead of rehydrating snapshot-grounded booking state and recomputing the effective earliest missing reference slot, so stale `service_choice` continuity can override the correct `name` prompt and drop `datetime`.
- **Fix mechanism:** in the live non-frozen check-booking prompt owner, rehydrate missing `service/datetime/active` from `conversation_snapshot` after message/LLM slot merging, recompute the effective missing slot with `_first_missing_booking_slot(...)`, and finalize the prompt from that effective slot/state; add focused deterministic regressions for the stale-service-choice family.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `decision_router._first_missing_booking_slot(...)`
  - `decision_router._booking_has_reference(...)`
  - `decision_router._update_booking_from_messages(...)`
  - `decision_router._expected_reply_for_booking_question(...)`
  - booking-verification snapshot grounding already present in `truffles-api/app/services/reasoning_core.py:9498-9507`
  - existing check-booking prompt owner tests in `truffles-api/tests/test_reasoning_core.py`
- **External reuse:**
  - official Rasa requested-slot guidance only
- **Why not reinvent the wheel:**
  - the repo already owns booking-state continuity and missing-slot selection; this block only makes the live check-booking prompt owner conform to those contracts.

## Work mode (mandatory)
- `Mode`: `implementation`
- `Why this mode`: this block changes live non-frozen runtime code and deterministic regressions for one bounded runtime family
- `Family handled in this block`: `check-booking reference continuity under stale service-choice / dropped datetime pressure`
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
- do not add phrase-hardcoded branching for booking verification wording
- do not claim acceptance closure from this block alone

## Scope
- repair the live turn-11 check-booking prompt owner so repeated verification preserves earliest missing reference continuity
- preserve grounded `booking.datetime` and `expected_reply_type=name` when service/datetime are already known
- add focused deterministic regression coverage for the surfaced stale-service-choice family
- sync canon/session/packet to the implementation block and move the next step to guarded replay

## Out of scope
- guarded llm-quality replay itself
- `ops/diagnose.py` or oracle changes
- duplicate-def cleanup beyond acknowledging the live later definition
- edits to `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`
- multi-pack acceptance or open-world closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md`
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
1. Publish this implementation TP and promote canon/session references from the meta-block to this runtime family.
2. Repair the live later duplicate `_try_handle_turn_planner_safe_check_booking_prompt_owner_cutover(...)` without touching frozen routers or duplicate counts.
3. Rehydrate snapshot-grounded booking state and normalize the effective reference collect slot to the earliest missing slot before finalizing the prompt.
4. Add focused deterministic regression coverage for the stale-service-choice / dropped-datetime repeated verification family.
5. Run focused regressions and mandatory governance checks.
6. Hand off the next move as guarded replay on the same locked canary family.

## DoD
- active canon points to this implementation TP
- turn `11` repeated verification preserves `expected_reply_type=name` when `service/datetime` are already grounded
- grounded `booking_slots.datetime` is preserved through the repaired owner path
- focused reasoning-core regressions pass
- mandatory packet / guard / architecture / session checks pass
- next non-negotiable move becomes guarded replay on the same canary family

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "check_booking_prompt_owner"`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-implementation-a922.md`
- focused pytest output from the checks above
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** focused deterministic regressions only; guarded replay stays in the next block
- **Stop condition:** if the repair requires frozen-router edits, duplicate-def cleanup outside the live owner, or oracle weakening, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded non-frozen runtime cut plus focused regressions, then mandatory guards
- **Go/no-go signals:** new turn-11 regression passes, adjacent check-booking continuity tests stay green, architecture/session guards stay green
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
- no phrase hardcodes for booking verification phrasing
- no new acceptance claim without replay evidence

## Risks / blockers
- the owner lives inside a duplicate-def hotspot, so the repair must stay on the later live definition only
- if the surfaced drift actually originates before snapshot construction, this repair may expose a new adjacent continuity debt on replay
- acceptance remains open until the same canary replay reruns on fresh runtime

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:`
  - duplicate defs remain in `truffles-api/app/services/reasoning_core.py`; only the live later definition is repaired here
  - guarded replay for the repaired turn-11 family is still pending
  - downstream turn `13` remains unresolved until replay reaches it again
- `Why not in this block:`
  - this block only lands the bounded runtime family plus deterministic regression
- `Risk if deferred:`
  - without replay, the repo still lacks truthful canary evidence that the surfaced turn-11 family is gone on the real artifact lane
- `Linked follow-up Task Package(s):`
  - `rerun_consultant_core_demo_salon_turn11_check_booking_reference_continuity_canary_replay`
- `Expiry/trigger to stop deferral:`
  - stop deferral before any oracle tightening, acceptance claim, or new downstream runtime TP

## Next-block contract (mandatory)
- `Next block objective:`
  - rerun the guarded canary path for the repaired turn-11 family and reclassify any surviving failures only from fresh evidence
- `First deterministic check command:`
  - `pytest -q truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_safe_check_booking_prompt_owner_bypasses_frozen_delegate truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_safe_check_booking_prompt_owner_accepts_verification_recovery_envelope truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_safe_check_booking_prompt_owner_repairs_repeated_reference_continuity_from_snapshot`
- `Blocked-by conditions:`
  - focused deterministic regressions go red
  - governance/session checks go red
  - replay would proceed without fresh packet/canon truth
- `Owner role for closure:` `Top Architect`
