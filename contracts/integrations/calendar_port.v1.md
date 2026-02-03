# Calendar Port v1

Purpose
- Provide a stable interface for scheduling systems (Google Calendar, CRM calendars, etc).

Interface
- get_availability(request: AvailabilityRequest) -> Result[AvailabilityResult]
- create_booking(request: BookingCreateRequest) -> Result[BookingCreateResult]
- cancel_booking(request: BookingCancelRequest) -> Result[BookingCancelResult]

AvailabilityRequest
- client_id: uuid
- branch_id: uuid | null
- specialist_id: string | null
- service_id: string | null
- start_at: date-time
- end_at: date-time
- metadata: object

AvailabilityResult
- slots: list[{start_at: date-time, end_at: date-time, specialist_id: string | null}]
- raw: object

BookingCreateRequest
- client_id: uuid
- branch_id: uuid | null
- customer_name: string | null
- customer_phone: string | null
- service_id: string | null
- specialist_id: string | null
- start_at: date-time
- end_at: date-time
- idempotency_key: string
- metadata: object

BookingCreateResult
- booking_id: string
- external_id: string | null
- raw: object

BookingCancelRequest
- booking_id: string
- reason: string | null
- metadata: object

BookingCancelResult
- cancelled: boolean
- raw: object

Rules
- Idempotency required for create_booking.
- Errors are returned as Result.fail with stable codes (CALENDAR_TIMEOUT, SLOT_UNAVAILABLE, CALENDAR_CONFLICT, CALENDAR_STALE).
- Provider data never overwrites SoT; inbound provider events map to busy blocks only.
- Availability must be fresh; stale data should return CALENDAR_STALE (caller falls back to collect_preferences).

Notes
- Breaking changes require a new version file (calendar_port.v2.md).
