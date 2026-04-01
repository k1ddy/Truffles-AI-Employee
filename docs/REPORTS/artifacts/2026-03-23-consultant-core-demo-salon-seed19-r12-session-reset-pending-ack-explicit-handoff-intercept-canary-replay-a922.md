# Report - 2026-03-23 - Consultant Core Demo Salon Seed19 R12 Session Reset Pending Ack Explicit Handoff Intercept Canary Replay A922

## Outcome
- Replay attempted and classified.
- `r13` is now explicitly non-canonical and inadmissible.
- Fresh exact replay `r14` no longer reopens the old explicit-handoff interceptor.
- The replay still remains non-canonical before any scenario turn because `pending_ack` now falls into the terminal unresolved runtime path.
- The next honest move is `classify_consultant_core_demo_salon_seed19_r14_after_pending_ack_explicit_handoff_intercept_replay`.

## What happened
- Verified fresh runtime parity before replay:
  - `HEAD = 0d8d2078697193832a2d6cae6709a2d7489bf9ca`
  - `/admin/version.git_commit = 0d8d2078697193832a2d6cae6709a2d7489bf9ca`
  - `/admin/health` returned `200`
- Strict-audited `/tmp/booking_quality/a922-go2f-seed19-r13` and closed it as self-inflicted invalid preflight evidence:
  - `runtime_fingerprint_preflight` failed with `admin_version_unreachable`
  - artifact stayed incomplete (`dialogs_seen=0`, missing trace/responses)
- Re-ran the exact replay as fresh artifact `r14`:
  - `/tmp/booking_quality/a922-go2f-seed19-r14/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r14/brief.md`
  - `/tmp/booking_quality/a922-go2f-seed19-r14/manual_audit.json`

## Truthful split
- The old pending-ack explicit-handoff-intercept blocker no longer appears as the first stop.
- Replay stdout for `r14` shows contaminated preflight now receives:
  - `message="Reasoning core terminal unresolved response skipped"`
  - `bot_response="Извините, произошла ошибка. Попробуйте позже."`
  - on `pending_ack` text `ок`
- That means the bounded explicit-handoff defer repair is active on the replay surface.
- The new first stop is later in the same preflight clear sequence:
  - `state_before=pending`, `state_after=pending`, `cleared=false`
  - contamination reasons still keep multiple recent pending / trace-bearing conversations
- `r14` therefore remains non-canonical for closure (`dialogs_seen=0`, `responses_rows=0`, `trace_rows=0`), but it truthfully reclassifies the next blocker family.

## Checks
- `git rev-parse HEAD` -> `0d8d2078697193832a2d6cae6709a2d7489bf9ca`
- `curl -sf http://127.0.0.1:18186/admin/version` -> commit parity confirmed
- `curl -sf http://127.0.0.1:18186/admin/health` -> `200`
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r13 --status done --strict-artifacts` -> `OK`
- `python3 ops/diagnose.py llm-quality --base-url http://127.0.0.1:18186 ... --run-id a922-go2f-seed19-r14 --quality-lane dev` -> exits on contaminated preflight after terminal unresolved response path
- `python3 ops/diagnose.py llm-quality-audit --run-dir /tmp/booking_quality/a922-go2f-seed19-r14 --status done --strict-artifacts` -> `OK`

## Closure verdict
- The bounded pending-ack explicit-handoff-intercept family is no longer the first admissible blocker.
- The next admissible block is a runtime decision on pending-ack falling through to the terminal unresolved path during session-reset preflight clear.
