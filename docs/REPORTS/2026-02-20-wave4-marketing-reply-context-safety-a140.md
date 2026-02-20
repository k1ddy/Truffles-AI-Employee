# Wave 4 — Marketing Reply-Context Safety (a140)

Date
- 2026-02-20

Goal
- Reduce false marketing-context attachment on unrelated inbound turns and keep context scoped to actual text reply events.

Changes
- Updated `truffles-api/app/routers/webhook/decision.py` (`_maybe_attach_marketing_reply_context`):
  - clear stale `conversation.context.marketing_context` at each inbound evaluation;
  - attach only for meaningful final text (skip empty and placeholder payload like `[image]`);
  - use strict recent window (`72h`) instead of broad 30-day lookup;
  - skip deliveries with terminal/non-actionable state (`failed|replied`) and skip when outbox is `FAILED`;
  - skip ambiguous candidate set when two recent deliveries are too close (`6h` ambiguity window);
  - move attach call after ASR/caption normalization so voice/caption replies are evaluated on final text;
  - write explicit trace for skipped paths (`stage=marketing_reply_context`, `decision=skipped`, `reason=<...>`).
- Extended `truffles-api/tests/test_webhook_marketing_reply_context.py` with safety cases:
  - stale context clear when no delivery row;
  - skip for non-attachable delivery status;
  - skip for empty/placeholder inbound text;
  - allow caption text (`message_type=image`) and voice transcript attach;
  - skip for failed outbox delivery;
  - skip for stale and ambiguous delivery candidates.

Checks
- `python3 -m py_compile truffles-api/app/routers/webhook/decision.py` -> pass
- `pytest -q truffles-api/tests/test_webhook_marketing_reply_context.py` -> `10 passed`
- `pytest -q truffles-api/tests/test_message_endpoint.py` -> `222 passed, 2 warnings`
- `pytest -q truffles-api/tests/test_booking_chaos_dialogs.py` -> `1 passed`
- `pytest -q truffles-api/tests/test_booking_quality_response_guard.py` -> `30 passed`
- `timeout 180 pytest -q truffles-api/tests/test_demo_salon_eval.py` -> `EXIT:124` (timeout in this environment)

Outcome
- Marketing reply-context is no longer attached on stale/failed/ambiguous paths and now uses final normalized inbound text (caption/ASR aware).
- Core message endpoint regression tests are green after safety guards.
- `test_demo_salon_eval.py` remains infra/runtime-timeout blocked in this environment.
