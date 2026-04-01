# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R22 Preflight Contamination Proof Decision A922

## Truthful Split
- Fresh `r22` replay proves the old runtime family is closed:
  - `pending_ack` returns `Pending ack response sent`
  - exact reset-only `session_reset` now returns `Session reset ack sent`
  - `decision_meta.session_memory_reset="explicit_reset"`
- The replay still fails before dialog turn `1`, but the new blocker is not runtime.

## New First Blocker
- Classification: `proof/preflight contamination gap`
- Evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r22/manual_audit.json`
  - live replay stdout from `r22`
  - `ops/diagnose.py` preflight fallback + contamination logic
- First surviving reasons after the runtime repair:
  - `multiple_recent_conversations`
  - `decision_trace_present`
  - stale historical `booking_active` / `simulation_id_mismatch` on older conversations in the same allowlist JID pool
- Removed reason:
  - `reset_ack_missing`

## Decision
- Do not reopen runtime code first.
- Move to a bounded proof-only family in `ops/diagnose.py` and its contract tests.
