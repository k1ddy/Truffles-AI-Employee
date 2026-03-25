# TP-2026-03-22 — Consultant Core Demo Salon Main Canary Turn 9 Exact-Time Progression Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-EXACT-TIME-PROGRESSION-RUNTIME-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-EXACT-TIME-PROGRESSION-RUNTIME-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-decision-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-EXACT-TIME-PROGRESSION-RUNTIME-RERUN-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Implement the bounded turn-9 runtime family without touching frozen routers. This block is admissible only if exact-time progression is repaired through existing generic expected-reply / booking-state contracts, the fix stays inside live non-frozen runtime code, and turn `12` remains deferred until a guarded post-fix replay decides whether any downstream oracle debt survives.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-decision-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
- `/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r12/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r12/manual_audit.json`

## FACT pre-check (before implementation)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-implementation-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-implementation-a922.md`
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
for idx in [8, 9, 12]:
    for line in Path('/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl').open(encoding='utf-8'):
        row = json.loads(line)
        if row.get('turn_index') == idx:
            print(idx, row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('booking_slots'), row.get('hq1_classes'))
            break
PY`
  - `rg -n "_apply_turn_planner_exact_time_progression_override|Turn planner safe semantic booking prompt|expected_reply_time_progression_override" truffles-api/app/services/reasoning_core.py truffles-api/tests/test_reasoning_core.py`
  - `pytest -q truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_booking_prompt_owner_preserves_time_slot_constraint_after_pricing_interrupt truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_booking_prompt_owner_keeps_time_followup_for_ambiguous_daypart_reply truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression truffles-api/tests/test_message_endpoint.py::test_expected_reply_time_merges_datetime_and_clears_stale_intent_queue truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_reschedule_missing_reference_escalates_to_handoff truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_reschedule_missing_reference_availability_phrase_escalates_to_handoff`
- `FACT findings`:
  - the live exact-time family is implemented inside non-frozen `truffles-api/app/services/reasoning_core.py`, not frozen routers
  - the fix reuses frozen deterministic helpers instead of adding new regex/phrase branches in core
  - focused regressions prove question-like exact time now grounds the booking datetime and advances to `expected_reply_type=name`
  - existing reschedule-without-reference endpoint contracts still pass unchanged
- `Detected drift (docs vs code)`:
  - once runtime code lands, active canon may not stay on the decision TP; it must promote the implementation block and move the next non-negotiable step to guarded replay

## One web search (mandatory before implementation)
- **Query (exact):** `dateparser parse time-only string relative base languages ru site:dateparser.readthedocs.io`
- **Date/time (local):** `2026-03-22T08:05:26+05:00`
- **Sources opened (from this query):**
  - `https://dateparser.readthedocs.io/en/latest/settings.html`
- **Source quality:** official library documentation / primary source.
- **Reuse rule for this block:** this exact query is the single implementation search; no second query is allowed or needed.
- **Existing solutions found:** time-only parsing should be anchored against an existing base date via `RELATIVE_BASE`; for this repo, the safer analogue is to reuse the existing expected-reply datetime merge contract instead of inventing a parallel parser path.
- **Decision:** `reuse/integrate`
  - reuse the repo's current expected-reply slot merger and bounded booking-state writer
  - integrate one non-frozen override only where question-like exact time is already inside an active time-collect family
- **Rejected options:**
  - second web query
  - patching frozen `booking.py` / `decision.py`
  - phrase hardcoding around `изменить время` / `11 утра`
  - tightening turn-12 oracle before replay

## Root cause (mandatory)
- **Symptom:** refreshed canary turn `9` keeps `booking_slots.datetime='в субботу'` and stale `expected_reply_type=time` after explicit exact-time fill `Могу ли я изменить время на 11 утра?`.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl` turn `9`
  2. confirm `decision_action=booking_prompt`, `decision_source=llm_policy_core`, `expected_reply_type=time`, `booking_slots.datetime='в субботу'`
  3. inspect `truffles-api/app/services/reasoning_core.py` semantic booking-prompt recovery and active booking-prompt owner paths
  4. confirm both paths can detect the active time-collect state but did not persist the merged grounded datetime into canonical booking context
- **Evidence:**
  - `/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl`
  - `truffles-api/tests/test_message_endpoint.py:9006`
  - `truffles-api/tests/test_booking_dialog_scenarios_script.py:1582`
  - `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml:316`
  - `truffles-api/app/services/reasoning_core.py`
- **Five Whys (or equivalent):**
  1. Why did turn `9` re-ask for exact time? Because runtime recovery kept the partial datetime and reopened the same missing-slot prompt.
  2. Why did runtime keep the partial datetime? Because the detected exact time was not merged through canonical expected-reply slot application on the live non-frozen recovery path.
  3. Why did that survive even after `reply_type=name` contracts existed elsewhere? Because final booking context writing only filled missing slots and therefore did not overwrite the already-populated partial datetime.
  4. Why is this a runtime bug and not only proof drift? Because deterministic repo contracts already require grounded exact time to advance or hand off.
  5. Why is the fix bounded? Because the repo already owns the merge and validation rules; only the non-frozen runtime execution path was missing them.
- **Root cause statement:** the live non-frozen runtime paths for semantic booking recovery and active booking prompt progression did not route question-like exact-time replies through the existing expected-reply datetime merger and canonical booking-state overwrite, so partial datetimes stayed stuck in context and the flow re-asked `time`.
- **Fix mechanism:** add one non-frozen exact-time progression helper in `reasoning_core.py`, reuse `decision_router._apply_expected_reply_slot(...)` plus `booking_payload_override`, and cover the repaired family with focused deterministic regressions.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `decision_router._apply_expected_reply_slot(...)`
  - `decision_router._is_datetime_grounded_for_prompt(...)`
  - `DialogStateService` booking payload writer via `_finalize_turn_planner_owner_cutover(...)`
  - existing message-endpoint / scenario-normalization / owner-matrix contracts
- **External reuse:**
  - dateparser settings guidance only
- **Why not reinvent the wheel:**
  - the repo already owns slot parsing and merge semantics; this block only makes the live runtime path conform to them

## Invariant
- do not edit frozen webhook routers
- do not weaken judge / threshold / acceptance gates
- do not tighten turn `12` oracle before post-fix replay
- do not add phrase-hardcoded runtime branching for niche wording
- do not claim open-world or multi-pack closure from this block

## Scope
- implement bounded exact-time progression in non-frozen runtime
- persist the merged grounded datetime into canonical booking context when that progression fires
- add focused deterministic regression coverage
- sync canon/session/packet to the implementation block and move the next step to guarded replay

## Out of scope
- guarded llm-quality replay itself
- turn `12` oracle tightening
- edits to `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`
- multi-pack acceptance or open-world closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-implementation-a922.md`
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
1. Publish this implementation TP and switch active canon/session references to it.
2. Repair exact-time progression in live non-frozen runtime by reusing the existing expected-reply datetime merger.
3. Persist the repaired datetime through canonical booking payload overwrite only when the bounded override fires.
4. Add focused regression coverage for question-like exact-time progression.
5. Run focused regressions and mandatory governance checks.
6. Hand off the next move as guarded replay before any turn-12 oracle work.

