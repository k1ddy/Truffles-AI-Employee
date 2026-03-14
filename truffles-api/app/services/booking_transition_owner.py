from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

from app.services.booking_signal_service import normalize_phone_digits as _normalize_phone_digits_impl

DEFAULT_BOOKING_SLOT_ORDER = ("service", "datetime", "name")
NAME_SOURCE_TOOL_ARGS = "tool_args"
NAME_SOURCE_USER_PROFILE = "user_profile"
NAME_SOURCE_MISSING = "missing"
PHONE_SOURCE_TOOL_ARGS = "tool_args"
PHONE_SOURCE_USER_PROFILE = "user_profile"
PHONE_SOURCE_REMOTE_JID = "remote_jid"
PHONE_SOURCE_MISSING = "missing"
BOOKING_TRANSITION_OWNER_V1 = "booking_profile_single_writer_v1"


@dataclass(frozen=True)
class PhoneResolution:
    phone: str | None
    source: str


@dataclass(frozen=True)
class BookingContactResolution:
    name: str | None
    name_source: str
    phone: str | None
    phone_source: str
    missing_fields: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.missing_fields


@dataclass(frozen=True)
class ToolTransitionOwnerResult:
    booking_state: dict[str, Any]
    merged_slots: dict[str, str]
    slot_snapshot_override_keys: set[str]
    booking_state_applied: bool
    booking_has_service: bool
    booking_has_datetime: bool
    booking_has_name: bool
    owner: str = BOOKING_TRANSITION_OWNER_V1


def normalize_phone_digits(value: str | None) -> str | None:
    return _normalize_phone_digits_impl(value)


def resolve_phone_from_remote_jid(remote_jid: str | None) -> str | None:
    if not isinstance(remote_jid, str):
        return None
    local_part = remote_jid.split("@", 1)[0].strip()
    if not local_part:
        return None
    return normalize_phone_digits(local_part)


def resolve_user_phone_for_tool(
    *,
    user_phone: str | None,
    remote_jid: str | None,
) -> PhoneResolution:
    normalized_user_phone = normalize_phone_digits(user_phone)
    if normalized_user_phone:
        return PhoneResolution(phone=normalized_user_phone, source=PHONE_SOURCE_USER_PROFILE)
    fallback_phone = resolve_phone_from_remote_jid(remote_jid)
    if fallback_phone:
        return PhoneResolution(phone=fallback_phone, source=PHONE_SOURCE_REMOTE_JID)
    return PhoneResolution(phone=None, source=PHONE_SOURCE_MISSING)


def resolve_customer_phone(
    *,
    customer_phone: str | None,
    user_phone: str | None,
    user_phone_source: str | None = None,
    user_remote_jid: str | None,
) -> PhoneResolution:
    normalized_customer_phone = normalize_phone_digits(customer_phone)
    if normalized_customer_phone:
        return PhoneResolution(phone=normalized_customer_phone, source=PHONE_SOURCE_TOOL_ARGS)
    normalized_user_phone = normalize_phone_digits(user_phone)
    if normalized_user_phone:
        normalized_source = str(user_phone_source or PHONE_SOURCE_USER_PROFILE).strip().casefold()
        if normalized_source not in {
            PHONE_SOURCE_USER_PROFILE,
            PHONE_SOURCE_REMOTE_JID,
            PHONE_SOURCE_MISSING,
        }:
            normalized_source = PHONE_SOURCE_USER_PROFILE
        return PhoneResolution(phone=normalized_user_phone, source=normalized_source)
    fallback_phone = resolve_phone_from_remote_jid(user_remote_jid)
    if fallback_phone:
        return PhoneResolution(phone=fallback_phone, source=PHONE_SOURCE_REMOTE_JID)
    return PhoneResolution(phone=None, source=PHONE_SOURCE_MISSING)


def resolve_booking_contact_minimum(
    *,
    customer_name: str | None,
    customer_phone: str | None,
    user_name: str | None,
    user_phone: str | None,
    user_phone_source: str | None = None,
    user_remote_jid: str | None,
) -> BookingContactResolution:
    normalized_name = None
    name_source = NAME_SOURCE_MISSING
    if isinstance(customer_name, str) and customer_name.strip():
        normalized_name = customer_name.strip()
        name_source = NAME_SOURCE_TOOL_ARGS
    elif isinstance(user_name, str) and user_name.strip():
        normalized_name = user_name.strip()
        name_source = NAME_SOURCE_USER_PROFILE

    phone_resolution = resolve_customer_phone(
        customer_phone=customer_phone,
        user_phone=user_phone,
        user_phone_source=user_phone_source,
        user_remote_jid=user_remote_jid,
    )
    missing_fields: list[str] = []
    if not normalized_name:
        missing_fields.append("name")
    if not phone_resolution.phone:
        missing_fields.append("phone")
    return BookingContactResolution(
        name=normalized_name,
        name_source=name_source,
        phone=phone_resolution.phone,
        phone_source=phone_resolution.source,
        missing_fields=tuple(missing_fields),
    )


