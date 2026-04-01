# TP-2026-03-23 Consultant Core Demo Salon Seed19 R22 Preflight Contamination Proof Decision A922

## Title/goal
Classify the first surviving blocker after the runtime reset repair and lock the next admissible proof-only family.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r14-session-reset-pending-ack-terminal-unresolved-canary-replay-a922.md`

## Invariant
Do not reopen runtime code until the surviving blocker is shown to be runtime, not proof/preflight.

## Scope
Truthful classification of the fresh `r22` replay outcome and canon sync to the next proof lane.

## Out of scope
- new runtime patches
- frozen router edits

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
1. Record the runtime closure proven by `r22`.
2. Record the non-canonical replay attempts as audited invalid evidence.
3. Classify the surviving blocker as proof/preflight contamination.
4. Lock the next proof-only implementation family.

## DoD
- canon points to the new proof decision block
- next move no longer points at runtime repair
- the surviving blocker is described as proof/preflight contamination with concrete evidence

## Work mode (mandatory)
- `Mode`: `closure`
- `Why this mode`: the runtime family is already closed on fresh replay evidence; this block only classifies the next surviving family.
- `Family handled in this block`: `seed19 r22 preflight contamination proof decision`
- `Closure artifact expected from this mode`: one decision TP/report pair and canon sync to the next proof-only implementation family.

## One web search (mandatory before implementation)
- **Query (exact):** `n/a — decision-only closure block after the already-executed implementation family`
- **Date/time (local):** `2026-03-23T10:27:00+06:00`
- **Sources opened (from this query):** `https://rasa.com/docs/rasa/forms/` (reused as the preceding implementation-family primary-source anchor; no new query executed in this decision block)
- **Source quality:** `vendor documentation / primary source reused from the preceding implementation family`
- **Existing solutions found:** runtime closure already proved; this block only classifies the surviving evidence lane.
- **Decision:** `reuse existing implementation-family research; no new search in this decision block`
- **Reuse / integrate / build decision:** `reuse the existing replay evidence and local source analysis to classify the next family before any new implementation`
- **Rejected options:** `opening a second implementation query for a closure-only block`, `reopening runtime research before proof classification`

## Reuse-first plan (mandatory)
- Internal reuse:
  - `ops/diagnose.py` preflight contamination/fallback logic
  - existing proof tests in `truffles-api/tests/test_booking_quality_status_gate.py`
  - existing fallback/JID policy tests in `truffles-api/tests/test_booking_quality_jid_mode.py`
- External reuse:
  - `https://rasa.com/docs/rasa/forms/`
- Why not reinvent the wheel:
  - the surviving blocker is already localized to the proof/preflight lane; the next work should refine the existing contamination contract instead of creating a new runtime reset path.

## Root cause (mandatory)
- Symptom: fresh replay `r22` still fail-closes before dialog turn `1` after the runtime reset repair.
- Minimal reproduction: exact seed-`19` replay on fresh runtime parity, `--reset-before-dialog`, outbox enabled, allowlist pool reused.
- Evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r22/manual_audit.json`
  - replay stdout from the fresh `r22` run
  - `ops/diagnose.py` contamination and fallback logic
- Five Whys:
  1. Why does replay still stop? preflight remains contaminated.
  2. Why is preflight contaminated? the allowlist JID pool still surfaces historical recent-conversation state after reset.
  3. Why does reset no longer explain the stop? `Session reset ack sent` now lands with `session_memory_reset=explicit_reset`.
  4. Why do we still fail before turn `1`? proof/preflight contamination logic and JID reuse still fail-closed on the dirty allowlist pool.
  5. Why is this not runtime? the repaired runtime path already returns the contractually correct reset acknowledgment; the surviving stop is now in replay isolation/evidence handling.
- Root cause statement: the remaining blocker after `r22` is proof/preflight contamination on the allowlist JID pool, not a runtime reset owner bug.
- Fix mechanism: next block must repair the contamination/isolation family inside `ops/diagnose.py` and its proof tests without weakening the outbox/allowlist contract.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0` in this decision block
- Max replay runs: `1` already consumed by `r22`
- Stop condition: if the blocker is still ambiguous after the fresh replay and audit, do not spend another expensive run before opening the next proof implementation block.

## Release safety (mandatory for non-doc changes)
- Strategy: `no production rollout in this decision block; classify only and keep the local replay runtime isolated on 127.0.0.1:18186`
- Go/no-go signals: `r22` must continue to show runtime reset closure and the next block must stay proof-only`
- Rollback: `revert the local runtime patch and canon sync if the blocker is reclassified as runtime`
- Post-release monitoring window: `n/a for this decision block; next implementation block must define it if proof tooling changes could affect acceptance flows`

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r22 --status done --strict-artifacts`

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r22/manual_audit.json`
- live replay stdout from `r22`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r22-preflight-contamination-proof-decision-a922.md`

## Rollback
Revert canon/session updates if the blocker classification proves wrong.

## No-go
- no new runtime code in this decision block
- no gate weakening
- no frozen router edits

## Risks/blockers
- `r22` summary remains incomplete because replay exited on contaminated preflight before any dialog rows were written.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- `reasoning_core.py` still carries duplicate top-level defs
- proof preflight contamination heuristics remain broader than the actual replay isolation need

### Why not in this block
This block is classification only.

### Risk if deferred
Replay cannot reach turn `1` on the dirty allowlist pool.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r22-preflight-contamination-proof-implementation-a922.md`

### Expiry/trigger to stop deferral
Immediate; no further runtime work is admissible first.

## Next-block contract (mandatory)
### Next block objective
Repair the proof/preflight contamination family in `ops/diagnose.py` without weakening the outbox/allowlist contract.

### First deterministic check command
`pytest -q truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_jid_mode.py -k "preflight or contamination or fallback_jid"`

### Blocked-by conditions
Unresolved classification disagreement about proof vs runtime.

### Owner role for closure
Brain / Top Architect
