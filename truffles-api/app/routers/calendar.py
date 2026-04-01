"""
Calendar and Booking API Router.
Provides endpoints for slots, bookings, and Google Calendar OAuth.
"""
import re
from datetime import datetime, timedelta, timezone
from typing import Any, List, Literal, Optional
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.logging_config import (
    get_logger,
    record_calendar_booking_action_denied,
    record_calendar_booking_double_submit_blocked,
    record_calendar_booking_version_conflict,
    record_calendar_filter_apply,
    record_calendar_filter_reset,
    record_calendar_followup_invalid,
)
from app.models.agent import Agent
from app.models.appointment import Appointment
from app.models.appointment_audit import AppointmentAudit
from app.models.appointment_service import AppointmentService as AppointmentServiceModel
from app.models.appointment_sync_state import AppointmentSyncState
from app.models.branch import Branch
from app.models.conversation import Conversation
from app.models.handover import Handover
from app.models.specialist import Specialist
from app.services.appointment_reminder_service import schedule_default_reminders
from app.services.appointment_service import (
    AppointmentConflictError,
    AppointmentLifecycleActionDeniedError,
    AppointmentNotFoundError,
    AppointmentStatusValidationError,
    AppointmentVersionConflictError,
    InvalidAppointmentTransitionError,
    SchedulingService,
    SpecialistNotFoundError,
)
from app.services.audit_service import record_audit_event
from app.services.calendar_action_contract import (
    BOOKING_ACTION_ORDER,
    CalendarActorClass,
    CalendarBlockedActionPayload,
    CalendarBookingActionId,
    CalendarBookingBlockedReasonCode,
    build_calendar_booking_action_contract,
    get_calendar_actor_class_for_role,
)
from app.services.calendar_sync_service import enqueue_appointment_sync
from app.services.console_auth import (
    ConsoleAuthContext,
    get_console_context,
    has_console_permission,
    require_console_permission,
)
from app.services.console_errors import ConsoleAPIError
from app.services.google_calendar_service import GoogleCalendarService
from app.services.handover_owner_service import manager_reopen as state_manager_reopen
from app.services.onboarding_state import OnboardingStep, ensure_onboarding_step

logger = get_logger(__name__)

router = APIRouter(prefix="/calendar", tags=["Calendar"])

_DEFAULT_NO_SHOW_FOLLOW_UP_WINDOW = timedelta(hours=2)

def _resolve_calendar_branch(context: ConsoleAuthContext) -> UUID:
    if context.effective_branch_id:
        return context.effective_branch_id
    if len(context.branches) == 1:
        return context.branches[0].id
    raise ConsoleAPIError(400, "BRANCH_SELECTION_REQUIRED", "Branch selection required")


# ==================== Schemas ====================

class SlotResponse(BaseModel):
    start: str
    end: str
    start_time: str
    end_time: str
    available: bool


class SlotsResponse(BaseModel):
    date: str
    specialist_id: str
    specialist_name: str
    duration_minutes: int
    slots: List[SlotResponse]


class SpecialistResponse(BaseModel):
    id: str
    name: str
    branch_id: Optional[str] = None
    branch_name: Optional[str] = None
    services: List[dict] = Field(default_factory=list)
    is_active: bool


class SpecialistsResponse(BaseModel):
    items: List[SpecialistResponse]


class SpecialistServicePayload(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    duration_min: Optional[int] = Field(default=None, ge=5, le=480)
    price: Optional[int] = Field(default=None, ge=0)


class SpecialistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    branch_id: Optional[str] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    google_calendar_id: Optional[str] = Field(default=None, max_length=255)
    services: List[SpecialistServicePayload] = Field(default_factory=list)
    working_hours: Optional[dict[str, dict[str, str]]] = None
    is_active: bool = True


class SpecialistUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    branch_id: Optional[str] = None
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    google_calendar_id: Optional[str] = Field(default=None, max_length=255)
    services: Optional[List[SpecialistServicePayload]] = None
    working_hours: Optional[dict[str, dict[str, str]]] = None
    is_active: Optional[bool] = None


class BookingCreate(BaseModel):
    specialist_id: str
    start_at: datetime
    end_at: datetime
    customer_name: str = Field(min_length=1, max_length=255)
    customer_phone: str = Field(min_length=7, max_length=32)
    service_type: str = Field(min_length=1, max_length=255)
    notes: Optional[str] = None
    conversation_id: Optional[str] = None
    case_id: Optional[str] = None


class BookingUpdate(BaseModel):
    specialist_id: str
    start_at: datetime
    end_at: datetime
    customer_name: str = Field(min_length=1, max_length=255)
    customer_phone: str = Field(min_length=7, max_length=32)
    service_type: str = Field(min_length=1, max_length=255)
    notes: Optional[str] = None
    version: int = Field(ge=1)


class BookingCancelRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)
    version: int = Field(ge=1)


class BookingStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=3, max_length=32)
    reason: Optional[str] = Field(default=None, max_length=500)
    version: int = Field(ge=1)


class BookingNoShowFollowUpRequest(BaseModel):
    result: Literal["contacted", "rebooked"] = "contacted"
    rebooked_appointment_id: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=500)
    version: int = Field(ge=1)


class BookingFollowUpGovernanceRequest(BaseModel):
    owner_agent_id: Optional[str] = None
    due_at: Optional[datetime] = None
    version: int = Field(ge=1)


class BookingBlockedAction(BaseModel):
    action_id: CalendarBookingActionId
    reason_code: CalendarBookingBlockedReasonCode


class BookingResponse(BaseModel):
    id: str
    specialist_id: str
    specialist_name: str
    start_at: str
    end_at: str
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    service_type: Optional[str] = None
    notes: Optional[str] = None
    status: str
    no_show_followup_done: bool = False
    no_show_followup_result: Optional[str] = None
    no_show_followup_closed_at: Optional[str] = None
    no_show_followup_closed_by: Optional[str] = None
    no_show_followup_rebooked_appointment_id: Optional[str] = None
    follow_up_owner_id: Optional[str] = None
    follow_up_owner_name: Optional[str] = None
    follow_up_due_at: Optional[str] = None
    follow_up_overdue: bool = False
    google_event_id: Optional[str] = None
    conversation_id: Optional[str] = None
    case_id: Optional[str] = None
    needs_action: bool = False
    attention_reason: Optional[str] = None
    version: int = 1
    allowed_actions: List[CalendarBookingActionId] = Field(default_factory=list)
    blocked_actions: List[BookingBlockedAction] = Field(default_factory=list)
    last_actor_type: Optional[str] = None
    created_at: str


class BookingsListResponse(BaseModel):
    items: List[BookingResponse]
    cursor: Optional[str] = None
    has_more: bool = False


class BookingCaseEffect(BaseModel):
    case_id: str
    action: Literal["reopened_for_booking_attention", "linked_rebooked_booking"]
    message: str


class BookingActionResponse(BaseModel):
    success: bool
    booking: BookingResponse
    case_effects: List[BookingCaseEffect] = Field(default_factory=list)


CalendarOperatorEventType = Literal[
    "filter_apply",
    "filter_reset",
    "double_submit_blocked",
]
CalendarOperatorEventActionId = Literal[
    "apply_filters",
    "reset_filters",
    "create_booking",
    "edit_booking",
    "reschedule_booking",
    "cancel_booking",
    "mark_completed",
    "mark_no_show",
    "record_follow_up_contacted",
    "record_follow_up_rebooked",
    "manage_follow_up_governance",
]
CalendarOperatorEventSurface = Literal[
    "filter_panel",
    "booking_panel",
    "follow_up_panel",
    "follow_up_governance",
    "composer",
]


class CalendarOperatorEventRequest(BaseModel):
    event_type: CalendarOperatorEventType
    action_id: CalendarOperatorEventActionId
    surface: CalendarOperatorEventSurface
    booking_id: Optional[str] = None


class CalendarOperatorEventResponse(BaseModel):
    success: bool


# ==================== Specialists ====================

def _parse_uuid(raw_value: str, *, field_name: str) -> UUID:
    try:
        return UUID(raw_value)
    except ValueError as exc:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is invalid") from exc


