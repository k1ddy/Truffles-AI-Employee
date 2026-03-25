# TP-2026-03-22 — Consultant Core Demo Salon Main Canary Turn 11 Check-Booking Reference Continuity Runtime Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN11-CHECK-BOOKING-REFERENCE-CONTINUITY-RUNTIME-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN13-NAME-PROGRESSION-CANARY-REPLAY-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-canary-replay-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN11-CHECK-BOOKING-REFERENCE-CONTINUITY-RUNTIME-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish one bounded runtime-family decision for fresh canary turn `11` (`Подтвердите, пожалуйста, запись на маникюр.`). This block must prove that turn `9` stays repaired on the fresh post-fix replay, that turn `10` remains non-blocking, and that the new surviving blocker is a real runtime continuity bug where the check-booking reference collect lane drops grounded booking state and rewrites `expected_reply_type` from `name` to `service_choice` before turn `13` is even reached.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-canary-replay-a922.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-implementation-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
- `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r16/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r16/manual_audit.json`

## FACT pre-check (before decision sync)
- `Impacted docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-decision-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-decision-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-canary-replay-a922.md`
  - `docs/ACTIVE_PROGRAM.md`
  - `docs/SOURCE_OF_TRUTH.yaml`
  - `STATE.md`
  - `STRUCTURE.md`
  - `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
  - `docs/SESSION_INDEX.md`
  - `docs/_generated/AGENT_PACKET.md`
  - `docs/_generated/AGENT_PACKET.json`
  - `truffles-api/tests/architecture/test_arch_guard_packet.py`
- `Baseline commands`:
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r16 --status done --strict-artifacts`
  - `python3 - <<'PY'
import json
from pathlib import Path
for run_id in ['a922-check-booking-proof-r14', 'a922-check-booking-proof-r16']:
    rows=[json.loads(line) for line in Path(f'/tmp/booking_quality/{run_id}/responses.jsonl').open(encoding='utf-8') if line.strip()]
    print('RUN', run_id)
    for idx in [9, 10, 11]:
        row = next((r for r in rows if r.get('turn_index') == idx), None)
        print(idx, row and row['turn_text'], row and row['outbox_text'], row and row.get('expected_reply_type'), row and row.get('booking_slots'), row and row.get('evaluation'))
PY`
  - `nl -ba truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml | sed -n '903,943p'`
- `FACT findings`:
  - `/tmp/booking_quality/a922-check-booking-proof-r16/summary.json` is `infra_valid=true`, `semantic_valid=false`, and stops on the first strict failure at turn `11`.
  - `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl` proves turn `9` remains repaired and turn `10` remains strict-green on the fresh replay.
  - On turn `11`, the runtime still emits `check_booking_prompt`, but now rewrites `expected_reply_type` from `name` to `service_choice` and drops `booking_slots.datetime`, causing `expected_state_mismatch` + `expected_reply_mismatch`.
  - `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl` proves the same turn previously preserved `expected_reply_type=name` and `booking_slots={'service': 'Маникюр', 'datetime': 'в субботу 11:00'}`.
  - Because `r16` stops at turn `11`, fresh replay does not reach turn `13`; the old explicit-name family is no longer the first surviving blocker.
- `INFERENCE to verify in this block`:
  - the next truthful move is a bounded runtime implementation family for turn `11` continuity, not another replay or oracle patch.

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa docs forms slot mappings from text requested slot explicit value`
- **Date/time (local):** `2026-03-22T09:00:00+05:00`
- **Sources opened (from this query):**
  - `https://rasa.com/docs/rasa/forms/`
- **Source quality:** vendor documentation / primary source.
- **Reuse rule for this block:** reuse the exact search already recorded in the turn-13 runtime implementation lane; no second query is allowed or needed.
- **Existing solutions found:** once a requested slot is already grounded, follow-up turns should preserve that slot state instead of reopening unrelated slot collection.
- **Decision:** `reuse/integrate`
  - reuse the repo's existing expected-reply / booking-state continuity contracts
  - integrate the future fix into the live check-booking reference collect path
  - do not build a new scenario/oracle bridge in this block
- **Rejected options:**
  - another replay before classification
  - oracle tightening first
  - phrase-hardcoded handling for booking confirmation wording
  - frozen-router edits

