# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R14 Session Reset Pending Ack Terminal Unresolved Canary Replay A922

## Replay Chain
- Non-canonical attempts closed as invalid or interrupted evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r15`
  - `/tmp/booking_quality/a922-go2f-seed19-r18`
  - `/tmp/booking_quality/a922-go2f-seed19-r19`
  - `/tmp/booking_quality/a922-go2f-seed19-r20`
  - `/tmp/booking_quality/a922-go2f-seed19-r21`
- Truthful fresh replay for the repaired runtime family:
  - `/tmp/booking_quality/a922-go2f-seed19-r22`
  - strict audit: `/tmp/booking_quality/a922-go2f-seed19-r22/manual_audit.json`

## Runtime Closure Proven
- `pending_ack` still clears pending state.
- `session_reset` no longer returns `Turn planner safe explicit handoff sent`.
- Fresh runtime replay stdout now records:
  - `message="Session reset ack sent"`
  - `decision_meta.session_memory_reset="explicit_reset"`
  - `decision_trace` contains `session_memory.reset` / `session_memory.reset_ack`

## New First Surviving Blocker
- The replay still remains pre-turn and non-canonical, but not because of a runtime reset owner bug.
- The new first blocker is proof/preflight contamination:
  - allowlist fallback JIDs remain exhausted/dirty under outbox-enabled replay
  - contamination reasons are now dominated by historical recent-conversation state (`multiple_recent_conversations`, `decision_trace_present`, stale `booking_active` / `simulation_id_mismatch` on older conversations)
  - `reset_ack_missing` no longer survives

## Classification
- Runtime family `r14 pending_ack/session_reset owner path`: closed.
- New surviving family: `proof/preflight contamination`, not a new runtime blocker.
