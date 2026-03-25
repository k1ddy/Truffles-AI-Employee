# TP-2026-03-23 Consultant Core Demo Salon Seed19 R39 Dialog Preflight Fallback Cycle Proof Decision A922

## Title/goal
Classify the first admissible blocker after the bounded `r29` runtime repair when fresh replay `r39` no longer fails on dialog `1`, turn `1` but still cannot progress canonically because dialog-level preflight fallback cycles before the next truthful blocker is surfaced.

## Canon refs
- `STATE.md` NOW
- `docs/ACTIVE_PROGRAM.md`
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r29-initial-booking-handoff-regression-runtime-implementation-a922.md`
- CA_ID `a922-go2f-seed19-r39-dialog-preflight-fallback-cycle-proof-family`

## One web search (mandatory before implementation)
- **Query (exact):** `site:docs.python.org python collections deque rotate documentation`
- **Date/time (local):** `2026-03-23 15:27 +05:00`
- **Sources opened (from this query):** `https://docs.python.org/3/library/collections.html#collections.deque.rotate`
- **Found ready-made solutions:** the Python docs describe deterministic rotation over a bounded collection; the useful takeaway here is to treat visited candidates as explicit state so rotation does not revisit prior positions.
- **Decision:** `build` a bounded proof-tooling repair in local fallback-JID selection.
- **Why:** the blocker lives in repo-specific replay preflight state, not in a reusable external library gap.
- **Rejected options:** new runtime edits, oracle threshold relaxation, acceptance-gate weakening.

## Root cause (mandatory)
- **Symptom:** fresh replay `r39` repairs dialog `1`, turn `1`, but the run remains non-canonical because dialog-level preflight repeatedly resets contaminated conversations and rotates among fallback JIDs before the next truthful blocker can be classified.
- **Minimal reproduction:** inspect `/tmp/booking_quality/a922-go2f-seed19-r39/manual_audit.json` together with replay stdout; dialog `1` completes strict-green, but dialog `2` never records a turn because preflight keeps emitting `preflight_clear` + `preflight_fallback_jid` with contamination reasons such as `re_entry_required`, `canonical_question_contract`, `decision_trace_present`, and `simulation_id_mismatch`.
- **Evidence:**
  - `/tmp/booking_quality/a922-go2f-seed19-r39/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r39/manual_audit.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r39/responses.jsonl`
  - `ops/diagnose.py:3288`
  - `ops/diagnose.py:19258`
- **Five Whys:**
  - Why is `r39` non-canonical? The replay is manually interrupted while still trying to clear contaminated dialog preflight.
  - Why is preflight still trying new JIDs? `_reset_dialog_state(...)` keeps finding contaminated recent conversations for the selected JID.
  - Why does fallback selection revisit already-used JIDs? The selector only persists chosen fallback JIDs, not the contaminated current JID it just failed on.
  - Why does that matter? Rotation over the allowlist can re-select earlier contaminated JIDs instead of exhausting the list and minting a fresh non-allowlist dialog JID.
  - Why is this proof/tooling rather than runtime? No new failing runtime turn is surfaced before the loop; dialog `1` is already strict-green and the obstruction is in `ops/diagnose.py` replay isolation logic.
- **Root cause statement:** replay preflight fallback-JID rotation in `ops/diagnose.py` does not persist the current contaminated JID in the tried set, so allowlist rotation can revisit already-failed JIDs and stall canonical replay isolation before the next runtime blocker is surfaced.
- **Fix mechanism:** make fallback selection persist the current contaminated JID in the shared tried set, add deterministic coverage for allowlist exhaustion without cycling, and then rerun replay.

## Reuse-first plan (mandatory)
- **Internal reuse:**
  - `_llm_quality_select_fallback_jid(...)`
  - `_llm_quality_generate_unique_jid(...)`
  - existing JID-mode regression suite in `truffles-api/tests/test_booking_quality_jid_mode.py`
- **External reuse:**
  - `https://docs.python.org/3/library/collections.html#collections.deque.rotate`
- **Why not reinvent the wheel:** the replay engine already has the right fallback phases; the missing piece is correct visited-candidate bookkeeping.

## Invariant
Do not change runtime semantics, do not weaken replay/oracle gates, and do not mark `r39` as truthful closure evidence.

## Scope
Proof/tooling family classification only.

## Out of scope
- runtime code changes
- acceptance lock/full work
- baseline updates from non-canonical artifacts

## Touch-list
- `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r39-dialog-preflight-fallback-cycle-proof-decision-a922.md`
- `docs/REPORTS/artifacts/2026-03-23-consultant-core-demo-salon-seed19-r39-dialog-preflight-fallback-cycle-proof-decision-a922.md`
- `docs/ACTIVE_PROGRAM.md`
- `docs/SOURCE_OF_TRUTH.yaml`
- `STATE.md`
- `docs/SESSIONS/SESSION-2026-03-15-consultant-core-governance-lock-a922.md`
- `docs/SESSION_INDEX.md`
- `STRUCTURE.md`
- `docs/_generated/AGENT_PACKET.md`
- `docs/_generated/AGENT_PACKET.json`
- `truffles-api/tests/architecture/test_arch_guard_packet.py`

## Plan (1..N)
1. Audit `r39` as non-canonical and inspect the replay preflight loop against fallback-JID selection code.
2. Classify whether the blocker is runtime or proof/tooling before any new code.
3. Lock the next bounded implementation family only if the obstruction is inside replay isolation logic.

## DoD
- `r39` is explicitly excluded as non-canonical.
- The next admissible family is classified in the correct layer.
- The next move is bounded to either proof tooling or runtime, not both.

## Work mode (mandatory)
`closure`

## Checks
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r39 --status done`

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r39/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r39/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r39/responses.jsonl`
- `ops/diagnose.py`

## Rollback
Not applicable; decision-only block.

## No-go
- no runtime patches before layer classification
- no gate/oracle weakening
- no claims that `r39` is canonical replay closure

## Risks/blockers
- replay progress is slow because every contaminated JID requires a real session-reset round-trip; manual interruption keeps artifacts non-canonical.

## Residual architecture debt (mandatory)
- **Current residuals accepted in this block:** `reasoning_core.py` duplicate-def debt remains; truthful next runtime blocker is still unknown until replay isolation succeeds.
- **Why not in this block:** this block only classifies the replay obstruction.
- **Risk if deferred:** the team can keep chasing non-canonical replay churn instead of the next real runtime family.
- **Linked follow-up Task Package(s):** `docs/TASK_PACKAGES/TP-2026-03-23-consultant-core-demo-salon-seed19-r39-dialog-preflight-fallback-cycle-proof-implementation-a922.md`
- **Expiry/trigger to stop deferral:** immediate; either fix the replay tooling family next or stop further replay churn.

## Next-block contract (mandatory)
- **Next block objective:** repair fallback-JID tried-set bookkeeping so replay isolation can exhaust contaminated allowlist JIDs and reach a fresh dialog JID without cycling.
- **First deterministic check command:** `pytest -q truffles-api/tests/test_booking_quality_jid_mode.py -k "fallback_jid or jid_mode"`
- **Blocked-by conditions:** if the replay loop is caused by runtime contamination rather than selector bookkeeping.
- **Owner role for closure:** Brain / Top Architect
