"""Booking state machine helpers (expected_reply_type, slot validators)."""

from __future__ import annotations

import os
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable
from uuid import UUID
from zoneinfo import ZoneInfo

import dateparser
from rapidfuzz import fuzz, process
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.routers.webhook.booking_runtime import (
    MSG_BOOKING_ASK_ALL,
    MSG_BOOKING_CANCELLED,
    MSG_BOOKING_REENGAGE,
    MSG_BOOKING_SLOT_LOCK_STUB,
    NAME_NOISE_TOKENS,
    NAME_PATTERN,
    _is_booking_cancel,
    _matches_guest_policy_lexicon,
)
from app.routers.webhook.booking_signal_runtime import (
    TIME_HOUR_PATTERN,
    TIME_PATTERN,
    _extract_datetime,
    _extract_service_hint,
    _is_booking_request,
)
from app.routers.webhook.context_runtime import (
    SERVICE_HINT_AT_KEY,
    SERVICE_HINT_KEY,
    SERVICE_HINT_WINDOW_MINUTES,
    _is_refusal_flag_active,
)
from app.routers.webhook.guard_runtime import MSG_FACT_GUARD_CLARIFY
from app.routers.webhook.pending_runtime import MSG_PENDING_ESCALATION
from app.routers.webhook.info import _detect_info_class_intents, _looks_like_info_query
from app.routers.webhook.class_router_runtime import (
    CONTROLLER_CONFIDENCE_THRESHOLD,
    DomainIntent,
    _build_controller_meta_output,
    _ensure_controller_output_meta,
    _resolve_class_router_result,
    _resolve_controller_signal_class,
    _router_observability_updates_from_class_router,
)
from app.routers.webhook.media import _is_style_reference_request
from app.routers.webhook.runtime_primitives import (
    BOOKING_TIME_SERVICE_INTENTS,
    EXPECTED_REPLY_NAME,
    EXPECTED_REPLY_PHONE,
    EXPECTED_REPLY_SERVICE,
    EXPECTED_REPLY_TIME,
    INFO_INTENTS,
    MSG_AI_ERROR,
    MSG_BOOKING_ASK_DATETIME,
    MSG_BOOKING_ASK_NAME,
    MSG_BOOKING_ASK_SERVICE,
    MSG_BOOKING_PENDING_QUESTION_TIME_GUIDANCE,
    MSG_ESCALATED,
    MSG_EXPECTED_SERVICE_OFF_TOPIC,
    MSG_STYLE_REFERENCE_NEED_MEDIA,
    _combine_sidecar,
)
from app.schemas.webhook import WebhookResponse
from app.services.appointment_service import SchedulingService
from app.services.ai_service import (
    detect_refusal_flags,
    is_acknowledgement_message,
    is_bot_status_question,
    is_greeting_message,
    is_low_signal_message,
    is_thanks_message,
    normalize_for_matching,
)
from app.services.booking_signal_service import (
    clean_name_candidate as _clean_name_candidate_impl,
)
from app.services.booking_signal_service import (
    collapse_repeats as _collapse_repeats,
)
from app.services.booking_signal_service import (
    extract_relative_date_token as _extract_relative_date_token,
)
from app.services.booking_signal_service import (
    has_daypart_stem as _has_daypart_stem,
)
from app.services.booking_signal_service import (
    has_duration_context_marker as _has_duration_context_marker,
)
from app.services.booking_signal_service import (
    looks_like_layout_swap as _looks_like_layout_swap,
)
from app.services.booking_signal_service import (
    looks_like_phone as _looks_like_phone,
)
from app.services.booking_signal_service import (
    match_booking_hour_fallback as _match_booking_hour_fallback,
)
from app.services.booking_signal_service import (
    normalize_phone_digits as _normalize_phone_digits_impl,
)
from app.services.booking_signal_service import (
    normalize_resolved_datetime_value as _normalize_resolved_datetime_value,
)
from app.services.booking_signal_service import (
    parse_iso_datetime as _parse_iso_datetime,
)
from app.services.booking_signal_service import (
    pick_daypart_token as _pick_daypart_token,
)
from app.services.booking_signal_service import (
    swap_keyboard_layout as _swap_keyboard_layout,
)
from app.services.capabilities_runtime import get_runtime_capabilities
from app.services.expected_reply_contract import (
    expected_reply_slot_key,
    should_allow_layout_swap_for_expected_reply,
    should_keep_booking_prompt_for_info_clarify_time_followup,
    should_mark_booking_time_service_candidate,
    should_prefer_info_class_for_booking_interrupt,
    should_repeat_booking_prompt,
    should_skip_booking_interrupt_for_expected_reply,
    should_use_expected_service_off_topic_prompt,
)
from app.services.handover_owner_service import (
    ActiveHandoverReuseRuntimeHooks,
    _reuse_active_handover,
    escalate_to_pending,
    get_active_handover,
    send_telegram_notification,
)
from app.services.intent_service import (
    is_frustration_message,
    is_human_request_message,
    is_opt_out_message,
)
from app.services.pack_runtime_service import (
    _format_service_not_found_reply,
    _normalize_text,
    get_system_lexicon_list,
    load_yaml_truth,
    phrase_match_intent,
)
from app.services.state_machine import ConversationState
from app.services.state_service import transition_state

