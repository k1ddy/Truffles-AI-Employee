# TP-2026-03-22 — Consultant Core Demo Salon Main Canary R19 Oracle Conflict Proof Decision A922

## Block identity
- `BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-R19-ORACLE-CONFLICT-PROOF-DECISION-A922`
- `PARENT_BLOCK_ID`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-TURN9-GROUNDED-DATETIME-RESCHEDULE-CANARY-REPLAY-A922`
- `DEPENDS_ON`: `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-grounded-datetime-reschedule-canary-replay-a922.md`
- `UNLOCKS`: `CONSULTANT-CORE-DEMO-SALON-MAIN-CANARY-R19-CONTRACT-ALIGNED-ORACLE-PROOF-IMPLEMENTATION-A922`

## Git / worktree
- `Branch`: `feat/2026-03-15-consultant-core-governance-lock-a922`
- `Worktree path`: `/home/zhan/worktrees/2026-03-15-consultant-core-governance-lock-a922`
- `Base ref`: `origin/main`
- `Merge policy`: `merge only, no rebase`
- `Cleanup`: `Brain or Top Architect removes branch/worktree after merge`

## Name / goal
Publish one bounded proof-family decision for truthful replay `r19`. This block must prove that no honest runtime blocker survives on the current canary artifact, classify the remaining semantic-invalid status into exact oracle subfamilies, and lock the next move to one contract-aligned oracle implementation family inside `ops/diagnose.py` instead of another runtime patch or scenario mutation.

## Canon refs
- `AGENTS.md`
- `STATE.md`
- `STRUCTURE.md`
- `STRATEGY/REQUIREMENTS.md`
- `docs/DECISIONS/DEC-2026-03-15-consultant-core-controlled-demolition.md`
- `docs/TASK_PACKAGES/TP-2026-03-15-consultant-core-controlled-demolition-master.md`
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-turn9-grounded-datetime-reschedule-canary-replay-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-turn9-grounded-datetime-reschedule-canary-replay-a922.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `docs/ACTIVE_PROGRAM.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `ops/diagnose.py`
- `truffles-api/tests/test_booking_quality_judge_suppression.py`
- `truffles-api/tests/test_booking_quality_status_gate.py`
- `/tmp/booking_quality/a922-check-booking-proof-r19/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r19/manual_audit.json`
- `/tmp/booking_quality/a922-check-booking-proof-r19/failure_families.json`

## FACT pre-check (before decision sync)
- `Impacted docs/tests`:
  - `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-oracle-conflict-proof-decision-a922.md`
  - `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-oracle-conflict-proof-decision-a922.md`
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
  - `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r19 --status done --strict-artifacts`
  - `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl').open(encoding='utf-8') if line.strip()]
for idx in [6, 9, 11, 12]:
    row = next(r for r in rows if r.get('turn_index') == idx)
    print(idx, row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('turn_expectations'), row.get('evaluation'), row.get('judge'))
PY`
  - `nl -ba ops/diagnose.py | sed -n '4288,4443p'`
  - `nl -ba ops/diagnose.py | sed -n '4897,4985p'`
  - `nl -ba ops/diagnose.py | sed -n '9148,9162p'`
  - `nl -ba ops/diagnose.py | sed -n '12480,12494p'`
  - `nl -ba truffles-api/tests/test_booking_quality_judge_suppression.py | sed -n '1,240p'`
  - `nl -ba truffles-api/tests/test_booking_quality_status_gate.py | sed -n '2003,2046p'`
- `FACT findings`:
  - `/tmp/booking_quality/a922-check-booking-proof-r19/summary.json` is truthful and runtime-green on the locked canary (`infra_valid=true`, `turns_strict_failed=0`), but `semantic_valid=false` remains because `blocking_reasons={'handoff_miss': 2}`.
  - `/tmp/booking_quality/a922-check-booking-proof-r19/manual_audit.json` records `judge_oracle_alignment_gap`, `winner=contract`, and `conflict_count=4`; the remaining red is already classified by audit as oracle drift, not runtime drift.
  - Turns `9` and `12` are strict-green collect continuations with grounded exact-time progression, but HQ1 still classifies them as `handoff_miss` solely because `reschedule_signal` is present while the auxiliary classifier ignores the same booking-active handoff fallback already accepted by `_llm_quality_action_matches_expected(...)`.
  - Turns `6`, `9`, `11`, and `12` still carry judge `missed_question` even though the strict contract stays green; `_llm_quality_should_suppress_missed_question_judge_fail(...)` currently suppresses only a narrower subset of follow-up contracts and does not mirror the current booking continuity / check-booking collect / booking-interrupt info allowances.
  - `ops/diagnose.py:12485-12488` already codifies that `check_booking_prompt` is a collection step, not a terminal booking confirmation, which is why turn `11` is contract-valid despite the judge failure.
  - Turn `12` scenario expectation still says `action=handoff`, but `ops/diagnose.py:4897-4931` already allows `booking_prompt` as a contract-valid fallback for handoff expectations during active booking continuity, so the surfaced blocker is not a scenario mutation first.
