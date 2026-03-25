# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R25 Post-Cancel Rebooking State Runtime Decision A922

## Truthful Split
- Fresh replay `r25` closes the old fallback-JID proof family:
  - replay no longer fail-closes during preflight exhaustion
  - fresh generated non-allowlist dialog JIDs are used on the live surface
  - `infra_valid=true`
- The new first blocker is now runtime, not proof.

## New First Blocker
- Classification: `runtime contract bug`
- Evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r25/summary.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r25/manual_audit.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r25/responses.jsonl`
  - `truffles-api/app/services/reasoning_core.py:3321`
  - `truffles-api/app/services/reasoning_core.py:5005`
  - `truffles-api/app/services/reasoning_core.py:8440`
  - `truffles-api/app/services/reasoning_core.py:10095`
- Fresh blocker shape:
  - dialog `2`, turn `8`, message `LLM-QUAL-a922-go2f-seed19-r25-002-08-a600b7`
  - user: `Когда я могу записаться снова?`
  - runtime now produces the correct collect reply surface:
    - `decision_meta.action='booking_prompt'`
    - `decision_meta.expected_reply_type='service_choice'`
  - but continuity is still wrong:
    - actual `conversation_state='pending'`
    - expected scenario state `bot_active`
  - strict fail: `expected_state_mismatch`
- Root cause statement:
  - post-cancel rebooking reentry reaches the correct booking collect owner, but stale pending/handoff continuity still survives and leaves the conversation `pending` instead of restoring `bot_active`

## Decision
- Do not reopen proof tooling first.
- Move to a bounded runtime family in the executable non-frozen owner chain for post-cancel rebooking state continuity.
