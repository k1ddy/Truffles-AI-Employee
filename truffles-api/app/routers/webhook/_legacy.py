"""Governed legacy webhook adapter: explicit compatibility exports only."""

from __future__ import annotations

import os
import re
import time
from typing import Any, Callable

from app.routers.webhook.booking_compat import _looks_like_booking_reschedule_request
from app.routers.webhook.booking_runtime import (
    _matches_guest_policy_lexicon as _booking_runtime_matches_guest_policy_lexicon,
)
from app.routers.webhook.booking_signal_runtime import (
    TIME_HOUR_PATTERN,
    TIME_ONLY_ALLOWED_PREFIXES,
    TIME_ONLY_ALLOWED_TOKENS,
    TIME_ONLY_AMPM_PATTERN,
    TIME_PATTERN,
    _extract_datetime,
    _has_explicit_service_signal,
)
from app.routers.webhook.class_router_runtime import _resolve_class_router_result
from app.routers.webhook.context_manager import _apply_consult_return
from app.routers.webhook.decision_compat import (
    _format_discounts_reply_for_message,
    _looks_like_promo_code_request,
)
from app.routers.webhook.expected_reply_interrupt_runtime import _validate_expected_reply_value
from app.routers.webhook.info import (
    _count_anchor_hits,
    _has_token_prefix,
    _normalized_contains_any,
    _signal_all_match,
    _signal_any_match,
    _signal_pair_match,
    _signal_phrase_list,
    _system_any_match,
    _system_any_match_multi,
    _tokenize_for_matching,
    _tokens_have_prefixes,
)
from app.routers.webhook.info_followup_compat import (
    _looks_like_carryover_followup,
    _looks_like_hours_followup,
)
from app.routers.webhook.media import _is_style_reference_request
from app.routers.webhook.policy import _POLICY_HANDLERS, _get_policy_handler
from app.routers.webhook.policy_compat import (
    _looks_like_policy_topic,
    _looks_like_promotions_request,
)
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
    _contains_any,
)
from app.services.ai_service import (
    is_acknowledgement_message,
    is_greeting_message,
    is_low_signal_message,
    is_thanks_message,
    normalize_for_matching,
)
from app.services.booking_signal_service import (
    extract_daypart_token as _extract_daypart_token,
)
from app.services.booking_signal_service import (
    has_daypart_stem as _has_daypart_stem,
)
from app.services.booking_signal_service import (
    has_pending_time_question_marker as _has_pending_time_question_marker,
)
from app.services.booking_signal_service import (
    looks_like_time_preference_statement as _looks_like_time_preference_statement,
)
from app.services.chatflow_service import send_bot_response
from app.services.handover_owner_service import (
    _create_pending_escalation_with_notification as _handover_owner_create_pending_escalation_with_notification,
)
from app.services.handover_owner_service import (
    _reuse_active_handover as _handover_owner_reuse_active_handover,
)
from app.services.handover_owner_service import (
    escalate_to_pending as _handover_owner_escalate_to_pending,
)
from app.services.handover_owner_service import (
    get_active_handover as _handover_owner_get_active_handover,
)
from app.services.handover_owner_service import (
    manager_reassign as _handover_owner_manager_reassign,
)
from app.services.handover_owner_service import (
    manager_reopen as _handover_owner_manager_reopen,
)
from app.services.handover_owner_service import (
    manager_resolve as _handover_owner_manager_resolve,
)
from app.services.handover_owner_service import (
    manager_return as _handover_owner_manager_return,
)
from app.services.handover_owner_service import (
    manager_take as _handover_owner_manager_take,
)
from app.services.handover_owner_service import (
    resolve_active_handover_rejection as _handover_owner_resolve_active_handover_rejection,
)
from app.services.intent_service import (
    classify_domain_with_scores,
    is_strong_out_of_domain,
    route_dialogue_controller,
)
from app.services.pack_runtime_compat import (
    phrase_match_intent,
    resolve_master_intent,
    semantic_question_type,
)
from app.services.pack_runtime_service import (
    _detect_promotion_intent,
    _format_service_not_found_reply,
    _has_contact_signal,
    _has_duration_signal,
    _has_guest_waiting_signal,
    _has_parking_signal,
    _has_price_signal,
    _match_service,
    _normalize_text,
    get_signal_lexicon_list,
    get_system_lexicon_list,
    load_yaml_truth,
)

from . import decision as _decision

_DECISION_MODULE = _decision
ACKNOWLEDGEMENT_RESPONSE = _DECISION_MODULE.ACKNOWLEDGEMENT_RESPONSE
Conversation = _DECISION_MODULE.Conversation
DecisionOutcome = _DECISION_MODULE.DecisionOutcome
DecisionSignals = _DECISION_MODULE.DecisionSignals
DomainIntent = _DECISION_MODULE.DomainIntent
GREETING_RESPONSE = _DECISION_MODULE.GREETING_RESPONSE
Intent = _DECISION_MODULE.Intent
IntentRoutingState = _DECISION_MODULE.IntentRoutingState
Message = _DECISION_MODULE.Message
PackDecision = _DECISION_MODULE.PackDecision
THANKS_RESPONSE = _DECISION_MODULE.THANKS_RESPONSE
_compact_signal_snapshot = _DECISION_MODULE._compact_signal_snapshot
_is_env_enabled = _DECISION_MODULE._is_env_enabled
_normalize_service_text = _DECISION_MODULE._normalize_service_text
_record_decision_trace = _DECISION_MODULE._record_decision_trace
_set_router_observability = _DECISION_MODULE._set_router_observability
_should_escalate_to_pending = _DECISION_MODULE._should_escalate_to_pending
_update_message_decision_metadata = _DECISION_MODULE._update_message_decision_metadata
_update_message_signal_snapshot = _DECISION_MODULE._update_message_signal_snapshot
classify_intent = _DECISION_MODULE.classify_intent
is_bot_status_question = _DECISION_MODULE.is_bot_status_question
is_frustration_message = _DECISION_MODULE.is_frustration_message
is_human_request_message = _DECISION_MODULE.is_human_request_message
is_rejection = _DECISION_MODULE.is_rejection
logger = _DECISION_MODULE.logger
should_escalate = _DECISION_MODULE.should_escalate


_BOOKING_VERIFICATION_PATTERNS = (
    re.compile(r"\bпров\w*\b.*\b(запис|брон|бронир)\w*"),
    re.compile(r"\bподтверд\w*\b.*\b(запис|брон|бронир)\w*"),
    re.compile(r"\bподтверд\w*\b.*\b(дат|врем)\w*"),
    re.compile(r"\b(жду|ожидаю|не получил\w*)\b.*\b(подтвержд|ответ)\w*"),
    re.compile(r"\b(check|verify|confirm)\b.*\b(booking|appointment|reservation)\b"),
)