## DoD
- active canon points to this implementation TP
- turn `9` exact-time progression is repaired in non-frozen runtime only
- canonical booking context stores the merged grounded datetime for the repaired family
- focused reasoning-core and endpoint regressions pass
- mandatory packet / guard / architecture / session checks pass
- next non-negotiable move becomes guarded replay, not oracle tightening

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_booking_prompt_owner_preserves_time_slot_constraint_after_pricing_interrupt truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_booking_prompt_owner_keeps_time_followup_for_ambiguous_daypart_reply truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression truffles-api/tests/test_message_endpoint.py::test_expected_reply_time_merges_datetime_and_clears_stale_intent_queue truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_reschedule_missing_reference_escalates_to_handoff truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_reschedule_missing_reference_availability_phrase_escalates_to_handoff`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-implementation-a922.md`
- focused pytest outputs from the checks above
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Fail-fast / scenario lock:** focused deterministic regressions only; replay stays in the next block
- **Stop condition:** if the fix requires frozen-router edits or breaks existing reschedule contracts, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded non-frozen runtime cut plus focused regressions, then mandatory guards
- **Go/no-go signals:** new regression passes, endpoint contracts unchanged, architecture/session guards green
- **Rollback:** revert `reasoning_core.py`, `test_reasoning_core.py`, TP/report/canon sync, regenerate packet, rerun guards
- **Post-release monitoring window:** next block must be guarded replay on the exact canary family before any turn-12 oracle work

## Rollback
1. Revert the non-frozen runtime/test changes.
2. Revert this TP/report/canon sync.
3. Rebuild packet and rerun the mandatory checks.

## No-go
- no frozen-router edits
- no second web query
- no turn-12 oracle tightening first
- no phrase hardcodes for exact-time expressions
- no new proof claims without replay evidence

## Risks / blockers
- semantic booking recovery and active booking prompt owner share the same family; both had to stay aligned
- existing booking payload writing fills only missing slots, so the fix needed bounded overwrite on the repaired family
- acceptance remains open until guarded replay reruns the real canary artifact

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:`
  - guarded replay for the repaired family is still pending
  - turn `12` remains deferred oracle/proof debt until replay evidence exists
  - broader acceptance / open-world closure remains pending
- `Why not in this block:`
  - this block only lands the runtime family and focused deterministic proof
- `Risk if deferred:`
  - without replay, the repo still lacks truthful canary evidence that the surfaced family is gone on the real artifact lane
- `Linked follow-up Task Package(s):`
  - `rerun_consultant_core_demo_salon_turn9_exact_time_progression_canary_replay`
- `Expiry/trigger to stop deferral:`
  - stop deferral before any turn-12 oracle patch or acceptance-closure claim

## Next-block contract (mandatory)
- `Next block objective:`
  - rerun the guarded canary/replay path for the repaired turn-9 family and reclassify turn `12` only after fresh evidence
- `First deterministic check command:`
  - `pytest -q truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_booking_prompt_owner_preserves_time_slot_constraint_after_pricing_interrupt truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_booking_prompt_owner_keeps_time_followup_for_ambiguous_daypart_reply truffles-api/tests/test_reasoning_core.py::test_reasoning_core_turn_planner_semantic_booking_prompt_merges_question_like_exact_time_progression truffles-api/tests/test_message_endpoint.py::test_expected_reply_time_merges_datetime_and_clears_stale_intent_queue truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_reschedule_missing_reference_escalates_to_handoff truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_reschedule_missing_reference_availability_phrase_escalates_to_handoff`
- `Blocked-by conditions:`
  - focused deterministic regressions go red
  - governance/session checks go red
  - replay would proceed without fresh packet/canon truth
- `Owner role for closure:` `Top Architect`
