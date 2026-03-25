# TP-2026-03-23 Consultant Core Demo Salon Seed19 R23 Pending Reschedule Handoff Runtime Decision A922

## Title/goal
Classify the first surviving blocker from fresh replay `r23` and lock the next admissible runtime family.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r22-preflight-contamination-canary-replay-a922.md`

## Invariant
Do not reopen proof tooling or acceptance gates first once fresh replay has reached the runtime row.

## Scope
Truthful classification of `r23` dialog `2`, turn `9` and canon sync to the next runtime implementation family.

## Out of scope
- new code changes
- frozen router edits
- proof tooling changes

## Touch-list (files/tables)
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan
1. Record the proof-family closure proven by `r23`.
2. Record the fresh first failing row and its runtime contract mismatch.
3. Lock the next bounded runtime family around pending-state reschedule follow-up handoff interception.

## DoD
- canon points at the new runtime decision block
- next move no longer points at proof tooling
- `r23` is described as runtime-blocking, not proof-blocking

## Work mode (mandatory)
- `Mode`: `closure`
- `Why this mode`: fresh replay and audit already exist; this block only classifies the surviving family.
- `Family handled in this block`: `seed19 r23 pending reschedule handoff runtime decision`
- `Closure artifact expected from this mode`: one decision TP/report pair and canon sync to the next runtime implementation family.

## One web search (mandatory before implementation)
- **Query (exact):** `n/a — decision-only closure block after the already-executed proof implementation family`
- **Date/time (local):** `2026-03-23 11:27 +06:00`
- **Sources opened (from this query):** `https://docs.pytest.org/en/6.2.x/fixture.html` (reused from the preceding implementation-family anchor; no new query executed in this decision block)
- **Source quality:** `official documentation / primary source reused from the preceding implementation family`
- **Existing solutions found:** proof isolation closure already proved; this block only classifies the surviving runtime lane.
- **Decision:** `reuse existing implementation-family research; no new search in this decision block`
- **Reuse / integrate / build decision:** `reuse the fresh replay artifact and local source analysis to classify the next runtime family before any new implementation`
- **Rejected options:** `opening a second query for a closure-only block`, `reopening proof heuristics before runtime classification`

## Reuse-first plan (mandatory)
- Internal reuse:
  - `ops/diagnose.py` replay artifact and audit helpers
  - existing runtime path in `truffles-api/app/services/reasoning_core.py`
- External reuse:
  - `https://docs.pytest.org/en/6.2.x/fixture.html`
- Why not reinvent the wheel:
  - the proof lane is already green enough to reach the runtime row; the next work should repair the surfaced runtime continuity defect instead of adding more proof heuristics.

## Root cause (mandatory)
- Symptom: fresh replay `r23` reaches dialog `2`, turn `9`, but the runtime escalates instead of resuming booking collect.
- Minimal reproduction: `/tmp/booking_quality/a922-go2f-seed19-r23/responses.jsonl`, row `LLM-QUAL-a922-go2f-seed19-r23-002-09-6f3a38`.
- Evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r23/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r23/brief.md`
  - `/tmp/booking_quality/a922-go2f-seed19-r23/manual_audit.json`
  - `truffles-api/app/services/reasoning_core.py`
- Five Whys:
  1. Why does replay stop now? strict evaluation fails at dialog `2`, turn `9`.
  2. Why does that row fail? expected `booking_prompt` collect contract is missing.
  3. Why is it missing? runtime emits `policy_core_guard` / `handoff` with `terminal_owner_unresolved` instead.
  4. Why is that admissible now? proof isolation no longer blocks preflight, so the row is reached on fresh exact replay.
  5. Why is this not another proof gap? `infra_valid=true`, strict failure is on runtime `decision_meta` + `decision_trace`, and manual audit no longer points at contamination.
- Root cause statement: after the proof isolation repair, the first surviving blocker is a live runtime contract bug where a pending-state reschedule follow-up (`На какое время лучше записаться?`) falls into `terminal_owner_unresolved` handoff instead of resuming the expected booking collect contract.
- Fix mechanism: next block must localize and repair the pending-state reschedule follow-up owner path in non-frozen runtime code before another replay.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0` in this decision block
- Max replay runs: `1` already consumed by `r23`
- Stop condition: if the surviving blocker is still runtime after fresh replay and audit, do not spend another expensive run before opening the runtime implementation block.

## Release safety (mandatory for non-doc changes)
- Strategy: `no production rollout in this decision block; classify only and keep the local replay runtime isolated on 127.0.0.1:18186`
- Go/no-go signals: `r23` must keep proof isolation green and show the surviving runtime row on fresh parity`
- Rollback: `revert canon sync if later evidence disproves the runtime classification`
- Post-release monitoring window: `n/a for this decision block`

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r23 --status done --strict-artifacts`

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r23/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r23/responses.jsonl`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r23-pending-reschedule-handoff-runtime-decision-a922.md`

## Rollback
Revert canon/session updates if the blocker classification proves wrong.

## No-go
- no more proof-tool edits first
- no frozen router edits
- no gate weakening

## Risks/blockers
- fail-fast replay stops at dialog `2`, turn `9`, so downstream rows remain unresolved debt.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `reasoning_core.py` still carries duplicate explicit-handoff owner defs.
- Downstream rows after dialog `2`, turn `9` remain unclassified.

### Why not in this block
This block is classification only.

### Risk if deferred
The next implementation could conflate proof closure with runtime continuity bugs.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r23-pending-reschedule-handoff-runtime-implementation-a922.md`

### Expiry/trigger to stop deferral
Immediate; no more proof work is admissible first.

## Next-block contract (mandatory)
### Next block objective
Repair the pending-state reschedule follow-up runtime family so dialog `2`, turn `9` resumes collect instead of terminal handoff.

### First deterministic check command
`pytest -q truffles-api/tests/test_reasoning_core.py -k "pending_reschedule or terminal_owner_unresolved or explicit_handoff_owner"`

### Blocked-by conditions
Unresolved disagreement about proof vs runtime; stale local runtime for replay closure.

### Owner role for closure
Brain / Top Architect
