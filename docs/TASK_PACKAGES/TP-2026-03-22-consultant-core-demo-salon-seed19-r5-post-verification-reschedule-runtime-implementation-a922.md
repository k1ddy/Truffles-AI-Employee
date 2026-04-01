# TP-2026-03-22 - Consultant Core Demo Salon Seed19 R5 Post Verification Reschedule Runtime Implementation A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R5-POST-VERIFICATION-RESCHEDULE-RUNTIME-IMPLEMENTATION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-SEED19-R5-POST-VERIFICATION-RESCHEDULE-RUNTIME-DECISION-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-decision-a922.md`
- `UNLOCKS`: `rerun_consultant_core_demo_salon_seed19_r5_post_verification_reschedule_canary_replay`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Implement one bounded runtime-family repair for fresh seed-`19` replay turn `13` (`Можно на 18:30?`). The fix is admissible only if post-verification exact-time reschedule preserves grounded `service`, updates `datetime`, and keeps `expected_reply_type=name` without touching frozen routers, oracle thresholds, or acceptance evidence assembly.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-decision-a922.md`
- `/tmp/booking_quality/a922-go2f-seed19-r5/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r5/responses.jsonl`
- `/tmp/booking_quality/a922-go2f-seed19-r5/manual_audit.json`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/architecture/test_no_duplicate_core_defs.py`

## FACT pre-check (before implementation)
- `Impacted code/docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md`
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
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r5 --status done --strict-artifacts`
  - `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-go2f-seed19-r5/responses.jsonl').read_text().splitlines() if line.strip()]
for row in rows:
    if row.get('dialog_index') == 1 and row.get('turn_index') in {12, 13}:
        print(json.dumps({
            'turn': row.get('turn_index'),
            'text': row.get('turn_text'),
            'decision_meta': row.get('decision_meta'),
            'booking_slots': row.get('booking_slots'),
            'strict_reasons': (row.get('evaluation') or {}).get('strict_reasons'),
        }, ensure_ascii=False, indent=2))
PY`
  - `nl -ba truffles-api/app/services/reasoning_core.py | sed -n '10768,10835p;13166,13240p'`
  - `nl -ba truffles-api/tests/test_reasoning_core.py | sed -n '15588,15880p'`
- `FACT findings`:
  - fresh replay `r5` is infra-valid and surfaces a runtime-only blocker at dialog `1`, turn `13`
  - the surviving family appears after booking verification already grounded `service='Маникюр'`, `datetime='15:00'`, and `expected_reply_type=name`
  - the live later booking-prompt owner path does not restore snapshot-grounded `service` / `datetime` before recomputing the next missing slot when the user only proposes a new exact time
  - the semantic booking recovery lane mirrors the same gap when policy-valid slots only carry the new exact time
  - deterministic coverage already exists for adjacent `name`-pending exact-time progression, but there is no focused regression for the post-verification reschedule family
- `Detected drift (docs vs code)`:
  - active canon still points to the decision block; once this runtime family lands, canon must promote the implementation block and hand off guarded replay

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa forms interruptions requested slot preserve filled slots official docs`
- **Date/time (local):** `2026-03-22T21:15:53+05:00`
- **Sources opened (from this query):**
  - `https://rasa.com/docs/rasa/forms/`
- **Source quality:** vendor documentation / primary source.
- **Existing solutions found:** requested-slot flows should preserve already filled slot state and continue from the first truly missing slot instead of reopening unrelated collection after an interruption or correction.
- **Decision:** `reuse/integrate`
  - reuse the repo's existing snapshot-grounding, exact-time merge, and earliest-missing-slot contracts
  - integrate the repair into the live post-verification reschedule continuity surfaces only
  - do not add a new oracle/proof bridge for this runtime family
- **Rejected options:**
  - second web query
  - frozen-router edits
  - proof/oracle changes first
  - phrase hardcode for `Можно на 18:30?`