- `INFERENCE to verify in this block`:
  - the next truthful move is a bounded oracle/proof implementation family rooted in `ops/diagnose.py`; no runtime patch and no scenario mutation are admissible before that proof family is handled.

## One web search (mandatory before implementation)
- **Query (exact):** `site:developers.openai.com/api/docs/guides/evaluation-best-practices llm judge pass fail clear detailed rubric`
- **Date/time (local):** `2026-03-22T13:34:21+05:00`
- **Sources opened (from this query):**
  - `https://developers.openai.com/api/docs/guides/evaluation-best-practices`
- **Source quality:** official vendor documentation / primary source.
- **Existing solutions found:**
  - evals should stay task-specific and aligned to production behavior
  - automated scoring must be calibrated against human judgment
  - pass/fail or pairwise grading is more reliable than open-ended vibe scoring
  - judge rubrics must stay clear and detailed, especially around follow-up questions and handoff boundaries
- **Decision:** `reuse/integrate`
  - reuse the repo's existing contract-first strict evaluator and manual-audit arbitration
  - integrate the next fix into auxiliary oracle layers (`judge` suppression + HQ1 classifier) so they mirror the current deterministic contract allowances
  - do not weaken thresholds, rewrite runtime semantics, or mutate the scenario as the first response
- **Rejected options:**
  - runtime patch before oracle classification
  - threshold or gate weakening
  - scenario rewrite before proving oracle mismatch
  - open-ended judge wording tweaks without deterministic regression coverage

## Root cause (mandatory)
- **Symptom:** truthful replay `r19` is runtime-green but still semantically invalid because auxiliary oracle layers keep classifying contract-valid turns as `missed_question` / `handoff_miss`.
- **Minimal reproduction:**
  1. inspect `/tmp/booking_quality/a922-check-booking-proof-r19/summary.json` and confirm `infra_valid=true`, `turns_strict_failed=0`, `semantic_valid=false`, `blocking_reasons={'handoff_miss': 2}`.
  2. inspect `/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl` turns `9` and `12` and confirm both are strict-green booking continuations (`expected_reply_type=name`, grounded datetime advanced) while still landing in the blocking handoff family.
  3. inspect turns `6`, `9`, `11`, and `12` and confirm each still carries judge `missed_question` even though strict reasons are empty.
  4. inspect `ops/diagnose.py:4897-4931` and confirm the strict evaluator already treats active-booking `booking_prompt` as a valid fallback for expected handoff.
  5. inspect `ops/diagnose.py:4288-4443` and `ops/diagnose.py:9148-9162` and confirm the judge suppression helper and HQ1 classifier do not reuse that same contract fallback envelope.
- **Evidence:**
  - `/tmp/booking_quality/a922-check-booking-proof-r19/summary.json`
  - `/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl`
  - `/tmp/booking_quality/a922-check-booking-proof-r19/manual_audit.json`
  - `ops/diagnose.py:4288-4443`
  - `ops/diagnose.py:4897-4931`
  - `ops/diagnose.py:9148-9162`
  - `ops/diagnose.py:12485-12488`
  - `truffles-api/tests/test_booking_quality_judge_suppression.py`
  - `truffles-api/tests/test_booking_quality_status_gate.py:2003-2046`
- **Five Whys (or equivalent):**
  1. Why is `r19` still semantically red? Because blocking reasons still count `handoff_miss=2`, and judge conflicts remain unsuppressed on four strict-green turns.
  2. Why do turns `9` and `12` still count as `handoff_miss`? Because the HQ1 classifier keys off `reschedule_signal` and collect-like actions but does not mirror the existing action-fallback contract for active booking continuation.
  3. Why do turns `6`, `9`, `11`, and `12` still show judge `missed_question`? Because the judge suppression helper covers only a narrow whitelist of follow-up envelopes and misses contract-valid booking continuity / check-booking collect / booking-interrupt info turns.
  4. Why is this not a runtime defect? Because the same artifact has `turns_strict_failed=0`, `winner=contract`, and no surviving runtime blocker across turns `8`, `9`, `11`, `12`, `13`, and `14`.
  5. Why is the next fix bounded? Because the strict evaluator and manual audit already contain the correct contract-first allowances; only the auxiliary oracle heuristics lag behind.
