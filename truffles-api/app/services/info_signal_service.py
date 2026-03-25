"""Signal helpers for info/lexicon matching (routing-neutral)."""

from __future__ import annotations

import re
from functools import lru_cache
from collections.abc import Callable, Iterable

from app.services.ai_service import normalize_for_matching
from app.services.booking_signal_service import (
    extract_relative_date_token,
    extract_time_token,
    has_explicit_date_signal,
    has_pending_time_question_marker,
    normalize_resolved_datetime_value,
)
from app.services.pack_runtime_default import (
    _detect_promotion_intent,
    _has_contact_signal,
    _has_duration_signal,
    _has_parking_signal,
    _has_price_signal,
    get_pack_service_hint,
)
from app.services.pack_runtime_service import (
    MasterIntentResolution,
    _normalize_text,
    resolve_master_intent,
    get_signal_lexicon_list,
    get_system_lexicon_list,
)
from app.services.signal_manifest_service import get_info_regex_pattern

_TOKENIZE_WORD_RE = get_info_regex_pattern("tokenize_word_pattern") or re.compile(r"\w+")
_CONTACT_QUERY_PATTERNS = (
    re.compile(r"\bкак(?:\s+\w+){0,3}\s+связ"),
    re.compile(r"\bкуда(?:\s+\w+){0,3}\s+напис"),
    re.compile(r"\bконтактн\w*\s+(?:номер|тел(?:ефон)?)\b"),
    re.compile(
        r"\b(?:ваш|ваша|ваше|ваши)\b(?:\s+\w+){0,4}\s+"
        r"(?:номер|тел(?:ефон)?|контакт|whatsapp|instagram|telegram|ватсап\w*|вацап\w*|инстаграм\w*|телеграм\w*)\b"
    ),
    re.compile(
        r"\bу\s+вас\b(?:\s+\w+){0,4}\s+"
        r"(?:номер|тел(?:ефон)?|whatsapp|instagram|telegram|ватсап\w*|вацап\w*|инстаграм\w*|телеграм\w*)\b"
    ),
    re.compile(
        r"\b(?:подскажите|скиньте|дайте)\b(?:\s+\w+){0,4}\s+"
        r"(?:номер|тел(?:ефон)?|whatsapp|instagram|telegram|ватсап\w*|вацап\w*|инстаграм\w*|телеграм\w*)\b"
    ),
)
_CONTACT_OFFTOPIC_PATTERNS = (
    re.compile(r"\bинтеграц"),
    re.compile(r"\bподключ"),
    re.compile(r"\bcrm\b"),
    re.compile(r"\bбитрикс"),
    re.compile(r"\bамо\b"),
    re.compile(
        r"\bработа\w*\s+с\b(?:\s+\w+){0,2}\b"
        r"(?:whatsapp|instagram|telegram|ватсап\w*|вацап\w*|инстаграм\w*|телеграм\w*)\b"
    ),
    re.compile(
        r"\b(?:whatsapp|instagram|telegram|ватсап\w*|вацап\w*|инстаграм\w*|телеграм\w*)\b"
        r"(?:\s+\w+){0,2}\bработа\w*"
    ),
)


@lru_cache(maxsize=None)
def _system_token_tuple(key: str) -> tuple[str, ...]:
    return tuple(get_system_lexicon_list(key))


def _location_question_prefixes() -> tuple[str, ...]:
    return _system_token_tuple("location_question_prefixes")


def _deictic_time_phrases() -> tuple[str, ...]:
    return _system_token_tuple("deictic_time_phrases")


def _deictic_day_phrases() -> tuple[str, ...]:
    return _system_token_tuple("deictic_day_phrases")


def _deictic_time_availability_prefixes() -> tuple[str, ...]:
    return _system_token_tuple("deictic_time_availability_prefixes")


def _specialist_availability_prefixes() -> tuple[str, ...]:
    return _system_token_tuple("specialist_availability_prefixes")


def _specialist_date_range_followup_phrases() -> tuple[str, ...]:
    return _system_token_tuple("specialist_date_range_followup_phrases")


def _weekday_prefixes() -> tuple[str, ...]:
    return _system_token_tuple("weekday_prefixes")


def _weekend_prefixes() -> tuple[str, ...]:
    return _system_token_tuple("weekend_prefixes")


def _availability_confirmation_prefixes() -> tuple[str, ...]:
    return _system_token_tuple("availability_confirmation_prefixes")


def tokenize_for_matching(normalized: str) -> list[str]:
    return _TOKENIZE_WORD_RE.findall(normalized)


def has_token_prefix(tokens: list[str], prefix: str) -> bool:
    return any(token.startswith(prefix) for token in tokens)


def tokens_have_prefixes(tokens: list[str], prefixes: Iterable[str]) -> bool:
    return any(has_token_prefix(tokens, prefix) for prefix in prefixes)


