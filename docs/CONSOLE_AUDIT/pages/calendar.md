# Page: Calendar (Bookings)

Route
- `/calendar`

UI entry points
- `console-web/src/app/calendar/page.tsx`

Roles
- Read: platform_admin, owner, admin, manager.
- Write (create booking): platform_admin, owner, admin, manager.
- Write (visit status update): platform_admin, owner, admin, manager.

Layout
- Header with title, guidance, and link back to Inbox.
- Left side: filters + available slots + booking form.
- Right side: bookings list for selected date.

Key UI elements
- Specialist selector (dropdown).
- Service selector (if specialist has services).
- Date picker.
- Slots grid:
  - Available slots are clickable (creates booking form).
  - Unavailable slots are disabled.
- Booking form:
  - Customer name/phone.
  - Optional notes.
  - Create booking and cancel buttons.
- Bookings list:
  - Time range, status badge, specialist name, customer details, service.
  - Status actions:
    - `PENDING_CONFIRMATION`/`CONFIRMED`/`RESCHEDULE_REQUESTED`/`HOLD` -> `COMPLETED` (`Пришел`) or `NO_SHOW`
    - `CHECKED_IN` (legacy row) -> `COMPLETED` (`Пришел`) or `NO_SHOW`
    - `NO_SHOW` -> follow-up actions `Связались` or `Перезаписали` (фиксируется в audit, статус визита не меняется)

Operating contract (one page)
| Role | Action in Calendar | Fact written (SoT) | Why it matters | KPI surface |
| --- | --- | --- | --- | --- |
| manager/admin/owner | `Пришел` | `appointments.status=COMPLETED` + `visits` row + `appointment_audit` | Confirms that service was delivered | Completed visits by branch/day/specialist |
| manager/admin/owner | `Не пришел` | `appointments.status=NO_SHOW` + `appointment_audit` | Moves booking into no-show handling | No-show count and rate |
| manager/admin/owner | `Связались` (on `NO_SHOW`) | `appointment_audit.action=no_show_followup`, payload: `result=contacted`, `follow_up_closed_at`, `follow_up_closed_by` | Closes operational loop for missed visit | Closed no-show follow-ups |
| manager/admin/owner | `Перезаписали` (on `NO_SHOW`) | same audit fact, payload: `result=rebooked`, optional `rebooked_appointment_id` | Shows that no-show was handled with rebooking | Rebooked no-show follow-ups |

Rule of ownership
- Follow-up closure is done by manager/admin/owner from the same Calendar list where `NO_SHOW` is visible.
- No separate screen is required for this wave.

Behavior
- Default date is set to the user's local date (no UTC shift).
- Date input enforces `min=today` (past dates are not selectable).
- Specialists load error shows a user-friendly message with expandable technical details.

API endpoints used
- Specialists: `GET /calendar/specialists`.
- Slots: `GET /calendar/slots?specialist_id=...&date=...&duration=...`.
- Bookings list: `GET /calendar/bookings?date_from=...&date_to=...`.
- Create booking: `POST /calendar/bookings`.
- Update booking visit status: `POST /calendar/bookings/{booking_id}/status`.
- Record no-show follow-up: `POST /calendar/bookings/{booking_id}/no-show-followup`.

Backend handlers
- `truffles-api/app/routers/calendar.py`:
  - `list_specialists`, `get_slots`, `list_bookings`, `create_booking`, `update_booking_status`.

Data sources
- `specialists`, `appointments`, `appointment_services`, `appointment_sync_state`, `visits`, `appointment_audit`.
- `SchedulingService` computes slots and creates bookings.

System interactions
- Booking creation uses `SchedulingService.create_appointment` with conflict checks.
- Booking status mutation uses `SchedulingService.update_appointment_status` with transition guard, `visits` upsert, and `appointment_audit` write.
- In the operator UX, `Пришел` is a terminal outcome and maps directly to `COMPLETED` (separate check-in step is removed).
- For `NO_SHOW`, manager follow-up is tracked via `appointment_audit.action=no_show_followup` with explicit `result=contacted|rebooked`.
- Errors surfaced as `BOOKING_CONFLICT` when slot is taken.

Related code
- UI: `console-web/src/app/calendar/page.tsx`.
- Backend: `truffles-api/app/routers/calendar.py`, `app/services/appointment_service.py`.
