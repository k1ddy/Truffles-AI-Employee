# Report - 2026-03-23 - Consultant Core Demo Salon Seed19 R7 Session Reset Simulation Transport Canary Replay A922

## Outcome
- Replay attempted and classified.
- Pre-existing `r10` was closed as non-canonical (`invalid_preflight`, incomplete artifact discovered before the fresh attempt).
- Fresh exact replay `r11` did not reopen the old provider-transport blocker; it surfaced a new preflight-clear runtime family before turn execution.
- The next honest move is `classify_consultant_core_demo_salon_seed19_r11_session_reset_pending_ack_greeting_intercept_runtime_family`.

## What happened
- Verified fresh runtime parity before replay:
  - `HEAD = 0d8d2078697193832a2d6cae6709a2d7489bf9ca`
  - `/admin/version.git_commit = 0d8d2078697193832a2d6cae6709a2d7489bf9ca`
- Attempted replay `r10`, but the output directory already contained a stale pre-existing incomplete artifact.
- Audited that stale artifact:
  - `/tmp/booking_quality/a922-go2f-seed19-r10/manual_audit.json`
  - verdict: non-canonical `invalid_preflight`, `run_incomplete`
- Re-ran the exact replay as fresh artifact `r11`:
  - `/tmp/booking_quality/a922-go2f-seed19-r11/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r11/brief.md`
  - `/tmp/booking_quality/a922-go2f-seed19-r11/manual_audit.json`

## Truthful split
- The old simulation-transport blocker no longer appears as the first stop.
- Replay stdout for `r11` showed the preflight session-reset now returns:
  - `message="Turn planner safe explicit handoff sent"`
  - `decision_meta.transport_simulated=true`
- That means the bounded explicit-handoff simulation transport repair is active on the replay surface.
- The new first stop is later in the same preflight clear sequence:
  - repeated `pending_ack` sends with text `ок`
  - runtime response: `Turn planner safe greeting owner sent`
  - `state_before=pending`, `state_after=pending`, `cleared=false`
  - final replay error: `contaminated preflight`
- `r11` therefore remains non-canonical for closure (`dialogs_seen=0`, `turns=0`), but it truthfully reclassifies the next blocker family.

## Checks
- `git rev-parse HEAD` -> `0d8d2078697193832a2d6cae6709a2d7489bf9ca`
- `curl -sf http://127.0.0.1:18186/admin/version` -> commit parity confirmed
- `curl -sf http://127.0.0.1:18186/admin/health` -> `200`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r10 --status done ...` -> stale artifact closed as non-canonical
- `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 ... --run-id a922-go2f-seed19-r11 --quality-lane dev` -> exits on contaminated preflight after pending-ack greeting intercept
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r11 --status done --strict-artifacts` -> `OK`

## Closure verdict
- The bounded simulation transport family is no longer the first admissible blocker.
- The next admissible block is a runtime decision on `pending_ack` interception by the live greeting owner during session-reset preflight clear.