## Root cause (mandatory)
- Symptom: fresh exact replay `r5` fails at dialog `1`, turn `13` because post-verification exact-time reschedule reopens generic booking collect with `expected_reply_type=service_choice` and drops grounded `service`.
- Minimal reproduction:
  1. inspect `/tmp/booking_quality/a922-go2f-seed19-r5/responses.jsonl` turn `12` and confirm booking verification leaves `service='Маникюр'`, `datetime='15:00'`, `expected_reply_type=name`
  2. inspect turn `13` on the same artifact and confirm the user turn `Можно на 18:30?` resets state to `booking_slots={'datetime': '18:30'}` with `expected_reply_type=service_choice`
  3. inspect the live later booking-prompt owner in `truffles-api/app/services/reasoning_core.py` and confirm it applies exact-time progression but does not rehydrate missing snapshot-grounded `service` before `_next_booking_prompt(...)`
  4. inspect the semantic booking recovery lane in the same file and confirm it likewise merges validated slots without snapshot service rehydration
- Evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r5/{summary.json,responses.jsonl,manual_audit.json}`
  - `truffles-api/app/services/reasoning_core.py:10768`
  - `truffles-api/app/services/reasoning_core.py:13166`
  - `truffles-api/tests/test_reasoning_core.py:15770`
- Five Whys:
  1. Why does turn `13` fail strict continuity? Because runtime asks for `service` again instead of keeping `name` pending.
  2. Why does runtime ask for `service` again? Because the active booking state loses grounded `service` while only the new exact time is merged.
  3. Why is grounded `service` lost? Because the live post-verification reschedule path relies on live booking state plus exact-time merge but does not restore missing service from `conversation_snapshot`.
  4. Why does this survive after exact-time progression fixes? Because exact-time merge alone only updates `datetime`; it does not restore grounded reference continuity.
  5. Why is the fix bounded? Because the repo already has snapshot-grounding and missing-slot selection contracts; this family only needs them wired into the live post-verification reschedule path.
- Root cause statement: post-verification exact-time reschedule currently merges the new time without rehydrating snapshot-grounded `service`, so the active booking state collapses to `datetime`-only and `_next_booking_prompt(...)` reopens `service_choice` instead of keeping `name` pending.
- Fix mechanism: rehydrate missing `service` / `datetime` from `conversation_snapshot` inside the live later booking-prompt owner and the adjacent semantic booking recovery lane before recomputing the next missing slot, then lock the family with deterministic regression.

## Reuse-first plan (mandatory)
- Internal reuse:
  - `_restore_turn_planner_snapshot_datetime_if_message_echo(...)`
  - `_apply_turn_planner_exact_time_progression_override(...)`
  - `decision_router._next_booking_prompt(...)`
  - `decision_router._first_missing_booking_slot(...)`
  - `ReasoningCoreConversationSnapshot.service_referent`
  - existing adjacent regressions in `truffles-api/tests/test_reasoning_core.py`
- External reuse:
  - official Rasa forms guidance only
- Why not reinvent the wheel:
  - the repo already owns slot progression and snapshot continuity; this block only makes the live post-verification reschedule family obey them.

## Work mode (mandatory)
- `Mode`: `implementation`
- `Why this mode`: this block changes live non-frozen runtime code and deterministic regression coverage for one bounded runtime family
- `Family handled in this block`: `seed19 r5 post-verification exact-time reschedule continuity`
- `Closure artifact expected from this mode`: focused deterministic green plus canon sync to the implementation handoff; guarded replay stays next

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `18`
- `Code dominance`: `single_runtime_family`
- `Override token`: `none`
- `Why this profile fits`:
  - the block is one bounded runtime repair with focused deterministic regressions and canon sync; replay stays in the next closure block

## Invariant
- do not edit frozen webhook routers
- do not weaken judge / threshold / acceptance gates
- do not add phrase-hardcoded branching for reschedule wording
- do not claim replay closure from deterministic proof alone
- do not widen duplicate-def cleanup beyond acknowledging the live later owner definition

## Scope
- repair the live post-verification reschedule continuity path so grounded `service` survives exact-time correction while `name` remains pending
- patch the adjacent semantic booking recovery lane for the same family contract
- add focused deterministic regression coverage for the surfaced family
- sync canon/session/packet to the implementation result and hand off guarded replay

## Out of scope
- guarded replay itself
- oracle/proof changes
- acceptance evidence-pack work
- frozen-router edits
- duplicate-def cleanup beyond this bounded family

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md`
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
1. Publish this implementation TP and promote canon/session references from the decision block to this runtime family.
2. Patch the live later booking-prompt owner so missing `service` / `datetime` are restored from `conversation_snapshot` before `_next_booking_prompt(...)`.
3. Patch the adjacent semantic booking recovery lane for the same continuity contract.
4. Add focused deterministic regression coverage for post-verification exact-time reschedule.
5. Run focused regressions and the mandatory guard/session stack.
6. Hand off the next move as one fresh exact replay on the same locked seed-`19` scenarios.