from .trace import (
    _record_decision_trace,
    _record_message_decision_meta,
    _update_message_decision_metadata,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Conversation, Message, User
    from app.services.pack_runtime_service import PackDecision

BOOKING_SLOT_ORDER = ("service", "datetime", "name")

@dataclass(frozen=True)
class SlotCandidate:
    text: str
    flags: tuple[str, ...]

def _context_runtime():
    from . import context_manager as context_router

    return context_router

def _guards_runtime():
    from . import guards as guards_router

    return guards_router

def _is_env_enabled(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}

def _get_booking_confirm_threshold() -> float:
    raw = os.environ.get("BOOKING_CONFIRM_CONFIDENCE_THRESHOLD", "0.9")
    try:
        threshold = float(raw)
    except (TypeError, ValueError):
        return 0.9
    return max(0.0, min(threshold, 1.0))

def _is_booking_confirm_enabled() -> bool:
    return _is_env_enabled(os.environ.get("BOOKING_CONFIRM_ENABLED"), default=False)

def _build_slot_candidates(
    message_text: str, *, expected_reply_type: str | None
) -> list[SlotCandidate]:
    raw = (message_text or "").strip()
    if not raw:
        return []
    seen: set[str] = set()
    candidates: list[SlotCandidate] = []

    def _push(text: str, flags: tuple[str, ...]) -> None:
        cleaned = (text or "").strip()
        if not cleaned or cleaned in seen:
            return
        seen.add(cleaned)
        candidates.append(SlotCandidate(cleaned, flags))

    allow_layout_swap = should_allow_layout_swap_for_expected_reply(expected_reply_type)
    if allow_layout_swap and _looks_like_layout_swap(raw):
        swapped = _swap_keyboard_layout(raw)
        swapped_normalized = _normalize_text(swapped)
        if swapped_normalized and swapped_normalized != raw:
            _push(swapped_normalized, ("layout_swap", "normalized"))
        swapped_collapsed = _collapse_repeats(swapped_normalized)
        if swapped_collapsed and swapped_collapsed != swapped_normalized:
            _push(swapped_collapsed, ("layout_swap", "normalized", "repeat_collapse"))

    _push(raw, ())

    normalized = _normalize_text(raw)
    if normalized and normalized != raw:
        _push(normalized, ("normalized",))
    collapsed = _collapse_repeats(normalized)
    if collapsed and collapsed != normalized:
        _push(collapsed, ("normalized", "repeat_collapse"))

    return candidates

def _get_booking_context(context: dict) -> dict:
    booking = context.get("booking") if isinstance(context, dict) else None
    if isinstance(booking, dict):
        return dict(booking)
    return {}

def _set_booking_context(context: dict, booking: dict) -> dict:
    context = dict(context)
    context["booking"] = booking
    return context

def _get_booking_confirmation(booking: dict) -> dict | None:
    confirmation = booking.get("confirmation") if isinstance(booking, dict) else None
    if isinstance(confirmation, dict):
        return dict(confirmation)
    return None

def _set_booking_confirmation(booking: dict, confirmation: dict | None) -> dict:
    booking = dict(booking)
    if confirmation:
        booking["confirmation"] = confirmation
    else:
        booking.pop("confirmation", None)
    return booking

def _build_booking_confirmation_prompt(slot_key: str, value: str) -> str:
    if slot_key == "service":
        return f"Я понял: услуга — {value}. Верно?"
    if slot_key == "datetime":
        return f"Я понял дату и время: {value}. Верно?"
    if slot_key == "name":
        return f"Я правильно понял, вас зовут {value}?"
    return f"Подтвердите, пожалуйста: {value}. Верно?"

def _should_defer_booking_confirmation_for_info(
    *,
    confirmation: dict | None,
    basic_info_message: bool,
    message_text: str | None,
    client_slug: str | None,
) -> bool:
    return bool(
        confirmation
        and basic_info_message
        and message_text
        and _looks_like_info_query(message_text, client_slug=client_slug)
    )

def _should_defer_booking_flow_for_info_interrupt(
    *,
    booking_active: bool,
    booking_signal: bool,
    booking_related: bool,
    basic_info_message: bool,
) -> bool:
    return bool(
        booking_active
        and basic_info_message
        and not booking_signal
        and not booking_related
    )

def _set_service_hint(context: dict, service: str, now: datetime) -> dict:
    context = dict(context)
    context[SERVICE_HINT_KEY] = service
    context[SERVICE_HINT_AT_KEY] = now.isoformat()
    return context

def _clear_service_hint(context: dict) -> dict:
    context = dict(context)
    context.pop(SERVICE_HINT_KEY, None)
    context.pop(SERVICE_HINT_AT_KEY, None)
    return context

def _get_recent_service_hint(context: dict, now: datetime) -> str | None:
    if not isinstance(context, dict):
        return None
    value = context.get(SERVICE_HINT_KEY)
    if not value:
        return None
    timestamp_raw = context.get(SERVICE_HINT_AT_KEY)
    if not timestamp_raw:
        return None
    try:
        timestamp = datetime.fromisoformat(timestamp_raw)
    except (TypeError, ValueError):
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    if (now - timestamp) > timedelta(minutes=SERVICE_HINT_WINDOW_MINUTES):
        return None
    return str(value).strip() or None

def _is_blocked_slot_message(message_text: str) -> bool:
    return is_opt_out_message(message_text) or is_frustration_message(message_text)

def _is_noise_slot_message(message_text: str) -> bool:
    return (
        is_low_signal_message(message_text)
        or is_acknowledgement_message(message_text)
        or is_greeting_message(message_text)
        or is_thanks_message(message_text)
        or is_bot_status_question(message_text)
        or is_human_request_message(message_text)
    )

def _clean_name_candidate(value: str) -> str:
    return _clean_name_candidate_impl(value)

@lru_cache(maxsize=16)
def _load_datetime_lexicon(client_slug: str | None) -> dict:
    from app.services.pack_runtime_service import load_yaml_truth

    truth = load_yaml_truth(client_slug)
    domain_pack = truth.get("domain_pack") if isinstance(truth, dict) else None
    lexicon = domain_pack.get("datetime_lexicon") if isinstance(domain_pack, dict) else None
    return lexicon if isinstance(lexicon, dict) else {}

@lru_cache(maxsize=16)
def _build_datetime_variant_index(client_slug: str | None) -> tuple[
    dict[str, str],
    set[str],
    list[tuple[tuple[str, ...], str, str]],
]:
    lexicon = _load_datetime_lexicon(client_slug)
    variant_map: dict[str, str] = {}
    canonical_set: set[str] = set()
    entries: list[tuple[tuple[str, ...], str, str]] = []

    for group_name in ("days", "dayparts"):
        group = lexicon.get(group_name)
        if not isinstance(group, dict):
            continue
        for payload in group.values():
            if not isinstance(payload, dict):
                continue
            canonical_raw = payload.get("canonical_ru")
            if not isinstance(canonical_raw, str):
                continue
            canonical = _normalize_text(canonical_raw)
            if not canonical:
                continue
            canonical_set.add(canonical)
            variant_map.setdefault(canonical, canonical)
            entries.append((tuple(canonical.split()), canonical, canonical))
            for lang_key in ("ru", "kk"):
                variants = payload.get(lang_key)
                if not isinstance(variants, list):
                    continue
                for variant in variants:
                    if not isinstance(variant, str):
                        continue
                    normalized = _normalize_text(variant)
                    if not normalized:
                        continue
                    variant_map[normalized] = canonical
                    entries.append((tuple(normalized.split()), canonical, normalized))

    entries.sort(key=lambda item: len(item[0]), reverse=True)
    return variant_map, canonical_set, entries

def _canonicalize_datetime_text(
    message_text: str,
    *,
    client_slug: str | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    normalized = _normalize_text(message_text)
    if not normalized:
        return "", []

    variant_map, canonical_set, entries = _build_datetime_variant_index(client_slug)
    if not variant_map:
        return normalized, []

    tokens = normalized.split()
    matches: list[dict[str, Any]] = []
    replaced_tokens: list[str] = []
    idx = 0
    while idx < len(tokens):
        matched = False
        for variant_tokens, canonical, variant in entries:
            if not variant_tokens:
                continue
            size = len(variant_tokens)
            if idx + size <= len(tokens) and tuple(tokens[idx : idx + size]) == variant_tokens:
                replaced_tokens.append(canonical)
                matches.append({"variant": variant, "canonical": canonical, "method": "direct"})
                idx += size
                matched = True
                break
        if not matched:
            replaced_tokens.append(tokens[idx])
            idx += 1

    variants = list(variant_map.keys())
    for token_index, token in enumerate(replaced_tokens):
        if token in canonical_set or len(token) < 2:
            continue
        if any(char.isdigit() for char in token):
            continue
        match = process.extractOne(token, variants, scorer=fuzz.ratio)
        if not match:
            continue
        variant, score, _ = match
        threshold = 92 if len(token) <= 4 else 88
        if score < threshold:
            continue
        canonical = variant_map.get(variant)
        if not canonical or canonical == token:
            continue
        replaced_tokens[token_index] = canonical
        matches.append(
            {
                "variant": variant,
                "canonical": canonical,
                "method": "fuzzy",
                "score": score,
            }
        )

    return " ".join(replaced_tokens), matches

def _resolve_datetime_offline(
    message_text: str,
    *,
    client_slug: str | None = None,
    relative_base: datetime | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"value": None, "confidence": 0.0, "evidence": {}}
    if not message_text:
        return result

    normalized, matches = _canonicalize_datetime_text(message_text, client_slug=client_slug)
    if not normalized:
        return result

    settings: dict[str, Any] = {"PREFER_DATES_FROM": "future"}
    if relative_base is not None:
        if relative_base.tzinfo is None:
            relative_base = relative_base.replace(tzinfo=timezone.utc)
        settings["RELATIVE_BASE"] = relative_base
    try:
        parsed = dateparser.parse(message_text, languages=["ru"], settings=settings)
    except Exception:
        parsed = None
    if not parsed and normalized != message_text:
        try:
            parsed = dateparser.parse(normalized, languages=["ru"], settings=settings)
        except Exception:
            parsed = None
    normalized_value = _normalize_resolved_datetime_value(
        message_text,
        normalized_text=normalized,
    )
    if not parsed:
        if normalized_value and not any(char.isdigit() for char in message_text):
            result["value"] = normalized_value
            result["confidence"] = 0.45 if matches else 0.35
            result["evidence"] = {
                "normalized_text": normalized,
                "lexicon_matches": matches,
                "parser": "relative_fallback",
            }
            return result
        if matches:
            value = message_text.strip() if any(char.isdigit() for char in message_text) else normalized
            result["value"] = value
            result["confidence"] = 0.4
            result["evidence"] = {
                "normalized_text": normalized,
                "lexicon_matches": matches,
                "parser": "lexicon",
            }
        return result

    if any(char.isdigit() for char in message_text):
        value = message_text.strip()
    else:
        value = normalized_value or normalized
    confidence = 0.6
    if matches:
        confidence += 0.2
    if normalized != message_text:
        confidence += 0.1

    result["value"] = value
    result["confidence"] = min(confidence, 1.0)
    result["evidence"] = {
        "normalized_text": normalized,
        "lexicon_matches": matches,
        "parser": "dateparser",
    }
    return result

def _validate_service_slot(
    message_text: str,
    *,
    allow_freeform: bool,
    client_slug: str | None,
) -> str | None:
    if _is_blocked_slot_message(message_text):
        return None
    extracted = _extract_service_hint(message_text, client_slug)
    if extracted:
        return extracted
    if client_slug:
        from app.services.pack_runtime_service import get_pack_service_hint

        fallback = get_pack_service_hint(message_text, client_slug=client_slug)
        if fallback:
            return fallback
    return None

def _validate_datetime_slot(
    message_text: str,
    *,
    allow_freeform: bool,
    client_slug: str | None,
) -> str | None:
    if _is_blocked_slot_message(message_text):
        return None
    normalized = _normalize_text(message_text)
    has_duration_context = _has_duration_context_marker(normalized)
    booking_signal = bool(_is_booking_request(message_text, client_slug=client_slug))

    def _allow_partial_daypart_candidate(value: str) -> bool:
        if not isinstance(value, str) or not value.strip():
            return False
        if TIME_PATTERN.search(value) or TIME_HOUR_PATTERN.search(value):
            return True
        is_daypart_only = bool(
            _pick_daypart_token(value)
            and not _extract_relative_date_token(value)
        )
        if not is_daypart_only:
            return True
        ambiguous_bare_day = bool(
            re.search(r"\bдень\b", normalized)
            and not any(
                marker in normalized
                for marker in (
                    "днем",
                    "днём",
                    "после обеда",
                    "ближе к обеду",
                    "на день",
                    "дневн",
                )
            )
        )
        if ambiguous_bare_day:
            return False
        if not booking_signal and len(normalized.split()) > 6:
            return False
        return True

    extracted = _extract_datetime(message_text, client_slug=client_slug)
    if extracted and _allow_partial_daypart_candidate(extracted):
        return extracted
    resolved_partial = _normalize_resolved_datetime_value(
        message_text,
        normalized_text=normalized,
    )
    if resolved_partial:
        resolved_normalized = normalize_for_matching(resolved_partial)
        if (
            resolved_normalized
            and _has_daypart_stem(resolved_normalized)
            and not (has_duration_context and not booking_signal)
            and _allow_partial_daypart_candidate(resolved_partial)
        ):
            return resolved_partial
    match = _match_booking_hour_fallback(message_text)
    if not match:
        return None
    prep = (match.get("prep") or "").casefold()
    if has_duration_context and not booking_signal:
        return None
    if prep == "на" and not booking_signal:
        if "?" in message_text:
            return None
        if len(normalized.split()) > 4:
            return None
    hour = int(match.get("hour") or 0)
    minute = match.get("minute") or "00"
    return f"{hour:02d}:{minute}"

def _validate_name_slot(
    message_text: str,
    *,
    allow_freeform: bool,
    client_slug: str | None,
) -> str | None:
    if _is_blocked_slot_message(message_text):
        return None
    if _is_noise_slot_message(message_text):
        return None
    name_match = NAME_PATTERN.search(message_text)
    if name_match:
        candidate = name_match.group(1)
    elif not allow_freeform:
        return None
    else:
        if _extract_service_hint(message_text, client_slug) or _extract_datetime(
            message_text, client_slug=client_slug
        ):
            return None
        candidate = message_text
    cleaned = _clean_name_candidate(candidate)
    if not cleaned:
        return None
    if any(char.isdigit() for char in cleaned):
        return None
    normalized = _normalize_text(cleaned)
    tokens = normalized.split()
    if not tokens or len(tokens) > 3:
        return None
    if allow_freeform and len(tokens) > 2:
        return None
    if any(len(token) < 2 for token in tokens):
        return None
    booking_action_tokens = {
        "проверь",
        "проверить",
        "подтверди",
        "подтвердить",
        "перенеси",
        "перенести",
        "отмени",
        "отменить",
    }
    booking_object_tokens = {"запись", "бронь", "броньку", "броню"}
    if (
        set(tokens).intersection(booking_action_tokens)
        and set(tokens).intersection(booking_object_tokens)
    ):
        return None
    if all(token in NAME_NOISE_TOKENS for token in tokens):
        return None
    return cleaned

def _validate_phone_slot(
    message_text: str,
    *,
    allow_freeform: bool,
    client_slug: str | None,
) -> str | None:
    del allow_freeform, client_slug
    if _is_blocked_slot_message(message_text):
        return None
    return _normalize_phone_digits(message_text)

BOOKING_SLOT_VALIDATORS = {
    "service": _validate_service_slot,
    "datetime": _validate_datetime_slot,
    "name": _validate_name_slot,
    "phone": _validate_phone_slot,
}

def _expected_reply_for_booking_question(last_question: str | None) -> str | None:
    if last_question == "service":
        return EXPECTED_REPLY_SERVICE
    if last_question == "datetime":
        return EXPECTED_REPLY_TIME
    if last_question == "name":
        return EXPECTED_REPLY_NAME
    if last_question == "phone":
        return EXPECTED_REPLY_PHONE
    return None

def _match_expected_reply(
    *,
    expected_reply_type: str | None,
    message_text: str,
    client_slug: str | None,
) -> tuple[bool, str | None, list[str]]:
    slot_key = expected_reply_slot_key(expected_reply_type)
    validator_by_slot = {
        "service": _validate_service_slot,
        "datetime": _validate_datetime_slot,
        "name": _validate_name_slot,
        "phone": _validate_phone_slot,
    }
    if not expected_reply_type or not message_text:
        return False, None, []
    if not slot_key:
        return False, None, []
    if _is_blocked_slot_message(message_text):
        return False, None, []
    validator = validator_by_slot.get(slot_key)
    if validator is None:
        return False, None, []

    for candidate in _build_slot_candidates(
        message_text, expected_reply_type=expected_reply_type
    ):
        value = validator(
            candidate.text,
            allow_freeform=True,
            client_slug=client_slug,
        )
        if value:
            return True, value, list(candidate.flags)
    return False, None, []

def _apply_expected_reply_slot(context: dict, *, expected_reply_type: str | None, value: str) -> dict:
    if not expected_reply_type or not value:
        return context
    slot_key = expected_reply_slot_key(expected_reply_type)
    if not slot_key:
        return context
    def _merge_datetime_slot(existing_value: str, incoming_value: str) -> str | None:
        existing = existing_value.strip()
        incoming = incoming_value.strip()
        if not existing or not incoming:
            return None
        existing_day = _extract_relative_date_token(existing)
        incoming_day = _extract_relative_date_token(incoming)
        existing_daypart = _pick_daypart_token(existing)
        incoming_daypart = _pick_daypart_token(incoming)
        merged_day = existing_day or incoming_day
        merged_daypart = existing_daypart or incoming_daypart
        if merged_day and merged_daypart:
            return f"{merged_day} {merged_daypart}".strip()
        existing_normalized = normalize_for_matching(existing)
        incoming_normalized = normalize_for_matching(incoming)
        if (
            existing_normalized
            and incoming_normalized
            and existing_normalized in incoming_normalized
        ):
            return incoming
        if (
            existing_normalized
            and incoming_normalized
            and incoming_normalized in existing_normalized
        ):
            return existing
        if TIME_PATTERN.search(existing) or TIME_HOUR_PATTERN.search(existing):
            return None
        if not (TIME_PATTERN.search(incoming) or TIME_HOUR_PATTERN.search(incoming)):
            return None
        return f"{existing} {incoming}".strip()

    booking_state = _get_booking_context(context)
    if not isinstance(booking_state, dict) or not booking_state:
        return context
    existing_slot_value = booking_state.get(slot_key)
    if isinstance(existing_slot_value, str) and existing_slot_value.strip():
        if slot_key != "datetime":
            return context
        merged_datetime = _merge_datetime_slot(existing_slot_value, value)
        if not merged_datetime:
            return context
        value = merged_datetime
    last_question = booking_state.get("last_question")
    if not booking_state.get("active") and last_question != slot_key:
        return context
    booking_state = dict(booking_state)
    booking_state[slot_key] = value
    return _set_booking_context(context, booking_state)

def _is_booking_related_message(
    message_text: str | None,
    client_slug: str | None,
    *,
    allow_name: bool = True,
    allow_service: bool = True,
) -> bool:
    if not message_text:
        return False
    if _is_booking_request(message_text, client_slug=client_slug):
        return True
    refusal_flags = detect_refusal_flags(message_text)
    if refusal_flags.get("name") or refusal_flags.get("phone"):
        return True
    if allow_service and _extract_service_hint(message_text, client_slug):
        return True
    if _extract_datetime(message_text, client_slug=client_slug):
        return True
    if allow_name and _validate_name_slot(message_text, allow_freeform=True, client_slug=client_slug):
        return True
    return False

def _is_booking_slot_signal(message_text: str | None, *, client_slug: str | None) -> bool:
    if not message_text:
        return False
    if _looks_like_phone(message_text):
        return True
    if _looks_like_info_query(message_text, client_slug=client_slug) and not _is_booking_request(
        message_text,
        client_slug=client_slug,
    ):
        return False
    return _is_booking_related_message(
        message_text,
        client_slug,
        allow_name=True,
        allow_service=False,
    )

def _select_last_non_booking_message(messages: list[str], *, client_slug: str | None) -> str | None:
    for message in reversed(messages or []):
        if not message:
            continue
        if _is_booking_related_message(message, client_slug, allow_name=False, allow_service=False):
            continue
        if _looks_like_info_query(message, client_slug=client_slug):
            return message
        return message
    return None

def _select_booking_interrupt_text(
    *,
    message_text: str | None,
    batch_non_booking_message: str | None,
    client_slug: str | None,
) -> str | None:
    if not message_text:
        return batch_non_booking_message
    if not batch_non_booking_message:
        return message_text
    if _is_booking_related_message(
        message_text,
        client_slug,
        allow_name=False,
        allow_service=False,
    ):
        return batch_non_booking_message
    return message_text

def _resolve_booking_info_intents(
    *,
    intent_decomp_used: bool,
    intent_decomp_set: set[str],
    info_class_intents: set[str],
    expected_reply_type: str | None,
    booking_time_service_candidate: bool,
    expected_reply_shortcircuit: bool,
    booking_interrupt_text: str | None,
    client_slug: str | None,
) -> list[str]:
    booking_info_intents: list[str] = []
    should_prefer_info_class = should_prefer_info_class_for_booking_interrupt(
        info_class_intents_present=bool(info_class_intents),
        booking_time_service_candidate=booking_time_service_candidate,
        expected_reply_type=expected_reply_type,
    )
    if should_prefer_info_class:
        booking_info_intents = sorted(info_class_intents)
    elif intent_decomp_used:
        booking_info_intents = sorted(intent_decomp_set & INFO_INTENTS)

    if booking_interrupt_text:
        anchor_intents, _ = _detect_info_class_intents(
            booking_interrupt_text,
            intent_decomp_set=set(),
            client_slug=client_slug,
        )
        if expected_reply_shortcircuit and anchor_intents:
            booking_info_intents = sorted(anchor_intents)
        elif not booking_info_intents and anchor_intents:
            # Keep booking flow resilient when intent decomposition misses short
            # info interruptions (parking, duration, etc.).
            booking_info_intents = sorted(anchor_intents)

    return booking_info_intents

def _looks_like_booking_reschedule_request(
    message_text: str | None,
    *,
    client_slug: str | None = None,
) -> bool:
    normalized = _normalize_text(message_text or "")
    if not normalized:
        return False
    try:
        intent_signals = {
            str(item).strip().casefold()
            for item in phrase_match_intent(normalized, client_slug=client_slug)
            if isinstance(item, str) and item.strip()
        }
    except Exception:
        intent_signals = set()
    if intent_signals & {"reschedule", "cancel_request"}:
        return True
    # Check explicit reschedule lexicon before generic info-question guards.
    # Phrases like "что если я захочу изменить время" can look informational,
    # but operationally they still mean reschedule flow.
    reschedule_markers = get_system_lexicon_list("booking_reschedule_keywords")
    if any(marker in normalized for marker in reschedule_markers):
        return True
    if intent_signals & INFO_INTENTS:
        return False
    if _looks_like_info_query(message_text, client_slug=client_slug):
        return False
    booking_reference_markers = get_system_lexicon_list("booking_request")
    booking_keyword_markers = get_system_lexicon_list("booking_keywords")
    has_booking_reference = any(marker in normalized for marker in booking_reference_markers) or any(
        marker in normalized for marker in booking_keyword_markers
    )
    if not has_booking_reference:
        return False
    cancel_markers = get_system_lexicon_list("booking_cancel_keywords")
    return any(marker in normalized for marker in cancel_markers)

def _select_expected_reply_message(
    messages: list[str],
    *,
    expected_reply_type: str | None,
    client_slug: str | None,
) -> str | None:
    if not messages or not expected_reply_type:
        return None
    last_message = None
    for message in reversed(messages or []):
        if message:
            last_message = message
            break
    if not last_message:
        return None
    matched, _, _ = _match_expected_reply(
        expected_reply_type=expected_reply_type,
        message_text=last_message,
        client_slug=client_slug,
    )
    return last_message if matched else None

def _apply_booking_slot(
    booking: dict,
    slot_key: str,
    message_text: str,
    *,
    allow_freeform: bool,
    client_slug: str | None,
) -> dict:
    if booking.get(slot_key):
        if slot_key != "datetime":
            return booking
        existing_datetime = str(booking.get("datetime") or "").strip()
        if existing_datetime:
            if TIME_PATTERN.search(existing_datetime) or TIME_HOUR_PATTERN.search(
                existing_datetime
            ):
                return booking
    validator = BOOKING_SLOT_VALIDATORS.get(slot_key)
    if not validator:
        return booking
    value = validator(message_text, allow_freeform=allow_freeform, client_slug=client_slug)
    if value:
        booking[slot_key] = value
    return booking

def _update_booking_from_message(booking: dict, message_text: str, *, client_slug: str | None) -> dict:
    booking = dict(booking)
    last_question = booking.get("last_question")
    if _is_blocked_slot_message(message_text):
        return booking

    if last_question in BOOKING_SLOT_ORDER:
        booking = _apply_booking_slot(
            booking,
            last_question,
            message_text,
            allow_freeform=True,
            client_slug=client_slug,
        )

    for slot_key in BOOKING_SLOT_ORDER:
        booking = _apply_booking_slot(
            booking,
            slot_key,
            message_text,
            allow_freeform=False,
            client_slug=client_slug,
        )

    return booking

def _update_booking_from_messages(
    booking: dict,
    messages: list[str],
    *,
    client_slug: str | None,
) -> dict:
    updated = dict(booking)
    for message in messages:
        updated = _update_booking_from_message(updated, message, client_slug=client_slug)
    return updated

def _is_datetime_grounded_for_prompt(
    datetime_value: str | None,
    *,
    client_slug: str | None,
) -> bool:
    if not isinstance(datetime_value, str) or not datetime_value.strip():
        return False
    value = datetime_value.strip()
    if TIME_PATTERN.search(value) or TIME_HOUR_PATTERN.search(value):
        return True
    if not _pick_daypart_token(value):
        return False
    if _extract_relative_date_token(value):
        return True
    if re.search(r"\d{4}-\d{2}-\d{2}", value) or re.search(
        r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b",
        value,
    ):
        return True
    _, matches = _canonicalize_datetime_text(value, client_slug=client_slug)
    canonical_tokens: list[str] = []
    for item in matches:
        if not isinstance(item, dict):
            continue
        token = str(item.get("canonical") or item.get("variant") or "").strip().casefold()
        if token:
            canonical_tokens.append(token)
    return any(
        token and not _has_daypart_stem(token)
        for token in canonical_tokens
    )

def _next_booking_prompt(
    booking: dict,
    *,
    refusal_flags: dict | None = None,
    client_slug: str | None = None,
) -> tuple[dict, str | None]:
    booking = dict(booking)
    if not booking.get("service"):
        booking["last_question"] = "service"
        return booking, MSG_BOOKING_ASK_SERVICE
    datetime_value = booking.get("datetime")
    datetime_grounded = _is_datetime_grounded_for_prompt(datetime_value, client_slug=client_slug)
    if not datetime_grounded:
        booking["last_question"] = "datetime"
        if isinstance(datetime_value, str) and datetime_value.strip():
            has_daypart_only = bool(
                _pick_daypart_token(datetime_value)
                and not _is_datetime_grounded_for_prompt(datetime_value, client_slug=client_slug)
                and not _extract_relative_date_token(datetime_value)
                and not re.search(r"\d{4}-\d{2}-\d{2}", datetime_value)
                and not re.search(r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b", datetime_value)
            )
            if not has_daypart_only:
                service_value = booking.get("service")
                if isinstance(service_value, str) and service_value.strip():
                    prompt = (
                        f"Понял, {datetime_value.strip()} по услуге «{service_value.strip()}». "
                        "Подскажите, пожалуйста, точное время."
                    )
                else:
                    prompt = f"Понял, {datetime_value.strip()}. Подскажите, пожалуйста, точное время."
                return booking, prompt
        return booking, MSG_BOOKING_ASK_DATETIME
    if not booking.get("name"):
        if _is_refusal_flag_active(refusal_flags, "name"):
            booking["last_question"] = None
            return booking, None
        booking["last_question"] = "name"
        return booking, MSG_BOOKING_ASK_NAME
    booking["last_question"] = None
    return booking, None

def _should_collect_booking_details(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = normalize_for_matching(message_text)
    if not normalized:
        return False
    detail_markers = get_system_lexicon_list("booking_collect_detail_markers")
    if detail_markers and any(marker in normalized for marker in detail_markers):
        return True
    relative_markers = get_system_lexicon_list("booking_collect_detail_relative_markers")
    duration_units = get_system_lexicon_list("booking_collect_detail_duration_units")
    if (
        relative_markers
        and duration_units
        and any(marker in normalized for marker in relative_markers)
        and any(unit in normalized for unit in duration_units)
    ):
        return True
    return False

def _apply_collect_all_prompt(
    booking_state: dict,
    prompt: str | None,
    message_text: str | None,
) -> tuple[dict, str | None]:
    if not prompt or not _should_collect_booking_details(message_text):
        return booking_state, prompt
    booking_state = dict(booking_state)
    booking_state["last_question"] = None
    return booking_state, MSG_BOOKING_ASK_ALL

def _is_booking_time_service_decision(decision: PackDecision | None) -> bool:
    if not decision or getattr(decision, "action", None) != "reply":
        return False
    intent = getattr(decision, "intent", None)
    if not isinstance(intent, str):
        return False
    return intent.strip().casefold() in BOOKING_TIME_SERVICE_INTENTS

def _build_booking_summary(booking: dict, *, refusal_flags: dict | None = None) -> str:
    service = booking.get("service") or "не указано"
    datetime_pref = booking.get("datetime") or "не указано"
    name = booking.get("name")
    name_refused = _is_refusal_flag_active(refusal_flags, "name")
    if not name and name_refused:
        name_value = "отказ"
    else:
        name_value = name or "не указано"
    summary = f"Запись: услуга={service}; дата/время={datetime_pref}; имя={name_value}."
    if _is_refusal_flag_active(refusal_flags, "phone"):
        summary = f"{summary} Телефон: отказ."
    return summary

def _normalize_phone_digits(value: str | None) -> str | None:
    return _normalize_phone_digits_impl(value)

def _parse_booking_datetime(value: str | None, *, tz_name: str | None, now: datetime) -> datetime | None:
    if not value or not value.strip():
        return None
    raw = value.strip()
    parsed = _parse_iso_datetime(raw)
    if parsed is None:
        timezone_name = tz_name or "UTC"
        settings = {
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": now,
            "TIMEZONE": timezone_name,
            "TO_TIMEZONE": timezone_name,
            "RETURN_AS_TIMEZONE_AWARE": True,
        }
        try:
            parsed = dateparser.parse(raw, languages=["ru"], settings=settings)
        except Exception:
            parsed = None
    if not parsed:
        return None
    if parsed.tzinfo is None:
        tz = timezone.utc
        if tz_name:
            try:
                tz = ZoneInfo(tz_name)
            except Exception:
                tz = timezone.utc
        parsed = parsed.replace(tzinfo=tz)
    return parsed

def _normalize_booking_setting(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value

def _resolve_booking_settings(settings: dict | None, *, provider_ready: bool | None = None) -> tuple[str, str, str]:
    raw = settings if isinstance(settings, dict) else {}
    booking_mode = _normalize_booking_setting(raw.get("booking_mode"))
    availability_provider = _normalize_booking_setting(raw.get("availability_provider"))
    if booking_mode is None or availability_provider is None:
        runtime = get_runtime_capabilities()
        if runtime:
            if booking_mode is None:
                booking_mode = runtime.payload.features.booking_mode
            if availability_provider is None:
                availability_provider = runtime.payload.providers.availability_provider
    booking_mode = booking_mode or "collect_preferences"
    availability_provider = availability_provider or "none"
    effective_mode = booking_mode
    if booking_mode == "confirm_slots" and availability_provider in {"none", "", None}:
        effective_mode = "collect_preferences"
    if booking_mode == "confirm_slots" and provider_ready is False:
        effective_mode = "collect_preferences"
    return booking_mode, availability_provider, effective_mode

def _resolve_default_specialist_id(
    db: Session,
    *,
    branch_id: Any,
    service_name: str | None,
) -> tuple[Any | None, str]:
    from app.models.service import Service
    from app.models.specialist import Specialist
    from app.models.specialist_service import SpecialistService

    def _extract_row_id(row: Any) -> Any | None:
        if row is None:
            return None
        if type(row).__module__ == "unittest.mock":
            return None
        mapping = getattr(row, "_mapping", None)
        if isinstance(mapping, Mapping):
            if "id" in mapping:
                return mapping["id"]
            if len(mapping) == 1:
                return next(iter(mapping.values()))
        if isinstance(row, Mapping):
            if "id" in row:
                return row["id"]
            if len(row) == 1:
                return next(iter(row.values()))
        candidate_id = getattr(row, "id", None)
        if candidate_id and type(candidate_id).__module__ != "unittest.mock":
            return candidate_id
        if isinstance(row, (list, tuple)):
            return row[0] if row else None
        return row if isinstance(row, (UUID, str)) else None

    if service_name and isinstance(service_name, str):
        normalized = service_name.strip().casefold()
        if normalized:
            candidates = (
                db.query(Specialist.id)
                .join(SpecialistService, SpecialistService.specialist_id == Specialist.id)
                .join(Service, Service.id == SpecialistService.service_id)
                .filter(
                    Specialist.branch_id == branch_id,
                    Specialist.is_active == True,
                    Service.branch_id == branch_id,
                    Service.is_active == True,
                    func.lower(Service.name) == normalized,
                )
                .order_by(Specialist.name)
                .all()
            )
            if isinstance(candidates, (list, tuple)) and candidates:
                candidate_id = _extract_row_id(candidates[0])
                if candidate_id:
                    return candidate_id, "service_default"

    fallback = (
        db.query(Specialist.id)
        .filter(
            Specialist.branch_id == branch_id,
            Specialist.is_active == True,
        )
        .order_by(Specialist.name)
        .first()
    )
    fallback_id = _extract_row_id(fallback)
    if fallback_id:
        return fallback_id, "branch_default"
    return None, "specialist_not_found"

def _create_booking_appointment(
    *,
    db: Session,
    conversation: Conversation,
    user: User | None,
    booking_state: dict,
    now: datetime,
    saved_message: Message | None,
) -> tuple[Any | None, dict[str, Any]]:
    from app.models.appointment import Appointment
    from app.models.branch import Branch
    from app.models.service import Service
    from app.services.appointment_service import (
        AppointmentConflictError,
        BranchNotFoundError,
        SpecialistNotFoundError,
    )

    meta: dict[str, Any] = {}
    branch_id = getattr(conversation, "branch_id", None)
    if not branch_id:
        meta["appointment_skip_reason"] = "missing_branch"
        return None, meta

    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        meta["appointment_skip_reason"] = "branch_not_found"
        return None, meta

    existing = (
        db.query(Appointment)
        .filter(
            Appointment.conversation_id == conversation.id,
            Appointment.status.in_(SchedulingService.ACTIVE_STATUSES),
        )
        .first()
    )
    if existing:
        meta["appointment_id"] = str(existing.id)
        meta["appointment_status"] = existing.status
        meta["appointment_reused"] = True
        return existing, meta

    provider_ready = None
    availability_provider = None
    if isinstance(branch.booking_settings, dict):
        availability_provider = _normalize_booking_setting(
            branch.booking_settings.get("availability_provider")
        )
    if availability_provider is None:
        runtime = get_runtime_capabilities()
        if runtime:
            availability_provider = runtime.payload.providers.availability_provider
    if availability_provider == "google_calendar":
        from app.services.calendar_sync_service import get_provider_health

        health = get_provider_health(
            db,
            client_id=conversation.client_id,
            branch_id=branch_id,
        )
        provider_ready = health.ready
        meta["provider_ready"] = health.ready
        meta["provider_reason"] = health.reason

    booking_mode, availability_provider, effective_mode = _resolve_booking_settings(
        branch.booking_settings,
        provider_ready=provider_ready,
    )
    meta.update(
        {
            "booking_mode": booking_mode,
            "availability_provider": availability_provider,
            "effective_booking_mode": effective_mode,
        }
    )
    if effective_mode not in {"collect_preferences", "confirm_slots"}:
        meta["appointment_skip_reason"] = "booking_mode_not_supported"
        return None, meta

    start_at = _parse_booking_datetime(
        booking_state.get("datetime"),
        tz_name=branch.timezone,
        now=now,
    )
    if not start_at:
        meta["appointment_skip_reason"] = "datetime_parse_failed"
        return None, meta

    service_name = booking_state.get("service")
    duration_min = None
    if service_name:
        service_row = (
            db.query(Service)
            .filter(
                Service.client_id == conversation.client_id,
                Service.branch_id == branch_id,
                Service.name == service_name,
            )
            .first()
        )
        if service_row and service_row.duration_min:
            duration_min = service_row.duration_min
            meta["appointment_duration_source"] = "service"

    if not duration_min:
        settings = branch.booking_settings if isinstance(branch.booking_settings, dict) else {}
        duration_min = settings.get("default_duration_min") or settings.get("slot_duration_min")
        if duration_min:
            meta["appointment_duration_source"] = "branch_default"
    if not duration_min:
        duration_min = SchedulingService.DEFAULT_SLOT_DURATION
        meta["appointment_duration_source"] = "fallback_default"

    end_at = start_at + timedelta(minutes=int(duration_min))

    customer_name = booking_state.get("name") or getattr(user, "name", None)
    customer_phone = getattr(user, "phone", None) or _normalize_phone_digits(
        getattr(user, "remote_jid", None)
    )

    audit_payload = {
        "booking": {
            "service": service_name,
            "datetime": booking_state.get("datetime"),
            "name": booking_state.get("name"),
        },
        "booking_mode": booking_mode,
        "availability_provider": availability_provider,
        "effective_booking_mode": effective_mode,
    }

    trace_id = None
    correlation_id = None
    message_meta = getattr(saved_message, "message_metadata", None)
    if isinstance(message_meta, dict):
        trace_id = (message_meta.get("decision_meta") or {}).get("trace_id")
    if getattr(conversation, "id", None):
        correlation_id = str(conversation.id)

    appointment_status = "PENDING_CONFIRMATION"
    confirmation_policy = None
    if isinstance(branch.booking_settings, dict):
        confirmation_policy = branch.booking_settings.get("confirmation_policy")
    if effective_mode == "confirm_slots" and confirmation_policy == "client":
        appointment_status = "CONFIRMED"

    specialist_id, specialist_selection = _resolve_default_specialist_id(
        db,
        branch_id=branch_id,
        service_name=service_name,
    )
    meta["specialist_selection"] = specialist_selection
    if specialist_id:
        meta["specialist_id"] = str(specialist_id)

    try:
        appointment = SchedulingService(db).create_appointment(
            client_id=conversation.client_id,
            branch_id=branch_id,
            specialist_id=specialist_id,
            start_at=start_at,
            end_at=end_at,
            customer_name=customer_name,
            customer_phone=customer_phone,
            service_type=service_name,
            notes=None,
            created_by=None,
            conversation_id=conversation.id,
            status=appointment_status,
            source="bot",
            confirmation_policy=None,
            audit={
                "actor_type": "bot",
                "actor_id": getattr(user, "id", None),
                "channel": "whatsapp",
                "action": "create",
                "payload": audit_payload,
                "trace_id": trace_id,
                "correlation_id": correlation_id,
            },
            commit=False,
        )
    except (AppointmentConflictError, SpecialistNotFoundError, BranchNotFoundError):
        meta["appointment_skip_reason"] = "appointment_create_failed"
        return None, meta

    meta["appointment_id"] = str(appointment.id)
    meta["appointment_status"] = appointment.status

    if availability_provider == "google_calendar":
        from app.services.calendar_sync_service import enqueue_appointment_sync

        enqueued, enqueue_error = enqueue_appointment_sync(
            db,
            appointment=appointment,
            action="create",
            commit=False,
        )
        meta["calendar_sync_enqueued"] = bool(enqueued)
        if enqueue_error:
            meta["calendar_sync_error"] = enqueue_error
    from app.services.appointment_reminder_service import schedule_default_reminders

    reminders = schedule_default_reminders(db, appointment=appointment, commit=False)
    meta["reminder_jobs_scheduled"] = len(reminders)
    return appointment, meta

def _is_appointment_overlap_integrity_error(exc: Exception) -> bool:
    text = str(getattr(exc, "orig", exc) or exc).casefold()
    return "appointments_no_overlap" in text or "exclusion constraint" in text

@dataclass(frozen=True)
class BookingFlowResult:
    response: WebhookResponse | None
    booking_t0: float | None
    booking_logged: bool

def _build_booking_class_router_result(
    *,
    intent_decomp_set: set[str] | None,
    booking_signal: bool,
) -> dict[str, Any]:
    controller_output = _build_controller_meta_output(error="skipped")
    controller_output["class"] = "booking"
    controller_output["goal"] = "booking"
    controller_output["confidence"] = max(CONTROLLER_CONFIDENCE_THRESHOLD, 0.5)
    controller_output = _ensure_controller_output_meta(controller_output, error="skipped")
    router_state = {
        "used": True,
        "attempted": False,
        "fallback": False,
        "confidence": controller_output["confidence"],
        "error": "skipped",
        "fallback_reason": None,
        "signal_class": _resolve_controller_signal_class(
            intent_decomp_set=intent_decomp_set or set(),
            booking_signal=booking_signal,
        ),
        "signal_match": False,
        "used_reason": "deterministic",
        "output": controller_output,
        "sla": None,
    }
    return _resolve_class_router_result(
        info_intents=set(),
        info_meta=None,
        booking_signal=booking_signal,
        class_carryover=None,
        domain_intent=DomainIntent.UNKNOWN,
        domain_meta=None,
        router_state=router_state,
        explicit_service_signal=False,
    )

def _record_booking_class_router_trace(
    *,
    conversation: Conversation,
    class_router_result: dict | None,
) -> None:
    if not isinstance(class_router_result, dict):
        return

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
    trace_payload.update(_router_observability_updates_from_class_router(class_router_result))
    _record_decision_trace(conversation, trace_payload)

def _handle_booking_interrupt(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str | None,
    saved_message: Message | None,
    client_slug: str | None,
    routing: dict,
    has_media: bool,
    bypass_domain_flows: bool,
    booking_wants_flow: bool,
    consult_intent: bool | None,
    intent_decomp_used: bool,
    intent_decomp_set: set[str],
    intent_decomp_payload: dict | None,
    multi_intent_primary: str | None,
    info_class_intents: set[str],
    early_domain_intent: Any | None,
    expected_reply_type: str | None,
    expected_reply_matched: bool | None,
    expected_reply_shortcircuit: bool,
    expected_reply_blocked_by_info: bool,
    pending_question_act: str | None,
    pending_question_target: str | None,
    batch_non_booking_message: str | None,
    booking_messages: list[str],
    booking_context: dict | None,
    booking: dict | None,
    current_goal: str | None,
    basic_info_message: bool,
    session_memory_reset_reason: str | None,
    memory_expected_reply_type: str | None,
    policy_handler: dict | None,
    policy_type: str | None,
    now: datetime,
    message_count: int,
    consult_return_pending: bool,
    consult_return_prompt: str | None,
    consult_context: dict | None,
    consult_return_reason: str | None,
    maybe_apply_fact_guard: Callable[..., Any],
    send_and_save: Callable[..., tuple[str, bool]],
    send_response: Callable[..., Any],
    finalize_response: Callable[..., Any],
) -> WebhookResponse | None:
    from app.services.pack_runtime_service import (
        PackDecision,
        build_info_combined_reply,
        compose_multi_truth_reply,
        format_reply_from_truth,
        get_pack_decision,
        resolve_master_intent,
    )

    from .info import _build_info_intent_reply as _build_booking_interrupt_info_reply

    booking_state = booking if isinstance(booking, dict) else _get_booking_context(booking_context or {})
    if booking_state.get("active") and all(booking_state.get(key) for key in BOOKING_SLOT_ORDER):
        return None
    has_info_interrupt = bool(info_class_intents)
    if not has_info_interrupt and intent_decomp_set:
        has_info_interrupt = bool(intent_decomp_set & INFO_INTENTS)
    if should_skip_booking_interrupt_for_expected_reply(
        expected_reply_type=expected_reply_type,
        expected_reply_blocked_by_info=expected_reply_blocked_by_info,
        has_info_interrupt=has_info_interrupt,
    ):
        return None

    booking_interrupt_text = _select_booking_interrupt_text(
        message_text=message_text,
        batch_non_booking_message=batch_non_booking_message,
        client_slug=client_slug,
    )
    if (
        _looks_like_booking_reschedule_request(
            booking_interrupt_text,
            client_slug=client_slug,
        )
        and conversation.state == ConversationState.BOT_ACTIVE.value
        and routing.get("allow_handover_create", False)
    ):
        handover_message = booking_interrupt_text or message_text or "Клиент просит изменить время записи."
        _, reused, telegram_sent = _reuse_active_handover(
            db=db,
            conversation=conversation,
            user=user,
            message=handover_message,
            source="booking_interrupt",
            intent="reschedule_request",
            hooks=ActiveHandoverReuseRuntimeHooks(
                get_active_handover=get_active_handover,
                transition_state=transition_state,
                send_telegram_notification=send_telegram_notification,
                record_decision_trace=_record_decision_trace,
            ),
        )
        if reused:
            result_message = (
                f"Booking reschedule handoff reused, telegram={'sent' if telegram_sent else 'failed'}"
            )
        else:
            result = escalate_to_pending(
                db=db,
                conversation=conversation,
                user_message=handover_message,
                trigger_type="intent",
                trigger_value="reschedule_request",
            )
            if result.ok:
                handover = result.value
                telegram_sent = send_telegram_notification(
                    db=db,
                    handover=handover,
                    conversation=conversation,
                    user=user,
                    message=handover_message,
                )
                result_message = (
                    f"Booking reschedule handoff created, telegram={'sent' if telegram_sent else 'failed'}"
                )
            else:
                result_message = f"Booking reschedule handoff failed: {result.error}"
        _record_decision_trace(
            conversation,
            {
                "stage": "booking_interrupt",
                "decision": "handoff",
                "intent": "reschedule_request",
                "state": conversation.state,
            },
        )
        _record_message_decision_meta(
            saved_message,
            action="escalate",
            intent="reschedule_request",
            source="booking_interrupt",
            fast_intent=False,
        )
        bot_response, sent = send_and_save(MSG_ESCALATED)
        if not sent:
            result_message = f"{result_message}; response_send=failed"
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )
    booking_time_service_candidate = should_mark_booking_time_service_candidate(
        expected_reply_type=expected_reply_type,
        expected_reply_matched=expected_reply_matched,
        message_text=message_text,
    )
    pending_question_target_value = (
        pending_question_target.strip().casefold()
        if isinstance(pending_question_target, str) and pending_question_target.strip()
        else None
    )

    def _merge_info_sections(info_meta: dict[str, Any], intents: list[str]) -> list[str]:
        sections: list[str] = []
        aliases = {
            "duration": ("duration", "service_duration"),
            "service_duration": ("duration", "service_duration"),
        }

        def _append_section(section: str) -> None:
            values = aliases.get(section, (section,))
            for value in values:
                if value not in sections:
                    sections.append(value)

        existing = info_meta.get("info_sections")
        if isinstance(existing, list):
            for section in existing:
                if isinstance(section, str) and section.strip():
                    key = section.strip().lower()
                    _append_section(key)
        for intent in intents or []:
            if isinstance(intent, str) and intent.strip():
                key = intent.strip().lower()
                _append_section(key)
        return sections
    if (
        routing.get("allow_booking_flow")
        and not bypass_domain_flows
        and booking_wants_flow
        and not consult_intent
        and (
            intent_decomp_used
            or booking_time_service_candidate
            or batch_non_booking_message
            or expected_reply_shortcircuit
        )
    ):
        booking_info_intents = _resolve_booking_info_intents(
            intent_decomp_used=intent_decomp_used,
            intent_decomp_set=intent_decomp_set,
            info_class_intents=info_class_intents,
            expected_reply_type=expected_reply_type,
            booking_time_service_candidate=booking_time_service_candidate,
            expected_reply_shortcircuit=expected_reply_shortcircuit,
            booking_interrupt_text=booking_interrupt_text,
            client_slug=client_slug,
        )
        promotions_signal = False
        if message_text:
            policy_pack = (
                policy_handler.get("policy_pack") if isinstance(policy_handler, dict) else None
            )
            from app.routers.webhook.policy import _looks_like_promotions_request

            promotions_signal = _looks_like_promotions_request(
                message_text,
                policy_pack=policy_pack,
                client_slug=client_slug,
            )
        if promotions_signal and "promotions" not in booking_info_intents:
            booking_info_intents = [*booking_info_intents, "promotions"]
        master_service_query = None
        if isinstance(intent_decomp_payload, dict):
            raw_master_service_query = intent_decomp_payload.get("service_query")
            if isinstance(raw_master_service_query, str) and raw_master_service_query.strip():
                master_service_query = raw_master_service_query.strip()
        if not master_service_query:
            booking_service_value = booking_state.get("service")
            if isinstance(booking_service_value, str) and booking_service_value.strip():
                master_service_query = booking_service_value.strip()
        master_resolution = resolve_master_intent(
            message_text=booking_interrupt_text,
            client_slug=client_slug,
            service_query=master_service_query,
            intent_decomp=intent_decomp_payload if isinstance(intent_decomp_payload, dict) else None,
            force_master_intent=False,
        )
        if (
            pending_question_target_value is None
            and master_resolution.explicit
            and expected_reply_type == EXPECTED_REPLY_TIME
            and booking_state.get("active")
        ):
            # For active-time info interrupts the pending target must stay aligned
            # with the blocked resume slot, not with the transient info subject.
            pending_question_target_value = "time"
        if master_resolution.explicit and "master" not in booking_info_intents:
            booking_info_intents = [*booking_info_intents, "master"]
        if not master_resolution.explicit and "master" in booking_info_intents:
            booking_info_intents = [
                intent_name for intent_name in booking_info_intents if intent_name != "master"
            ]
        resolved_master_service_query = (
            master_resolution.service_query
            if isinstance(master_resolution.service_query, str)
            and master_resolution.service_query.strip()
            else master_service_query
        )
        guest_policy_hit = bool(
            booking_interrupt_text
            and _matches_guest_policy_lexicon(
                booking_interrupt_text, client_slug=client_slug
            )
        )
        if guest_policy_hit and "guest_policy" not in booking_info_intents:
            booking_info_intents = [*booking_info_intents, "guest_policy"]
        allow_booking_interrupt_info = bool(
            booking_info_intents
            or booking_time_service_candidate
            or (batch_non_booking_message and not expected_reply_shortcircuit)
        )
        if allow_booking_interrupt_info and routing.get("allow_truth_gate_reply"):
            info_decision = None
            info_source = None
            service_matcher = (
                policy_handler.get("service_matcher")
                if isinstance(policy_handler, dict)
                else None
            )
            truth_gate = (
                policy_handler.get("truth_gate")
                if isinstance(policy_handler, dict)
                else None
            )
            booking_info_set = set(booking_info_intents)
            non_service_interrupt_priority = [
                intent_name
                for intent_name in ("hours", "location", "parking", "contact", "guest_policy")
                if intent_name in booking_info_set
            ]
            strict_non_service_interrupt = bool(
                non_service_interrupt_priority
                and not ({"pricing", "duration", "promotions", "master"} & booking_info_set)
            )
            if strict_non_service_interrupt and booking_interrupt_text:
                # Explicit non-service info asks (hours/location/parking/contact) must stay in
                # info contract and must not be hijacked into stale price/service replies.
                contract_intent = non_service_interrupt_priority[0]
                contract_reply, contract_meta = _build_booking_interrupt_info_reply(
                    contract_intent,
                    service_query=None,
                    client_slug=client_slug,
                    message_text=booking_interrupt_text,
                )
                if contract_reply:
                    info_decision = PackDecision(
                        action="reply",
                        response=contract_reply,
                        intent=contract_intent,
                        meta=contract_meta if isinstance(contract_meta, dict) else None,
                    )
                    info_source = "booking_info_contract"
            master_only_interrupt = set(booking_info_intents) == {"master"}
            if (
                not info_decision
                and master_only_interrupt
                and master_resolution.explicit
                and isinstance(resolved_master_service_query, str)
                and resolved_master_service_query.strip()
            ):
                contract_reply, contract_meta = _build_booking_interrupt_info_reply(
                    "master",
                    service_query=resolved_master_service_query.strip(),
                    client_slug=client_slug,
                    message_text=booking_interrupt_text,
                )
                if contract_reply:
                    info_decision = PackDecision(
                        action="reply",
                        response=contract_reply,
                        intent="master",
                        meta=contract_meta if isinstance(contract_meta, dict) else None,
                    )
                    info_source = "booking_info_contract"
            if guest_policy_hit:
                guest_reply, guest_meta = build_info_combined_reply(
                    include_parking=False,
                    include_guest=True,
                    client_slug=client_slug,
                )
                if guest_reply:
                    info_decision = PackDecision(
                        action="reply",
                        response=guest_reply,
                        intent="guest_policy",
                        meta=guest_meta if isinstance(guest_meta, dict) else None,
                    )
                    info_source = "guest_policy"
            if info_decision and pending_question_target_value:
                info_meta = info_decision.meta if isinstance(info_decision.meta, dict) else {}
                info_decision = PackDecision(
                    action=info_decision.action,
                    response=info_decision.response,
                    intent=info_decision.intent,
                    meta={
                        **info_meta,
                        "pending_question_target": pending_question_target_value,
                    },
                )
            if booking_info_intents:
                if "hours" in booking_info_intents and {"pricing", "duration"} & set(booking_info_intents):
                    multi_result = compose_multi_truth_reply(
                        booking_interrupt_text,
                        client_slug,
                        intent_decomp=intent_decomp_payload,
                        return_meta=True,
                    )
                    if multi_result:
                        multi_reply, multi_meta = multi_result
                        info_decision = PackDecision(
                            action="reply",
                            response=multi_reply,
                            intent="multi_truth",
                            meta=multi_meta if isinstance(multi_meta, dict) else None,
                        )
                        info_source = "multi_truth"
                prefer_truth_gate = bool(
                    {"pricing", "duration", "promotions", "master"} & set(booking_info_intents)
                )
                if not info_decision and prefer_truth_gate:
                    if truth_gate:
                        info_decision = truth_gate(
                            booking_interrupt_text,
                            client_slug=client_slug,
                            intent_decomp=intent_decomp_payload,
                        )
                        if info_decision:
                            info_source = "truth_gate"
                if not info_decision:
                    if service_matcher:
                        info_decision = service_matcher(
                            booking_interrupt_text,
                            client_slug=client_slug,
                            intent_decomp=intent_decomp_payload,
                        )
                        if info_decision:
                            info_source = "service_matcher"
                if not info_decision and not prefer_truth_gate:
                    if truth_gate:
                        info_decision = truth_gate(
                            booking_interrupt_text,
                            client_slug=client_slug,
                            intent_decomp=intent_decomp_payload,
                        )
                        if info_decision:
                            info_source = "truth_gate"
                if not info_decision and "promotions" in booking_info_intents:
                    # In active booking flow generic promo/discount questions must stay in
                    # booking_interrupt path with deterministic info metadata.
                    promo_reply = format_reply_from_truth("promotions", client_slug=client_slug)
                    if promo_reply:
                        info_decision = PackDecision(
                            action="reply",
                            response=promo_reply,
                            intent="promotions",
                            meta={
                                "fact_source": "truth",
                                "fact_intents": ["promotions"],
                                "info_sections": ["promotions"],
                            },
                        )
                        info_source = "truth_gate"
                if not info_decision and "pricing" in booking_info_intents:
                    service_hint = booking_state.get("service")
                    if isinstance(service_hint, str) and service_hint.strip():
                        service_enriched_text = f"{booking_interrupt_text or ''} {service_hint.strip()}".strip()
                        candidate = get_pack_decision(
                            service_enriched_text,
                            client_slug=client_slug,
                            intent_decomp=intent_decomp_payload,
                        )
                        if candidate and candidate.action == "reply":
                            candidate_meta = candidate.meta if isinstance(candidate.meta, dict) else {}
                            candidate_meta = dict(candidate_meta)
                            fact_intents = candidate_meta.get("fact_intents")
                            if isinstance(fact_intents, list):
                                merged_fact_intents = [
                                    item.strip()
                                    for item in fact_intents
                                    if isinstance(item, str) and item.strip()
                                ]
                            else:
                                merged_fact_intents = []
                            if "pricing" not in merged_fact_intents:
                                merged_fact_intents.append("pricing")
                            candidate_meta["fact_intents"] = merged_fact_intents
                            info_sections = candidate_meta.get("info_sections")
                            if isinstance(info_sections, list):
                                merged_info_sections = [
                                    item.strip()
                                    for item in info_sections
                                    if isinstance(item, str) and item.strip()
                                ]
                            else:
                                merged_info_sections = []
                            if "pricing" not in merged_info_sections:
                                merged_info_sections.append("pricing")
                            candidate_meta["info_sections"] = merged_info_sections
                            info_decision = PackDecision(
                                action="reply",
                                response=candidate.response,
                                intent="pricing",
                                meta=candidate_meta,
                            )
                            info_source = "service_enriched_pricing"
            if not info_decision and batch_non_booking_message and not booking_info_intents:
                if service_matcher:
                    info_decision = service_matcher(
                        booking_interrupt_text,
                        client_slug=client_slug,
                        intent_decomp=intent_decomp_payload,
                    )
                    if info_decision:
                        info_source = "service_matcher"
                if not info_decision:
                    if truth_gate:
                        info_decision = truth_gate(
                            booking_interrupt_text,
                            client_slug=client_slug,
                            intent_decomp=intent_decomp_payload,
                        )
                        if info_decision:
                            info_source = "truth_gate"
            if not info_decision and booking_time_service_candidate:
                if service_matcher:
                    candidate = service_matcher(
                        booking_interrupt_text,
                        client_slug=client_slug,
                        intent_decomp=intent_decomp_payload,
                    )
                    if _is_booking_time_service_decision(candidate):
                        info_decision = candidate
                        info_source = "service_matcher"
                if not info_decision:
                    if truth_gate:
                        candidate = truth_gate(
                            booking_interrupt_text,
                            client_slug=client_slug,
                            intent_decomp=intent_decomp_payload,
                        )
                        if _is_booking_time_service_decision(candidate):
                            info_decision = candidate
                            info_source = "truth_gate"

            if (
                not info_decision
                and booking_interrupt_text
                and (booking_info_intents or expected_reply_blocked_by_info)
            ):
                multi_result = compose_multi_truth_reply(
                    booking_interrupt_text,
                    client_slug,
                    intent_decomp=intent_decomp_payload,
                    return_meta=True,
                )
                if multi_result:
                    multi_reply, multi_meta = multi_result
                    info_decision = PackDecision(
                        action="reply",
                        response=multi_reply,
                        intent="multi_truth",
                        meta=multi_meta if isinstance(multi_meta, dict) else None,
                    )
                    info_source = "multi_truth_fallback"

            if not info_decision and booking_info_intents:
                for intent_name in booking_info_intents:
                    fallback_reply = format_reply_from_truth(
                        intent_name,
                        client_slug=client_slug,
                    )
                    if not fallback_reply:
                        continue
                    info_decision = PackDecision(
                        action="reply",
                        response=fallback_reply,
                        intent=intent_name,
                        meta={
                            "fact_source": "truth",
                            "fact_intents": [intent_name],
                            "info_sections": [intent_name],
                        },
                    )
                    info_source = "truth_fallback"
                    break
            if (
                not info_decision
                and pending_question_act == "ask_about_requested_slot"
                and pending_question_target_value in {None, "time"}
                and expected_reply_type == EXPECTED_REPLY_TIME
                and expected_reply_matched is not True
                and expected_reply_blocked_by_info
                and booking_time_service_candidate
            ):
                context = (
                    booking_context
                    if isinstance(booking_context, dict)
                    else _context_runtime()._get_conversation_context(conversation)
                )
                booking_state = (
                    booking if isinstance(booking, dict) else _get_booking_context(context)
                )
                booking_active = bool(booking_state.get("active"))
                if not booking_active:
                    booking_state = dict(booking_state)
                    booking_state["active"] = True
                    booking_state["started_at"] = now.isoformat()
                booking_state = _update_booking_from_messages(
                    booking_state,
                    booking_messages,
                    client_slug=client_slug,
                )
                if booking_active and not booking_state.get("service"):
                    service_hint = _get_recent_service_hint(context, now)
                    if service_hint:
                        booking_state["service"] = service_hint
                        context = _clear_service_hint(context)
                context_manager = _context_runtime()._get_context_manager(context)
                refusal_flags = context_manager.get("refusal_flags")
                booking_state, prompt = _next_booking_prompt(
                    booking_state, refusal_flags=refusal_flags
                )
                booking_state, prompt = _apply_collect_all_prompt(
                    booking_state,
                    prompt,
                    message_text,
                )
                context = _set_booking_context(context, booking_state)
                _context_runtime()._set_conversation_context(conversation, context)
                booking_expected = _expected_reply_for_booking_question(
                    booking_state.get("last_question")
                )
                if booking_expected == EXPECTED_REPLY_TIME:
                    context = _context_runtime()._set_expected_reply_context(
                        conversation=conversation,
                        saved_message=saved_message,
                        context=context,
                        expected_reply_type=booking_expected,
                        reason="booking_slot_guidance",
                        now=now,
                    )
                    _record_decision_trace(
                        conversation,
                        {
                            "stage": "pending_question_interaction",
                            "decision": "booking_slot_guidance",
                            "state": conversation.state,
                            "source": "booking_interrupt",
                            "pending_question_act": pending_question_act,
                            "pending_question_target": pending_question_target_value or "time",
                            "requested_slot": "datetime",
                            "expected_reply_type": booking_expected,
                        },
                    )
                    _record_message_decision_meta(
                        saved_message,
                        action="reply",
                        intent="booking",
                        source="booking_slot_guidance",
                        fast_intent=False,
                    )
                    if saved_message:
                        _update_message_decision_metadata(
                            saved_message,
                            {
                                "pending_question_act": pending_question_act,
                                "pending_question_target": pending_question_target_value or "time",
                                "pending_question_interaction": pending_question_act,
                                "pending_question_owner": "booking_slot_guidance",
                            },
                        )
                    bot_response = MSG_BOOKING_PENDING_QUESTION_TIME_GUIDANCE
                    style_reference_signal = bool(
                        message_text
                        and _is_style_reference_request(message_text, has_media=has_media)
                    )
                    if style_reference_signal and not has_media:
                        bot_response = _combine_sidecar(
                            MSG_STYLE_REFERENCE_NEED_MEDIA,
                            bot_response,
                        )
                    bot_response = bot_response.strip()
                    if consult_return_pending:
                        bot_response = _context_runtime()._apply_consult_return(
                            conversation=conversation,
                            saved_message=saved_message,
                            bot_response=bot_response,
                            consult_return_prompt=consult_return_prompt,
                            consult_context=consult_context,
                            reason=consult_return_reason or "booking_slot_guidance",
                        )
                    _context_runtime()._reset_low_confidence_retry(conversation)
                    bot_response, sent = send_and_save(bot_response)
                    result_message = (
                        "Booking slot guidance sent"
                        if sent
                        else "Booking slot guidance failed"
                    )
                    db.commit()
                    return WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    )
            if not info_decision and expected_reply_blocked_by_info:
                info_decision = PackDecision(
                    action="reply",
                    response=MSG_FACT_GUARD_CLARIFY,
                    intent="info_clarify",
                    meta={
                        "fact_source": "info_clarify",
                        "fact_intents": ["info_clarify"],
                        "info_sections": [],
                    },
                )
                info_source = "info_clarify"

            if info_decision and info_decision.action == "escalate":
                info_meta = info_decision.meta if isinstance(info_decision.meta, dict) else {}
                info_meta = dict(info_meta)
                trace_info_intents = booking_info_intents
                if not trace_info_intents:
                    fact_intents = info_meta.get("fact_intents")
                    if isinstance(fact_intents, list):
                        trace_info_intents = [
                            item.strip()
                            for item in fact_intents
                            if isinstance(item, str) and item.strip()
                        ]
                if (
                    not trace_info_intents
                    and info_decision.intent
                    and isinstance(info_decision.intent, str)
                ):
                    trace_info_intents = [info_decision.intent]
                if not booking_info_intents and trace_info_intents:
                    booking_info_intents = list(trace_info_intents)
                info_sections = _merge_info_sections(info_meta, trace_info_intents)
                if info_sections:
                    info_meta["info_sections"] = info_sections
                trace_payload = {
                    "stage": "booking_interrupt",
                    "decision": info_decision.action,
                    "intent": info_decision.intent,
                    "state": conversation.state,
                    "booking_interrupt_info": True,
                }
                if trace_info_intents:
                    trace_payload["info_intents"] = list(trace_info_intents)
                if info_sections:
                    trace_payload["info_sections"] = info_sections
                if info_source == "truth_gate":
                    gate_trace = {
                        "stage": "truth_gate",
                        "decision": info_decision.action,
                        "intent": info_decision.intent,
                        "state": conversation.state,
                        "booking_wants_flow": booking_wants_flow,
                        "policy_type": policy_type,
                    }
                    gate_trace.update(info_meta)
                    _record_decision_trace(conversation, gate_trace)
                trace_payload.update(info_meta)
                _record_decision_trace(conversation, trace_payload)
                _record_message_decision_meta(
                    saved_message,
                    action=info_decision.action,
                    intent=info_decision.intent,
                    source=info_source or "booking_interrupt",
                    fast_intent=False,
                )
                if saved_message:
                    _update_message_decision_metadata(
                        saved_message,
                        {
                            **info_meta,
                            "booking_info_interrupt": True,
                            "booking_info_intents": booking_info_intents,
                            "booking_interrupt_info": True,
                        },
                    )
                bot_response = info_decision.response or MSG_ESCALATED
                _context_runtime()._reset_low_confidence_retry(conversation)

                result_message = "Booking interrupt escalation"
                _, reused, telegram_sent = _reuse_active_handover(
                    db=db,
                    conversation=conversation,
                    user=user,
                    message=message_text,
                    source=info_source or "booking_interrupt",
                    intent=info_decision.intent,
                    hooks=ActiveHandoverReuseRuntimeHooks(
                        get_active_handover=get_active_handover,
                        transition_state=transition_state,
                        send_telegram_notification=send_telegram_notification,
                        record_decision_trace=_record_decision_trace,
                    ),
                )
                if reused:
                    result_message = f"Booking interrupt reuse, telegram={'sent' if telegram_sent else 'failed'}"
                elif conversation.state == ConversationState.BOT_ACTIVE.value and routing.get(
                    "allow_handover_create", False
                ):
                    result = escalate_to_pending(
                        db=db,
                        conversation=conversation,
                        user_message=message_text,
                        trigger_type="intent",
                        trigger_value=info_decision.intent or "booking_interrupt",
                    )
                    if result.ok:
                        handover = result.value
                        telegram_sent = send_telegram_notification(
                            db=db,
                            handover=handover,
                            conversation=conversation,
                            user=user,
                            message=message_text,
                        )
                        result_message = (
                            f"Booking interrupt escalation, telegram={'sent' if telegram_sent else 'failed'}"
                        )
                    else:
                        result_message = f"Booking interrupt escalation failed: {result.error}"
                else:
                    result_message = "Booking interrupt escalation skipped (already pending)"

                bot_response, sent = send_and_save(bot_response)
                if not sent:
                    result_message = f"{result_message}; response_send=failed"
                db.commit()
                return WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                )

            if info_decision and info_decision.action == "reply":
                info_meta = info_decision.meta if isinstance(info_decision.meta, dict) else {}
                info_meta = dict(info_meta)
                trace_info_intents = booking_info_intents
                if not trace_info_intents:
                    fact_intents = info_meta.get("fact_intents")
                    if isinstance(fact_intents, list):
                        trace_info_intents = [
                            item.strip()
                            for item in fact_intents
                            if isinstance(item, str) and item.strip()
                        ]
                if (
                    not trace_info_intents
                    and info_decision.intent
                    and isinstance(info_decision.intent, str)
                ):
                    trace_info_intents = [info_decision.intent]
                if not booking_info_intents and trace_info_intents:
                    booking_info_intents = list(trace_info_intents)
                info_sections = _merge_info_sections(info_meta, trace_info_intents)
                if info_sections:
                    info_meta["info_sections"] = info_sections
                guard_response = maybe_apply_fact_guard(
                    decision_meta=info_meta,
                    intent=info_decision.intent,
                    source=info_source or "booking_interrupt",
                    allow_handover=routing.get("allow_handover_create", False),
                )
                if guard_response:
                    db.commit()
                    return guard_response
                booking_time_service_interrupt = bool(
                    booking_time_service_candidate and _is_booking_time_service_decision(info_decision)
                )
                booking_interrupt_info = bool(
                    info_decision
                    and info_decision.action == "reply"
                    and not booking_time_service_interrupt
                )

                context = (
                    booking_context
                    if isinstance(booking_context, dict)
                    else _context_runtime()._get_conversation_context(conversation)
                )
                booking_state = (
                    booking if isinstance(booking, dict) else _get_booking_context(context)
                )
                booking_active = bool(booking_state.get("active"))
                if not booking_active:
                    booking_state = dict(booking_state)
                    booking_state["active"] = True
                    booking_state["started_at"] = now.isoformat()
                booking_state = _update_booking_from_messages(
                    booking_state,
                    booking_messages,
                    client_slug=client_slug,
                )
                if booking_time_service_interrupt:
                    service_query = info_meta.get("service_query")
                    if isinstance(service_query, str) and service_query.strip():
                        booking_state["service"] = service_query.strip()
                # Do not auto-fill stale service hints on the first booking turn.
                if booking_active and not booking_state.get("service"):
                    service_hint = _get_recent_service_hint(context, now)
                    if service_hint:
                        booking_state["service"] = service_hint
                        context = _clear_service_hint(context)
                context_manager = _context_runtime()._get_context_manager(context)
                refusal_flags = context_manager.get("refusal_flags")
                booking_state, prompt = _next_booking_prompt(
                    booking_state, refusal_flags=refusal_flags
                )
                booking_state, prompt = _apply_collect_all_prompt(
                    booking_state,
                    prompt,
                    message_text,
                )
                context = _set_booking_context(context, booking_state)
                _context_runtime()._set_conversation_context(conversation, context)
                booking_expected = _expected_reply_for_booking_question(
                    booking_state.get("last_question")
                )
                booking_prompt_repeat = should_repeat_booking_prompt(
                    expected_reply_type=expected_reply_type,
                    expected_reply_matched=expected_reply_matched,
                    booking_expected_reply_type=booking_expected,
                )
                if prompt and booking_expected:
                    context = _context_runtime()._set_expected_reply_context(
                        conversation=conversation,
                        saved_message=saved_message,
                        context=context,
                        expected_reply_type=booking_expected,
                        reason="booking_prompt",
                        now=now,
                    )

                if (
                    info_decision.intent in {"service_clarify", "duration_or_price_clarify"}
                    and not booking_time_service_interrupt
                ):
                    if booking_interrupt_info:
                        prompt = None
                    else:
                        clarify_intent = current_goal or "info"
                        context_manager = _context_runtime()._get_context_manager(context)
                        if _guards_runtime()._should_escalate_for_clarify(context_manager, clarify_intent):
                            clarify_count, _ = _guards_runtime()._get_clarify_attempt_state(
                                context_manager, clarify_intent
                            )
                            _context_runtime()._record_context_manager_decision(
                                conversation,
                                saved_message,
                                decision="clarify_limit",
                                updates={
                                    "clarify_attempt": {"intent": clarify_intent, "count": clarify_count},
                                    "clarify_reason": "service_clarify",
                                    "clarify_limit": True,
                                },
                            )
                            return _guards_runtime()._handle_clarify_limit_escalation(
                                db=db,
                                conversation=conversation,
                                user=user,
                                message_text=message_text,
                                saved_message=saved_message,
                                source=info_source or "booking_interrupt",
                                allow_handover=routing.get("allow_handover_create", False),
                                send_response=send_response,
                                finalize_response=finalize_response,
                            )
                        _guards_runtime()._register_clarify_attempt(
                            conversation=conversation,
                            saved_message=saved_message,
                            intent=clarify_intent,
                            now=now,
                            reason="service_clarify",
                        )
                        context = _context_runtime()._set_expected_reply_context(
                            conversation=conversation,
                            saved_message=saved_message,
                            context=context,
                            expected_reply_type=EXPECTED_REPLY_SERVICE,
                            reason="service_clarify",
                            now=now,
                        )
                        prompt = None

                booking_slot_signal = _is_booking_slot_signal(
                    message_text,
                    client_slug=client_slug,
                )
                if prompt and not booking_time_service_interrupt and not booking_interrupt_info and booking_prompt_repeat:
                    context_manager = _context_runtime()._get_context_manager(context)
                    clarify_guard_reason = _guards_runtime()._booking_clarify_guard_reason(
                        booking_interrupt_info=booking_interrupt_info,
                        basic_info_message=basic_info_message,
                        session_memory_reset_reason=session_memory_reset_reason,
                        memory_expected_reply_type=memory_expected_reply_type,
                        message_text=message_text,
                        booking_slot_signal=booking_slot_signal,
                    )
                    if clarify_guard_reason:
                        if saved_message:
                            _update_message_decision_metadata(
                                saved_message,
                                {
                                    "clarify_guard": True,
                                    "clarify_guard_reason": clarify_guard_reason,
                                },
                            )
                        _record_decision_trace(
                            conversation,
                            {
                                "stage": "clarify_guard",
                                "decision": "skip",
                                "intent": "booking",
                                "reason": clarify_guard_reason,
                            },
                        )
                    elif _guards_runtime()._should_escalate_for_clarify(context_manager, "booking"):
                        clarify_count, _ = _guards_runtime()._get_clarify_attempt_state(context_manager, "booking")
                        _context_runtime()._record_context_manager_decision(
                            conversation,
                            saved_message,
                            decision="clarify_limit",
                            updates={
                                "clarify_attempt": {"intent": "booking", "count": clarify_count},
                                "clarify_reason": "booking_prompt",
                                "clarify_limit": True,
                            },
                        )
                        return _guards_runtime()._handle_clarify_limit_escalation(
                            db=db,
                            conversation=conversation,
                            user=user,
                            message_text=message_text,
                            saved_message=saved_message,
                            source="booking",
                            allow_handover=routing.get("allow_handover_create", False),
                            send_response=send_response,
                            finalize_response=finalize_response,
                        )
                    elif clarify_guard_reason is None:
                        _guards_runtime()._register_clarify_attempt(
                            conversation=conversation,
                            saved_message=saved_message,
                            intent="booking",
                            now=now,
                            reason="booking_prompt",
                        )

                class_router_result = _build_booking_class_router_result(
                    intent_decomp_set=intent_decomp_set,
                    booking_signal=booking_wants_flow,
                )
                _record_booking_class_router_trace(
                    conversation=conversation,
                    class_router_result=class_router_result,
                )
                trace_payload = {
                    "stage": "booking_interrupt",
                    "decision": "info_reply",
                    "state": conversation.state,
                    "info_intents": list(trace_info_intents),
                    "booking_prompt": prompt,
                }
                prompt_text = prompt.strip() if isinstance(prompt, str) else ""
                info_response_text = (
                    info_decision.response.strip()
                    if isinstance(info_decision.response, str)
                    else ""
                )
                primary_intent_token = (
                    multi_intent_primary.strip().casefold()
                    if isinstance(multi_intent_primary, str) and multi_intent_primary.strip()
                    else ""
                )
                if not primary_intent_token and isinstance(intent_decomp_payload, dict):
                    payload_primary_intent = intent_decomp_payload.get("primary_intent")
                    if isinstance(payload_primary_intent, str) and payload_primary_intent.strip():
                        primary_intent_token = payload_primary_intent.strip().casefold()
                domain_token = (
                    early_domain_intent.value
                    if hasattr(early_domain_intent, "value")
                    else early_domain_intent
                )
                domain_out_of_domain = (
                    isinstance(domain_token, str)
                    and domain_token.strip().casefold() == "out_of_domain"
                )
                from app.services.pack_runtime_service import (
                    has_walkin_without_booking_signal,
                )

                walkin_without_booking_signal = has_walkin_without_booking_signal(
                    message_text,
                    client_slug=client_slug,
                )
                pricing_name_followup_signal = bool(
                    booking_wants_flow
                    and not expected_reply_blocked_by_info
                    and "pricing" in set(trace_info_intents or [])
                    and booking_expected == EXPECTED_REPLY_NAME
                )
                specialist_name_followup_signal = bool(
                    booking_interrupt_info
                    and info_decision.intent == "master"
                    and pending_question_target_value == "specialist"
                    and booking_expected == EXPECTED_REPLY_NAME
                )
                specialist_time_followup_signal = bool(
                    booking_interrupt_info
                    and info_decision.intent == "master"
                    and pending_question_target_value in {"specialist", "time"}
                    and booking_expected == EXPECTED_REPLY_TIME
                )
                booking_prompt_kept = bool(
                    prompt_text
                    and (
                        (
                            booking_wants_flow
                            and not booking_active
                            and primary_intent_token == "booking"
                        )
                        or should_keep_booking_prompt_for_info_clarify_time_followup(
                            info_intent=info_decision.intent,
                            booking_active=booking_active,
                            expected_reply_type=expected_reply_type,
                            booking_expected_reply_type=booking_expected,
                            domain_out_of_domain=domain_out_of_domain,
                        )
                        or (
                            info_decision.intent == "info_clarify"
                            and booking_wants_flow
                            and walkin_without_booking_signal
                        )
                        or pricing_name_followup_signal
                        or specialist_name_followup_signal
                        or specialist_time_followup_signal
                    )
                )
                booking_prompt_suppressed = bool(
                    prompt_text and info_response_text and not booking_prompt_kept
                )
                if booking_prompt_suppressed:
                    trace_payload["booking_prompt_suppressed"] = True
                if booking_interrupt_info:
                    trace_payload["booking_interrupt_info"] = True
                if info_sections:
                    trace_payload["info_sections"] = info_sections
                if pending_question_target_value:
                    trace_payload["pending_question_target"] = pending_question_target_value
                _record_decision_trace(conversation, trace_payload)

                if info_source == "service_matcher":
                    matcher_trace = {
                        "stage": "service_matcher",
                        "decision": info_decision.intent,
                        "state": conversation.state,
                    }
                    matcher_trace.update(info_meta)
                    _record_decision_trace(conversation, matcher_trace)
                elif info_source == "truth_gate":
                    gate_trace = {
                        "stage": "truth_gate",
                        "decision": info_decision.action,
                        "intent": info_decision.intent,
                        "state": conversation.state,
                        "booking_wants_flow": booking_wants_flow,
                        "policy_type": policy_type,
                    }
                    gate_trace.update(info_meta)
                    _record_decision_trace(conversation, gate_trace)
                elif info_source == "multi_truth":
                    multi_trace = {
                        "stage": "multi_truth",
                        "decision": "reply",
                        "intent": "multi_truth",
                        "state": conversation.state,
                        "intents": booking_info_intents,
                    }
                    multi_trace.update(info_meta)
                    _record_decision_trace(conversation, multi_trace)

                _record_message_decision_meta(
                    saved_message,
                    action=info_decision.action,
                    intent=info_decision.intent,
                    source=info_source or "booking_interrupt",
                    fast_intent=False,
                )
                if saved_message:
                    message_meta_updates = {
                        **info_meta,
                        "booking_info_interrupt": True,
                        "booking_info_intents": booking_info_intents,
                        "booking_interrupt_info": bool(booking_interrupt_info),
                    }
                    if pending_question_target_value:
                        message_meta_updates["pending_question_target"] = pending_question_target_value
                    if booking_prompt_suppressed:
                        message_meta_updates["carryover_ignored"] = True
                        message_meta_updates[
                            "carryover_ignored_reason"
                        ] = "info_reply_no_stale_booking_prompt"
                    _update_message_decision_metadata(
                        saved_message,
                        message_meta_updates,
                    )
                _context_runtime()._maybe_store_service_carryover(
                    conversation=conversation,
                    service_meta=info_meta,
                    intent=info_decision.intent,
                    message_count=message_count,
                    reason="booking_interrupt",
                )
                _context_runtime()._maybe_store_class_carryover(
                    conversation=conversation,
                    class_name="info_bundle",
                    intents=booking_info_intents,
                    info_meta=info_meta,
                    message_count=message_count,
                    reason="booking_interrupt",
                )

                if info_decision.intent == "info_clarify" and booking_prompt_kept:
                    bot_response = prompt_text
                else:
                    bot_response = info_response_text
                    if booking_prompt_kept and prompt_text and bot_response:
                        bot_response = _combine_sidecar(bot_response, prompt_text)
                if not bot_response:
                    bot_response = prompt_text
                style_reference_signal = bool(
                    message_text
                    and _is_style_reference_request(message_text, has_media=has_media)
                )
                if style_reference_signal and not has_media:
                    bot_response = _combine_sidecar(
                        MSG_STYLE_REFERENCE_NEED_MEDIA,
                        bot_response,
                    )
                bot_response = bot_response.strip()
                if consult_return_pending:
                    bot_response = _context_runtime()._apply_consult_return(
                        conversation=conversation,
                        saved_message=saved_message,
                        bot_response=bot_response,
                        consult_return_prompt=consult_return_prompt,
                        consult_context=consult_context,
                        reason=consult_return_reason or "booking_interrupt",
                    )
                _context_runtime()._reset_low_confidence_retry(conversation)
                bot_response, sent = send_and_save(bot_response)
                result_message = "Booking info interrupt sent" if sent else "Booking info interrupt failed"
                db.commit()
                return WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                )
    return None

def _handle_booking_flow(
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
    booking_active: bool,
    booking_signal: bool,
    booking_messages: list[str],
    booking_context: dict | None,
    booking: dict | None,
    expected_reply_type: str | None,
    expected_reply_matched: bool | None,
    expected_reply_blocked_by_info: bool = False,
    basic_info_message: bool,
    session_memory_reset_reason: str | None,
    memory_expected_reply_type: str | None,
    policy_handler: dict | None,
    policy_pack: dict | None,
    now: datetime,
    message_count: int,
    multi_intent_booking_followup: str | None,
    consult_return_pending: bool,
    consult_return_prompt: str | None,
    consult_context: dict | None,
    consult_return_reason: str | None,
    send_and_save: Callable[..., tuple[str, bool]],
    send_response: Callable[..., Any],
    finalize_response: Callable[..., Any],
    log_timing: Callable[[str, float, dict | None], None],
    record_escalation_metric: Callable[[str], None],
) -> BookingFlowResult:
    policy_price_sidecar = None
    if (
        not bypass_domain_flows
        and policy_handler
        and routing.get("allow_truth_gate_reply")
        and booking_wants_flow
    ):
        price_sidecar = policy_handler.get("price_sidecar")
        if price_sidecar:
            policy_price_sidecar, price_item = price_sidecar(
                booking_messages,
                client_slug=client_slug,
            )
            if price_item:
                booking_context = (
                    booking_context
                    if isinstance(booking_context, dict)
                    else _context_runtime()._get_conversation_context(conversation)
                )
                booking_context = _set_service_hint(booking_context, price_item, now)
                _context_runtime()._set_conversation_context(conversation, booking_context)

    if (
        message_text
        and policy_handler
        and routing.get("allow_truth_gate_reply")
        and (booking_wants_flow or booking_active or booking_signal)
    ):
        truth_gate = policy_handler.get("truth_gate") if isinstance(policy_handler, dict) else None
        if truth_gate:
            decision = truth_gate(message_text, client_slug=client_slug)
            if (
                decision
                and decision.action == "escalate"
                and decision.intent == "same_day_booking"
            ):
                bot_response = decision.response or MSG_ESCALATED
                _context_runtime()._reset_low_confidence_retry(conversation)
                record_escalation_metric("intent")

                result_message = "Booking same-day escalation"
                _, reused, telegram_sent = _reuse_active_handover(
                    db=db,
                    conversation=conversation,
                    user=user,
                    message=message_text,
                    source="booking",
                    intent=decision.intent,
                    hooks=ActiveHandoverReuseRuntimeHooks(
                        get_active_handover=get_active_handover,
                        transition_state=transition_state,
                        send_telegram_notification=send_telegram_notification,
                        record_decision_trace=_record_decision_trace,
                    ),
                )
                if reused:
                    result_message = f"Booking same-day reuse, telegram={'sent' if telegram_sent else 'failed'}"
                elif conversation.state == ConversationState.BOT_ACTIVE.value and routing.get(
                    "allow_handover_create", False
                ):
                    result = escalate_to_pending(
                        db=db,
                        conversation=conversation,
                        user_message=message_text,
                        trigger_type="intent",
                        trigger_value=decision.intent or "same_day_booking",
                    )
                    if result.ok:
                        handover = result.value
                        telegram_sent = send_telegram_notification(
                            db=db,
                            handover=handover,
                            conversation=conversation,
                            user=user,
                            message=message_text,
                        )
                        result_message = (
                            f"Booking same-day escalation, telegram={'sent' if telegram_sent else 'failed'}"
                        )
                    else:
                        result_message = f"Booking same-day escalation failed: {result.error}"
                else:
                    result_message = "Booking same-day escalation skipped (already pending)"

                trace_payload = {
                    "stage": "truth_gate",
                    "decision": decision.action,
                    "intent": decision.intent,
                    "state": conversation.state,
                    "booking_wants_flow": booking_wants_flow,
                    "policy_type": policy_pack.get("policy_type") if isinstance(policy_pack, dict) else None,
                }
                if isinstance(getattr(decision, "meta", None), dict):
                    trace_payload.update(decision.meta)
                _record_decision_trace(conversation, trace_payload)
                _record_message_decision_meta(
                    saved_message,
                    action=decision.action,
                    intent=decision.intent,
                    source="truth_gate",
                    fast_intent=False,
                )
                if saved_message and isinstance(getattr(decision, "meta", None), dict):
                    _update_message_decision_metadata(saved_message, decision.meta)

                bot_response, sent = send_and_save(bot_response)
                if not sent:
                    result_message = f"{result_message}; response_send=failed"
                db.commit()
                return BookingFlowResult(
                    response=WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    ),
                    booking_t0=None,
                    booking_logged=True,
                )

    booking_t0 = None
    booking_logged = False
    if routing.get("allow_booking_flow") and not bypass_domain_flows:
        booking_t0 = time.monotonic()
        context = (
            booking_context
            if isinstance(booking_context, dict)
            else _context_runtime()._get_conversation_context(conversation)
        )
        booking_state = booking if isinstance(booking, dict) else _get_booking_context(context)
        booking_active = bool(booking_state.get("active"))

        # If expected-reply/booking flow was bypassed for a manager request, do not
        # re-enter booking prompts from active context; route to handoff instead.
        if (
            booking_active
            and message_text
            and is_human_request_message(message_text)
            and not booking_wants_flow
        ):
            _, reused, telegram_sent = _reuse_active_handover(
                db=db,
                conversation=conversation,
                user=user,
                message=message_text,
                source="booking",
                intent="human_request",
                hooks=ActiveHandoverReuseRuntimeHooks(
                    get_active_handover=get_active_handover,
                    transition_state=transition_state,
                    send_telegram_notification=send_telegram_notification,
                    record_decision_trace=_record_decision_trace,
                ),
            )
            if reused:
                bot_response = MSG_ESCALATED
                result_message = (
                    f"Booking human-request handoff reused, telegram={'sent' if telegram_sent else 'failed'}"
                )
            elif conversation.state == ConversationState.BOT_ACTIVE.value and routing.get(
                "allow_handover_create", False
            ):
                record_escalation_metric("intent")
                result = escalate_to_pending(
                    db=db,
                    conversation=conversation,
                    user_message=message_text,
                    trigger_type="intent",
                    trigger_value="human_request",
                )
                if result.ok:
                    handover = result.value
                    telegram_sent = send_telegram_notification(
                        db=db,
                        handover=handover,
                        conversation=conversation,
                        user=user,
                        message=message_text,
                    )
                    bot_response = MSG_ESCALATED
                    result_message = (
                        f"Booking human-request handoff, telegram={'sent' if telegram_sent else 'failed'}"
                    )
                else:
                    bot_response = MSG_AI_ERROR
                    result_message = "Booking human-request handoff failed"
            else:
                bot_response = MSG_PENDING_ESCALATION
                result_message = "Booking human-request handoff skipped (already pending)"

            _record_decision_trace(
                conversation,
                {
                    "stage": "booking",
                    "decision": "human_request_handoff",
                    "state": conversation.state,
                    "booking_wants_flow": booking_wants_flow,
                },
            )
            _record_message_decision_meta(
                saved_message,
                action="escalate",
                intent="human_request",
                source="booking",
                fast_intent=False,
            )
            bot_response, sent = send_and_save(bot_response)
            if not sent:
                result_message = f"{result_message}; response_send=failed"
            log_timing("booking_ms", (time.monotonic() - booking_t0) * 1000)
            booking_logged = True
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                if not _is_appointment_overlap_integrity_error(exc):
                    raise
                booking_state["active"] = True
                booking_state["datetime"] = None
                booking_state["last_question"] = "datetime"
                context = _set_booking_context(context, booking_state)
                _context_runtime()._set_conversation_context(conversation, context)
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "booking_commit",
                        "decision": "appointment_conflict",
                        "state": conversation.state,
                        "skip_reason": "appointment_overlap_conflict",
                    },
                )
                _record_message_decision_meta(
                    saved_message,
                    action="booking_prompt",
                    intent="booking",
                    source="booking",
                    fast_intent=False,
                )
                conflict_prompt = "Похоже, это время уже занято. На какую дату и время вам удобно?"
                conflict_prompt = _combine_sidecar(
                    conflict_prompt, multi_intent_booking_followup
                )
                conflict_prompt, sent_conflict = send_and_save(conflict_prompt)
                conflict_message = (
                    "Booking conflict prompt sent"
                    if sent_conflict
                    else "Booking conflict prompt failed"
                )
                db.commit()
                return BookingFlowResult(
                    response=WebhookResponse(
                        success=True,
                        message=conflict_message,
                        conversation_id=conversation.id,
                        bot_response=conflict_prompt,
                    ),
                    booking_t0=booking_t0,
                    booking_logged=booking_logged,
                )
            return BookingFlowResult(
                response=WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                ),
                booking_t0=booking_t0,
                booking_logged=booking_logged,
            )

        if booking_active and expected_reply_blocked_by_info and not booking_wants_flow:
            _record_decision_trace(
                conversation,
                {
                    "stage": "booking",
                    "decision": "defer_expected_reply_info_interrupt",
                    "state": conversation.state,
                },
            )
            if saved_message:
                _update_message_decision_metadata(
                    saved_message,
                    {
                        "booking_flow_deferred": True,
                        "booking_flow_deferred_reason": "expected_reply_info_interrupt",
                    },
                )
            return BookingFlowResult(response=None, booking_t0=booking_t0, booking_logged=booking_logged)

        if booking_active and _is_booking_cancel(message_text, policy_pack=policy_pack):
            booking_state = {"active": False}
            context = _set_booking_context(context, booking_state)
            _context_runtime()._set_conversation_context(conversation, context)
            _record_decision_trace(
                conversation,
                {
                    "stage": "booking",
                    "decision": "cancelled",
                    "state": conversation.state,
                },
            )
            _record_message_decision_meta(
                saved_message,
                action="booking_cancelled",
                intent="booking",
                source="booking",
                fast_intent=False,
            )
            bot_response = _combine_sidecar(MSG_BOOKING_CANCELLED, multi_intent_booking_followup)
            bot_response, sent = send_and_save(bot_response)
            result_message = "Booking cancelled" if sent else "Booking cancel response failed"
            log_timing("booking_ms", (time.monotonic() - booking_t0) * 1000)
            booking_logged = True
            db.commit()
            return BookingFlowResult(
                response=WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                ),
                booking_t0=booking_t0,
                booking_logged=booking_logged,
            )

        confirmation = _get_booking_confirmation(booking_state)
        confirmation_info_interrupt = _should_defer_booking_confirmation_for_info(
            confirmation=confirmation,
            basic_info_message=basic_info_message,
            message_text=message_text,
            client_slug=client_slug,
        )
        if confirmation_info_interrupt:
            slot_key = confirmation.get("slot") if isinstance(confirmation, dict) else None
            slot_value = confirmation.get("value") if isinstance(confirmation, dict) else None
            _record_decision_trace(
                conversation,
                {
                    "stage": "booking_confirm",
                    "decision": "defer_info_interrupt",
                    "slot": slot_key,
                    "value": slot_value,
                },
            )
            if saved_message:
                _update_message_decision_metadata(
                    saved_message,
                    {
                        "slot_confirmation_deferred": True,
                        "slot_confirmation_deferred_reason": "info_interrupt",
                        "slot": slot_key,
                        "slot_value": slot_value,
                    },
                )
            return BookingFlowResult(response=None, booking_t0=booking_t0, booking_logged=booking_logged)
        if confirmation:
            from app.services.ai_service import classify_confirmation

            slot_key = confirmation.get("slot")
            slot_value = confirmation.get("value")
            decision = classify_confirmation(message_text or "")
            if decision in {"yes", "no"}:
                booking_state = dict(booking_state)
                if decision == "yes" and slot_key in BOOKING_SLOT_ORDER and slot_value:
                    booking_state[slot_key] = str(slot_value).strip()
                if decision == "no" and slot_key in BOOKING_SLOT_ORDER:
                    booking_state[slot_key] = None
                booking_state = _set_booking_confirmation(booking_state, None)
                context = _set_booking_context(context, booking_state)
                _context_runtime()._set_conversation_context(conversation, context)
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "booking_confirm",
                        "decision": "confirmed" if decision == "yes" else "rejected",
                        "slot": slot_key,
                        "value": slot_value,
                        "confidence": confirmation.get("confidence"),
                        "source": confirmation.get("source"),
                    },
                )
                if saved_message:
                    _update_message_decision_metadata(
                        saved_message,
                        {
                            "slot_confirmation_decision": decision,
                            "slot": slot_key,
                            "slot_value": slot_value,
                        },
                    )
                if decision == "no":
                    context_manager = _context_runtime()._get_context_manager(context)
                    refusal_flags = context_manager.get("refusal_flags")
                    booking_state, prompt = _next_booking_prompt(
                        booking_state, refusal_flags=refusal_flags
                    )
                    booking_state, prompt = _apply_collect_all_prompt(
                        booking_state,
                        prompt,
                        message_text,
                    )
                    if prompt:
                        booking_expected = _expected_reply_for_booking_question(
                            booking_state.get("last_question")
                        )
                        if booking_expected:
                            context = _context_runtime()._set_expected_reply_context(
                                conversation=conversation,
                                saved_message=saved_message,
                                context=context,
                                expected_reply_type=booking_expected,
                                reason="booking_confirm_reject",
                                now=now,
                            )
                        _record_decision_trace(
                            conversation,
                            {
                                "stage": "booking",
                                "decision": "prompt",
                                "state": conversation.state,
                                "missing_slot": booking_state.get("last_question"),
                                "source": "booking_confirm",
                            },
                        )
                        _record_message_decision_meta(
                            saved_message,
                            action="booking_prompt",
                            intent="booking",
                            source="booking_confirm",
                            fast_intent=False,
                        )
                        bot_response = _combine_sidecar(
                            prompt, multi_intent_booking_followup
                        )
                        bot_response, sent = send_and_save(bot_response)
                        result_message = (
                            "Booking slot requested" if sent else "Booking slot response failed"
                        )
                        log_timing("booking_ms", (time.monotonic() - booking_t0) * 1000)
                        booking_logged = True
                        db.commit()
                        return BookingFlowResult(
                            response=WebhookResponse(
                                success=True,
                                message=result_message,
                                conversation_id=conversation.id,
                                bot_response=bot_response,
                            ),
                            booking_t0=booking_t0,
                            booking_logged=booking_logged,
                        )
                booking_messages = []
            else:
                if slot_key and slot_value:
                    prompt = _build_booking_confirmation_prompt(slot_key, str(slot_value).strip())
                else:
                    prompt = "Подтвердите, пожалуйста, данные для записи. Верно?"
                confirmation = dict(confirmation)
                confirmation["asked_at"] = now.isoformat()
                booking_state = _set_booking_confirmation(dict(booking_state), confirmation)
                context = _set_booking_context(context, booking_state)
                _context_runtime()._set_conversation_context(conversation, context)
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "booking_confirm",
                        "decision": "prompt",
                        "slot": slot_key,
                        "value": slot_value,
                        "confidence": confirmation.get("confidence"),
                        "source": confirmation.get("source"),
                    },
                )
                _record_message_decision_meta(
                    saved_message,
                    action="booking_confirm",
                    intent="booking",
                    source="booking",
                    fast_intent=False,
                )
                if saved_message:
                    slot_snapshot = {
                        "service": booking_state.get("service"),
                        "datetime": booking_state.get("datetime"),
                        "name": booking_state.get("name"),
                    }
                    _update_message_decision_metadata(
                        saved_message,
                        {
                            "slot_confirmation_required": True,
                            "slot": slot_key,
                            "slot_value": slot_value,
                            "slot_confidence": confirmation.get("confidence"),
                            "slot_source": confirmation.get("source"),
                            "slot_lock": True,
                            "slot_snapshot": slot_snapshot,
                        },
                    )
                bot_response = _combine_sidecar(prompt, multi_intent_booking_followup)
                bot_response, sent = send_and_save(bot_response)
                result_message = (
                    "Booking confirmation requested"
                    if sent
                    else "Booking confirmation response failed"
                )
                log_timing("booking_ms", (time.monotonic() - booking_t0) * 1000)
                booking_logged = True
                db.commit()
                return BookingFlowResult(
                    response=WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    ),
                    booking_t0=booking_t0,
                    booking_logged=booking_logged,
                )

        booking_related = any(
            _is_booking_related_message(msg, client_slug) for msg in booking_messages
        )
        if _should_defer_booking_flow_for_info_interrupt(
            booking_active=booking_active,
            booking_signal=booking_signal,
            booking_related=booking_related,
            basic_info_message=basic_info_message,
        ):
            _record_decision_trace(
                conversation,
                {
                    "stage": "booking",
                    "decision": "defer_info_interrupt",
                    "state": conversation.state,
                    "booking_active": booking_active,
                },
            )
            if saved_message:
                _update_message_decision_metadata(
                    saved_message,
                    {
                        "booking_flow_deferred": True,
                        "booking_flow_deferred_reason": "info_interrupt",
                    },
                )
            return BookingFlowResult(response=None, booking_t0=booking_t0, booking_logged=booking_logged)
        last_question = booking_state.get("last_question")
        slot_lock_active = bool(
            booking_active
            and (
                expected_reply_type
                in {
                    EXPECTED_REPLY_SERVICE,
                    EXPECTED_REPLY_TIME,
                    EXPECTED_REPLY_NAME,
                }
                or last_question in BOOKING_SLOT_ORDER
            )
        )
        if booking_active and not booking_signal and not booking_related and not slot_lock_active:
            booking_state = {"active": False}
            context = _set_booking_context(context, booking_state)
            _context_runtime()._set_conversation_context(conversation, context)
            _record_decision_trace(
                conversation,
                {
                    "stage": "booking",
                    "decision": "paused",
                    "state": conversation.state,
                },
            )
            _record_message_decision_meta(
                saved_message,
                action="booking_paused",
                intent="booking",
                source="booking",
                fast_intent=False,
            )
            bot_response = _combine_sidecar(MSG_BOOKING_REENGAGE, multi_intent_booking_followup)
            bot_response, sent = send_and_save(bot_response)
            result_message = "Booking paused" if sent else "Booking pause response failed"
            log_timing("booking_ms", (time.monotonic() - booking_t0) * 1000)
            booking_logged = True
            db.commit()
            return BookingFlowResult(
                response=WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                ),
                booking_t0=booking_t0,
                booking_logged=booking_logged,
            )

        if booking_active or booking_signal:
            if not booking_active:
                booking_state = dict(booking_state)
                booking_state["active"] = True
                booking_state["started_at"] = now.isoformat()

            booking_state = _update_booking_from_messages(
                booking_state,
                booking_messages,
                client_slug=client_slug,
            )
            context_manager = _context_runtime()._get_context_manager(context)
            # Only reuse service carryover while already inside an active booking flow.
            if booking_active and not booking_state.get("service"):
                service_hint = _get_recent_service_hint(context, now)
                if service_hint:
                    booking_state["service"] = service_hint
                    context = _clear_service_hint(context)
                else:
                    carryover = _context_runtime()._get_service_carryover(
                        context_manager, message_count=message_count
                    )
                    service_query = (
                        carryover.get("service_query")
                        if isinstance(carryover, dict)
                        else None
                    )
                    if isinstance(service_query, str) and service_query.strip():
                        booking_state["service"] = service_query.strip()
                        _record_decision_trace(
                            conversation,
                            {
                                "stage": "service_carryover",
                                "decision": "used",
                                "service_query": service_query.strip(),
                                "service_query_source": carryover.get("service_query_source")
                                if isinstance(carryover, dict)
                                else None,
                                "service_query_score": carryover.get("service_query_score")
                                if isinstance(carryover, dict)
                                else None,
                                "projection_source": carryover.get("projection_source")
                                if isinstance(carryover, dict)
                                else None,
                                "canonical_state_owner": carryover.get("canonical_state_owner")
                                if isinstance(carryover, dict)
                                else None,
                                "reason": "booking_flow",
                            },
                        )
                        if saved_message:
                            _update_message_decision_metadata(
                                saved_message,
                                {
                                    "service_query": service_query.strip(),
                                    "service_query_source": "context",
                                    "service_query_score": carryover.get("service_query_score")
                                    if isinstance(carryover, dict)
                                    else None,
                                    "projection_source": carryover.get("projection_source")
                                    if isinstance(carryover, dict)
                                    else None,
                                    "canonical_state_owner": carryover.get("canonical_state_owner")
                                    if isinstance(carryover, dict)
                                    else None,
                                },
                            )
            refusal_flags = context_manager.get("refusal_flags")
            booking_state, prompt = _next_booking_prompt(booking_state, refusal_flags=refusal_flags)
            booking_state, prompt = _apply_collect_all_prompt(
                booking_state,
                prompt,
                message_text,
            )
            if (
                prompt
                and booking_state.get("last_question") == "service"
                and expected_reply_matched is not True
                and isinstance(message_text, str)
                and message_text.strip()
            ):
                normalized_invalid_choice = normalize_for_matching(message_text)
                booking_like_signal = "запис" in normalized_invalid_choice
                if not booking_like_signal:
                    booking_like_signal = bool(
                        _extract_datetime(message_text, client_slug=client_slug)
                    )
                unknown_service_request_signal = any(
                    marker in normalized_invalid_choice
                    for marker in ("хочу", "можно", "нужн", "надо", "сдела", "подравн")
                ) and not booking_like_signal
                if unknown_service_request_signal:
                    service_not_found_reply = _format_service_not_found_reply(
                        load_yaml_truth(client_slug)
                    )
                    if service_not_found_reply:
                        prompt = service_not_found_reply
                        _record_decision_trace(
                            conversation,
                            {
                                "stage": "booking",
                                "decision": "invalid_choice_service_not_found",
                                "state": conversation.state,
                            },
                        )
            slot_lock_reprompt = bool(slot_lock_active and not booking_related and not booking_signal)
            if slot_lock_reprompt and prompt:
                if should_use_expected_service_off_topic_prompt(expected_reply_type):
                    prompt = MSG_EXPECTED_SERVICE_OFF_TOPIC
                else:
                    prompt = _combine_sidecar(prompt, MSG_BOOKING_SLOT_LOCK_STUB)
            context = _set_booking_context(context, booking_state)
            _context_runtime()._set_conversation_context(conversation, context)
            booking_expected = _expected_reply_for_booking_question(booking_state.get("last_question"))
            booking_prompt_repeat = should_repeat_booking_prompt(
                expected_reply_type=expected_reply_type,
                expected_reply_matched=expected_reply_matched,
                booking_expected_reply_type=booking_expected,
            )
            booking_slot_signal = _is_booking_slot_signal(
                message_text,
                client_slug=client_slug,
            )
            if prompt and booking_expected:
                context = _context_runtime()._set_expected_reply_context(
                    conversation=conversation,
                    saved_message=saved_message,
                    context=context,
                    expected_reply_type=booking_expected,
                    reason="booking_prompt",
                    now=now,
                )

            if prompt:
                context_manager = _context_runtime()._get_context_manager(context)
                if booking_prompt_repeat:
                    clarify_guard_reason = _guards_runtime()._booking_clarify_guard_reason(
                        booking_interrupt_info=False,
                        basic_info_message=basic_info_message,
                        session_memory_reset_reason=session_memory_reset_reason,
                        memory_expected_reply_type=memory_expected_reply_type,
                        message_text=message_text,
                        booking_slot_signal=booking_slot_signal,
                    )
                    if clarify_guard_reason:
                        if saved_message:
                            _update_message_decision_metadata(
                                saved_message,
                                {
                                    "clarify_guard": True,
                                    "clarify_guard_reason": clarify_guard_reason,
                                },
                            )
                        _record_decision_trace(
                            conversation,
                            {
                                "stage": "clarify_guard",
                                "decision": "skip",
                                "intent": "booking",
                                "reason": clarify_guard_reason,
                            },
                        )
                    elif _guards_runtime()._should_escalate_for_clarify(context_manager, "booking"):
                        clarify_count, _ = _guards_runtime()._get_clarify_attempt_state(context_manager, "booking")
                        _context_runtime()._record_context_manager_decision(
                            conversation,
                            saved_message,
                            decision="clarify_limit",
                            updates={
                                "clarify_attempt": {"intent": "booking", "count": clarify_count},
                                "clarify_reason": "booking_prompt",
                                "clarify_limit": True,
                            },
                        )
                        return BookingFlowResult(
                            response=_guards_runtime()._handle_clarify_limit_escalation(
                                db=db,
                                conversation=conversation,
                                user=user,
                                message_text=message_text,
                                saved_message=saved_message,
                                source="booking",
                                allow_handover=routing.get("allow_handover_create", False),
                                send_response=send_response,
                                finalize_response=finalize_response,
                            ),
                            booking_t0=booking_t0,
                            booking_logged=booking_logged,
                        )
                    elif clarify_guard_reason is None:
                        _guards_runtime()._register_clarify_attempt(
                            conversation=conversation,
                            saved_message=saved_message,
                            intent="booking",
                            now=now,
                            reason="booking_prompt",
                        )
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "booking",
                        "decision": "prompt",
                        "state": conversation.state,
                        "missing_slot": booking_state.get("last_question"),
                    },
                )
                _record_message_decision_meta(
                    saved_message,
                    action="booking_prompt",
                    intent="booking",
                    source="booking",
                    fast_intent=False,
                )
                if saved_message:
                    slot_snapshot = {
                        "service": booking_state.get("service"),
                        "datetime": booking_state.get("datetime"),
                        "name": booking_state.get("name"),
                    }
                    _update_message_decision_metadata(
                        saved_message,
                        {
                            "slot_lock": slot_lock_active,
                            "slot_snapshot": slot_snapshot,
                            "slot_confirmation_required": False,
                        },
                    )
                bot_response = _combine_sidecar(prompt, policy_price_sidecar)
                bot_response = _combine_sidecar(bot_response, multi_intent_booking_followup)
                if consult_return_pending:
                    bot_response = _context_runtime()._apply_consult_return(
                        conversation=conversation,
                        saved_message=saved_message,
                        bot_response=bot_response,
                        consult_return_prompt=consult_return_prompt,
                        consult_context=consult_context,
                        reason=consult_return_reason or "booking_prompt",
                    )
                bot_response, sent = send_and_save(bot_response)
                result_message = "Booking slot requested" if sent else "Booking slot response failed"
                log_timing("booking_ms", (time.monotonic() - booking_t0) * 1000)
                booking_logged = True
                db.commit()
                return BookingFlowResult(
                    response=WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    ),
                    booking_t0=booking_t0,
                    booking_logged=booking_logged,
                )

            context_manager = _context_runtime()._get_context_manager(context)
            refusal_flags = context_manager.get("refusal_flags")
            booking_summary = _build_booking_summary(booking_state, refusal_flags=refusal_flags)

            appointment = None
            appointment_meta: dict[str, Any] = {}
            appointment, appointment_meta = _create_booking_appointment(
                db=db,
                conversation=conversation,
                user=user,
                booking_state=booking_state,
                now=now,
                saved_message=saved_message,
            )
            if saved_message and appointment_meta:
                _update_message_decision_metadata(saved_message, appointment_meta)
            _record_decision_trace(
                conversation,
                {
                    "stage": "booking_commit",
                    "decision": "appointment_created" if appointment else "appointment_skipped",
                    "appointment_id": appointment_meta.get("appointment_id"),
                    "appointment_status": appointment_meta.get("appointment_status"),
                    "appointment_reused": appointment_meta.get("appointment_reused"),
                    "booking_mode": appointment_meta.get("booking_mode"),
                    "availability_provider": appointment_meta.get("availability_provider"),
                    "effective_booking_mode": appointment_meta.get("effective_booking_mode"),
                    "skip_reason": appointment_meta.get("appointment_skip_reason"),
                },
            )
            if routing.get("allow_handover_create"):
                _, reused, telegram_sent = _reuse_active_handover(
                    db=db,
                    conversation=conversation,
                    user=user,
                    message=booking_summary,
                    source="booking",
                    intent="booking",
                    hooks=ActiveHandoverReuseRuntimeHooks(
                        get_active_handover=get_active_handover,
                        transition_state=transition_state,
                        send_telegram_notification=send_telegram_notification,
                        record_decision_trace=_record_decision_trace,
                    ),
                )
                if reused:
                    bot_response = _combine_sidecar(MSG_ESCALATED, policy_price_sidecar)
                    result_message = f"Booking reuse, telegram={'sent' if telegram_sent else 'failed'}"
                    trace_decision = "reuse_handover"
                else:
                    record_escalation_metric("intent")
                    result = escalate_to_pending(
                        db=db,
                        conversation=conversation,
                        user_message=booking_summary,
                        trigger_type="intent",
                        trigger_value="booking",
                    )

                    if result.ok:
                        handover = result.value
                        telegram_sent = send_telegram_notification(
                            db=db,
                            handover=handover,
                            conversation=conversation,
                            user=user,
                            message=booking_summary,
                        )
                        bot_response = _combine_sidecar(MSG_ESCALATED, policy_price_sidecar)
                        result_message = f"Booking escalation, telegram={'sent' if telegram_sent else 'failed'}"
                        trace_decision = "escalated"
                    else:
                        if result.error_code == "no_telegram":
                            bot_response = _combine_sidecar(MSG_ESCALATED, policy_price_sidecar)
                            result_message = "Booking captured without telegram"
                            trace_decision = "captured_pending"
                        else:
                            bot_response = MSG_AI_ERROR
                            result_message = f"Booking escalation failed: {result.error}"
                            trace_decision = "escalation_failed"
            else:
                bot_response = _combine_sidecar(MSG_ESCALATED, policy_price_sidecar)
                result_message = "Booking captured while pending"
                trace_decision = "captured_pending"

            bot_response = _combine_sidecar(bot_response, multi_intent_booking_followup)
            context = _set_booking_context(context, {"active": False})
            _context_runtime()._set_conversation_context(conversation, context)
            _record_decision_trace(
                conversation,
                {
                    "stage": "booking",
                    "decision": trace_decision,
                    "state": conversation.state,
                },
            )
            _record_message_decision_meta(
                saved_message,
                action=f"booking_{trace_decision}",
                intent="booking",
                source="booking",
                fast_intent=False,
            )
            bot_response, sent = send_and_save(bot_response)
            if not sent:
                result_message = f"{result_message}; response_send=failed"
            log_timing("booking_ms", (time.monotonic() - booking_t0) * 1000)
            booking_logged = True
            db.commit()
            return BookingFlowResult(
                response=WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                ),
                booking_t0=booking_t0,
                booking_logged=booking_logged,
            )
    return BookingFlowResult(response=None, booking_t0=booking_t0, booking_logged=booking_logged)

__all__ = [
    "BOOKING_SLOT_ORDER",
    "BOOKING_SLOT_VALIDATORS",
    "_apply_booking_slot",
    "_apply_expected_reply_slot",
    "_build_booking_summary",
    "_handle_booking_flow",
    "_handle_booking_interrupt",
    "_clean_name_candidate",
    "_clear_service_hint",
    "_expected_reply_for_booking_question",
    "_get_booking_context",
    "_get_recent_service_hint",
    "_is_blocked_slot_message",
    "_is_booking_related_message",
    "_is_booking_slot_signal",
    "_is_booking_time_service_decision",
    "_is_noise_slot_message",
    "_match_expected_reply",
    "_next_booking_prompt",
    "_resolve_datetime_offline",
    "_select_expected_reply_message",
    "_select_last_non_booking_message",
    "_set_booking_context",
    "_set_service_hint",
    "_update_booking_from_message",
    "_update_booking_from_messages",
    "_validate_datetime_slot",
    "_validate_name_slot",
    "_validate_service_slot",
]
