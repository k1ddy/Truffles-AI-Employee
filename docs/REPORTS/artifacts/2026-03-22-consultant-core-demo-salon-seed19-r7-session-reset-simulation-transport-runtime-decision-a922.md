# Report - 2026-03-22 - Consultant Core Demo Salon Seed19 R7 Session Reset Simulation Transport Runtime Decision A922

## Decision
- Classified the next first admissible blocker as a `runtime contract bug`, not another proof fallback defect.

## Fresh evidence used
- `/tmp/booking_quality/a922-go2f-seed19-r7/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r8/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r9/manual_audit.json`
- fresh local runtime logs from the `127.0.0.1:18186` replay attempts

## What changed after the proof fix
- old `r6` blocker is closed: contaminated replay fallback no longer jumps to a generated non-allowlist JID while outbox is enabled
- fresh replay now stops earlier in preflight because simulated session-reset traffic on allowlist JIDs creates real explicit handoff state and hits provider transport

## Root cause
- `ops/diagnose.py` sends preflight session-reset messages with `simulation_mode=True`
- the executable later explicit-handoff owner in `truffles-api/app/services/reasoning_core.py` still calls `send_message_safe(...)` directly
- `truffles-api/app/services/chatflow_service.py` sends to real ChatFlow for allowlist JIDs and surfaced `Your plan has been expired please renew.` / `CHATFLOW_BILLING_BLOCKED`
- `truffles-api/app/adapters/chatflow.py` already contains a simulation-safe transport path, so the failure is not a generic provider limitation; it is a runtime bypass of the simulation-aware adapter contract

## Truthful classification
- `r7`: first admissible blocker; non-canonical preflight contamination after allowlist-safe fallback; provider transport was touched during simulated reset traffic
- `r8`: invalid-preflight artifact created only because the manual-audit gate rejected the previous pending run
- `r9`: same as `r8`; not a new blocker family

## Consequence
- the next honest move is one bounded runtime family on the executable later explicit-handoff owner / simulation-safe transport seam
- do not open another proof or replay-only block first

## Next move
- `implement_consultant_core_demo_salon_seed19_r7_session_reset_simulation_transport_runtime_family`
