"""Narrow runtime owner for continuity/session context keys and helpers."""

from __future__ import annotations

CONTEXT_MANAGER_KEY = "context_manager"
EXPECTED_REPLY_TYPE_KEY = "expected_reply_type"
EXPECTED_REPLY_REASON_KEY = "expected_reply_reason"
RE_ENTRY_REQUIRED_KEY = "re_entry_required"
REENGAGE_CONFIRM_KEY = "reengage_confirmation"
ASR_CONFIRM_KEY = "asr_confirm_pending"
ASR_INFLIGHT_KEY = "asr_inflight"
STYLE_REFERENCE_PENDING_KEY = "style_reference_pending"
HANDOVER_CONFIRM_WINDOW_MINUTES = 15
REENGAGE_CONFIRM_WINDOW_MINUTES = 15
ASR_CONFIRM_WINDOW_MINUTES = 10
ASR_INFLIGHT_TTL_SECONDS = 90
MEMORY_PROFILE_KEY = "memory_profile"
MEMORY_PENDING_KEY = "memory_pending"
MEMORY_PROFILE_TTL_DAYS = 180
SERVICE_HINT_KEY = "last_service_hint"
SERVICE_HINT_AT_KEY = "last_service_hint_at"
SERVICE_HINT_WINDOW_MINUTES = 120
CLASS_CARRYOVER_KEY = "class_carryover"
CLASS_CARRYOVER_TTL_MESSAGES = 4
CLASS_CARRYOVER_CLASSES = {"info_bundle"}
SERVICE_CARRYOVER_KEY = "service_carryover"
CONSULT_CONTEXT_KEY = "consult_context"
SERVICE_CARRYOVER_SKIP_INTENTS = {
    "service_clarify",
    "duration_or_price_clarify",
    "service_not_found",
}


def _is_refusal_flag_active(refusal_flags: dict | None, field: str) -> bool:
    if not isinstance(refusal_flags, dict):
        return False
    payload = refusal_flags.get(field)
    if isinstance(payload, dict):
        return payload.get("value") is True
    if isinstance(payload, bool):
        return payload
    return False


def _ensure_question_mark(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return ""
    if cleaned.endswith("?"):
        return cleaned
    return f"{cleaned}?"


__all__ = [
    "ASR_CONFIRM_KEY",
    "ASR_CONFIRM_WINDOW_MINUTES",
    "ASR_INFLIGHT_KEY",
    "ASR_INFLIGHT_TTL_SECONDS",
    "CLASS_CARRYOVER_CLASSES",
    "CLASS_CARRYOVER_KEY",
    "CLASS_CARRYOVER_TTL_MESSAGES",
    "CONSULT_CONTEXT_KEY",
    "CONTEXT_MANAGER_KEY",
    "EXPECTED_REPLY_REASON_KEY",
    "EXPECTED_REPLY_TYPE_KEY",
    "HANDOVER_CONFIRM_WINDOW_MINUTES",
    "MEMORY_PENDING_KEY",
    "MEMORY_PROFILE_KEY",
    "MEMORY_PROFILE_TTL_DAYS",
    "REENGAGE_CONFIRM_KEY",
    "REENGAGE_CONFIRM_WINDOW_MINUTES",
    "RE_ENTRY_REQUIRED_KEY",
    "SERVICE_CARRYOVER_KEY",
    "SERVICE_CARRYOVER_SKIP_INTENTS",
    "SERVICE_HINT_AT_KEY",
    "SERVICE_HINT_KEY",
    "SERVICE_HINT_WINDOW_MINUTES",
    "STYLE_REFERENCE_PENDING_KEY",
    "_ensure_question_mark",
    "_is_refusal_flag_active",
]
