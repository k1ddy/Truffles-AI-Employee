# Report — 2026-03-23 Consultant Core Demo Salon Seed19 R23 Pending Reschedule Handoff Runtime Decision A922

## Truthful Split
- Fresh replay `r23` closes the old proof family:
  - `infra_valid=true`
  - `contamination_reasons=[]`
  - dialog execution reaches dialog `2`, turn `9`
- The new first blocker is not proof and not preflight.

## New First Blocker
- Classification: `runtime contract bug`
- Evidence:
  - `/tmp/booking_quality/a922-go2f-seed19-r23/manual_audit.json`
  - `/tmp/booking_quality/a922-go2f-seed19-r23/responses.jsonl`
  - live runtime path in `truffles-api/app/services/reasoning_core.py`
- Fresh failing row:
  - `LLM-QUAL-a922-go2f-seed19-r23-002-09-6f3a38`
  - user: `На какое время лучше записаться?`
  - expected: `booking_prompt` collect with `expected_reply_type=service_choice` and `question_contract` trace
  - actual: `policy_core_guard` / `handoff` with `reason_code=terminal_owner_unresolved` in `conversation_state=pending`

## Decision
- Do not reopen proof tooling first.
- Move to a bounded runtime family around pending-state reschedule follow-up handoff interception.
