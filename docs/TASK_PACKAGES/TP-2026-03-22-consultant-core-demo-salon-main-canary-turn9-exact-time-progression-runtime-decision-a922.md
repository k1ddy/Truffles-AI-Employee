# TP-2026-03-22 — Consultant Core Demo Salon Main Canary Turn 9 Exact-Time Progression Runtime Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-EXACT-TIME-PROGRESSION-RUNTIME-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-PREFLIGHT-PROOF-GAP-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-demo-salon-main-canary-preflight-proof-gap-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-EXACT-TIME-PROGRESSION-RUNTIME-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish one bounded runtime-family decision for refreshed canary turn `9` (`Могу ли я изменить время на 11 утра?`). This block must prove why the family is a real runtime contract bug, lock the admissible implementation lane to existing time-collect / question-contract semantics, keep downstream turn `12` as oracle debt only, and reject any fix that sneaks niche phrase logic or oracle weakening into core.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-21-consultant-core-demo-salon-main-canary-preflight-proof-gap-a922.md`
- `docs/REPORTS/artifacts/2026-03-21-consultant-core-demo-salon-main-canary-preflight-proof-gap-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/tests/test_booking_dialog_scenarios_script.py`
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
- `/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r12/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r12/manual_audit.json`

## FACT pre-check (before decision sync)
- `Impacted docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-decision-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-decision-a922.md`
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
  - `nl -ba truffles-api/tests/test_message_endpoint.py | sed -n '9006,9066p;17864,18182p'`
  - `nl -ba truffles-api/tests/test_booking_dialog_scenarios_script.py | sed -n '1582,1609p'`
  - `nl -ba truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml | sed -n '316,325p'`
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r12 --status done --strict-artifacts`
- `FACT findings`:
  - `/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl` shows turn `9` still emits `decision_action=booking_prompt`, `decision_source=llm_policy_core`, `expected_reply_type=time`, and `booking_slots.datetime='в субботу'` after explicit exact-time fill `11 утра`.
  - `truffles-api/tests/test_message_endpoint.py:9006-9066` already proves the expected-reply time contract must merge grounded exact time into booking `datetime` and clear stale queue state.
  - `truffles-api/tests/test_booking_dialog_scenarios_script.py:1582-1609` already proves explicit time fill inside `slot_constraint` normalizes out of the stale time-ask path into `reply_type=name`.
  - `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml:316-325` row `M13` already states that after `datetime` is grounded under active `slot_constraint`, canonical post-grounding contract becomes `expected_reply_type=name`.
  - `truffles-api/tests/test_message_endpoint.py:17864-18182` already proves exact-time reschedule-without-reference turns degrade to bounded handoff rather than silently re-asking `точное время`.
  - `/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl` turn `12` is downstream of the turn-9 stall and remains advisory because strict oracle still permits `booking_prompt` fallback while `booking_active=true`.
- `INFERENCE to verify in this block`:
  - the next truthful move is a bounded runtime implementation family for turn `9`; tightening turn `12` oracle first would hide downstream state corruption behind proof churn.

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa docs forms slot filling requested slot explicit value`
- **Date/time (local):** `2026-03-22T07:36:45+05:00`
- **Sources opened (from this query):**
  - `https://rasa.com/docs/rasa/forms/` (official docs; redirects to legacy OSS docs)
- **Source quality:** vendor documentation / primary source.
- **Existing solutions found:** active requested-slot loops should consume an explicit value and advance the flow; if the value cannot be safely applied, the system should exit or escalate explicitly rather than re-ask the same slot with stale state.
- **Decision:** `reuse/integrate/build`
  - reuse the repo's existing expected-reply merge contract, scenario-normalization contract, and bounded reschedule-handoff contract
  - integrate the future runtime fix into the existing generic question-contract / booking progression path
  - build only the missing bounded runtime-family implementation; do not add a new semantic bridge or phrase router
- **Rejected options:**
  - oracle tightening before runtime fix: rejected; turn `12` is downstream evidence only right now
  - phrase / regex hardcode for `11 утра` or similar variants: rejected; violates semantic-first charter
  - new scenario proliferation as a substitute for root-cause repair: rejected; scenario is evidence, not implementation

