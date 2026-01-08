"""CTA/quiet-hours/text assembly helpers."""

from __future__ import annotations


def _maybe_append_booking_cta(
    bot_response: str | None,
    *,
    conversation_state: str,
    allow_booking_flow: bool,
    has_followup: bool = False,
) -> str | None:
    if not bot_response:
        return bot_response
    from . import _legacy as legacy

    if conversation_state != legacy.ConversationState.BOT_ACTIVE.value:
        return bot_response
    if not allow_booking_flow or has_followup:
        return bot_response
    normalized = legacy._normalize_text(bot_response)
    if not normalized or "запис" in normalized:
        return bot_response
    return f"{bot_response}\n\n{legacy.MSG_BOOKING_CTA}"


def _apply_quiet_hours_notice(text: str, notice: str | None) -> str:
    if not text or not notice:
        return text
    from . import _legacy as legacy

    normalized_text = legacy._normalize_text(text)
    normalized_notice = legacy._normalize_text(notice)
    if normalized_notice and normalized_notice in normalized_text:
        return text
    if "салон закрыт" in normalized_text:
        return text
    return f"{notice}\n\n{text}"


__all__ = ["_apply_quiet_hours_notice", "_maybe_append_booking_cta"]
