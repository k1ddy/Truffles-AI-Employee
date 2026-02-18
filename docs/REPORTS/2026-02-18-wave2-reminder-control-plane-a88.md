# Wave2 Reminder Control Plane Report (2026-02-18)

## Scope
- TP: `docs/TASK_PACKAGES/TP-2026-02-18-wave2-reminder-control-plane-a88.md`
- Goal: add Console reminder queue diagnostics + safe retry flow without breaking existing outbox/cases/booking behavior.

## Delivered
- Backend reminder ops endpoints:
  - `GET /console/v1/ops/reminders`
  - `POST /console/v1/ops/reminders/retry`
- Reminder diagnostics includes:
  - counts: `pending/sent/failed/due_now/overdue_15m`
  - top failure reasons (`error_buckets`)
  - per-row outbox linkage (`outbox_id/status/attempts/last_error/updated_at`) via `dedupe_key -> inbound_message_id`
- Safe retry behavior:
  - retries only `FAILED/PENDING`
  - bulk retry requires explicit `confirm=true` (409 otherwise)
  - tenant/branch fail-closed scope preserved
  - audit event recorded (`event_type=reminder_retry`)
- Reminder processing observability improved:
  - `appointment_reminder_service.process_reminder_jobs` now increments `attempt` on each processed job.
- Ops UI:
  - new Reminder Queue panel on `/ops` with status filters, template filter, diagnostics counters, error taxonomy, linked outbox status, row retry and bulk retry.

## Contract updates
- OpenAPI updated:
  - new paths: `/ops/reminders`, `/ops/reminders/retry`
  - new schemas: `ReminderCounts`, `ReminderErrorBucket`, `ReminderItem`, `ReminderListResponse`, `ReminderRetryRequest`, `ReminderRetryResponse`

## Files touched
- Backend:
  - `truffles-api/app/routers/console.py`
  - `truffles-api/app/schemas/console.py`
  - `truffles-api/app/services/appointment_reminder_service.py`
- Frontend:
  - `console-web/src/components/OpsPage.tsx`
- Contract/docs:
  - `contracts/console_api/openapi.v1.yaml`
  - `docs/CONSOLE_AUDIT/pages/ops.md`
- Tests:
  - `truffles-api/tests/test_console_outbox_ops.py`
  - `truffles-api/tests/test_console_openapi_ops_reminder_contract.py`

## Checks
- `python3 -m py_compile truffles-api/app/routers/console.py truffles-api/app/services/appointment_reminder_service.py truffles-api/app/schemas/console.py` -> pass
- `pytest -q truffles-api/tests/test_reminder_jobs.py truffles-api/tests/test_console_outbox_ops.py truffles-api/tests/test_console_ops_jobs.py truffles-api/tests/test_console_openapi_ops_reminder_contract.py` -> `20 passed`
- `python3 truffles-api/scripts/generate_openapi.py --check` -> pass (method drift check)

## Environment blockers (known)
- `npm --prefix console-web run generate:api` -> `openapi-typescript: not found`
- `npm --prefix console-web run lint -- --file src/components/OpsPage.tsx` -> `next: not found`
- Interpretation: frontend dependency layer is not installed in this environment; backend and API contract validations are green.
- Canon blocker outside wave scope: `STATE.md` currently has unresolved merge markers in `NOW` section (`<<<<<<< ...`), which should be fixed before canon-sensitive doc updates.
