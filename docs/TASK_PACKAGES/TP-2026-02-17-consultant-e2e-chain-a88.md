# TP-2026-02-17-consultant-e2e-chain-a88

- Название/цель: Закрыть разрывы в цепочке консультанта (slots by specialist, booking confirm contract, media handoff context for Console/Telegram) и дать проверяемый evidence.
- Canon refs: AGENTS.md; STATE.md NOW/GAP по consultant booking/media quality; CA_ID: n/a.
- Invariant: Не ломать policy core verifier, media handoff contract и booking safety guard (no false confirmation).
- Scope:
  - `state_service`/`escalation_service`: handover context contract (`context_summary`, `messages`) + media relay metadata retention.
  - `decision` policy core arg normalization for specialist/book-slot/list-slots continuity.
  - Console case schema exposure for handover message context.
  - Targeted tests + llm-quality evidence + manual dialogue analysis.
- Out of scope:
  - Перестройка LLM orchestration или смена архитектурного слоя provider gateway.
  - UI redesign Console.
- Touch-list (files/tables):
  - `truffles-api/app/services/state_service.py`
  - `truffles-api/app/services/escalation_service.py`
  - `truffles-api/app/services/handover_context_service.py`
  - `truffles-api/app/routers/webhook/decision.py`
  - `truffles-api/app/models/handover.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/app/routers/console.py`
  - `truffles-api/tests/test_state_service.py`
  - `truffles-api/tests/test_escalation_media_contract.py`
  - `truffles-api/tests/test_escalation_handover_context.py`
  - `truffles-api/tests/test_message_endpoint.py`
  - DB table: `handovers` (existing columns `context_summary`, `messages`, `meta`).
- Plan:
  1. Sync with `origin/main` and verify merged PR baseline manually.
  2. Patch booking argument normalization gaps in policy core.
  3. Patch handover context persistence and telegram notification context composition.
  4. Expose handover message context in Console case schema/response.
  5. Add/adjust targeted tests.
  6. Run deterministic targeted suite.
  7. Run llm-quality fixed scenarios, then manual turn-by-turn and DB evidence review.
- DoD:
  - `calendar.book_slot` no longer fails on missing `start_at` when datetime is already grounded in booking context.
  - Specialist intent from message is propagated to list/book tool args when missing.
  - `handovers.context_summary` and `handovers.messages` are populated on escalation/reopen.
  - Media handoff row contains bound refs and delivery contract metadata.
  - Console case API returns handover context payload.
  - Targeted tests pass and llm-quality artifacts produced with manual dialogue analysis.
- Checks:
  - `PYTEST_ARGS="/app/tests/test_state_service.py /app/tests/test_escalation_media_contract.py /app/tests/test_escalation_handover_context.py /app/tests/test_message_endpoint.py::test_llm_policy_core_book_slot_backfills_required_args_from_slots_and_specialist_hint /app/tests/test_message_endpoint.py::test_llm_policy_core_list_slots_backfills_specialist_from_message_hint" ./scripts/test_api_container.sh`
  - `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/claim-v6-scenarios-a88.json --count 2 --tool-hooks auto --reset-before-dialog --judge-mode all --fail-on-thresholds --run-id claim-full-chain-2026-02-17-a88-v1`
  - `TEST_MODE=1 python3 ops/diagnose.py llm-quality --scenarios-file /tmp/booking_quality/claim-booking-confirm-v2.json --count 1 --tool-hooks auto --reset-before-dialog --judge-mode all --fail-on-thresholds --run-id claim-booking-confirm-v2-2026-02-17-a88`
- Evidence:
  - `/tmp/booking_quality/claim-full-chain-2026-02-17-a88-v1/{summary.json,brief.md,responses.jsonl,trace_bundle.jsonl}`
  - `/tmp/booking_quality/claim-booking-confirm-v2-2026-02-17-a88/{summary.json,brief.md,responses.jsonl,trace_bundle.jsonl}`
  - SQL snippets for `handovers.context_summary/messages/media_refs` and `appointments` rows.
- Rollback:
  - Revert commit from this branch and redeploy container image from previous main SHA.
- No-go:
  - Нельзя hardcode fixed answers per phrase/test.
  - Нельзя принимать quality как валидный при `infra_valid=false`.
  - Нельзя чистить БД/trace ради evidence.
- Риски/блокеры:
  - llm-quality infra validity may fail on confirm-hook strict policy despite semantic pass.
  - Existing conversations can reopen previous handover IDs, affecting isolated proof readability.
