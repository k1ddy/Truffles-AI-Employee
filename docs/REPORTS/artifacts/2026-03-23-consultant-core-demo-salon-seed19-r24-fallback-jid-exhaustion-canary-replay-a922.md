# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R24 Fallback JID Exhaustion Canary Replay A922

## Truthful Replay Result
- Fresh exact replay `r25` proves the old fallback-JID proof family is closed on the live surface.
- Replay now uses fresh non-allowlist dialog JIDs under outbox-enabled unique mode instead of fail-closing during preflight exhaustion.
- The run no longer stops before dialog execution; it reaches dialog `2`, turn `8` with `infra_valid=true`.

## Evidence
- `/tmp/booking_quality/a922-go2f-seed19-r25/summary.json`
- `/tmp/booking_quality/a922-go2f-seed19-r25/brief.md`
- `/tmp/booking_quality/a922-go2f-seed19-r25/manual_audit.json`
- `/tmp/booking_quality/a922-go2f-seed19-r25/runtime_state.json`

## Closure Proof
- `runtime_state.progress.remote_jid_by_dialog` now records fresh generated dialog JIDs, including non-allowlist values such as `99953746942@s.whatsapp.net` and `99905914999@s.whatsapp.net`.
- `summary.json` is now `infra_valid=true` with `stop_reason=max_failures_reached:1`, so the old preflight-exhaustion blocker is gone.

## New First Blocker
- Classification moved forward to runtime.
- Fresh first blocker: dialog `2`, turn `8`, message `LLM-QUAL-a922-go2f-seed19-r25-002-08-a600b7`.
- User: `Когда я могу записаться снова?`
- Runtime returns a valid `booking_prompt` collect reply, but keeps `conversation_state=pending` instead of the expected `bot_active`.
