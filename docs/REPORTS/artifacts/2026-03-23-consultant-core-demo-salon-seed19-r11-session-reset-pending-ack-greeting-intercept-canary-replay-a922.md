# Report - 2026-03-23 - Consultant Core Demo Salon Seed19 R11 Session Reset Pending Ack Greeting Intercept Canary Replay A922

## Outcome
- Replay attempted and classified.
- Fresh exact replay `r12` no longer reopens the old greeting-owner interceptor.
- The replay still remains non-canonical before any scenario turn because `pending_ack` is now intercepted by the live explicit-handoff owner.
- The next honest move is `classify_consultant_core_demo_salon_seed19_r12_after_pending_ack_greeting_intercept_replay`.

## What happened
- Verified fresh runtime parity before replay:
  - `HEAD = 0d8d2078697193832a2d6cae6709a2d7489bf9ca`
  - `/admin/version.git_commit = 0d8d2078697193832a2d6cae6709a2d7489bf9ca`
  - `/admin/health` returned `200`
- Re-ran the exact replay as fresh artifact `r12`:
  - `/tmp/booking_quality/a922-go2f-seed19-r12/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r12/brief.md`
  - `/tmp/booking_quality/a922-go2f-seed19-r12/manual_audit.json`

## Truthful split
- The old pending-ack greeting-intercept blocker no longer appears as the first stop.
- Replay stdout for `r12` shows contaminated preflight now receives:
  - `message="Turn planner safe explicit handoff sent"`
  - on `pending_ack` text `ок`
- That means the bounded greeting-owner defer repair is active on the replay surface.
- The new first stop is later in the same preflight clear sequence:
  - `state_before=pending`, `state_after=pending`, `cleared=false`
  - runtime response stays `Turn planner safe explicit handoff sent`
  - contamination reasons still include `reset_ack_missing`
- `r12` therefore remains non-canonical for closure (`dialogs_seen=0`, `responses_rows=0`, `trace_rows=0`), but it truthfully reclassifies the next blocker family.

## Checks
- `git rev-parse HEAD` -> `0d8d2078697193832a2d6cae6709a2d7489bf9ca`
- `curl -sf http://127.0.0.1:18186/admin/version` -> commit parity confirmed
- `curl -sf http://127.0.0.1:18186/admin/health` -> `200`
- `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 ... --run-id a922-go2f-seed19-r12 --quality-lane dev` -> exits on contaminated preflight after pending-ack explicit-handoff intercept
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r12 --status done --strict-artifacts` -> `OK`

## Closure verdict
- The bounded pending-ack greeting-intercept family is no longer the first admissible blocker.
- The next admissible block is a runtime decision on pending-ack interception by the live explicit-handoff owner during session-reset preflight clear.