## Root cause (mandatory)
- **Symptom:** fresh replay `r16` fails at turn `11` because the booking-verification collect-reference path drops grounded booking state and rewrites the active expected reply from `name` to `service_choice`.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl` turn `10` and confirm the runtime still asks for booking reference details with `expected_reply_type=name` and grounded `booking_slots.datetime='в субботу 11:00'`
  2. inspect the same artifact turn `11` and confirm the next verification follow-up keeps the same text reply but changes runtime state to `expected_reply_type=service_choice` and `booking_slots={'service': 'Маникюр'}`
  3. compare against `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl` turn `11` and confirm the same turn previously preserved the `name`/full-datetime continuity state
  4. inspect `decision_meta.expected_reply_bypassed=booking_verification` and `llm_policy_core_collect_slot=service` on `r16` turn `11`
  5. confirm the strict failure is contract-level (`expected_state_mismatch`, `expected_reply_mismatch`), not judge-only wording drift
- **Evidence:**
  - `/tmp/booking_quality/a922-check-booking-proof-r16/summary.json`
  - `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl`
  - `/tmp/booking_quality/a922-check-booking-proof-r16/manual_audit.json`
  - `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl`
  - `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml:903-943`
- **Five Whys:**
  1. Why did the fresh replay stop before turn `13`? Because turn `11` became the first strict failure on the locked scenario surface.
  2. Why is turn `11` a strict failure? Because runtime state no longer matches the contract after the repeat check-booking follow-up.
  3. Why is this not just oracle drift? Because the failure is on structured contract fields (`expected_reply_type`, `booking_slots`) rather than reply wording alone.
  4. Why does the state drift matter? Because it discards already grounded booking reference continuity and changes the missing-slot owner mid-flow.
  5. Why is the next move bounded? Because the contradiction is localized to the check-booking reference collect path under active expected-reply continuity.
- **Root cause statement:** the live check-booking verification collect path is bypassing/pivoting active reference continuity and reconstructing missing reference slots from scratch, which drops grounded `datetime` state and rewrites the requested slot from `name` to `service`.
- **Fix mechanism:** publish one bounded runtime implementation block that preserves active check-booking reference continuity on the surfaced non-frozen path, adds deterministic regression coverage for the exact turn-11 family, and only then reruns the same canary.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - fresh replay artifact `/tmp/booking_quality/a922-check-booking-proof-r16`
  - truthful comparison artifact `/tmp/booking_quality/a922-check-booking-proof-r14`
  - existing generic interaction matrix in `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
  - existing check-booking prompt owner and continuity contracts already exercised by the canary lane
- **External reuse:**
  - official Rasa forms/requested-slot guidance already recorded in the prior turn-13 lane
- **Why not reinvent the wheel:**
  - the repo already has the expected-reply/slot continuity contract; the missing work is runtime conformance on one bounded collect-reference family

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `34`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`:
  - this decision block is doc-only by intent, but the worktree already contains approved runtime diffs and replay artifacts; keeping `implementation` mode avoids false governance failures on the existing code delta.

## Invariant
- do not edit frozen webhook routers
- do not reopen turn `9` as an active blocker
- do not weaken judge / threshold / acceptance gates
- do not treat turn `13` as closed without fresh evidence that reaches it
- do not add phrase-hardcoded branching for booking confirmation wording

## Scope
- define the exact bounded runtime family rooted at fresh canary turn `11`
- lock turn `9` as still repaired and turn `10` as still non-blocking on the fresh replay
- demote turn `13` from active blocker to downstream unresolved debt because the new replay never reaches it
- switch canon/session/packet to this new decision block

## Out of scope
- runtime implementation in this block
- `ops/diagnose.py` oracle changes
- new replay beyond the already completed `r16`
- edits to `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`
- multi-pack acceptance or open-world closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-canary-replay-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `STRUCTURE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Publish the truthful `r16` replay findings in the existing replay report.
2. Publish this bounded turn-11 runtime decision TP and matching report with RCA and reuse record.
3. Switch canon/session artifacts from the replay block to this new runtime-family decision block.
4. Rebuild the generated packet and rerun governance/session checks.
5. Hand off the exact next move as a bounded runtime implementation family for turn `11` continuity.

