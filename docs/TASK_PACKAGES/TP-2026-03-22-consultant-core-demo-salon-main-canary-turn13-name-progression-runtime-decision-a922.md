# TP-2026-03-22 — Consultant Core Demo Salon Main Canary Turn 13 Name Progression Runtime Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN13-NAME-PROGRESSION-RUNTIME-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-EXACT-TIME-PROGRESSION-CANARY-REPLAY-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN13-NAME-PROGRESSION-RUNTIME-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish one bounded runtime-family decision for fresh canary turn `13` (`Меня зовут Амина.`). This block must prove that turn `9` is repaired on the refreshed runtime, that turn `12` now satisfies the handoff contract on the same artifact, and that the surviving blocker is a real runtime contract bug where explicit name fill loops back into stale `booking_prompt/name` instead of progressing booking completion or bounded handoff.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `truffles-api/tests/test_reasoning_core.py`
- `truffles-api/tests/test_message_endpoint.py`
- `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml`
- `/tmp/booking_quality/a922-check-booking-proof-r14/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r14/manual_audit.json`
- `/tmp/booking_quality/a922-check-booking-proof-r14/failure_families.json`

## FACT pre-check (before decision sync)
- `Impacted docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-decision-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-decision-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md`
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
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r14 --status done --strict-artifacts`
  - `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl').open(encoding='utf-8') if line.strip()]
for idx in [9, 12, 13]:
    row = next(r for r in rows if r.get('turn_index') == idx)
    print(idx, row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('conversation_state'), row.get('booking_slots'), row.get('evaluation'))
PY`
  - `nl -ba truffles-api/tests/test_reasoning_core.py | sed -n '8689,8788p'`
  - `nl -ba truffles-api/tests/test_message_endpoint.py | sed -n '16162,16327p'`
  - `nl -ba truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml | sed -n '903,943p'`
- `FACT findings`:
  - `/tmp/booking_quality/a922-check-booking-proof-r14/summary.json` is now `infra_valid=true` on the refreshed local runtime and fails semantically only because `turn 13` hits `booking_slot_stall`.
  - `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl` proves turn `9` now advances to `expected_reply_type=name` with `booking_slots.datetime='в субботу 11:00'`.
  - The same artifact proves turn `12` now satisfies the scenario contract with `conversation_state=pending` and a handoff reply on `Можно на 19:00?`.
  - `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl` turn `13` still replies `Отлично, время подходит. Как вас зовут?` after explicit name fill, keeps `expected_reply_type=name`, and records `evaluation.reasons=['booking_slot_stall']`.
  - `truffles-api/tests/test_reasoning_core.py:8689-8788` already proves that a complete name turn under active `expected_reply_type=name` must execute booking completion, not re-ask the same slot.
  - `truffles-api/tests/test_message_endpoint.py:16162-16327` already proves terminal `calendar.book_slot` success clears follow-up expected-reply state.
  - `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml:903-943` already proves active `name` resume must be preserved across side paths instead of collapsing into generic `booking_prompt` churn.
- `INFERENCE to verify in this block`:
  - the next truthful move is a bounded runtime implementation family for turn `13`; turn `9` and turn `12` no longer justify new work on the fresh artifact.

## One web search (mandatory before implementation)
- **Query (exact):** `Rasa docs forms slot mappings from text requested slot explicit value`
- **Date/time (local):** `2026-03-22T09:00:00+05:00`
- **Sources opened (from this query):**
  - `https://rasa.com/docs/rasa/forms/`
- **Source quality:** vendor documentation / primary source.
- **Existing solutions found:** when a requested slot is filled, the form advances; if the slot is not filled, it re-asks or rejects explicitly. Dynamic slot flow should not keep re-asking a slot that has already been extracted.
- **Decision:** `reuse/integrate/build`
  - reuse the repo's existing active-name completion contracts and bounded handoff rules
  - integrate the future fix into existing booking completion / active-name continuation owners
  - build only the missing bounded runtime-family implementation; do not add a new semantic bridge or judge workaround
- **Rejected options:**
  - oracle tightening before runtime fix
  - phrase-hardcoded handling for `Меня зовут ...`
  - new scenario mutations as a substitute for repairing runtime conformance