def has_anchor_prefix(tokens: list[str], prefix: str) -> bool:
    # Short stems require exact token match to avoid prefix false positives.
    if len(prefix) <= 2:
        return any(token == prefix for token in tokens)
    return any(token.startswith(prefix) for token in tokens)


def anchor_group_hit(tokens: list[str], group: tuple[str, ...]) -> bool:
    return all(has_anchor_prefix(tokens, prefix) for prefix in group)


def count_anchor_hits(tokens: list[str], groups: list[tuple[str, ...]]) -> int:
    hits = 0
    for group in groups:
        if anchor_group_hit(tokens, group):
            hits += 1
    return hits


def signal_phrase_list(client_slug: str | None, *keys: str) -> list[str]:
    phrases: list[str] = []
    for key in keys:
        values = get_signal_lexicon_list(client_slug, key)
        if not values:
            continue
        for phrase in values:
            token = phrase.strip() if isinstance(phrase, str) else ""
            if token and token not in phrases:
                phrases.append(token)
    return phrases


def normalized_contains_any(normalized: str, phrases: Iterable[str]) -> bool:
    if not normalized:
        return False
    return any(phrase and phrase in normalized for phrase in phrases)


def signal_any_match(normalized: str, client_slug: str | None, *keys: str) -> bool:
    if not keys:
        return False
    phrases = signal_phrase_list(client_slug, *keys)
    return bool(phrases) and normalized_contains_any(normalized, phrases)


def signal_all_match(normalized: str, client_slug: str | None, key: str) -> bool:
    phrases = signal_phrase_list(client_slug, key)
    return bool(phrases) and all(phrase in normalized for phrase in phrases)


def split_relative_date_daypart_suffix(
    normalized_datetime_value: str | None,
    relative_date_token: str | None,
) -> str | None:
    if not isinstance(normalized_datetime_value, str) or not normalized_datetime_value.strip():
        return None
    if not isinstance(relative_date_token, str) or not relative_date_token.strip():
        return None
    normalized_datetime_parts = normalized_datetime_value.split(maxsplit=1)
    if len(normalized_datetime_parts) != 2:
        return None
    if normalized_datetime_parts[0] != relative_date_token:
        return None
    daypart_suffix = normalized_datetime_parts[1].strip()
    return daypart_suffix or None


def signal_pair_match(
    normalized: str,
    client_slug: str | None,
    key_a: str,
    key_b: str,
) -> bool:
    phrases_a = signal_phrase_list(client_slug, key_a)
    phrases_b = signal_phrase_list(client_slug, key_b)
    if not phrases_a or not phrases_b:
        return False
    return normalized_contains_any(normalized, phrases_a) and normalized_contains_any(normalized, phrases_b)


def system_any_match(normalized: str, key: str) -> bool:
    phrases = get_system_lexicon_list(key)
    return bool(phrases) and normalized_contains_any(normalized, phrases)


def system_any_match_multi(normalized: str, *keys: str) -> bool:
    return any(system_any_match(normalized, key) for key in keys)


def is_short_reply(message_text: str | None, *, max_tokens: int) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    tokens = tokenize_for_matching(normalized)
    return 0 < len(tokens) <= max_tokens


