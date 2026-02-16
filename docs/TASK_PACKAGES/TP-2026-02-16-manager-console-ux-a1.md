# Task Package: Manager Console UX and Queue Control

- Название/цель: Закрыть P0/P1 неудобства для manager в Inbox: длинные диалоги, слабая прозрачность очереди, разрыв SLA-индикации, некорректная метка first_response_at.
- Canon refs: docs/CONSOLE_AUDIT/pages/inbox.md, docs/CONSOLE_AUDIT/roles/manager.md, STATE.md (manager UX gaps and inbox control loop)

## Invariant
- Не ломать RBAC для manager/support/admin.
- Не менять бизнес-логику handover state machine кроме корректного момента фиксации first_response_at.
- Не ухудшать существующие API контракты (только backward-compatible расширения).

## Scope
- Inbox chat UX: load older, стабильный scroll, корректный send-failure.
- Queue visibility: total count from backend and loaded vs total in UI.
- SLA indicator alignment frontend to backend thresholds.
- first_response_at set only on first real manager outbound.
- Docs + targeted tests.

## Out of scope
- Полный редизайн inbox.
- Новая роль/новый раздел Console.
- Изменение формата decision_trace/meta beyond current manager path.

## Touch-list
- `console-web/src/components/ChatInterface.tsx`
- `console-web/src/components/CaseConversation.tsx`
- `console-web/src/components/CaseList.tsx`
- `console-web/src/components/CaseView.tsx`
- `console-web/src/components/InboxView.tsx`
- `console-web/src/hooks/useCaseData.ts`
- `console-web/src/utils/labels.ts`
- `console-web/src/types/api.generated.ts`
- `truffles-api/app/routers/console.py`
- `truffles-api/app/schemas/console.py`
- `truffles-api/app/services/state_service.py`
- `truffles-api/app/services/callback_service.py`
- `truffles-api/app/services/manager_message_service.py`
- `contracts/console_api/openapi.v1.yaml`
- `truffles-api/tests/test_state_service.py`
- `truffles-api/tests/test_callback.py`
- `truffles-api/tests/test_console_media.py`
- `truffles-api/tests/test_manager_message_rbac.py`
- `docs/CONSOLE_AUDIT/pages/inbox.md`
- `docs/CONSOLE_AUDIT/roles/manager.md`

## Plan
1. Finish chat pagination UX and stable scroll behavior.
2. Align case list totals and SLA indicator to backend contract.
3. Fix first_response_at semantics in all manager send paths.
4. Update docs and add/adjust targeted tests.
5. Run targeted backend/frontend verification.

## DoD
- Manager can load older messages without scroll jump.
- Failed text/media send is visible in chat and not silently marked as success.
- Queue counter shows loaded and total when backend has more results.
- SLA chip timing matches backend warning/breached boundaries.
- first_response_at is absent on take and set on first manager outbound.
- Docs reflect current manager inbox behavior.

## Checks
- `pytest -q truffles-api/tests/test_state_service.py::TestManagerTake::test_success_from_pending`
- `pytest -q truffles-api/tests/test_callback.py::TestHandleTake::test_take_from_pending`
- `pytest -q truffles-api/tests/test_console_media.py::test_console_media_upload_outbox_payload`
- `pytest -q truffles-api/tests/test_manager_message_rbac.py`
- `pytest -q truffles-api/tests/test_message_endpoint.py -k booking_info_interrupt_with_expected_reply_type_keeps_info_reply`
- `cd console-web && npm run lint -- --file src/components/ChatInterface.tsx --file src/components/CaseConversation.tsx --file src/components/CaseList.tsx --file src/hooks/useCaseData.ts --file src/utils/labels.ts`
- `cd console-web && npx tsc --noEmit --incremental false`

## Evidence
- Git diff for touched files.
- Test command outputs with pass status.
- PR description with before/after behavior.
- Screenshots from Inbox flow showing queue counter, load older button, conversation risk hints.

## Rollback
- Revert commit restoring previous chat/list behavior.
- For API contract rollback: remove optional `total` field from response model and OpenAPI.

## No-go
- No hardcoded client-specific behavior.
- No destructive data operations.
- No change to policy/LAW contracts.

## Risks and blockers
- Screenshot capture depends on local UI runtime and auth fixture availability.