## Root cause (mandatory)
- **Symptom:** fresh canary run `a922-check-booking-proof-r14` still loops `booking_prompt/name` on turn `13` after the user provides explicit name input under an active booking name-collect state.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl` turn `9` and confirm exact-time progression is fixed to `expected_reply_type=name`.
  2. inspect the same artifact turn `12` and confirm the runtime now emits a handoff reply with `conversation_state=pending`.
  3. inspect turn `13` and confirm the runtime repeats `Как вас зовут?`, keeps `expected_reply_type=name`, and records `booking_slot_stall`.
  4. inspect `truffles-api/tests/test_reasoning_core.py:8689-8788` and confirm that an explicit name turn with grounded booking slots must execute booking completion rather than re-ask `name`.
  5. inspect `truffles-api/tests/test_message_endpoint.py:16162-16327` and confirm a terminal booking success must clear follow-up expected-reply state.
- **Evidence:**
  - `/tmp/booking_quality/a922-check-booking-proof-r14/summary.json`
  - `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl`
  - `/tmp/booking_quality/a922-check-booking-proof-r14/manual_audit.json`
  - `/tmp/booking_quality/a922-check-booking-proof-r14/failure_families.json`
  - `truffles-api/tests/test_reasoning_core.py:8689-8788`
  - `truffles-api/tests/test_message_endpoint.py:16162-16327`
  - `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml:903-943`
- **Five Whys (or equivalent):**
  1. Why is the replay still semantically red? Because turn `13` repeats the name prompt after the user already filled `name`.
  2. Why is this no longer a turn-9 family? Because turn `9` now advances correctly to `name` and persists `в субботу 11:00` on the fresh runtime.
  3. Why is turn `12` no longer the active blocker? Because the same artifact now emits the expected handoff state and reply on turn `12`.
  4. Why is turn `13` a runtime bug instead of judge-only drift? Because deterministic contracts already require complete-name progression / terminal clear, while the artifact loops the same missing-slot prompt and records `booking_slot_stall`.
  5. Why is the fix bounded? Because the repo already defines correct active-name completion behavior; the missing work is limited runtime conformance on this surfaced path.
- **Root cause statement:** the current runtime family keeps stale active-name booking-prompt state alive after explicit name fill on the fresh canary path, so booking completion never consumes the provided customer name and the dialog loops instead of completing or degrading contractually.
- **Fix mechanism:** publish one bounded implementation block that repairs active-name progression on the surfaced non-frozen owner path, adds deterministic regression coverage for the exact turn-13 family, and reruns the same fresh canary before any proof-lane tightening.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing active-name booking-completion contract in `truffles-api/tests/test_reasoning_core.py:8689-8788`
  - existing terminal expected-reply clear contract in `truffles-api/tests/test_message_endpoint.py:16162-16327`
  - existing active-name continuity preservation contract in `truffles-api/app/knowledge/generic/INTERACTION_OWNER_MATRIX.yaml:903-943`
  - existing fresh replay artifact `/tmp/booking_quality/a922-check-booking-proof-r14`
- **External reuse:**
  - official Rasa forms/requested-slot guidance only
- **Why not reinvent the wheel:**
  - the repo already defines correct active-name completion and terminal-clear behavior; the missing work is runtime conformance, not a new product contract.

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `32`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`:
  - this decision block is doc-only by intent, but the worktree already carries approved runtime diffs from earlier blocks; keeping `implementation` mode avoids false fail-closed governance on unrelated existing code changes.

## Invariant
- do not edit frozen webhook routers
- do not reopen turn `9` or turn `12` as active blockers on stale reasoning
- do not weaken judge / threshold / acceptance gates
- do not add phrase-hardcoded runtime branching for customer-name phrases
- do not claim acceptance closure from this decision block alone

## Scope
- define the exact bounded runtime family rooted at fresh canary turn `13`
- lock turn `9` as repaired on fresh replay and turn `12` as closed on the same artifact
- switch canon/session/packet to this new decision block

