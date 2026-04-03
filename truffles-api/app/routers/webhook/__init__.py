"""Adapter-only webhook package exports.

Keep the mounted ingress minimal: only the real router and non-legacy runtime
primitives load eagerly. Legacy helper names stay available as lazy
compatibility exports for tests and shadow callers, but the package root does
not re-own legacy router behavior.
"""

from __future__ import annotations

from importlib import import_module
from typing import Final

from app.routers.webhook.context_runtime import (
    EXPECTED_REPLY_REASON_KEY,
    EXPECTED_REPLY_TYPE_KEY,
)
from app.routers.webhook.runtime_primitives import (
    EXPECTED_REPLY_NAME,
    EXPECTED_REPLY_TIME,
    MSG_BOOKING_CTA,
    ConversationState,
)

from .http import router

_LAZY_COMPAT_EXPORTS: Final[dict[str, tuple[str, str]]] = {
    "_apply_quiet_hours_notice": (
        "app.routers.webhook.response",
        "_apply_quiet_hours_notice",
    ),
    "_buffer_user_message": (
        "app.routers.webhook.dedup",
        "_buffer_user_message",
    ),
    "_drain_buffered_messages": (
        "app.routers.webhook.dedup",
        "_drain_buffered_messages",
    ),
    "_get_expected_reply_reason": (
        "app.routers.webhook.context_manager",
        "_get_expected_reply_reason",
    ),
    "_get_expected_reply_type": (
        "app.routers.webhook.context_manager",
        "_get_expected_reply_type",
    ),
    "_is_booking_slot_signal": (
        "app.routers.webhook.booking",
        "_is_booking_slot_signal",
    ),
    "_match_expected_reply": (
        "app.routers.webhook.booking",
        "_match_expected_reply",
    ),
    "_maybe_append_booking_cta": (
        "app.routers.webhook.response",
        "_maybe_append_booking_cta",
    ),
    "_set_expected_reply_type": (
        "app.routers.webhook.context_manager",
        "_set_expected_reply_type",
    ),
    "_should_block_expected_reply_by_info": (
        "app.routers.webhook.expected_reply_interrupt_runtime",
        "_should_block_expected_reply_by_info",
    ),
    "_validate_name_slot": (
        "app.routers.webhook.booking",
        "_validate_name_slot",
    ),
    "is_duplicate_message_id": (
        "app.routers.webhook.dedup",
        "is_duplicate_message_id",
    ),
}


def __getattr__(name: str):
    lazy_target = _LAZY_COMPAT_EXPORTS.get(name)
    if lazy_target is not None:
        module_name, attr_name = lazy_target
        return getattr(import_module(module_name), attr_name)
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
