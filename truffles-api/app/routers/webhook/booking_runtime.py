"""Booking-only helper residue moved out of decision.py."""

from __future__ import annotations

import re

from app.services.ai_service import normalize_for_matching
from app.services.pack_runtime_service import load_yaml_truth

from .policy import _detect_booking_cancel

MSG_BOOKING_ASK_ALL = "Чтобы записать, пожалуйста, напишите: услуга, точная дата, точное время, имя, контактный номер."
MSG_BOOKING_SLOT_LOCK_STUB = "Я помогаю только по вопросам салона и записи."
MSG_BOOKING_CANCELLED = "Хорошо, если передумаете — пишите."
MSG_BOOKING_REENGAGE = "Хотите продолжить запись? Если да — напишите услугу."
NAME_PATTERN = re.compile(r"\bменя зовут\s+([a-zа-яё-]{2,})", re.IGNORECASE)
NAME_NOISE_TOKENS = {"меня", "зовут", "это", "я", "имя"}


def _matches_guest_policy_lexicon(
    message_text: str | None,
    *,
    client_slug: str | None,
) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    truth = load_yaml_truth(client_slug)
    domain_pack = truth.get("domain_pack") if isinstance(truth, dict) else None
    lexicon = domain_pack.get("guest_policy_lexicon") if isinstance(domain_pack, dict) else None
    if not isinstance(lexicon, dict):
        return False
    for lang_key in ("ru", "kk"):
        phrases = lexicon.get(lang_key)
        if not isinstance(phrases, list):
            continue
        for phrase in phrases:
            if not isinstance(phrase, str):
                continue
            candidate = normalize_for_matching(phrase)
            if candidate and candidate in normalized:
                return True
    return False


def _is_booking_cancel(text: str, *, policy_pack: dict | None) -> bool:
    return _detect_booking_cancel(text, policy_pack=policy_pack)


__all__ = [
    "MSG_BOOKING_ASK_ALL",
    "MSG_BOOKING_CANCELLED",
    "MSG_BOOKING_REENGAGE",
    "MSG_BOOKING_SLOT_LOCK_STUB",
    "NAME_NOISE_TOKENS",
    "NAME_PATTERN",
    "_is_booking_cancel",
    "_matches_guest_policy_lexicon",
]
