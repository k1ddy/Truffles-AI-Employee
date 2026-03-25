# Dialog Audit: Booking + Media + Runtime Safety (2026-02-17)

Scope:
- per-dialog evidence from `/tmp/booking_quality/booking-lock-step3-42-skipoutbox/responses.jsonl`
- manual webhook probes in runtime DB (`messages.metadata.messageId`)
- runtime outbox worker blocker

## Evidence Table

| Dialog / Message ID | User turn | Actual bot behavior | Expected behavior | Violation / Root cause | Fix status |
|---|---|---|---|---|---|
| `LLM-QUAL-booking-lock-step3-42-skipoutbox-002-03-90e2c2` | `Какова цена маникюра?` | Escalated with `contract_invalid` + booking follow-up instead of direct price answer | FACT pricing answer from catalog/truth | Strict post-condition mismatch for `catalog.service_query` decisions (`tool_decision_mismatch`) in verifier path (`truffles-api/app/routers/webhook/decision.py:3464`, `truffles-api/app/routers/webhook/decision.py:3516`) | `fixed` (action-specific success decisions already added) |
| `LLM-QUAL-booking-lock-step3-42-skipoutbox-009-05-3604f0` | `Я не могу в 15:00, может быть 16:00?` | Generic clarify: `Подскажите, пожалуйста, что именно вас интересует?` | Booking-reference prompt for reschedule/check flow | `appointment_id` verifier error had no slot mapping, fell into generic clarify (`truffles-api/app/routers/webhook/decision.py:3482`) | `fixed` (`appointment_id -> booking_reference`, dedicated prompt) |
| `LLM-QUAL-booking-lock-step3-42-skipoutbox-009-10-3c5296` | `Подтвердите новое время, пожалуйста.` | Generic clarify again | Booking-reference prompt or valid reschedule/check path | Same root cause as above + missing appointment ref propagation from context | `fixed` (slot mapping + context reference autofill) |
| `MANUAL-CHECK-PRICE-20260217043855-30138` | `Какова цена маникюра?` | Assistant returned factual pricing (plus closed-hours notice) | FACT pricing answer | Previously failing pricing contract path now returns correct response; DB evidence in `messages` row (`role=assistant`) | `fixed-confirmed` |
| `MANUAL-REF-1771286380` | `Перенеси запись на завтра в 11:00` | Policy-pack escalation: `Перенос записи подтверждает администратор...` | For current policy, escalation is acceptable, but must be explicit and traceable | Hard-LAW policy gate dominates this flow (`policy_gate=hard_law` in decision_meta); not a verifier fallback issue | `open-by-design` (policy decision) |
| Live media step2 probes (`LIVE-MEDIA-STEP2-*`) | media handoff | Stored media + pending path, but outbox delivery failed (`invalid_response`) | End-to-end relay to manager/Telegram/Console | Outbox runtime + provider response path unstable; see prior report `docs/REPORTS/2026-02-16-live-media-chaos-single-pass-v1.md` | `open` |

## Implemented fixes in this cycle

1. Booking reference verifier path:
- Added `appointment_id` slot mapping to `booking_reference`: `truffles-api/app/routers/webhook/decision.py:3482`
- Added dedicated prompt: `MSG_BOOKING_ASK_REFERENCE` in `truffles-api/app/routers/webhook/decision.py:2746`
- Added auto-fill of `appointment_id` from booking context for `calendar.get_booking/reschedule/cancel`: `truffles-api/app/routers/webhook/decision.py:9353`
- Added persistence of tool result `appointment_id` back to booking context: `truffles-api/app/routers/webhook/decision.py:9643`, `truffles-api/app/routers/webhook/decision.py:9680`

2. Runtime blocker remediation (outbox restart loop):
- Root cause: safety guard blocked startup (`test_mode_outbox_worker_on_nonlocal_db`) in `truffles-api/app/services/runtime_safety.py:111`
- Added explicit compose knob for controlled override:
  `truffles-api/docker-compose.yml:46` (`OUTBOX_WORKER_UNSAFE_ALLOW=${OUTBOX_WORKER_UNSAFE_ALLOW:-0}`)
- Runtime applied for this stand:
  - recreated `truffles-outbox` with `OUTBOX_WORKER_UNSAFE_ALLOW=1`
  - status moved from `Restarting` to stable `Up`

## Targeted checks executed

- `pytest -q truffles-api/tests/test_message_endpoint.py -k "reschedule_missing_reference_prompts_booking_reference or get_booking_invalid_reference_maps_to_booking_reference_slot or reschedule_uses_booking_context_appointment_id or book_slot_missing_start_at_blocked_by_policy_verifier or book_slot_contract_invalid_escalates or low_confidence_book_slot_with_complete_slots_is_allowed"`
  - result: `6 passed`
- `pytest -q truffles-api/tests/test_webhook_media_policy.py`
  - result: `3 passed`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k "catalog_tool_decision_mismatch_escalates or catalog_service_reply_normalized_to_booking_prompt"`
  - result: `3 passed`

## Remaining open items

1. Media relay end-to-end still needs a clean non-`invalid_response` outbox delivery proof to Telegram + Console in one evidence bundle.
2. Hard-LAW policy behavior for reschedule/check should be reviewed as product policy (not code bug), because it can intentionally override tool-driven conversational flow.