def looks_like_services_overview_message(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if any(marker in normalized for marker in ("акци", "скидк", "промо")) and not any(
        marker in normalized for marker in ("услуг", "процед", "сервис")
    ):
        return False
    markers = get_signal_lexicon_list(client_slug, "services_overview_phrases")
    if not markers:
        markers = get_system_lexicon_list("services_overview_phrases")
    if bool(markers and normalized_contains_any(normalized, markers)):
        return True
    return bool(
        (
            "информац" in normalized
            or "какие" in normalized
            or "что у вас" in normalized
        )
        and any(marker in normalized for marker in ("услуг", "процед", "сервис"))
    )


def looks_like_booking_verification_message(text: str | None) -> bool:
    if not text:
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    keywords = get_system_lexicon_list("booking_verification_keywords")
    return bool(keywords and normalized_contains_any(normalized, keywords))


def looks_like_booking_confirmation_message(text: str | None) -> bool:
    if not text:
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    keywords = get_system_lexicon_list("booking_confirmation_keywords")
    return bool(keywords and normalized_contains_any(normalized, keywords))


def detect_booking_verification_mode(text: str | None) -> str | None:
    if not looks_like_booking_verification_message(text):
        return None
    if looks_like_booking_confirmation_message(text):
        return "confirm"
    return "check"


def detect_location_policy_pack_refs(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> tuple[str, ...]:
    if not isinstance(text, str) or not text.strip():
        return ()
    normalized = _normalize_text(text)
    if not normalized:
        return ()
    tokens = tokenize_for_matching(normalized)
    question_like = "?" in text
    if not question_like and tokens:
        question_like = tokens_have_prefixes(tokens, _location_question_prefixes())
    parking_signal = _has_parking_signal(normalized, client_slug=client_slug)
    location_signal = parking_signal or signal_any_match(
        normalized,
        client_slug,
        "location_keywords",
        "location_phrases",
    )
    if (
        question_like
        and tokens_have_prefixes(tokens, _location_question_prefixes())
        and signal_any_match(normalized, client_slug, "location_question_scope_terms")
    ):
        location_signal = True
    if not location_signal and not parking_signal:
        return ()
    refs: list[str] = []
    if location_signal:
        refs.append("location")
    if parking_signal:
        refs.append("parking")
    return tuple(refs)


def looks_like_hours_policy_message(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if _has_parking_signal(normalized, client_slug=client_slug):
        return False
    if signal_any_match(
        normalized,
        client_slug,
        "location_keywords",
        "location_phrases",
        "location_question_scope_terms",
    ):
        return False
    if signal_any_match(normalized, client_slug, "hours_question_phrases", "hours_keywords"):
        return True
    return signal_any_match(
        normalized,
        client_slug,
        "info_hours_stems",
    ) and signal_any_match(
        normalized,
        client_slug,
        "info_time_markers",
        "hours_question_time_phrases",
        "hours_question_work_verbs",
        "hours_question_work_singular",
    )


def looks_like_promotions_policy_message(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    generic_promo_marker = any(marker in normalized for marker in ("акци", "скидк", "промо"))
    if signal_any_match(normalized, client_slug, "promotions_stacking_phrases"):
        return False
    if signal_all_match(normalized, client_slug, "promotions_stacking_terms"):
        return False
    if detect_location_policy_pack_refs(text, client_slug=client_slug):
        return False
    if looks_like_hours_policy_message(text, client_slug=client_slug):
        return False
    if _has_price_signal(normalized, text, client_slug=client_slug):
        return False
    if _has_duration_signal(normalized, text, client_slug=client_slug):
        return False
    if _detect_promotion_intent(normalized, client_slug=client_slug) is not None:
        return True
    if generic_promo_marker:
        return True
    if looks_like_services_overview_message(text, client_slug=client_slug):
        return False
    from app.routers.webhook.policy import _looks_like_promotions_request

    return _looks_like_promotions_request(text, client_slug=client_slug)


def looks_like_promotions_rules_policy_message(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if looks_like_services_overview_message(text, client_slug=client_slug):
        return False
    if detect_location_policy_pack_refs(text, client_slug=client_slug):
        return False
    if looks_like_hours_policy_message(text, client_slug=client_slug):
        return False
    if _has_price_signal(normalized, text, client_slug=client_slug):
        return False
    if _has_duration_signal(normalized, text, client_slug=client_slug):
        return False
    if get_pack_service_hint(text, client_slug=client_slug):
        return False
    return signal_any_match(
        normalized,
        client_slug,
        "promotions_stacking_phrases",
    ) or signal_all_match(
        normalized,
        client_slug,
        "promotions_stacking_terms",
    )


def looks_like_contact_policy_message(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if looks_like_services_overview_message(text, client_slug=client_slug):
        return False
    if detect_location_policy_pack_refs(text, client_slug=client_slug):
        return False
    if looks_like_hours_policy_message(text, client_slug=client_slug):
        return False
    if looks_like_promotions_rules_policy_message(text, client_slug=client_slug):
        return False
    if looks_like_promotions_policy_message(text, client_slug=client_slug):
        return False
    if _has_price_signal(normalized, text, client_slug=client_slug):
        return False
    if _has_duration_signal(normalized, text, client_slug=client_slug):
        return False
    if system_any_match(normalized, "offtopic_keywords"):
        return False
    if any(pattern.search(normalized) for pattern in _CONTACT_OFFTOPIC_PATTERNS):
        return False
    if not _has_contact_signal(normalized, None, client_slug=client_slug):
        return False
    return any(pattern.search(normalized) for pattern in _CONTACT_QUERY_PATTERNS)


def detect_portfolio_policy_service_query(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> tuple[bool, str | None]:
    if not isinstance(text, str) or not text.strip():
        return False, None
    normalized = _normalize_text(text)
    if not normalized:
        return False, None
    if looks_like_services_overview_message(text, client_slug=client_slug):
        return False, None
    if detect_location_policy_pack_refs(text, client_slug=client_slug):
        return False, None
    if looks_like_hours_policy_message(text, client_slug=client_slug):
        return False, None
    if looks_like_promotions_rules_policy_message(text, client_slug=client_slug):
        return False, None
    if looks_like_promotions_policy_message(text, client_slug=client_slug):
        return False, None
    if looks_like_contact_policy_message(text, client_slug=client_slug):
        return False, None
    if _has_price_signal(normalized, text, client_slug=client_slug):
        return False, None
    if re.search(r"\bскольк\w*(?:\s+\w+){0,3}\s+это\s+(?:будет|стоит)\b", normalized):
        return False, None
    if _has_duration_signal(normalized, text, client_slug=client_slug):
        return False, None
    if detect_grounded_pricing_service_query(text, client_slug=client_slug):
        return False, None
    if detect_grounded_duration_service_query(text, client_slug=client_slug):
        return False, None
    markers = get_signal_lexicon_list(client_slug, "portfolio_question_keywords")
    if not markers:
        markers = get_system_lexicon_list("portfolio_question_keywords")
    if not markers or not normalized_contains_any(normalized, markers):
        return False, None
    service_query = get_pack_service_hint(text, client_slug=client_slug)
    if not isinstance(service_query, str):
        return True, None
    service_query = service_query.strip()
    return True, service_query or None


def detect_grounded_master_service_query(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> str | None:
    resolution = _resolve_master_policy_resolution(text, client_slug=client_slug)
    if resolution is None or resolution.needs_service_clarify:
        return None
    if resolution.reason not in {
        "direct_signal",
        "person_action_signal",
        "question_person_signal",
        "person_service_signal",
    }:
        return None
    service_query = resolution.service_query
    if not isinstance(service_query, str):
        return None
    service_query = service_query.strip()
    return service_query or None


def detect_service_choice_specialist_weekend_followup_service_query(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    normalized = _normalize_text(text or "")
    if not normalized:
        return None
    tokens = tokenize_for_matching(normalized)
    if not tokens_have_prefixes(tokens, _weekend_prefixes()):
        return None
    if not all(
        (
            not looks_like_services_overview_message(text, client_slug=client_slug),
            not detect_location_policy_pack_refs(text, client_slug=client_slug),
            not looks_like_promotions_rules_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_policy_message(text, client_slug=client_slug),
            not looks_like_contact_policy_message(text, client_slug=client_slug),
        )
    ):
        return None
    if not all(
        (
            not extract_time_token(text),
            not _has_price_signal(normalized, text, client_slug=client_slug),
            not _has_duration_signal(normalized, text, client_slug=client_slug),
            not signal_any_match(
                normalized,
                client_slug,
                "booking_reschedule_keywords",
                "booking_cancel_keywords",
            ),
        )
    ):
        return None
    resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    if not resolution.explicit or resolution.needs_service_clarify:
        return None
    if resolution.reason != "direct_signal":
        return None
    service_query = resolution.service_query
    if not isinstance(service_query, str):
        return None
    service_query = service_query.strip()
    return service_query or None


def detect_service_choice_specialist_weekday_followup_service_query(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    normalized = _normalize_text(text or "")
    if not normalized:
        return None
    tokens = tokenize_for_matching(normalized)
    if not tokens_have_prefixes(tokens, _weekday_prefixes()):
        return None
    if normalize_resolved_datetime_value(text, normalized_text=normalized):
        return None
    if not all(
        (
            not looks_like_services_overview_message(text, client_slug=client_slug),
            not detect_location_policy_pack_refs(text, client_slug=client_slug),
            not looks_like_promotions_rules_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_policy_message(text, client_slug=client_slug),
            not looks_like_contact_policy_message(text, client_slug=client_slug),
        )
    ):
        return None
    if not all(
        (
            not extract_time_token(text),
            not _has_price_signal(normalized, text, client_slug=client_slug),
            not _has_duration_signal(normalized, text, client_slug=client_slug),
            not signal_any_match(
                normalized,
                client_slug,
                "booking_reschedule_keywords",
                "booking_cancel_keywords",
            ),
        )
    ):
        return None
    resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    if not resolution.explicit or resolution.needs_service_clarify:
        return None
    if resolution.reason != "direct_signal":
        return None
    service_query = resolution.service_query
    if not isinstance(service_query, str):
        return None
    service_query = service_query.strip()
    return service_query or None


def detect_service_choice_specialist_day_followup_service_query(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    normalized = _normalize_text(text or "")
    if not normalized:
        return None
    relative_date_token = extract_relative_date_token(text)
    if not isinstance(relative_date_token, str) or not relative_date_token.strip():
        return None
    normalized_datetime_value = normalize_resolved_datetime_value(
        text,
        normalized_text=normalized,
    )
    if normalized_datetime_value != relative_date_token:
        return None
    tokens = tokenize_for_matching(normalized)
    if tokens_have_prefixes(tokens, _weekend_prefixes()) or tokens_have_prefixes(
        tokens, _weekday_prefixes()
    ):
        return None
    if not all(
        (
            not looks_like_services_overview_message(text, client_slug=client_slug),
            not detect_location_policy_pack_refs(text, client_slug=client_slug),
            not looks_like_hours_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_rules_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_policy_message(text, client_slug=client_slug),
            not looks_like_contact_policy_message(text, client_slug=client_slug),
        )
    ):
        return None
    if not all(
        (
            not extract_time_token(text),
            not _has_price_signal(normalized, text, client_slug=client_slug),
            not _has_duration_signal(normalized, text, client_slug=client_slug),
            not signal_any_match(
                normalized,
                client_slug,
                "booking_reschedule_keywords",
                "booking_cancel_keywords",
            ),
        )
    ):
        return None
    resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    if not resolution.explicit or resolution.needs_service_clarify:
        return None
    if resolution.reason != "direct_signal":
        return None
    service_query = resolution.service_query
    if not isinstance(service_query, str):
        return None
    service_query = service_query.strip()
    return service_query or None


def detect_service_choice_specialist_daypart_followup(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> tuple[str, str] | None:
    if not isinstance(text, str) or not text.strip():
        return None
    normalized = _normalize_text(text or "")
    if not normalized:
        return None
    relative_date_token = extract_relative_date_token(text)
    if not isinstance(relative_date_token, str) or not relative_date_token.strip():
        return None
    normalized_datetime_value = normalize_resolved_datetime_value(
        text,
        normalized_text=normalized,
    )
    if not isinstance(normalized_datetime_value, str) or not normalized_datetime_value.strip():
        return None
    daypart_suffix = split_relative_date_daypart_suffix(
        normalized_datetime_value,
        relative_date_token,
    )
    if not daypart_suffix:
        return None
    tokens = tokenize_for_matching(normalized)
    if tokens_have_prefixes(tokens, _weekend_prefixes()) or tokens_have_prefixes(
        tokens, _weekday_prefixes()
    ):
        return None
    if not all(
        (
            not looks_like_services_overview_message(text, client_slug=client_slug),
            not detect_location_policy_pack_refs(text, client_slug=client_slug),
            not looks_like_hours_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_rules_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_policy_message(text, client_slug=client_slug),
            not looks_like_contact_policy_message(text, client_slug=client_slug),
        )
    ):
        return None
    if not all(
        (
            not extract_time_token(text),
            not _has_price_signal(normalized, text, client_slug=client_slug),
            not _has_duration_signal(normalized, text, client_slug=client_slug),
            not signal_any_match(
                normalized,
                client_slug,
                "booking_reschedule_keywords",
                "booking_cancel_keywords",
            ),
        )
    ):
        return None
    resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    if not resolution.explicit or resolution.needs_service_clarify:
        return None
    if resolution.reason != "direct_signal":
        return None
    service_query = resolution.service_query
    if not isinstance(service_query, str):
        return None
    service_query = service_query.strip()
    if not service_query:
        return None
    return service_query, normalized_datetime_value


def detect_service_choice_specialist_exact_time_followup(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> tuple[str, str] | None:
    if not isinstance(text, str) or not text.strip():
        return None
    normalized = _normalize_text(text or "")
    if not normalized:
        return None
    relative_date_token = extract_relative_date_token(text)
    if not isinstance(relative_date_token, str) or not relative_date_token.strip():
        return None
    normalized_datetime_value = normalize_resolved_datetime_value(
        text,
        normalized_text=normalized,
    )
    if normalized_datetime_value != relative_date_token:
        return None
    time_token = extract_time_token(text)
    if not isinstance(time_token, str) or not time_token.strip():
        return None
    tokens = tokenize_for_matching(normalized)
    if tokens_have_prefixes(tokens, _weekend_prefixes()) or tokens_have_prefixes(
        tokens, _weekday_prefixes()
    ):
        return None
    if not all(
        (
            not looks_like_services_overview_message(text, client_slug=client_slug),
            not detect_location_policy_pack_refs(text, client_slug=client_slug),
            not looks_like_hours_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_rules_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_policy_message(text, client_slug=client_slug),
            not looks_like_contact_policy_message(text, client_slug=client_slug),
        )
    ):
        return None
    if not all(
        (
            not _has_price_signal(normalized, text, client_slug=client_slug),
            not _has_duration_signal(normalized, text, client_slug=client_slug),
            not signal_any_match(
                normalized,
                client_slug,
                "booking_reschedule_keywords",
                "booking_cancel_keywords",
            ),
        )
    ):
        return None
    resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    if not resolution.explicit or resolution.needs_service_clarify:
        return None
    if resolution.reason != "direct_signal":
        return None
    service_query = resolution.service_query
    if not isinstance(service_query, str):
        return None
    service_query = service_query.strip()
    if not service_query:
        return None
    return service_query, " ".join((relative_date_token, time_token))


def looks_like_master_service_clarify_policy_message(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    resolution = _resolve_master_policy_resolution(text, client_slug=client_slug)
    return bool(resolution is not None and resolution.needs_service_clarify)


def looks_like_pricing_service_clarify_policy_message(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if looks_like_services_overview_message(text, client_slug=client_slug):
        return False
    if detect_location_policy_pack_refs(text, client_slug=client_slug):
        return False
    if looks_like_hours_policy_message(text, client_slug=client_slug):
        return False
    if looks_like_promotions_rules_policy_message(text, client_slug=client_slug):
        return False
    if looks_like_promotions_policy_message(text, client_slug=client_slug):
        return False
    if looks_like_contact_policy_message(text, client_slug=client_slug):
        return False
    master_resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    if master_resolution.explicit or bool(master_resolution.matched_signals):
        return False
    if not _has_price_signal(normalized, text, client_slug=client_slug):
        return False
    if _has_duration_signal(normalized, text, client_slug=client_slug):
        return False
    service_query = get_pack_service_hint(text, client_slug=client_slug)
    if isinstance(service_query, str) and service_query.strip():
        return False
    return True


def looks_like_duration_service_clarify_policy_message(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if looks_like_services_overview_message(text, client_slug=client_slug):
        return False
    if detect_location_policy_pack_refs(text, client_slug=client_slug):
        return False
    if looks_like_hours_policy_message(text, client_slug=client_slug):
        return False
    if looks_like_promotions_rules_policy_message(text, client_slug=client_slug):
        return False
    if looks_like_promotions_policy_message(text, client_slug=client_slug):
        return False
    if looks_like_contact_policy_message(text, client_slug=client_slug):
        return False
    master_resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    if master_resolution.explicit or bool(master_resolution.matched_signals):
        return False
    if _has_price_signal(normalized, text, client_slug=client_slug):
        return False
    if not _has_duration_signal(normalized, text, client_slug=client_slug):
        return False
    service_query = get_pack_service_hint(text, client_slug=client_slug)
    if isinstance(service_query, str) and service_query.strip():
        return False
    return True


def looks_like_bookability_time_collect_policy_message(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if looks_like_services_overview_message(text, client_slug=client_slug):
        return False
    if detect_location_policy_pack_refs(text, client_slug=client_slug):
        return False
    if looks_like_hours_policy_message(text, client_slug=client_slug):
        return False
    if looks_like_promotions_rules_policy_message(text, client_slug=client_slug):
        return False
    if looks_like_promotions_policy_message(text, client_slug=client_slug):
        return False
    if looks_like_contact_policy_message(text, client_slug=client_slug):
        return False
    master_resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    if master_resolution.explicit or bool(master_resolution.matched_signals):
        return False
    if _has_price_signal(normalized, text, client_slug=client_slug):
        return False
    if _has_duration_signal(normalized, text, client_slug=client_slug):
        return False
    if get_pack_service_hint(text, client_slug=client_slug):
        return False
    if signal_any_match(
        normalized,
        client_slug,
        "booking_reschedule_keywords",
        "booking_cancel_keywords",
    ):
        return False
    if has_explicit_date_signal(text):
        return False
    if extract_time_token(text):
        return False
    if normalize_resolved_datetime_value(text, normalized_text=normalized):
        return False
    booking_signal = signal_any_match(
        normalized,
        client_slug,
        "booking_request",
        "booking_keywords",
    )
    if not booking_signal:
        return False
    return signal_any_match(
        normalized,
        client_slug,
        "time_only_request_phrases",
    ) or has_pending_time_question_marker(normalized)


def detect_active_name_time_availability_followup_time_token(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    normalized = _normalize_text(text)
    if not normalized:
        return None
    time_token = extract_time_token(text)
    if not time_token:
        return None
    if not signal_any_match(normalized, client_slug, "booking_request"):
        return None
    if not all(
        (
            not looks_like_services_overview_message(text, client_slug=client_slug),
            not detect_location_policy_pack_refs(text, client_slug=client_slug),
            not looks_like_hours_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_rules_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_policy_message(text, client_slug=client_slug),
            not looks_like_contact_policy_message(text, client_slug=client_slug),
            not has_explicit_date_signal(text),
            not _has_price_signal(normalized, text, client_slug=client_slug),
            not _has_duration_signal(normalized, text, client_slug=client_slug),
            not get_pack_service_hint(text, client_slug=client_slug),
            not signal_any_match(
                normalized,
                client_slug,
                "booking_reschedule_keywords",
                "booking_cancel_keywords",
            ),
        )
    ):
        return None
    master_resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    if master_resolution.explicit or bool(master_resolution.matched_signals):
        return None
    return time_token


def looks_like_active_name_deictic_time_availability_followup(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    tokens = tokenize_for_matching(normalized)
    if not tokens or not normalized_contains_any(normalized, _deictic_time_phrases()):
        return False
    if not tokens_have_prefixes(tokens, _deictic_time_availability_prefixes()):
        return False
    if "?" not in text and not tokens_have_prefixes(tokens, _availability_confirmation_prefixes()):
        return False
    if not all(
        (
            not looks_like_services_overview_message(text, client_slug=client_slug),
            not detect_location_policy_pack_refs(text, client_slug=client_slug),
            not looks_like_hours_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_rules_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_policy_message(text, client_slug=client_slug),
            not looks_like_contact_policy_message(text, client_slug=client_slug),
            not has_explicit_date_signal(text),
            not extract_time_token(text),
            not _has_price_signal(normalized, text, client_slug=client_slug),
            not _has_duration_signal(normalized, text, client_slug=client_slug),
            not get_pack_service_hint(text, client_slug=client_slug),
            not signal_any_match(
                normalized,
                client_slug,
                "booking_reschedule_keywords",
                "booking_cancel_keywords",
            ),
        )
    ):
        return False
    master_resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    if master_resolution.explicit or bool(master_resolution.matched_signals):
        return False
    return True


def looks_like_active_name_deictic_day_availability_followup(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    tokens = tokenize_for_matching(normalized)
    if not tokens:
        return False
    if not all(
        (
            normalized_contains_any(normalized, _deictic_day_phrases()),
            tokens_have_prefixes(tokens, _deictic_time_availability_prefixes()),
        )
    ):
        return False
    if "?" not in text and not tokens_have_prefixes(tokens, _availability_confirmation_prefixes()):
        return False
    if not all(
        (
            not normalized_contains_any(normalized, _deictic_time_phrases()),
            not looks_like_services_overview_message(text, client_slug=client_slug),
            not detect_location_policy_pack_refs(text, client_slug=client_slug),
            not looks_like_hours_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_rules_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_policy_message(text, client_slug=client_slug),
            not looks_like_contact_policy_message(text, client_slug=client_slug),
            not has_explicit_date_signal(text),
            not extract_time_token(text),
            not _has_price_signal(normalized, text, client_slug=client_slug),
            not _has_duration_signal(normalized, text, client_slug=client_slug),
            not get_pack_service_hint(text, client_slug=client_slug),
            not signal_any_match(
                normalized,
                client_slug,
                "booking_reschedule_keywords",
                "booking_cancel_keywords",
            ),
        )
    ):
        return False
    master_resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    if master_resolution.explicit or bool(master_resolution.matched_signals):
        return False
    return True


def detect_active_name_relative_date_availability_followup_datetime_token(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    normalized = _normalize_text(text)
    if not normalized:
        return None
    tokens = tokenize_for_matching(normalized)
    if not tokens or not tokens_have_prefixes(tokens, _deictic_time_availability_prefixes()):
        return None
    if "?" not in text and not tokens_have_prefixes(tokens, _availability_confirmation_prefixes()):
        return None
    relative_date_token = extract_relative_date_token(text)
    if not isinstance(relative_date_token, str) or not relative_date_token.strip():
        return None
    normalized_datetime_value = normalize_resolved_datetime_value(
        text,
        normalized_text=normalized,
    )
    if normalized_datetime_value != relative_date_token:
        return None
    if not all(
        (
            not normalized_contains_any(normalized, _deictic_time_phrases()),
            not normalized_contains_any(normalized, _deictic_day_phrases()),
            not looks_like_services_overview_message(text, client_slug=client_slug),
            not detect_location_policy_pack_refs(text, client_slug=client_slug),
            not looks_like_hours_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_rules_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_policy_message(text, client_slug=client_slug),
            not looks_like_contact_policy_message(text, client_slug=client_slug),
            not extract_time_token(text),
            not _has_price_signal(normalized, text, client_slug=client_slug),
            not _has_duration_signal(normalized, text, client_slug=client_slug),
            not get_pack_service_hint(text, client_slug=client_slug),
            not signal_any_match(
                normalized,
                client_slug,
                "booking_reschedule_keywords",
                "booking_cancel_keywords",
            ),
        )
    ):
        return None
    master_resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    if master_resolution.explicit or bool(master_resolution.matched_signals):
        return None
    return relative_date_token


def detect_active_name_relative_daypart_availability_followup_datetime_token(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    normalized = _normalize_text(text)
    if not normalized:
        return None
    tokens = tokenize_for_matching(normalized)
    if not tokens or not tokens_have_prefixes(tokens, _deictic_time_availability_prefixes()):
        return None
    if "?" not in text and not tokens_have_prefixes(tokens, _availability_confirmation_prefixes()):
        return None
    relative_date_token = extract_relative_date_token(text)
    if not isinstance(relative_date_token, str) or not relative_date_token.strip():
        return None
    normalized_datetime_value = normalize_resolved_datetime_value(
        text,
        normalized_text=normalized,
    )
    if not isinstance(normalized_datetime_value, str) or not normalized_datetime_value.strip():
        return None
    if not split_relative_date_daypart_suffix(normalized_datetime_value, relative_date_token):
        return None
    if not all(
        (
            not normalized_contains_any(normalized, _deictic_time_phrases()),
            not normalized_contains_any(normalized, _deictic_day_phrases()),
            not looks_like_services_overview_message(text, client_slug=client_slug),
            not detect_location_policy_pack_refs(text, client_slug=client_slug),
            not looks_like_hours_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_rules_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_policy_message(text, client_slug=client_slug),
            not looks_like_contact_policy_message(text, client_slug=client_slug),
            not extract_time_token(text),
            not _has_price_signal(normalized, text, client_slug=client_slug),
            not _has_duration_signal(normalized, text, client_slug=client_slug),
            not get_pack_service_hint(text, client_slug=client_slug),
            not signal_any_match(
                normalized,
                client_slug,
                "booking_reschedule_keywords",
                "booking_cancel_keywords",
            ),
        )
    ):
        return None
    master_resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    if master_resolution.explicit or bool(master_resolution.matched_signals):
        return None
    return normalized_datetime_value


def looks_like_specialist_date_range_availability_followup(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if not normalized_contains_any(normalized, _specialist_date_range_followup_phrases()):
        return False
    if not all(
        (
            not normalized_contains_any(normalized, _deictic_time_phrases()),
            not normalized_contains_any(normalized, _deictic_day_phrases()),
            not looks_like_services_overview_message(text, client_slug=client_slug),
            not detect_location_policy_pack_refs(text, client_slug=client_slug),
            not looks_like_hours_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_rules_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_policy_message(text, client_slug=client_slug),
            not looks_like_contact_policy_message(text, client_slug=client_slug),
            not has_explicit_date_signal(text),
            not extract_time_token(text),
            not _has_price_signal(normalized, text, client_slug=client_slug),
            not _has_duration_signal(normalized, text, client_slug=client_slug),
            not get_pack_service_hint(text, client_slug=client_slug),
            not signal_any_match(
                normalized,
                client_slug,
                "booking_reschedule_keywords",
                "booking_cancel_keywords",
            ),
        )
    ):
        return False
    resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    return bool(
        resolution.explicit
        and resolution.needs_service_clarify
        and resolution.reason == "direct_signal"
    )


def looks_like_grounded_specialist_availability_followup(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    tokens = tokenize_for_matching(normalized)
    if not tokens or not tokens_have_prefixes(tokens, _specialist_availability_prefixes()):
        return False
    if not all(
        (
            not normalized_contains_any(normalized, _specialist_date_range_followup_phrases()),
            not normalized_contains_any(normalized, _deictic_time_phrases()),
            not normalized_contains_any(normalized, _deictic_day_phrases()),
            not looks_like_services_overview_message(text, client_slug=client_slug),
            not detect_location_policy_pack_refs(text, client_slug=client_slug),
            not looks_like_hours_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_rules_policy_message(text, client_slug=client_slug),
            not looks_like_promotions_policy_message(text, client_slug=client_slug),
            not looks_like_contact_policy_message(text, client_slug=client_slug),
            not has_explicit_date_signal(text),
            not extract_time_token(text),
            not normalize_resolved_datetime_value(text, normalized_text=normalized),
            not _has_price_signal(normalized, text, client_slug=client_slug),
            not _has_duration_signal(normalized, text, client_slug=client_slug),
            not get_pack_service_hint(text, client_slug=client_slug),
            not signal_any_match(
                normalized,
                client_slug,
                "booking_reschedule_keywords",
                "booking_cancel_keywords",
            ),
        )
    ):
        return False
    resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    return bool(
        resolution.explicit
        and resolution.needs_service_clarify
        and resolution.reason == "direct_signal"
    )


def _resolve_master_policy_resolution(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> MasterIntentResolution | None:
    if not isinstance(text, str) or not text.strip():
        return None
    normalized = _normalize_text(text)
    if not normalized:
        return None
    if looks_like_services_overview_message(text, client_slug=client_slug):
        return None
    if detect_location_policy_pack_refs(text, client_slug=client_slug):
        return None
    if looks_like_hours_policy_message(text, client_slug=client_slug):
        return None
    if looks_like_promotions_rules_policy_message(text, client_slug=client_slug):
        return None
    if looks_like_promotions_policy_message(text, client_slug=client_slug):
        return None
    if looks_like_contact_policy_message(text, client_slug=client_slug):
        return None
    if _has_price_signal(normalized, text, client_slug=client_slug):
        return None
    if _has_duration_signal(normalized, text, client_slug=client_slug):
        return None
    resolution = resolve_master_intent(
        message_text=text,
        client_slug=client_slug,
        service_query=None,
        intent_decomp=None,
        force_master_intent=False,
    )
    if not resolution.explicit:
        return None
    return resolution


def _detect_grounded_service_query(
    text: str | None,
    *,
    client_slug: str | None,
    primary_signal: Callable[[str, str, str | None], bool],
    conflicting_signal: Callable[[str, str, str | None], bool],
) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None
    normalized = _normalize_text(text)
    if not normalized:
        return None
    if looks_like_services_overview_message(text, client_slug=client_slug):
        return None
    if detect_location_policy_pack_refs(text, client_slug=client_slug):
        return None
    if looks_like_hours_policy_message(text, client_slug=client_slug):
        return None
    if not primary_signal(normalized, text, client_slug=client_slug):
        return None
    if conflicting_signal(normalized, text, client_slug=client_slug):
        return None
    service_query = get_pack_service_hint(text, client_slug=client_slug)
    if not isinstance(service_query, str):
        return None
    service_query = service_query.strip()
    return service_query or None


def detect_grounded_pricing_service_query(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> str | None:
    return _detect_grounded_service_query(
        text,
        client_slug=client_slug,
        primary_signal=_has_price_signal,
        conflicting_signal=_has_duration_signal,
    )


def detect_grounded_duration_service_query(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> str | None:
    return _detect_grounded_service_query(
        text,
        client_slug=client_slug,
        primary_signal=_has_duration_signal,
        conflicting_signal=_has_price_signal,
    )
