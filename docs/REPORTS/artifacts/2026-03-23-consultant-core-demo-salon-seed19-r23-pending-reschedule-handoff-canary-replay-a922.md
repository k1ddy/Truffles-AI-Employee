# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R23 Pending Reschedule Handoff Canary Replay A922

## Replay Truth
- Fresh replay artifact: `/tmp/booking_quality/a922-go2f-seed19-r24`
- Runtime parity held on `127.0.0.1:18186` before replay:
  - `/admin/health` -> `200`
  - `/admin/version.git_commit == HEAD`
- The bounded `r23` runtime repair is truthfully closed on fresh evidence:
  - dialog `2`, turn `9` (`На какое время лучше записаться?`) now stays on `booking_prompt` / `collect`
  - `expected_reply_type=service_choice`
  - strict evaluation remains green on the covered row

## What Closed
- The old runtime blocker from `r23` no longer survives on the fresh replay surface.
- Covered downstream rows in dialog `2` also remain strict-green through turn `14`, including:
  - turn `12`: `Можно на 20:00?`
  - turn `13`: `Меня зовут Амина.`
  - turn `14`: `Можно связаться с менеджером?`

## New First Blocker
- Classification: `proof / preflight contamination gap`
- Replay stops non-canonically before dialog `3` turn execution:
  - wrapper exit: `llm-quality: contaminated preflight`
  - final artifact status: `infra_valid=false`, `semantic_valid=false`, `stop_reason=in_progress`
  - strict audit: `/tmp/booking_quality/a922-go2f-seed19-r24/manual_audit.json`
- Fresh blocker shape:
  - dialogs `1` and `2` complete strict-green
  - dialog `3` preflight rotates across previously contaminated allowlist JIDs
  - once the allowlist pool is exhausted, replay fail-closes instead of minting a fresh unique JID
- Evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r24/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r24/runtime_state.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r24/manual_audit.json`
  - `ops/diagnose.py:3288`
  - `ops/diagnose.py:19256`

## Decision
- Do not reopen `reasoning_core.py` first.
- Move to a bounded proof family around fallback-JID exhaustion under contaminated preflight.