## Out of scope
- runtime implementation in this block
- `ops/diagnose.py` oracle tightening
- new `llm-quality` run or baseline update
- edits to `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`
- multi-pack acceptance or open-world closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md`
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
1. Publish the refreshed replay findings in the existing replay report and classify the surviving blocker truthfully.
2. Publish this bounded turn-13 runtime decision TP and matching report with RCA and the single-search record.
3. Switch canon/session artifacts from the replay block to this new runtime-family decision block.
4. Rebuild the generated packet and rerun governance/session checks.
5. Hand off the exact next move as a bounded runtime implementation family for turn `13`.

## DoD
- this TP and matching report exist and are the active block artifacts
- the replay report truthfully records turn `9` as fixed, turn `12` as closed, and turn `13` as the new surviving blocker on `r14`
- canon/packet/session all state that turn `13` is the next bounded runtime family
- `docs/SOURCE_OF_TRUTH.yaml` points `current_nonnegotiable_next_move` at the implementation of the turn-13 runtime family
- packet/guard stack stays green after sync
- no frozen runtime file is edited in this block

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r14 --status done --strict-artifacts`
- `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl').open(encoding='utf-8') if line.strip()]
for idx in [9, 12, 13]:
    row = next(r for r in rows if r.get('turn_index') == idx)
    print(idx, row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('conversation_state'), row.get('booking_slots'), row.get('evaluation'))
PY`
- `nl -ba truffles-api/tests/test_reasoning_core.py | sed -n '8689,8788p'`
- `nl -ba truffles-api/tests/test_message_endpoint.py | sed -n '16162,16327p'`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn13-name-progression-runtime-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-exact-time-progression-canary-replay-a922.md`
- `/tmp/booking_quality/a922-check-booking-proof-r14/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r14/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r14/manual_audit.json`
- `/tmp/booking_quality/a922-check-booking-proof-r14/failure_families.json`
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0`
- `Fail-fast / scenario lock`: reuse existing `r14` artifact only
- `Stop condition`: if fresh code exploration disproves the runtime-bug classification, stop and publish a corrective decision before code
- `Escalation path`: `Top Architect`

## Release safety (mandatory for non-doc changes)
- Strategy: no runtime or rollout change in this block
- Go/no-go signals: packet/docs/guards stay green; frozen routers untouched
- Rollback: revert canon/session/doc/test changes and rebuild packet
- Post-release monitoring window: next block must implement the bounded runtime family and rerun before any proof-lane tightening

## Rollback
1. Revert this decision TP/report and matching canon/session updates.
2. Restore the replay TP as active.
3. Rebuild the packet and rerun governance/session checks.

## No-go
- do not treat turn `9` as still open on the fresh runtime
- do not patch `ops/diagnose.py` first
- do not push business-specific phrases into core to force name extraction
- do not count this decision block as runtime progress
- do not reopen stale `r13` runtime freshness as if it were still the blocker

## Risks / blockers
- the eventual runtime fix may expose that active-name completion is split across more than one non-frozen owner lane
- judge conflicts on turns `6`, `9`, and `11` remain proof debt and could distract the implementation lane if mixed with runtime work
- acceptance remains blocked until the bounded runtime family lands and the same canary is rerun

## Residual architecture debt (mandatory)
- Current residuals accepted in this block:
  - turn `13` name progression runtime family remains unfixed
  - judge/oracle advisory conflicts on turns `6`, `9`, and `11` remain untightened proof debt
  - guarded `demo_salon/main` acceptance rerun remains pending
  - multi-pack / open-world closure remains pending
- Why not in this block:
  - this block is the required classification/decision boundary before any new runtime code
- Risk if deferred:
  - without a bounded implementation block, the team can drift back into proof churn or reopen already-closed turn-9/12 debates
- Linked follow-up Task Package(s):
  - `implement_consultant_core_demo_salon_turn13_name_progression_runtime_family`
- Expiry/trigger to stop deferral:
  - stop deferral immediately before any new llm-quality rerun, oracle tightening, or runtime patch outside the bounded family

## Next-block contract (mandatory)
- `Next block objective:`
  - implement the bounded non-frozen turn-13 runtime family so explicit customer-name fill under active `expected_reply_type=name` progresses into booking completion or bounded degrade/handoff instead of re-asking `name`
- `First deterministic check command:`
  - `pytest -q truffles-api/tests/test_reasoning_core.py -k "booking_completion_owner and complete_name_turn"`
- `Blocked-by conditions:`
  - frozen-router edits become necessary
  - root cause disproves the current active-name completion classification
  - a new expensive replay is proposed before deterministic runtime evidence lands
- `Owner role for closure:` `Top Architect`
