from __future__ import annotations

import os
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
from app.schemas.intent import validate_tool_args_shape
from app.services.appointment_reminder_service import (
    mark_pending_reminders_failed,
    schedule_default_reminders,
)
from app.services.appointment_service import AppointmentConflictError, SchedulingService
from app.services.calendar_sync_service import enqueue_appointment_sync, get_provider_health
from app.services.capabilities_runtime import get_runtime_capabilities
from app.services.pack_runtime_service import (
    _detect_promotion_intent,
    _has_duration_signal,
    _has_parking_signal,
    _has_price_signal,
    _match_service,
    _normalize_text,
    build_info_combined_reply,
    format_reply_from_truth,
    get_pack_adapter,
    load_yaml_truth,
)

_TIME_TOKEN_RE = re.compile(r"\b([01]?\d|2[0-3])[:.][0-5]\d\b")
_BOOKING_VERIFICATION_RE = re.compile(
    r"\b(проверь|провер|подтверд|подтвержд|check|confirm|verify)\w*",
    re.IGNORECASE,
)
_SERVICES_OVERVIEW_RE = re.compile(
    r"\b(какие|что|какой|какова)\b.{0,40}\b(услуг[аи]?|процедур[аы]?|сервис[аы]?)\b"
    r"|\b(перечень|список|каталог|ассортимент)\b.{0,30}\b(услуг[аи]?|процедур[аы]?|сервис[аы]?)\b",
    re.IGNORECASE,
)

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

_CALENDAR_PROVIDER_HARD_FAILURES = {
    "connection_missing",
    "token_missing",
    "token_expired",
}


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


def _calendar_provider_should_block(reason: str | None) -> bool:
    return (reason or "") in _CALENDAR_PROVIDER_HARD_FAILURES