def _legacy_looks_like_booking_verification_request(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in _BOOKING_VERIFICATION_PATTERNS)


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
    if _detect_promotion_intent(normalized, client_slug=client_slug) is not None:
        return False
    if client_slug and "services_overview" in phrase_match_intent(text, client_slug):
        return True
    markers = _signal_phrase_list(client_slug, "services_overview_phrases")
    for phrase in get_system_lexicon_list("services_overview_phrases"):
        token = phrase.strip() if isinstance(phrase, str) else ""
        if token and token not in markers:
            markers.append(token)
    return bool(markers and _normalized_contains_any(normalized, markers))


def _is_timeout_pending_time_slot_question(
    *,
    message_text: str | None,
    client_slug: str | None,
    expected_reply_type: str | None,
    expected_reply_matched: bool | None,
    expected_reply_blocked_by_info: bool,
    booking_service: str | None,
    intent_decomp_payload: dict[str, Any] | None,
    now,
) -> bool:
    if (
        expected_reply_type != EXPECTED_REPLY_TIME
        or not isinstance(message_text, str)
        or not message_text.strip()
        or expected_reply_matched is True
        or not expected_reply_blocked_by_info
    ):
        return False
    normalized_message = normalize_for_matching(message_text)
    if not normalized_message:
        return False
    time_preference_statement = _looks_like_time_preference_statement(
        message_text,
        normalized_text=normalized_message,
    )
    question_like = "?" in message_text
    if not question_like:
        tokens = normalized_message.split()
        if tokens:
            question_like = any(tokens[0].startswith(prefix) for prefix in QUESTION_WORD_PREFIXES)
    if not question_like and not time_preference_statement:
        return False
    if _validate_expected_reply_value(
        expected_reply_type=expected_reply_type,
        value=message_text,
        client_slug=client_slug,
    ):
        return False
    normalized_service_message = _normalize_text(message_text)
    if _has_price_signal(normalized_service_message, message_text):
        return False
    if _has_duration_signal(normalized_service_message, message_text) and not time_preference_statement:
        return False
    if _is_style_reference_request(message_text, has_media=False):
        return False
    if _looks_like_booking_reschedule_request(
        message_text,
        client_slug=client_slug,
    ):
        return False
    try:
        if _extract_datetime(
            message_text,
            client_slug=client_slug,
            relative_base=now,
        ):
            return False
    except TypeError:
        if _extract_datetime(message_text, client_slug=client_slug):
            return False
    master_resolution = resolve_master_intent(
        message_text=message_text,
        client_slug=client_slug,
        service_query=booking_service,
        intent_decomp=intent_decomp_payload,
    )
    if master_resolution.explicit:
        return False
    return bool(
        time_preference_statement
        or _has_daypart_stem(normalized_message)
        or _has_pending_time_question_marker(normalized_message)
    )


def _is_timeout_master_info_interrupt_candidate(
    *,
    message_text: str | None,
    client_slug: str | None,
    expected_reply_type: str | None,
    expected_reply_matched: bool | None,
    expected_reply_blocked_by_info: bool,
    booking_service: str | None,
    intent_decomp_payload: dict[str, Any] | None,
) -> bool:
    if (
        expected_reply_type != EXPECTED_REPLY_NAME
        or not isinstance(message_text, str)
        or not message_text.strip()
        or expected_reply_matched is True
        or not expected_reply_blocked_by_info
    ):
        return False
    master_resolution = resolve_master_intent(
        message_text=message_text,
        client_slug=client_slug,
        service_query=booking_service,
        intent_decomp=intent_decomp_payload if isinstance(intent_decomp_payload, dict) else None,
        force_master_intent=False,
    )
    return bool(master_resolution.explicit)


def _is_timeout_active_time_specialist_interrupt_candidate(
    *,
    message_text: str | None,
    client_slug: str | None,
    expected_reply_type: str | None,
    expected_reply_matched: bool | None,
    expected_reply_blocked_by_info: bool,
    booking_service: str | None,
    intent_decomp_payload: dict[str, Any] | None,
) -> bool:
    if (
        expected_reply_type != EXPECTED_REPLY_TIME
        or not isinstance(message_text, str)
        or not message_text.strip()
        or expected_reply_matched is True
        or not expected_reply_blocked_by_info
    ):
        return False
    master_resolution = resolve_master_intent(
        message_text=message_text,
        client_slug=client_slug,
        service_query=booking_service,
        intent_decomp=intent_decomp_payload if isinstance(intent_decomp_payload, dict) else None,
        force_master_intent=False,
    )
    return bool(master_resolution.explicit)


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
    if _looks_like_services_overview_message(text, client_slug=client_slug):
        return False
    return _looks_like_promotions_request(text, client_slug=client_slug)


