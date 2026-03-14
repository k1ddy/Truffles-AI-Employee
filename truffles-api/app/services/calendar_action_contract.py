from __future__ import annotations

from typing import Literal, TypedDict

from app.services.console_auth import has_console_permission

CalendarActorClass = Literal["manager", "owner_admin", "consultant_bot"]
CalendarBookingActionId = Literal[
    "edit_booking",
    "cancel_booking",
    "mark_completed",
    "mark_no_show",
    "record_follow_up_contacted",
    "record_follow_up_rebooked",
    "manage_follow_up_governance",
    "open_case_from_booking",
]
CalendarBookingBlockedReasonCode = Literal[
    "permission_required",
    "active_status_only",
    "open_no_show_required",
    "follow_up_already_closed",
    "case_link_required",
]

ACTIVE_BOOKING_STATUSES = frozenset(
    {
        "HOLD",
        "PENDING_CONFIRMATION",
        "CONFIRMED",
        "RESCHEDULE_REQUESTED",
        "CHECKED_IN",
    }
)
BOOKING_ACTION_ORDER: tuple[CalendarBookingActionId, ...] = (
    "edit_booking",
    "cancel_booking",
    "mark_completed",
    "mark_no_show",
    "record_follow_up_contacted",
    "record_follow_up_rebooked",
    "manage_follow_up_governance",
    "open_case_from_booking",
)
_ACTIVE_LIFECYCLE_ACTIONS: tuple[CalendarBookingActionId, ...] = (
    "edit_booking",
    "cancel_booking",
    "mark_completed",
    "mark_no_show",
)
_NO_SHOW_FOLLOW_UP_ACTIONS: tuple[CalendarBookingActionId, ...] = (
    "record_follow_up_contacted",
    "record_follow_up_rebooked",
)


class CalendarBlockedActionPayload(TypedDict):
    action_id: CalendarBookingActionId
    reason_code: CalendarBookingBlockedReasonCode


class CalendarActionContractPayload(TypedDict):
    allowed_actions: list[CalendarBookingActionId]
    blocked_actions: list[CalendarBlockedActionPayload]


def _append_blocked(
    blocked_actions: list[CalendarBlockedActionPayload],
    *,
    action_id: CalendarBookingActionId,
    reason_code: CalendarBookingBlockedReasonCode,
) -> None:
    blocked_actions.append(
        {
            "action_id": action_id,
            "reason_code": reason_code,
        }
    )


def build_calendar_booking_action_contract(
    *,
    role: str,
    status: str | None,
    no_show_followup_done: bool,
    case_id: str | None,
) -> CalendarActionContractPayload:
    normalized_status = (status or "").strip().upper()
    can_write_calendar = has_console_permission(role, "calendar", "write")
    can_manage_follow_up_governance = has_console_permission(role, "team", "write")

    allowed_actions: list[CalendarBookingActionId] = []
    blocked_actions: list[CalendarBlockedActionPayload] = []

    lifecycle_block_reason: CalendarBookingBlockedReasonCode = (
        "permission_required" if not can_write_calendar else "active_status_only"
    )
    for action_id in _ACTIVE_LIFECYCLE_ACTIONS:
        if can_write_calendar and normalized_status in ACTIVE_BOOKING_STATUSES:
            allowed_actions.append(action_id)
        else:
            _append_blocked(
                blocked_actions,
                action_id=action_id,
                reason_code=lifecycle_block_reason,
            )

    if can_write_calendar:
        if normalized_status == "NO_SHOW" and not no_show_followup_done:
            allowed_actions.extend(_NO_SHOW_FOLLOW_UP_ACTIONS)
        else:
            follow_up_reason: CalendarBookingBlockedReasonCode = (
                "follow_up_already_closed"
                if normalized_status == "NO_SHOW" and no_show_followup_done
                else "open_no_show_required"
            )
            for action_id in _NO_SHOW_FOLLOW_UP_ACTIONS:
                _append_blocked(
                    blocked_actions,
                    action_id=action_id,
                    reason_code=follow_up_reason,
                )
    else:
        for action_id in _NO_SHOW_FOLLOW_UP_ACTIONS:
            _append_blocked(
                blocked_actions,
                action_id=action_id,
                reason_code="permission_required",
            )

    if can_manage_follow_up_governance:
        if normalized_status == "NO_SHOW" and not no_show_followup_done:
            allowed_actions.append("manage_follow_up_governance")
        else:
            _append_blocked(
                blocked_actions,
                action_id="manage_follow_up_governance",
                reason_code=(
                    "follow_up_already_closed"
                    if normalized_status == "NO_SHOW" and no_show_followup_done
                    else "open_no_show_required"
                ),
            )
    else:
        _append_blocked(
            blocked_actions,
            action_id="manage_follow_up_governance",
            reason_code="permission_required",
        )

    if can_write_calendar and case_id:
        allowed_actions.append("open_case_from_booking")
    elif not can_write_calendar:
        _append_blocked(
            blocked_actions,
            action_id="open_case_from_booking",
            reason_code="permission_required",
        )
    else:
        _append_blocked(
            blocked_actions,
            action_id="open_case_from_booking",
            reason_code="case_link_required",
        )

    allowed_actions = [action_id for action_id in BOOKING_ACTION_ORDER if action_id in allowed_actions]
    blocked_actions = [
        payload
        for action_id in BOOKING_ACTION_ORDER
        for payload in blocked_actions
        if payload["action_id"] == action_id
    ]
    return {
        "allowed_actions": allowed_actions,
        "blocked_actions": blocked_actions,
    }


def get_calendar_actor_class_for_role(role: str | None) -> CalendarActorClass:
    normalized = str(role or "").strip().lower()
    if normalized == "consultant_bot":
        return "consultant_bot"
    if normalized in {"platform_admin", "owner", "admin"}:
        return "owner_admin"
    return "manager"