def _normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_required_text(value: str, *, field_name: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is required")
    return cleaned


def _normalize_operator_grade_text(
    value: str,
    *,
    field_name: str,
    min_length: int = 2,
) -> str:
    cleaned = _normalize_required_text(value, field_name=field_name)
    if len(cleaned) < min_length:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is too short")
    return cleaned


def _normalize_calendar_customer_phone(
    value: str,
    *,
    field_name: str = "customer_phone",
) -> str:
    cleaned = _normalize_required_text(value, field_name=field_name)
    if not re.fullmatch(r"[+\d\s().-]+", cleaned):
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is invalid")
    digits = re.sub(r"\D+", "", cleaned)
    if len(digits) == 10:
        if cleaned.startswith("+") or re.match(r"^7(?:[\s().-]|$)", cleaned) or re.match(r"^8(?:[\s().-]|$)", cleaned):
            raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is invalid")
        digits = f"7{digits}"
    elif len(digits) == 11 and digits[0] in {"7", "8"}:
        digits = f"7{digits[-10:]}"
    else:
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is invalid")
    if len(digits) != 11 or not digits.startswith("7"):
        raise ConsoleAPIError(400, "INVALID_PARAM", f"{field_name} is invalid")
    return f"+{digits}"


def _parse_booking_cursor(cursor: Optional[str]) -> tuple[datetime, Optional[UUID]] | None:
    if not cursor:
        return None
    cursor_value = cursor.strip()
    if not cursor_value:
        return None
    raw_time, raw_id = cursor_value, None
    if "|" in cursor_value:
        raw_time, raw_id = cursor_value.split("|", 1)
    try:
        cursor_time = datetime.fromisoformat(raw_time)
    except ValueError as exc:
        raise ConsoleAPIError(400, "INVALID_PARAM", "cursor is invalid") from exc
    if cursor_time.tzinfo is None:
        cursor_time = cursor_time.replace(tzinfo=timezone.utc)
    cursor_id = None
    if raw_id:
        cursor_id = _parse_uuid(raw_id, field_name="cursor")
    return cursor_time, cursor_id


def _encode_booking_cursor(booking: Appointment) -> str:
    return f"{booking.start_at.isoformat()}|{booking.id}"


def _normalize_status_filters(status: Optional[str]) -> tuple[Optional[str], Optional[list[str]]]:
    if not status:
        return None, None
    status_norm = status.lower().strip()
    single_status_map = {
        "pending": "PENDING_CONFIRMATION",
        "confirmed": "CONFIRMED",
        "cancelled": "CANCELLED",
        "completed": "COMPLETED",
        "no_show": "NO_SHOW",
        "draft": "DRAFT",
        "hold": "HOLD",
        "checked_in": "CHECKED_IN",
        "reschedule_requested": "RESCHEDULE_REQUESTED",
    }
    if status_norm == "scheduled":
        return None, ["DRAFT", "HOLD", "PENDING_CONFIRMATION", "CONFIRMED", "CHECKED_IN", "RESCHEDULE_REQUESTED"]
    resolved_status = single_status_map.get(status_norm, status.upper())
    return resolved_status, None


def _booking_attention_reason(status: str, *, followup_done: bool) -> Optional[str]:
    normalized = status.upper()
    if normalized == "PENDING_CONFIRMATION":
        return "Нужно подтвердить визит"
    if normalized == "RESCHEDULE_REQUESTED":
        return "Клиент просит перенос"
    if normalized == "HOLD":
        return "Нужно решение менеджера"
    if normalized == "NO_SHOW" and not followup_done:
        return "Связаться после неявки"
    return None


def _booking_needs_action(status: str, *, followup_done: bool) -> bool:
    return _booking_attention_reason(status, followup_done=followup_done) is not None


def _normalize_services_payload(
    services: Optional[List[SpecialistServicePayload]],
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for service in services or []:
        service_name = _normalize_required_text(service.name, field_name="services.name")
        item: dict[str, Any] = {"name": service_name}
        if service.duration_min is not None:
            item["duration_min"] = int(service.duration_min)
        if service.price is not None:
            item["price"] = int(service.price)
        normalized.append(item)
    return normalized


def _serialize_specialist(specialist: Specialist, service: SchedulingService) -> SpecialistResponse:
    return SpecialistResponse(
        id=str(specialist.id),
        name=specialist.name,
        branch_id=str(specialist.branch_id) if specialist.branch_id else None,
        branch_name=specialist.branch.name if specialist.branch else None,
        services=service.get_specialist_services(specialist),
        is_active=specialist.is_active,
    )


def _resolve_specialist_branch(
    context: ConsoleAuthContext,
    db: Session,
    branch_id: Optional[str],
) -> Branch:
    target_branch_id = _resolve_calendar_branch(context) if branch_id is None else _parse_uuid(
        branch_id,
        field_name="branch_id",
    )
    if context.branch_restricted and target_branch_id not in context.allowed_branch_ids:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this branch denied")
    branch = db.query(Branch).filter(
        Branch.id == target_branch_id,
        Branch.client_id == context.client.id,
    ).first()
    if not branch:
        raise ConsoleAPIError(404, "BRANCH_NOT_FOUND", "Branch not found")
    return branch


def _resolve_specialist(
    context: ConsoleAuthContext,
    db: Session,
    specialist_id: str,
) -> Specialist:
    specialist_uuid = _parse_uuid(specialist_id, field_name="specialist_id")
    specialist = db.query(Specialist).filter(
        Specialist.id == specialist_uuid,
        Specialist.client_id == context.client.id,
    ).first()
    if not specialist:
        raise ConsoleAPIError(404, "SPECIALIST_NOT_FOUND", "Specialist not found")
    if specialist.branch_id is None:
        raise ConsoleAPIError(400, "BRANCH_REQUIRED", "Specialist branch is required")
    if context.branch_restricted and specialist.branch_id not in context.allowed_branch_ids:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this branch denied")
    return specialist


def _set_specialist_active(*, specialist: Specialist, is_active: bool) -> None:
    specialist.is_active = is_active
    specialist.updated_at = datetime.now(timezone.utc)


def _resolve_booking_for_context(
    context: ConsoleAuthContext,
    db: Session,
    booking_id: UUID,
    *,
    for_update: bool = False,
) -> Appointment:
    query = db.query(Appointment).filter(
        Appointment.id == booking_id,
        Appointment.client_id == context.client.id,
    )
    if for_update and hasattr(query, "with_for_update"):
        query = query.with_for_update()
    booking = query.first()
    if not booking:
        raise ConsoleAPIError(404, "BOOKING_NOT_FOUND", "Booking not found")
    if context.branch_restricted and booking.branch_id not in context.allowed_branch_ids:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this branch denied")
    return booking


def _serialize_no_show_followup_state(audit_row: Optional[AppointmentAudit]) -> dict[str, Any]:
    if not audit_row:
        return {
            "done": False,
            "result": None,
            "closed_at": None,
            "closed_by": None,
            "rebooked_appointment_id": None,
        }
    payload = audit_row.payload if isinstance(audit_row.payload, dict) else {}
    closed_at = payload.get("follow_up_closed_at")
    if not closed_at and audit_row.created_at:
        closed_at = audit_row.created_at.isoformat()
    closed_by = payload.get("follow_up_closed_by")
    if not closed_by and audit_row.actor_id:
        closed_by = str(audit_row.actor_id)
    result = payload.get("result") or "contacted"
    rebooked_appointment_id = payload.get("rebooked_appointment_id")
    return {
        "done": True,
        "result": result,
        "closed_at": closed_at,
        "closed_by": closed_by,
        "rebooked_appointment_id": rebooked_appointment_id,
    }


def _serialize_booking_blocked_actions(
    blocked_actions: list[CalendarBlockedActionPayload],
) -> list[BookingBlockedAction]:
    blocked_map = {
        payload["action_id"]: BookingBlockedAction(
            action_id=payload["action_id"],
            reason_code=payload["reason_code"],
        )
        for payload in blocked_actions
    }
    return [
        blocked_map[action_id]
        for action_id in BOOKING_ACTION_ORDER
        if action_id in blocked_map
    ]


def _latest_actor_type_for_booking(db: Session, booking_id: UUID) -> Optional[str]:
    latest_audit = (
        db.query(AppointmentAudit)
        .filter(AppointmentAudit.appointment_id == booking_id)
        .order_by(AppointmentAudit.created_at.desc())
        .first()
    )
    actor_type = getattr(latest_audit, "actor_type", None)
    return actor_type or None


def _latest_actor_type_by_appointment(
    db: Session,
    appointment_ids: list[UUID],
) -> dict[UUID, Optional[str]]:
    latest_actor_type_map: dict[UUID, Optional[str]] = {}
    if not appointment_ids:
        return latest_actor_type_map
    rows = (
        db.query(AppointmentAudit)
        .filter(AppointmentAudit.appointment_id.in_(appointment_ids))
        .order_by(
            AppointmentAudit.appointment_id.asc(),
            AppointmentAudit.created_at.desc(),
        )
        .all()
    )
    for row in rows:
        appointment_id = getattr(row, "appointment_id", None)
        if not appointment_id or appointment_id in latest_actor_type_map:
            continue
        latest_actor_type_map[appointment_id] = getattr(row, "actor_type", None) or None
    return latest_actor_type_map


def _build_booking_action_fields(
    *,
    context: ConsoleAuthContext,
    booking: Appointment,
    no_show_followup_done: bool,
    case_id: Optional[str],
) -> tuple[list[CalendarBookingActionId], list[BookingBlockedAction]]:
    contract = build_calendar_booking_action_contract(
        role=context.role,
        status=booking.status,
        no_show_followup_done=no_show_followup_done,
        case_id=case_id,
    )
    return contract["allowed_actions"], _serialize_booking_blocked_actions(contract["blocked_actions"])


def _enrich_booking_response_for_context(
    *,
    context: ConsoleAuthContext,
    booking: Appointment,
    booking_response: BookingResponse,
    no_show_followup_done: bool,
    case_id: Optional[str],
    last_actor_type: Optional[str],
) -> BookingResponse:
    allowed_actions, blocked_actions = _build_booking_action_fields(
        context=context,
        booking=booking,
        no_show_followup_done=no_show_followup_done,
        case_id=case_id,
    )
    return booking_response.model_copy(
        update={
            "version": int(getattr(booking, "version", 1) or 1),
            "allowed_actions": allowed_actions,
            "blocked_actions": blocked_actions,
            "last_actor_type": last_actor_type,
            "case_id": case_id,
        }
    )


def _build_booking_response_for_context(
    *,
    db: Session,
    context: ConsoleAuthContext,
    booking: Appointment,
) -> BookingResponse:
    booking_response = _build_booking_response(db, booking)
    return _enrich_booking_response_for_context(
        context=context,
        booking=booking,
        booking_response=booking_response,
        no_show_followup_done=booking_response.no_show_followup_done,
        case_id=booking_response.case_id,
        last_actor_type=booking_response.last_actor_type,
    )


def _raise_booking_version_conflict(
    *,
    expected_version: int,
    current_version: int,
    db: Optional[Session] = None,
    context: Optional[ConsoleAuthContext] = None,
    action_id: Optional[str] = None,
    booking: Optional[Appointment] = None,
) -> None:
    if db is not None and context is not None and action_id:
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id=action_id,
            outcome="version_conflict",
            booking=booking,
            old_status=getattr(booking, "status", None),
            new_status=getattr(booking, "status", None),
            blocked_reason_code="version_conflict",
            version_conflict=True,
            linked_case_id=str(getattr(booking, "case_id", "")) or None,
            payload={
                "expected_version": expected_version,
                "current_version": current_version,
            },
        )
        _commit_if_supported(db)
    raise ConsoleAPIError(
        409,
        "BOOKING_VERSION_CONFLICT",
        "Booking was changed by another action. Refresh the card and try again.",
        details={
            "expected_version": expected_version,
            "current_version": current_version,
        },
    )


def _assert_booking_version(
    *,
    booking: Appointment,
    expected_version: int,
    db: Optional[Session] = None,
    context: Optional[ConsoleAuthContext] = None,
    action_id: Optional[str] = None,
) -> int:
    current_version = int(getattr(booking, "version", 1) or 1)
    if expected_version != current_version:
        _raise_booking_version_conflict(
            expected_version=expected_version,
            current_version=current_version,
            db=db,
            context=context,
            action_id=action_id,
            booking=booking,
        )
    return current_version


def _record_booking_router_mutation(
    *,
    db: Session,
    booking: Appointment,
    context: ConsoleAuthContext,
    action: str,
    payload: Optional[dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> int:
    resolved_now = now or datetime.now(timezone.utc)
    prev_version = int(getattr(booking, "version", 1) or 1)
    booking.version = prev_version + 1
    booking.updated_at = resolved_now
    db.add(booking)
    db.add(
        AppointmentAudit(
            appointment_id=booking.id,
            actor_type="agent",
            actor_id=context.agent.id,
            channel="console",
            action=action,
            prev_status=booking.status,
            new_status=booking.status,
            prev_version=prev_version,
            new_version=booking.version,
            payload=payload or {},
            correlation_id=str(booking.conversation_id) if getattr(booking, "conversation_id", None) else None,
        )
    )
    return int(booking.version or prev_version + 1)


def _calendar_client_slug(context: ConsoleAuthContext) -> str | None:
    return getattr(getattr(context, "client", None), "slug", None)


def _calendar_branch_id(context: ConsoleAuthContext, booking: Optional[Appointment] = None) -> Optional[UUID]:
    booking_branch_id = getattr(booking, "branch_id", None) if booking is not None else None
    return (
        booking_branch_id
        or getattr(context, "effective_branch_id", None)
        or getattr(context, "selected_branch_id", None)
        or getattr(getattr(context, "agent", None), "branch_id", None)
    )


def _commit_if_supported(db: Session) -> None:
    commit = getattr(db, "commit", None)
    if callable(commit):
        commit()


def _can_record_audit_event(db: Session) -> bool:
    return callable(getattr(db, "add", None))


def _record_calendar_action_observation(
    *,
    db: Session,
    context: ConsoleAuthContext,
    action_id: str,
    outcome: Literal["applied", "denied", "version_conflict", "invalid"],
    booking: Optional[Appointment],
    old_status: Optional[str],
    new_status: Optional[str],
    blocked_reason_code: Optional[str] = None,
    version_conflict: bool = False,
    linked_case_id: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
) -> None:
    actor_class = get_calendar_actor_class_for_role(getattr(context, "role", None))
    normalized_old_status = (old_status or "").strip().upper() or None
    normalized_new_status = (new_status or "").strip().upper() or None
    normalized_reason_code = (blocked_reason_code or "").strip() or None
    if _can_record_audit_event(db):
        record_audit_event(
            db,
            actor=context.agent,
            event_type=f"calendar_booking_action_{outcome}",
            entity_type="appointment",
            entity_id=getattr(booking, "id", None),
            payload={
                "action_id": action_id,
                "actor_class": actor_class,
                "booking_id": str(getattr(booking, "id", "")) or None,
                "old_status": normalized_old_status,
                "new_status": normalized_new_status,
                "blocked_reason_code": normalized_reason_code,
                "version_conflict": version_conflict,
                "linked_case_id": linked_case_id,
                **(payload or {}),
            },
            client_id=context.client.id,
            branch_id=_calendar_branch_id(context, booking),
        )

    client_slug = _calendar_client_slug(context)
    if outcome == "denied" and normalized_reason_code:
        record_calendar_booking_action_denied(
            client_slug,
            action_id=action_id,
            actor_class=actor_class,
            status=normalized_old_status,
            reason_code=normalized_reason_code,
        )
    elif outcome == "version_conflict":
        record_calendar_booking_version_conflict(
            client_slug,
            action_id=action_id,
            actor_class=actor_class,
        )
    elif outcome == "invalid" and normalized_reason_code:
        record_calendar_followup_invalid(
            client_slug,
            action_id=action_id,
            actor_class=actor_class,
            reason_code=normalized_reason_code,
        )


def _record_calendar_operator_event_observation(
    *,
    db: Session,
    context: ConsoleAuthContext,
    event_type: CalendarOperatorEventType,
    action_id: CalendarOperatorEventActionId,
    surface: CalendarOperatorEventSurface,
    booking_id: Optional[str] = None,
) -> None:
    actor_class = get_calendar_actor_class_for_role(getattr(context, "role", None))
    client_slug = _calendar_client_slug(context)
    if event_type == "filter_apply":
        record_calendar_filter_apply(client_slug, actor_class=actor_class)
    elif event_type == "filter_reset":
        record_calendar_filter_reset(client_slug, actor_class=actor_class)
    elif event_type == "double_submit_blocked":
        record_calendar_booking_double_submit_blocked(
            client_slug,
            action_id=action_id,
            actor_class=actor_class,
            surface=surface,
        )
    if _can_record_audit_event(db):
        record_audit_event(
            db,
            actor=context.agent,
            event_type=f"calendar_operator_{event_type}",
            entity_type="appointment" if booking_id else "calendar_queue",
            entity_id=_parse_uuid(booking_id, field_name="booking_id") if booking_id else None,
            payload={
                "action_id": action_id,
                "actor_class": actor_class,
                "surface": surface,
                "booking_id": booking_id,
            },
            client_id=context.client.id,
            branch_id=_calendar_branch_id(context),
        )


def _can_manage_follow_up_governance(context: ConsoleAuthContext) -> bool:
    return has_console_permission(context.role, "team", "write")


def _require_follow_up_governance_permission(context: ConsoleAuthContext) -> None:
    if _can_manage_follow_up_governance(context):
        return
    raise ConsoleAPIError(403, "ACCESS_DENIED", "Only owner/admin can manage booking follow-up ownership")


def _normalize_follow_up_due_at(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _resolve_follow_up_owner_agent(
    *,
    context: ConsoleAuthContext,
    db: Session,
    owner_agent_id: UUID,
) -> Agent:
    agent = (
        db.query(Agent)
        .filter(
            Agent.id == owner_agent_id,
            Agent.client_id == context.client.id,
            Agent.is_active.is_(True),
        )
        .first()
    )
    if not agent:
        raise ConsoleAPIError(404, "AGENT_NOT_FOUND", "Follow-up owner not found")
    if agent.branch_id and context.allowed_branch_ids and agent.branch_id not in context.allowed_branch_ids:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this agent branch denied")
    if not has_console_permission(agent.role, "calendar", "write"):
        raise ConsoleAPIError(400, "INVALID_PARAM", "owner_agent_id is not eligible for booking follow-up")
    return agent


def _booking_follow_up_overdue(
    *,
    booking: Appointment,
    followup_done: bool,
    now: Optional[datetime] = None,
) -> bool:
    follow_up_due_at = getattr(booking, "follow_up_due_at", None)
    if (booking.status or "").upper() != "NO_SHOW" or followup_done or not follow_up_due_at:
        return False
    resolved_now = now or datetime.now(timezone.utc)
    return follow_up_due_at < resolved_now


_CASE_SNOOZE_META_KEYS = (
    "snoozed_until",
    "snoozed_at",
    "snooze_reason",
    "snoozed_by_id",
    "snoozed_by_name",
)


def _clear_case_snooze_meta(handover: Handover) -> None:
    raw_meta = getattr(handover, "meta", None)
    if not isinstance(raw_meta, dict):
        return
    meta = dict(raw_meta)
    changed = False
    for key in _CASE_SNOOZE_META_KEYS:
        if key in meta:
            meta.pop(key, None)
            changed = True
    if changed:
        handover.meta = meta


def _resolve_booking_case_context(
    db: Session,
    *,
    client_id: UUID,
    case_id: UUID | None,
    lock: bool = False,
) -> tuple[Optional[Handover], Optional[Conversation]]:
    if case_id is None:
        return None, None

    case_query = db.query(Handover).filter(
        Handover.id == case_id,
        Handover.client_id == client_id,
    )
    if lock:
        case_query = case_query.with_for_update()
    handover = case_query.first()
    if handover is None:
        return None, None

    conversation_query = db.query(Conversation).filter(Conversation.id == handover.conversation_id)
    if lock:
        conversation_query = conversation_query.with_for_update()
    conversation = conversation_query.first()
    return handover, conversation


def _maybe_reopen_linked_case_for_booking_attention(
    *,
    db: Session,
    context: ConsoleAuthContext,
    booking: Appointment,
) -> list[BookingCaseEffect]:
    handover, conversation = _resolve_booking_case_context(
        db,
        client_id=context.client.id,
        case_id=booking.case_id,
        lock=True,
    )
    if handover is None or conversation is None:
        return []
    if handover.status != "resolved":
        return []

    manager_name = context.agent.name or "Менеджер"
    _clear_case_snooze_meta(handover)
    result = state_manager_reopen(
        db,
        conversation,
        handover,
        manager_id=str(context.agent.id),
        manager_name=manager_name,
    )
    if not result.ok:
        logger.warning(
            "Booking attention could not reopen linked case",
            extra={
                "context": {
                    "booking_id": str(booking.id),
                    "case_id": str(handover.id),
                    "reason": result.error,
                }
            },
        )
        return []

    record_audit_event(
        db,
        actor=context.agent,
        event_type="case_reopened_from_booking_attention",
        entity_type="handover",
        entity_id=handover.id,
        payload={
            "booking_id": str(booking.id),
            "booking_status": booking.status,
            "source": "calendar_booking_status",
        },
        branch_id=conversation.branch_id,
    )
    return [
        BookingCaseEffect(
            case_id=str(handover.id),
            action="reopened_for_booking_attention",
            message="Неявка требует follow-up: заявка возвращена в работу.",
        )
    ]


def _validate_or_link_rebooked_booking_case(
    *,
    db: Session,
    context: ConsoleAuthContext,
    source_booking: Appointment,
    rebooked_booking: Appointment,
) -> tuple[list[BookingCaseEffect], bool]:
    source_case_id = getattr(source_booking, "case_id", None)
    source_conversation_id = getattr(source_booking, "conversation_id", None)
    if source_case_id is None and source_conversation_id is None:
        return [], False

    rebooked_case_id = getattr(rebooked_booking, "case_id", None)
    rebooked_conversation_id = getattr(rebooked_booking, "conversation_id", None)

    if source_case_id and rebooked_case_id and rebooked_case_id != source_case_id:
        raise ConsoleAPIError(
            409,
            "REBOOKED_BOOKING_CASE_CONFLICT",
            "Rebooked booking is already linked to another case",
        )
    if (
        source_conversation_id
        and rebooked_conversation_id
        and rebooked_conversation_id != source_conversation_id
    ):
        raise ConsoleAPIError(
            409,
            "REBOOKED_BOOKING_CONVERSATION_CONFLICT",
            "Rebooked booking is already linked to another conversation",
        )

    changed = False
    if source_case_id and rebooked_case_id is None:
        rebooked_booking.case_id = source_case_id
        changed = True
    if source_conversation_id and rebooked_conversation_id is None:
        rebooked_booking.conversation_id = source_conversation_id
        changed = True
    if not changed:
        return [], False

    _record_booking_router_mutation(
        db=db,
        booking=rebooked_booking,
        context=context,
        action="case_link_update",
        payload={
            "source_booking_id": str(source_booking.id),
            "case_id": str(source_case_id) if source_case_id else None,
            "conversation_id": str(source_conversation_id) if source_conversation_id else None,
        },
    )

    record_audit_event(
        db,
        actor=context.agent,
        event_type="rebooked_booking_linked_to_case",
        entity_type="appointment",
        entity_id=rebooked_booking.id,
        payload={
            "source_booking_id": str(source_booking.id),
            "case_id": str(source_case_id) if source_case_id else None,
            "conversation_id": str(source_conversation_id) if source_conversation_id else None,
        },
        branch_id=getattr(rebooked_booking, "branch_id", None),
    )
    if source_case_id is None:
        return [], True
    return ([
        BookingCaseEffect(
            case_id=str(source_case_id),
            action="linked_rebooked_booking",
            message="Новая запись привязана к этой заявке.",
        )
    ], True)


def _latest_case_ids_by_conversation(
    db: Session,
    *,
    client_id: UUID,
    conversation_ids: set[UUID],
) -> dict[UUID, UUID]:
    if not conversation_ids:
        return {}

    rows = (
        db.query(Handover)
        .filter(
            Handover.client_id == client_id,
            Handover.conversation_id.in_(conversation_ids),
        )
        .order_by(Handover.conversation_id.asc(), Handover.created_at.desc())
        .all()
    )
    mapping: dict[UUID, UUID] = {}
    for row in rows:
        if not row.conversation_id:
            continue
        if row.conversation_id in mapping:
            continue
        mapping[row.conversation_id] = row.id
    return mapping


def _build_booking_response(db: Session, booking: Appointment) -> BookingResponse:
    specialist = None
    if booking.specialist_id:
        specialist = db.query(Specialist).filter(Specialist.id == booking.specialist_id).first()
    follow_up_owner_id = getattr(booking, "follow_up_owner_id", None)
    follow_up_due_at = getattr(booking, "follow_up_due_at", None)
    follow_up_owner_name = None
    if follow_up_owner_id:
        follow_up_owner_name = (
            db.query(Agent.name)
            .filter(Agent.id == follow_up_owner_id)
            .scalar()
        )
    service_name = (
        db.query(AppointmentServiceModel.service_name)
        .filter(AppointmentServiceModel.appointment_id == booking.id)
        .scalar()
    )
    google_event_id = (
        db.query(AppointmentSyncState.external_id)
        .filter(
            AppointmentSyncState.appointment_id == booking.id,
            AppointmentSyncState.provider == "google_calendar",
        )
        .scalar()
    )
    no_show_followup_audit = (
        db.query(AppointmentAudit)
        .filter(
            AppointmentAudit.appointment_id == booking.id,
            AppointmentAudit.action == "no_show_followup",
        )
        .order_by(AppointmentAudit.created_at.desc())
        .first()
    )
    no_show_followup_state = _serialize_no_show_followup_state(no_show_followup_audit)
    case_id = str(booking.case_id) if booking.case_id else None
    if not case_id and booking.conversation_id:
        latest_case = (
            db.query(Handover)
            .filter(
                Handover.client_id == booking.client_id,
                Handover.conversation_id == booking.conversation_id,
            )
            .order_by(Handover.created_at.desc())
            .first()
        )
        if latest_case:
            case_id = str(latest_case.id)
    attention_reason = _booking_attention_reason(
        booking.status,
        followup_done=bool(no_show_followup_state["done"]),
    )
    follow_up_overdue = _booking_follow_up_overdue(
        booking=booking,
        followup_done=bool(no_show_followup_state["done"]),
    )
    last_actor_type = _latest_actor_type_for_booking(db, booking.id)
    return BookingResponse(
        id=str(booking.id),
        specialist_id=str(booking.specialist_id),
        specialist_name=specialist.name if specialist else "Unknown",
        start_at=booking.start_at.isoformat(),
        end_at=booking.end_at.isoformat(),
        customer_name=booking.customer_name,
        customer_phone=booking.customer_phone,
        service_type=service_name,
        notes=booking.notes,
        status=booking.status,
        no_show_followup_done=no_show_followup_state["done"],
        no_show_followup_result=no_show_followup_state["result"],
        no_show_followup_closed_at=no_show_followup_state["closed_at"],
        no_show_followup_closed_by=no_show_followup_state["closed_by"],
        no_show_followup_rebooked_appointment_id=no_show_followup_state["rebooked_appointment_id"],
        follow_up_owner_id=str(follow_up_owner_id) if follow_up_owner_id else None,
        follow_up_owner_name=follow_up_owner_name,
        follow_up_due_at=follow_up_due_at.isoformat() if follow_up_due_at else None,
        follow_up_overdue=follow_up_overdue,
        google_event_id=google_event_id,
        conversation_id=str(booking.conversation_id) if booking.conversation_id else None,
        case_id=case_id,
        needs_action=_booking_needs_action(
            booking.status,
            followup_done=bool(no_show_followup_state["done"]),
        ),
        attention_reason=attention_reason,
        version=int(getattr(booking, "version", 1) or 1),
        last_actor_type=last_actor_type,
        created_at=booking.created_at.isoformat(),
    )


@router.get("/specialists", response_model=SpecialistsResponse)
async def list_specialists(
    request: Request,
    branch_id: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Get all specialists for the client."""
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "read")

    query = db.query(Specialist).filter(Specialist.client_id == context.client.id)
    if not include_inactive:
        query = query.filter(Specialist.is_active.is_(True))

    if branch_id:
        requested_branch = _parse_uuid(branch_id, field_name="branch_id")
        if requested_branch not in context.allowed_branch_ids:
            raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this branch denied")
        query = query.filter(Specialist.branch_id == requested_branch)
    elif context.branch_restricted:
        query = query.filter(Specialist.branch_id.in_(context.allowed_branch_ids))

    specialists = query.order_by(Specialist.name).all()
    service = SchedulingService(db)
    return SpecialistsResponse(items=[_serialize_specialist(s, service) for s in specialists])


@router.post("/specialists", response_model=SpecialistResponse)
async def create_specialist(
    request: Request,
    data: SpecialistCreate,
    db: Session = Depends(get_db),
):
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "team",
        "write",
        message="Only owner/admin can manage specialists",
    )
    branch = _resolve_specialist_branch(context, db, data.branch_id)
    ensure_onboarding_step(db, branch, OnboardingStep.BOOKING)

    now = datetime.now(timezone.utc)
    specialist = Specialist(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=branch.id,
        name=_normalize_required_text(data.name, field_name="name"),
        phone=_normalize_optional_text(data.phone),
        email=_normalize_optional_text(data.email),
        google_calendar_id=_normalize_optional_text(data.google_calendar_id),
        services=_normalize_services_payload(data.services),
        working_hours=data.working_hours or {},
        is_active=bool(data.is_active),
        created_at=now,
        updated_at=now,
    )
    db.add(specialist)
    db.commit()
    db.refresh(specialist)
    service = SchedulingService(db)
    return _serialize_specialist(specialist, service)


@router.patch("/specialists/{specialist_id}", response_model=SpecialistResponse)
async def update_specialist(
    specialist_id: str,
    request: Request,
    data: SpecialistUpdate,
    db: Session = Depends(get_db),
):
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "team",
        "write",
        message="Only owner/admin can manage specialists",
    )
    specialist = _resolve_specialist(context, db, specialist_id)

    if "branch_id" in data.model_fields_set:
        if data.branch_id is None:
            raise ConsoleAPIError(400, "INVALID_PARAM", "branch_id is required")
        target_branch = _resolve_specialist_branch(context, db, data.branch_id)
    else:
        target_branch = specialist.branch
        if not target_branch:
            target_branch = db.query(Branch).filter(
                Branch.id == specialist.branch_id,
                Branch.client_id == context.client.id,
            ).first()
        if not target_branch:
            raise ConsoleAPIError(404, "BRANCH_NOT_FOUND", "Branch not found")
    ensure_onboarding_step(db, target_branch, OnboardingStep.BOOKING)

    if "name" in data.model_fields_set:
        if data.name is None:
            raise ConsoleAPIError(400, "INVALID_PARAM", "name is required")
        specialist.name = _normalize_required_text(data.name, field_name="name")
    if "branch_id" in data.model_fields_set:
        specialist.branch_id = target_branch.id
    if "phone" in data.model_fields_set:
        specialist.phone = _normalize_optional_text(data.phone)
    if "email" in data.model_fields_set:
        specialist.email = _normalize_optional_text(data.email)
    if "google_calendar_id" in data.model_fields_set:
        specialist.google_calendar_id = _normalize_optional_text(data.google_calendar_id)
    if "services" in data.model_fields_set:
        specialist.services = _normalize_services_payload(data.services)
    if "working_hours" in data.model_fields_set:
        specialist.working_hours = data.working_hours or {}
    if "is_active" in data.model_fields_set:
        if data.is_active is None:
            raise ConsoleAPIError(400, "INVALID_PARAM", "is_active must be true or false")
        specialist.is_active = data.is_active
    specialist.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(specialist)
    service = SchedulingService(db)
    return _serialize_specialist(specialist, service)


@router.post("/specialists/{specialist_id}/enable", response_model=SpecialistResponse)
async def enable_specialist(
    specialist_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "team",
        "write",
        message="Only owner/admin can manage specialists",
    )
    specialist = _resolve_specialist(context, db, specialist_id)
    branch = specialist.branch or db.query(Branch).filter(Branch.id == specialist.branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "BRANCH_NOT_FOUND", "Branch not found")
    ensure_onboarding_step(db, branch, OnboardingStep.BOOKING)
    _set_specialist_active(specialist=specialist, is_active=True)
    db.commit()
    db.refresh(specialist)
    service = SchedulingService(db)
    return _serialize_specialist(specialist, service)


@router.post("/specialists/{specialist_id}/disable", response_model=SpecialistResponse)
async def disable_specialist(
    specialist_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "team",
        "write",
        message="Only owner/admin can manage specialists",
    )
    specialist = _resolve_specialist(context, db, specialist_id)
    branch = specialist.branch or db.query(Branch).filter(Branch.id == specialist.branch_id).first()
    if not branch:
        raise ConsoleAPIError(404, "BRANCH_NOT_FOUND", "Branch not found")
    ensure_onboarding_step(db, branch, OnboardingStep.BOOKING)
    _set_specialist_active(specialist=specialist, is_active=False)
    db.commit()
    db.refresh(specialist)
    service = SchedulingService(db)
    return _serialize_specialist(specialist, service)


# ==================== Slots ====================

@router.get("/slots", response_model=SlotsResponse)
async def get_slots(
    request: Request,
    specialist_id: UUID,
    date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    duration: int = Query(60, ge=15, le=240),
    db: Session = Depends(get_db)
):
    """
    Get available time slots for a specialist on a given date.
    Combines working hours, existing bookings, and Google Calendar.
    """
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "read")
    
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ConsoleAPIError(400, "INVALID_DATE", "Date format must be YYYY-MM-DD")
    
    specialist = db.query(Specialist).filter(
        Specialist.id == specialist_id,
        Specialist.client_id == context.client.id
    ).first()
    
    if not specialist:
        raise ConsoleAPIError(404, "SPECIALIST_NOT_FOUND", "Specialist not found")

    if specialist.branch_id is None:
        raise ConsoleAPIError(400, "BRANCH_REQUIRED", "Specialist branch is required")

    if context.branch_restricted and specialist.branch_id not in context.allowed_branch_ids:
        raise ConsoleAPIError(403, "ACCESS_DENIED", "Access to this branch denied")
    
    service = SchedulingService(db)
    
    try:
        branch_tz = specialist.branch.timezone if specialist.branch and specialist.branch.timezone else "Asia/Almaty"
        try:
            tz = ZoneInfo(branch_tz)
        except Exception:
            tz = ZoneInfo("Asia/Almaty")
        parsed_date = parsed_date.replace(tzinfo=tz)
        slots = service.get_available_slots(
            specialist_id=UUID(specialist_id),
            date=parsed_date,
            duration_minutes=duration,
            client_id=context.client.id,
        )
    except SpecialistNotFoundError:
        raise ConsoleAPIError(404, "SPECIALIST_NOT_FOUND", "Specialist not found")
    
    return SlotsResponse(
        date=date,
        specialist_id=specialist_id,
        specialist_name=specialist.name,
        duration_minutes=duration,
        slots=[
            SlotResponse(
                start=slot.start.isoformat(),
                end=slot.end.isoformat(),
                start_time=slot.start.strftime("%H:%M"),
                end_time=slot.end.strftime("%H:%M"),
                available=slot.available
            )
            for slot in slots
        ]
    )


# ==================== Bookings ====================

@router.post("/bookings", response_model=BookingActionResponse)
async def create_booking(
    request: Request,
    data: BookingCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new booking.
    
    Concurrency-safe: uses FOR UPDATE NOWAIT to prevent double-booking.
    """
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "write")
    specialist_uuid = _parse_uuid(data.specialist_id, field_name="specialist_id")

    # Verify specialist belongs to client
    specialist = db.query(Specialist).filter(
        Specialist.id == specialist_uuid,
        Specialist.client_id == context.client.id
    ).first()
    
    if not specialist:
        raise ConsoleAPIError(404, "SPECIALIST_NOT_FOUND", "Specialist not found")
    
    if specialist.branch_id is None:
        raise ConsoleAPIError(400, "BRANCH_REQUIRED", "Specialist branch is required")

    customer_name = _normalize_operator_grade_text(data.customer_name, field_name="customer_name")
    customer_phone = _normalize_calendar_customer_phone(data.customer_phone, field_name="customer_phone")
    service_type = _normalize_operator_grade_text(data.service_type, field_name="service_type")
    notes = _normalize_optional_text(data.notes)

    service = SchedulingService(db)
    conversation_uuid = _parse_uuid(data.conversation_id, field_name="conversation_id") if data.conversation_id else None
    case_uuid = _parse_uuid(data.case_id, field_name="case_id") if data.case_id else None
    if case_uuid:
        linked_case = (
            db.query(Handover)
            .filter(
                Handover.id == case_uuid,
                Handover.client_id == context.client.id,
            )
            .first()
        )
        if not linked_case:
            raise ConsoleAPIError(404, "CASE_NOT_FOUND", "Case not found")
        if conversation_uuid and linked_case.conversation_id != conversation_uuid:
            raise ConsoleAPIError(
                400,
                "INVALID_PARAM",
                "case_id does not belong to conversation_id",
            )
        conversation_uuid = linked_case.conversation_id
    elif conversation_uuid:
        latest_case = (
            db.query(Handover)
            .filter(
                Handover.client_id == context.client.id,
                Handover.conversation_id == conversation_uuid,
            )
            .order_by(Handover.created_at.desc())
            .first()
        )
        if latest_case:
            case_uuid = latest_case.id
    
    try:
        booking = service.create_appointment(
            client_id=context.client.id,
            branch_id=specialist.branch_id,
            specialist_id=specialist_uuid,
            start_at=data.start_at,
            end_at=data.end_at,
            customer_name=customer_name,
            customer_phone=customer_phone,
            service_type=service_type,
            notes=notes,
            created_by=context.agent.id,
            conversation_id=conversation_uuid,
            case_id=case_uuid,
        )

        if specialist.branch and isinstance(specialist.branch.booking_settings, dict):
            availability_provider = specialist.branch.booking_settings.get("availability_provider")
            if availability_provider == "google_calendar":
                enqueue_appointment_sync(
                    db,
                    appointment=booking,
                    action="create",
                    commit=True,
                )
        schedule_default_reminders(
            db,
            appointment=booking,
            commit=True,
        )
        
        logger.info(
            f"Booking created: {booking.id}",
            extra={"context": {
                "agent": context.agent.name,
                "specialist": specialist.name,
                "time": f"{data.start_at} - {data.end_at}"
            }}
        )
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id="create_booking",
            outcome="applied",
            booking=booking,
            old_status=None,
            new_status=getattr(booking, "status", None),
            linked_case_id=str(case_uuid) if case_uuid else None,
        )
        _commit_if_supported(db)
        
        return BookingActionResponse(
            success=True,
            booking=_build_booking_response_for_context(
                db=db,
                context=context,
                booking=booking,
            ),
        )
        
    except AppointmentConflictError as e:
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id="create_booking",
            outcome="denied",
            booking=None,
            old_status=None,
            new_status=None,
            blocked_reason_code="slot_conflict",
            linked_case_id=str(case_uuid) if case_uuid else None,
            payload={"reason": str(e)},
        )
        _commit_if_supported(db)
        raise ConsoleAPIError(
            409,
            "BOOKING_CONFLICT",
            "Выбранное время уже занято. Пожалуйста, выберите другой слот.",
            details={"reason": str(e)}
        )
    except SpecialistNotFoundError:
        raise ConsoleAPIError(404, "SPECIALIST_NOT_FOUND", "Specialist not found")


@router.get("/bookings", response_model=BookingsListResponse)
async def list_bookings(
    request: Request,
    specialist_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    case_id: Optional[str] = None,
    lane: Literal["attention", "all"] = "all",
    needs_action: Optional[bool] = None,
    follow_up_owner_id: Optional[str] = None,
    follow_up_overdue: Optional[bool] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get bookings with filters."""
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "read")
    resolved_limit = int(getattr(limit, "default", limit))
    
    service = SchedulingService(db)
    
    # Parse dates
    parsed_from = None
    parsed_to = None
    if date_from:
        parsed_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if date_to:
        parsed_to = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)

    status_filter, status_filters = _normalize_status_filters(status)

    specialist_uuid = _parse_uuid(specialist_id, field_name="specialist_id") if specialist_id else None
    conversation_uuid = _parse_uuid(conversation_id, field_name="conversation_id") if conversation_id else None
    case_uuid = _parse_uuid(case_id, field_name="case_id") if case_id else None
    follow_up_owner_uuid = _parse_uuid(follow_up_owner_id, field_name="follow_up_owner_id") if follow_up_owner_id else None
    cursor_payload = _parse_booking_cursor(cursor)
    cursor_start_at = cursor_payload[0] if cursor_payload else None
    cursor_id = cursor_payload[1] if cursor_payload else None
    
    bookings = service.get_appointments(
        client_id=context.client.id,
        specialist_id=specialist_uuid,
        branch_ids=list(context.allowed_branch_ids) if context.branch_restricted else None,
        conversation_id=conversation_uuid,
        case_id=case_uuid,
        date_from=parsed_from,
        date_to=parsed_to,
        status=status_filter,
        status_filters=status_filters,
        lane=lane,
        needs_action=needs_action,
        follow_up_owner_id=follow_up_owner_uuid,
        follow_up_overdue=follow_up_overdue,
        cursor_start_at=cursor_start_at,
        cursor_id=cursor_id,
        limit=resolved_limit + 1,
    )
    has_more = len(bookings) > resolved_limit
    if has_more:
        bookings = bookings[:resolved_limit]
        next_cursor = _encode_booking_cursor(bookings[-1])
    else:
        next_cursor = None
    
    appointment_ids = [b.id for b in bookings]
    specialist_ids = {b.specialist_id for b in bookings if b.specialist_id}
    follow_up_owner_ids = {
        getattr(booking, "follow_up_owner_id", None)
        for booking in bookings
        if getattr(booking, "follow_up_owner_id", None)
    }
    specialists_map = {
        s.id: s.name
        for s in db.query(Specialist).filter(Specialist.id.in_(specialist_ids)).all()
    }
    follow_up_owner_map = {
        agent.id: agent.name
        for agent in db.query(Agent).filter(Agent.id.in_(follow_up_owner_ids)).all()
    } if follow_up_owner_ids else {}

    services_map = {}
    if appointment_ids:
        rows = db.query(AppointmentServiceModel).filter(
            AppointmentServiceModel.appointment_id.in_(appointment_ids)
        ).all()
        for row in rows:
            services_map.setdefault(row.appointment_id, row.service_name)

    sync_map = {}
    if appointment_ids:
        rows = db.query(AppointmentSyncState).filter(
            AppointmentSyncState.appointment_id.in_(appointment_ids),
            AppointmentSyncState.provider == "google_calendar",
        ).all()
        for row in rows:
            sync_map[row.appointment_id] = row.external_id

    no_show_followup_map: dict[UUID, dict[str, Any]] = {}
    if appointment_ids:
        rows = (
            db.query(AppointmentAudit)
            .filter(
                AppointmentAudit.appointment_id.in_(appointment_ids),
                AppointmentAudit.action == "no_show_followup",
            )
            .order_by(
                AppointmentAudit.appointment_id.asc(),
                AppointmentAudit.created_at.desc(),
            )
            .all()
        )
        for row in rows:
            if not row or not row.appointment_id:
                continue
            if row.appointment_id in no_show_followup_map:
                continue
            no_show_followup_map[row.appointment_id] = _serialize_no_show_followup_state(row)
    latest_actor_type_map = _latest_actor_type_by_appointment(db, appointment_ids)

    conversation_ids = {b.conversation_id for b in bookings if b.conversation_id and not b.case_id}
    case_map = _latest_case_ids_by_conversation(
        db,
        client_id=context.client.id,
        conversation_ids=conversation_ids,
    )
    
    return BookingsListResponse(
        items=[
            _enrich_booking_response_for_context(
                context=context,
                booking=booking,
                booking_response=BookingResponse(
                    id=str(booking.id),
                    specialist_id=str(booking.specialist_id),
                    specialist_name=specialists_map.get(booking.specialist_id, "Unknown"),
                    start_at=booking.start_at.isoformat(),
                    end_at=booking.end_at.isoformat(),
                    customer_name=booking.customer_name,
                    customer_phone=booking.customer_phone,
                    service_type=services_map.get(booking.id),
                    notes=getattr(booking, "notes", None),
                    status=booking.status,
                    no_show_followup_done=bool(followup_state.get("done", False)),
                    no_show_followup_result=followup_state.get("result"),
                    no_show_followup_closed_at=followup_state.get("closed_at"),
                    no_show_followup_closed_by=followup_state.get("closed_by"),
                    no_show_followup_rebooked_appointment_id=followup_state.get("rebooked_appointment_id"),
                    follow_up_owner_id=str(getattr(booking, "follow_up_owner_id", None)) if getattr(booking, "follow_up_owner_id", None) else None,
                    follow_up_owner_name=follow_up_owner_map.get(getattr(booking, "follow_up_owner_id", None)),
                    follow_up_due_at=getattr(booking, "follow_up_due_at", None).isoformat() if getattr(booking, "follow_up_due_at", None) else None,
                    follow_up_overdue=_booking_follow_up_overdue(
                        booking=booking,
                        followup_done=bool(followup_state.get("done", False)),
                    ),
                    google_event_id=sync_map.get(booking.id),
                    conversation_id=str(booking.conversation_id) if booking.conversation_id else None,
                    case_id=str(linked_case_id) if linked_case_id else None,
                    needs_action=_booking_needs_action(
                        booking.status,
                        followup_done=bool(followup_state.get("done", False)),
                    ),
                    attention_reason=_booking_attention_reason(
                        booking.status,
                        followup_done=bool(followup_state.get("done", False)),
                    ),
                    version=int(getattr(booking, "version", 1) or 1),
                    last_actor_type=latest_actor_type_map.get(booking.id),
                    created_at=booking.created_at.isoformat(),
                ),
                no_show_followup_done=bool(followup_state.get("done", False)),
                case_id=str(linked_case_id) if linked_case_id else None,
                last_actor_type=latest_actor_type_map.get(booking.id),
            )
            for booking in bookings
            for followup_state in [no_show_followup_map.get(booking.id, {})]
            for linked_case_id in [
                booking.case_id
                or (case_map.get(booking.conversation_id) if booking.conversation_id else None)
            ]
        ],
        cursor=next_cursor,
        has_more=has_more,
    )


@router.post("/operator-events", response_model=CalendarOperatorEventResponse)
async def record_calendar_operator_event(
    request: Request,
    data: CalendarOperatorEventRequest,
    db: Session = Depends(get_db),
):
    """Record bounded operator-side Calendar telemetry for replay and failure-family review."""
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "read")

    if data.event_type == "filter_apply" and data.action_id != "apply_filters":
        raise ConsoleAPIError(400, "INVALID_PARAM", "filter_apply requires action_id=apply_filters")
    if data.event_type == "filter_reset" and data.action_id != "reset_filters":
        raise ConsoleAPIError(400, "INVALID_PARAM", "filter_reset requires action_id=reset_filters")
    if data.event_type == "double_submit_blocked" and data.action_id in {"apply_filters", "reset_filters"}:
        raise ConsoleAPIError(400, "INVALID_PARAM", "double_submit_blocked requires a mutation action_id")
    if data.event_type == "double_submit_blocked" and data.action_id != "create_booking" and not data.booking_id:
        raise ConsoleAPIError(400, "INVALID_PARAM", "booking_id is required for double_submit_blocked")

    _record_calendar_operator_event_observation(
        db=db,
        context=context,
        event_type=data.event_type,
        action_id=data.action_id,
        surface=data.surface,
        booking_id=data.booking_id,
    )
    db.commit()
    return CalendarOperatorEventResponse(success=True)


@router.post("/bookings/{booking_id}/cancel", response_model=BookingActionResponse)
async def cancel_booking(
    request: Request,
    booking_id: str,
    data: BookingCancelRequest,
    db: Session = Depends(get_db)
):
    """Cancel a booking."""
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "write")

    service = SchedulingService(db)

    try:
        booking_uuid = _parse_uuid(booking_id, field_name="booking_id")
        current_booking = _resolve_booking_for_context(context, db, booking_uuid)
        previous_status = getattr(current_booking, "status", None)
        booking = service.cancel_appointment(
            appointment_id=booking_uuid,
            client_id=context.client.id,
            expected_version=data.version,
            reason=_normalize_optional_text(data.reason),
            actor_id=context.agent.id,
            actor_type="agent",
            channel="console",
            commit=False,
        )

        logger.info(
            f"Booking cancelled: {booking_id}",
            extra={"context": {"agent": context.agent.name, "reason": data.reason}}
        )

        if booking.branch and isinstance(booking.branch.booking_settings, dict):
            availability_provider = booking.branch.booking_settings.get("availability_provider")
            if availability_provider == "google_calendar":
                enqueue_appointment_sync(
                    db,
                    appointment=booking,
                    action="cancel",
                    commit=False,
                )

        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id="cancel_booking",
            outcome="applied",
            booking=booking,
            old_status=previous_status,
            new_status=getattr(booking, "status", None),
            linked_case_id=str(getattr(booking, "case_id", "")) or None,
            payload={"reason": _normalize_optional_text(data.reason)},
        )
        _commit_if_supported(db)
        db.refresh(booking)

        return BookingActionResponse(
            success=True,
            booking=_build_booking_response_for_context(
                db=db,
                context=context,
                booking=booking,
            ),
        )

    except AppointmentNotFoundError:
        raise ConsoleAPIError(404, "BOOKING_NOT_FOUND", "Booking not found")
    except AppointmentLifecycleActionDeniedError as exc:
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id="cancel_booking",
            outcome="denied",
            booking=current_booking if "current_booking" in locals() else None,
            old_status=exc.current_status,
            new_status=exc.current_status,
            blocked_reason_code="active_status_only",
            linked_case_id=str(getattr(current_booking, "case_id", "")) or None if "current_booking" in locals() else None,
        )
        _commit_if_supported(db)
        raise ConsoleAPIError(
            409,
            "BOOKING_CANCEL_DENIED",
            "Booking cancellation is not allowed",
            details={"status": exc.current_status},
        )
    except AppointmentVersionConflictError as exc:
        _raise_booking_version_conflict(
            expected_version=exc.expected_version,
            current_version=exc.current_version,
            db=db,
            context=context,
            action_id="cancel_booking",
            booking=current_booking if "current_booking" in locals() else None,
        )


@router.patch("/bookings/{booking_id}", response_model=BookingActionResponse)
async def update_booking(
    request: Request,
    booking_id: str,
    data: BookingUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing booking."""
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "write")

    booking_uuid = _parse_uuid(booking_id, field_name="booking_id")
    current_booking = _resolve_booking_for_context(context, db, booking_uuid)
    previous_status = getattr(current_booking, "status", None)
    previous_specialist_id = str(getattr(current_booking, "specialist_id", "")) or None
    previous_start_at = getattr(current_booking, "start_at", None)
    previous_end_at = getattr(current_booking, "end_at", None)

    specialist_uuid = _parse_uuid(data.specialist_id, field_name="specialist_id")
    specialist = db.query(Specialist).filter(
        Specialist.id == specialist_uuid,
        Specialist.client_id == context.client.id,
    ).first()
    if not specialist:
        raise ConsoleAPIError(404, "SPECIALIST_NOT_FOUND", "Specialist not found")
    if specialist.branch_id is None:
        raise ConsoleAPIError(400, "BRANCH_REQUIRED", "Specialist branch is required")

    customer_name = _normalize_operator_grade_text(data.customer_name, field_name="customer_name")
    customer_phone = _normalize_calendar_customer_phone(data.customer_phone, field_name="customer_phone")
    service_type = _normalize_operator_grade_text(data.service_type, field_name="service_type")
    notes = _normalize_optional_text(data.notes)

    service = SchedulingService(db)
    try:
        action_id = (
            "reschedule_booking"
            if (
                previous_specialist_id != str(specialist_uuid)
                or previous_start_at != data.start_at
                or previous_end_at != data.end_at
            )
            else "edit_booking"
        )
        booking = service.update_appointment(
            appointment_id=booking_uuid,
            client_id=context.client.id,
            specialist_id=specialist_uuid,
            start_at=data.start_at,
            end_at=data.end_at,
            customer_name=customer_name,
            customer_phone=customer_phone,
            service_type=service_type,
            notes=notes,
            expected_version=data.version,
            actor_id=context.agent.id,
            actor_type="agent",
            channel="console",
            correlation_id=str(context.agent.id),
            commit=False,
        )
        if booking.branch and isinstance(booking.branch.booking_settings, dict):
            availability_provider = booking.branch.booking_settings.get("availability_provider")
            if availability_provider == "google_calendar":
                enqueue_appointment_sync(
                    db,
                    appointment=booking,
                    action="update",
                    commit=False,
                )
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id=action_id,
            outcome="applied",
            booking=booking,
            old_status=previous_status,
            new_status=booking.status,
            linked_case_id=str(getattr(booking, "case_id", "")) or None,
        )
        _commit_if_supported(db)
        db.refresh(booking)
        return BookingActionResponse(
            success=True,
            booking=_build_booking_response_for_context(
                db=db,
                context=context,
                booking=booking,
            ),
        )
    except AppointmentNotFoundError:
        raise ConsoleAPIError(404, "BOOKING_NOT_FOUND", "Booking not found")
    except SpecialistNotFoundError:
        raise ConsoleAPIError(404, "SPECIALIST_NOT_FOUND", "Specialist not found")
    except AppointmentConflictError as exc:
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id=action_id if "action_id" in locals() else "edit_booking",
            outcome="denied",
            booking=current_booking,
            old_status=previous_status,
            new_status=previous_status,
            blocked_reason_code="slot_conflict",
            linked_case_id=str(getattr(current_booking, "case_id", "")) or None,
            payload={"reason": str(exc)},
        )
        _commit_if_supported(db)
        raise ConsoleAPIError(
            409,
            "BOOKING_CONFLICT",
            "Выбранное время уже занято. Пожалуйста, выберите другой слот.",
            details={"reason": str(exc)},
        )
    except AppointmentLifecycleActionDeniedError as exc:
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id=action_id if "action_id" in locals() else "edit_booking",
            outcome="denied",
            booking=current_booking,
            old_status=exc.current_status,
            new_status=exc.current_status,
            blocked_reason_code="active_status_only",
            linked_case_id=str(getattr(current_booking, "case_id", "")) or None,
        )
        _commit_if_supported(db)
        raise ConsoleAPIError(
            409,
            "BOOKING_UPDATE_DENIED",
            "Booking edit is not allowed",
            details={"status": exc.current_status},
        )
    except AppointmentVersionConflictError as exc:
        _raise_booking_version_conflict(
            expected_version=exc.expected_version,
            current_version=exc.current_version,
            db=db,
            context=context,
            action_id=action_id if "action_id" in locals() else "edit_booking",
            booking=current_booking,
        )