def _looks_like_promotions_rules_policy_message(
    text: str | None,
    *,
    client_slug: str | None = None,
    explicit_service_query: str | None = None,
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
    if isinstance(explicit_service_query, str) and explicit_service_query.strip():
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
    intents = {intent for intent in intent_decomp_set if intent in INFO_INTENTS}
    meta: dict[str, Any] = {}
    explicit_service_query = (
        service_query.strip()
        if isinstance(service_query, str) and service_query.strip()
        else None
    )
    normalized = normalize_for_matching(message_text) if message_text else ""
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
    price_signal = _has_price_signal(
        normalized,
        message_text,
        client_slug=client_slug,
    )
    duration_signal = _has_duration_signal(
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
                for token in normalize_for_matching(address_full).split()
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
    if not hours_signal and question_like:
        why_booking_schedule_question = (
            _has_token_prefix(tokens, "почему")
            and _signal_any_match(normalized, client_slug, "booking_keywords")
            and _signal_any_match(normalized, client_slug, "hours_question_time_phrases")
        )
        if why_booking_schedule_question:
            hours_signal = True
            meta["booking_schedule_question"] = True
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
        explicit_service_query=explicit_service_query,
    )
    promotions_signal = False
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
            and explicit_service_query
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
        question_type = semantic_question_type(message_text, include_kinds=INFO_INTENTS)
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
        if _looks_like_promotions_request(message_text, client_slug=client_slug):
            return True
        if client_slug and "order_booking" in phrase_match_intent(message_text, client_slug):
            return True
        normalized = normalize_for_matching(message_text)
        if normalized and client_slug:
            truth = load_yaml_truth(client_slug)
            address = truth.get("salon", {}).get("address", {}) if isinstance(truth, dict) else {}
            address_full = address.get("full") if isinstance(address, dict) else None
            if isinstance(address_full, str) and address_full.strip():
                address_tokens = [
                    token
                    for token in normalize_for_matching(address_full).split()
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
        ) and _system_any_match(normalized, "booking_required_details_keywords"):
            return True
    return False


def _extract_service_hint(text: str | None, client_slug: str | None) -> str | None:
    if not text:
        return None
    if not isinstance(client_slug, str):
        return None
    slug = client_slug.strip()
    if not slug:
        return None
    cleaned_text = re.sub(r"\[[^\]]+\]", " ", text).strip()
    if not cleaned_text:
        return None
    normalized_text = _DECISION_MODULE._normalize_service_text(cleaned_text)
    if not normalized_text:
        return None
    match = _match_service(normalized_text, slug)
    if not isinstance(match, dict):
        return None
    canonical_name = match.get("name")
    if isinstance(canonical_name, str) and canonical_name.strip():
        return canonical_name.strip()
    return None


def _legacy_is_booking_request(text: str, *, client_slug: str | None) -> bool:
    if _DECISION_MODULE._matches_booking_request_lexicon(text, client_slug=client_slug):
        return True
    normalized = normalize_for_matching(text)
    if not normalized:
        return False
    booking_keywords = _DECISION_MODULE.get_system_lexicon_list("booking_keywords")
    if booking_keywords and _DECISION_MODULE._contains_any(normalized, booking_keywords):
        return True
    desire_keywords = _DECISION_MODULE.get_system_lexicon_list("booking_desire_keywords")
    need_or_desire_signal = bool(
        desire_keywords and _DECISION_MODULE._contains_any(normalized, desire_keywords)
    )
    if not need_or_desire_signal or not client_slug:
        return False
    cleaned_text = re.sub(r"\[[^\]]+\]", " ", text)
    normalized_service = _DECISION_MODULE._normalize_service_text(cleaned_text)
    if not normalized_service:
        return False
    if not (
        _match_service(normalized_service, client_slug)
        or _DECISION_MODULE._matches_service_request_lexicon(normalized_service, client_slug)
    ):
        return False
    try:
        has_datetime_signal = bool(
            _DECISION_MODULE._extract_datetime(cleaned_text, client_slug=client_slug)
        )
    except TypeError:
        has_datetime_signal = bool(_DECISION_MODULE._extract_datetime(cleaned_text))
    if not has_datetime_signal:
        return False
    info_intents, _ = _detect_info_class_intents(
        cleaned_text,
        intent_decomp_set=set(),
        client_slug=client_slug,
    )
    return not bool({"location", "hours", "parking"} & info_intents)


def _legacy_evaluate_booking_signal(
    messages: list[str],
    *,
    client_slug: str | None,
    message_text: str | None,
    relative_base=None,
) -> tuple[bool, dict | None]:
    if not messages:
        return False, None
    if any(_legacy_is_booking_request(message, client_slug=client_slug) for message in messages):
        return True, None
    has_service = any(_extract_service_hint(message, client_slug) for message in messages)
    has_datetime = any(
        _DECISION_MODULE._extract_datetime(
            message,
            client_slug=client_slug,
            relative_base=relative_base,
        )
        for message in messages
    )
    booking_signal = bool(has_service and has_datetime)
    if booking_signal and message_text:
        if _looks_like_info_query(message_text, client_slug=client_slug):
            return False, {"booking_blocked_reason": "info_question"}
        normalized = normalize_for_matching(message_text)
        procedure_combo_any = _DECISION_MODULE.get_signal_lexicon_list(
            client_slug,
            "procedure_combo_require_any",
        )
        procedure_combo_all = _DECISION_MODULE.get_signal_lexicon_list(
            client_slug,
            "procedure_combo_require_all",
        )
        if (
            normalized
            and procedure_combo_any
            and procedure_combo_all
            and _DECISION_MODULE._contains_any(normalized, procedure_combo_any)
            and _DECISION_MODULE._contains_any(normalized, procedure_combo_all)
        ):
            return False, {"booking_blocked_reason": "procedure_combo"}
        segments = [
            segment.strip()
            for segment in re.split(r"[?!\.,;]+", message_text)
            if segment.strip()
        ]
        if not segments:
            segments = [message_text.strip()]
        for segment in segments:
            question_type = semantic_question_type(
                segment,
                include_kinds=_DECISION_MODULE.BOOKING_INFO_QUESTION_TYPES,
                client_slug=client_slug,
            )
            if question_type and question_type.kind in _DECISION_MODULE.BOOKING_INFO_QUESTION_TYPES:
                return (
                    False,
                    {
                        "booking_blocked_reason": "info_question",
                        "question_type": question_type.kind,
                        "question_type_score": question_type.score,
                    },
                )
    return booking_signal, None


def _legacy_has_booking_signal(
    messages: list[str],
    *,
    client_slug: str | None = None,
    message_text: str | None = None,
) -> bool:
    booking_signal, _ = _legacy_evaluate_booking_signal(
        messages,
        client_slug=client_slug,
        message_text=message_text,
    )
    return booking_signal


def _preflight_booking_block(
    *,
    message_text: str | None,
    client_config: dict | None,
    booking_active: bool,
) -> dict | None:
    if booking_active or not message_text:
        return None
    if (
        is_greeting_message(message_text)
        or is_thanks_message(message_text)
        or is_acknowledgement_message(message_text)
        or is_low_signal_message(message_text)
    ):
        return {"booking_blocked_reason": "intent_signal"}
    domain_intent, in_score, out_score, _ = classify_domain_with_scores(
        message_text,
        client_config,
    )
    strong_out, _ = is_strong_out_of_domain(
        message_text,
        domain_intent,
        in_score,
        out_score,
        client_config,
    )
    if strong_out:
        return {"booking_blocked_reason": "out_of_domain_signal"}
    return None


def _looks_like_time_only_request(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    time_only_phrases = get_system_lexicon_list("time_only_request_phrases")
    if time_only_phrases and _contains_any(normalized, time_only_phrases):
        return True
    tokens = _tokenize_for_matching(normalized)
    if not tokens:
        return False
    has_time_token = False
    has_time_marker = bool(TIME_PATTERN.search(message_text) or TIME_HOUR_PATTERN.search(message_text))
    for token in tokens:
        if token.isdigit():
            if len(token) <= 2:
                has_time_token = True
                continue
            if has_time_marker and len(token) in (3, 4):
                has_time_token = True
                continue
            return False
        if TIME_ONLY_AMPM_PATTERN.fullmatch(token):
            has_time_token = True
            continue
        if token in TIME_ONLY_ALLOWED_TOKENS:
            continue
        if any(token.startswith(prefix) for prefix in TIME_ONLY_ALLOWED_PREFIXES):
            has_time_marker = True
            continue
        return False
    return has_time_token


def _extract_pack_index_meta(client_config: dict | None) -> dict[str, Any] | None:
    if not isinstance(client_config, dict):
        return None
    pack_index = client_config.get("pack_index")
    if not isinstance(pack_index, dict):
        return None
    meta = _compact_signal_snapshot(
        {
            "schema_version": pack_index.get("schema_version"),
            "hash": pack_index.get("hash"),
            "version_id": pack_index.get("version_id"),
            "compiled_at": pack_index.get("compiled_at"),
            "source": pack_index.get("source"),
        }
    )
    return meta or None


def _extract_compiled_pack_meta(client_config: dict | None) -> dict[str, Any] | None:
    if not isinstance(client_config, dict):
        return None
    compiled_pack = client_config.get("compiled_pack")
    if not isinstance(compiled_pack, dict):
        return None
    meta = _compact_signal_snapshot(
        {
            "schema_version": compiled_pack.get("schema_version"),
            "hash": compiled_pack.get("hash"),
            "version_id": compiled_pack.get("version_id"),
            "compiled_at": compiled_pack.get("compiled_at"),
            "source": compiled_pack.get("source"),
        }
    )
    return meta or None


def _detect_fast_intent(
    message_text: str,
    *,
    policy_type: str | None,
    booking_wants_flow: bool,
    bypass_domain_flows: bool,
) -> PackDecision | None:
    del policy_type
    if not message_text or booking_wants_flow or bypass_domain_flows:
        return None

    if is_greeting_message(message_text):
        return _DECISION_MODULE.PackDecision(
            action="smalltalk",
            response=GREETING_RESPONSE,
            intent="greeting",
        )
    if is_thanks_message(message_text):
        return _DECISION_MODULE.PackDecision(
            action="smalltalk",
            response=THANKS_RESPONSE,
            intent="thanks",
        )
    if is_acknowledgement_message(message_text):
        return _DECISION_MODULE.PackDecision(
            action="smalltalk",
            response=ACKNOWLEDGEMENT_RESPONSE,
            intent="ack",
        )
    return None


def _detect_intent_signals(message_text: str, *, timing_context: dict | None = None) -> DecisionSignals:
    intent_hint = None
    if isinstance(timing_context, dict):
        hinted = timing_context.get("short_intent_hint")
        if isinstance(hinted, str):
            try:
                intent_hint = _DECISION_MODULE.Intent(hinted)
            except ValueError:
                intent_hint = None

    is_greeting = is_greeting_message(message_text)
    is_thanks = is_thanks_message(message_text)
    is_ack = is_acknowledgement_message(message_text)
    is_low_signal = is_low_signal_message(message_text)
    is_status_question = is_bot_status_question(message_text)
    is_human_request = is_human_request_message(message_text)

    if is_human_request:
        intent = _DECISION_MODULE.Intent.HUMAN_REQUEST
        logger.info("Intent shortcut: human_request (lexicon)")
    elif intent_hint == _DECISION_MODULE.Intent.GREETING:
        intent = _DECISION_MODULE.Intent.GREETING
        logger.info("Intent shortcut: greeting (llm hint)")
    elif intent_hint == _DECISION_MODULE.Intent.THANKS:
        intent = _DECISION_MODULE.Intent.THANKS
        logger.info("Intent shortcut: thanks (llm hint)")
    elif intent_hint == _DECISION_MODULE.Intent.QUESTION:
        intent = _DECISION_MODULE.Intent.QUESTION
        logger.info("Intent shortcut: question (llm hint)")
    elif is_greeting:
        intent = _DECISION_MODULE.Intent.GREETING
        logger.info("Intent shortcut: greeting")
    elif is_thanks:
        intent = _DECISION_MODULE.Intent.THANKS
        logger.info("Intent shortcut: thanks")
    elif is_ack or is_low_signal:
        intent = _DECISION_MODULE.Intent.OTHER
        logger.info("Intent shortcut: acknowledgement/low-signal -> other")
    else:
        intent = classify_intent(message_text, timing_context=timing_context)
        logger.info(f"Intent classified: {intent.value}")

    if (
        intent_hint
        in {
            _DECISION_MODULE.Intent.GREETING,
            _DECISION_MODULE.Intent.THANKS,
            _DECISION_MODULE.Intent.QUESTION,
        }
        and intent != _DECISION_MODULE.Intent.HUMAN_REQUEST
    ):
        is_greeting = intent_hint == _DECISION_MODULE.Intent.GREETING
        is_thanks = intent_hint == _DECISION_MODULE.Intent.THANKS
        is_ack = False
        is_low_signal = False
        is_status_question = False

    return DecisionSignals(
        intent=intent,
        is_greeting=is_greeting,
        is_thanks=is_thanks,
        is_ack=is_ack,
        is_low_signal=is_low_signal,
        is_status_question=is_status_question,
    )


def _resolve_action(
    *,
    routing: dict[str, bool],
    state: str,
    signals: DecisionSignals,
    is_pending_status_question: bool,
    style_reference: bool,
    in_domain_override: bool = False,
    out_of_domain_signal: bool,
    rag_confident: bool = False,
    llm_first_firebreak: bool = False,
) -> DecisionOutcome:
    if routing["allow_bot_reply"] and (signals.is_greeting or signals.is_thanks):
        return _DECISION_MODULE.DecisionOutcome("smalltalk")
    if routing["allow_bot_reply"] and state == ConversationState.PENDING.value and is_pending_status_question:
        return _DECISION_MODULE.DecisionOutcome("pending_status")
    if routing["allow_bot_reply"] and signals.is_status_question:
        return _DECISION_MODULE.DecisionOutcome("bot_status")
    if routing["allow_bot_reply"] and style_reference:
        return _DECISION_MODULE.DecisionOutcome("style_reference")
    if routing["allow_bot_reply"] and in_domain_override:
        return _DECISION_MODULE.DecisionOutcome("ai_response")
    firebreak_reasons = _llm_first_firebreak_semantic_reasons(
        routing=routing,
        signals=signals,
        out_of_domain_signal=out_of_domain_signal,
        rag_confident=rag_confident,
        llm_first_firebreak=llm_first_firebreak,
    )
    if firebreak_reasons:
        return _DECISION_MODULE.DecisionOutcome("ai_response")
    if routing["allow_bot_reply"] and (out_of_domain_signal or signals.is_low_signal) and not rag_confident:
        return _DECISION_MODULE.DecisionOutcome("out_of_domain")
    if _should_escalate_to_pending(routing, signals.intent):
        return _DECISION_MODULE.DecisionOutcome("escalate")
    if should_escalate(signals.intent) and not routing["allow_handover_create"]:
        return _DECISION_MODULE.DecisionOutcome("pending_escalation")
    if is_rejection(signals.intent):
        return _DECISION_MODULE.DecisionOutcome("rejection")
    if routing["allow_bot_reply"]:
        return _DECISION_MODULE.DecisionOutcome("ai_response")
    return _DECISION_MODULE.DecisionOutcome("unknown_state")


def _llm_first_firebreak_semantic_reasons(
    *,
    routing: dict[str, bool],
    signals: DecisionSignals,
    out_of_domain_signal: bool,
    rag_confident: bool,
    llm_first_firebreak: bool,
) -> list[str]:
    if not llm_first_firebreak or not routing.get("allow_bot_reply", False):
        return []

    reasons: list[str] = []
    if (out_of_domain_signal or signals.is_low_signal) and not rag_confident:
        reasons.append("out_of_domain_signal" if out_of_domain_signal else "low_signal")
    if _should_escalate_to_pending(routing, signals.intent):
        reasons.append("escalate_to_pending_intent")
    if should_escalate(signals.intent) and not routing.get("allow_handover_create", False):
        reasons.append("pending_without_handover_create")
    if is_rejection(signals.intent):
        reasons.append("rejection_intent")
    return reasons


def _run_class_router_stage(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    message_text: str | None,
    client_slug: str | None,
    client_config: dict | None,
    remote_jid: str | None,
    timing_context: dict | None,
    info_class_intents: set[str],
    info_class_meta: dict[str, Any],
    booking_signal: bool,
    class_carryover: dict | None,
    router_state: dict | None,
    intent_decomp_payload: dict[str, Any] | None,
    expected_reply_shortcircuit: bool,
    log_timing: Callable[[str, float, dict | None], None],
) -> IntentRoutingState:
    intent_t0 = time.monotonic()
    decision_text = _DECISION_MODULE._normalize_message_text(message_text)
    signals = _detect_intent_signals(decision_text, timing_context=timing_context)
    intent = signals.intent
    intent_contract, intent_error = _DECISION_MODULE.build_intent_contract(
        signals,
        intent_decomp_payload,
    )
    _record_decision_trace(
        conversation,
        {
            "stage": "contract",
            "decision": "intent",
            "contract_ok": intent_error is None,
            "contract_error": intent_error,
            "contract": intent_contract,
        },
    )

    domain_intent = DomainIntent.UNKNOWN
    domain_in_score = 0.0
    domain_out_score = 0.0
    domain_meta: dict = {}
    if (
        conversation.state == ConversationState.BOT_ACTIVE.value
        and not (signals.is_greeting or signals.is_thanks or signals.is_ack or signals.is_low_signal)
        and not signals.is_status_question
    ):
        domain_intent, domain_in_score, domain_out_score, domain_meta = classify_domain_with_scores(
            message_text,
            client_config,
        )
        log_scores = _is_env_enabled(
            os.environ.get("DOMAIN_ROUTER_LOG_SCORES"),
            default=False,
        )
        if log_scores and (
            domain_intent != DomainIntent.UNKNOWN or max(domain_in_score, domain_out_score) >= 0.45
        ):
            logger.info(
                "Domain scores",
                extra={
                    "context": {
                        "client_slug": client_slug,
                        "remote_jid": remote_jid,
                        "intent": intent.value,
                        "domain_intent": domain_intent.value,
                        "in_score": round(domain_in_score, 4),
                        "out_score": round(domain_out_score, 4),
                        "in_threshold": domain_meta.get("in_threshold"),
                        "out_threshold": domain_meta.get("out_threshold"),
                        "margin": domain_meta.get("margin"),
                        "out_hits": domain_meta.get("out_hits"),
                        "strict_in_hits": domain_meta.get("strict_in_hits"),
                        "matched_in": domain_meta.get("matched_in"),
                        "matched_out": domain_meta.get("matched_out"),
                        "matched_strict_in": domain_meta.get("matched_strict_in"),
                        "anchors_in": domain_meta.get("anchors_in"),
                        "anchors_out": domain_meta.get("anchors_out"),
                        "strict_in_anchors": domain_meta.get("strict_in_anchors"),
                        "message_len": len(message_text),
                        "message_preview": message_text[:80],
                    }
                },
            )

    domain_out_hits = int(domain_meta.get("out_hits") or 0)
    domain_strict_in_hits = int(domain_meta.get("strict_in_hits") or 0)
    explicit_service_signal = _has_explicit_service_signal(
        message_text,
        client_slug=client_slug,
        intent_decomp_payload=intent_decomp_payload,
    )
    class_router_result = _resolve_class_router_result(
        info_intents=info_class_intents,
        info_meta=info_class_meta,
        booking_signal=booking_signal,
        class_carryover=class_carryover,
        domain_intent=domain_intent,
        domain_meta=domain_meta,
        router_state=router_state,
        explicit_service_signal=explicit_service_signal,
    )
    out_of_domain_signal = class_router_result["out_of_domain_signal"]
    in_signals = class_router_result.get("in_signals") or []
    controller_booking_hint = False
    controller_meta_hint = class_router_result.get("controller") if isinstance(class_router_result, dict) else None
    controller_output_hint = (
        controller_meta_hint.get("output") if isinstance(controller_meta_hint, dict) else None
    )
    if isinstance(controller_output_hint, dict):
        controller_goal_hint = controller_output_hint.get("goal")
        controller_class_hint = controller_output_hint.get("class")
        controller_booking_hint = (
            isinstance(controller_goal_hint, str)
            and controller_goal_hint.strip().casefold() in {"booking", "reschedule", "cancel_request"}
        ) or (
            isinstance(controller_class_hint, str)
            and controller_class_hint.strip().casefold() == "booking"
        )
    if (
        conversation.state == ConversationState.BOT_ACTIVE.value
        and intent == _DECISION_MODULE.Intent.OTHER
        and not expected_reply_shortcircuit
        and not in_signals
        and not out_of_domain_signal
        and not controller_booking_hint
    ):
        out_of_domain_signal = True
        out_signals = list(class_router_result.get("out_signals") or [])
        if "intent_other" not in out_signals:
            out_signals.append("intent_other")
        class_router_result["out_signals"] = out_signals
        classes = list(class_router_result.get("classes") or [])
        if "out_of_domain" not in classes:
            classes.append("out_of_domain")
        class_router_result["classes"] = classes
        class_router_result["out_of_domain_signal"] = True
    log_timing(
        "intent_ms",
        (time.monotonic() - intent_t0) * 1000,
        {
            "intent": intent.value,
            "domain_intent": domain_intent.value,
            "out_of_domain_signal": out_of_domain_signal,
            "out_hits": domain_out_hits,
            "strict_in_hits": domain_strict_in_hits,
            "class_router": class_router_result,
        },
    )

    router_meta = _set_router_observability(
        saved_message,
        eligible=not expected_reply_shortcircuit,
        reason="expected_reply_shortcircuit" if expected_reply_shortcircuit else "none",
    )
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
        "out_of_domain_signal": out_of_domain_signal,
        "explicit_service_signal": explicit_service_signal,
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
    trace_payload.update(router_meta)
    _record_decision_trace(conversation, trace_payload)
    if saved_message:
        _update_message_decision_metadata(
            saved_message,
            {
                "class_router": class_router_result,
                "carryover_class": class_router_result.get("carryover_class"),
                "router_fallback_reason": class_router_result.get("router_fallback_reason"),
                "controller_used": controller_used,
                "controller_attempted": controller_attempted,
                "controller_fallback": controller_fallback,
                "controller_low_confidence": controller_low_confidence,
                "controller_used_reason": controller_used_reason,
                "controller_confidence": controller_confidence,
                "controller_error": controller_error,
                "controller_goal": controller_goal,
                "controller_fallback_reason": class_router_result.get("controller_fallback_reason"),
            },
        )
        intent_value = getattr(signals.intent, "value", None)
        domain_snapshot = _compact_signal_snapshot(
            {
                "intent": getattr(domain_intent, "value", None),
                "in_score": domain_in_score,
                "out_score": domain_out_score,
                "in_hits": domain_meta.get("in_hits"),
                "out_hits": domain_meta.get("out_hits"),
                "strict_in_hits": domain_meta.get("strict_in_hits"),
                "matched_in": domain_meta.get("matched_in"),
                "matched_out": domain_meta.get("matched_out"),
                "matched_strict_in": domain_meta.get("matched_strict_in"),
                "in_threshold": domain_meta.get("in_threshold"),
                "out_threshold": domain_meta.get("out_threshold"),
                "margin": domain_meta.get("margin"),
                "in_hit_threshold": domain_meta.get("in_hit_threshold"),
                "out_hit_threshold": domain_meta.get("out_hit_threshold"),
                "strict_in_hit_threshold": domain_meta.get("strict_in_hit_threshold"),
                "anchors_in": domain_meta.get("anchors_in"),
                "anchors_out": domain_meta.get("anchors_out"),
                "strict_in_anchors": domain_meta.get("strict_in_anchors"),
            }
        )
        controller_snapshot = _compact_signal_snapshot(
            {
                "used": controller_used,
                "attempted": controller_attempted,
                "fallback": controller_fallback,
                "low_confidence": controller_low_confidence,
                "confidence": controller_confidence,
                "goal": controller_goal,
                "error": controller_error,
                "fallback_reason": class_router_result.get("controller_fallback_reason"),
            }
        )
        class_router_snapshot = _compact_signal_snapshot(
            {
                "classes": class_router_result.get("classes"),
                "intents": class_router_result.get("intents"),
                "in_signals": class_router_result.get("in_signals"),
                "out_signals": class_router_result.get("out_signals"),
                "explicit_service_signal": explicit_service_signal,
                "out_of_domain_signal": out_of_domain_signal,
                "router_fallback_reason": class_router_result.get("router_fallback_reason"),
                "controller": controller_snapshot or None,
            }
        )
        signal_snapshot = _compact_signal_snapshot(
            {
                "intent_signals": _compact_signal_snapshot(
                    {
                        "intent": intent_value,
                        "is_greeting": signals.is_greeting,
                        "is_thanks": signals.is_thanks,
                        "is_ack": signals.is_ack,
                        "is_low_signal": signals.is_low_signal,
                        "is_status_question": signals.is_status_question,
                    }
                ),
                "domain_router": domain_snapshot,
                "class_router": class_router_snapshot,
                "pack_index": _extract_pack_index_meta(client_config),
                "compiled_pack": _extract_compiled_pack_meta(client_config),
            }
        )
        _update_message_signal_snapshot(saved_message, signal_snapshot)

    _record_decision_trace(
        conversation,
        {
            "stage": "intent",
            "decision": intent.value,
            "state": conversation.state,
            "domain_intent": domain_intent.value,
            "out_of_domain_signal": out_of_domain_signal,
            "rag_confident": False,
            "out_hits": domain_out_hits,
            "strict_in_hits": domain_strict_in_hits,
            "info_intents": sorted(info_class_intents),
        },
    )

    return _DECISION_MODULE.IntentRoutingState(
        signals=signals,
        intent=intent,
        domain_intent=domain_intent,
        domain_meta=domain_meta,
        class_router_result=class_router_result,
        out_of_domain_signal=out_of_domain_signal,
    )


def _should_use_expected_reply_collect_fast_path(
    *,
    message_text: str | None,
    expected_reply_type: str | None,
    expected_reply_matched: bool | None,
    expected_reply_blocked_by_info: bool,
    intent_decomp_set: set[str],
    info_class_intents: set[str] | list[str] | tuple[str, ...] | None,
    booking_wants_flow: bool,
    booking_slot_signal: bool,
    consult_intent: bool,
    booking_reference_present: bool,
    booking_slots_complete: bool,
    refusal_flags: dict[str, bool] | None,
    client_slug: str | None,
) -> bool:
    fast_path_enabled = str(
        os.environ.get("POLICY_CORE_EXPECTED_REPLY_COLLECT_FAST_PATH", "0")
    ).strip().lower() in {"1", "true", "yes", "on"}
    if not fast_path_enabled:
        return False
    if expected_reply_type not in {EXPECTED_REPLY_SERVICE, EXPECTED_REPLY_TIME, EXPECTED_REPLY_NAME}:
        return False
    if expected_reply_matched is not False or expected_reply_blocked_by_info:
        return False
    normalized_text = message_text.strip() if isinstance(message_text, str) else ""
    if not normalized_text:
        return False
    if not booking_wants_flow or consult_intent:
        return False
    if info_class_intents:
        return False
    allow_intent_override = False
    if intent_decomp_set == {"other"} and not booking_slot_signal:
        return False
    if intent_decomp_set != {"other"}:
        verification_intents = {
            "check_booking",
            "verify_booking",
            "confirm_booking",
            "booking_confirmation",
        }
        allow_verification_collect = bool(
            intent_decomp_set
            and intent_decomp_set <= verification_intents
            and expected_reply_type in {EXPECTED_REPLY_NAME, EXPECTED_REPLY_TIME}
            and not booking_reference_present
        )
        allow_booking_collect = bool(
            intent_decomp_set == {"booking"}
            and expected_reply_type in {EXPECTED_REPLY_SERVICE, EXPECTED_REPLY_TIME, EXPECTED_REPLY_NAME}
            and not booking_reference_present
            and (
                not booking_slots_complete
                or expected_reply_type in {EXPECTED_REPLY_NAME, EXPECTED_REPLY_TIME}
            )
        )
        if not (allow_verification_collect or allow_booking_collect):
            return False
        allow_intent_override = True
    if booking_slot_signal and not allow_intent_override:
        return False
    if _looks_like_info_query(normalized_text, client_slug=client_slug):
        return False
    if expected_reply_type == EXPECTED_REPLY_TIME and isinstance(client_slug, str) and client_slug.strip():
        normalized_service = _normalize_service_text(normalized_text)
        if normalized_service and (
            _match_service(normalized_service, client_slug)
            or _DECISION_MODULE._matches_service_request_lexicon(normalized_service, client_slug)
        ):
            return False
    if is_human_request_message(normalized_text) or is_frustration_message(normalized_text):
        return False
    if isinstance(refusal_flags, dict) and any(bool(value) for value in refusal_flags.values()):
        return False
    return True


def _build_expected_reply_collect_fast_policy_result(
    *,
    expected_reply_type: str | None,
    booking_state: dict[str, Any] | None,
) -> dict[str, Any] | None:
    collect_slot = _DECISION_MODULE._expected_reply_slot_key(expected_reply_type)
    if collect_slot not in {"service", "datetime", "name"}:
        return None
    slot_state: dict[str, str] = {}
    if isinstance(booking_state, dict):
        for slot_key in _DECISION_MODULE.BOOKING_SLOT_ORDER:
            value = booking_state.get(slot_key)
            if isinstance(value, str) and value.strip():
                slot_state[slot_key] = value.strip()
    payload = {
        "intent": "booking",
        "action": "collect",
        "tool_action": "collect",
        "tool_args": {},
        "pack_refs": [],
        "confidence": 1.0,
        "reason": "expected_reply_pending_collect_fast_path",
        "goal": "booking",
        "slots": slot_state,
        "next_question": collect_slot,
        "open_questions": [collect_slot],
        "needs_manager": False,
        "risk_signals": [],
    }
    return {
        "ok": True,
        "payload": payload,
        "error": None,
        "raw": None,
        "attempted": False,
        "elapsed_ms": 0.0,
        "compact_input_used": False,
        "compact_retry_used": False,
    }


# Explicit temporary surface for current repo consumers; do not widen without TP evidence.
_DECISION_EXPORTS = (
    "ACKNOWLEDGEMENT_RESPONSE",
    "ASR_LOW_CONFIDENCE_MIN_CHARS",
    "ASR_LOW_CONFIDENCE_MIN_DURATION_SECONDS",
    "ASR_LOW_CONFIDENCE_MIN_WORDS",
    "ASR_LOW_CONFIDENCE_NON_LETTER_RATIO",
    "AUDIO_TRANSCRIPTION_DEFAULT_MAX_MB",
    "BOOKING_INFO_QUESTION_TYPES",
    "CLARIFY_MAX_ATTEMPTS",
    "CLASS_CARRYOVER_KEY",
    "CONSULT_CONTEXT_KEY",
    "CONSULT_CONTEXT_TTL_MESSAGES",
    "CONSULT_INTERRUPT_INTENTS",
    "CONTROLLER_CONFIDENCE_THRESHOLD",
    "DecisionSignals",
    "DomainIntent",
    "EVENING_GREETING_KEY",
    "EVENING_GREETING_TTL_HOURS",
    "GREETING_RESPONSE",
    "LOW_CONFIDENCE_MAX_RETRIES",
    "MEDIA_MAX_DEFAULT_MB",
    "MEDIA_RATE_LIMIT_DEFAULTS",
    "MEDIA_STORAGE_DEFAULT_DIR",
    "MEDIA_STORAGE_MAX_BYTES",
    "MEDIA_TYPE_ALIASES",
    "MSG_BOOKING_ASK_ALL",
    "MSG_BOOKING_ASK_PHONE",
    "MSG_BOOKING_CANCELLED",
    "MSG_BOOKING_REENGAGE",
    "MSG_BOOKING_SLOT_LOCK_STUB",
    "MSG_ESCALATED",
    "MSG_FACT_GUARD_CLARIFY",
    "MSG_HANDOVER_CONFIRM",
    "MSG_LOW_CONFIDENCE_RETRY",
    "MSG_MEDIA_RATE_LIMIT",
    "MSG_MEDIA_TOO_LARGE",
    "MSG_MEDIA_UNSUPPORTED",
    "MSG_PENDING_ESCALATION",
    "MSG_PENDING_LOW_CONFIDENCE",
    "MSG_STYLE_REFERENCE_NEED_MEDIA",
    "NAME_NOISE_TOKENS",
    "NAME_PATTERN",
    "OUT_OF_DOMAIN_RESPONSE",
    "QUIET_HOURS_NOTICE_KEY",
    "QUIET_HOURS_NOTICE_TTL_MINUTES",
    "REENGAGE_CONFIRM_WINDOW_MINUTES",
    "ROUTING_MATRIX",
    "SERVICE_CARRYOVER_INTENTS",
    "SERVICE_CARRYOVER_KEY",
    "SERVICE_HINT_AT_KEY",
    "SERVICE_HINT_KEY",
    "SERVICE_HINT_WINDOW_MINUTES",
    "SESSION_MEMORY_KEY",
    "SESSION_MEMORY_RESET_PHRASES",
    "SESSION_MEMORY_TTL_HOURS",
    "SHIELD_CONTEXT_KEY",
    "SHIELD_LAST_TEXT_KEY",
    "SHIELD_MAX_MESSAGE_LENGTH",
    "SHIELD_MEANINGFUL_PATTERN",
    "SHIELD_RECENT_KEY",
    "SHIELD_SHORT_MESSAGE_LEN",
    "SHIELD_SPAM_MAX_MESSAGES",
    "SHIELD_SPAM_WINDOW_SECONDS",
    "SHIELD_TOXIC_PATTERNS",
    "STYLE_REFERENCE_HINT_TOKENS",
    "STYLE_REFERENCE_PATTERNS",
    "THANKS_RESPONSE",
    "TIME_HOUR_PATTERN",
    "TIME_PATTERN",
    "TOOL_VERIFIER_SLOT_BY_FIELD",
    "_append_followup",
    "_apply_expected_reply_slot",
    "_booking_clarify_guard_reason",
    "_booking_prompt_for_expected_reply_type",
    "_build_consult_return_prompt",
    "_build_controller_meta_output",
    "_clear_service_hint",
    "_clear_session_memory_expected_reply",
    "_combine_sidecar",
    "_compact_signal_snapshot",
    "_compose_fact_response",
    "_contains_any",
    "_controller_meta_updates_from_class_router",
    "_current_openai_api_key",
    "_derive_booking_followup_prompt",
    "_derive_rag_status",
    "_deserialize_media_decision",
    "_detect_llm_guard_topics",
    "_ensure_controller_output_meta",
    "_ensure_rag_meta_defaults",
    "_evaluate_media_decision",
    "_expected_reply_for_booking_question",
    "_extract_datetime",
    "_find_message_by_conversation_created_at",
    "_find_message_by_message_id",
    "_get_booking_context",
    "_get_canonical_dialog_state",
    "_get_clarify_attempt_state",
    "_get_class_carryover",
    "_get_consult_context",
    "_get_context_manager",
    "_get_conversation_context",
    "_get_debounce_redis",
    "_get_expected_reply_reason",
    "_get_expected_reply_type",
    "_get_intent_queue",
    "_get_low_confidence_retry_count",
    "_get_recent_service_hint",
    "_get_routing_policy",
    "_get_service_carryover",
    "_get_session_memory",
    "_get_user_branch_preference",
    "_handle_clarify_limit_escalation",
    "_handle_truth_gate_fallback",
    "_has_explicit_service_signal",
    "_has_timeout_slot_question_info_lock_surface",
    "_is_booking_cancel",
    "_is_booking_related_message",
    "_is_booking_slot_signal",
    "_is_booking_time_service_decision",
    "_is_booking_verification_handoff_intent",
    "_is_env_enabled",
    "_is_hygiene_context_text",
    "_is_re_entry_required",
    "_is_reengage_confirmation_active",
    "_is_refusal_flag_active",
    "_is_session_memory_expired",
    "_is_short_reply",
    "_is_style_reference_request",
    "_match_expected_reply_candidates",
    "_maybe_store_class_carryover",
    "_maybe_store_service_carryover",
    "_merge_rag_scores",
    "_next_booking_prompt",
    "_normalize_class_name",
    "_normalize_controller_fallback_reason",
    "_normalize_service_text",
    "_normalize_text",
    "_plan_has_complete_booking_slots",
    "_record_context_manager_decision",
    "_record_decision_trace",
    "_record_knowledge_backlog",
    "_record_message_decision_meta",
    "_record_session_memory_update",
    "_register_clarify_attempt",
    "_reset_low_confidence_retry",
    "_resolve_backlog_language",
    "_resolve_class_router_result",
    "_resolve_controller_signal_class",
    "_resolve_current_goal",
    "_resolve_policy_collect_interrupt_arbitration",
    "_router_observability_updates_from_class_router",
    "_run_intent_decomposition",
    "_select_expected_reply_message",
    "_select_intent_from_queue",
    "_set_booking_context",
    "_set_class_carryover",
    "_set_consult_context",
    "_set_context_manager",
    "_set_conversation_context",
    "_set_expected_reply_context",
    "_set_expected_reply_type",
    "_set_handover_confirmation",
    "_set_intent_queue",
    "_set_low_confidence_retry_count",
    "_set_re_entry_required",
    "_set_router_observability",
    "_set_service_hint",
    "_set_user_branch_preference",
    "_should_block_expected_reply_by_info",
    "_should_escalate_for_clarify",
    "_should_escalate_to_pending",
    "_should_preserve_active_name_time_availability_followup_owner",
    "_should_preserve_specialist_availability_followup_owner",
    "_should_run_booking_flow",
    "_should_run_demo_truth_gate",
    "_sync_canonical_dialog_state",
    "_update_booking_from_messages",
    "_update_compact_summary",
    "_update_message_decision_metadata",
    "_update_message_signal_snapshot",
    "_update_router_sla",
    "_update_session_memory_goal",
    "_update_session_memory_on_answer",
    "_validate_datetime_slot",
    "_validate_name_slot",
    "_verify_policy_tool_args_contract",
    "classify_intent",
    "detect_multi_intent",
    "detect_refusal_flags",
    "generate_bot_response",
    "interpret_expected_reply",
    "is_acknowledgement_message",
    "is_bot_status_question",
    "is_frustration_message",
    "is_greeting_message",
    "is_human_request_message",
    "is_low_signal_message",
    "is_opt_out_message",
    "is_rejection",
    "is_thanks_message",
    "logger",
    "normalize_for_matching",
    "rewrite_for_service_match",
    "route_dialogue_controller",
    "send_telegram_notification",
    "should_escalate",
    "should_offer_low_confidence_retry",
    "transition_state",
)

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

_DIRECT_EXPORTS = {
    "_POLICY_HANDLERS": _POLICY_HANDLERS,
    "_apply_consult_return": _apply_consult_return,
    "_apply_quiet_hours_notice": _apply_quiet_hours_notice,
    "_detect_fast_intent": _detect_fast_intent,
    "_detect_intent_signals": _detect_intent_signals,
    "_evaluate_booking_signal": _legacy_evaluate_booking_signal,
    "_extract_compiled_pack_meta": _extract_compiled_pack_meta,
    "_extract_pack_index_meta": _extract_pack_index_meta,
    "_extract_service_hint": _extract_service_hint,
    "_has_booking_signal": _legacy_has_booking_signal,
    "_is_booking_request": _legacy_is_booking_request,
    "_llm_first_firebreak_semantic_reasons": _llm_first_firebreak_semantic_reasons,
    "_maybe_append_booking_cta": _maybe_append_booking_cta,
    "_resolve_action": _resolve_action,
    "_run_class_router_stage": _run_class_router_stage,
    "_should_use_expected_reply_collect_fast_path": _should_use_expected_reply_collect_fast_path,
    "_build_expected_reply_collect_fast_policy_result": _build_expected_reply_collect_fast_policy_result,
    "route_dialogue_controller": route_dialogue_controller,
    "send_bot_response": send_bot_response,
    "_detect_info_class_intents": _detect_info_class_intents,
    "_format_discounts_reply_for_message": _format_discounts_reply_for_message,
    "_format_service_not_found_reply": _format_service_not_found_reply,
    "_looks_like_carryover_followup": _looks_like_carryover_followup,
    "_looks_like_hours_followup": _looks_like_hours_followup,
    "_looks_like_info_query": _looks_like_info_query,
    "_looks_like_promo_code_request": _looks_like_promo_code_request,
    "_looks_like_policy_topic": _looks_like_policy_topic,
    "_looks_like_booking_verification_request": _legacy_looks_like_booking_verification_request,
    "_looks_like_time_only_request": _looks_like_time_only_request,
    "_matches_guest_policy_lexicon": _booking_runtime_matches_guest_policy_lexicon,
    "_match_service": _match_service,
    "_get_policy_handler": _get_policy_handler,
    "_preflight_booking_block": _preflight_booking_block,
    "classify_domain_with_scores": classify_domain_with_scores,
}

globals().update(_SHARED_EXPORTS)
globals().update(_DIRECT_EXPORTS)
for _name in _DECISION_EXPORTS:
    if hasattr(_decision, _name):
        globals()[_name] = getattr(_decision, _name)

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

__all__ = sorted(
    set(_SHARED_EXPORTS)
    | set(_DIRECT_EXPORTS)
    | set(_DECISION_EXPORTS)
    | {
        "get_active_handover",
        "_reuse_active_handover",
        "_create_pending_escalation_with_notification",
        "escalate_to_pending",
        "manager_take",
        "manager_reassign",
        "manager_resolve",
        "manager_return",
        "manager_reopen",
        "resolve_active_handover_rejection",
    }
)

del _decision
del _DIRECT_EXPORTS
del _SHARED_EXPORTS
del _name
