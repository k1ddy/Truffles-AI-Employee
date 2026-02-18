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
    - `CONFIRMED`/`RESCHEDULE_REQUESTED` -> `CHECKED_IN` or `NO_SHOW`
    - `CHECKED_IN` -> `COMPLETED`

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

Backend handlers
- `truffles-api/app/routers/calendar.py`:
  - `list_specialists`, `get_slots`, `list_bookings`, `create_booking`, `update_booking_status`.

Data sources
- `specialists`, `appointments`, `appointment_services`, `appointment_sync_state`, `visits`, `appointment_audit`.
- `SchedulingService` computes slots and creates bookings.

System interactions
- Booking creation uses `SchedulingService.create_appointment` with conflict checks.
- Booking status mutation uses `SchedulingService.update_appointment_status` with transition guard, `visits` upsert, and `appointment_audit` write.
- Errors surfaced as `BOOKING_CONFLICT` when slot is taken.

Related code
- UI: `console-web/src/app/calendar/page.tsx`.
- Backend: `truffles-api/app/routers/calendar.py`, `app/services/appointment_service.py`.
