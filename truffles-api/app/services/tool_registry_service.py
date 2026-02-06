from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.appointment_audit import AppointmentAudit
from app.models.appointment_service import AppointmentService as AppointmentServiceModel
from app.models.branch import Branch
from app.models.service import Service
from app.models.specialist import Specialist
from app.models.specialist_service import SpecialistService
from app.services.appointment_reminder_service import (
    mark_pending_reminders_failed,
    schedule_default_reminders,
)
from app.services.appointment_service import AppointmentConflictError, SchedulingService
from app.services.calendar_sync_service import enqueue_appointment_sync, get_provider_health

CALENDAR_TOOL_ACTIONS = {
    "calendar.list_slots",
    "calendar.book_slot",
    "calendar.get_booking",
    "calendar.reschedule",
    "calendar.cancel",
}

CATALOG_TOOL_ACTIONS = {
    "catalog.service_query",
    "catalog.location",
    "catalog.portfolio",
}

TOOL_ACTIONS = CALENDAR_TOOL_ACTIONS | CATALOG_TOOL_ACTIONS


@dataclass(frozen=True)
class ToolExecutionResult:
    handled: bool
    ok: bool
    response_text: str | None
    error_code: str | None
    decision_meta: dict[str, Any]
    trace: dict[str, Any]
    expected_reply_type: str | None = None


def is_tool_action(action: str | None) -> bool:
    return bool(action) and action in TOOL_ACTIONS


