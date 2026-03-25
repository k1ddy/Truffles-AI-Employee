from __future__ import annotations

from enum import Enum


class Channel(str, Enum):
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    INSTAGRAM = "instagram"
    WEB = "web"


def parse_channel(value: Channel | str | None) -> Channel | None:
    if isinstance(value, Channel):
        return value
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    try:
        return Channel(normalized)
    except ValueError:
        return None


__all__ = ["Channel", "parse_channel"]