## DoD
- active canon points to this implementation TP
- post-verification exact-time reschedule preserves grounded `service` and keeps `expected_reply_type=name`
- focused deterministic regressions pass
- mandatory packet / guard / architecture / session checks pass
- next non-negotiable move becomes guarded replay on the same seed-`19` family

## Checks
- `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_prompt_owner_restores_snapshot_service_for_post_verification_reschedule or updates_grounded_datetime_while_name_pending or check_booking_prompt_owner"`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-seed19-r5-post-verification-reschedule-runtime-implementation-a922.md`
- `truffles-api/app/services/reasoning_core.py`
- `truffles-api/tests/test_reasoning_core.py`
- focused pytest output from the checks above
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- **Max full runs:** `0`
- **Max replay runs:** `0`
- **Fail-fast / scenario lock:** focused deterministic regressions only; fresh replay stays in the next block
- **Stop condition:** if the repair requires frozen-router edits, oracle weakening, or duplicate-def cleanup outside the live later owner surface, stop and publish `GAP`
- **Escalation path:** `Top Architect`

## Release safety (mandatory for non-doc changes)
- **Strategy:** bounded non-frozen runtime cut plus focused regressions, then mandatory guards
- **Go/no-go signals:** new post-verification reschedule regression passes, adjacent `name`-pending exact-time tests stay green, architecture/session guards stay green
- **Rollback:** revert `reasoning_core.py`, `test_reasoning_core.py`, TP/report/canon sync; regenerate packet; rerun guards
- **Post-release monitoring window:** next block must be one fresh exact replay on the same locked seed-`19` scenarios before any acceptance evidence work resumes

## Rollback
1. Revert the non-frozen runtime/test changes.
2. Revert this TP/report/canon sync.
3. Rebuild packet and rerun the mandatory checks.

## No-go
- no frozen-router edits
- no second web query
- no proof/oracle patch first
- no phrase hardcodes for reschedule wording
- no acceptance claim without fresh replay evidence

## Risks / blockers
- the hotspot still carries duplicate top-level defs, so the repair must stay on the live later owner plus the adjacent semantic recovery lane only
- fresh replay may expose a new downstream family once turn `13` is closed
- acceptance remains open until the same seed-`19` scenarios rerun on fresh runtime

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:`
  - duplicate defs remain in `truffles-api/app/services/reasoning_core.py`; only the live later owner plus adjacent semantic recovery lane are repaired here
  - guarded replay for the repaired `r5` family is still pending
  - seed `42` and acceptance `go_to_full` evidence-pack work remain paused behind this seed-`19` family closure
- `Why not in this block:`
  - this block only lands the bounded runtime family plus deterministic regression
- `Risk if deferred:`
  - without replay, the repo still lacks truthful evidence that the surfaced `r5` family is gone on the exact seed-`19` artifact lane
- `Linked follow-up Task Package(s):`
  - `rerun_consultant_core_demo_salon_seed19_r5_post_verification_reschedule_canary_replay`
- `Expiry/trigger to stop deferral:`
  - stop deferral before any new acceptance `lock`, seed `42`, or oracle/proof tightening

## Next-block contract (mandatory)
- `Next block objective:`
  - rerun the exact seed-`19` blocker scenarios on fresh local runtime and prove whether turn `13` is closed on truthful replay evidence
- `First deterministic check command:`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r6 --status done --strict-artifacts`
- `Blocked-by conditions:`
  - focused deterministic regressions fail
  - guard/session stack fails
  - fresh local runtime parity (`/admin/version.git_commit == HEAD`) cannot be established
- `Owner role for closure:`
  - `Brain / Top Architect`