## Root cause (mandatory)
- **Symptom:** refreshed canary run `a922-check-booking-proof-r12` keeps turn `9` in stale `expected_reply_type=time` / `booking_prompt` state after the user provides explicit exact time (`11 утра`) under an active booking time-collect flow.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl` turn `8` and confirm the runtime asks for exact time while holding `booking_slots.datetime='в субботу'`.
  2. inspect the same artifact turn `9` and confirm the runtime still re-asks `Подскажите, пожалуйста, точное время.` instead of progressing or escalating.
  3. inspect `truffles-api/tests/test_message_endpoint.py:9006-9066` and confirm repo contract already requires exact-time merge plus stale expected-reply cleanup.
  4. inspect `truffles-api/tests/test_booking_dialog_scenarios_script.py:1582-1609` and `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml:316-325` and confirm explicit time fill under `slot_constraint` must normalize to `reply_type=name`.
  5. inspect `truffles-api/tests/test_message_endpoint.py:17864-18182` and confirm ambiguous reschedule-without-reference turns must hand off, not re-ask the exact-time slot forever.
- **Evidence:**
  - `/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl`
  - `/tmp/booking_quality/a922-check-booking-proof-r12/summary.json`
  - `/tmp/booking_quality/a922-check-booking-proof-r12/manual_audit.json`
  - `truffles-api/tests/test_message_endpoint.py:9006-9066`
  - `truffles-api/tests/test_booking_dialog_scenarios_script.py:1582-1609`
  - `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml:316-325`
  - `truffles-api/tests/test_message_endpoint.py:17864-18182`
- **Five Whys (or equivalent):**
  1. Why does turn `9` re-ask for exact time? Because the runtime resolves the turn through stale `booking_prompt` missing-slot semantics instead of consuming the explicit exact time.
  2. Why does the runtime still think `datetime` is missing? Because this family keeps only the partial-day scope (`в субботу`) and does not merge the grounded exact time into canonical booking state.
  3. Why is this a runtime bug instead of an oracle disagreement? Because deterministic repo contracts already require either `datetime` merge -> `expected_reply_type=name` progression or bounded handoff, and the artifact violates both.
  4. Why not tighten turn `12` first? Because turn `12` occurs after the stalled turn-9 state; current strict fallback does not prove an independent runtime defect there.
  5. Why is the fix bounded? Because the repo already has the right generic contracts; the missing piece is limited runtime execution of those contracts on this explicit exact-time progression family.
- **Root cause statement:** the current runtime family does not apply the existing exact-time progression contract when a user answers an active `time` collect with a grounded exact time, so stale `booking_prompt` / `expected_reply_type=time` state survives and blocks canonical progression or bounded handoff.
- **Fix mechanism:** publish one bounded implementation block that repairs exact-time progression on the active time-collect path using existing generic contracts, adds deterministic regression coverage for this family, and reruns the refreshed canary before any turn-12 oracle tightening.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing expected-reply time-merge contract in `truffles-api/tests/test_message_endpoint.py:9006-9066`
  - existing explicit-time scenario-normalization contract in `truffles-api/tests/test_booking_dialog_scenarios_script.py:1582-1609`
  - existing interaction-owner matrix row `M13` in `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml:316-325`
  - existing bounded reschedule-handoff contract in `truffles-api/tests/test_message_endpoint.py:17864-18182`
  - existing `llm-quality` run artifact `/tmp/booking_quality/a922-check-booking-proof-r12`
- **External reuse:**
  - official Rasa forms/requested-slot guidance only
- **Why not reinvent the wheel:**
  - the repo already defines what correct behavior is; the missing work is runtime conformance, not a new product contract.

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `30`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`:
  - this decision block is doc-only by intent, but the worktree already carries approved runtime diffs from earlier blocks; keeping `implementation` mode avoids false fail-closed governance on unrelated existing code changes.

## Invariant
- do not edit frozen webhook routers
- do not tighten turn `12` oracle before a post-fix rerun
- do not weaken judge / threshold / acceptance gates
- do not add phrase-hardcoded runtime branching for exact-time expressions
- do not claim any runtime seam deletion from this decision block alone

