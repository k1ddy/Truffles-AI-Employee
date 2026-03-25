# TP-2026-03-23 Consultant Core Demo Salon Seed19 R24 Fallback JID Exhaustion Proof Decision A922

## Title/goal
Classify the first surviving blocker from fresh replay `r24` and lock the next admissible proof family after the `r23` runtime repair closure.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r23-pending-reschedule-handoff-canary-replay-a922.md`

## Invariant
Do not reopen runtime code first once fresh replay has already proven the `r23` row closed on the live surface.

## Scope
Truthful classification of the new `r24` replay stop and canon sync to the next bounded proof implementation family.

## Out of scope
- new runtime changes
- frozen router edits
- acceptance gate changes

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
1. Record the truthful closure of the old `r23` runtime family proven by fresh replay `r24`.
2. Record the new replay stop as proof/preflight contamination, not runtime regression.
3. Lock the next bounded proof family around fallback-JID exhaustion in `ops/diagnose.py`.

## DoD
- canon points at the new proof decision block
- next move no longer points at `reasoning_core.py`
- `r24` is described as proof-blocking after the `r23` row closed

## Work mode (mandatory)
- `Mode`: `closure`
- `Why this mode`: fresh replay and audit already exist; this block only classifies the surviving family.
- `Family handled in this block`: `seed19 r24 fallback-jid exhaustion proof decision`
- `Closure artifact expected from this mode`: one decision TP/report pair and canon sync to the next proof implementation family.

## One web search (mandatory before implementation)
- **Query (exact):** `n/a — decision-only closure block after the already-executed runtime implementation family`
- **Date/time (local):** `2026-03-23 11:10 +05:00`
- **Sources opened (from this query):** `https://legacy-docs-oss.rasa.com/docs/rasa/forms/` (reused from the preceding runtime implementation family; no new query executed in this decision block)
- **Source quality:** `official documentation / primary source reused from the preceding implementation family`
- **Existing solutions found:** the old runtime family is already closed; this block only classifies the new proof/preflight stop.
- **Decision:** `reuse existing replay artifact and local source analysis; no new search in this decision block`
- **Reuse / integrate / build decision:** `reuse the fresh replay artifact and local code inspection to classify the next proof family before any new implementation`
- **Rejected options:** `opening a second query for a closure-only block`, `reopening runtime code before proving the blocker is no longer semantic/runtime`

## Reuse-first plan (mandatory)
- Internal reuse:
  - `ops/diagnose.py` replay artifact and audit helpers
  - existing fallback-JID helpers in `ops/diagnose.py`
  - existing JID-mode regressions in `truffles-api/tests/test_booking_quality_jid_mode.py`
- External reuse:
  - `https://legacy-docs-oss.rasa.com/docs/rasa/forms/`
- Why not reinvent the wheel:
  - the blocker is inside existing proof-path JID selection logic; the next work should repair that helper rather than adding a new runtime branch.

## Root cause (mandatory)
- Symptom: fresh replay `r24` closes dialog `2`, turn `9` but still fail-closes before dialog `3` turns on contaminated preflight.
- Minimal reproduction: `/tmp/booking_quality/a922-go2f-seed19-r24/summary.json` plus the replay stdout contamination stop on dialog `3` after dialogs `1` and `2` complete strict-green.
- Evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r24/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r24/runtime_state.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r24/manual_audit.json`
  - `ops/diagnose.py:3288`
  - `ops/diagnose.py:19256`
  - `truffles-api/tests/test_booking_quality_jid_mode.py`
- Five Whys:
  1. Why is `r24` still infra-invalid? Replay stops with contaminated preflight before dialog `3` turns start.
  2. Why does preflight still fail after two clean dialogs? The reset loop rotates through already contaminated allowlist JIDs.
  3. Why does it stop instead of moving to a fresh JID? `_llm_quality_select_fallback_jid(...)` returns `None` once the allowlist pool is exhausted while outbox is enabled.
  4. Why is that wrong here? The run is already in `jid_mode=unique` with `allow_non_allowlist=true`, so exhausted allowlist fallback should be able to mint a fresh dialog JID instead of hard-stopping.
  5. Why is this not a runtime regression? Dialog `2`, turn `9` and downstream rows are strict-green on fresh evidence; the new stop happens entirely inside replay preflight before dialog `3` execution.
- Root cause statement: the proof-path fallback-JID helper in `ops/diagnose.py` fail-closes when the contaminated allowlist pool is exhausted under outbox-enabled replay, even though `jid_mode=unique` and `allow_non_allowlist=true` permit a fresh dialog JID.
- Fix mechanism: next block must repair fallback-JID selection and its deterministic tests so replay can mint a fresh unique JID after allowlist exhaustion instead of stopping as contaminated preflight.

## Token / run budget (mandatory for expensive suites)
- Max full runs: `0` in this decision block
- Max replay runs: `1` already consumed by `r24`
- Stop condition: if the surviving blocker is still proof/preflight after fresh replay and audit, do not spend another replay before opening the proof implementation block.

## Release safety (mandatory for non-doc changes)
- Strategy: `no production rollout in this decision block; classify only and keep replay runtime local on 127.0.0.1:18186`
- Go/no-go signals: `r24` must prove the old runtime row closed before any proof-family reopening`
- Rollback: `revert canon sync if later evidence disproves the proof classification`
- Post-release monitoring window: `n/a for this decision block`

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r24 --status done --strict-artifacts`

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r24/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r24/runtime_state.json`
- `/tmp/booking_quality/a922-go2f-seed19-r24/manual_audit.json`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-proof-decision-a922.md`

## Rollback
Revert canon/session updates if the blocker classification proves wrong.

## No-go
- no more `reasoning_core.py` edits first
- no frozen router edits
- no acceptance-gate weakening

## Risks/blockers
- the replay artifact is still non-canonical (`run_incomplete`), so downstream runtime families after dialog `3` remain unresolved.

## Residual architecture debt (mandatory)
### Current residuals accepted in this block
- downstream rows after dialog `2`, turn `14` remain unclassified
- `reasoning_core.py` duplicate top-level defs remain deferred debt

### Why not in this block
This block is classification only.

### Risk if deferred
The next implementation could wrongly reopen runtime work even though fresh replay already proved the target row closed.

### Linked follow-up Task Package(s)
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r24-fallback-jid-exhaustion-proof-implementation-a922.md`

### Expiry/trigger to stop deferral
Immediate; no more runtime work is admissible before the fallback-JID proof family is repaired.

## Next-block contract (mandatory)
### Next block objective
Repair the fallback-JID proof family so outbox-enabled unique replay can mint a fresh dialog JID after allowlist exhaustion instead of fail-closing contaminated preflight.

### First deterministic check command
`pytest -q truffles-api/tests/test_booking_quality_jid_mode.py -k "fallback_jid or jid_mode"`

### Blocked-by conditions
Unresolved disagreement about proof vs runtime; stale local replay runtime; missing replay artifact audit.

### Owner role for closure
Brain / Top Architect