- **Root cause statement:** the remaining `r19` semantic invalidity is caused by oracle parity drift inside `ops/diagnose.py`: the strict contract evaluator and manual audit already accept the current booking continuity path, but auxiliary judge suppression and HQ1 blocking heuristics do not mirror those same allowances, so contract-valid turns still count as semantic failures.
- **Fix mechanism:** implement one bounded proof-family change inside `ops/diagnose.py` that aligns judge suppression and HQ1 handoff blocking with the existing contract-first fallback rules, add deterministic regressions for the surfaced turn classes, and only then rerun the same locked canary.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - existing strict action fallback in `ops/diagnose.py:4897-4931`
  - existing booking verification collect contract in `ops/diagnose.py:12485-12488`
  - existing manual audit arbitration on `/tmp/booking_quality/a922-check-booking-proof-r19/manual_audit.json`
  - existing deterministic test files `truffles-api/tests/test_booking_quality_judge_suppression.py` and `truffles-api/tests/test_booking_quality_status_gate.py`
- **External reuse:**
  - official OpenAI evaluation best-practices guidance only
- **Why not reinvent the wheel:**
  - the repo already defines the truthful contract; the missing work is oracle parity, not a new rubric or a new runtime feature.

## Work mode (mandatory)
- `Mode`: `forensic`
- `Why this mode`: this block is classification-only and must map the remaining proof family precisely before any code or replay changes.
- `Family handled in this block`: `r19 contract-vs-oracle conflict family`
- `Closure artifact expected from this mode`: one decision TP/report pair plus canon sync and a single exact implementation handoff.

## Execution profile (mandatory for non-doc blocks)
- `TP mode`: `implementation`
- `Doc touch budget (files)`: `18`
- `Code dominance`: `off`
- `Override token`: `none`
- `Why this profile fits`:
  - the block is doc-only by intent, but the worktree already carries approved runtime diffs; keeping `implementation` mode avoids false governance failure on the existing code delta while canon switches to the proof lane.

## Invariant
- do not edit runtime code in this block
- do not edit frozen webhook routers
- do not weaken judge / threshold / acceptance gates
- do not mutate the locked scenario file
- do not claim acceptance closure from this decision block alone

## Scope
- classify the remaining `r19` semantic-invalid status into bounded oracle subfamilies
- prove that no honest runtime blocker survives on `r19`
- define the exact next proof implementation family in `ops/diagnose.py`
- switch canon/session/packet to this new proof decision block

