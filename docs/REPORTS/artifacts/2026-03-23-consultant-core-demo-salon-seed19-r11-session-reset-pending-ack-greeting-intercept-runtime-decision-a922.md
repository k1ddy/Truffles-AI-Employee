# Report - 2026-03-23 - Consultant Core Demo Salon Seed19 R11 Session Reset Pending Ack Greeting Intercept Runtime Decision A922

## Outcome
- Complete.
- The old provider-transport blocker is no longer first on fresh replay evidence.
- The new first admissible blocker is a bounded runtime family: pending-ack session-reset clear traffic is intercepted by the live greeting owner and leaves the conversation in `pending`.
- The next honest move is `implement_consultant_core_demo_salon_seed19_r11_session_reset_pending_ack_greeting_intercept_runtime_family`.

## Truthful split
- `r10` is stale, pre-existing, and non-canonical:
  - `invalid_preflight`
  - incomplete artifact
  - closed via `/tmp/booking_quality/a922-go2f-seed19-r10/manual_audit.json`
- `r11` is the first admissible fresh replay after the transport repair:
  - runtime parity was confirmed before run
  - strict audit exists at `/tmp/booking_quality/a922-go2f-seed19-r11/manual_audit.json`
- Replay stdout shows the repaired explicit-handoff path now succeeds in simulation mode:
  - `message="Turn planner safe explicit handoff sent"`
  - `decision_meta.transport_simulated=true`
- The first surviving blocker appears immediately after that:
  - `pending_ack` with text `ок`
  - runtime response `Turn planner safe greeting owner sent`
  - `state_before=pending`, `state_after=pending`, `cleared=false`
  - final run outcome remains non-canonical with `dialogs_seen=0`

## Classification
- Blocker class: `runtime contract bug`
- Family: `session-reset pending-ack greeting intercept`
- Live path:
  - greeting owner executes early at `truffles-api/app/services/reasoning_core.py:15246`
  - live greeting owner body is `truffles-api/app/services/reasoning_core.py:8108`
- Decision:
  - do not patch proof/oracle
  - do not rerun replay first
  - patch the bounded non-frozen greeting-owner interception family next
