# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R22 Preflight Contamination Proof Implementation A922

## What Changed
- `ops/diagnose.py` now distinguishes live preflight contamination from historical bot-active residue.
- Historical bot-active rows no longer poison replay preflight just because they still carry old booking context, decision traces, or previous simulation ids.
- `multiple_recent_conversations` now fires only when more than one recent conversation is still actually contaminated.

## Why
- `r22` already proved reset correctness on the latest conversation.
- The surviving blocker was proof isolation drift: the classifier treated historical allowlist history as if it were live continuity.

## Deterministic Proof
- `pytest -q truffles-api/tests/test_booking_quality_status_gate.py truffles-api/tests/test_booking_quality_jid_mode.py -k "preflight or contamination or fallback_jid"`
- Result: `12 passed`

## Next Honest Move
- Run one fresh exact replay on the same seed-`19` scenario file and strict-audit the result before opening any new runtime family.
