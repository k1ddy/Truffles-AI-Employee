# Report - 2026-03-23 - Consultant Core Demo Salon Seed19 R14 Session Reset Pending Ack Terminal Unresolved Runtime Decision A922

## Outcome
- Complete.
- Invalid `r13` is now explicitly excluded as self-inflicted non-canonical evidence.
- The old pending-ack explicit-handoff-intercept blocker is no longer first on fresh replay evidence.
- The new first admissible blocker is a bounded runtime family: pending-ack session-reset clear traffic now falls through to the terminal unresolved response path and leaves the conversation in `pending`.
- The next honest move is `implement_consultant_core_demo_salon_seed19_r14_session_reset_pending_ack_terminal_unresolved_runtime_family`.

## Truthful split
- `r14` is the first admissible fresh replay after the explicit-handoff defer repair:
  - runtime parity was confirmed before run
  - `/admin/health` returned `200`
  - strict audit exists at `/tmp/booking_quality/a922-go2f-seed19-r14/manual_audit.json`
- `r13` is excluded from closure evidence:
  - strict audit records `invalid_runtime_fingerprint_preflight`
  - `admin_version_unreachable`
  - `dialogs_seen=0`
- Replay stdout for `r14` shows the repaired greeting/explicit-handoff paths no longer consume `pending_ack`:
  - `pending_ack` no longer returns `Turn planner safe greeting owner sent`
  - `pending_ack` no longer returns `Turn planner safe explicit handoff sent`
  - it now returns `Reasoning core terminal unresolved response skipped`
- The first surviving blocker appears immediately after that:
  - `pending_ack` with text `ок`
  - `bot_response="Извините, произошла ошибка. Попробуйте позже."`
  - `state_before=pending`, `state_after=pending`, `cleared=false`
  - final run outcome remains non-canonical with `dialogs_seen=0`

## Classification
- Blocker class: `runtime contract bug`
- Family: `session-reset pending-ack terminal unresolved`
- Live path:
  - greeting defer guard is already active at `truffles-api/app/services/reasoning_core.py:8190`
  - explicit-handoff defer guard is already active at `truffles-api/app/services/reasoning_core.py:8283`
  - terminal unresolved closure returns the blocking response at `truffles-api/app/services/reasoning_core.py:15639`
- Decision:
  - do not patch proof/oracle
  - do not rerun replay first
  - patch the bounded non-frozen terminal-unresolved family next