def _parse_datetime(value: str | None, *, fallback_tz: str | None = None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
    if not parsed:
        try:
            import dateparser

            parsed = dateparser.parse(text)
        except Exception:
            parsed = None
    if not parsed:
        return None
    if parsed.tzinfo is None:
        tz_name = fallback_tz or "Asia/Almaty"
        try:
            from zoneinfo import ZoneInfo

            parsed = parsed.replace(tzinfo=ZoneInfo(tz_name))
        except Exception:
            parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _resolve_branch(db: Session, branch_id: UUID | None) -> Branch | None:
    if not branch_id:
        return None
    return db.query(Branch).filter(Branch.id == branch_id).first()


def _resolve_service_duration(
    db: Session,
    *,
    service_name: str | None,
    branch: Branch | None,
) -> int:
    if service_name:
        service = (
            db.query(Service)
            .filter(
                Service.branch_id == branch.id if branch else True,
                Service.name == service_name,
                Service.is_active == True,
            )
            .first()
        )
        if service and service.duration_min:
            return int(service.duration_min)
    if branch and isinstance(branch.booking_settings, dict):
        duration = branch.booking_settings.get("default_duration_min") or branch.booking_settings.get(
            "slot_duration_min"
        )
        if duration:
            return int(duration)
    return SchedulingService.DEFAULT_SLOT_DURATION


def _clean_specialist_name(value: str | None) -> str | None:
    if not value or not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    cleaned = re.sub(r"^(мастер|мастеру|master)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or None


def _resolve_specialist_by_name(
    db: Session,
    *,
    branch: Branch,
    specialist_name: str,
) -> tuple[Specialist | None, str | None]:
    cleaned = _clean_specialist_name(specialist_name)
    if not cleaned:
        return None, "specialist_not_found"
    normalized = cleaned.casefold()
    base_query = (
        db.query(Specialist)
        .filter(
            Specialist.branch_id == branch.id,
            Specialist.is_active == True,
        )
    )
    exact = base_query.filter(func.lower(Specialist.name) == normalized).all()
    if len(exact) == 1:
        return exact[0], None
    if len(exact) > 1:
        return None, "specialist_ambiguous"
    prefix = base_query.filter(func.lower(Specialist.name).like(normalized + "%")).all()
    if len(prefix) == 1:
        return prefix[0], None
    if len(prefix) > 1:
        return None, "specialist_ambiguous"
    return None, "specialist_not_found"


def _resolve_specialists_for_service(
    db: Session,
    *,
    branch: Branch,
    service_name: str | None,
) -> list[Specialist]:
    if not service_name or not isinstance(service_name, str):
        return []
    normalized = service_name.strip().casefold()
    if not normalized:
        return []
    return (
        db.query(Specialist)
        .join(SpecialistService, SpecialistService.specialist_id == Specialist.id)
        .join(Service, Service.id == SpecialistService.service_id)
        .filter(
            Specialist.branch_id == branch.id,
            Specialist.is_active == True,
            Service.branch_id == branch.id,
            Service.is_active == True,
            func.lower(Service.name) == normalized,
        )
        .order_by(Specialist.name)
        .all()
    )


def _resolve_specialist_filter(
    db: Session,
    *,
    branch: Branch,
    specialist_id: str | None,
    specialist_name: str | None,
) -> tuple[UUID | None, str | None, str | None]:
    if specialist_id:
        try:
            specialist_uuid = UUID(str(specialist_id))
        except (ValueError, TypeError):
            return None, None, "specialist_not_found"
        specialist = (
            db.query(Specialist)
            .filter(
                Specialist.id == specialist_uuid,
                Specialist.branch_id == branch.id,
                Specialist.is_active == True,
            )
            .first()
        )
        if not specialist:
            return None, None, "specialist_not_found"
        return specialist.id, "explicit_id", None
    if specialist_name:
        specialist, error = _resolve_specialist_by_name(
            db,
            branch=branch,
            specialist_name=specialist_name,
        )
        if specialist:
            return specialist.id, "explicit_name", None
        return None, None, error
    return None, None, None


def _resolve_specialist_for_booking(
    db: Session,
    *,
    branch: Branch,
    service_name: str | None,
    specialist_id: str | None,
    specialist_name: str | None,
) -> tuple[Specialist | None, str | None, str | None]:
    specialist_uuid, selection_reason, error = _resolve_specialist_filter(
        db,
        branch=branch,
        specialist_id=specialist_id,
        specialist_name=specialist_name,
    )
    if error:
        return None, None, error
    if specialist_uuid:
        specialist = (
            db.query(Specialist)
            .filter(
                Specialist.id == specialist_uuid,
                Specialist.branch_id == branch.id,
                Specialist.is_active == True,
            )
            .first()
        )
        if specialist:
            return specialist, selection_reason, None
        return None, None, "specialist_not_found"

    candidates = _resolve_specialists_for_service(db, branch=branch, service_name=service_name)
    if candidates:
        return candidates[0], "service_default", None

    fallback = (
        db.query(Specialist)
        .filter(
            Specialist.branch_id == branch.id,
            Specialist.is_active == True,
        )
        .order_by(Specialist.name)
        .first()
    )
    if fallback:
        return fallback, "branch_default", None
    return None, None, "specialist_not_found"


def _format_slot_list(slots_by_specialist: dict[str, list[str]]) -> str:
    parts: list[str] = []
    for specialist_name, slots in slots_by_specialist.items():
        if not slots:
            continue
        slot_text = ", ".join(slots[:5])
        parts.append(f"{specialist_name}: {slot_text}")
    if not parts:
        return "Свободных слотов не нашлось. Могу предложить другое время."
    return "Свободные слоты: " + " | ".join(parts)


def _list_slots(
    db: Session,
    *,
    branch: Branch,
    specialist_id: UUID | None,
    date_value: str | None,
    duration_min: int | None,
) -> tuple[str | None, str | None]:
    if not date_value:
        return None, "missing_date"
    date_parsed = _parse_datetime(date_value, fallback_tz=branch.timezone if branch else None)
    if not date_parsed:
        return None, "invalid_date"

    duration = duration_min or SchedulingService.DEFAULT_SLOT_DURATION
    service = SchedulingService(db)
    specialists: list[Specialist] = []
    if specialist_id:
        specialist = (
            db.query(Specialist)
            .filter(
                Specialist.id == specialist_id,
                Specialist.branch_id == branch.id,
                Specialist.is_active == True,
            )
            .first()
        )
        if not specialist:
            return None, "specialist_not_found"
        specialists = [specialist]
    else:
        specialists = (
            db.query(Specialist)
            .filter(
                Specialist.branch_id == branch.id,
                Specialist.is_active == True,
            )
            .order_by(Specialist.name)
            .all()
        )

    slots_by_specialist: dict[str, list[str]] = {}
    for specialist in specialists:
        slots = service.get_available_slots(
            specialist_id=specialist.id,
            date=date_parsed,
            duration_minutes=duration,
            client_id=branch.client_id,
        )
        slots_by_specialist[specialist.name] = [
            slot.start.strftime("%H:%M") for slot in slots if slot.available
        ]

    return _format_slot_list(slots_by_specialist), None


def _get_booking(
    db: Session,
    *,
    appointment_id: UUID | None,
    conversation_id: UUID | None,
) -> tuple[Appointment | None, str | None]:
    query = db.query(Appointment)
    if appointment_id:
        appointment = query.filter(Appointment.id == appointment_id).first()
    elif conversation_id:
        appointment = (
            query.filter(Appointment.conversation_id == conversation_id)
            .order_by(Appointment.created_at.desc())
            .first()
        )
    else:
        appointment = None
    if not appointment:
        return None, "appointment_not_found"
    return appointment, None


def _format_booking_summary(db: Session, appointment: Appointment) -> str:
    service_name = (
        db.query(AppointmentServiceModel.service_name)
        .filter(AppointmentServiceModel.appointment_id == appointment.id)
        .scalar()
    )
    specialist_name = (
        db.query(Specialist.name)
        .filter(Specialist.id == appointment.specialist_id)
        .scalar()
    )
    service_label = service_name or "услуга"
    specialist_label = specialist_name or "мастер"
    return (
        f"Запись: {service_label}, {specialist_label}, "
        f"{appointment.start_at.strftime('%d.%m %H:%M')}."
    )


def _book_slot(
    db: Session,
    *,
    branch: Branch,
    specialist_id: UUID | None,
    start_at: datetime | None,
    end_at: datetime | None,
    service_name: str | None,
    customer_name: str | None,
    customer_phone: str | None,
    conversation_id: UUID | None,
) -> tuple[Appointment | None, str | None]:
    if not start_at:
        return None, "missing_start_at"

    duration_min = _resolve_service_duration(db, service_name=service_name, branch=branch)
    resolved_end = end_at or (start_at + timedelta(minutes=duration_min))

    service = SchedulingService(db)
    appointment = service.create_appointment(
        client_id=branch.client_id,
        branch_id=branch.id,
        specialist_id=specialist_id,
        start_at=start_at,
        end_at=resolved_end,
        customer_name=customer_name,
        customer_phone=customer_phone,
        service_type=service_name,
        notes=None,
        created_by=None,
        conversation_id=conversation_id,
        status="PENDING_CONFIRMATION",
        source="bot",
        confirmation_policy=None,
        audit={
            "actor_type": "bot",
            "channel": "whatsapp",
            "action": "create",
            "payload": {"tool_action": "calendar.book_slot"},
        },
        commit=True,
    )
    return appointment, None


def _reschedule_booking(
    db: Session,
    *,
    appointment: Appointment,
    start_at: datetime | None,
    end_at: datetime | None,
) -> tuple[Appointment | None, str | None]:
    if not start_at or not end_at:
        return None, "missing_datetime"
    prev_status = appointment.status
    prev_version = appointment.version
    appointment.start_at = start_at
    appointment.end_at = end_at
    appointment.status = "RESCHEDULE_REQUESTED"
    appointment.version = int(appointment.version or 0) + 1
    appointment.updated_at = datetime.now(timezone.utc)
    db.add(
        AppointmentAudit(
            appointment_id=appointment.id,
            actor_type="bot",
            actor_id=None,
            channel="whatsapp",
            action="reschedule",
            prev_status=prev_status,
            new_status=appointment.status,
            prev_version=prev_version,
            new_version=appointment.version,
            payload={"tool_action": "calendar.reschedule"},
            correlation_id=str(appointment.conversation_id) if appointment.conversation_id else None,
        )
    )
    db.commit()
    return appointment, None


def _cancel_booking(
    db: Session,
    *,
    appointment: Appointment,
    reason: str | None,
) -> tuple[Appointment | None, str | None]:
    prev_status = appointment.status
    prev_version = appointment.version
    appointment.status = "CANCELLED"
    appointment.version = int(appointment.version or 0) + 1
    appointment.updated_at = datetime.now(timezone.utc)
    db.add(
        AppointmentAudit(
            appointment_id=appointment.id,
            actor_type="bot",
            actor_id=None,
            channel="whatsapp",
            action="cancel",
            prev_status=prev_status,
            new_status=appointment.status,
            prev_version=prev_version,
            new_version=appointment.version,
            payload={"tool_action": "calendar.cancel", "reason": reason},
            correlation_id=str(appointment.conversation_id) if appointment.conversation_id else None,
        )
    )
    db.commit()
    return appointment, None


def _format_service_catalog(
    service_name: str,
    duration_min: int | None,
    price: int | None,
    masters: list[str],
) -> str:
    parts = [service_name]
    if duration_min:
        parts.append(f"{duration_min} мин")
    if price is not None:
        parts.append(f"{price} ₸")
    reply = " — ".join(parts)
    if masters:
        reply = f"{reply}. Мастера: {', '.join(masters)}."
    return reply


def _resolve_masters_for_service(
    db: Session,
    *,
    service_id: UUID,
    branch_id: UUID,
) -> list[str]:
    rows = (
        db.query(Specialist.name)
        .join(SpecialistService, SpecialistService.specialist_id == Specialist.id)
        .filter(
            SpecialistService.service_id == service_id,
            SpecialistService.is_active == True,
            Specialist.branch_id == branch_id,
            Specialist.is_active == True,
        )
        .order_by(Specialist.name)
        .all()
    )
    return [row[0] for row in rows if row and row[0]]


def _catalog_service_query(
    db: Session,
    *,
    branch: Branch,
    service_query: str,
) -> tuple[str | None, str | None]:
    services = (
        db.query(Service)
        .filter(
            Service.branch_id == branch.id,
            Service.is_active == True,
        )
        .all()
    )
    if not services:
        return None, "services_missing"

    service_name = service_query.strip()
    match = next((svc for svc in services if svc.name.casefold() == service_name.casefold()), None)
    if not match:
        try:
            from rapidfuzz import process

            candidates = {svc.name: svc for svc in services if svc.name}
            if candidates:
                best = process.extractOne(service_name, candidates.keys(), score_cutoff=70)
                if best:
                    match = candidates.get(best[0])
        except Exception:
            match = None

    if not match:
        return None, "service_not_found"

    masters = _resolve_masters_for_service(db, service_id=match.id, branch_id=branch.id)
    return _format_service_catalog(match.name, match.duration_min, match.price, masters), None


def _catalog_location(client_slug: str | None) -> tuple[str | None, str | None]:
    from app.services.demo_salon_knowledge import format_reply_from_truth

    reply = format_reply_from_truth("location", client_slug=client_slug)
    if reply:
        return reply, None
    return None, "location_missing"


def _catalog_portfolio(client_slug: str | None) -> tuple[str | None, str | None]:
    from app.services.demo_salon_knowledge import load_yaml_truth

    truth = load_yaml_truth(client_slug)
    instagram = (
        truth.get("salon", {}).get("instagram") if isinstance(truth, dict) else None
    )
    if instagram:
        return f"Примеры работ: {instagram}", None
    return None, "portfolio_missing"


def execute_tool_action(
    db: Session,
    *,
    tool_action: str,
    tool_args: dict[str, Any],
    conversation_id: UUID | None,
    branch_id: UUID | None,
    client_slug: str | None,
    service_query: str | None,
    now: datetime | None = None,
    user_name: str | None = None,
    user_phone: str | None = None,
) -> ToolExecutionResult:
    if tool_action not in TOOL_ACTIONS:
        return ToolExecutionResult(
            handled=False,
            ok=False,
            response_text=None,
            error_code="tool_action_invalid",
            decision_meta={},
            trace={},
        )

    now = now or datetime.now(timezone.utc)
    branch = _resolve_branch(db, branch_id)
    if tool_action.startswith("calendar.") and not branch:
        return ToolExecutionResult(
            handled=True,
            ok=False,
            response_text="Не могу определить филиал для записи. Уточните, пожалуйста, филиал.",
            error_code="branch_missing",
            decision_meta={"tool_action": tool_action, "tool_decision": "branch_missing"},
            trace={"stage": "tool_registry", "decision": "error", "reason": "branch_missing"},
        )

    if tool_action == "calendar.list_slots":
        if isinstance(branch.booking_settings, dict):
            availability_provider = branch.booking_settings.get("availability_provider")
            if availability_provider == "google_calendar":
                health = get_provider_health(
                    db,
                    client_id=branch.client_id,
                    branch_id=branch.id,
                )
                if not health.ready:
                    return ToolExecutionResult(
                        handled=True,
                        ok=False,
                        response_text=(
                            "Сейчас календарь недоступен. Напишите удобное время, и мы уточним."
                        ),
                        error_code="provider_unavailable",
                        decision_meta={
                            "tool_action": tool_action,
                            "tool_decision": "provider_unavailable",
                            "provider_reason": health.reason,
                        },
                        trace={
                            "stage": "tool_registry",
                            "decision": "provider_unavailable",
                            "tool_action": tool_action,
                            "provider_reason": health.reason,
                        },
                    )
        raw_date = tool_args.get("date") or tool_args.get("start_at")
        duration = tool_args.get("duration_min") or _resolve_service_duration(
            db, service_name=service_query, branch=branch
        )
        specialist_id = tool_args.get("specialist_id")
        specialist_name = tool_args.get("specialist_name")
        specialist_uuid, _, specialist_error = _resolve_specialist_filter(
            db,
            branch=branch,
            specialist_id=specialist_id,
            specialist_name=specialist_name,
        )
        if specialist_error:
            message = (
                "Нашла несколько мастеров с таким именем. Уточните, пожалуйста."
                if specialist_error == "specialist_ambiguous"
                else "Не нашла такого мастера. Уточните, пожалуйста."
            )
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text=message,
                error_code=specialist_error,
                decision_meta={
                    "tool_action": tool_action,
                    "tool_decision": "specialist_missing",
                },
                trace={
                    "stage": "tool_registry",
                    "decision": "specialist_missing",
                    "tool_action": tool_action,
                    "specialist_name": specialist_name,
                },
            )
        response, error = _list_slots(
            db,
            branch=branch,
            specialist_id=specialist_uuid,
            date_value=raw_date,
            duration_min=duration,
        )
        if error:
            missing_type = "datetime" if error in {"missing_date", "invalid_date"} else None
            prompt = None
            expected_reply_type = None
            if missing_type == "datetime":
                from app.routers.webhook import _legacy as legacy

                prompt = legacy.MSG_BOOKING_ASK_DATETIME
                expected_reply_type = legacy.EXPECTED_REPLY_TIME
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text=prompt,
                error_code=error,
                decision_meta={
                    "tool_action": tool_action,
                    "tool_decision": "missing_slot",
                    "missing_slot": missing_type,
                },
                trace={
                    "stage": "tool_registry",
                    "decision": "missing_slot",
                    "tool_action": tool_action,
                    "missing_slot": missing_type,
                },
                expected_reply_type=expected_reply_type,
            )
        return ToolExecutionResult(
            handled=True,
            ok=True,
            response_text=response,
            error_code=None,
            decision_meta={"tool_action": tool_action, "tool_decision": "ok"},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": tool_action},
        )

    if tool_action == "calendar.get_booking":
        appointment_id = tool_args.get("appointment_id")
        appointment_uuid = UUID(appointment_id) if isinstance(appointment_id, str) else None
        appointment, error = _get_booking(
            db,
            appointment_id=appointment_uuid,
            conversation_id=conversation_id,
        )
        if error:
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text="Запись не найдена. Хотите записаться на новое время?",
                error_code=error,
                decision_meta={"tool_action": tool_action, "tool_decision": "not_found"},
                trace={
                    "stage": "tool_registry",
                    "decision": "not_found",
                    "tool_action": tool_action,
                },
            )
        return ToolExecutionResult(
            handled=True,
            ok=True,
            response_text=_format_booking_summary(db, appointment),
            error_code=None,
            decision_meta={"tool_action": tool_action, "tool_decision": "ok"},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": tool_action},
        )

    if tool_action == "calendar.book_slot":
        health = get_provider_health(
            db,
            client_id=branch.client_id,
            branch_id=branch.id,
        )
        if not health.ready:
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text="Сейчас календарь недоступен. Напишите удобное время, и мы уточним.",
                error_code="provider_unavailable",
                decision_meta={
                    "tool_action": tool_action,
                    "tool_decision": "provider_unavailable",
                    "provider_reason": health.reason,
                },
                trace={
                    "stage": "tool_registry",
                    "decision": "provider_unavailable",
                    "tool_action": tool_action,
                    "provider_reason": health.reason,
                },
            )

        start_at = _parse_datetime(tool_args.get("start_at"), fallback_tz=branch.timezone)
        end_at = _parse_datetime(tool_args.get("end_at"), fallback_tz=branch.timezone)
        specialist_id = tool_args.get("specialist_id")
        specialist_name = tool_args.get("specialist_name")
        specialist, specialist_selection, specialist_error = _resolve_specialist_for_booking(
            db,
            branch=branch,
            service_name=service_query,
            specialist_id=specialist_id,
            specialist_name=specialist_name,
        )
        if specialist_error:
            message = (
                "Нашла несколько мастеров с таким именем. Уточните, пожалуйста."
                if specialist_error == "specialist_ambiguous"
                else "Не нашла такого мастера. Уточните, пожалуйста."
            )
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text=message,
                error_code=specialist_error,
                decision_meta={
                    "tool_action": tool_action,
                    "tool_decision": "specialist_missing",
                },
                trace={
                    "stage": "tool_registry",
                    "decision": "specialist_missing",
                    "tool_action": tool_action,
                    "specialist_name": specialist_name,
                },
            )
        try:
            appointment, error = _book_slot(
                db,
                branch=branch,
                specialist_id=specialist.id if specialist else None,
                start_at=start_at,
                end_at=end_at,
                service_name=service_query,
                customer_name=tool_args.get("customer_name") or user_name,
                customer_phone=tool_args.get("customer_phone") or user_phone,
                conversation_id=conversation_id,
            )
        except AppointmentConflictError:
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text="Этот слот уже занят. Могу предложить другое время.",
                error_code="slot_unavailable",
                decision_meta={"tool_action": tool_action, "tool_decision": "conflict"},
                trace={"stage": "tool_registry", "decision": "conflict", "tool_action": tool_action},
            )
        if error:
            from app.routers.webhook import _legacy as legacy

            missing_slot = "datetime" if error == "missing_start_at" else None
            prompt = legacy.MSG_BOOKING_ASK_DATETIME if missing_slot == "datetime" else None
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text=prompt,
                error_code=error,
                decision_meta={
                    "tool_action": tool_action,
                    "tool_decision": "missing_slot",
                    "missing_slot": missing_slot,
                },
                trace={
                    "stage": "tool_registry",
                    "decision": "missing_slot",
                    "tool_action": tool_action,
                    "missing_slot": missing_slot,
                },
                expected_reply_type=legacy.EXPECTED_REPLY_TIME if missing_slot else None,
            )
        enqueue_appointment_sync(
            db,
            appointment=appointment,
            action="create",
            commit=True,
        )
        scheduled = schedule_default_reminders(
            db,
            appointment=appointment,
            commit=True,
        )
        return ToolExecutionResult(
            handled=True,
            ok=True,
            response_text="Запись создана. Хотите что-то изменить?",
            error_code=None,
            decision_meta={
                "tool_action": tool_action,
                "tool_decision": "ok",
                "appointment_id": str(appointment.id),
                "reminder_jobs_scheduled": len(scheduled),
                "specialist_id": str(specialist.id) if specialist else None,
                "specialist_name": specialist.name if specialist else None,
                "specialist_selection": specialist_selection,
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": tool_action,
                "appointment_id": str(appointment.id),
                "reminder_jobs_scheduled": len(scheduled),
                "specialist_id": str(specialist.id) if specialist else None,
                "specialist_selection": specialist_selection,
            },
        )

    if tool_action == "calendar.reschedule":
        appointment_id = tool_args.get("appointment_id")
        appointment_uuid = UUID(appointment_id) if isinstance(appointment_id, str) else None
        appointment, error = _get_booking(
            db,
            appointment_id=appointment_uuid,
            conversation_id=conversation_id,
        )
        if error:
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text="Запись не найдена. Хотите записаться на новое время?",
                error_code=error,
                decision_meta={"tool_action": tool_action, "tool_decision": "not_found"},
                trace={
                    "stage": "tool_registry",
                    "decision": "not_found",
                    "tool_action": tool_action,
                },
            )
        start_at = _parse_datetime(tool_args.get("start_at"), fallback_tz=branch.timezone)
        end_at = _parse_datetime(tool_args.get("end_at"), fallback_tz=branch.timezone)
        updated, error = _reschedule_booking(
            db,
            appointment=appointment,
            start_at=start_at,
            end_at=end_at,
        )
        if error:
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text="Уточните, пожалуйста, новое время.",
                error_code=error,
                decision_meta={"tool_action": tool_action, "tool_decision": "missing_slot"},
                trace={
                    "stage": "tool_registry",
                    "decision": "missing_slot",
                    "tool_action": tool_action,
                },
            )
        enqueue_appointment_sync(
            db,
            appointment=updated,
            action="update",
            commit=True,
        )
        cancelled_jobs = mark_pending_reminders_failed(
            db,
            appointment_id=updated.id,
            reason="rescheduled",
            commit=False,
        )
        scheduled = schedule_default_reminders(
            db,
            appointment=updated,
            commit=True,
        )
        return ToolExecutionResult(
            handled=True,
            ok=True,
            response_text="Перенос оформлен. Менеджер подтвердит новое время.",
            error_code=None,
            decision_meta={
                "tool_action": tool_action,
                "tool_decision": "ok",
                "reminder_jobs_cancelled": len(cancelled_jobs),
                "reminder_jobs_scheduled": len(scheduled),
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": tool_action,
                "reminder_jobs_cancelled": len(cancelled_jobs),
                "reminder_jobs_scheduled": len(scheduled),
            },
        )

    if tool_action == "calendar.cancel":
        appointment_id = tool_args.get("appointment_id")
        appointment_uuid = UUID(appointment_id) if isinstance(appointment_id, str) else None
        appointment, error = _get_booking(
            db,
            appointment_id=appointment_uuid,
            conversation_id=conversation_id,
        )
        if error:
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text="Запись не найдена. Хотите записаться на новое время?",
                error_code=error,
                decision_meta={"tool_action": tool_action, "tool_decision": "not_found"},
                trace={
                    "stage": "tool_registry",
                    "decision": "not_found",
                    "tool_action": tool_action,
                },
            )
        updated, error = _cancel_booking(
            db,
            appointment=appointment,
            reason=tool_args.get("reason"),
        )
        if error:
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text="Не смог отменить запись. Уточните причину отмены.",
                error_code=error,
                decision_meta={"tool_action": tool_action, "tool_decision": "error"},
                trace={"stage": "tool_registry", "decision": "error", "tool_action": tool_action},
            )
        enqueue_appointment_sync(
            db,
            appointment=updated,
            action="cancel",
            commit=True,
        )
        cancelled_jobs = mark_pending_reminders_failed(
            db,
            appointment_id=updated.id,
            reason="cancelled",
            commit=True,
        )
        return ToolExecutionResult(
            handled=True,
            ok=True,
            response_text="Запись отменена. Если нужно новое время — напишите.",
            error_code=None,
            decision_meta={
                "tool_action": tool_action,
                "tool_decision": "ok",
                "reminder_jobs_cancelled": len(cancelled_jobs),
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": tool_action,
                "reminder_jobs_cancelled": len(cancelled_jobs),
            },
        )

    if tool_action == "catalog.service_query":
        if not branch:
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text="Уточните, пожалуйста, филиал.",
                error_code="branch_missing",
                decision_meta={"tool_action": tool_action, "tool_decision": "branch_missing"},
                trace={"stage": "tool_registry", "decision": "branch_missing"},
            )
        if not service_query:
            from app.routers.webhook import _legacy as legacy

            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text=legacy.MSG_BOOKING_ASK_SERVICE,
                error_code="missing_service",
                decision_meta={
                    "tool_action": tool_action,
                    "tool_decision": "missing_slot",
                    "missing_slot": "service",
                },
                trace={"stage": "tool_registry", "decision": "missing_slot"},
                expected_reply_type=legacy.EXPECTED_REPLY_SERVICE,
            )
        reply, error = _catalog_service_query(
            db,
            branch=branch,
            service_query=service_query,
        )
        if error:
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text="Такой услуги нет. Уточните, пожалуйста, что интересует.",
                error_code=error,
                decision_meta={"tool_action": tool_action, "tool_decision": "not_found"},
                trace={"stage": "tool_registry", "decision": "not_found"},
            )
        return ToolExecutionResult(
            handled=True,
            ok=True,
            response_text=reply,
            error_code=None,
            decision_meta={"tool_action": tool_action, "tool_decision": "ok"},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": tool_action},
        )

    if tool_action == "catalog.location":
        reply, error = _catalog_location(client_slug)
        if error:
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text="Адрес сейчас недоступен. Напишите, пожалуйста, какой район удобен.",
                error_code=error,
                decision_meta={"tool_action": tool_action, "tool_decision": "not_found"},
                trace={"stage": "tool_registry", "decision": "not_found"},
            )
        return ToolExecutionResult(
            handled=True,
            ok=True,
            response_text=reply,
            error_code=None,
            decision_meta={"tool_action": tool_action, "tool_decision": "ok"},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": tool_action},
        )

    if tool_action == "catalog.portfolio":
        reply, error = _catalog_portfolio(client_slug)
        if error:
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text="Портфолио сейчас недоступно. Могу помочь подобрать услугу.",
                error_code=error,
                decision_meta={"tool_action": tool_action, "tool_decision": "not_found"},
                trace={"stage": "tool_registry", "decision": "not_found"},
            )
        return ToolExecutionResult(
            handled=True,
            ok=True,
            response_text=reply,
            error_code=None,
            decision_meta={"tool_action": tool_action, "tool_decision": "ok"},
            trace={"stage": "tool_registry", "decision": "ok", "tool_action": tool_action},
        )

    return ToolExecutionResult(
        handled=True,
        ok=False,
        response_text=None,
        error_code="tool_action_invalid",
        decision_meta={"tool_action": tool_action, "tool_decision": "invalid"},
        trace={"stage": "tool_registry", "decision": "invalid", "tool_action": tool_action},
    )
