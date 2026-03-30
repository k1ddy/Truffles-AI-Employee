"""Webhook package exports.

Keep the mounted ingress minimal while preserving the narrow compatibility
surface still consumed by tests.
"""

from __future__ import annotations

from app.routers.webhook.booking import (
    _is_booking_slot_signal,
    _match_expected_reply,
    _validate_name_slot,
)
from app.routers.webhook.context_manager import (
    _get_expected_reply_reason,
    _get_expected_reply_type,
    _set_expected_reply_type,
)
from app.routers.webhook.context_runtime import (
    EXPECTED_REPLY_REASON_KEY,
    EXPECTED_REPLY_TYPE_KEY,
)
from app.routers.webhook.dedup import (
    _buffer_user_message,
    _drain_buffered_messages,
    is_duplicate_message_id,
)
from app.routers.webhook.runtime_primitives import (
    EXPECTED_REPLY_NAME,
    EXPECTED_REPLY_TIME,
    ConversationState,
    MSG_BOOKING_CTA,
)

from .http import router
from .response import _apply_quiet_hours_notice, _maybe_append_booking_cta


def __getattr__(name: str):
    if name == "_should_block_expected_reply_by_info":
        from app.routers.webhook.decision import _should_block_expected_reply_by_info

        return _should_block_expected_reply_by_info
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ConversationState",
    "EXPECTED_REPLY_NAME",
    "EXPECTED_REPLY_REASON_KEY",
    "EXPECTED_REPLY_TIME",
    "EXPECTED_REPLY_TYPE_KEY",
    "MSG_BOOKING_CTA",
    "_apply_quiet_hours_notice",
    "_buffer_user_message",
    "_drain_buffered_messages",
    "_get_expected_reply_reason",
    "_get_expected_reply_type",
    "_is_booking_slot_signal",
    "_match_expected_reply",
    "_maybe_append_booking_cta",
    "_set_expected_reply_type",
    "_should_block_expected_reply_by_info",
    "_validate_name_slot",
    "is_duplicate_message_id",
    "router",
]