## DoD
- this TP and matching report exist and are the active block artifacts
- the replay report truthfully records invalid pre-run artifacts, truthful `r16`, and turn `11` as the first surviving blocker
- canon/packet/session all state that turn `11` is the next bounded runtime family
- `docs/SOURCE_OF_TRUTH.yaml` points `current_nonnegotiable_next_move` at the implementation of the turn-11 runtime family
- packet/guard stack stays green after sync
- no frozen runtime file is edited in this block

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r16 --status done --strict-artifacts`
- `python3 - <<'PY'
import json
from pathlib import Path
for run_id in ['a922-check-booking-proof-r14', 'a922-check-booking-proof-r16']:
    rows=[json.loads(line) for line in Path(f'/tmp/booking_quality/{run_id}/responses.jsonl').open(encoding='utf-8') if line.strip()]
    print('RUN', run_id)
    for idx in [9, 10, 11]:
        row = next((r for r in rows if r.get('turn_index') == idx), None)
        print(idx, row and row['turn_text'], row and row['outbox_text'], row and row.get('expected_reply_type'), row and row.get('booking_slots'), row and row.get('evaluation'))
PY`
- `nl -ba truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml | sed -n '903,943p'`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn11-check-booking-reference-continuity-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-canary-replay-a922.md`
- `/tmp/booking_quality/a922-check-booking-proof-r16/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r16/manual_audit.json`
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0`
- `Fail-fast / scenario lock`: reuse existing `r16` artifact only
- `Stop condition`: if fresh code exploration disproves the runtime-bug classification, stop and publish a corrective decision before code
- `Escalation path`: `Top Architect`

## Release safety (mandatory for non-doc changes)
- Strategy: no runtime or rollout change in this block
- Go/no-go signals: packet/docs/guards stay green; frozen routers untouched
- Rollback: revert canon/session/doc/test changes and rebuild packet
- Post-release monitoring window: next block must implement the bounded runtime family and rerun before any new proof-lane classification

## Rollback
1. Revert this decision TP/report and matching canon/session updates.
2. Restore the replay TP as active.
3. Rebuild the packet and rerun governance/session checks.

## No-go
- do not reopen turn `9` as active runtime debt
- do not patch `ops/diagnose.py` first
- do not count turn `13` as closed or reopened without a replay that reaches it
- do not widen into frozen routers
- do not count this decision block as runtime progress

## Risks / blockers
- the bounded runtime family may live close to existing check-booking prompt continuity logic, so implementation must avoid regressing turn `10` / turn `12`
- because `r16` stops at turn `11`, the old explicit-name family remains unresolved downstream and must be revisited only after the new blocker is fixed
- final acceptance still remains open until a later replay reaches and classifies the downstream turns again

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:`
  - turn `11` runtime family is still unfixed
  - turn `13` remains unresolved downstream debt because `r16` no longer reaches it
  - judge conflicts on turns `6` and `9` remain proof debt only
  - multi-pack / open-world closure remains pending
- `Why not in this block:`
  - this block only classifies the truthful fresh replay artifact and locks the next bounded runtime family
- `Risk if deferred:`
  - without a bounded turn-11 decision, the team would either reopen stale turn-13 work or mix runtime and proof lanes again
- `Linked follow-up Task Package(s):`
  - `implement_consultant_core_demo_salon_turn11_check_booking_reference_continuity_runtime_family`
- `Expiry/trigger to stop deferral:`
  - stop deferral before any new replay or oracle tightening

## Next-block contract (mandatory)
- `Next block objective:`
  - implement the bounded turn-11 check-booking reference continuity runtime family and add deterministic coverage for the exact surfaced mismatch
- `First deterministic check command:`
  - `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r16/responses.jsonl').open(encoding='utf-8') if line.strip()]
row = next(r for r in rows if r.get('turn_index') == 11)
print(row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('booking_slots'), row.get('evaluation'))
PY`
- `Blocked-by conditions:`
  - fresh code inspection disproves the runtime classification
  - governance/session checks go red
  - implementation would require frozen-router edits
- `Owner role for closure:` `Top Architect`
