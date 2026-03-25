"""Legacy webhook adapter: re-export decision orchestrator symbols."""

from __future__ import annotations

from app.routers.webhook.context_manager import _apply_consult_return
from app.routers.webhook.response import _apply_quiet_hours_notice, _maybe_append_booking_cta
from app.routers.webhook.runtime_primitives import (
    BOOKING_CTA_SERVICE_INTENTS,
    BOOKING_TIME_SERVICE_INTENTS,
    EXPECTED_REPLY_INTENT_CHOICE,
    EXPECTED_REPLY_NAME,
    EXPECTED_REPLY_PHONE,
    EXPECTED_REPLY_SERVICE,
    EXPECTED_REPLY_TIME,
    INFO_ANCHOR_GROUPS,
    INFO_INTENT_PRIORITY_GENERIC,
    INFO_INTENT_PRIORITY_SERVICE,
    INFO_INTENTS,
    INFO_NON_SERVICE_INTENTS,
    INFO_SERVICE_DEPENDENT_INTENTS,
    MSG_AI_ERROR,
    MSG_BOOKING_ASK_DATETIME,
    MSG_BOOKING_ASK_NAME,
    MSG_BOOKING_ASK_SERVICE,
    MSG_BOOKING_CTA,
    MSG_BOOKING_PENDING_QUESTION_TIME_GUIDANCE,
    MSG_BOOKING_SPECIALIST_AVAILABILITY_FOLLOWUP,
    MSG_DELIVERY_FAILED,
    MSG_EXPECTED_SERVICE_OFF_TOPIC,
    QUESTION_WORD_PREFIXES,
    SERVICE_CARRYOVER_TTL_MESSAGES,
    SESSION_MEMORY_SHORT_TOKENS,
    ConversationState,
)
from app.services.chatflow_service import send_bot_response
from app.services.handover_owner_service import (
    _create_pending_escalation_with_notification as _handover_owner_create_pending_escalation_with_notification,
    _reuse_active_handover as _handover_owner_reuse_active_handover,
    escalate_to_pending as _handover_owner_escalate_to_pending,
    get_active_handover as _handover_owner_get_active_handover,
    manager_reassign as _handover_owner_manager_reassign,
    manager_reopen as _handover_owner_manager_reopen,
    manager_resolve as _handover_owner_manager_resolve,
    manager_return as _handover_owner_manager_return,
    manager_take as _handover_owner_manager_take,
    resolve_active_handover_rejection as _handover_owner_resolve_active_handover_rejection,
)

from . import decision as _decision

_SHARED_EXPORTS = {
    "BOOKING_CTA_SERVICE_INTENTS": BOOKING_CTA_SERVICE_INTENTS,
    "BOOKING_TIME_SERVICE_INTENTS": BOOKING_TIME_SERVICE_INTENTS,
    "ConversationState": ConversationState,
    "EXPECTED_REPLY_INTENT_CHOICE": EXPECTED_REPLY_INTENT_CHOICE,
    "EXPECTED_REPLY_NAME": EXPECTED_REPLY_NAME,
    "EXPECTED_REPLY_PHONE": EXPECTED_REPLY_PHONE,
    "EXPECTED_REPLY_SERVICE": EXPECTED_REPLY_SERVICE,
    "EXPECTED_REPLY_TIME": EXPECTED_REPLY_TIME,
    "INFO_ANCHOR_GROUPS": INFO_ANCHOR_GROUPS,
    "INFO_INTENTS": INFO_INTENTS,
    "INFO_INTENT_PRIORITY_GENERIC": INFO_INTENT_PRIORITY_GENERIC,
    "INFO_INTENT_PRIORITY_SERVICE": INFO_INTENT_PRIORITY_SERVICE,
    "INFO_NON_SERVICE_INTENTS": INFO_NON_SERVICE_INTENTS,
    "INFO_SERVICE_DEPENDENT_INTENTS": INFO_SERVICE_DEPENDENT_INTENTS,
    "MSG_AI_ERROR": MSG_AI_ERROR,
    "MSG_BOOKING_ASK_DATETIME": MSG_BOOKING_ASK_DATETIME,
    "MSG_BOOKING_ASK_NAME": MSG_BOOKING_ASK_NAME,
    "MSG_BOOKING_PENDING_QUESTION_TIME_GUIDANCE": MSG_BOOKING_PENDING_QUESTION_TIME_GUIDANCE,
    "MSG_BOOKING_SPECIALIST_AVAILABILITY_FOLLOWUP": MSG_BOOKING_SPECIALIST_AVAILABILITY_FOLLOWUP,
    "MSG_BOOKING_ASK_SERVICE": MSG_BOOKING_ASK_SERVICE,
    "MSG_BOOKING_CTA": MSG_BOOKING_CTA,
    "MSG_DELIVERY_FAILED": MSG_DELIVERY_FAILED,
    "MSG_EXPECTED_SERVICE_OFF_TOPIC": MSG_EXPECTED_SERVICE_OFF_TOPIC,
    "QUESTION_WORD_PREFIXES": QUESTION_WORD_PREFIXES,
    "SERVICE_CARRYOVER_TTL_MESSAGES": SERVICE_CARRYOVER_TTL_MESSAGES,
    "SESSION_MEMORY_SHORT_TOKENS": SESSION_MEMORY_SHORT_TOKENS,
}

globals().update(_SHARED_EXPORTS)

for _name, _value in _decision.__dict__.items():
    if _name.startswith("__") or _name in _SHARED_EXPORTS:
        continue
    globals()[_name] = _value

globals().update(
    {
        "get_active_handover": _handover_owner_get_active_handover,
        "_reuse_active_handover": _handover_owner_reuse_active_handover,
        "_create_pending_escalation_with_notification": (
            _handover_owner_create_pending_escalation_with_notification
        ),
        "escalate_to_pending": _handover_owner_escalate_to_pending,
        "manager_take": _handover_owner_manager_take,
        "manager_reassign": _handover_owner_manager_reassign,
        "manager_resolve": _handover_owner_manager_resolve,
        "manager_return": _handover_owner_manager_return,
        "manager_reopen": _handover_owner_manager_reopen,
        "resolve_active_handover_rejection": _handover_owner_resolve_active_handover_rejection,
    }
)

del _decision
del _SHARED_EXPORTS

__all__ = [name for name in globals() if not name.startswith("__")]
