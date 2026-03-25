# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R22 Preflight Contamination Canary Replay A922

## Replay Truth
- Started a fresh local runtime on `127.0.0.1:18186` and confirmed `HEAD == /admin/version.git_commit`.
- Fresh exact replay `/tmp/booking_quality/a922-go2f-seed19-r23` no longer fails on preflight contamination.
- `preflight_clear` is now truthfully clean on reused allowlist JIDs even when historical conversations still exist.

## What Closed
- The old proof family is closed on fresh evidence:
  - `contamination_reasons=[]`
  - `Session reset ack sent`
  - dialog execution now reaches dialog `2`, turn `9`

## New First Blocker
- Classification: `runtime contract bug`
- Artifact: `/tmp/booking_quality/a922-go2f-seed19-r23/manual_audit.json`
- Fresh failure row: `LLM-QUAL-a922-go2f-seed19-r23-002-09-6f3a38`
- User turn: `На какое время лучше записаться?`
- Expected contract: `booking_prompt` / `collect` with `expected_reply_type=service_choice` and `question_contract` trace.
- Actual runtime: `policy_core_guard` -> `handoff` with `reason_code=terminal_owner_unresolved` in `conversation_state=pending`.
