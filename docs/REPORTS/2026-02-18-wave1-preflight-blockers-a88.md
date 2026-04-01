# Wave1 Preflight Blockers (2026-02-18)

## Scope
- Session: `2026-02-18-wave1-visit-fact-pipeline-a88`
- TP: `docs/TASK_PACKAGES/TP-2026-02-18-wave1-visit-fact-pipeline-a88.md`
- Goal: start visit fact pipeline (`CHECKED_IN`, `COMPLETED`, `NO_SHOW`) without booking regressions.

## Facts (current architecture)
- `calendar` router exposes booking create/list/cancel only.
  - `POST /calendar/bookings`
  - `GET /calendar/bookings`
  - `POST /calendar/bookings/{booking_id}/cancel`
- No API endpoint exists for visit-status transitions.
- `SchedulingService` supports create/cancel only; no generic status-transition method.
- `appointments` schema allows statuses `CHECKED_IN`, `COMPLETED`, `NO_SHOW`.
- `visits` and `appointment_audit` tables exist in schema and models.
- `visits` has no unique constraint on `appointment_id` (duplicate risk if transitions are retried concurrently).

## Data preflight (prod DB snapshot)
Commands:
- `SELECT status, COUNT(*) FROM appointments GROUP BY status ORDER BY COUNT(*) DESC;`
- visit consistency aggregate query (`visits_total`, duplicate appointment ids, mismatches, missing visit rows).

Result:
- `appointments`:
  - `CANCELLED=57`
  - `PENDING_CONFIRMATION=48`
  - `CONFIRMED=20`
  - `RESCHEDULE_REQUESTED=3`
- `visits_total=0`
- `visits_duplicate_appointment_ids=0`
- `visit_status_mismatch_count=0`
- `appointment_visit_missing_count=0`

Inference:
- Wave1 can launch from clean visit-fact state (no backfill pressure from existing visit rows).

## Blockers
1. API contract gap: no transition endpoint in `openapi.v1.yaml` for `checked_in/completed/no_show`.
2. Service gap: missing atomic transition method that updates `appointments` + `visits` + `appointment_audit` together.
3. Consistency gap: no DB-level uniqueness guard for one-visit-per-appointment.
4. UI gap: `calendar/page.tsx` has no operator actions for visit statuses.
5. Test gap: no router/service tests for transition state machine and idempotent retries.

## Implementation order (Wave1)
1. Add backend transition API (`POST /calendar/bookings/{booking_id}/status`) with strict allowed transitions.
2. Implement service transaction for status update + visit upsert + audit entry.
3. Add uniqueness guard (`UNIQUE (appointment_id)` in `visits`) with safe migration.
4. Update OpenAPI contract + calendar contract test expectations.
5. Add calendar UI action controls per role with invalid-transition guard hints.
6. Add deterministic tests:
   - success transitions
   - invalid transition rejection
   - idempotent repeat
   - branch/role fail-closed checks

## No-go checks for implementation
- No status mutation without `appointment_audit` row.
- No cross-branch mutation for manager role.
- No duplicate `visits` rows per `appointment_id`.
- No regression in existing create/list/cancel endpoints.