## Out of scope
- `ops/diagnose.py` code changes in this block
- new replay run or baseline update
- runtime implementation
- edits to `truffles-api/app/routers/webhook/decision.py`, `truffles-api/app/routers/webhook/booking.py`, or `truffles-api/app/routers/webhook/pending.py`
- multi-pack acceptance or open-world closure

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-oracle-conflict-proof-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-oracle-conflict-proof-decision-a922.md`
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
1. Re-audit `r19` and inspect turns `6`, `9`, `11`, and `12` plus the relevant oracle helpers in `ops/diagnose.py`.
2. Publish this bounded proof decision TP and matching report with RCA and the exact search record.
3. Switch canon/session artifacts from the replay block to this oracle-decision block.
4. Rebuild the packet and rerun governance/session checks.
5. Hand off the exact next move as one contract-aligned oracle proof implementation family.

## DoD
- this TP and matching report exist and are the active block artifacts
- canon states that no honest runtime blocker survives on `r19`
- canon states that turns `9` and `12` form the semantic-blocking HQ1 false-positive subfamily and turns `6`, `9`, `11`, `12` form the judge suppression subfamily
- `docs/SOURCE_OF_TRUTH.yaml` points `current_nonnegotiable_next_move` at the proof implementation family
- packet/guard stack stays green after sync
- no frozen runtime file is edited in this block

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-check-booking-proof-r19 --status done --strict-artifacts`
- `python3 - <<'PY'
import json
from pathlib import Path
rows=[json.loads(line) for line in Path('/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl').open(encoding='utf-8') if line.strip()]
for idx in [6, 9, 11, 12]:
    row = next(r for r in rows if r.get('turn_index') == idx)
    print(idx, row['turn_text'], row['outbox_text'], row.get('expected_reply_type'), row.get('turn_expectations'), row.get('evaluation'), row.get('judge'))
PY`
- `nl -ba ops/diagnose.py | sed -n '4288,4443p'`
- `nl -ba ops/diagnose.py | sed -n '4897,4985p'`
- `nl -ba ops/diagnose.py | sed -n '9148,9162p'`
- `nl -ba ops/diagnose.py | sed -n '12480,12494p'`
- `nl -ba truffles-api/tests/test_booking_quality_judge_suppression.py | sed -n '1,240p'`
- `nl -ba truffles-api/tests/test_booking_quality_status_gate.py | sed -n '2003,2046p'`
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
- `docs/TASK_PACKAGES/TP-2026-03-22-consultant-core-demo-salon-main-canary-r19-oracle-conflict-proof-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-22-consultant-core-demo-salon-main-canary-r19-oracle-conflict-proof-decision-a922.md`
- `/tmp/booking_quality/a922-check-booking-proof-r19/summary.json`
- `/tmp/booking_quality/a922-check-booking-proof-r19/responses.jsonl`
- `/tmp/booking_quality/a922-check-booking-proof-r19/manual_audit.json`
- `/tmp/booking_quality/a922-check-booking-proof-r19/failure_families.json`
- updated canon / packet / session artifacts

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0`
- `Fail-fast / scenario lock`: reuse existing `r19` artifact only
- `Stop condition`: if classification uncovers a strict runtime contradiction or a scenario-contract mismatch that invalidates the current proof reading
- `Escalation path`: `Top Architect`

## Release safety (mandatory for non-doc changes)
- Strategy: no runtime, rollout, or oracle-code mutation in this block
- Go/no-go signals: packet/docs/guards stay green; frozen routers untouched
- Rollback: revert canon/session/doc/test changes and rebuild packet
- Post-release monitoring window: the next block must implement the bounded oracle family and rerun before any acceptance claim changes

## Rollback
1. Revert this decision TP/report and matching canon/session updates.
2. Restore the replay TP as active.
3. Rebuild the packet and rerun governance/session checks.

## No-go
- do not open a new runtime family from `r19`
- do not patch `ops/diagnose.py` in this decision block
- do not weaken thresholds or blocking gates to get `semantic_valid=true`
- do not mutate the locked scenario as a substitute for oracle parity
- do not treat this decision block as acceptance closure

## Risks / blockers
- an over-broad oracle patch could hide a real future semantic miss, so the next implementation must anchor every suppression to contract-valid strict-green envelopes only
- turns `9` and `12` share both judge and HQ1 false positives, while turns `6` and `11` are judge-only; if the next block mixes these without deterministic tests, proof churn will return
- duplicate top-level defs in `truffles-api/app/services/reasoning_core.py` remain structural debt outside this proof block

## Residual architecture debt (mandatory)
- `Current residuals accepted in this block:`
  - contract-aligned oracle parity is not implemented yet
  - duplicate defs in `truffles-api/app/services/reasoning_core.py` remain deferred
  - final acceptance / open-world closure remain pending
- `Why not in this block:`
  - this block is the required classification boundary before any oracle code change
- `Risk if deferred:`
  - without a bounded oracle family, the team can drift back into runtime churn or threshold weakening even though `r19` is already runtime-green
- `Linked follow-up Task Package(s):`
  - `implement_consultant_core_demo_salon_r19_contract_aligned_oracle_proof_family`
- `Expiry/trigger to stop deferral:`
  - if the next proof implementation family cannot make HQ1 blocking reasons mirror the contract-first fallback, stop and publish a narrower decision before replay

## Next-block contract (mandatory)
- `Next block objective:`
  - land one bounded `ops/diagnose.py` proof family that removes false `handoff_miss` on turns `9`/`12` and suppresses contract-valid `missed_question` on turns `6`/`9`/`11`/`12` without weakening thresholds or touching runtime code
- `First deterministic check command:`
  - `pytest -q truffles-api/tests/test_booking_quality_judge_suppression.py truffles-api/tests/test_booking_quality_status_gate.py -k "missed_question or handoff_miss"`
- `Blocked-by conditions:`
  - if a deterministic test shows the surfaced turns are not strict-green under the current contract
  - if the required change would force runtime edits or scenario mutation first
  - if the proof fix cannot stay bounded to `ops/diagnose.py` + proof tests
- `Owner role for closure:`
  - `Hands`, with `Brain / Top Architect` accepting the next replay handoff