def sync_user_profile_from_booking_args(
    *,
    user: Any,
    tool_args: Mapping[str, Any] | None,
    remote_jid: str | None,
) -> dict[str, Any]:
    if user is None:
        return {"applied": False, "reason": "user_missing"}
    updates: dict[str, Any] = {"applied": False}
    args = tool_args if isinstance(tool_args, Mapping) else {}

    candidate_name = args.get("customer_name")
    if isinstance(candidate_name, str):
        candidate_name = candidate_name.strip()
    else:
        candidate_name = None

    current_name = getattr(user, "name", None)
    if (not isinstance(current_name, str) or not current_name.strip()) and candidate_name:
        setattr(user, "name", candidate_name)
        updates["name_synced"] = True
    else:
        updates["name_synced"] = False

    current_phone = normalize_phone_digits(getattr(user, "phone", None))
    phone_source = "existing"
    phone_value = current_phone
    if not phone_value:
        candidate_phone = normalize_phone_digits(args.get("customer_phone"))
        if candidate_phone:
            phone_value = candidate_phone
            phone_source = PHONE_SOURCE_TOOL_ARGS
        else:
            fallback_phone = resolve_phone_from_remote_jid(remote_jid)
            if fallback_phone:
                phone_value = fallback_phone
                phone_source = PHONE_SOURCE_REMOTE_JID
    if not current_phone and phone_value:
        setattr(user, "phone", phone_value)
        updates["phone_synced"] = True
    else:
        updates["phone_synced"] = False
    updates["phone_source"] = phone_source if phone_value else PHONE_SOURCE_MISSING
    updates["phone_available"] = bool(phone_value)
    updates["applied"] = bool(updates.get("name_synced") or updates.get("phone_synced"))
    return updates


def _extract_slot_snapshot(
    *,
    policy_slot_state: Mapping[str, Any] | None,
    tool_args: Mapping[str, Any] | None,
) -> dict[str, str]:
    slot_snapshot: dict[str, str] = {}
    if isinstance(policy_slot_state, Mapping):
        for key, value in policy_slot_state.items():
            if isinstance(value, str) and value.strip():
                slot_snapshot[str(key)] = value.strip()
    raw_start_at = tool_args.get("start_at") if isinstance(tool_args, Mapping) else None
    if (
        not slot_snapshot.get("datetime")
        and isinstance(raw_start_at, str)
        and raw_start_at.strip()
    ):
        slot_snapshot["datetime"] = raw_start_at.strip()
    return slot_snapshot


def apply_tool_transition_owner(
    *,
    existing_booking_state: Mapping[str, Any] | None,
    policy_slot_state: Mapping[str, Any] | None,
    tool_args: Mapping[str, Any] | None,
    tool_action: str | None,
    tool_decision: str | None = None,
    policy_intent: str | None,
    policy_goal: str | None,
    booking_wants_flow: bool,
    appointment_id: str | None,
    now: datetime,
    slot_order: Sequence[str] = DEFAULT_BOOKING_SLOT_ORDER,
) -> ToolTransitionOwnerResult:
    base_booking_state: dict[str, Any] = (
        dict(existing_booking_state) if isinstance(existing_booking_state, Mapping) else {}
    )
    slot_snapshot = _extract_slot_snapshot(
        policy_slot_state=policy_slot_state,
        tool_args=tool_args,
    )
    normalized_action = str(tool_action or "").strip().casefold()
    normalized_decision = str(tool_decision or "").strip().casefold()
    booking_scope = bool(
        str(policy_intent or "").strip().casefold() == "booking"
        or normalized_action.startswith("calendar.")
        or str(policy_goal or "").strip().casefold() == "booking"
        or booking_wants_flow
    )
    prefer_slot_snapshot_datetime = bool(
        normalized_action.startswith("calendar.")
        or str(policy_intent or "").strip().casefold() == "booking"
        or str(policy_goal or "").strip().casefold() == "booking"
    )
    clear_datetime_after_negative_booking = bool(
        normalized_action == "calendar.book_slot"
        and normalized_decision in {"conflict", "time_mismatch"}
    )
    # Transient provider outages do not invalidate the user-grounded requested time.

    merged_slots: dict[str, str] = {}
    for key in slot_order:
        value = base_booking_state.get(key)
        if isinstance(value, str) and value.strip():
            merged_slots[key] = value.strip()

    slot_snapshot_override_keys: set[str] = set()
    for key, value in slot_snapshot.items():
        if not isinstance(value, str) or not value.strip():
            continue
        if key == "datetime" and prefer_slot_snapshot_datetime:
            slot_snapshot_override_keys.add(key)
            merged_slots[key] = value
        elif not merged_slots.get(key):
            merged_slots[key] = value

    next_booking_state = dict(base_booking_state)
    booking_state_applied = False
    if merged_slots and booking_scope:
        if next_booking_state.get("active") is not True:
            next_booking_state["active"] = True
            next_booking_state.setdefault("started_at", now.isoformat())
            booking_state_applied = True
        for key, value in merged_slots.items():
            if key in slot_snapshot_override_keys or not next_booking_state.get(key):
                if next_booking_state.get(key) != value:
                    booking_state_applied = True
                next_booking_state[key] = value

    if clear_datetime_after_negative_booking:
        if merged_slots.pop("datetime", None) is not None:
            booking_state_applied = True
        if next_booking_state.pop("datetime", None) is not None:
            booking_state_applied = True

    if appointment_id and normalized_action.startswith("calendar."):
        if next_booking_state.get("appointment_id") != appointment_id:
            booking_state_applied = True
        next_booking_state["appointment_id"] = appointment_id

    booking_has_service = bool(
        isinstance(merged_slots.get("service"), str) and merged_slots.get("service").strip()
    )
    booking_has_datetime = bool(
        isinstance(merged_slots.get("datetime"), str) and merged_slots.get("datetime").strip()
    )
    booking_has_name = bool(
        isinstance(merged_slots.get("name"), str) and merged_slots.get("name").strip()
    )
    return ToolTransitionOwnerResult(
        booking_state=next_booking_state,
        merged_slots=merged_slots,
        slot_snapshot_override_keys=slot_snapshot_override_keys,
        booking_state_applied=booking_state_applied,
        booking_has_service=booking_has_service,
        booking_has_datetime=booking_has_datetime,
        booking_has_name=booking_has_name,
    )