## Scope
- define the exact bounded runtime family rooted at refreshed canary turn `9`
- lock the admissible implementation objective to exact-time progression / bounded handoff semantics only
- keep turn `12` explicit deferred oracle debt
- switch canon/session/packet to this new decision block

## Out of scope
- runtime implementation in this block
- `ops/diagnose.py` oracle tightening
- new `llm-quality` run or baseline update
- edits to `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`
- multi-pack acceptance or open-world closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-decision-a922.md`
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
1. Publish this bounded turn-9 runtime decision TP and matching report with RCA, evidence, and the single-search record.
2. Switch canon/session artifacts from the proof-gap block to this new runtime-family decision block.
3. Rebuild the generated packet and rerun governance/session checks.
4. Hand off the exact next move as a bounded runtime implementation family; keep turn `12` in oracle debt until a post-fix rerun.

## DoD
- this TP and matching report exist and are the active block artifacts
- canon/packet/session all state that turn `9` is the next bounded runtime family and turn `12` remains deferred oracle debt
- `docs/SOURCE_OF_TRUTH.yaml` points `current_nonnegotiable_next_move` at the implementation of the turn-9 runtime family
- packet/guard stack stays green after sync
- no frozen runtime file is edited in this block

## Checks
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
- `nl -ba truffles-api/tests/test_message_endpoint.py | sed -n '9006,9066p;17864,18182p'`
- `nl -ba truffles-api/tests/test_booking_dialog_scenarios_script.py | sed -n '1582,1609p'`
- `nl -ba truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml | sed -n '316,325p'`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r12 --status done --strict-artifacts`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-runtime-decision-a922.md`
- `/tmp/booking_quality/a922-check-booking-proof-r12/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r12/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r12/manual_audit.json`
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0`
- `Fail-fast / scenario lock`: reuse existing `r12` artifact only
- `Stop condition`: if new evidence contradicts the runtime-bug classification, stop and publish a corrective decision before code
- `Escalation path`: `Top Architect`

## Release safety (mandatory for non-doc changes)
- Strategy: no runtime or rollout change in this block
- Go/no-go signals: packet/docs/guards stay green; frozen routers untouched
- Rollback: revert canon/session/doc/test changes and rebuild packet
- Post-release monitoring window: next block must implement the bounded runtime family and rerun before any oracle tightening

## Rollback
1. Revert this decision TP/report and matching canon/session updates.
2. Restore the proof-gap TP as active.
3. Rebuild the packet and rerun governance/session checks.

## No-go
- do not treat turn `12` as the next runtime bug from the current artifact alone
- do not patch `ops/diagnose.py` first
- do not push business-specific phrases into core to force exact-time recognition
- do not count this decision block as runtime progress
- do not reopen stale turn-10 proof drift as if it were still the blocker

## Risks / blockers
- the eventual runtime fix may expose that exact-time progression is split across more than one non-frozen owner lane
- turn `12` may disappear after the turn-9 fix rerun, which would invalidate any preemptive oracle work now
- acceptance remains blocked until the bounded runtime family lands and rerun evidence is collected

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - turn `9` exact-time progression runtime family remains unfixed
  - turn `12` oracle/proof weakness remains untightened until a post-fix rerun
  - guarded `demo_salon/main` acceptance rerun remains pending
  - multi-pack / open-world closure remains pending
- Why not in this block:
  - this block is the required classification/decision boundary before any new runtime code
- Risk if deferred:
  - without a bounded implementation block, the team can drift back into proof churn or ad-hoc phrase fixes
- Linked follow-up Task Package(s):
  - `implement_consultant_core_demo_salon_turn9_exact_time_progression_runtime_family`
- Expiry/trigger to stop deferral:
  - stop deferral immediately before any new llm-quality rerun, oracle tightening, or runtime patch outside the bounded family

## Next-block contract (mandatory)
- Next block objective:
  - implement the bounded runtime family that consumes explicit exact-time fills under active booking time-collect state, then rerun refreshed canary evidence before any turn-12 oracle work
- First deterministic check command:
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
- Blocked-by conditions:
  - this decision block not merged into canon
  - deterministic regression coverage for the exact-time family not yet authored
  - frozen-file scope would need widening
- Owner role for closure:
  - `Brain | Top Architect`
