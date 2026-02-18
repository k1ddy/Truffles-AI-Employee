# Task Package: Booking Context + Style Handoff Stabilization (r2)

- Canon refs: AGENTS.md, STATE.md booking quality gaps, CA-13 media simulation exception
- Invariant: booking context must not be lost across pending/simulated resolve; media style turns must escalate correctly
- Scope: webhook decision flow, state restore, scenario payload media support, targeted tests
- Out of scope: provider adapter redesign, new packs, judge-mode policy changes
- Touch-list:
  - scripts/booking_dialog_scenarios.py
  - truffles-api/app/routers/telegram_webhook.py
  - truffles-api/app/routers/webhook/decision.py
  - truffles-api/app/services/state_service.py
  - truffles-api/tests/test_message_endpoint.py
  - truffles-api/tests/test_state_service.py
  - truffles-api/tests/test_telegram_webhook.py
- Plan:
  1. restore pending snapshot context on manager resolve/return
  2. fix style media detection and handoff routing for image/photo + caption
  3. keep validated datetime context for list-slots follow-ups without new datetime token
  4. cover with deterministic tests and no-judge LLM replay/style runs
- DoD:
  - no redundant service/time re-ask in previously failing replay turns
  - style payload media enters pending handoff path
  - deterministic tests pass for touched areas
- Checks:
  - pytest -q truffles-api/tests/test_state_service.py truffles-api/tests/test_telegram_webhook.py truffles-api/tests/test_message_endpoint.py::test_style_reference_photo_escalates_during_booking_flow truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_list_slots_keeps_context_datetime_when_expected_time truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_list_slots_keeps_context_datetime_when_expected_service_choice truffles-api/tests/test_message_endpoint.py::test_llm_policy_core_list_slots_drops_hallucinated_date_without_datetime_signal
  - TEST_MODE=1 python3 ops/diagnose.py llm-quality ... --judge-mode off --allow-judge-off --run-id booking-fix-context-style-timecarry-replay-subset124-r8-2026-02-18
  - TEST_MODE=1 python3 ops/diagnose.py llm-quality ... --media-mode payload --judge-mode off --allow-judge-off --run-id booking-fix-context-style-timecarry-style-order-ref-r7-2026-02-18
- Evidence:
  - /tmp/booking_quality/booking-fix-context-style-timecarry-replay-subset124-r8-2026-02-18
  - /tmp/booking_quality/booking-fix-context-style-timecarry-style-order-ref-r7-2026-02-18
- Rollback: revert commit on branch
- No-go: no hardcoded scenario answers, no db/trace cleanup for evidence, no judge-mode enable
- Risks/blockers: residual trace_stale in style run is separate canon hardening item
