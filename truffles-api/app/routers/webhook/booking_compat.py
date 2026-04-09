"""Compatibility-only booking helper exports."""

from __future__ import annotations

from app.services.pack_runtime_service import _normalize_text, get_system_lexicon_list


def _looks_like_booking_reschedule_request(
    message_text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    del client_slug
    normalized = _normalize_text(message_text or "")
    if not normalized:
        return False
    reschedule_markers = get_system_lexicon_list("booking_reschedule_keywords")
    if any(marker in normalized for marker in reschedule_markers):
        return True
    booking_reference_markers = get_system_lexicon_list("booking_request")
    booking_keyword_markers = get_system_lexicon_list("booking_keywords")
    has_booking_reference = any(marker in normalized for marker in booking_reference_markers) or any(
        marker in normalized for marker in booking_keyword_markers
    )
    if not has_booking_reference:
        return False
    cancel_markers = get_system_lexicon_list("booking_cancel_keywords")
    return any(marker in normalized for marker in cancel_markers)


__all__ = ["_looks_like_booking_reschedule_request"]