def _with_provider_health_meta(
    decision_meta: dict[str, Any],
    trace: dict[str, Any],
    *,
    reason: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not reason:
        return decision_meta, trace
    decision_meta = dict(decision_meta)
    trace = dict(trace)
    decision_meta["provider_health_reason"] = reason
    trace["provider_health_reason"] = reason
    if reason in {"sync_missing", "sync_stale"}:
        decision_meta["provider_health_degraded"] = True
    return decision_meta, trace


def _normalize_tool_policy_tokens(raw_tokens: Any) -> list[str]:
    if not isinstance(raw_tokens, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for token in raw_tokens:
        text = str(token or "").strip().casefold()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _is_env_enabled(value: str | None, *, default: bool = True) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _is_tool_policy_enforcement_enabled() -> bool:
    return _is_env_enabled(os.environ.get("TOOL_POLICY_ENFORCEMENT"), default=True)


def _tool_policy_token_matches(*, token: str, tool_action: str) -> bool:
    if token == "*":
        return True
    if token.endswith(".*"):
        return tool_action.startswith(token[:-1])
    return token == tool_action


def _resolve_runtime_tool_policy() -> tuple[list[str], list[str], str]:
    runtime = get_runtime_capabilities()
    if runtime is None:
        return [], [], "default"
    tools_config = getattr(runtime.payload, "tools", None)
    allow_tokens = _normalize_tool_policy_tokens(getattr(tools_config, "allow", None))
    deny_tokens = _normalize_tool_policy_tokens(getattr(tools_config, "deny", None))
    source = str(getattr(runtime, "source", "") or "runtime")
    return allow_tokens, deny_tokens, source


def _tool_action_block_reason(
    *,
    tool_action: str,
    allow_tokens: list[str],
    deny_tokens: list[str],
) -> str | None:
    for token in deny_tokens:
        if _tool_policy_token_matches(token=token, tool_action=tool_action):
            return f"deny:{token}"
    if allow_tokens:
        for token in allow_tokens:
            if _tool_policy_token_matches(token=token, tool_action=tool_action):
                return None
        return "allowlist_miss"
    return None


def _parse_datetime(
    value: str | None,
    *,
    fallback_tz: str | None = None,
    now: datetime | None = None,
) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    timezone_name = fallback_tz or "Asia/Almaty"
    reference_now = now or datetime.now(timezone.utc)
    if reference_now.tzinfo is None:
        reference_now = reference_now.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
    if not parsed:
        try:
            import dateparser

            parsed = dateparser.parse(
                text,
                languages=["ru", "kk", "en"],
                settings={
                    "PREFER_DATES_FROM": "future",
                    "RELATIVE_BASE": reference_now,
                    "TIMEZONE": timezone_name,
                    "TO_TIMEZONE": timezone_name,
                    "RETURN_AS_TIMEZONE_AWARE": True,
                },
            )
        except Exception:
            parsed = None
    if not parsed:
        time_only_match = re.fullmatch(r"(?P<hour>\d{1,2})[:.](?P<minute>\d{2})", text)
        if time_only_match:
            try:
                hour = int(time_only_match.group("hour"))
                minute = int(time_only_match.group("minute"))
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    from zoneinfo import ZoneInfo

                    local_now = reference_now.astimezone(ZoneInfo(timezone_name))
                    parsed = local_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if parsed <= local_now:
                        parsed = parsed + timedelta(days=1)
            except Exception:
                parsed = None
    if not parsed:
        return None
    if parsed.tzinfo is None:
        tz_name = timezone_name
        try:
            from zoneinfo import ZoneInfo

            parsed = parsed.replace(tzinfo=ZoneInfo(tz_name))
        except Exception:
            parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_uuid(value: Any) -> UUID | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return UUID(text)
    except (ValueError, TypeError):
        return None


def _extract_time_token(text: str | None) -> str | None:
    if not text:
        return None
    match = _TIME_TOKEN_RE.search(text)
    if not match:
        return None
    token = match.group(0)
    return token.replace(".", ":")


def _looks_like_booking_verification_message(text: str | None) -> bool:
    if not text:
        return False
    return bool(_BOOKING_VERIFICATION_RE.search(text))


def _extract_daypart_token(text: str | None) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    normalized = text.casefold()
    if any(token in normalized for token in ("вечер", "вечером", "на вечер", "к вечеру")):
        return "evening"
    if any(token in normalized for token in ("утро", "утром", "на утро")):
        return "morning"
    if any(token in normalized for token in ("день", "днем", "днём", "на день", "днев")):
        return "day"
    return None


def _time_token_in_daypart(token: str, daypart: str) -> bool:
    if not token or ":" not in token:
        return False
    hour_raw, _, minute_raw = token.partition(":")
    try:
        hour = int(hour_raw)
        minute = int(minute_raw)
    except ValueError:
        return False
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return False
    if daypart == "morning":
        return 6 <= hour <= 11
    if daypart == "day":
        return 12 <= hour <= 16
    if daypart == "evening":
        return 17 <= hour <= 23
    return False


def _looks_like_services_overview_message(text: str | None) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = text.casefold()
    if _SERVICES_OVERVIEW_RE.search(normalized):
        return True
    return any(
        marker in normalized
        for marker in (
            "что вы предлагаете",
            "что у вас есть",
            "какие процедуры",
            "какие есть услуги",
        )
    )


def _format_services_overview_reply(
    db: Session,
    *,
    branch: Branch,
    client_slug: str | None,
) -> str | None:
    reply = format_reply_from_truth("services_overview", client_slug=client_slug)
    if isinstance(reply, str) and reply.strip():
        return reply

    rows = (
        db.query(Service.name)
        .filter(
            Service.branch_id == branch.id,
            Service.is_active == True,
        )
        .order_by(Service.name)
        .all()
    )
    names: list[str] = []
    for row in rows:
        value: str | None = None
        if isinstance(row, str):
            value = row
        elif isinstance(row, (tuple, list)) and row:
            value = str(row[0]) if row[0] is not None else None
        else:
            candidate = getattr(row, "name", None)
            value = str(candidate) if candidate is not None else None
        if value and value.strip():
            names.append(value.strip())
    if not names:
        return None
    return f"Мы предлагаем: {', '.join(names[:8])}. Подскажу по цене и времени любой услуги."


def _call_pack_adapter(adapter_slug: str | None, attr_name: str, *args: Any, **kwargs: Any) -> Any:
    adapter = get_pack_adapter(adapter_slug)
    handler = getattr(adapter, attr_name, None)
    if callable(handler):
        try:
            return handler(*args, **kwargs)
        except Exception:
            return None
    return None


def _expected_reply_prompt_from_hint(expected_reply_type: str | None) -> str | None:
    normalized = str(expected_reply_type or "").strip().casefold()
    if normalized == "name":
        return "Как вас зовут?"
    if normalized == "time":
        return "На какую дату и время вам удобно?"
    if normalized == "service_choice":
        return "На какую услугу хотите записаться?"
    return None


def _map_tool_args_shape_error(error: str) -> tuple[str, str]:
    if error == "tool_args_invalid":
        return "tool_args_not_dict", "tool_args"
    if error == "tool_args_key_invalid":
        return "tool_args_key_invalid", "tool_args"
    if error.startswith("tool_args_unknown_field:"):
        _, _, field = error.partition(":")
        return "tool_args_unknown_field", (field or "tool_args")
    if error.startswith("tool_args_type_invalid:"):
        _, _, field = error.partition(":")
        field_name = field or "tool_args"
        return f"{field_name}_type_invalid", field_name
    return "tool_args_invalid", "tool_args"


def _validate_tool_args_contract(
    *,
    tool_action: str,
    tool_args: Any,
    fallback_tz: str | None = None,
) -> tuple[str | None, str | None]:
    normalized_args, shape_error = validate_tool_args_shape(
        tool_action=tool_action,
        tool_args=tool_args,
    )
    if shape_error:
        return _map_tool_args_shape_error(shape_error)
    tool_args = normalized_args or {}

    def _validate_optional_text(field: str) -> tuple[str | None, str | None]:
        value = tool_args.get(field)
        if value is None:
            return None, None
        if not isinstance(value, str):
            return f"{field}_type_invalid", field
        if not value.strip():
            return f"{field}_empty", field
        return None, None

    def _validate_optional_uuid(field: str) -> tuple[str | None, str | None]:
        value = tool_args.get(field)
        if value is None:
            return None, None
        if not isinstance(value, str):
            return f"{field}_type_invalid", field
        if not value.strip():
            return None, None
        if _parse_uuid(value) is None:
            return f"{field}_invalid", field
        return None, None

    def _validate_optional_datetime(field: str) -> tuple[str | None, str | None]:
        value = tool_args.get(field)
        if value is None:
            return None, None
        if not isinstance(value, str):
            return f"{field}_type_invalid", field
        if not value.strip():
            return None, None
        if _parse_datetime(value, fallback_tz=fallback_tz) is None:
            return f"{field}_invalid", field
        return None, None

    def _validate_optional_duration(field: str) -> tuple[str | None, str | None]:
        value = tool_args.get(field)
        if value is None:
            return None, None
        if isinstance(value, bool):
            return f"{field}_type_invalid", field
        if isinstance(value, (int, float)):
            minutes = int(value)
            if minutes <= 0:
                return f"{field}_non_positive", field
            return None, None
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None, None
            if stripped.isdigit():
                if int(stripped) <= 0:
                    return f"{field}_non_positive", field
                return None, None
            return f"{field}_invalid", field
        return f"{field}_type_invalid", field

    checks: list[tuple[str | None, str | None]] = []
    if tool_action == "calendar.list_slots":
        checks.extend(
            [
                _validate_optional_text("date"),
                # list_slots supports fuzzy values like "завтра" or "18:30";
                # strict datetime parsing is enforced later in slot resolver flow.
                _validate_optional_text("start_at"),
                _validate_optional_duration("duration_min"),
                _validate_optional_text("specialist_id"),
                _validate_optional_text("specialist_name"),
            ]
        )
    elif tool_action == "calendar.book_slot":
        checks.extend(
            [
                _validate_optional_datetime("start_at"),
                _validate_optional_datetime("end_at"),
                _validate_optional_text("specialist_id"),
                _validate_optional_text("specialist_name"),
                _validate_optional_text("customer_name"),
                _validate_optional_text("customer_phone"),
            ]
        )
    elif tool_action == "calendar.get_booking":
        checks.append(_validate_optional_uuid("appointment_id"))
    elif tool_action == "calendar.reschedule":
        checks.extend(
            [
                _validate_optional_uuid("appointment_id"),
                _validate_optional_datetime("start_at"),
                _validate_optional_datetime("end_at"),
            ]
        )
    elif tool_action == "calendar.cancel":
        checks.extend(
            [
                _validate_optional_uuid("appointment_id"),
                _validate_optional_text("reason"),
            ]
        )

    for error_code, field in checks:
        if error_code:
            return error_code, field
    return None, None


def validate_tool_args_contract(
    *,
    tool_action: str,
    tool_args: Any,
    fallback_tz: str | None = None,
) -> tuple[str | None, str | None]:
    return _validate_tool_args_contract(
        tool_action=tool_action,
        tool_args=tool_args,
        fallback_tz=fallback_tz,
    )


def _is_photo_offer_message(text: str | None) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if "фото" not in normalized and "референс" not in normalized:
        return False
    return any(
        token in normalized
        for token in ("пришл", "отправл", "скин", "могу", "можно", "покаж", "прикреп")
    )


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
    requested_time: str | None = None,
    requested_daypart: str | None = None,
    now: datetime | None = None,
) -> tuple[str | None, str | None]:
    if not date_value:
        return None, "missing_date"
    date_parsed = _parse_datetime(
        date_value,
        fallback_tz=branch.timezone if branch else None,
        now=now,
    )
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

    requested_token = requested_time.strip() if isinstance(requested_time, str) else ""
    available_times = sorted(
        {
            token
            for specialist_slots in slots_by_specialist.values()
            for token in specialist_slots
            if isinstance(token, str) and token
        }
    )
    if requested_token:
        if requested_token in available_times:
            return (
                f"Да, на {requested_token} есть свободное окно. "
                f"{_format_slot_list(slots_by_specialist)}"
            ), None
        if available_times:
            return (
                f"На {requested_token} свободного окна нет. "
                f"Доступны: {', '.join(available_times[:5])}."
            ), None
        return f"На {requested_token} свободных окон нет. Могу предложить другое время.", None

    daypart = requested_daypart.strip().casefold() if isinstance(requested_daypart, str) else ""
    if daypart in {"morning", "day", "evening"}:
        daypart_times = [token for token in available_times if _time_token_in_daypart(token, daypart)]
        daypart_label = {"morning": "утро", "day": "день", "evening": "вечер"}[daypart]
        if daypart_times:
            return f"На {daypart_label} доступны: {', '.join(daypart_times[:5])}.", None
        return f"На {daypart_label} свободных окон нет. Могу предложить другое время.", None

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


def _appointment_time_token(appointment: Appointment | None) -> str | None:
    if appointment is None:
        return None
    start_at = getattr(appointment, "start_at", None)
    if not isinstance(start_at, datetime):
        return None
    return start_at.strftime("%H:%M")


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


def _catalog_location(
    client_slug: str | None,
    *,
    message_text: str | None = None,
    info_sections_hint: list[str] | None = None,
) -> tuple[str | None, str | None, dict[str, Any]]:
    if not client_slug:
        return None, "location_missing", {}

    include_parking = bool(
        any(
            isinstance(item, str) and item.strip().lower() == "parking"
            for item in (info_sections_hint or [])
        )
    )
    if message_text:
        normalized = _normalize_text(message_text)
        include_parking = bool(
            include_parking
            or (
                normalized and _has_parking_signal(normalized, client_slug=client_slug)
            )
        )

    reply, meta = build_info_combined_reply(
        include_parking=include_parking,
        client_slug=client_slug,
    )
    if reply:
        return reply, None, meta or {}

    intent = "parking" if include_parking else "location"
    reply = format_reply_from_truth(intent, client_slug=client_slug)
    if reply:
        sections = ["parking"] if include_parking else ["location"]
        return reply, None, {"info_sections": sections}
    return None, "location_missing", {}


def _catalog_portfolio(
    client_slug: str | None,
    *,
    message_text: str | None = None,
) -> tuple[str | None, str | None]:
    truth = load_yaml_truth(client_slug)
    instagram = (
        truth.get("salon", {}).get("instagram") if isinstance(truth, dict) else None
    )
    if instagram:
        prefix = "Примеры работ"
        if _is_photo_offer_message(message_text):
            prefix = "Да, конечно. Пришлите фото, и я помогу сориентировать по услуге.\nПримеры работ"
        return f"{prefix}: {instagram}", None
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
    info_sections_hint: list[str] | None = None,
    message_text: str | None = None,
    expected_reply_type: str | None = None,
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

    tool_args_error, tool_args_field = _validate_tool_args_contract(
        tool_action=tool_action,
        tool_args=tool_args,
    )
    if tool_args_error:
        return ToolExecutionResult(
            handled=True,
            ok=False,
            response_text=(
                "Не получилось обработать запрос автоматически. "
                "Уточните детали, пожалуйста, и я помогу."
            ),
            error_code="tool_args_invalid",
            decision_meta={
                "tool_action": tool_action,
                "tool_decision": "invalid_args",
                "tool_args_checked": True,
                "tool_args_contract": "invalid",
                "tool_args_error": tool_args_error,
                "tool_args_error_field": tool_args_field,
            },
            trace={
                "stage": "tool_registry",
                "decision": "invalid_args",
                "tool_action": tool_action,
                "tool_args_contract": "invalid",
                "tool_args_error": tool_args_error,
                "tool_args_error_field": tool_args_field,
            },
        )

    allow_tokens, deny_tokens, capability_source = _resolve_runtime_tool_policy()
    capability_block_reason = None
    if _is_tool_policy_enforcement_enabled():
        capability_block_reason = _tool_action_block_reason(
            tool_action=tool_action,
            allow_tokens=allow_tokens,
            deny_tokens=deny_tokens,
        )
    if capability_block_reason:
        response_text = (
            "В этом филиале онлайн-календарь для такого запроса отключен. "
            "Передам менеджеру, чтобы помочь вручную."
            if tool_action.startswith("calendar.")
            else "Для этого запроса в данном филиале используется ручная обработка менеджером."
        )
        return ToolExecutionResult(
            handled=True,
            ok=False,
            response_text=response_text,
            error_code="tool_action_disabled",
            decision_meta={
                "tool_action": tool_action,
                "tool_decision": "capability_blocked",
                "capability_reason": capability_block_reason,
                "capability_source": capability_source,
            },
            trace={
                "stage": "tool_registry",
                "decision": "capability_blocked",
                "tool_action": tool_action,
                "capability_reason": capability_block_reason,
                "capability_source": capability_source,
            },
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
        availability_provider = None
        provider_health_reason: str | None = None
        if isinstance(branch.booking_settings, dict):
            availability_provider = branch.booking_settings.get("availability_provider")
            if isinstance(availability_provider, str) and not availability_provider.strip():
                availability_provider = None
        if availability_provider is None:
            runtime = get_runtime_capabilities()
            if runtime:
                availability_provider = runtime.payload.providers.availability_provider
        if availability_provider == "google_calendar":
            health = get_provider_health(
                db,
                client_id=branch.client_id,
                branch_id=branch.id,
            )
            if not health.ready and _calendar_provider_should_block(health.reason):
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
            if not health.ready:
                provider_health_reason = health.reason
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
        requested_time = _extract_time_token(message_text)
        requested_daypart = None if requested_time else _extract_daypart_token(message_text)
        response, error = _list_slots(
            db,
            branch=branch,
            specialist_id=specialist_uuid,
            date_value=raw_date,
            duration_min=duration,
            requested_time=requested_time,
            requested_daypart=requested_daypart,
            now=now,
        )
        if error:
            missing_type = "datetime" if error in {"missing_date", "invalid_date"} else None
            prompt = None
            expected_reply_type = None
            if missing_type == "datetime":
                from app.routers.webhook import _legacy as legacy

                prompt = legacy.MSG_BOOKING_ASK_DATETIME
                time_token = _extract_time_token(message_text)
                if time_token:
                    prompt = f"На какую дату вам удобно, если время {time_token}?"
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
        decision_meta, trace = _with_provider_health_meta(
            {"tool_action": tool_action, "tool_decision": "ok"},
            {"stage": "tool_registry", "decision": "ok", "tool_action": tool_action},
            reason=provider_health_reason,
        )
        return ToolExecutionResult(
            handled=True,
            ok=True,
            response_text=response,
            error_code=None,
            decision_meta=decision_meta,
            trace=trace,
        )

    if tool_action == "calendar.get_booking":
        appointment_id = tool_args.get("appointment_id")
        appointment_uuid = _parse_uuid(appointment_id)
        requested_time = _extract_time_token(message_text)
        appointment, error = _get_booking(
            db,
            appointment_id=appointment_uuid,
            conversation_id=conversation_id,
        )
        if error:
            followup_prompt = _expected_reply_prompt_from_hint(expected_reply_type)
            if _looks_like_booking_verification_message(message_text):
                # For check/confirm requests avoid generic booking-slot followups like
                # "На какую услугу..." that look like semantic reroute.
                followup_prompt = None
            response_parts: list[str] = []
            if requested_time:
                response_parts.append(f"Проверил: пока не вижу подтверждённой записи на {requested_time}.")
            else:
                response_parts.append("Проверил: пока не вижу подтверждённой записи.")
            if _is_photo_offer_message(message_text):
                response_parts.append(
                    "Да, конечно, можно прислать фото/референс. Это поможет менеджеру уточнить детали."
                )
            response_parts.append(
                "Если нужно перенести, подтвердить или отменить запись, "
                "подскажите номер телефона и примерную дату/время, и я помогу найти."
            )
            if followup_prompt:
                response_parts.append(followup_prompt)
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text=" ".join(response_parts),
                error_code=error,
                decision_meta={
                    "tool_action": tool_action,
                    "tool_decision": "not_found",
                    "requested_time": requested_time,
                },
                trace={
                    "stage": "tool_registry",
                    "decision": "not_found",
                    "tool_action": tool_action,
                    "requested_time": requested_time,
                },
            )
        appointment_time = _appointment_time_token(appointment)
        if requested_time and appointment_time and requested_time != appointment_time:
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text=(
                    f"На {requested_time} записи не вижу. "
                    "Хотите проверить другую дату/время или оформить новую запись?"
                ),
                error_code="booking_time_mismatch",
                decision_meta={
                    "tool_action": tool_action,
                    "tool_decision": "time_mismatch",
                    "requested_time": requested_time,
                    "appointment_time": appointment_time,
                },
                trace={
                    "stage": "tool_registry",
                    "decision": "time_mismatch",
                    "tool_action": tool_action,
                    "requested_time": requested_time,
                    "appointment_time": appointment_time,
                },
            )
        return ToolExecutionResult(
            handled=True,
            ok=True,
            response_text=_format_booking_summary(db, appointment),
            error_code=None,
            decision_meta={
                "tool_action": tool_action,
                "tool_decision": "ok",
                "appointment_id": str(appointment.id),
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": tool_action,
                "appointment_id": str(appointment.id),
            },
        )

    if tool_action == "calendar.book_slot":
        provider_health_reason: str | None = None
        health = get_provider_health(
            db,
            client_id=branch.client_id,
            branch_id=branch.id,
        )
        if not health.ready and _calendar_provider_should_block(health.reason):
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
        if not health.ready:
            provider_health_reason = health.reason

        start_at = _parse_datetime(
            tool_args.get("start_at"),
            fallback_tz=branch.timezone,
            now=now,
        )
        end_at = _parse_datetime(
            tool_args.get("end_at"),
            fallback_tz=branch.timezone,
            now=now,
        )
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
            explicit_specialist_requested = bool(
                (isinstance(specialist_id, str) and specialist_id.strip())
                or (isinstance(specialist_name, str) and specialist_name.strip())
            )
            if specialist_error == "specialist_not_found" and not explicit_specialist_requested:
                specialist = None
                specialist_selection = "none_available"
                specialist_error = None
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
            conflict_text = "Этот слот уже занят. Могу предложить другое время."
            if _looks_like_booking_verification_message(message_text):
                conflict_text = (
                    "Подтвердить запись на это время не удалось: слот уже занят. "
                    "Могу предложить другое время."
                )
            else:
                requested_time = _extract_time_token(message_text)
                if not requested_time and isinstance(start_at, datetime):
                    requested_time = start_at.strftime("%H:%M")
                alternative_reply = None
                if isinstance(start_at, datetime):
                    alternative_reply, _ = _list_slots(
                        db,
                        branch=branch,
                        specialist_id=specialist.id if specialist else None,
                        date_value=start_at.isoformat(),
                        duration_min=None,
                        requested_time=requested_time,
                        now=now,
                    )
                if isinstance(alternative_reply, str) and alternative_reply.strip():
                    conflict_text = alternative_reply
                elif requested_time:
                    conflict_text = (
                        f"На {requested_time} слот уже занят. Могу предложить другое время."
                    )
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text=conflict_text,
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
        decision_meta, trace = _with_provider_health_meta(
            {
                "tool_action": tool_action,
                "tool_decision": "ok",
                "appointment_id": str(appointment.id),
                "appointment_status": getattr(appointment, "status", None),
                "reminder_jobs_scheduled": len(scheduled),
                "specialist_id": str(specialist.id) if specialist else None,
                "specialist_name": specialist.name if specialist else None,
                "specialist_selection": specialist_selection,
                "booking_blocked_reason": None,
            },
            {
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": tool_action,
                "appointment_id": str(appointment.id),
                "appointment_status": getattr(appointment, "status", None),
                "reminder_jobs_scheduled": len(scheduled),
                "specialist_id": str(specialist.id) if specialist else None,
                "specialist_selection": specialist_selection,
            },
            reason=provider_health_reason,
        )
        appointment_status_token = str(getattr(appointment, "status", "") or "").strip().casefold()
        if appointment_status_token in {"confirmed", "booked"}:
            response_text = "Запись подтверждена. Хотите что-то изменить?"
        else:
            response_text = "Заявка на запись принята. Менеджер подтвердит время."
        return ToolExecutionResult(
            handled=True,
            ok=True,
            response_text=response_text,
            error_code=None,
            decision_meta=decision_meta,
            trace=trace,
        )

    if tool_action == "calendar.reschedule":
        appointment_id = tool_args.get("appointment_id")
        appointment_uuid = _parse_uuid(appointment_id)
        requested_time = _extract_time_token(message_text)
        appointment, error = _get_booking(
            db,
            appointment_id=appointment_uuid,
            conversation_id=conversation_id,
        )
        if error:
            prefix = f"Время {requested_time} отметил. " if requested_time else ""
            followup_prompt = _expected_reply_prompt_from_hint(expected_reply_type)
            response_text = (
                f"{prefix}Чтобы перенести запись, сначала нужно найти текущую. "
                "Подскажите номер телефона и примерную дату/время записи."
            )
            if followup_prompt:
                response_text = f"{response_text} {followup_prompt}"
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text=response_text,
                error_code=error,
                decision_meta={
                    "tool_action": tool_action,
                    "tool_decision": "not_found",
                    "requested_time": requested_time,
                },
                trace={
                    "stage": "tool_registry",
                    "decision": "not_found",
                    "tool_action": tool_action,
                    "requested_time": requested_time,
                },
            )
        start_at = _parse_datetime(
            tool_args.get("start_at"),
            fallback_tz=branch.timezone,
            now=now,
        )
        end_at = _parse_datetime(
            tool_args.get("end_at"),
            fallback_tz=branch.timezone,
            now=now,
        )
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
                "appointment_id": str(updated.id),
                "reminder_jobs_cancelled": len(cancelled_jobs),
                "reminder_jobs_scheduled": len(scheduled),
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": tool_action,
                "appointment_id": str(updated.id),
                "reminder_jobs_cancelled": len(cancelled_jobs),
                "reminder_jobs_scheduled": len(scheduled),
            },
        )

    if tool_action == "calendar.cancel":
        appointment_id = tool_args.get("appointment_id")
        appointment_uuid = _parse_uuid(appointment_id)
        appointment, error = _get_booking(
            db,
            appointment_id=appointment_uuid,
            conversation_id=conversation_id,
        )
        if error:
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text=(
                    "Чтобы отменить запись, сначала нужно найти текущую. "
                    "Подскажите номер телефона и примерную дату/время записи."
                ),
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
                "appointment_id": str(updated.id),
                "reminder_jobs_cancelled": len(cancelled_jobs),
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": tool_action,
                "appointment_id": str(updated.id),
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
        hint_set = {
            item.strip().lower()
            for item in (info_sections_hint or [])
            if isinstance(item, str) and item.strip()
        }
        duration_hint = bool(hint_set & {"duration", "service_duration"})
        promo_hint = bool(
            hint_set & {"promotions", "promo", "promotion", "discount", "discounts"}
        )
        price_hint = bool(hint_set & {"pricing", "price", "payment", "payment_info"})
        if not service_query:
            from app.routers.webhook import _legacy as legacy

            reply = legacy.MSG_BOOKING_ASK_SERVICE
            info_sections: list[str] = []
            tool_decision = "missing_slot"
            expected_reply_type = legacy.EXPECTED_REPLY_SERVICE
            if _looks_like_services_overview_message(message_text):
                overview_reply = _format_services_overview_reply(
                    db,
                    branch=branch,
                    client_slug=client_slug,
                )
                if overview_reply:
                    reply = overview_reply
                    tool_decision = "services_overview"
                    info_sections = ["services_overview"]
                    expected_reply_type = None
            if client_slug and message_text:
                normalized = _normalize_text(message_text)
                promo_intent = "promotions" if promo_hint else _detect_promotion_intent(
                    normalized, client_slug=client_slug
                )
                duration_signal = duration_hint or _has_duration_signal(
                    normalized, raw_text=message_text, client_slug=client_slug
                )
                price_signal = price_hint or _has_price_signal(
                    normalized, message_text, client_slug=client_slug
                )
                if promo_intent:
                    promo_reply = format_reply_from_truth(
                        "promotions",
                        slots={"promotion_intent": promo_intent},
                        client_slug=client_slug,
                    )
                    if promo_reply:
                        reply = promo_reply
                        info_sections = ["promotions"]
                        tool_decision = "promotions"
                        expected_reply_type = None
                elif duration_signal and price_signal:
                    clarify = format_reply_from_truth(
                        "duration_or_price_clarify",
                        client_slug=client_slug,
                    )
                    duration_reply = _call_pack_adapter(
                        client_slug,
                        "_format_service_duration_reply",
                        None,
                        message=message_text,
                        client_slug=client_slug,
                    )
                    if isinstance(clarify, str) and clarify.strip():
                        reply = clarify
                    elif isinstance(duration_reply, str) and duration_reply.strip():
                        reply = duration_reply
                    info_sections = ["duration", "pricing"]
                elif duration_signal:
                    duration_reply = _call_pack_adapter(
                        client_slug,
                        "_format_service_duration_reply",
                        None,
                        message=message_text,
                        client_slug=client_slug,
                    )
                    if isinstance(duration_reply, str) and duration_reply.strip():
                        reply = duration_reply
                    info_sections = ["duration"]
                elif price_signal:
                    clarify = format_reply_from_truth("service_clarify", client_slug=client_slug)
                    if clarify:
                        reply = clarify
                    info_sections = ["pricing"]

            decision_meta = {
                "tool_action": tool_action,
                "tool_decision": tool_decision,
            }
            trace = {
                "stage": "tool_registry",
                "decision": tool_decision,
                "tool_action": tool_action,
            }
            if tool_decision == "missing_slot":
                decision_meta["missing_slot"] = "service"
                trace["missing_slot"] = "service"
            if info_sections:
                decision_meta["info_sections"] = info_sections
                trace["info_sections"] = info_sections

            return ToolExecutionResult(
                handled=True,
                ok=tool_decision != "missing_slot",
                response_text=reply,
                error_code=None if tool_decision != "missing_slot" else "missing_service",
                decision_meta=decision_meta,
                trace=trace,
                expected_reply_type=expected_reply_type,
            )
        if client_slug and message_text:
            normalized = _normalize_text(message_text)
            message_tokens = set(normalized.split()) if normalized else set()
            inferred_price_item = _call_pack_adapter(
                client_slug,
                "_find_best_price_item",
                message_text,
                client_slug,
            )
            inferred_service_name = None
            if isinstance(inferred_price_item, dict):
                candidate_name = inferred_price_item.get("name")
                if isinstance(candidate_name, str) and candidate_name.strip():
                    inferred_service_name = candidate_name.strip()
            if inferred_service_name:
                inferred_tokens = set(_normalize_text(inferred_service_name).split())
                current_tokens = (
                    set(_normalize_text(service_query).split())
                    if isinstance(service_query, str) and service_query.strip()
                    else set()
                )
                inferred_overlap = bool(inferred_tokens & message_tokens)
                current_overlap = bool(current_tokens & message_tokens)
                if inferred_overlap and (not current_tokens or not current_overlap):
                    service_query = inferred_service_name
            promo_intent = "promotions" if promo_hint else _detect_promotion_intent(
                normalized,
                client_slug=client_slug,
            )
            if promo_intent:
                promo_reply = format_reply_from_truth(
                    "promotions",
                    slots={"promotion_intent": promo_intent},
                    client_slug=client_slug,
                )
                if promo_reply:
                    return ToolExecutionResult(
                        handled=True,
                        ok=True,
                        response_text=promo_reply,
                        error_code=None,
                        decision_meta={
                            "tool_action": tool_action,
                            "tool_decision": "promotions",
                            "info_sections": ["promotions"],
                        },
                        trace={
                            "stage": "tool_registry",
                            "decision": "promotions",
                            "tool_action": tool_action,
                            "info_sections": ["promotions"],
                        },
                    )
            if duration_hint or _has_duration_signal(
                normalized, raw_text=message_text, client_slug=client_slug
            ):
                service_match = (
                    _match_service(
                        _normalize_text(service_query),
                        client_slug or "generic",
                    )
                    if service_query
                    else None
                )
                duration_reply = _call_pack_adapter(
                    client_slug,
                    "_format_service_duration_reply",
                    service_match,
                    message=message_text,
                    service_label=service_query,
                    client_slug=client_slug,
                )
                if duration_reply:
                    return ToolExecutionResult(
                        handled=True,
                        ok=True,
                        response_text=duration_reply,
                        error_code=None,
                        decision_meta={
                            "tool_action": tool_action,
                            "tool_decision": "duration",
                            "info_sections": ["duration"],
                        },
                        trace={
                            "stage": "tool_registry",
                            "decision": "duration",
                            "tool_action": tool_action,
                            "info_sections": ["duration"],
                        },
                    )

        reply, error = _catalog_service_query(
            db,
            branch=branch,
            service_query=service_query,
        )
        if error and client_slug:
            normalized_query = _normalize_text(service_query)
            truth = load_yaml_truth(client_slug)
            service_match = _match_service(normalized_query, client_slug or "generic") if normalized_query else None
            if isinstance(service_match, dict):
                matched_name = service_match.get("name")
                if isinstance(matched_name, str) and matched_name.strip():
                    # Guard against harmful fallback where a different service is selected
                    # without any lexical overlap with the user's explicit query.
                    query_tokens = set(_normalize_text(service_query).split())
                    matched_tokens = set(_normalize_text(matched_name).split())
                    if query_tokens and matched_tokens and not (query_tokens & matched_tokens):
                        service_match = None
            if isinstance(service_match, dict):
                truth_reply = _call_pack_adapter(
                    client_slug,
                    "_format_service_reply",
                    service_match,
                    truth,
                    client_slug,
                )
                if truth_reply:
                    return ToolExecutionResult(
                        handled=True,
                        ok=True,
                        response_text=truth_reply,
                        error_code=None,
                        decision_meta={
                            "tool_action": tool_action,
                            "tool_decision": "truth_fallback",
                            "info_sections": ["pricing"],
                        },
                        trace={
                            "stage": "tool_registry",
                            "decision": "truth_fallback",
                            "tool_action": tool_action,
                            "info_sections": ["pricing"],
                        },
                    )
                service_name = service_match.get("name") if isinstance(service_match, dict) else None
                if isinstance(service_name, str) and service_name.strip():
                    presence = _call_pack_adapter(
                        client_slug,
                        "_format_service_presence_reply_for_name",
                        service_name,
                        client_slug,
                    )
                    if presence:
                        return ToolExecutionResult(
                            handled=True,
                            ok=True,
                            response_text=presence,
                            error_code=None,
                            decision_meta={
                                "tool_action": tool_action,
                                "tool_decision": "presence_fallback",
                            },
                            trace={
                                "stage": "tool_registry",
                                "decision": "presence_fallback",
                                "tool_action": tool_action,
                            },
                        )
            price_item = _call_pack_adapter(
                client_slug,
                "_find_best_price_item",
                message_text or service_query or "",
                client_slug or "generic",
            )
            if isinstance(price_item, dict):
                raw_item = price_item.get("item")
                if isinstance(raw_item, dict):
                    price_reply = _call_pack_adapter(
                        client_slug,
                        "_format_price_reply",
                        raw_item,
                    )
                    if price_reply:
                        return ToolExecutionResult(
                            handled=True,
                            ok=True,
                            response_text=price_reply,
                            error_code=None,
                            decision_meta={
                                "tool_action": tool_action,
                                "tool_decision": "price_item_fallback",
                                "info_sections": ["pricing"],
                            },
                            trace={
                                "stage": "tool_registry",
                                "decision": "price_item_fallback",
                                "tool_action": tool_action,
                                "info_sections": ["pricing"],
                            },
                        )
            not_found = _call_pack_adapter(client_slug, "_format_service_not_found_reply", truth)
            if not_found:
                return ToolExecutionResult(
                    handled=True,
                    ok=True,
                    response_text=not_found,
                    error_code=None,
                    decision_meta={
                        "tool_action": tool_action,
                        "tool_decision": "not_found_fallback",
                        "info_sections": ["pricing"],
                    },
                    trace={
                        "stage": "tool_registry",
                        "decision": "not_found_fallback",
                        "tool_action": tool_action,
                        "info_sections": ["pricing"],
                    },
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
            decision_meta={
                "tool_action": tool_action,
                "tool_decision": "ok",
                "info_sections": ["pricing"],
            },
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": tool_action,
                "info_sections": ["pricing"],
            },
        )

    if tool_action == "catalog.location":
        reply, error, meta = _catalog_location(
            client_slug,
            message_text=message_text,
            info_sections_hint=info_sections_hint,
        )
        if error:
            return ToolExecutionResult(
                handled=True,
                ok=False,
                response_text="Адрес сейчас недоступен. Напишите, пожалуйста, какой район удобен.",
                error_code=error,
                decision_meta={"tool_action": tool_action, "tool_decision": "not_found"},
                trace={"stage": "tool_registry", "decision": "not_found"},
            )
        meta = meta or {}
        if "info_sections" not in meta:
            meta["info_sections"] = ["location"]
        return ToolExecutionResult(
            handled=True,
            ok=True,
            response_text=reply,
            error_code=None,
            decision_meta={**meta, "tool_action": tool_action, "tool_decision": "ok"},
            trace={
                "stage": "tool_registry",
                "decision": "ok",
                "tool_action": tool_action,
                "info_sections": meta.get("info_sections"),
            },
        )

    if tool_action == "catalog.portfolio":
        reply, error = _catalog_portfolio(client_slug, message_text=message_text)
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
