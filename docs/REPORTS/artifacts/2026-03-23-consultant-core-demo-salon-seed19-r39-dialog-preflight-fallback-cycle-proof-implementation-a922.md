# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R39 Dialog Preflight Fallback Cycle Proof Implementation A922

## Scope
Bounded replay-tooling repair for the fallback-JID cycling family surfaced after non-canonical replay `r39`.

## Changes Landed
- Updated `_llm_quality_select_fallback_jid(...)` in `ops/diagnose.py:3288` so the shared tried set persists the current contaminated JID before rotating to the next candidate.
- Added deterministic regression `truffles-api/tests/test_booking_quality_jid_mode.py:163` proving repeated selector calls exhaust the allowlist before minting a fresh dialog JID.

## Root Cause Locked Before Code
Replay preflight remembered only fallback candidates it had already chosen. It did not persist the contaminated current JID that just failed. That allowed allowlist rotation to revisit prior contaminated entries and stall replay isolation.

## Deterministic Evidence
- `python3 -m py_compile ops/diagnose.py truffles-api/tests/test_booking_quality_jid_mode.py`
- `pytest -q truffles-api/tests/test_booking_quality_jid_mode.py -k "fallback_jid or jid_mode"`
- Result: `13 passed`

## Partial Live Evidence
- Interrupted replay `/tmp/booking_quality/a922-go2f-seed19-r40` is explicitly audited as non-canonical.
- Despite being non-canonical, it proves the old replay stall boundary moved materially:
  - dialog `1` turns `1..15` are strict-green
  - dialog `2` turns `1..14` are strict-green
  - dialog `3` reaches turn `7` strict-green before manual interruption
- That means the repaired selector now exhausts contaminated allowlist JIDs and reaches fresh dialog JIDs repeatedly enough for replay to progress past the old `r39` dialog-`2` preflight loop.

## Outcome
The bounded proof-tooling fix is landed locally and partial replay evidence shows the old dialog-preflight fallback-cycle family is no longer the first blocker. Truthful next-block classification is still pending because `r40` was manually interrupted and remains non-canonical.