@router.post("/bookings/{booking_id}/status", response_model=BookingActionResponse)
async def update_booking_status(
    request: Request,
    booking_id: str,
    data: BookingStatusUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update booking visit status (completed/no_show)."""
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "write")

    service = SchedulingService(db)

    booking_uuid = _parse_uuid(booking_id, field_name="booking_id")
    current_booking = _resolve_booking_for_context(context, db, booking_uuid)
    previous_status = getattr(current_booking, "status", None)
    reason = _normalize_optional_text(data.reason)
    action_id = "mark_completed" if (data.status or "").upper() == "COMPLETED" else "mark_no_show"

    try:
        booking = service.update_appointment_status(
            appointment_id=booking_uuid,
            client_id=context.client.id,
            target_status=data.status,
            expected_version=data.version,
            actor_id=context.agent.id,
            actor_type="agent",
            channel="console",
            reason=reason,
            commit=False,
        )
    except AppointmentNotFoundError:
        raise ConsoleAPIError(404, "BOOKING_NOT_FOUND", "Booking not found")
    except AppointmentStatusValidationError as exc:
        raise ConsoleAPIError(
            400,
            "INVALID_STATUS",
            "Status must be one of: completed, no_show",
            details={"status": exc.status},
        )
    except InvalidAppointmentTransitionError as exc:
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id=action_id,
            outcome="denied",
            booking=current_booking,
            old_status=exc.current_status,
            new_status=exc.current_status,
            blocked_reason_code="active_status_only",
            linked_case_id=str(getattr(current_booking, "case_id", "")) or None,
            payload={"target_status": exc.target_status},
        )
        _commit_if_supported(db)
        raise ConsoleAPIError(
            409,
            "BOOKING_STATUS_TRANSITION_DENIED",
            "Booking status transition is not allowed",
            details={
                "from": exc.current_status,
                "to": exc.target_status,
            },
        )
    except AppointmentVersionConflictError as exc:
        _raise_booking_version_conflict(
            expected_version=exc.expected_version,
            current_version=exc.current_version,
            db=db,
            context=context,
            action_id=action_id,
            booking=current_booking,
        )

    case_effects: list[BookingCaseEffect] = []
    if (booking.status or "").upper() == "NO_SHOW":
        follow_up_defaults_changed = False
        if getattr(booking, "follow_up_owner_id", None) is None:
            booking.follow_up_owner_id = context.agent.id
            follow_up_defaults_changed = True
        if getattr(booking, "follow_up_due_at", None) is None:
            booking.follow_up_due_at = datetime.now(timezone.utc) + _DEFAULT_NO_SHOW_FOLLOW_UP_WINDOW
            follow_up_defaults_changed = True
        if follow_up_defaults_changed:
            _record_booking_router_mutation(
                db=db,
                booking=booking,
                context=context,
                action="no_show_follow_up_defaults",
                payload={
                    "follow_up_owner_id": str(booking.follow_up_owner_id) if booking.follow_up_owner_id else None,
                    "follow_up_due_at": booking.follow_up_due_at.isoformat() if booking.follow_up_due_at else None,
                },
            )
        case_effects = _maybe_reopen_linked_case_for_booking_attention(
            db=db,
            context=context,
            booking=booking,
        )

    _record_calendar_action_observation(
        db=db,
        context=context,
        action_id=action_id,
        outcome="applied",
        booking=booking,
        old_status=previous_status,
        new_status=booking.status,
        linked_case_id=str(getattr(booking, "case_id", "")) or None,
        payload={"reason": reason},
    )
    db.commit()
    db.refresh(booking)

    logger.info(
        "Booking status updated",
        extra={
            "context": {
                "agent": context.agent.name,
                "booking_id": booking_id,
                "target_status": booking.status,
                "case_effects": [effect.action for effect in case_effects],
            }
        },
    )
    return BookingActionResponse(
        success=True,
        booking=_build_booking_response_for_context(
            db=db,
            context=context,
            booking=booking,
        ),
        case_effects=case_effects,
    )


@router.post("/bookings/{booking_id}/no-show-followup", response_model=BookingActionResponse)
async def register_booking_no_show_followup(
    request: Request,
    booking_id: str,
    data: BookingNoShowFollowUpRequest,
    db: Session = Depends(get_db),
):
    """Record manager follow-up for a no-show booking."""
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "write")

    booking_uuid = _parse_uuid(booking_id, field_name="booking_id")
    booking = _resolve_booking_for_context(context, db, booking_uuid, for_update=True)
    result = (data.result or "contacted").strip().lower()
    action_id = "record_follow_up_rebooked" if result == "rebooked" else "record_follow_up_contacted"
    _assert_booking_version(
        booking=booking,
        expected_version=data.version,
        db=db,
        context=context,
        action_id=action_id,
    )
    if (booking.status or "").upper() != "NO_SHOW":
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id=action_id,
            outcome="invalid",
            booking=booking,
            old_status=booking.status,
            new_status=booking.status,
            blocked_reason_code="booking_status_required",
            linked_case_id=str(getattr(booking, "case_id", "")) or None,
        )
        _commit_if_supported(db)
        raise ConsoleAPIError(
            409,
            "BOOKING_STATUS_REQUIRED",
            "Booking status must be NO_SHOW for follow-up",
            details={"current_status": booking.status, "required_status": "NO_SHOW"},
        )

    note = _normalize_optional_text(data.note)
    rebooked_appointment_id = _normalize_optional_text(data.rebooked_appointment_id)
    if result == "rebooked" and not rebooked_appointment_id:
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id=action_id,
            outcome="invalid",
            booking=booking,
            old_status=booking.status,
            new_status=booking.status,
            blocked_reason_code="rebook_link_required",
            linked_case_id=str(getattr(booking, "case_id", "")) or None,
        )
        _commit_if_supported(db)
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            "rebooked_appointment_id is required when result=rebooked",
        )
    if result != "rebooked" and rebooked_appointment_id:
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id=action_id,
            outcome="invalid",
            booking=booking,
            old_status=booking.status,
            new_status=booking.status,
            blocked_reason_code="unexpected_rebook_link",
            linked_case_id=str(getattr(booking, "case_id", "")) or None,
        )
        _commit_if_supported(db)
        raise ConsoleAPIError(
            400,
            "INVALID_PARAM",
            "rebooked_appointment_id is allowed only when result=rebooked",
        )
    rebooked_booking: Optional[Appointment] = None
    if rebooked_appointment_id:
        rebooked_uuid = _parse_uuid(
            rebooked_appointment_id,
            field_name="rebooked_appointment_id",
        )
        if rebooked_uuid == booking.id:
            raise ConsoleAPIError(
                400,
                "INVALID_PARAM",
                "rebooked_appointment_id must reference another booking",
            )
        rebooked_booking = (
            db.query(Appointment)
            .filter(
                Appointment.id == rebooked_uuid,
                Appointment.client_id == context.client.id,
            )
            .first()
        )
        if not rebooked_booking:
            raise ConsoleAPIError(
                404,
                "BOOKING_NOT_FOUND",
                "Rebooked booking not found",
            )

    existing_followup = (
        db.query(AppointmentAudit)
        .filter(
            AppointmentAudit.appointment_id == booking.id,
            AppointmentAudit.action == "no_show_followup",
        )
        .order_by(AppointmentAudit.created_at.desc())
        .first()
    )
    followup_state = _serialize_no_show_followup_state(existing_followup)

    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "action": "contact_rebook",
        "source": "calendar_console",
        "result": result,
        "follow_up_closed_at": now.isoformat(),
        "follow_up_closed_by": str(context.agent.id),
    }
    if note:
        payload["note"] = note
    if rebooked_appointment_id:
        payload["rebooked_appointment_id"] = rebooked_appointment_id

    followup_changed = False
    if followup_state["done"]:
        current_payload = (
            dict(existing_followup.payload)
            if existing_followup and isinstance(existing_followup.payload, dict)
            else {}
        )
        requested_signature = {
            "result": result,
            "note": note,
            "rebooked_appointment_id": rebooked_appointment_id,
        }
        current_signature = {
            "result": current_payload.get("result") or followup_state["result"],
            "note": current_payload.get("note"),
            "rebooked_appointment_id": current_payload.get("rebooked_appointment_id"),
        }
        if current_signature != requested_signature:
            _record_calendar_action_observation(
                db=db,
                context=context,
                action_id=action_id,
                outcome="invalid",
                booking=booking,
                old_status=booking.status,
                new_status=booking.status,
                blocked_reason_code="follow_up_already_closed",
                linked_case_id=str(getattr(booking, "case_id", "")) or None,
            )
            _commit_if_supported(db)
            raise ConsoleAPIError(409, "FOLLOW_UP_ALREADY_CLOSED", "No-show follow-up is already closed")
    else:
        _record_booking_router_mutation(
            db=db,
            booking=booking,
            context=context,
            action="no_show_followup",
            payload=payload,
            now=now,
        )
        followup_changed = True

    case_effects: list[BookingCaseEffect] = []
    rebook_link_changed = False
    if result == "rebooked" and rebooked_booking is not None:
        case_effects, rebook_link_changed = _validate_or_link_rebooked_booking_case(
            db=db,
            context=context,
            source_booking=booking,
            rebooked_booking=rebooked_booking,
        )

    if followup_changed or rebook_link_changed:
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id=action_id,
            outcome="applied",
            booking=booking,
            old_status=booking.status,
            new_status=booking.status,
            linked_case_id=str(getattr(booking, "case_id", "")) or None,
            payload={
                "result": result,
                "rebooked_appointment_id": rebooked_appointment_id,
            },
        )
        _commit_if_supported(db)
    if rebooked_booking is not None:
        db.refresh(rebooked_booking)

    logger.info(
        "Booking no_show follow-up recorded",
        extra={
            "context": {
                "agent": context.agent.name,
                "booking_id": booking_id,
                "action": "contact_rebook",
                "result": result,
                "case_effects": [effect.action for effect in case_effects],
            }
        },
    )
    return BookingActionResponse(
        success=True,
        booking=_build_booking_response_for_context(
            db=db,
            context=context,
            booking=booking,
        ),
        case_effects=case_effects,
    )


@router.post("/bookings/{booking_id}/follow-up-governance", response_model=BookingActionResponse)
async def update_booking_follow_up_governance(
    request: Request,
    booking_id: str,
    data: BookingFollowUpGovernanceRequest,
    db: Session = Depends(get_db),
):
    """Update no-show follow-up owner/due governance for a booking."""
    context = get_console_context(request, db)
    require_console_permission(context, "calendar", "write")
    try:
        _require_follow_up_governance_permission(context)
    except ConsoleAPIError:
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id="manage_follow_up_governance",
            outcome="denied",
            booking=None,
            old_status=None,
            new_status=None,
            blocked_reason_code="permission_required",
        )
        _commit_if_supported(db)
        raise

    booking_uuid = _parse_uuid(booking_id, field_name="booking_id")
    booking = _resolve_booking_for_context(context, db, booking_uuid, for_update=True)
    action_id = "manage_follow_up_governance"
    _assert_booking_version(
        booking=booking,
        expected_version=data.version,
        db=db,
        context=context,
        action_id=action_id,
    )
    if (booking.status or "").upper() != "NO_SHOW":
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id=action_id,
            outcome="invalid",
            booking=booking,
            old_status=booking.status,
            new_status=booking.status,
            blocked_reason_code="booking_status_required",
            linked_case_id=str(getattr(booking, "case_id", "")) or None,
        )
        _commit_if_supported(db)
        raise ConsoleAPIError(
            409,
            "BOOKING_STATUS_REQUIRED",
            "Booking status must be NO_SHOW for follow-up governance",
            details={"current_status": booking.status, "required_status": "NO_SHOW"},
        )

    existing_followup = (
        db.query(AppointmentAudit)
        .filter(
            AppointmentAudit.appointment_id == booking.id,
            AppointmentAudit.action == "no_show_followup",
        )
        .order_by(AppointmentAudit.created_at.desc())
        .first()
    )
    followup_state = _serialize_no_show_followup_state(existing_followup)
    if followup_state["done"]:
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id=action_id,
            outcome="invalid",
            booking=booking,
            old_status=booking.status,
            new_status=booking.status,
            blocked_reason_code="follow_up_already_closed",
            linked_case_id=str(getattr(booking, "case_id", "")) or None,
        )
        _commit_if_supported(db)
        raise ConsoleAPIError(409, "FOLLOW_UP_ALREADY_CLOSED", "No-show follow-up is already closed")

    body_fields = data.model_dump(exclude_unset=True, exclude={"version"})
    if not body_fields:
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id=action_id,
            outcome="invalid",
            booking=booking,
            old_status=booking.status,
            new_status=booking.status,
            blocked_reason_code="governance_fields_required",
            linked_case_id=str(getattr(booking, "case_id", "")) or None,
        )
        _commit_if_supported(db)
        raise ConsoleAPIError(400, "INVALID_PARAM", "At least one governance field is required")

    changes: dict[str, Any] = {}
    owner_agent_uuid: Optional[UUID] = None
    if "owner_agent_id" in body_fields:
        owner_agent_id = data.owner_agent_id.strip() if data.owner_agent_id else None
        if owner_agent_id:
            owner_agent_uuid = _parse_uuid(owner_agent_id, field_name="owner_agent_id")
            _resolve_follow_up_owner_agent(
                context=context,
                db=db,
                owner_agent_id=owner_agent_uuid,
            )
        if booking.follow_up_owner_id != owner_agent_uuid:
            booking.follow_up_owner_id = owner_agent_uuid
            changes["follow_up_owner_id"] = str(owner_agent_uuid) if owner_agent_uuid else None

    if "due_at" in body_fields:
        normalized_due_at = _normalize_follow_up_due_at(data.due_at)
        if normalized_due_at and normalized_due_at <= datetime.now(timezone.utc) - timedelta(days=30):
            _record_calendar_action_observation(
                db=db,
                context=context,
                action_id=action_id,
                outcome="invalid",
                booking=booking,
                old_status=booking.status,
                new_status=booking.status,
                blocked_reason_code="due_at_too_far_past",
                linked_case_id=str(getattr(booking, "case_id", "")) or None,
            )
            _commit_if_supported(db)
            raise ConsoleAPIError(400, "INVALID_PARAM", "due_at is too far in the past")
        current_due_at = _normalize_follow_up_due_at(getattr(booking, "follow_up_due_at", None))
        if current_due_at != normalized_due_at:
            booking.follow_up_due_at = normalized_due_at
            changes["follow_up_due_at"] = normalized_due_at.isoformat() if normalized_due_at else None

    if changes:
        _record_booking_router_mutation(
            db=db,
            booking=booking,
            context=context,
            action="follow_up_governance",
            payload=changes,
        )
        _record_calendar_action_observation(
            db=db,
            context=context,
            action_id=action_id,
            outcome="applied",
            booking=booking,
            old_status=booking.status,
            new_status=booking.status,
            linked_case_id=str(getattr(booking, "case_id", "")) or None,
            payload=changes,
        )

    db.commit()
    db.refresh(booking)

    logger.info(
        "Booking follow-up governance updated",
        extra={
            "context": {
                "agent": context.agent.name,
                "booking_id": booking_id,
                "follow_up_owner_id": str(booking.follow_up_owner_id) if booking.follow_up_owner_id else None,
                "follow_up_due_at": booking.follow_up_due_at.isoformat() if booking.follow_up_due_at else None,
            }
        },
    )
    return BookingActionResponse(
        success=True,
        booking=_build_booking_response_for_context(
            db=db,
            context=context,
            booking=booking,
        ),
        case_effects=[],
    )


# ==================== Google Calendar OAuth ====================

@router.get(
    "/google/connect",
    status_code=307,
    response_class=RedirectResponse,
    responses={307: {"description": "Temporary redirect to Google OAuth"}},
)
async def google_connect(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Start Google Calendar OAuth flow.
    Redirects to Google consent screen.
    """
    context = get_console_context(request, db)
    require_console_permission(
        context,
        "settings",
        "write",
        message="Only owner/admin can connect Google Calendar",
    )
    branch_id = _resolve_calendar_branch(context)
    service = GoogleCalendarService(db)
    auth_url = service.get_auth_url(
        client_id=context.client.id,
        branch_id=branch_id
    )
    
    return RedirectResponse(url=auth_url)


@router.get(
    "/google/callback",
    status_code=307,
    response_class=RedirectResponse,
    responses={307: {"description": "Temporary redirect back to Console settings"}},
)
async def google_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback.
    Stores tokens and redirects to settings page.
    """
    service = GoogleCalendarService(db)
    
    try:
        token = service.handle_callback(code=code, state=state)
        logger.info(f"Google Calendar connected for client {token.client_id}")
        
        # Redirect to settings with success message
        return RedirectResponse(url="/settings?google_connected=true")
        
    except Exception as e:
        logger.error(f"Google OAuth callback failed: {e}")
        return RedirectResponse(url="/settings?google_error=true")


@router.get("/google/status")
async def google_status(
    request: Request,
    db: Session = Depends(get_db)
):
    """Check if Google Calendar is connected."""
    context = get_console_context(request, db)
    require_console_permission(context, "settings", "read")
    branch_id = _resolve_calendar_branch(context)
    
    from app.models.google_calendar_token import GoogleCalendarToken
    
    token = db.query(GoogleCalendarToken).filter(
        GoogleCalendarToken.client_id == context.client.id,
        GoogleCalendarToken.branch_id == branch_id
    ).first()
    
    return {
        "connected": token is not None,
        "expires_at": token.expires_at.isoformat() if token else None,
        "is_expired": token.is_expired() if token else True
    }
