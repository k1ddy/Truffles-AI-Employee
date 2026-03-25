"""Truth-gate/info bundle helpers and info-response composition."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

from app.core import DialogStateService
from app.routers.webhook.runtime_primitives import (
    BOOKING_CTA_SERVICE_INTENTS,
    INFO_ANCHOR_GROUPS,
    INFO_INTENT_PRIORITY_GENERIC,
    INFO_INTENT_PRIORITY_SERVICE,
    INFO_INTENTS,
    QUESTION_WORD_PREFIXES,
    SESSION_MEMORY_SHORT_TOKENS,
)
from app.schemas.webhook import WebhookResponse
from app.services.booking_signal_service import (
    extract_daypart_token as _extract_daypart_token,
)
from app.services.expected_reply_contract import (
    should_override_truth_gate_off_topic_contract,
    truth_gate_expected_reply_prompt_contract,
)
from app.services.handover_owner_service import ActiveHandoverReuseRuntimeHooks
from app.services.pack_runtime_service import (
    _detect_promotion_intent,
    _build_fact_meta,
    _has_contact_signal,
    _has_duration_signal,
    _has_guest_waiting_signal,
    _has_parking_signal,
    _has_price_signal,
    _normalize_text,
    build_info_combined_reply,
    build_master_reply_from_pack,
    compose_multi_truth_reply,
    ensure_resolver_meta,
    format_reply_from_truth,
    get_pack_decision,
    get_pack_service_hint,
    get_signal_lexicon_list,
    get_system_lexicon_list,
    load_yaml_truth,
    phrase_match_intent,
    resolve_master_intent,
)
from app.services.signal_manifest_service import get_info_regex_pattern

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Conversation, Message, User


_TOKENIZE_WORD_RE = get_info_regex_pattern("tokenize_word_pattern") or re.compile(r"\w+")


def _tokenize_for_matching(normalized: str) -> list[str]:
    return _TOKENIZE_WORD_RE.findall(normalized)


def _normalized_contains_any(normalized: str, phrases: tuple[str, ...] | list[str]) -> bool:
    if not normalized:
        return False
    return any(phrase and phrase in normalized for phrase in phrases)


def _signal_phrase_list(client_slug: str | None, *keys: str) -> list[str]:
    phrases: list[str] = []
    for key in keys:
        for phrase in get_signal_lexicon_list(client_slug, key):
            token = phrase.strip() if isinstance(phrase, str) else ""
            if token and token not in phrases:
                phrases.append(token)
    return phrases


def _signal_any_match(normalized: str, client_slug: str | None, *keys: str) -> bool:
    return bool(keys) and _normalized_contains_any(normalized, _signal_phrase_list(client_slug, *keys))


def _signal_all_match(normalized: str, client_slug: str | None, key: str) -> bool:
    phrases = _signal_phrase_list(client_slug, key)
    return bool(phrases) and all(phrase in normalized for phrase in phrases)


def _signal_pair_match(
    normalized: str,
    client_slug: str | None,
    key_a: str,
    key_b: str,
) -> bool:
    phrases_a = _signal_phrase_list(client_slug, key_a)
    phrases_b = _signal_phrase_list(client_slug, key_b)
    return bool(phrases_a and phrases_b) and _normalized_contains_any(
        normalized, phrases_a
    ) and _normalized_contains_any(normalized, phrases_b)


def _system_any_match(normalized: str, key: str) -> bool:
    phrases = get_system_lexicon_list(key)
    return bool(phrases) and _normalized_contains_any(normalized, phrases)


def _system_any_match_multi(normalized: str, *keys: str) -> bool:
    return any(_system_any_match(normalized, key) for key in keys)


def _has_token_prefix(tokens: list[str], prefix: str) -> bool:
    return any(token.startswith(prefix) for token in tokens)


def _tokens_have_prefixes(tokens: list[str], prefixes: tuple[str, ...]) -> bool:
    return any(_has_token_prefix(tokens, prefix) for prefix in prefixes)


def _has_anchor_prefix(tokens: list[str], prefix: str) -> bool:
    if len(prefix) <= 2:
        return any(token == prefix for token in tokens)
    return any(token.startswith(prefix) for token in tokens)


def _anchor_group_hit(tokens: list[str], group: tuple[str, ...]) -> bool:
    return all(_has_anchor_prefix(tokens, prefix) for prefix in group)


def _count_anchor_hits(tokens: list[str], groups: list[tuple[str, ...]]) -> int:
    return sum(1 for group in groups if _anchor_group_hit(tokens, group))


def _is_short_reply(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = _normalize_text(message_text)
    if not normalized:
        return False
    tokens = _tokenize_for_matching(normalized)
    return 0 < len(tokens) <= SESSION_MEMORY_SHORT_TOKENS


def _looks_like_services_overview_message(
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
    if bool(markers and _normalized_contains_any(normalized, markers)):
        return True
    return bool(
        ("информац" in normalized or "какие" in normalized or "что у вас" in normalized)
        and any(marker in normalized for marker in ("услуг", "процед", "сервис"))
    )


def _detect_location_policy_pack_refs(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> tuple[str, ...]:
    if not isinstance(text, str) or not text.strip():
        return ()
    normalized = _normalize_text(text)
    if not normalized:
        return ()
    tokens = _tokenize_for_matching(normalized)
    question_like = "?" in text or _tokens_have_prefixes(tokens, ("где",))
    parking_signal = _has_parking_signal(normalized, client_slug=client_slug)
    location_signal = parking_signal or _signal_any_match(
        normalized, client_slug, "location_keywords", "location_phrases"
    )
    if (
        question_like
        and _tokens_have_prefixes(tokens, ("где",))
        and _signal_any_match(normalized, client_slug, "location_question_scope_terms")
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


def _looks_like_hours_policy_message(
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
    if _signal_any_match(
        normalized,
        client_slug,
        "location_keywords",
        "location_phrases",
        "location_question_scope_terms",
    ):
        return False
    if _signal_any_match(normalized, client_slug, "hours_question_phrases", "hours_keywords"):
        return True
    return _signal_any_match(normalized, client_slug, "info_hours_stems") and _signal_any_match(
        normalized,
        client_slug,
        "info_time_markers",
        "hours_question_time_phrases",
        "hours_question_work_verbs",
        "hours_question_work_singular",
    )


def _looks_like_promotions_policy_message(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if _signal_any_match(normalized, client_slug, "promotions_stacking_phrases"):
        return False
    if _signal_all_match(normalized, client_slug, "promotions_stacking_terms"):
        return False
    if _detect_location_policy_pack_refs(text, client_slug=client_slug):
        return False
    if _looks_like_hours_policy_message(text, client_slug=client_slug):
        return False
    if _has_price_signal(normalized, text, client_slug=client_slug):
        return False
    if _has_duration_signal(normalized, text, client_slug=client_slug):
        return False
    if _detect_promotion_intent(normalized, client_slug=client_slug) is not None:
        return True
    if any(marker in normalized for marker in ("акци", "скидк", "промо")):
        return True
    if _looks_like_services_overview_message(text, client_slug=client_slug):
        return False
    from app.routers.webhook.policy import _looks_like_promotions_request

    return _looks_like_promotions_request(text, client_slug=client_slug)


def _looks_like_promotions_rules_policy_message(
    text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    normalized = _normalize_text(text)
    if not normalized:
        return False
    if _looks_like_services_overview_message(text, client_slug=client_slug):
        return False
    if _detect_location_policy_pack_refs(text, client_slug=client_slug):
        return False
    if _looks_like_hours_policy_message(text, client_slug=client_slug):
        return False
    if _has_price_signal(normalized, text, client_slug=client_slug):
        return False
    if _has_duration_signal(normalized, text, client_slug=client_slug):
        return False
    if get_pack_service_hint(text, client_slug=client_slug):
        return False
    return _signal_any_match(normalized, client_slug, "promotions_stacking_phrases") or _signal_all_match(
        normalized,
        client_slug,
        "promotions_stacking_terms",
    )


def _detect_info_anchor_hits(tokens: list[str]) -> dict[str, int]:
    hits: dict[str, int] = {}
    for intent in INFO_INTENTS:
        groups = INFO_ANCHOR_GROUPS.get(intent)
        if not groups:
            continue
        count = _count_anchor_hits(tokens, groups)
        if count:
            hits[intent] = count
    return hits


def _looks_like_daypart_preference_statement(
    message_text: str | None,
    *,
    normalized: str,
    question_like: bool,
) -> bool:
    if question_like or not normalized:
        return False
    if not _extract_daypart_token(message_text):
        return False
    if _system_any_match_multi(
        normalized,
        "hours_question_phrases",
        "hours_question_work_verbs",
        "hours_question_work_singular",
    ):
        return False
    return _system_any_match_multi(normalized, "daypart_preference_markers")


def _detect_info_class_intents(
    message_text: str | None,
    *,
    intent_decomp_set: set[str],
    client_slug: str | None = None,
    service_query: str | None = None,
) -> tuple[set[str], dict[str, Any]]:
    from . import _legacy as legacy

    intents = {intent for intent in intent_decomp_set if intent in INFO_INTENTS}
    meta: dict[str, Any] = {}
    normalized = legacy.normalize_for_matching(message_text) if message_text else ""
    if not normalized:
        return intents, meta

    tokens = _tokenize_for_matching(normalized)
    anchor_hits = _detect_info_anchor_hits(tokens)
    anchor_intents = {intent for intent, count in anchor_hits.items() if count > 0}
    question_like = "?" in (message_text or "")
    if not question_like and tokens:
        question_like = _tokens_have_prefixes(tokens, QUESTION_WORD_PREFIXES)
    short_query = 0 < len(tokens) <= 4
    daypart_preference_statement = _looks_like_daypart_preference_statement(
        message_text,
        normalized=normalized,
        question_like=question_like,
    )

    parking_signal = _has_parking_signal(normalized, client_slug=client_slug)
    guest_signal = _has_guest_waiting_signal(normalized, client_slug=client_slug)
    price_signal = legacy._has_price_signal(
        normalized,
        message_text,
        client_slug=client_slug,
    )
    duration_signal = legacy._has_duration_signal(
        normalized,
        message_text,
        client_slug=client_slug,
    )
    contact_signal = _has_contact_signal(
        normalized,
        message_text,
        client_slug=client_slug,
    )
    prep_brows_lashes_signal = bool(
        _signal_any_match(normalized, client_slug, "prep_brows_lashes_prepare_terms")
        and (
            _signal_any_match(normalized, client_slug, "prep_brows_lashes_focus_terms")
            or _signal_any_match(normalized, client_slug, "prep_brows_lashes_extra_terms")
        )
    )
    if not prep_brows_lashes_signal:
        prep_brows_lashes_signal = bool(
            _normalized_contains_any(normalized, ("подготов", "перед процедур", "что-то нужно делать"))
            and _normalized_contains_any(normalized, ("ресниц", "бров", "ламинир"))
        )
    hygiene_signal = _signal_any_match(normalized, client_slug, "hygiene_keywords")
    if not hygiene_signal:
        hygiene_signal = _signal_any_match(normalized, client_slug, "hygiene_dry_heat_terms")
    if not hygiene_signal:
        hygiene_signal = _signal_any_match(normalized, client_slug, "hygiene_disposables_terms")
    if not hygiene_signal:
        hygiene_signal = _signal_any_match(
            normalized,
            client_slug,
            "hygiene_friend_inflammation_terms",
        )
    location_signal = parking_signal or _signal_any_match(
        normalized,
        client_slug,
        "location_keywords",
        "location_phrases",
    )
    address_hint_signal = False
    if client_slug:
        truth = load_yaml_truth(client_slug)
        address = truth.get("salon", {}).get("address", {}) if isinstance(truth, dict) else {}
        address_full = address.get("full") if isinstance(address, dict) else None
        if isinstance(address_full, str) and address_full.strip():
            address_tokens = [
                token
                for token in legacy.normalize_for_matching(address_full).split()
                if len(token) >= 4 and not token.isdigit()
            ]
            if address_tokens:
                address_hint_signal = _normalized_contains_any(normalized, address_tokens)
    location_scope_signal = _signal_any_match(
        normalized,
        client_slug,
        "location_question_scope_terms",
    )
    location_question_signal = bool(
        question_like
        and _tokens_have_prefixes(tokens, ("где",))
        and location_scope_signal
    )
    if location_question_signal:
        location_signal = True
    if address_hint_signal:
        location_signal = True
    hours_signal = _signal_any_match(normalized, client_slug, "hours_keywords")
    hours_stem_signal = _signal_any_match(normalized, client_slug, "info_hours_stems")
    time_marker_signal = _signal_any_match(normalized, client_slug, "info_time_markers")
    if not hours_signal and question_like:
        has_work_schedule_signal = hours_stem_signal and time_marker_signal
        if has_work_schedule_signal:
            hours_signal = True
    pricing_signal = _has_price_signal(normalized, message_text, client_slug=client_slug)
    duration_signal = _has_duration_signal(normalized, message_text, client_slug=client_slug)
    duration_fallback_signal = _signal_pair_match(
        normalized,
        client_slug,
        "info_duration_fallback_verbs",
        "info_duration_fallback_question_markers",
    )
    if not duration_signal:
        duration_signal = duration_fallback_signal
    service_duration_context = _signal_any_match(
        normalized,
        client_slug,
        "info_duration_service_context_markers",
    )
    if duration_signal and hours_stem_signal and not service_duration_context:
        duration_signal = False
        hours_signal = True
    master_resolution = resolve_master_intent(
        message_text=message_text,
        client_slug=client_slug,
        service_query=service_query,
        force_master_intent=False,
    )
    master_signal = bool(master_resolution.explicit)
    if "pricing" in anchor_intents and not price_signal:
        anchor_intents.discard("pricing")
        anchor_hits.pop("pricing", None)

    if "location" in anchor_intents and (question_like or short_query or intent_decomp_set):
        location_signal = True
    if "hours" in anchor_intents and (question_like or short_query or intent_decomp_set):
        hours_signal = True
    if "pricing" in anchor_intents and (question_like or short_query or intent_decomp_set):
        pricing_signal = True
    if "duration" in anchor_intents and (question_like or short_query or intent_decomp_set):
        duration_signal = True

    suppressed_info_intents: set[str] = set()
    if daypart_preference_statement:
        hours_signal = False
        duration_signal = False
        for intent_name in ("hours", "duration"):
            anchor_intents.discard(intent_name)
            anchor_hits.pop(intent_name, None)
            suppressed_info_intents.add(intent_name)

    if parking_signal:
        intents.add("parking")
    if price_signal:
        intents.add("pricing")
    if duration_signal:
        intents.add("duration")
    if contact_signal:
        intents.add("contact")
    if prep_brows_lashes_signal:
        intents.add("prep_brows_lashes")
    if hygiene_signal:
        intents.add("hygiene")
    promotions_rules_signal = _looks_like_promotions_rules_policy_message(
        message_text,
        client_slug=client_slug,
    )
    promotions_signal = False
    from app.routers.webhook.policy import _looks_like_promotions_request

    if promotions_rules_signal:
        intents.add("promotions_rules")
    else:
        promotions_signal = _looks_like_promotions_policy_message(
            message_text,
            client_slug=client_slug,
        )
        promotions_request_like = _looks_like_promotions_request(
            message_text,
            client_slug=client_slug,
        )
        promotions_service_mention_rescue = bool(
            promotions_request_like
            and get_pack_service_hint(message_text, client_slug=client_slug)
        )
        if (
            not promotions_signal
            and promotions_request_like
            and not price_signal
            and not duration_signal
            and not hours_signal
        ):
            promotions_signal = True
            meta["promotions_request_rescue"] = True
        elif (
            promotions_signal
            and promotions_service_mention_rescue
            and not price_signal
            and not duration_signal
            and not hours_signal
        ):
            meta["promotions_request_rescue"] = True
        if promotions_signal:
            intents.add("promotions")
    if location_signal:
        intents.add("location")
    if hours_signal:
        intents.add("hours")
    if pricing_signal:
        intents.add("pricing")
    if duration_signal:
        intents.add("duration")
    if master_signal:
        intents.add("master")
    question_type = None
    try:
        question_type = legacy.semantic_question_type(message_text, include_kinds=INFO_INTENTS)
    except Exception:
        question_type = None
    if question_type and question_type.kind in INFO_INTENTS:
        if not (daypart_preference_statement and question_type.kind in {"hours", "duration"}):
            intents.add(question_type.kind)
            meta["question_type"] = question_type.kind
            meta["question_type_score"] = question_type.score
    explicit_hours_request = (
        not daypart_preference_statement
        and _looks_like_hours_policy_message(
        message_text,
        client_slug=client_slug,
        )
    )
    if explicit_hours_request:
        intents.add("hours")
        intents.discard("duration")
        anchor_intents.discard("duration")
        anchor_hits.pop("duration", None)
        meta["explicit_hours_request"] = True
    work_schedule_phrase = bool(hours_stem_signal and not service_duration_context)
    if work_schedule_phrase and "duration" in intents:
        intents.discard("duration")
        intents.add("hours")
        duration_signal = False
        hours_signal = True
    if explicit_hours_request:
        duration_signal = False
        hours_signal = True
    if suppressed_info_intents:
        intents.difference_update(suppressed_info_intents)
        meta["suppressed_info_intents"] = sorted(suppressed_info_intents)
        meta["daypart_preference_statement"] = True
    anchor_boost = question_like or short_query or bool(intent_decomp_set) or bool(question_type)
    if anchor_intents and anchor_boost:
        intents.update(anchor_intents)
        meta["anchor_intents"] = sorted(anchor_intents)
        meta["anchor_hits"] = anchor_hits
        meta["anchor_boost"] = anchor_boost
    meta["info_signals"] = {
        "parking": parking_signal,
        "pricing": price_signal or pricing_signal,
        "duration": duration_signal,
        "contact": contact_signal,
        "guest": guest_signal,
        "prep_brows_lashes": prep_brows_lashes_signal,
        "hygiene": hygiene_signal,
        "promotions": promotions_signal,
        "promotions_rules": promotions_rules_signal,
        "location": location_signal,
        "location_address_hint": address_hint_signal,
        "hours": hours_signal,
        "master": master_signal,
    }
    if master_signal:
        meta["master_resolution"] = {
            "reason": master_resolution.reason,
            "service_query": master_resolution.service_query,
            "service_query_source": master_resolution.service_query_source,
            "needs_service_clarify": master_resolution.needs_service_clarify,
            "matched_signals": list(master_resolution.matched_signals),
            "resolver_id": master_resolution.resolver_id,
            "resolver_version": master_resolution.resolver_version,
        }
    return intents, meta


def _looks_like_info_query(message_text: str | None, *, client_slug: str | None = None) -> bool:
    intents, meta = _detect_info_class_intents(
        message_text,
        intent_decomp_set=set(),
        client_slug=client_slug,
    )
    if intents:
        return True
    info_signals = meta.get("info_signals") if isinstance(meta, dict) else None
    if isinstance(info_signals, dict):
        if any(
            info_signals.get(signal)
            for signal in (
                "parking",
                "pricing",
                "duration",
                "contact",
                "guest",
                "prep_brows_lashes",
                "hygiene",
                "location",
                "hours",
                "master",
            )
        ):
            return True
    if message_text:
        from .policy import _looks_like_promotions_request

        if _looks_like_promotions_request(message_text, client_slug=client_slug):
            return True
        if client_slug:
            if "order_booking" in phrase_match_intent(message_text, client_slug):
                return True
        from . import _legacy as legacy

        normalized = legacy.normalize_for_matching(message_text)
        if normalized and client_slug:
            truth = load_yaml_truth(client_slug)
            address = truth.get("salon", {}).get("address", {}) if isinstance(truth, dict) else {}
            address_full = address.get("full") if isinstance(address, dict) else None
            if isinstance(address_full, str) and address_full.strip():
                address_tokens = [
                    token
                    for token in legacy.normalize_for_matching(address_full).split()
                    if len(token) >= 4 and not token.isdigit()
                ]
                has_address_hint = _normalized_contains_any(normalized, address_tokens)
                has_hours_hint = _system_any_match_multi(
                    normalized,
                    "hours_question_work_verbs",
                    "hours_question_work_singular",
                    "hours_question_time_phrases",
                )
                if has_address_hint and ("?" in message_text or has_hours_hint):
                    return True
        if normalized and _system_any_match_multi(
            normalized,
            "booking_request",
            "booking_keywords",
        ):
            if _system_any_match(normalized, "booking_required_details_keywords"):
                return True
    return False


def _truth_gate_expected_reply_prompt(expected_reply_type: str | None) -> tuple[str | None, str | None]:
    from . import _legacy as legacy

    prompt_key, intent = truth_gate_expected_reply_prompt_contract(expected_reply_type)
    prompt_map = {
        "service_clarify": legacy.MSG_EXPECTED_SERVICE_OFF_TOPIC,
        "booking_ask_datetime": legacy.MSG_BOOKING_ASK_DATETIME,
        "booking_ask_name": legacy.MSG_BOOKING_ASK_NAME,
    }
    if not prompt_key or not intent:
        return None, None
    return prompt_map.get(prompt_key), intent


def _should_override_truth_gate_off_topic(
    *,
    expected_reply_type: str | None,
    expected_reply_matched: bool | None,
    message_text: str | None,
    current_goal: str | None,
    client_slug: str | None,
) -> bool:
    from . import _legacy as legacy

    has_message_text = bool(message_text)
    is_short_reply = legacy._is_short_reply(message_text) if has_message_text else False
    has_booking_slot_signal = (
        legacy._is_booking_slot_signal(message_text, client_slug=client_slug)
        if has_message_text
        else False
    )
    has_service_hint = bool(get_pack_service_hint(message_text, client_slug=client_slug)) if has_message_text else False
    has_datetime_slot = bool(legacy._extract_datetime(message_text)) if has_message_text else False
    has_name_slot = bool(
        legacy._validate_name_slot(
            message_text,
            allow_freeform=True,
            client_slug=client_slug,
        )
    ) if has_message_text else False
    return should_override_truth_gate_off_topic_contract(
        expected_reply_type=expected_reply_type,
        expected_reply_matched=expected_reply_matched,
        has_message_text=has_message_text,
        current_goal=current_goal,
        is_short_reply=is_short_reply,
        has_booking_slot_signal=has_booking_slot_signal,
        has_service_hint=has_service_hint,
        has_datetime_slot=has_datetime_slot,
        has_name_slot=has_name_slot,
    )


def _build_info_intent_reply(
    intent: str,
    *,
    service_query: str | None,
    client_slug: str | None,
    message_text: str | None = None,
    include_info_bundle: bool = True,
) -> tuple[str | None, dict | None]:
    from . import _legacy as legacy

    normalized = legacy.normalize_for_matching(message_text) if message_text else ""
    parking_signal = _has_parking_signal(normalized, client_slug=client_slug) if normalized else False
    guest_signal = _has_guest_waiting_signal(normalized, client_slug=client_slug) if normalized else False
    location_signal = False
    if normalized:
        location_signal = _signal_any_match(
            normalized,
            client_slug,
            "location_keywords",
            "location_phrases",
        )
    include_info_bundle = include_info_bundle and (
        intent in {"location", "hours"} or location_signal or parking_signal or guest_signal
    )

    def _resolverize(
        meta_payload: dict | None,
        *,
        resolved_intent: str | None = None,
        resolved_action: str = "reply",
    ) -> dict:
        return ensure_resolver_meta(
            meta_payload if isinstance(meta_payload, dict) else {},
            action=resolved_action,
            intent=resolved_intent or intent,
            resolver_id="webhook.info_intent",
            client_slug=client_slug,
        )

    if intent == "contact":
        truth = load_yaml_truth(client_slug)
        salon = truth.get("salon", {}) if isinstance(truth, dict) else {}
        if isinstance(salon, dict):
            phone = str(salon.get("phone") or "").strip()
            whatsapp = str(salon.get("whatsapp") or "").strip()
            telegram = str(salon.get("telegram") or "").strip()
            instagram = str(salon.get("instagram") or "").strip()
            lines: list[str] = []
            if phone:
                lines.append(f"Телефон: {phone}.")
            if whatsapp:
                lines.append(f"WhatsApp: {whatsapp}.")
            if telegram:
                lines.append(f"Telegram: {telegram}.")
            if instagram:
                lines.append(f"Instagram: {instagram}.")
            if lines:
                if not phone and (whatsapp or telegram or instagram):
                    lines.insert(0, "Телефон в карточке салона не указан.")
                meta = _build_fact_meta(
                    meta={"info_sections": ["contact"]},
                    fact_source="truth",
                    fact_intents=["contact"],
                    info_sections=["contact"],
                )
                return " ".join(lines), _resolverize(meta, resolved_intent="contact")

    if intent == "hours":
        if not (parking_signal or guest_signal or location_signal):
            truth = load_yaml_truth(client_slug)
            hours = truth.get("salon", {}).get("hours", {}) if isinstance(truth, dict) else {}
            if isinstance(hours, dict):
                days = str(hours.get("days") or "").strip()
                open_label = str(hours.get("open") or "").strip()
                close_label = str(hours.get("close") or "").strip()
                parts = ["Работаем"]
                if days:
                    parts.append(days)
                if open_label and close_label:
                    parts.append(f"с {open_label} до {close_label}")
                elif open_label:
                    parts.append(f"с {open_label}")
                elif close_label:
                    parts.append(f"до {close_label}")
                hours_text = " ".join(part for part in parts if part).strip()
                if hours_text:
                    if not hours_text.endswith("."):
                        hours_text = f"{hours_text}."
                    meta = _build_fact_meta(
                        meta={"info_sections": ["hours"]},
                        fact_source="truth",
                        fact_intents=[intent],
                        info_sections=["hours"],
                    )
                    return hours_text, _resolverize(meta)
        reply, meta = build_info_combined_reply(
            include_parking=parking_signal,
            include_guest=guest_signal,
            client_slug=client_slug,
        )
        meta = _build_fact_meta(
            meta=meta,
            fact_source="truth",
            fact_intents=[intent],
        )
        return reply, _resolverize(meta)
    if intent == "location":
        reply, meta = build_info_combined_reply(
            include_parking=parking_signal,
            include_guest=guest_signal,
            client_slug=client_slug,
        )
        meta = _build_fact_meta(
            meta=meta,
            fact_source="truth",
            fact_intents=[intent],
        )
        return reply, _resolverize(meta)
    if intent == "master":
        resolution = resolve_master_intent(
            message_text=message_text,
            client_slug=client_slug,
            service_query=service_query,
            force_master_intent=True,
        )
        decision = build_master_reply_from_pack(
            client_slug=client_slug,
            message_text=message_text,
            resolution=resolution,
        )
        if not decision:
            return None, None
        return decision.response, _resolverize(
            decision.meta,
            resolved_intent=decision.intent or "master",
            resolved_action=decision.action or "reply",
        )
    if intent == "hygiene":
        reply = format_reply_from_truth("hygiene", client_slug=client_slug)
        if not reply:
            return None, None
        meta = _build_fact_meta(
            fact_source="truth",
            fact_intents=["hygiene"],
            info_sections=["hygiene"],
        )
        return reply, _resolverize(meta, resolved_intent="hygiene")
    if intent == "prep_brows_lashes":
        reply = format_reply_from_truth("prep_brows_lashes", client_slug=client_slug)
        if not reply:
            return None, None
        meta = _build_fact_meta(
            fact_source="truth",
            fact_intents=["prep_brows_lashes"],
            info_sections=["prep_brows_lashes"],
        )
        return reply, _resolverize(meta, resolved_intent="prep_brows_lashes")
    if intent == "promotions":
        reply = format_reply_from_truth("promotions", client_slug=client_slug)
        if not reply:
            reply = format_reply_from_truth("promotions_rules", client_slug=client_slug)
        if not reply:
            return None, None
        meta = _build_fact_meta(
            fact_source="truth",
            fact_intents=["promotions"],
            info_sections=["promotions"],
        )
        return reply, _resolverize(meta, resolved_intent="promotions")
    if intent == "promotions_rules":
        reply = format_reply_from_truth("promotions_rules", client_slug=client_slug)
        if not reply:
            return None, None
        meta = _build_fact_meta(
            fact_source="truth",
            fact_intents=["promotions"],
            info_sections=["promotions"],
        )
        return reply, _resolverize(meta, resolved_intent="promotions_rules")
    if intent in {"pricing", "duration"} and not service_query and message_text:
        service_query = get_pack_service_hint(message_text, client_slug=client_slug)
        if not service_query:
            decision = get_pack_decision(message_text, client_slug=client_slug)
            if (
                decision
                and decision.action == "reply"
                and decision.intent in {"service_not_found", "price_query"}
                and decision.response
            ):
                meta = decision.meta if isinstance(decision.meta, dict) else None
                resolved_action = (
                    "collect"
                    if decision.intent in {"service_not_found", "service_clarify"}
                    else (decision.action or "reply")
                )
                return decision.response, _resolverize(
                    meta,
                    resolved_intent=decision.intent,
                    resolved_action=resolved_action,
                )
    if intent == "pricing":
        question = f"Сколько стоит {service_query}?" if service_query else "Сколько стоит?"
    elif intent == "duration":
        question = f"Сколько длится {service_query}?" if service_query else "Сколько длится?"
    else:
        return None, None
    info_prefix: str | None = None
    info_meta: dict | None = None
    if include_info_bundle:
        info_prefix, info_meta = build_info_combined_reply(
            include_parking=parking_signal,
            include_guest=guest_signal,
            client_slug=client_slug,
        )
    duration_info_sections = ["duration", "service_duration"] if intent == "duration" else None
    decision = get_pack_decision(question, client_slug=client_slug)
    if decision and decision.action == "reply" and decision.response:
        meta = decision.meta if isinstance(decision.meta, dict) else {}
        if info_meta:
            meta = {**info_meta, **meta}
        reply_text = decision.response
        if info_prefix:
            reply_text = f"{info_prefix} {reply_text}".strip()
        meta = _build_fact_meta(
            meta=meta,
            fact_source="truth",
            fact_intents=[intent],
            info_sections=duration_info_sections,
        )
        resolved_action = (
            "collect"
            if decision.intent in {"service_not_found", "service_clarify", "duration_or_price_clarify"}
            else (decision.action or "reply")
        )
        return reply_text, _resolverize(
            meta,
            resolved_intent=decision.intent,
            resolved_action=resolved_action,
        )
    fallback = format_reply_from_truth("duration_or_price_clarify", client_slug=client_slug)
    if info_prefix:
        fallback = f"{info_prefix} {fallback}".strip() if fallback else info_prefix
    meta = _build_fact_meta(
        meta=info_meta,
        fact_source="truth",
        fact_intents=[intent],
        info_sections=duration_info_sections,
    )
    return fallback, _resolverize(
        meta,
        resolved_action="collect",
        resolved_intent="duration_or_price_clarify",
    )


def _extract_truth_gate_info_intents(
    message_text: str,
    *,
    policy_handler: dict | None,
    policy_type: str | None,
    client_slug: str | None,
    intent_decomp: dict | None,
) -> list[str]:
    if not message_text or not policy_handler:
        return []
    truth_gate = policy_handler.get("truth_gate")
    if not truth_gate:
        return []
    decision = truth_gate(message_text, client_slug=client_slug, intent_decomp=intent_decomp)
    if not decision or getattr(decision, "action", None) != "reply":
        return []
    intent = getattr(decision, "intent", None)
    if not isinstance(intent, str):
        return []
    intent_key = intent.strip().casefold()
    if intent_key == "hours":
        return ["hours"]
    if intent_key == "location" or intent_key.startswith("location_"):
        return ["location"]
    return []


@dataclass(frozen=True)
class InfoFlowResult:
    response: WebhookResponse | None
    force_truth_gate: bool


def _record_class_router_trace(*, conversation: Any, class_router_result: dict | None) -> None:
    if not conversation or not isinstance(class_router_result, dict):
        return
    from . import _legacy as legacy

    controller_meta = class_router_result.get("controller") if isinstance(class_router_result, dict) else None
    controller_used = bool(controller_meta.get("used")) if isinstance(controller_meta, dict) else False
    controller_attempted = bool(controller_meta.get("attempted")) if isinstance(controller_meta, dict) else False
    controller_fallback = bool(controller_meta.get("fallback")) if isinstance(controller_meta, dict) else False
    controller_low_confidence = (
        bool(controller_meta.get("low_confidence")) if isinstance(controller_meta, dict) else False
    )
    controller_used_reason = (
        controller_meta.get("used_reason") if isinstance(controller_meta, dict) else None
    )
    controller_confidence = (
        controller_meta.get("confidence") if isinstance(controller_meta, dict) else None
    )
    controller_error = controller_meta.get("error") if isinstance(controller_meta, dict) else None
    controller_goal = controller_meta.get("goal") if isinstance(controller_meta, dict) else None
    trace_payload = {
        "stage": "class_router",
        "classes": class_router_result.get("classes"),
        "intents": class_router_result.get("intents"),
        "carryover_intents": class_router_result.get("carryover_intents"),
        "in_signals": class_router_result.get("in_signals"),
        "out_signals": class_router_result.get("out_signals"),
        "anchors_in_hits": class_router_result.get("anchors_in_hits"),
        "anchors_out_hits": class_router_result.get("anchors_out_hits"),
        "out_of_domain_signal": class_router_result.get("out_of_domain_signal"),
        "carryover_class": class_router_result.get("carryover_class"),
        "carryover_info_sections": class_router_result.get("carryover_info_sections"),
        "router_fallback_reason": class_router_result.get("router_fallback_reason"),
        "controller_fallback_reason": class_router_result.get("controller_fallback_reason"),
        "router": class_router_result.get("router"),
        "controller": controller_meta,
        "controller_used": controller_used,
        "controller_attempted": controller_attempted,
        "controller_fallback": controller_fallback,
        "controller_low_confidence": controller_low_confidence,
        "controller_used_reason": controller_used_reason,
        "controller_confidence": controller_confidence,
        "controller_error": controller_error,
        "controller_goal": controller_goal,
    }
    trace_payload.update(
        legacy._router_observability_updates_from_class_router(class_router_result)
    )
    legacy._record_decision_trace(conversation, trace_payload)


def _handle_info_flow(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str | None,
    saved_message: Message | None,
    client_slug: str | None,
    routing: dict,
    bypass_domain_flows: bool,
    booking_wants_flow: bool,
    policy_handler: dict | None,
    intent_decomp_used: bool,
    intent_decomp_intents: list[str],
    intent_decomp_set: set[str],
    intent_decomp_payload: dict | None,
    intent_decomp_service_query: str | None,
    info_class_intents: set[str],
    info_class_meta: dict,
    booking_signal: bool,
    class_carryover: dict | None,
    router_state: dict | None,
    allow_service_carryover: bool,
    context_manager: dict,
    current_goal: str | None,
    message_count: int,
    now: datetime,
    consult_return_pending: bool,
    consult_return_prompt: str | None,
    consult_context: dict | None,
    consult_return_reason: str | None,
    multi_intent_other_followup: str | None,
    maybe_apply_fact_guard: Callable[..., Any],
    send_and_save: Callable[..., tuple[str, bool]],
    send_response: Callable[..., Any],
    finalize_response: Callable[..., Any],
) -> InfoFlowResult:
    from . import _legacy as legacy

    force_truth_gate = False
    if not (
        routing.get("allow_bot_reply")
        and not booking_wants_flow
        and not bypass_domain_flows
        and policy_handler
    ):
        return InfoFlowResult(response=None, force_truth_gate=force_truth_gate)

    if intent_decomp_used and message_text:
        intent_set = {intent.strip().casefold() for intent in intent_decomp_intents if intent}
        if "booking" not in intent_set and "hours" in intent_set and "pricing" in intent_set:
            multi_result = compose_multi_truth_reply(
                message_text,
                client_slug,
                intent_decomp=intent_decomp_payload,
                return_meta=True,
            )
            if multi_result:
                multi_reply, multi_meta = multi_result
                guard_response = maybe_apply_fact_guard(
                    decision_meta=multi_meta if isinstance(multi_meta, dict) else None,
                    intent="multi_truth",
                    source="multi_truth",
                    allow_handover=routing.get("allow_handover_create", False),
                )
                if guard_response:
                    db.commit()
                    return InfoFlowResult(response=guard_response, force_truth_gate=force_truth_gate)
                bot_response = multi_reply
                composer_meta = None
                bot_response, composer_meta = legacy._compose_fact_response(
                    bot_response,
                    client_slug=client_slug,
                    conversation_id=str(conversation.id),
                    response_tag="multi_truth",
                    conversation_state=conversation.state,
                    allow_booking_flow=routing["allow_booking_flow"],
                    has_followup=False,
                )
                legacy._reset_low_confidence_retry(conversation)

                result_message = "Multi-truth reply sent"
                trace_payload = {
                    "stage": "multi_truth",
                    "decision": "reply",
                    "intent": "multi_truth",
                    "state": conversation.state,
                    "intents": sorted(intent_set),
                }
                if isinstance(multi_meta, dict):
                    trace_payload.update(multi_meta)
                if composer_meta:
                    trace_payload.update(composer_meta)
                legacy._record_decision_trace(conversation, trace_payload)
                legacy._record_message_decision_meta(
                    saved_message,
                    action="reply",
                    intent="multi_truth",
                    source="multi_truth",
                    fast_intent=False,
                )
                if saved_message and isinstance(multi_meta, dict):
                    legacy._update_message_decision_metadata(saved_message, multi_meta)
                if saved_message and composer_meta:
                    legacy._update_message_decision_metadata(saved_message, composer_meta)
                legacy._maybe_store_class_carryover(
                    conversation=conversation,
                    class_name="info_bundle",
                    intents=["multi_truth"],
                    info_meta=multi_meta if isinstance(multi_meta, dict) else None,
                    message_count=message_count,
                    reason="multi_truth",
                )
                legacy._maybe_store_service_carryover(
                    conversation=conversation,
                    service_meta=multi_meta if isinstance(multi_meta, dict) else None,
                    intent="multi_truth",
                    message_count=message_count,
                    reason="multi_truth",
                )
                bot_response, sent = send_and_save(bot_response)
                if not sent:
                    result_message = f"{result_message}; response_send=failed"
                db.commit()
                return InfoFlowResult(
                    response=WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    ),
                    force_truth_gate=force_truth_gate,
                )

    explicit_service_signal = legacy._has_explicit_service_signal(
        message_text,
        client_slug=client_slug,
        intent_decomp_payload=intent_decomp_payload,
    )
    class_router_result = legacy._resolve_class_router_result(
        info_intents=info_class_intents,
        info_meta=info_class_meta,
        booking_signal=booking_signal,
        class_carryover=class_carryover,
        domain_intent=legacy.DomainIntent.UNKNOWN,
        domain_meta=None,
        router_state=router_state,
        explicit_service_signal=explicit_service_signal,
    )
    info_signals = info_class_meta.get("info_signals") if isinstance(info_class_meta, dict) else None
    guest_signal = bool(info_signals.get("guest")) if isinstance(info_signals, dict) else False
    info_class = "info_bundle" in (class_router_result.get("classes") or [])
    guest_policy_class = "guest_policy" in (class_router_result.get("classes") or []) or guest_signal
    base_info_intents: set[str] = set(class_router_result.get("intents") or [])
    info_class_intents_for_reply: set[str] = set(base_info_intents)
    carryover_intents: set[str] = set()
    for item in class_router_result.get("carryover_intents") or []:
        if isinstance(item, str) and item.strip():
            value = item.strip().casefold()
            info_class_intents_for_reply.add(value)
            carryover_intents.add(value)
    skip_info_class_for_service = False
    if (
        info_class
        and message_text
        and not info_class_intents
    ):
        normalized = legacy.normalize_for_matching(message_text)
        service_hint = get_pack_service_hint(message_text, client_slug=client_slug)
        if service_hint:
            if _has_parking_signal(normalized, client_slug=client_slug) or _has_guest_waiting_signal(
                normalized,
                client_slug=client_slug,
            ):
                service_hint = None
            else:
                presence_hint = _signal_any_match(
                    normalized,
                    client_slug,
                    "service_question_keywords",
                ) or ("?" in message_text and len(normalized.split()) <= 4)
                if presence_hint and not (
                    legacy._has_price_signal(normalized, message_text)
                    or legacy._has_duration_signal(normalized, message_text)
                ):
                    skip_info_class_for_service = True
    router_service_query = None
    alias_service_query = None
    intent_decomp_explicit_query = None
    carryover_has_hours = False
    carryover_has_parking = False
    if (
        info_class
        and info_class_intents_for_reply
        and not skip_info_class_for_service
        and not guest_policy_class
    ):
        carryover_sections = class_router_result.get("carryover_info_sections")
        if isinstance(carryover_sections, list):
            for section in carryover_sections:
                if isinstance(section, str) and section.strip().casefold() == "hours":
                    carryover_has_hours = True
                    break
            for section in carryover_sections:
                if isinstance(section, str) and section.strip().casefold() == "parking":
                    carryover_has_parking = True
                    break
        router_state = (
            class_router_result.get("router")
            if isinstance(class_router_result, dict)
            else None
        )
        router_output = router_state.get("output") if isinstance(router_state, dict) else None
        if isinstance(router_output, dict):
            slots = router_output.get("slots")
            if isinstance(slots, dict):
                candidate = slots.get("service_query")
                if isinstance(candidate, str) and candidate.strip():
                    router_service_query = candidate.strip()
        if message_text and client_slug:
            normalized_for_alias = legacy._normalize_service_text(message_text)
            if normalized_for_alias:
                alias_match = legacy._match_service(normalized_for_alias, client_slug=client_slug)
                if isinstance(alias_match, dict):
                    alias_name = alias_match.get("name")
                    if isinstance(alias_name, str) and alias_name.strip():
                        alias_service_query = alias_name.strip()
        intent_decomp_source = None
        if isinstance(intent_decomp_payload, dict):
            source = intent_decomp_payload.get("service_query_source")
            if isinstance(source, str):
                intent_decomp_source = source
        intent_decomp_explicit_query = (
            intent_decomp_service_query if intent_decomp_source != "context" else None
        )
    controller_low_confidence = False
    controller_state = (
        class_router_result.get("controller") if isinstance(class_router_result, dict) else None
    )
    if isinstance(controller_state, dict):
        controller_low_confidence = bool(controller_state.get("low_confidence"))
    explicit_service_signal = bool(
        explicit_service_signal
        or intent_decomp_explicit_query
        or router_service_query
        or alias_service_query
    )
    service_carryover_meta = legacy._get_service_carryover(
        context_manager, message_count=message_count
    )
    carryover_service_query = None
    if isinstance(service_carryover_meta, dict):
        carryover_service_query = service_carryover_meta.get("service_query")
    guest_policy_lock = guest_policy_class
    info_bundle_lock = info_class and not (
        explicit_service_signal or intent_decomp_explicit_query or router_service_query
    )
    info_semantic_lock = guest_policy_lock or info_bundle_lock or controller_low_confidence
    info_semantic_meta: dict[str, Any] = {}
    if info_semantic_lock:
        if guest_policy_lock:
            info_class_intents_for_reply.discard("pricing")
            info_class_intents_for_reply.discard("duration")
        else:
            if "pricing" not in base_info_intents and not (
                allow_service_carryover and "pricing" in carryover_intents
            ):
                info_class_intents_for_reply.discard("pricing")
            if "duration" not in base_info_intents and not (
                allow_service_carryover and "duration" in carryover_intents
            ):
                info_class_intents_for_reply.discard("duration")
        if guest_policy_lock:
            skip_reason = "guest_policy_lock"
        elif info_bundle_lock:
            skip_reason = "info_bundle_lock"
        else:
            skip_reason = "controller_low_confidence"
        info_semantic_meta = {
            "info_semantic_match_skipped": True,
            "info_semantic_match_skip_reason": skip_reason,
        }
        if guest_policy_lock:
            info_semantic_meta.update(
                {
                    "question_type": None,
                    "service_query": None,
                    "service_query_source": None,
                    "service_query_score": 0.0,
                }
            )
        if not (allow_service_carryover and carryover_intents):
            carryover_service_query = None
    normalized_followup = legacy.normalize_for_matching(message_text) if message_text else ""
    force_hours_followup = (
        carryover_has_hours
        and legacy._looks_like_hours_followup(message_text)
        and not explicit_service_signal
    )
    explicit_info_signal = bool(
        isinstance(info_signals, dict)
        and any(
            bool(info_signals.get(key))
            for key in (
                "parking",
                "pricing",
                "duration",
                "contact",
                "guest",
                "location",
                "hours",
                "prep_brows_lashes",
                "hygiene",
                "master",
            )
        )
    )
    force_parking_followup = bool(
        carryover_has_parking
        and normalized_followup
        and not explicit_service_signal
        and not explicit_info_signal
        and legacy._looks_like_carryover_followup(message_text)
    )
    base_info_override = False
    if isinstance(info_signals, dict):
        base_info_override = bool(info_signals.get("parking") or info_signals.get("guest"))
    if not base_info_override:
        base_info_override = bool({"location", "hours"} & info_class_intents_for_reply)
    effective_semantic_lock = info_semantic_lock and not (
        force_hours_followup or force_parking_followup or base_info_override
    )
    info_service_query = None
    if not effective_semantic_lock:
        if alias_service_query:
            info_service_query = alias_service_query
        elif router_service_query:
            info_service_query = router_service_query
        elif intent_decomp_explicit_query:
            info_service_query = intent_decomp_explicit_query
        if (
            not force_hours_followup
            and not info_service_query
            and {"pricing", "duration"} & info_class_intents_for_reply
            and not effective_semantic_lock
        ):
            info_service_query = legacy._extract_service_hint(message_text, client_slug)
        if (
            not force_hours_followup
            and not info_service_query
            and {"pricing", "duration"} & info_class_intents_for_reply
            and not effective_semantic_lock
            and allow_service_carryover
        ):
            if carryover_service_query:
                info_service_query = carryover_service_query
        if force_hours_followup:
            info_class_intents_for_reply.discard("duration")
            info_class_intents_for_reply.add("hours")

        priority = (
            INFO_INTENT_PRIORITY_SERVICE
            if info_service_query
            else INFO_INTENT_PRIORITY_GENERIC
        )
        answer_intents: list[str] = []
        for intent_name in priority:
            if intent_name in info_class_intents_for_reply and intent_name not in answer_intents:
                answer_intents.append(intent_name)
            if len(answer_intents) >= 2:
                break
        if not answer_intents:
            answer_intents = list(sorted(info_class_intents_for_reply))[:2]

        include_parking = (
            bool(info_signals.get("parking")) if isinstance(info_signals, dict) else False
        )
        if force_parking_followup:
            include_parking = True
        include_guest = (
            bool(info_signals.get("guest")) if isinstance(info_signals, dict) else False
        )
        include_base_bundle = False
        if isinstance(info_signals, dict):
            include_base_bundle = any(
                bool(info_signals.get(key))
                for key in ("parking", "guest", "location")
            )
        if not include_base_bundle:
            include_base_bundle = bool({"location"} & info_class_intents_for_reply)
        if force_parking_followup:
            include_base_bundle = True
        base_bundle_reply: str | None = None
        base_bundle_meta: dict[str, Any] = {}
        base_bundle_intents: set[str] = set()
        if include_base_bundle:
            base_bundle_reply, base_bundle_meta = build_info_combined_reply(
                include_parking=include_parking,
                include_guest=include_guest,
                client_slug=client_slug,
            )
            base_bundle_intents = {"location", "hours"}

        replies: list[str] = []
        info_meta_combined: dict[str, Any] = {}
        if isinstance(base_bundle_meta, dict) and base_bundle_meta:
            info_meta_combined.update(base_bundle_meta)
        if info_semantic_meta:
            info_meta_combined.update(info_semantic_meta)
        if isinstance(base_bundle_reply, str):
            base_bundle_reply = base_bundle_reply.strip()
            if base_bundle_reply:
                replies.append(base_bundle_reply)
        extra_intents = [
            intent_name for intent_name in answer_intents if intent_name not in base_bundle_intents
        ]
        for intent_name in extra_intents:
            reply, meta = _build_info_intent_reply(
                intent_name,
                service_query=info_service_query,
                client_slug=client_slug,
                message_text=message_text,
                include_info_bundle=False,
            )
            if isinstance(reply, str):
                reply = reply.strip()
                if reply:
                    replies.append(reply)
            if isinstance(meta, dict) and meta:
                info_meta_combined.update(meta)
        if force_hours_followup:
            info_meta_combined["question_type"] = "hours"
        if replies:
            guard_response = maybe_apply_fact_guard(
                decision_meta=info_meta_combined if info_meta_combined else None,
                intent="info_bundle",
                source="class_router",
                allow_handover=routing.get("allow_handover_create", False),
            )
            if guard_response:
                db.commit()
                return InfoFlowResult(response=guard_response, force_truth_gate=force_truth_gate)
            bot_response = "\n\n".join(replies)
            composer_meta = None
            bot_response, composer_meta = legacy._compose_fact_response(
                bot_response,
                client_slug=client_slug,
                conversation_id=str(conversation.id),
                response_tag="info_class",
                conversation_state=conversation.state,
                allow_booking_flow=routing["allow_booking_flow"],
                has_followup=False,
            )
            bot_response = legacy._combine_sidecar(bot_response, multi_intent_other_followup)
            legacy._reset_low_confidence_retry(conversation)
            _record_class_router_trace(
                conversation=conversation,
                class_router_result=class_router_result,
            )
            trace_payload = {
                "stage": "info_class",
                "decision": "reply",
                "state": conversation.state,
                "intents": answer_intents,
                "class_router": class_router_result,
            }
            trace_payload.update(info_meta_combined)
            if composer_meta:
                trace_payload.update(composer_meta)
            legacy._record_decision_trace(conversation, trace_payload)
            legacy._record_message_decision_meta(
                saved_message,
                action="reply",
                intent="info_bundle",
                source="class_router",
                fast_intent=False,
            )
            if saved_message:
                meta_updates = {"class_router": class_router_result}
                if info_meta_combined:
                    meta_updates.update(info_meta_combined)
                meta_updates.update(
                    legacy._controller_meta_updates_from_class_router(class_router_result)
                )
                meta_updates.update(
                    legacy._router_observability_updates_from_class_router(class_router_result)
                )
                legacy._update_message_decision_metadata(saved_message, meta_updates)
            if saved_message and composer_meta:
                legacy._update_message_decision_metadata(saved_message, composer_meta)
            legacy._maybe_store_class_carryover(
                conversation=conversation,
                class_name="info_bundle",
                intents=answer_intents,
                info_meta=info_meta_combined,
                message_count=message_count,
                reason="class_router",
            )
            legacy._maybe_store_service_carryover(
                conversation=conversation,
                service_meta=info_meta_combined,
                intent="info_bundle",
                message_count=message_count,
                reason="class_router",
            )
            if consult_return_pending:
                bot_response = legacy._apply_consult_return(
                    conversation=conversation,
                    saved_message=saved_message,
                    bot_response=bot_response,
                    consult_return_prompt=consult_return_prompt,
                    consult_context=consult_context,
                    reason=consult_return_reason or "info_class",
                )
            bot_response, sent = send_and_save(bot_response)
            result_message = "Info class reply sent" if sent else "Info class reply failed"
            db.commit()
            return InfoFlowResult(
                response=WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                ),
                force_truth_gate=force_truth_gate,
            )

    if guest_policy_class and routing.get("allow_bot_reply"):
        include_parking = (
            bool(info_signals.get("parking")) if isinstance(info_signals, dict) else False
        )
        base_bundle_reply, base_bundle_meta = build_info_combined_reply(
            include_parking=include_parking,
            include_guest=True,
            client_slug=client_slug,
        )
        if base_bundle_meta:
            info_class_intents_for_reply.add("guest_policy")
        if isinstance(base_bundle_reply, str) and base_bundle_reply.strip():
            guard_response = maybe_apply_fact_guard(
                decision_meta=base_bundle_meta if isinstance(base_bundle_meta, dict) else None,
                intent="guest_policy",
                source="class_router",
                allow_handover=routing.get("allow_handover_create", False),
            )
            if guard_response:
                db.commit()
                return InfoFlowResult(response=guard_response, force_truth_gate=force_truth_gate)
            bot_response = base_bundle_reply.strip()
            composer_meta = None
            bot_response, composer_meta = legacy._compose_fact_response(
                bot_response,
                client_slug=client_slug,
                conversation_id=str(conversation.id),
                response_tag="info_class",
                conversation_state=conversation.state,
                allow_booking_flow=routing["allow_booking_flow"],
                has_followup=bool(multi_intent_other_followup),
            )
            bot_response = legacy._combine_sidecar(bot_response, multi_intent_other_followup)
            legacy._reset_low_confidence_retry(conversation)
            _record_class_router_trace(
                conversation=conversation,
                class_router_result=class_router_result,
            )
            trace_payload = {
                "stage": "info_class",
                "decision": "reply",
                "state": conversation.state,
                "intents": sorted(info_class_intents_for_reply or {"guest_policy"}),
                "class_router": class_router_result,
            }
            if isinstance(base_bundle_meta, dict) and base_bundle_meta:
                trace_payload.update(base_bundle_meta)
            if composer_meta:
                trace_payload.update(composer_meta)
            legacy._record_decision_trace(conversation, trace_payload)
            legacy._record_message_decision_meta(
                saved_message,
                action="reply",
                intent="info_bundle",
                source="class_router",
                fast_intent=False,
            )
            if saved_message:
                meta_updates = {"class_router": class_router_result}
                if isinstance(base_bundle_meta, dict) and base_bundle_meta:
                    meta_updates.update(base_bundle_meta)
                meta_updates.update(
                    legacy._controller_meta_updates_from_class_router(class_router_result)
                )
                meta_updates.update(
                    legacy._router_observability_updates_from_class_router(class_router_result)
                )
                legacy._update_message_decision_metadata(saved_message, meta_updates)
            if saved_message and composer_meta:
                legacy._update_message_decision_metadata(saved_message, composer_meta)
            legacy._maybe_store_class_carryover(
                conversation=conversation,
                class_name="info_bundle",
                intents=sorted(info_class_intents_for_reply or {"guest_policy"}),
                info_meta=base_bundle_meta if isinstance(base_bundle_meta, dict) else {},
                message_count=message_count,
                reason="guest_policy_lock",
            )
            legacy._maybe_store_service_carryover(
                conversation=conversation,
                service_meta=base_bundle_meta if isinstance(base_bundle_meta, dict) else None,
                intent="info_bundle",
                message_count=message_count,
                reason="guest_policy_lock",
            )
            if consult_return_pending:
                bot_response = legacy._apply_consult_return(
                    conversation=conversation,
                    saved_message=saved_message,
                    bot_response=bot_response,
                    consult_return_prompt=consult_return_prompt,
                    consult_context=consult_context,
                    reason=consult_return_reason or "info_class",
                )
            bot_response, sent = send_and_save(bot_response)
            result_message = "Guest policy reply sent" if sent else "Guest policy reply failed"
            db.commit()
            return InfoFlowResult(
                response=WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                ),
                force_truth_gate=force_truth_gate,
            )

    if message_text:
        normalized_message = legacy.normalize_for_matching(message_text)
        info_signal_override = False
        if isinstance(info_signals, dict):
            info_signal_override = any(
                bool(info_signals.get(key))
                for key in (
                    "parking",
                    "location",
                    "hours",
                    "guest",
                    "pricing",
                    "duration",
                    "prep_brows_lashes",
                    "hygiene",
                )
            )
        force_truth_gate_intents = {
            "pricing",
            "duration",
            "parking",
            "location",
            "hours",
            "prep_brows_lashes",
            "hygiene",
            "guest_policy",
            "master",
            "promotions",
        }
        force_truth_gate = bool(
            info_class_intents_for_reply & force_truth_gate_intents
            or info_signal_override
            or legacy._has_price_signal(normalized_message, message_text)
            or legacy._has_duration_signal(normalized_message, message_text)
        )
    service_matcher = policy_handler.get("service_matcher")
    service_decision = None
    if service_matcher and not force_truth_gate:
        service_decision = service_matcher(
            message_text,
            client_slug=client_slug,
            intent_decomp=intent_decomp_payload,
        )
    if service_decision:
        if service_decision.action == "reply":
            guard_response = maybe_apply_fact_guard(
                decision_meta=service_decision.meta if isinstance(service_decision.meta, dict) else None,
                intent=service_decision.intent,
                source="service_matcher",
                allow_handover=routing.get("allow_handover_create", False),
            )
        if guard_response:
            db.commit()
            return InfoFlowResult(response=guard_response, force_truth_gate=force_truth_gate)
        bot_response = service_decision.response
        bot_response = legacy._combine_sidecar(bot_response, multi_intent_other_followup)
        composer_meta = None
        if (
            service_decision.action == "reply"
            and service_decision.intent in BOOKING_CTA_SERVICE_INTENTS
        ):
            bot_response, composer_meta = legacy._compose_fact_response(
                bot_response,
                client_slug=client_slug,
                conversation_id=str(conversation.id),
                response_tag="service_matcher",
                conversation_state=conversation.state,
                allow_booking_flow=routing["allow_booking_flow"],
                has_followup=bool(multi_intent_other_followup),
            )
        if consult_return_pending:
            bot_response = legacy._apply_consult_return(
                conversation=conversation,
                saved_message=saved_message,
                bot_response=bot_response,
                consult_return_prompt=consult_return_prompt,
                consult_context=consult_context,
                reason=consult_return_reason or "service_matcher",
            )
        legacy._reset_low_confidence_retry(conversation)

        result_message = "Service matcher reply sent"
        clarify_reason = None
        if service_decision.intent == "service_clarify":
            clarify_intent = current_goal or "info"
            context = legacy._get_conversation_context(conversation)
            context_manager = legacy._get_context_manager(context)
            if legacy._should_escalate_for_clarify(context_manager, clarify_intent):
                clarify_count, _ = legacy._get_clarify_attempt_state(context_manager, clarify_intent)
                legacy._record_context_manager_decision(
                    conversation,
                    saved_message,
                    decision="clarify_limit",
                    updates={
                        "clarify_attempt": {"intent": clarify_intent, "count": clarify_count},
                        "clarify_reason": "service_clarify",
                        "clarify_limit": True,
                    },
                )
                return InfoFlowResult(
                    response=legacy._handle_clarify_limit_escalation(
                        db=db,
                        conversation=conversation,
                        user=user,
                        message_text=message_text,
                        saved_message=saved_message,
                        source="service_matcher",
                        allow_handover=routing.get("allow_handover_create", False),
                        send_response=send_response,
                        finalize_response=finalize_response,
                    ),
                    force_truth_gate=force_truth_gate,
                )
            legacy._register_clarify_attempt(
                conversation=conversation,
                saved_message=saved_message,
                intent=clarify_intent,
                now=now,
                reason="service_clarify",
            )
            service_meta = getattr(service_decision, "meta", None)
            service_query = None
            service_source = None
            if isinstance(service_meta, dict):
                service_query = service_meta.get("service_query")
                service_source = service_meta.get("service_query_source")
            if not service_query and service_source in (None, "", "none"):
                clarify_reason = "missing_service_query"
            elif not service_query and intent_decomp_used:
                decomp_query = (
                    intent_decomp_payload.get("service_query")
                    if isinstance(intent_decomp_payload, dict)
                    else None
                )
                if not decomp_query:
                    intent_set = {intent.strip().casefold() for intent in intent_decomp_intents if intent}
                    if "pricing" in intent_set or "duration" in intent_set:
                        clarify_reason = "missing_service_query"
            if service_decision.action != "escalate":
                context = legacy._get_conversation_context(conversation)
                context = legacy._set_expected_reply_context(
                    conversation=conversation,
                    saved_message=saved_message,
                    context=context,
                    expected_reply_type=legacy.EXPECTED_REPLY_SERVICE,
                    reason="service_clarify",
                    now=now,
                )
        trace_payload = {
            "stage": "service_matcher",
            "decision": service_decision.intent,
            "state": conversation.state,
        }
        if isinstance(getattr(service_decision, "meta", None), dict):
            trace_payload.update(service_decision.meta)
        if composer_meta:
            trace_payload.update(composer_meta)
        legacy._record_decision_trace(conversation, trace_payload)
        legacy._record_message_decision_meta(
            saved_message,
            action=service_decision.action,
            intent=service_decision.intent,
            source="service_matcher",
            fast_intent=False,
        )
        if saved_message and isinstance(getattr(service_decision, "meta", None), dict):
            legacy._update_message_decision_metadata(saved_message, service_decision.meta)
        if saved_message and composer_meta:
            legacy._update_message_decision_metadata(saved_message, composer_meta)
        if saved_message and clarify_reason:
            legacy._update_message_decision_metadata(saved_message, {"clarify_reason": clarify_reason})
        legacy._maybe_store_service_carryover(
            conversation=conversation,
            service_meta=service_decision.meta if isinstance(service_decision.meta, dict) else None,
            intent=service_decision.intent,
            message_count=message_count,
            reason="service_matcher",
        )
        decision_meta = (
            service_decision.meta
            if isinstance(getattr(service_decision, "meta", None), dict)
            else {}
        )
        info_carryover_intents: list[str] = []
        if service_decision.intent in INFO_INTENTS:
            info_carryover_intents.append(service_decision.intent)
        if service_decision.intent == "service_clarify":
            question_type = decision_meta.get("question_type")
            if question_type == "pricing":
                info_carryover_intents.append("pricing")
            elif question_type == "duration":
                info_carryover_intents.append("duration")
        if info_carryover_intents or decision_meta.get("info_sections"):
            legacy._maybe_store_class_carryover(
                conversation=conversation,
                class_name="info_bundle",
                intents=info_carryover_intents,
                info_meta=decision_meta,
                message_count=message_count,
                reason="service_matcher",
            )
        bot_response, sent = send_and_save(bot_response)
        if not sent:
            result_message = f"{result_message}; response_send=failed"
        db.commit()
        return InfoFlowResult(
            response=WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            ),
            force_truth_gate=force_truth_gate,
        )

    return InfoFlowResult(response=None, force_truth_gate=force_truth_gate)


def _handle_truth_gate_fallback(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str | None,
    saved_message: Message | None,
    client_slug: str | None,
    routing: dict,
    booking_wants_flow: bool,
    policy_handler: dict | None,
    policy_type: str | None,
    current_goal: str | None,
    intent_decomp_used: bool,
    intent_decomp_intents: list[str],
    intent_decomp_payload: dict | None,
    llm_primary_reason: str | None,
    message_count: int,
    now: datetime,
    consult_return_pending: bool,
    consult_return_prompt: str | None,
    consult_context: dict | None,
    consult_return_reason: str | None,
    maybe_apply_fact_guard: Callable[..., Any],
    send_and_save: Callable[..., tuple[str, bool]],
    log_timing: Callable[[str, float, dict | None], None],
    record_escalation_metric: Callable[[str], None],
) -> WebhookResponse | None:
    from app.services.pack_runtime_service import PackDecision, ensure_resolver_meta

    from . import _legacy as legacy

    def _build_out_of_domain_class_router_result() -> dict[str, Any]:
        controller_output = legacy._build_controller_meta_output(error="skipped")
        controller_output["class"] = "out_of_domain"
        controller_output["goal"] = "out_of_domain"
        controller_output["confidence"] = max(legacy.CONTROLLER_CONFIDENCE_THRESHOLD, 0.5)
        controller_output = legacy._ensure_controller_output_meta(
            controller_output, error="skipped"
        )
        router_state = {
            "used": True,
            "attempted": False,
            "fallback": False,
            "confidence": controller_output["confidence"],
            "error": "skipped",
            "fallback_reason": None,
            "signal_class": legacy._resolve_controller_signal_class(
                intent_decomp_set=set(intent_decomp_intents),
                booking_signal=False,
            ),
            "signal_match": False,
            "used_reason": "deterministic",
            "output": controller_output,
            "sla": None,
        }
        return legacy._resolve_class_router_result(
            info_intents=set(),
            info_meta=None,
            booking_signal=False,
            class_carryover=None,
            domain_intent=legacy.DomainIntent.OUT_OF_DOMAIN,
            domain_meta=None,
            router_state=router_state,
            explicit_service_signal=False,
        )

    policy_t0 = time.monotonic()
    truth_gate = policy_handler.get("truth_gate") if policy_handler else None
    decision = None
    if truth_gate:
        decision = truth_gate(
            message_text,
            client_slug=client_slug,
            intent_decomp=intent_decomp_payload,
        )
    if decision:
        if decision.intent == "price_query":
            price_item_fn = policy_handler.get("price_item") if policy_handler else None
            price_item = price_item_fn(message_text, client_slug=client_slug) if price_item_fn else None
            if not price_item and price_item_fn and isinstance(getattr(decision, "meta", None), dict):
                service_query = decision.meta.get("service_query")
                if isinstance(service_query, str) and service_query.strip():
                    price_item = price_item_fn(service_query, client_slug=client_slug)
            if price_item:
                context = legacy._get_conversation_context(conversation)
                context = legacy._set_service_hint(context, price_item, now)
                legacy._set_conversation_context(conversation, context)
            elif not (
                isinstance(getattr(decision, "meta", None), dict)
                and decision.meta.get("service_query")
            ):
                decision = PackDecision(
                    action="escalate",
                    response=legacy.MSG_ESCALATED,
                    intent="price_query",
                )
        if decision.intent == "service_clarify" and decision.action != "escalate":
            clarify_intent = current_goal or "info"
            context = legacy._get_conversation_context(conversation)
            context_manager = legacy._get_context_manager(context)
            if legacy._should_escalate_for_clarify(context_manager, clarify_intent):
                clarify_count, _ = legacy._get_clarify_attempt_state(context_manager, clarify_intent)
                legacy._record_context_manager_decision(
                    conversation,
                    saved_message,
                    decision="clarify_limit",
                    updates={
                        "clarify_attempt": {"intent": clarify_intent, "count": clarify_count},
                        "clarify_reason": "service_clarify",
                        "clarify_limit": True,
                    },
                )
                decision = PackDecision(
                    action="escalate",
                    response=legacy.MSG_ESCALATED,
                    intent="clarify_limit",
                    meta={"clarify_limit": True},
                )
            else:
                legacy._register_clarify_attempt(
                    conversation=conversation,
                    saved_message=saved_message,
                    intent=clarify_intent,
                    now=now,
                    reason="service_clarify",
                )
        if decision.action != "escalate" and decision.intent in {
            "service_clarify",
            "duration_or_price_clarify",
        }:
            context = legacy._get_conversation_context(conversation)
            context = legacy._set_expected_reply_context(
                conversation=conversation,
                saved_message=saved_message,
                context=context,
                expected_reply_type=legacy.EXPECTED_REPLY_SERVICE,
                reason=decision.intent,
                now=now,
            )
        if decision.action == "reply":
            guard_response = maybe_apply_fact_guard(
                decision_meta=decision.meta if isinstance(decision.meta, dict) else None,
                intent=decision.intent,
                source="truth_gate",
                allow_handover=routing.get("allow_handover_create", False),
            )
            if guard_response:
                db.commit()
                return guard_response
        bot_response = decision.response
        if decision.action == "reply":
            cta_intents = set(INFO_INTENTS) | set(BOOKING_CTA_SERVICE_INTENTS) | {
                "location_directions",
                "location_signage",
                "parking",
                "guest_policy",
                "services_overview",
            }
            if decision.intent in cta_intents:
                bot_response = legacy._maybe_append_booking_cta(
                    bot_response,
                    conversation_state=conversation.state,
                    allow_booking_flow=routing["allow_booking_flow"],
                    has_followup=bool(consult_return_pending),
                )
        if consult_return_pending:
            bot_response = legacy._apply_consult_return(
                conversation=conversation,
                saved_message=saved_message,
                bot_response=bot_response,
                consult_return_prompt=consult_return_prompt,
                consult_context=consult_context,
                reason=consult_return_reason or "truth_gate",
            )
        legacy._reset_low_confidence_retry(conversation)

        result_message = "Truth gate fallback reply sent"
        if decision.action == "escalate":
            _, reused, telegram_sent = legacy._reuse_active_handover(
                db=db,
                conversation=conversation,
                user=user,
                message=message_text,
                source="truth_gate",
                intent=decision.intent,
                hooks=ActiveHandoverReuseRuntimeHooks(
                    get_active_handover=legacy.get_active_handover,
                    transition_state=legacy.transition_state,
                    send_telegram_notification=legacy.send_telegram_notification,
                    record_decision_trace=legacy._record_decision_trace,
                ),
            )
            if reused:
                result_message = f"Truth gate reuse, telegram={'sent' if telegram_sent else 'failed'}"
            elif conversation.state == legacy.ConversationState.BOT_ACTIVE.value:
                record_escalation_metric("intent")
                result = legacy.escalate_to_pending(
                    db=db,
                    conversation=conversation,
                    user_message=message_text,
                    trigger_type="intent",
                    trigger_value=decision.intent or "policy",
                )
                if result.ok:
                    handover = result.value
                    telegram_sent = legacy.send_telegram_notification(
                        db=db,
                        handover=handover,
                        conversation=conversation,
                        user=user,
                        message=message_text,
                    )
                    result_message = f"Truth gate escalation, telegram={'sent' if telegram_sent else 'failed'}"
                else:
                    result_message = f"Truth gate escalation failed: {result.error}"
            else:
                result_message = "Truth gate escalation skipped (already pending)"

        if decision.intent == "off_topic":
            context = legacy._get_conversation_context(conversation)
            expected_reply_type = legacy._get_expected_reply_type(context)
            saved_meta = None
            if saved_message is not None:
                # Tests may pass lightweight message doubles that only expose
                # `message_metadata` (without SQLAlchemy `.metadata`).
                raw_meta = getattr(saved_message, "message_metadata", None)
                if isinstance(raw_meta, dict):
                    saved_meta = raw_meta
                else:
                    legacy_meta = getattr(saved_message, "metadata", None)
                    if isinstance(legacy_meta, dict):
                        saved_meta = legacy_meta
            saved_decision_meta = (
                saved_meta.get("decision_meta")
                if isinstance(saved_meta, dict)
                else None
            )
            expected_reply_matched = (
                saved_decision_meta.get("expected_reply_matched")
                if isinstance(saved_decision_meta, dict)
                else None
            )
            if _should_override_truth_gate_off_topic(
                expected_reply_type=expected_reply_type,
                expected_reply_matched=expected_reply_matched,
                message_text=message_text,
                current_goal=current_goal,
                client_slug=client_slug,
            ):
                followup_prompt, followup_intent = _truth_gate_expected_reply_prompt(
                    expected_reply_type
                )
                if followup_prompt and followup_intent:
                    context = legacy._set_expected_reply_context(
                        conversation=conversation,
                        saved_message=saved_message,
                        context=context,
                        expected_reply_type=expected_reply_type,
                        reason="truth_gate_off_topic_override",
                        now=now,
                    )
                    pending_question_contract = DialogStateService().project_context_pending_question_contract(
                        context,
                        session_memory_key="__disabled_session_memory__",
                    )
                    override_meta = (
                        dict(decision.meta)
                        if isinstance(getattr(decision, "meta", None), dict)
                        else {}
                    )
                    override_meta.update(
                        {
                            "expected_reply_type": expected_reply_type,
                            "expected_reply_guard": "truth_gate_off_topic_override",
                        }
                    )
                    if pending_question_contract:
                        override_meta["pending_question_contract"] = pending_question_contract
                    if isinstance(expected_reply_matched, bool):
                        override_meta["expected_reply_matched"] = expected_reply_matched
                    decision = PackDecision(
                        action="reply",
                        response=followup_prompt,
                        intent=followup_intent,
                        meta=override_meta,
                    )
                    bot_response = decision.response
                    trace_payload = {
                        "stage": "truth_gate",
                        "decision": "expected_reply_override",
                        "expected_reply_type": expected_reply_type,
                        "expected_reply_matched": expected_reply_matched,
                    }
                    if pending_question_contract:
                        trace_payload["pending_question_contract"] = pending_question_contract
                    legacy._record_decision_trace(conversation, trace_payload)
            context_manager = legacy._get_context_manager(context)
            class_carryover = legacy._get_class_carryover(
                context_manager,
                message_count=message_count,
            )
            carryover_sections = (
                class_carryover.get("info_sections")
                if isinstance(class_carryover, dict)
                else None
            )
            normalized = legacy.normalize_for_matching(message_text) if message_text else ""
            tokens = _tokenize_for_matching(normalized) if normalized else []
            short_noisy_followup = bool(
                llm_primary_reason == "low_confidence"
                and conversation.state == legacy.ConversationState.BOT_ACTIVE.value
                and current_goal == "info"
                and isinstance(class_carryover, dict)
                and class_carryover.get("class") == "info_bundle"
                and isinstance(carryover_sections, list)
                and carryover_sections
                and 0 < len(tokens) <= SESSION_MEMORY_SHORT_TOKENS
                and "?" not in (message_text or "")
                and not any(ch.isdigit() for ch in (message_text or ""))
                and not get_pack_service_hint(message_text or "", client_slug=client_slug)
            )
            if short_noisy_followup:
                normalized_sections = {
                    section.strip().casefold()
                    for section in carryover_sections
                    if isinstance(section, str) and section.strip()
                }
                include_parking = "parking" in normalized_sections
                include_guest = "guest_policy" in normalized_sections
                carryover_reply, carryover_meta = build_info_combined_reply(
                    include_parking=include_parking,
                    include_guest=include_guest,
                    client_slug=client_slug,
                )
                if isinstance(carryover_reply, str) and carryover_reply.strip():
                    meta = dict(carryover_meta) if isinstance(carryover_meta, dict) else {}
                    if normalized_sections:
                        meta.setdefault("info_sections", sorted(normalized_sections))
                    meta.setdefault("fact_source", "truth")
                    decision = PackDecision(
                        action="reply",
                        response=carryover_reply.strip(),
                        intent="info_bundle",
                        meta=meta,
                    )
                    bot_response = decision.response
                    legacy._record_decision_trace(
                        conversation,
                        {
                            "stage": "truth_gate",
                            "decision": "carryover_override",
                            "reason": "short_noisy_followup",
                            "info_sections": sorted(normalized_sections),
                        },
                    )

        if decision.intent == "off_topic":
            class_router_result = _build_out_of_domain_class_router_result()
            _record_class_router_trace(
                conversation=conversation,
                class_router_result=class_router_result,
            )
        resolver_action = decision.action
        if decision.action != "escalate" and decision.intent in {
            "service_not_found",
            "service_clarify",
            "duration_or_price_clarify",
            "info_clarify",
        }:
            resolver_action = "collect"
        resolver_meta = ensure_resolver_meta(
            decision.meta if isinstance(decision.meta, dict) else {},
            action=resolver_action,
            intent=decision.intent,
            resolver_id="webhook.truth_gate",
            client_slug=client_slug,
        )
        decision = PackDecision(
            action=decision.action,
            response=decision.response,
            intent=decision.intent,
            collect=decision.collect,
            meta=resolver_meta,
        )
        trace_payload = {
            "stage": "truth_gate",
            "decision": decision.action,
            "intent": decision.intent,
            "state": conversation.state,
            "booking_wants_flow": booking_wants_flow,
            "policy_type": policy_type,
            "llm_fallback_reason": llm_primary_reason,
        }
        if decision.intent == "multi_truth":
            trace_payload["multi_truth"] = True
        if isinstance(getattr(decision, "meta", None), dict):
            trace_payload.update(decision.meta)
        legacy._record_decision_trace(conversation, trace_payload)
        legacy._record_message_decision_meta(
            saved_message,
            action=decision.action,
            intent=decision.intent,
            source="truth_gate",
            fast_intent=False,
        )
        if saved_message and isinstance(getattr(decision, "meta", None), dict):
            legacy._update_message_decision_metadata(saved_message, decision.meta)
        if saved_message and decision.intent == "service_clarify":
            clarify_reason = None
            service_meta = getattr(decision, "meta", None)
            service_query = None
            service_source = None
            if isinstance(service_meta, dict):
                service_query = service_meta.get("service_query")
                service_source = service_meta.get("service_query_source")
            if not service_query and service_source in (None, "", "none"):
                clarify_reason = "missing_service_query"
            elif not service_query and intent_decomp_used:
                decomp_query = (
                    intent_decomp_payload.get("service_query")
                    if isinstance(intent_decomp_payload, dict)
                    else None
                )
                if not decomp_query:
                    intent_set = {intent.strip().casefold() for intent in intent_decomp_intents if intent}
                    if "pricing" in intent_set or "duration" in intent_set:
                        clarify_reason = "missing_service_query"
            if clarify_reason:
                legacy._update_message_decision_metadata(saved_message, {"clarify_reason": clarify_reason})
        decision_meta = decision.meta if isinstance(getattr(decision, "meta", None), dict) else {}
        info_carryover_intents: list[str] = []
        if decision.intent in INFO_INTENTS:
            info_carryover_intents.append(decision.intent)
        if decision.intent in {"parking", "guest_policy"}:
            info_carryover_intents.append(decision.intent)
        if decision.intent == "service_clarify":
            question_type = decision_meta.get("question_type")
            if question_type == "pricing":
                info_carryover_intents.append("pricing")
            elif question_type == "duration":
                info_carryover_intents.append("duration")
        if info_carryover_intents or decision_meta.get("info_sections"):
            legacy._maybe_store_class_carryover(
                conversation=conversation,
                class_name="info_bundle",
                intents=info_carryover_intents,
                info_meta=decision_meta,
                message_count=message_count,
                reason="truth_gate",
            )
        legacy._maybe_store_service_carryover(
            conversation=conversation,
            service_meta=decision.meta if isinstance(decision.meta, dict) else None,
            intent=decision.intent,
            message_count=message_count,
            reason="truth_gate",
        )
        bot_response, sent = send_and_save(bot_response)
        if not sent:
            result_message = f"{result_message}; response_send=failed"
        log_timing(
            "policy_gate_ms",
            (time.monotonic() - policy_t0) * 1000,
            {"policy_type": policy_type, "booking_wants_flow": booking_wants_flow, "gate": "truth_fallback"},
        )
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )
    log_timing(
        "policy_gate_ms",
        (time.monotonic() - policy_t0) * 1000,
        {"policy_type": policy_type, "booking_wants_flow": booking_wants_flow, "gate": "truth_fallback"},
    )
    return None


def _handle_offline_info_class(
    *,
    db: Session,
    conversation: Conversation,
    saved_message: Message | None,
    routing: dict,
    booking_wants_flow: bool,
    bypass_domain_flows: bool,
    policy_handler: dict | None,
    class_router_result: dict | None,
    info_class_meta: dict,
    multi_intent_other_followup: str | None,
    message_count: int,
    consult_return_pending: bool,
    consult_return_prompt: str | None,
    consult_context: dict | None,
    consult_return_reason: str | None,
    client_slug: str | None,
    maybe_apply_fact_guard: Callable[..., Any],
    send_and_save: Callable[..., tuple[str, bool]],
) -> WebhookResponse | None:
    from . import _legacy as legacy

    controller_meta = class_router_result.get("controller") if isinstance(class_router_result, dict) else None
    controller_error = controller_meta.get("error") if isinstance(controller_meta, dict) else None
    offline_controller = (not legacy._current_openai_api_key()) or controller_error == "no_api_key"
    info_intents_for_reply: set[str] = set(class_router_result.get("intents") or [])
    for item in class_router_result.get("carryover_intents") or []:
        if isinstance(item, str) and item.strip():
            info_intents_for_reply.add(item.strip().casefold())
    carryover_sections = (
        [item for item in class_router_result.get("carryover_info_sections") or [] if isinstance(item, str)]
        if isinstance(class_router_result, dict)
        else []
    )
    for section in carryover_sections:
        normalized_section = section.strip().casefold()
        if normalized_section in {"location", "hours"}:
            info_intents_for_reply.add(normalized_section)
    info_signals = info_class_meta.get("info_signals") if isinstance(info_class_meta, dict) else None
    base_info_requested = bool(
        {"location", "hours"} & info_intents_for_reply
        or (
            isinstance(info_signals, dict)
            and (info_signals.get("parking") or info_signals.get("guest"))
        )
        or any(
            isinstance(section, str)
            and section.strip().casefold() in {"location", "hours", "parking", "guest_policy"}
            for section in carryover_sections
        )
    )
    if (
        offline_controller
        and routing.get("allow_bot_reply")
        and not booking_wants_flow
        and not bypass_domain_flows
        and policy_handler
        and base_info_requested
        and "info_bundle" in (class_router_result.get("classes") or [])
    ):
        carryover_sections_normalized = {section.strip().casefold() for section in carryover_sections}
        include_parking = (
            bool(info_signals.get("parking")) if isinstance(info_signals, dict) else False
        ) or "parking" in carryover_sections_normalized
        include_guest = (
            bool(info_signals.get("guest")) if isinstance(info_signals, dict) else False
        ) or "guest_policy" in carryover_sections_normalized
        base_bundle_reply, base_bundle_meta = build_info_combined_reply(
            include_parking=include_parking,
            include_guest=include_guest,
            client_slug=client_slug,
        )
        if isinstance(base_bundle_reply, str) and base_bundle_reply.strip():
            info_meta_combined: dict[str, Any] = {}
            if isinstance(base_bundle_meta, dict) and base_bundle_meta:
                info_meta_combined.update(base_bundle_meta)
            guard_response = maybe_apply_fact_guard(
                decision_meta=info_meta_combined if info_meta_combined else None,
                intent="info_bundle",
                source="class_router",
                allow_handover=routing.get("allow_handover_create", False),
            )
            if guard_response:
                db.commit()
                return guard_response
            bot_response = base_bundle_reply.strip()
            composer_meta = None
            bot_response, composer_meta = legacy._compose_fact_response(
                bot_response,
                client_slug=client_slug,
                conversation_id=str(conversation.id),
                response_tag="info_class",
                conversation_state=conversation.state,
                allow_booking_flow=routing["allow_booking_flow"],
                has_followup=False,
            )
            bot_response = legacy._combine_sidecar(bot_response, multi_intent_other_followup)
            legacy._reset_low_confidence_retry(conversation)
            trace_payload = {
                "stage": "info_class",
                "decision": "reply",
                "state": conversation.state,
                "intents": sorted(info_intents_for_reply),
                "class_router": class_router_result,
            }
            if info_meta_combined:
                trace_payload.update(info_meta_combined)
            if composer_meta:
                trace_payload.update(composer_meta)
            legacy._record_decision_trace(conversation, trace_payload)
            legacy._record_message_decision_meta(
                saved_message,
                action="reply",
                intent="info_bundle",
                source="class_router",
                fast_intent=False,
            )
            if saved_message:
                meta_updates = {"class_router": class_router_result}
                if info_meta_combined:
                    meta_updates.update(info_meta_combined)
                meta_updates.update(
                    legacy._controller_meta_updates_from_class_router(class_router_result)
                )
                meta_updates.update(
                    legacy._router_observability_updates_from_class_router(class_router_result)
                )
                legacy._update_message_decision_metadata(saved_message, meta_updates)
            if saved_message and composer_meta:
                legacy._update_message_decision_metadata(saved_message, composer_meta)
            legacy._maybe_store_class_carryover(
                conversation=conversation,
                class_name="info_bundle",
                intents=sorted(info_intents_for_reply),
                info_meta=info_meta_combined,
                message_count=message_count,
                reason="class_router_offline",
            )
            legacy._maybe_store_service_carryover(
                conversation=conversation,
                service_meta=info_meta_combined,
                intent="info_bundle",
                message_count=message_count,
                reason="class_router_offline",
            )
            if consult_return_pending:
                bot_response = legacy._apply_consult_return(
                    conversation=conversation,
                    saved_message=saved_message,
                    bot_response=bot_response,
                    consult_return_prompt=consult_return_prompt,
                    consult_context=consult_context,
                    reason=consult_return_reason or "info_class",
                )
            bot_response, sent = send_and_save(bot_response)
            result_message = "Info class reply sent" if sent else "Info class reply failed"
            db.commit()
            return WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            )
    return None


__all__ = [
    "_anchor_group_hit",
    "_build_info_intent_reply",
    "_count_anchor_hits",
    "_detect_info_anchor_hits",
    "_detect_info_class_intents",
    "_extract_truth_gate_info_intents",
    "_handle_info_flow",
    "_handle_offline_info_class",
    "_handle_truth_gate_fallback",
    "_is_short_reply",
    "_looks_like_info_query",
    "_tokenize_for_matching",
]
