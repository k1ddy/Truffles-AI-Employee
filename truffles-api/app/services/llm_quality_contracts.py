from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from app.services.scenario_contract_compiler import (
    compile_active_time_specialist_followup_expectations,
    should_compile_active_time_specialist_followup_expectations,
)

CHAOS_BOOKING_REPLY_TYPES = {"service_choice", "time", "name"}
LLM_QUALITY_INFO_TAGS = {
    "price",
    "location",
    "hours",
    "promo",
    "duration",
    "parking",
    "master",
}
LLM_QUALITY_EXPECT_ACTION_HANDOFF = {"booking_escalated", "escalate", "handoff"}
LLM_QUALITY_EXPECT_TAGS_ALLOW_PENDING = {
    "handoff",
    "human",
    "pending",
    "cancel",
    "reschedule",
    "media",
}
LLM_QUALITY_EXPECT_TAGS_ALLOW_MANAGER_ACTIVE = {
    "handoff",
    "human",
    "pending",
    "media",
}
LLM_QUALITY_EXPECT_INFO_TAGS = set(LLM_QUALITY_INFO_TAGS) | {"discount"}
_PENDING_QUESTION_TAGS = {
    "ask_about_requested_slot",
    "slot_constraint",
    "slot_compare",
    "mixed_fill_plus_question",
}
_PENDING_QUESTION_CONTEXT_PRESERVE_TAGS = {
    "info",
    "media",
    "price",
    "location",
    "hours",
    "promo",
    "duration",
    "parking",
    "master",
    "wrong_slot",
    "interrupt",
}
_BOOKING_SCENARIO_ACTIVE_PENDING_QUESTION_INFO_INTERRUPT_TAGS = {
    "info",
    "price",
    "duration",
    "hours",
    "location",
    "parking",
    "promo",
}
BOOKING_SCENARIO_EXPECT_INFO_SECTIONS = {
    "price": ["pricing", "price", "payment_info", "payment"],
    "location": ["address", "location"],
    "hours": ["hours", "working_hours", "schedule"],
    "promo": ["discounts", "discount", "promo", "promotion"],
    "duration": ["duration", "service_duration"],
    "parking": ["parking"],
    "master": ["master", "specialist"],
}
BOOKING_SCENARIO_EXPECT_ACTION_BY_TAG = {
    "handoff": ["booking_escalated", "escalate", "handoff"],
}
BOOKING_SCENARIO_EXPECT_REPLY_TYPE_BY_TAG = {
    "booking": "time",
    "time": "name",
    "ask_about_requested_slot": "time",
    "slot_constraint": "time",
    "slot_compare": "time",
    "mixed_fill_plus_question": "time",
}
BOOKING_SCENARIO_PENDING_QUESTION_TAGS = {
    "ask_about_requested_slot",
    "slot_constraint",
    "slot_compare",
    "mixed_fill_plus_question",
}
BOOKING_SCENARIO_TARGETED_PENDING_QUESTION_TAGS = {
    "ask_about_requested_slot",
    "slot_constraint",
    "slot_compare",
}
BOOKING_SCENARIO_EXPECT_META_ANY_BY_TAG = {
    "ask_about_requested_slot": {
        "pending_question_act": ["ask_about_requested_slot"],
        "pending_question_target": ["time"],
        "expected_reply_type": ["time"],
    },
    "slot_constraint": {
        "pending_question_act": ["slot_constraint"],
        "pending_question_target": ["time"],
        "expected_reply_type": ["time"],
    },
    "slot_compare": {
        "pending_question_act": ["slot_compare"],
        "pending_question_target": ["time"],
        "expected_reply_type": ["time"],
    },
    "mixed_fill_plus_question": {
        "expected_reply_type": ["time"],
    },
}
BOOKING_SCENARIO_EXPECT_TRACE_CONTAINS_BY_TAG = {
    "ask_about_requested_slot": [
        {
            "stage": "pending_question_interaction",
            "pending_question_act": "ask_about_requested_slot",
            "pending_question_target": "time",
        },
        {"stage": "question_contract", "expected_reply_type": "time"},
    ],
    "slot_constraint": [
        {
            "stage": "pending_question_interaction",
            "pending_question_act": "slot_constraint",
            "pending_question_target": "time",
        },
        {"stage": "question_contract", "expected_reply_type": "time"},
    ],
    "slot_compare": [
        {
            "stage": "pending_question_interaction",
            "pending_question_act": "slot_compare",
            "pending_question_target": "time",
        },
        {"stage": "question_contract", "expected_reply_type": "time"},
    ],
    "mixed_fill_plus_question": [
        {"stage": "question_contract", "expected_reply_type": "time"},
    ],
}
BOOKING_SCENARIO_EXPECT_STATE_BY_TAG = {
    "handoff": "pending",
}
BOOKING_SCENARIO_CANONICAL_EXPECT_ACTIONS = sorted(
    {
        action
        for actions in BOOKING_SCENARIO_EXPECT_ACTION_BY_TAG.values()
        for action in actions
    }
    | {"booking_prompt"}
)
BOOKING_SCENARIO_CANONICAL_EXPECT_STATES = sorted(
    set(BOOKING_SCENARIO_EXPECT_STATE_BY_TAG.values())
    | {"bot_active", "pending", "manager_active"}
)
BOOKING_SCENARIO_CANONICAL_EXPECT_REPLY_TYPES = sorted(
    set(BOOKING_SCENARIO_EXPECT_REPLY_TYPE_BY_TAG.values()) | {"service_choice"}
)
BOOKING_SCENARIO_CANONICAL_EXPECT_INFO_SECTIONS = sorted(
    {
        section
        for sections in BOOKING_SCENARIO_EXPECT_INFO_SECTIONS.values()
        for section in sections
    }
)
_BOOKING_PROGRESS_TAGS_BY_REPLY_KIND = {
    "service_choice": {"service", "multi_service"},
    "time": {"time", "time_alt", "date"},
    "name": {"name"},
}
_BOOKING_PROGRESS_SKIP_TAGS = {
    "interrupt",
    "noise",
    "media",
    "delay",
    "handoff",
    "hand_off",
    "human",
    "pending",
    "channel",
    "consult",
    "price",
    "promo",
    "location",
    "hours",
    "duration",
    "parking",
    "master",
    "cancel",
    "reschedule",
    "check_booking",
    "confirm",
    "tool",
}
_BOOKING_SCENARIO_SPECIALIST_REFERENCE_PATTERNS = (
    re.compile(r"\bмастер", re.IGNORECASE),
    re.compile(r"\bспециалист", re.IGNORECASE),
    re.compile(r"\bк\s+кому\b", re.IGNORECASE),
    re.compile(
        r"\bк\s+[A-ZА-ЯЁӘІҢҒҮҰҚӨҺ][A-Za-zА-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+\b"
    ),
    re.compile(
        r"\bу\s+[A-ZА-ЯЁӘІҢҒҮҰҚӨҺ][A-Za-zА-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+\b"
    ),
    re.compile(
        r"\bвыбр\w*\s+[A-ZА-ЯЁӘІҢҒҮҰҚӨҺ][A-Za-zА-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+\b"
    ),
)
_BOOKING_SCENARIO_GENERIC_MASTER_INFO_QUESTION_PATTERNS = (
    re.compile(
        r"\bкто\s+(?:будет\s+)?(?:делать|проводить|выполнять)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bкто\s+из\s+мастер\w*\b", re.IGNORECASE),
    re.compile(
        r"\b(?:какой|какие|какого|какому)\s+(?:мастер\w*|специалист\w*)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:какой|какие|какого|какому)\b(?:\s+\w+){0,3}\s+\b(?:мастер\w*|специалист\w*)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:есть|будут|бывают|доступн\w*|свободн\w*)\b.*\b(?:мастер\w*|специалист\w*)\b",
        re.IGNORECASE,
    ),
)
_BOOKING_SCENARIO_SPECIALIST_PREFERENCE_NAME_PATTERNS = (
    re.compile(
        r"\bпредпочит\w*\s+[A-ZА-ЯЁӘІҢҒҮҰҚӨҺ][A-Za-zА-Яа-яЁёӘәІіҢңҒғҮүҰұҚқӨөҺһ-]+\b",
        re.IGNORECASE,
    ),
)
_BOOKING_SCENARIO_STANDALONE_SPECIALIST_BOOKING_REQUEST_PATTERNS = (
    re.compile(
        r"^\s*(?:а\s+)?(?:можно|можно\s+ли|хочу|хотелось\s+бы|запишите)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bзапис\w*\b", re.IGNORECASE),
    re.compile(r"\bбола\s+ма\b", re.IGNORECASE),
    re.compile(r"\bжазыл\w*\b", re.IGNORECASE),
)
_BOOKING_SCENARIO_REQUESTED_SLOT_QUESTION_PATTERNS = (
    re.compile(r"\b(?:на|в)\s+какое\s+время\b", re.IGNORECASE),
    re.compile(
        r"\bкакое\s+время\b.*\b(?:свобод\w*|доступн\w*|слот\w*|окн\w*)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:свобод\w*|доступн\w*)\b.*\b(?:слот\w*|окн\w*|время)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:слот\w*|окн\w*)\b.*\b(?:свобод\w*|доступн\w*|время)\b",
        re.IGNORECASE,
    ),
)
_BOOKING_SCENARIO_MIXED_SLOT_CONSTRAINT_PATTERNS = (
    re.compile(
        r"\b(?:утр\w*|вечер\w*|после\s+обеда|до\s+обеда|днем|днём|после\s+\d{1,2}|до\s+\d{1,2})\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:в|к)\s*(?:[01]?\d|2[0-3])(?::[0-5]\d)?\b", re.IGNORECASE),
    re.compile(
        r"\b(?:сегодня|завтра|послезавтра|(?:на|в)\s+(?:понедельник\w*|вторник\w*|сред\w*|четверг\w*|пятниц\w*|суббот\w*|воскресень\w*|выходн\w*))\b",
        re.IGNORECASE,
    ),
)
_BOOKING_SCENARIO_MIXED_SLOT_QUESTION_PATTERNS = (
    re.compile(r"\bесть\s+ли\b", re.IGNORECASE),
    re.compile(r"\bможно\s+ли\b", re.IGNORECASE),
    re.compile(r"\bсвобод\w*\b", re.IGNORECASE),
    re.compile(r"\bслот\w*\b", re.IGNORECASE),
    re.compile(r"\bокн\w*\b", re.IGNORECASE),
)
_BOOKING_SCENARIO_PARTIAL_DATE_FILL_PATTERNS = (
    re.compile(
        r"\b(?:сегодня|завтра|послезавтра|(?:на|в)\s+(?:понедельник\w*|вторник\w*|сред\w*|четверг\w*|пятниц\w*|суббот\w*|воскресень\w*)|(?:на\s+)?(?:эту|этой|следующ\w+)\s+недел\w*)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?)\b", re.IGNORECASE),
)
_BOOKING_SCENARIO_AVAILABILITY_QUERY_PATTERNS = (
    re.compile(r"\bсвобод\w*\b", re.IGNORECASE),
    re.compile(r"\bдоступн\w*\b", re.IGNORECASE),
    re.compile(r"\bслот\w*\b", re.IGNORECASE),
    re.compile(r"\bокн\w*\b", re.IGNORECASE),
    re.compile(r"\bкогда\b", re.IGNORECASE),
    re.compile(r"\bво\s+сколько\b", re.IGNORECASE),
)
_BOOKING_SCENARIO_TIME_OCCUPANCY_QUERY_PATTERNS = (
    re.compile(r"\bзанят\w*\b", re.IGNORECASE),
    re.compile(r"\b(?:у\s+вас\s+)?есть\s+врем\w*\b", re.IGNORECASE),
)
_BOOKING_SCENARIO_MULTI_SERVICE_CONNECTOR_PATTERNS = (
    re.compile(r"\bи\b", re.IGNORECASE),
    re.compile(r"\bсначала\b", re.IGNORECASE),
    re.compile(r"\bпотом\b", re.IGNORECASE),
)
_BOOKING_SCENARIO_RESCHEDULE_VERB_PATTERNS = (
    re.compile(r"\b(?:перенест\w*|перенос\w*|поменя\w*|измен\w*|сдвин\w*)\b", re.IGNORECASE),
    re.compile(r"\b(?:ауыстыр\w*|жылжыт\w*)\b", re.IGNORECASE),
)
_BOOKING_SCENARIO_RESCHEDULE_OBJECT_PATTERNS = (
    re.compile(r"\b(?:запис\w*|бронь\w*|дат\w*|врем\w*)\b", re.IGNORECASE),
    re.compile(r"\b(?:жазыл\w*|күн\w*|уақыт\w*)\b", re.IGNORECASE),
)
_BOOKING_SCENARIO_CHECK_BOOKING_FOLLOWUP_PATTERNS = (
    re.compile(r"\bкогда\b.*\b(запис|встреч|назнач)", re.IGNORECASE),
    re.compile(r"\b(?:моя|мою)\b.*\bзапис(?:ь|и|ью|е|ей)\b", re.IGNORECASE),
    re.compile(r"\bу\s+меня\b.*\b(?:запис(?:ь|и|ью|е|ей)|встреч)\b", re.IGNORECASE),
    re.compile(r"\b(провер|уточн).*\bзапис", re.IGNORECASE),
    re.compile(r"\bназначен[ао]?\b.*\b(встреч|запис)", re.IGNORECASE),
)
_BOOKING_SCENARIO_GENERIC_BOOKING_REQUEST_PATTERNS = (
    re.compile(
        r"\b(?:хочу|хотел(?:ось)?\s+бы|мне\s+нужно|нужно|можно(?:\s+ли)?)\b.*\bзапис\w*\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bзапис\w*\b.*\b(?:на|к)\b", re.IGNORECASE),
    re.compile(r"\bжазыл\w*\b", re.IGNORECASE),
)
_BOOKING_SCENARIO_DEICTIC_TIME_REFERENCE_PATTERNS = (
    re.compile(r"\b(?:в|на)\s+это\s+время\b", re.IGNORECASE),
    re.compile(r"\b(?:в|на)\s+этот\s+слот\b", re.IGNORECASE),
    re.compile(r"\b(?:это|этот)\s+(?:время|слот)\b", re.IGNORECASE),
)
_BOOKING_SCENARIO_DEICTIC_DAY_REFERENCE_PATTERNS = (
    re.compile(r"\b(?:в|на)\s+этот\s+день\b", re.IGNORECASE),
    re.compile(r"\b(?:в|на)\s+эту\s+дат\w*\b", re.IGNORECASE),
    re.compile(r"\bэтот\s+день\b", re.IGNORECASE),
    re.compile(r"\bэту\s+дат\w*\b", re.IGNORECASE),
)
_BOOKING_SCENARIO_EXPLICIT_TIME_FILL_PATTERNS = (
    re.compile(r"\b(?:в|к|на)\s*(?:[01]?\d|2[0-3])(?::[0-5]\d)?\b", re.IGNORECASE),
    re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", re.IGNORECASE),
)
_BOOKING_SCENARIO_AMBIGUOUS_TIME_FILL_PATTERNS = (
    re.compile(r"\bили\s+(?:позже|позднее|раньше|пораньше)\b", re.IGNORECASE),
    re.compile(r"\bне\s+(?:раньше|позже)\b", re.IGNORECASE),
    re.compile(r"\b(?:после|до)\s*(?:[01]?\d|2[0-3])(?::[0-5]\d)?\b", re.IGNORECASE),
)
_BOOKING_SCENARIO_ASSISTANT_TURN_PATTERNS = (
    re.compile(r"\bвам удобно\b", re.IGNORECASE),
    re.compile(r"\bна какую\b", re.IGNORECASE),
    re.compile(r"\bна какой\b", re.IGNORECASE),
    re.compile(r"\bкакой день\b", re.IGNORECASE),
    re.compile(r"\bкак вас зовут\b", re.IGNORECASE),
    re.compile(r"\bвас зовут\b", re.IGNORECASE),
    re.compile(r"\bпришлите\b", re.IGNORECASE),
    re.compile(r"\bуточните\b", re.IGNORECASE),
    re.compile(r"\bнапишите\b", re.IGNORECASE),
    re.compile(r"\bсообщите\b", re.IGNORECASE),
    re.compile(r"\bмогу помочь\b", re.IGNORECASE),
    re.compile(r"^адрес[: ]", re.IGNORECASE),
    re.compile(r"\bработаем\b", re.IGNORECASE),
    re.compile(r"\bя вас записал\b", re.IGNORECASE),
)
_BOOKING_SCENARIO_FALLBACK_TEMPLATES_BY_TAG = {
    "location": "Где вы находитесь?",
    "hours": "Во сколько вы работаете?",
    "parking": "Есть ли парковка рядом?",
    "price": "Сколько стоит {service}?",
    "duration": "Сколько длится {service}?",
    "promo": "Есть ли акции на {service}?",
    "master": "Можно к мастеру {master}?",
    "booking": "{greet}, хочу записаться на {service}.",
    "time": "Можно {time_exact}?",
    "time_alt": "Если {time_exact} занято, можно {time_exact_alt}?",
    "ask_about_requested_slot": "На какое время лучше записаться?",
    "slot_constraint": "После обеда было бы удобнее.",
    "slot_compare": "Лучше утром или вечером?",
    "mixed_fill_plus_question": "Можно после 18, а утром или вечером лучше?",
    "name": "Меня зовут {name}.",
    "phone": "Телефон {phone}.",
    "confirm": "Да, все верно.",
    "check_booking": "Можете подтвердить мою запись?",
    "cancel": "Хочу отменить запись.",
    "reschedule": "Можно перенести запись?",
    "media": "Могу прислать фото.",
    "noise": "{noise}",
    "consult": "А у вас есть {service}?",
    "channel": "Можно только в чате?",
    "delay": "Я уточню и вернусь.",
    "handoff": "Можно связаться с менеджером?",
}
_BOOKING_SCENARIO_FALLBACK_TAG_PRIORITY = (
    "booking",
    "time",
    "ask_about_requested_slot",
    "slot_constraint",
    "slot_compare",
    "mixed_fill_plus_question",
    "name",
    "price",
    "duration",
    "location",
    "hours",
    "parking",
    "promo",
    "master",
    "check_booking",
    "cancel",
    "reschedule",
    "media",
    "noise",
    "consult",
    "channel",
    "delay",
    "handoff",
)
_BOOKING_SCENARIO_DEFAULT_SERVICE_CANDIDATES = (
    "маникюр",
    "педикюр",
    "стрижку",
    "окрашивание",
    "брови и ресницы",
    "депиляцию",
    "уход за лицом",
)
_BOOKING_SCENARIO_ORPHAN_PENDING_QUESTION_EXPECT_OVERRIDE = {
    "reply_type": "service_choice",
    "expected_reply": True,
    "meta_any": {
        "expected_reply_type": ["service_choice"],
    },
    "trace_contains": [
        {
            "stage": "question_contract",
            "expected_reply_type": "service_choice",
        }
    ],
}
_BOOKING_SCENARIO_RESCHEDULE_FOLLOWUP_EXPECT_OVERRIDE = {
    "action": "handoff",
    "state": "pending",
    "expected_reply": True,
}
_BOOKING_SCENARIO_CHECK_BOOKING_FOLLOWUP_EXPECT_OVERRIDE = {
    "expected_reply": True,
}
_BOOKING_SCENARIO_TIME_COLLECT_EXPECT_OVERRIDE = {
    "reply_type": "time",
    "expected_reply": True,
    "meta_any": {
        "expected_reply_type": ["time"],
    },
    "trace_contains": [
        {
            "stage": "question_contract",
            "expected_reply_type": "time",
        }
    ],
}


def normalize_expect_token(token: str | None) -> str | None:
    if token is None:
        return None
    value = token.strip()
    if not value:
        return None
    lowered = value.lower()
    if lowered in {"none", "null"}:
        return None
    return value


def normalize_expect_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        parts = [item.strip() for item in value.split(",") if item.strip()]
        if not parts:
            return None
        if len(parts) == 1:
            return normalize_expect_token(parts[0])
        return [normalize_expect_token(item) for item in parts]
    if isinstance(value, list):
        normalized = []
        for item in value:
            token = normalize_expect_token(str(item))
            if token is None and str(item).strip().lower() not in {"none", "null"}:
                continue
            normalized.append(token)
        return normalized or None
    return value


def collect_turn_tags(turn: Mapping[str, Any] | None) -> set[str]:
    if not isinstance(turn, Mapping):
        return set()
    raw_tags = turn.get("tags")
    if not isinstance(raw_tags, list):
        return set()
    return {
        str(tag).strip().lower()
        for tag in raw_tags
        if isinstance(tag, str) and str(tag).strip()
    }


def _normalize_lower_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = normalize_expect_token(value)
    return normalized.lower() if isinstance(normalized, str) else ""


def _payload_pending_question_contract(payload: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if not isinstance(payload, Mapping):
        return None
    candidate = payload.get("pending_question_contract")
    return candidate if isinstance(candidate, Mapping) else None


def _payload_expected_reply_kind(payload: Mapping[str, Any] | None) -> str:
    pending_question_contract = _payload_pending_question_contract(payload)
    if isinstance(pending_question_contract, Mapping):
        reply_kind = _normalize_lower_token(pending_question_contract.get("expected_reply_type"))
        if reply_kind:
            return reply_kind
    return _normalize_lower_token(payload.get("expected_reply_type") if isinstance(payload, Mapping) else None)


def _iter_booking_progress_payloads(
    meta: Mapping[str, Any] | None,
    trace_entries: list[Any] | None,
):
    if isinstance(meta, Mapping):
        yield meta
        llm_policy_meta = meta.get("llm_policy_core")
        if isinstance(llm_policy_meta, Mapping):
            yield llm_policy_meta
            payload = llm_policy_meta.get("payload")
            if isinstance(payload, Mapping):
                yield payload
    for entry in trace_entries or []:
        if isinstance(entry, Mapping):
            yield entry


def _collect_booking_progress_reply_kind(
    meta: Mapping[str, Any] | None,
    trace_entries: list[Any] | None,
) -> str:
    for payload in _iter_booking_progress_payloads(meta, trace_entries):
        token = _payload_expected_reply_kind(payload)
        if token in CHAOS_BOOKING_REPLY_TYPES:
            return token
    return ""


def _has_booking_progress_pending_question_contract(
    meta: Mapping[str, Any] | None,
    trace_entries: list[Any] | None,
    reply_kind: str,
) -> bool:
    if reply_kind not in CHAOS_BOOKING_REPLY_TYPES:
        return False
    saw_act = False
    saw_reply_kind = False
    for payload in _iter_booking_progress_payloads(meta, trace_entries):
        for key in ("pending_question_act", "dialog_act", "pending_question_interaction"):
            if _normalize_lower_token(payload.get(key)) in _PENDING_QUESTION_TAGS:
                saw_act = True
                break
        if _payload_expected_reply_kind(payload) == reply_kind:
            saw_reply_kind = True
    return saw_act and saw_reply_kind


def build_booking_progress_info_inference_context(
    *,
    turn_tags,
    meta: Mapping[str, Any] | None,
    trace_entries: list[Any] | None,
) -> dict[str, Any]:
    normalized_tags = {
        str(tag).strip().lower()
        for tag in (turn_tags or [])
        if isinstance(tag, str) and str(tag).strip()
    }
    reply_kind = _collect_booking_progress_reply_kind(meta, trace_entries)
    booking_contract = _has_booking_progress_pending_question_contract(
        meta,
        trace_entries,
        reply_kind,
    )
    info_like = bool(
        normalized_tags.intersection(LLM_QUALITY_INFO_TAGS) or "consult" in normalized_tags
    )
    progress_tags = _BOOKING_PROGRESS_TAGS_BY_REPLY_KIND.get(reply_kind, set())
    allowed_tags = progress_tags | _BOOKING_PROGRESS_SKIP_TAGS
    progress_only = bool(
        normalized_tags
        and normalized_tags.intersection(progress_tags)
        and normalized_tags <= allowed_tags
    )
    return {
        "reply_kind": reply_kind,
        "booking_contract": booking_contract,
        "info_like": info_like,
        "progress_only": progress_only,
    }


def extract_booking_prompt_kind(context: Mapping[str, Any] | None) -> str:
    if not isinstance(context, Mapping):
        return ""
    reply_kind = _payload_expected_reply_kind(context)
    if reply_kind in CHAOS_BOOKING_REPLY_TYPES:
        return reply_kind
    return ""


def has_active_booking_context(context: Mapping[str, Any] | None) -> bool:
    if extract_booking_prompt_kind(context) in CHAOS_BOOKING_REPLY_TYPES:
        return True
    booking = context.get("booking") if isinstance(context, Mapping) else None
    return isinstance(booking, Mapping) and booking.get("active") is True


def _collect_resume_contract_reply_kind(
    *,
    meta: Mapping[str, Any] | None,
    trace_entries: list[Any] | None,
    expected_meta_contains: Mapping[str, Any] | None,
    expected_trace_contains: list[Any] | None,
) -> str:
    candidates = [
        _payload_expected_reply_kind(meta),
    ]
    if isinstance(expected_meta_contains, Mapping):
        candidates.append(_payload_expected_reply_kind(expected_meta_contains))
    if isinstance(expected_trace_contains, list):
        for item in expected_trace_contains:
            if not isinstance(item, Mapping):
                continue
            if item.get("stage") != "question_contract":
                continue
            candidates.append(_payload_expected_reply_kind(item))
    candidates.append(_collect_booking_progress_reply_kind(meta, trace_entries))
    for candidate in candidates:
        if isinstance(candidate, list):
            values = candidate
        else:
            values = [candidate]
        for value in values:
            token = _normalize_lower_token(value)
            if token in CHAOS_BOOKING_REPLY_TYPES:
                return token
    return ""


def _trace_has_session_memory_question_set(
    trace_entries: list[Any] | None,
    *,
    reply_kind: str,
) -> bool:
    if reply_kind not in CHAOS_BOOKING_REPLY_TYPES:
        return False
    for entry in trace_entries or []:
        if not isinstance(entry, Mapping):
            continue
        if _normalize_lower_token(entry.get("stage")) != "session_memory":
            continue
        if _normalize_lower_token(entry.get("decision")) != "update":
            continue
        entry_reply_kind = _payload_expected_reply_kind(entry) or _normalize_lower_token(
            entry.get("last_question_type")
        )
        if entry_reply_kind != reply_kind:
            continue
        owner = str(entry.get("interaction_owner") or "").strip()
        if owner.startswith("question_contract:"):
            return True
    return False


def _trace_has_service_clarify_question_contract(trace_entries: list[Any] | None) -> bool:
    for entry in trace_entries or []:
        if not isinstance(entry, Mapping):
            continue
        if _normalize_lower_token(entry.get("stage")) != "question_contract":
            continue
        if _normalize_lower_token(entry.get("missing_slot")) == "service":
            return True
    return False


def _has_catalog_service_answer_sidecar_fallback(
    *,
    meta: Mapping[str, Any] | None,
    trace_entries: list[Any] | None,
    expected_info_sections,
    expected_section_answered: Callable[..., Any] | None = None,
) -> bool:
    if not isinstance(meta, Mapping):
        return False
    if _normalize_lower_token(meta.get("intent")) != "catalog.service_query":
        return False
    tool_decision_value = _normalize_lower_token(meta.get("tool_decision"))
    if tool_decision_value not in {"duration", "truth_fallback"}:
        return False
    if callable(expected_section_answered):
        answered, _, _ = expected_section_answered(
            expected_info_sections,
            meta,
            trace_entries,
        )
        return bool(answered)
    expected_tokens = {
        str(section).strip().lower()
        for section in expected_info_sections or []
        if isinstance(section, str) and str(section).strip()
    }
    actual_tokens = {
        str(section).strip().lower()
        for section in (meta.get("info_sections") or [])
        if isinstance(section, str) and str(section).strip()
    }
    intent_token = _normalize_lower_token(meta.get("intent"))
    if intent_token:
        actual_tokens.add(intent_token)
    return bool(expected_tokens & actual_tokens)


def has_resume_meta_trace_allowance(
    *,
    meta: Mapping[str, Any] | None,
    trace_entries: list[Any] | None,
    expected_info_sections,
    expected_meta_contains: Mapping[str, Any] | None,
    expected_trace_contains: list[Any] | None,
    expected_section_answered: Callable[..., Any] | None = None,
) -> bool:
    reply_kind = _collect_resume_contract_reply_kind(
        meta=meta,
        trace_entries=trace_entries,
        expected_meta_contains=expected_meta_contains,
        expected_trace_contains=expected_trace_contains,
    )
    if reply_kind in CHAOS_BOOKING_REPLY_TYPES:
        expected_trace_items = expected_trace_contains or []
        if any(
            isinstance(item, Mapping)
            and _normalize_lower_token(item.get("stage")) == "question_contract"
            and _payload_expected_reply_kind(item) == reply_kind
            for item in expected_trace_items
        ):
            return True
        if any(
            isinstance(entry, Mapping)
            and _normalize_lower_token(entry.get("stage")) == "question_contract"
            and _payload_expected_reply_kind(entry) == reply_kind
            for entry in trace_entries or []
        ):
            return True
        if _trace_has_session_memory_question_set(trace_entries, reply_kind=reply_kind):
            return True
    if (
        reply_kind == "service_choice"
        and _trace_has_service_clarify_question_contract(trace_entries)
    ):
        return True
    if expected_info_sections and _has_catalog_service_answer_sidecar_fallback(
        meta=meta,
        trace_entries=trace_entries,
        expected_info_sections=expected_info_sections,
        expected_section_answered=expected_section_answered,
    ):
        return True
    return False


def sanitize_expect_action_by_tags(tag_set: set[str], action: Any) -> Any:
    if action is None:
        return None
    allow_handoff = bool(tag_set & LLM_QUALITY_EXPECT_TAGS_ALLOW_PENDING)

    def _allow(token: Any) -> bool:
        normalized = normalize_expect_token(token)
        if normalized is None:
            return True
        lowered = normalized.lower()
        if lowered in LLM_QUALITY_EXPECT_ACTION_HANDOFF:
            return allow_handoff
        return True

    if isinstance(action, list):
        cleaned = []
        for token in action:
            value = normalize_expect_token(str(token))
            if _allow(value):
                cleaned.append(value)
        cleaned = [token for token in cleaned if token]
        if not cleaned:
            return None
        if len(cleaned) == 1:
            return cleaned[0]
        return cleaned

    token = normalize_expect_token(str(action))
    if not _allow(token):
        return None
    return token


def sanitize_expect_state_by_tags(tag_set: set[str], state: Any) -> Any:
    if state is None:
        return None
    allow_pending = bool(tag_set & LLM_QUALITY_EXPECT_TAGS_ALLOW_PENDING)
    allow_manager_active = bool(tag_set & LLM_QUALITY_EXPECT_TAGS_ALLOW_MANAGER_ACTIVE)

    def _allow(token: Any) -> bool:
        normalized = normalize_expect_token(token)
        if normalized is None:
            return True
        lowered = normalized.lower()
        if lowered == "bot_active":
            return True
        if lowered == "pending":
            return allow_pending
        if lowered == "manager_active":
            return allow_manager_active
        return False

    if isinstance(state, list):
        cleaned = []
        for token in state:
            value = normalize_expect_token(str(token))
            if _allow(value):
                cleaned.append(value)
        cleaned = [token for token in cleaned if token]
        if not cleaned:
            return None
        if len(cleaned) == 1:
            return cleaned[0]
        return cleaned

    token = normalize_expect_token(str(state))
    if not _allow(token):
        return None
    return token


def sanitize_expect_info_sections_by_tags(tag_set: set[str], info_sections: list[str]) -> list[str]:
    if not info_sections:
        return []
    if tag_set & LLM_QUALITY_EXPECT_INFO_TAGS:
        return info_sections
    return []


def normalize_expect_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, Any] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        key = raw_key.strip()
        if isinstance(raw_value, (str, int, float, bool)) or raw_value is None:
            normalized[key] = raw_value
            continue
        if isinstance(raw_value, list):
            cleaned = [
                item
                for item in raw_value
                if isinstance(item, (str, int, float, bool)) or item is None
            ]
            if cleaned:
                normalized[key] = cleaned
    return normalized


def normalize_expect_contains_mapping(value: Any) -> dict[str, list[Any]]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, list[Any]] = {}
    for raw_key, raw_value in value.items():
        if not isinstance(raw_key, str) or not raw_key.strip():
            continue
        key = raw_key.strip()
        values = raw_value if isinstance(raw_value, list) else [raw_value]
        cleaned = [
            item
            for item in values
            if isinstance(item, (str, int, float, bool)) or item is None
        ]
        if cleaned:
            normalized[key] = cleaned
    return normalized


def normalize_expect_trace_contains(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in value:
        mapping = normalize_expect_mapping(item)
        if mapping:
            normalized.append(mapping)
    return normalized


def is_weak_oracle_expectation(expectations: dict[str, Any] | None) -> bool:
    if not isinstance(expectations, dict):
        return True
    has_action = bool(expectations.get("action"))
    has_info_sections = bool(expectations.get("info_sections"))
    has_reply_type = bool(expectations.get("reply_type"))
    has_state = bool(expectations.get("state"))
    has_meta = bool(expectations.get("meta"))
    has_meta_any = bool(expectations.get("meta_any"))
    has_meta_contains = bool(expectations.get("meta_contains"))
    has_trace = bool(expectations.get("trace_contains"))
    return not (
        has_action
        or has_info_sections
        or has_reply_type
        or has_state
        or has_meta
        or has_meta_any
        or has_meta_contains
        or has_trace
    )


def _apply_service_choice_booking_collect_expectations(
    expect: dict[str, Any],
    *,
    tags: set[str],
) -> dict[str, Any]:
    if "booking" not in tags:
        return expect
    if tags & {"handoff", "human", "pending", "cancel", "reschedule", "check_booking", "confirm"}:
        return expect
    if _normalize_lower_token(expect.get("reply_type")) != "service_choice":
        return expect
    if _normalize_lower_token(expect.get("state")) in {"pending", "manager_active"}:
        return expect

    multi_service_clarify = booking_scenario_expectation_has_contract_reason(
        expect,
        "multi_service_booking_clarify",
    )

    expect["action"] = "booking_prompt"
    expect["expected_reply"] = True

    collect_reason = "collect:service"

    meta = deepcopy(dict(expect.get("meta") or {}))
    meta["action"] = "booking_prompt"
    meta["source"] = "llm_policy_core"
    meta["tool_action"] = "collect"
    meta["expected_reply_type"] = "service_choice"
    if not multi_service_clarify:
        meta["expected_reply_reason"] = collect_reason
    if meta:
        expect["meta"] = meta

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any["action"] = ["booking_prompt"]
    meta_any["source"] = ["llm_policy_core"]
    meta_any["tool_action"] = ["collect"]
    meta_any["expected_reply_type"] = ["service_choice"]
    if not multi_service_clarify:
        meta_any["expected_reply_reason"] = [collect_reason]
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in deepcopy(list(expect.get("trace_contains") or [])):
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = "service_choice"
            if not multi_service_clarify:
                normalized_entry["reason"] = collect_reason
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "service_choice",
    }
    if not multi_service_clarify:
        question_contract_trace["reason"] = collect_reason
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def extract_expectations(turn: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(turn, Mapping):
        return {}
    expect = turn.get("expect")
    if not isinstance(expect, Mapping):
        return {}

    action = expect.get("action")
    if isinstance(action, str):
        action = [item.strip() for item in action.split(",") if item.strip()]
    elif isinstance(action, list):
        action = [str(item).strip() for item in action if str(item).strip()]
    else:
        action = None

    info_sections = expect.get("info_sections")
    if isinstance(info_sections, str):
        info_sections = [item.strip() for item in info_sections.split(",") if item.strip()]
    elif isinstance(info_sections, list):
        info_sections = [str(item).strip() for item in info_sections if str(item).strip()]
    else:
        info_sections = []

    reply_type = normalize_expect_value(expect.get("reply_type"))
    state = normalize_expect_value(expect.get("state"))
    tag_set = collect_turn_tags(turn)
    if reply_type in CHAOS_BOOKING_REPLY_TYPES and "consult" in tag_set:
        reply_type = None

    action = sanitize_expect_action_by_tags(tag_set, action)
    state = sanitize_expect_state_by_tags(tag_set, state)
    if state is not None:
        allow_pending = bool(tag_set & LLM_QUALITY_EXPECT_TAGS_ALLOW_PENDING)
        allow_manager_active = bool(tag_set & LLM_QUALITY_EXPECT_TAGS_ALLOW_MANAGER_ACTIVE)
        state_values = list(state) if isinstance(state, (list, tuple, set)) else [state]
        normalized_states = []
        for value in state_values:
            if not isinstance(value, str):
                continue
            token = value.strip().lower()
            if token:
                normalized_states.append(token)
        if "bot_active" in normalized_states:
            if allow_pending and "pending" not in normalized_states:
                normalized_states.append("pending")
            if allow_manager_active and "manager_active" not in normalized_states:
                normalized_states.append("manager_active")
        if normalized_states:
            state = normalized_states[0] if len(normalized_states) == 1 else normalized_states
        else:
            state = None

    info_sections = sanitize_expect_info_sections_by_tags(tag_set, info_sections)

    expected_reply = expect.get("expected_reply")
    if isinstance(expected_reply, str):
        lowered = expected_reply.strip().lower()
        if lowered in {"true", "yes", "1"}:
            expected_reply = True
        elif lowered in {"false", "no", "0"}:
            expected_reply = False
        else:
            expected_reply = None
    if not isinstance(expected_reply, bool):
        expected_reply = None
    if "media" in tag_set:
        expected_reply = None

    allow_booking_stall = expect.get("allow_booking_stall")
    if isinstance(allow_booking_stall, str):
        token = allow_booking_stall.strip().lower()
        if token in {"true", "yes", "1"}:
            allow_booking_stall = True
        elif token in {"false", "no", "0"}:
            allow_booking_stall = False
        else:
            allow_booking_stall = None
    if not isinstance(allow_booking_stall, bool):
        allow_booking_stall = False

    normalized = {
        "action": action,
        "info_sections": [section.lower() for section in info_sections],
        "reply_type": reply_type or None,
        "state": state or None,
        "expected_reply": expected_reply,
        "allow_booking_stall": allow_booking_stall,
        "meta": normalize_expect_mapping(expect.get("meta")),
        "meta_any": normalize_expect_contains_mapping(expect.get("meta_any")),
        "meta_contains": normalize_expect_contains_mapping(expect.get("meta_contains")),
        "trace_contains": normalize_expect_trace_contains(expect.get("trace_contains")),
    }
    if should_compile_active_time_specialist_followup_expectations(normalized):
        compiled = compile_active_time_specialist_followup_expectations(normalized)
        if isinstance(compiled, dict):
            normalized = compiled
    normalized = _apply_service_choice_booking_collect_expectations(
        normalized,
        tags=tag_set,
    )
    return normalized


def parse_coverage_tokens(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        raw_tokens = [item.strip().casefold() for item in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        raw_tokens = [str(item).strip().casefold() for item in value]
    else:
        raw_tokens = [str(value).strip().casefold()]
    return {token for token in raw_tokens if token and token not in {"none", "off"}}


def build_scenario_contract_status(
    *,
    dialogs: Any,
    scenario_coverage: Any,
    allow_weak_oracle: bool = False,
    requested_count: int | None = None,
    include_media: bool = False,
    acceptance_contract: bool = False,
) -> dict[str, Any]:
    def _normalized_reply_type(expectations: dict[str, Any]) -> str | None:
        value = str((expectations or {}).get("reply_type") or "").strip().casefold()
        return value or None

    coverage_tokens = parse_coverage_tokens(scenario_coverage)
    required_tags_by_coverage = {
        "booking": ("booking", "check_booking", "confirm"),
        "handoff": ("handoff",),
    }
    tag_counts: dict[str, int] = {}
    dialogs_with_check_confirm_sequence = 0
    dialog_count = 0
    turn_count = 0
    weak_expectation_turns = 0
    reply_type_coverage_turns = 0
    action_coverage_turns = 0
    info_coverage_turns = 0
    reasons: list[str] = []

    for dialog in dialogs or []:
        if not isinstance(dialog, Mapping):
            continue
        turns = dialog.get("turns")
        if not isinstance(turns, list):
            continue
        dialog_count += 1
        active_reply_type = None
        first_check_booking = None
        first_confirm_after_check = None
        for idx, turn in enumerate(turns):
            if not isinstance(turn, Mapping):
                continue
            turn_count += 1
            expectations = extract_expectations(turn)
            if is_weak_oracle_expectation(expectations):
                weak_expectation_turns += 1
            if expectations.get("reply_type"):
                reply_type_coverage_turns += 1
            if expectations.get("action"):
                action_coverage_turns += 1
            if expectations.get("info_sections"):
                info_coverage_turns += 1
            raw_tags = turn.get("tags")
            if not isinstance(raw_tags, list):
                continue
            tags: list[str] = []
            for item in raw_tags:
                if not isinstance(item, str):
                    continue
                token = item.strip().casefold()
                if not token:
                    continue
                tags.append(token)
                tag_counts[token] = tag_counts.get(token, 0) + 1
            if "check_booking" in tags and first_check_booking is None:
                first_check_booking = idx
            if (
                "confirm" in tags
                and first_check_booking is not None
                and idx > first_check_booking
                and first_confirm_after_check is None
            ):
                first_confirm_after_check = idx
            if any(tag in _PENDING_QUESTION_TAGS for tag in tags) and active_reply_type != "time":
                reasons.append(f"orphan_pending_question_turn:d{dialog_count}:t{idx + 1}")
            reply_type = _normalized_reply_type(expectations)
            if reply_type:
                active_reply_type = reply_type
            elif any(tag in _PENDING_QUESTION_CONTEXT_PRESERVE_TAGS for tag in tags):
                pass
            else:
                active_reply_type = None
        if first_check_booking is not None and first_confirm_after_check is not None:
            dialogs_with_check_confirm_sequence += 1

    for coverage_token, required_tags in required_tags_by_coverage.items():
        if coverage_token not in coverage_tokens:
            continue
        for tag in required_tags:
            if tag_counts.get(tag, 0) <= 0:
                reasons.append(f"missing_tag:{tag}")

    if weak_expectation_turns > 0 and not allow_weak_oracle:
        reasons.append("weak_oracle_turn")
    if acceptance_contract:
        min_dialog_count = 10
        if isinstance(requested_count, int) and requested_count < min_dialog_count:
            reasons.append("acceptance_count_lt_10")
        if dialog_count < min_dialog_count:
            reasons.append("acceptance_dialogs_lt_10")
        if not include_media:
            reasons.append("acceptance_include_media_required")
        for token in ("booking", "info", "interrupt", "handoff"):
            if token not in coverage_tokens:
                reasons.append(f"acceptance_missing_coverage:{token}")
        if tag_counts.get("handoff", 0) <= 0:
            reasons.append("acceptance_handoff_tag_missing")
        if include_media and tag_counts.get("media", 0) <= 0:
            reasons.append("acceptance_media_tag_missing")

    weak_expectation_ratio = round(weak_expectation_turns / max(turn_count, 1), 4) if turn_count else 0.0
    reply_type_coverage_ratio = round(reply_type_coverage_turns / max(turn_count, 1), 4) if turn_count else 0.0
    action_coverage_ratio = round(action_coverage_turns / max(turn_count, 1), 4) if turn_count else 0.0
    info_coverage_ratio = round(info_coverage_turns / max(turn_count, 1), 4) if turn_count else 0.0

    return {
        "valid": not reasons,
        "reasons": reasons,
        "coverage_tokens": sorted(coverage_tokens),
        "tag_counts": tag_counts,
        "dialog_count": dialog_count,
        "dialogs_with_check_confirm_sequence": dialogs_with_check_confirm_sequence,
        "turn_count": turn_count,
        "weak_expectation_turns": weak_expectation_turns,
        "weak_expectation_ratio": weak_expectation_ratio,
        "reply_type_coverage": reply_type_coverage_ratio,
        "action_coverage": action_coverage_ratio,
        "info_coverage": info_coverage_ratio,
        "allow_weak_oracle": bool(allow_weak_oracle),
    }


def _normalize_booking_scenario_expected_reply(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            return True
        if lowered in {"false", "no", "0"}:
            return False
    return None


def _default_booking_scenario_expect() -> dict[str, Any]:
    return {
        "action": None,
        "info_sections": [],
        "reply_type": None,
        "state": "bot_active",
        "expected_reply": None,
        "allow_booking_stall": False,
    }


def normalize_booking_scenario_expect_override(override: Any) -> dict[str, Any]:
    if not isinstance(override, Mapping):
        return {}
    action = normalize_expect_value(
        override.get("action"),
    )
    if isinstance(action, list):
        action = [
            token
            for token in action
            if isinstance(token, str)
            and token.lower() in BOOKING_SCENARIO_CANONICAL_EXPECT_ACTIONS
        ] or None
        if isinstance(action, list) and len(action) == 1:
            action = action[0]
    elif isinstance(action, str) and action.lower() not in BOOKING_SCENARIO_CANONICAL_EXPECT_ACTIONS:
        action = None

    info_sections = normalize_expect_value(override.get("info_sections"))
    if isinstance(info_sections, str):
        info_sections = [info_sections]
    if isinstance(info_sections, list):
        info_sections = [
            token
            for token in info_sections
            if isinstance(token, str)
            and token.lower() in BOOKING_SCENARIO_CANONICAL_EXPECT_INFO_SECTIONS
        ]

    reply_type = normalize_expect_value(override.get("reply_type"))
    if isinstance(reply_type, str) and reply_type.lower() not in BOOKING_SCENARIO_CANONICAL_EXPECT_REPLY_TYPES:
        reply_type = None
    if isinstance(reply_type, list):
        reply_type = [
            token
            for token in reply_type
            if isinstance(token, str)
            and token.lower() in BOOKING_SCENARIO_CANONICAL_EXPECT_REPLY_TYPES
        ] or None
        if isinstance(reply_type, list) and len(reply_type) == 1:
            reply_type = reply_type[0]

    state = normalize_expect_value(override.get("state"))
    if isinstance(state, str) and state.lower() not in BOOKING_SCENARIO_CANONICAL_EXPECT_STATES:
        state = None
    if isinstance(state, list):
        state = [
            token
            for token in state
            if isinstance(token, str)
            and token.lower() in BOOKING_SCENARIO_CANONICAL_EXPECT_STATES
        ] or None
        if isinstance(state, list) and len(state) == 1:
            state = state[0]

    return {
        "action": action,
        "info_sections": info_sections,
        "reply_type": reply_type,
        "state": state,
        "expected_reply": _normalize_booking_scenario_expected_reply(
            override.get("expected_reply")
        ),
        "meta": normalize_expect_mapping(override.get("meta")),
        "meta_any": normalize_expect_contains_mapping(override.get("meta_any")),
        "meta_contains": normalize_expect_contains_mapping(override.get("meta_contains")),
        "trace_contains": normalize_expect_trace_contains(override.get("trace_contains")),
    }


def sanitize_booking_scenario_expect_state_by_tags(tags: list[str], state: Any) -> Any:
    if state is None:
        return None
    tag_set = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    allow_pending = bool(tag_set & {"handoff", "human", "pending", "cancel", "reschedule"})
    allow_manager_active = bool(tag_set & {"handoff", "human", "pending"})

    def _allow(token: str | None) -> bool:
        if token is None:
            return True
        if token == "bot_active":
            return True
        if token == "pending":
            return allow_pending
        if token == "manager_active":
            return allow_manager_active
        return False

    if isinstance(state, list):
        cleaned: list[str | None] = []
        for token in state:
            value = token if isinstance(token, str) else None
            if _allow(value):
                cleaned.append(value)
        cleaned = [token for token in cleaned if token is not None]
        if not cleaned:
            return None
        if len(cleaned) == 1:
            return cleaned[0]
        return cleaned

    token = state if isinstance(state, str) else None
    return token if _allow(token) else None


def sanitize_booking_scenario_expect_action_by_tags(tags: list[str], action: Any) -> Any:
    if action is None:
        return None
    tag_set = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    allow_handoff = bool(tag_set & {"handoff", "human", "pending", "cancel", "reschedule"})

    def _allow(token: str | None) -> bool:
        if token is None:
            return True
        if token == "booking_prompt":
            return True
        if token in BOOKING_SCENARIO_CANONICAL_EXPECT_ACTIONS:
            return allow_handoff
        return False

    if isinstance(action, list):
        cleaned: list[str | None] = []
        for token in action:
            value = token if isinstance(token, str) else None
            if _allow(value):
                cleaned.append(value)
        cleaned = [token for token in cleaned if token is not None]
        if not cleaned:
            return None
        if len(cleaned) == 1:
            return cleaned[0]
        return cleaned

    token = action if isinstance(action, str) else None
    return token if _allow(token) else None


def sanitize_booking_scenario_expect_override_for_tags(
    override: Any,
    *,
    tags: list[str],
) -> Any:
    if not isinstance(override, Mapping):
        return override
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if "mixed_fill_plus_question" not in lowered_tags:
        return dict(override)

    cleaned = normalize_booking_scenario_expect_override(override)
    cleaned.pop("reply_type", None)
    for key in ("meta", "meta_any", "meta_contains"):
        mapping = cleaned.get(key)
        if not isinstance(mapping, dict):
            continue
        normalized_mapping = dict(mapping)
        normalized_mapping.pop("pending_question_act", None)
        normalized_mapping.pop("pending_question_target", None)
        normalized_mapping.pop("pending_question_interaction", None)
        normalized_mapping.pop("pending_question_owner", None)
        normalized_mapping.pop("active_question_relation", None)
        normalized_mapping.pop("expected_reply_type", None)
        if normalized_mapping:
            cleaned[key] = normalized_mapping
        else:
            cleaned.pop(key, None)

    trace_contains = [
        dict(entry)
        for entry in (cleaned.get("trace_contains") or [])
        if entry.get("stage") not in {"pending_question_interaction", "question_contract"}
    ]
    if trace_contains:
        cleaned["trace_contains"] = trace_contains
    else:
        cleaned.pop("trace_contains", None)
    return cleaned


def looks_like_booking_scenario_specialist_reference(text: str | None) -> bool:
    if not text:
        return False
    return any(pattern.search(text) for pattern in _BOOKING_SCENARIO_SPECIALIST_REFERENCE_PATTERNS)


def _booking_scenario_looks_like_assistant_turn(text: str | None) -> bool:
    if not text:
        return False
    normalized = text.strip()
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in _BOOKING_SCENARIO_ASSISTANT_TURN_PATTERNS)


def _booking_scenario_fallback_text_for_tags(tags: list[str], ctx: dict[str, str]) -> str:
    for tag in _BOOKING_SCENARIO_FALLBACK_TAG_PRIORITY:
        if tag in tags:
            template = _BOOKING_SCENARIO_FALLBACK_TEMPLATES_BY_TAG.get(tag)
            if template:
                return template.format(**ctx)
    return f"{ctx.get('greet', 'Здравствуйте')}, хочу записаться на {ctx.get('service', 'услугу')}."


def _booking_scenario_text_matches_tag_contract(text: str, tags: list[str]) -> bool:
    if not text:
        return False
    lowered_tags = _booking_scenario_coerce_turn_tags(tags)
    if "master" in lowered_tags:
        return looks_like_booking_scenario_specialist_reference(text)
    return True


def booking_scenario_looks_like_generic_master_info_question(text: str | None) -> bool:
    if not text:
        return False
    return any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_GENERIC_MASTER_INFO_QUESTION_PATTERNS
    )


def booking_scenario_looks_like_specialist_availability_followup_question(
    text: str | None,
) -> bool:
    if not text:
        return False
    if not booking_scenario_looks_like_generic_master_info_question(text):
        return False
    if not any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_AVAILABILITY_QUERY_PATTERNS
    ):
        return False
    return any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_PARTIAL_DATE_FILL_PATTERNS
    )


def booking_scenario_looks_like_standalone_specialist_booking_request(
    text: str | None,
) -> bool:
    if not text:
        return False
    if booking_scenario_looks_like_generic_master_info_question(text):
        return False
    if not looks_like_booking_scenario_specialist_reference(text):
        return False
    return any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_STANDALONE_SPECIALIST_BOOKING_REQUEST_PATTERNS
    )


def booking_scenario_looks_like_named_specialist_preference_availability_question(
    text: str | None,
) -> bool:
    if not text:
        return False
    if not any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_SPECIALIST_PREFERENCE_NAME_PATTERNS
    ):
        return False
    return any(
        pattern.search(text)
        for pattern in (
            _BOOKING_SCENARIO_AVAILABILITY_QUERY_PATTERNS
            + _BOOKING_SCENARIO_TIME_OCCUPANCY_QUERY_PATTERNS
        )
    )


def booking_scenario_looks_like_grounded_time_specialist_availability_transition_question(
    text: str | None,
) -> bool:
    if not text:
        return False
    if not booking_scenario_looks_like_generic_master_info_question(text):
        return False
    if not any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_AVAILABILITY_QUERY_PATTERNS
    ):
        return False
    return not any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_PARTIAL_DATE_FILL_PATTERNS
    )


def booking_scenario_looks_like_mixed_slot_question(text: str | None) -> bool:
    if not text:
        return False
    if not any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_MIXED_SLOT_CONSTRAINT_PATTERNS
    ):
        return False
    return any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_MIXED_SLOT_QUESTION_PATTERNS
    )


def booking_scenario_looks_like_explicit_time_fill(text: str | None) -> bool:
    if not text:
        return False
    return any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_EXPLICIT_TIME_FILL_PATTERNS
    )


def booking_scenario_looks_like_ambiguous_time_fill(text: str | None) -> bool:
    if not text or not booking_scenario_looks_like_explicit_time_fill(text):
        return False
    return any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_AMBIGUOUS_TIME_FILL_PATTERNS
    )


def booking_scenario_looks_like_question_like_slot_constraint(text: str | None) -> bool:
    if not text:
        return False
    if booking_scenario_looks_like_explicit_time_fill(text):
        return False
    if not any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_MIXED_SLOT_CONSTRAINT_PATTERNS
    ):
        return False
    lowered = text.strip().lower()
    return "?" in text or lowered.startswith(("можно", "а можно", "могу", "может"))


def booking_scenario_looks_like_requested_slot_question_without_temporal_scope(
    text: str | None,
) -> bool:
    if not text:
        return False
    if booking_scenario_looks_like_explicit_time_fill(text):
        return False
    if booking_scenario_looks_like_mixed_slot_question(text):
        return False
    if any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_PARTIAL_DATE_FILL_PATTERNS
    ):
        return False
    if booking_scenario_looks_like_generic_master_info_question(text):
        return False
    return any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_REQUESTED_SLOT_QUESTION_PATTERNS
    )


def booking_scenario_looks_like_non_comparative_availability_question(
    text: str | None,
) -> bool:
    if booking_scenario_looks_like_requested_slot_question_without_temporal_scope(text):
        return True
    if not text:
        return False
    if booking_scenario_looks_like_explicit_time_fill(text):
        return False
    if booking_scenario_looks_like_mixed_slot_question(text):
        return False
    if any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_PARTIAL_DATE_FILL_PATTERNS
    ):
        return False
    if booking_scenario_looks_like_generic_master_info_question(text):
        return False
    return any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_AVAILABILITY_QUERY_PATTERNS
    )


def booking_scenario_looks_like_partial_date_fill_without_availability_query(
    text: str | None,
) -> bool:
    if not text:
        return False
    if booking_scenario_looks_like_explicit_time_fill(text):
        return False
    if not any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_PARTIAL_DATE_FILL_PATTERNS
    ):
        return False
    return not any(
        pattern.search(text)
        for pattern in (
            _BOOKING_SCENARIO_AVAILABILITY_QUERY_PATTERNS
            + _BOOKING_SCENARIO_TIME_OCCUPANCY_QUERY_PATTERNS
        )
    )


def booking_scenario_looks_like_grounded_time_availability_probe(
    text: str | None,
) -> bool:
    if not text:
        return False
    if not (
        booking_scenario_looks_like_explicit_time_fill(text)
        or any(
            pattern.search(text)
            for pattern in _BOOKING_SCENARIO_DEICTIC_TIME_REFERENCE_PATTERNS
        )
        or any(
            pattern.search(text)
            for pattern in _BOOKING_SCENARIO_DEICTIC_DAY_REFERENCE_PATTERNS
        )
    ):
        return False
    return (
        any(
            pattern.search(text)
            for pattern in _BOOKING_SCENARIO_MIXED_SLOT_QUESTION_PATTERNS
        )
        or any(
            pattern.search(text)
            for pattern in _BOOKING_SCENARIO_AVAILABILITY_QUERY_PATTERNS
        )
        or any(
            pattern.search(text)
            for pattern in _BOOKING_SCENARIO_TIME_OCCUPANCY_QUERY_PATTERNS
        )
    )


def booking_scenario_looks_like_grounded_partial_date_daypart_fill(
    text: str | None,
) -> bool:
    if not text:
        return False
    if booking_scenario_looks_like_explicit_time_fill(text):
        return False
    if any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_PARTIAL_DATE_FILL_PATTERNS
    ):
        return False
    has_daypart_reference = bool(
        _BOOKING_SCENARIO_MIXED_SLOT_CONSTRAINT_PATTERNS
        and _BOOKING_SCENARIO_MIXED_SLOT_CONSTRAINT_PATTERNS[0].search(text)
    )
    if not has_daypart_reference:
        return False
    return any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_AVAILABILITY_QUERY_PATTERNS
    )


def _booking_scenario_matched_service_candidates(
    text: str | None,
    *,
    service_candidates: tuple[str, ...] | list[str] = (),
    ctx: Mapping[str, str] | None = None,
) -> list[str]:
    if not text:
        return []
    normalized = text.lower()
    candidates: list[str] = []
    if isinstance(ctx, Mapping):
        candidates.append(str(ctx.get("service") or ""))
    candidates.extend(str(candidate or "") for candidate in service_candidates)
    matches: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        token = str(candidate or "").strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        if token in normalized:
            matches.append(token)
    return matches


def booking_scenario_looks_like_multi_service_booking_request(
    text: str | None,
    *,
    service_candidates: tuple[str, ...] | list[str] = (),
    ctx: Mapping[str, str] | None = None,
) -> bool:
    matches = _booking_scenario_matched_service_candidates(
        text,
        service_candidates=service_candidates,
        ctx=ctx,
    )
    if len(matches) < 2:
        return False
    source_text = str(text or "")
    return any(
        pattern.search(source_text)
        for pattern in _BOOKING_SCENARIO_MULTI_SERVICE_CONNECTOR_PATTERNS
    )


def booking_scenario_looks_like_service_grounded_booking(
    text: str | None,
    *,
    service_candidates: tuple[str, ...] | list[str] = (),
    ctx: Mapping[str, str] | None = None,
) -> bool:
    if not text:
        return False
    if booking_scenario_looks_like_multi_service_booking_request(
        text,
        service_candidates=service_candidates,
        ctx=ctx,
    ):
        return False
    return bool(
        _booking_scenario_matched_service_candidates(
            text,
            service_candidates=service_candidates,
            ctx=ctx,
        )
    )


def booking_scenario_looks_like_partial_date_availability_slot_constraint(
    text: str | None,
) -> bool:
    if not text:
        return False
    if booking_scenario_looks_like_generic_master_info_question(text):
        return False
    if not any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_PARTIAL_DATE_FILL_PATTERNS
    ):
        return False
    if booking_scenario_looks_like_explicit_time_fill(text):
        return False
    if any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_AMBIGUOUS_TIME_FILL_PATTERNS
    ):
        return False
    lowered = f" {text.strip().lower()} "
    if " или " in lowered:
        return False
    has_availability_surface = any(
        pattern.search(text)
        for pattern in (
            _BOOKING_SCENARIO_AVAILABILITY_QUERY_PATTERNS
            + _BOOKING_SCENARIO_TIME_OCCUPANCY_QUERY_PATTERNS
        )
    )
    has_time_question_surface = booking_scenario_looks_like_mixed_slot_question(
        text
    ) and bool(re.search(r"\bврем\w*\b", text, re.IGNORECASE))
    return has_availability_surface or has_time_question_surface


def _booking_scenario_lowered_tags(tags: list[str]) -> set[str]:
    return {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }


def booking_scenario_looks_like_reschedule_followup(
    text: str | None,
    tags: list[str],
) -> bool:
    if not text:
        return False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if not (lowered_tags & (BOOKING_SCENARIO_PENDING_QUESTION_TAGS | {"booking", "time"})):
        return False
    has_reschedule_verb = any(
        pattern.search(text) for pattern in _BOOKING_SCENARIO_RESCHEDULE_VERB_PATTERNS
    )
    has_reschedule_object = any(
        pattern.search(text) for pattern in _BOOKING_SCENARIO_RESCHEDULE_OBJECT_PATTERNS
    )
    has_temporal_followup = bool(
        has_reschedule_object
        or booking_scenario_looks_like_partial_date_fill_without_availability_query(text)
        or booking_scenario_looks_like_explicit_time_fill(text)
        or booking_scenario_looks_like_mixed_slot_question(text)
        or booking_scenario_looks_like_question_like_slot_constraint(text)
    )
    if has_reschedule_verb and has_reschedule_object:
        return True
    if has_reschedule_verb:
        return has_temporal_followup
    return has_temporal_followup


def booking_scenario_looks_like_check_booking_followup(
    text: str | None,
    tags: list[str],
) -> bool:
    if not text:
        return False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "booking" not in lowered_tags:
        return False
    if lowered_tags & {"reschedule", "cancel", "confirm", "check_booking"}:
        return False
    return any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_CHECK_BOOKING_FOLLOWUP_PATTERNS
    )


def booking_scenario_looks_like_generic_booking_request(text: str | None) -> bool:
    if not text:
        return False
    if any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_CHECK_BOOKING_FOLLOWUP_PATTERNS
    ):
        return False
    if any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_RESCHEDULE_VERB_PATTERNS
    ):
        return False
    return any(
        pattern.search(text)
        for pattern in _BOOKING_SCENARIO_GENERIC_BOOKING_REQUEST_PATTERNS
    )


def booking_scenario_normalize_grounded_time_specialist_availability_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "slot_compare" not in lowered_tags:
        return tags, False
    if not booking_scenario_looks_like_grounded_time_specialist_availability_transition_question(
        text
    ):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "slot_compare":
            tag = "master"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "master" not in normalized:
        normalized.insert(0, "master")
    return normalized, replaced


def booking_scenario_normalize_pending_question_tags(
    text: str | None,
    tags: list[str],
) -> list[str]:
    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "ask_about_requested_slot" and booking_scenario_looks_like_mixed_slot_question(text):
            tag = "mixed_fill_plus_question"
            replaced = True
        elif tag == "ask_about_requested_slot" and booking_scenario_looks_like_generic_master_info_question(text):
            tag = "master"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "ask_about_requested_slot" in normalized:
        normalized = [tag for tag in normalized if tag != "ask_about_requested_slot"]
    return normalized


def booking_scenario_normalize_stateful_booking_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> list[str]:
    if active_reply_type != "time":
        return tags
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "booking" not in lowered_tags:
        return tags
    if not booking_scenario_looks_like_mixed_slot_question(text):
        return tags

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "booking":
            tag = "mixed_fill_plus_question"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "booking" in normalized:
        normalized = [tag for tag in normalized if tag != "booking"]
    return normalized


def booking_scenario_normalize_malformed_check_booking_tags(
    text: str | None,
    tags: list[str],
) -> tuple[list[str], bool]:
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "check_booking" not in lowered_tags:
        return tags, False
    if booking_scenario_looks_like_check_booking_followup(text, ["booking"]):
        return tags, False
    if not booking_scenario_looks_like_generic_booking_request(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "check_booking":
            tag = "booking"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "booking" not in normalized:
        normalized.insert(0, "booking")
    return normalized, replaced


def booking_scenario_normalize_active_name_master_info_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "name":
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "booking" not in lowered_tags:
        return tags, False
    if not booking_scenario_looks_like_generic_master_info_question(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "booking":
            tag = "master"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "master" not in normalized:
        normalized.insert(0, "master")
    return normalized, replaced


def booking_scenario_normalize_active_time_master_info_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "booking" not in lowered_tags:
        return tags, False
    if not booking_scenario_looks_like_generic_master_info_question(text):
        return tags, False
    if booking_scenario_looks_like_specialist_availability_followup_question(text):
        return tags, False
    if booking_scenario_looks_like_grounded_time_specialist_availability_transition_question(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "booking":
            tag = "master"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "master" not in normalized:
        normalized.insert(0, "master")
    return normalized, replaced


def booking_scenario_normalize_active_time_specialist_master_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type not in {None, "time", "name"}:
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if not ({"master", "slot_compare"} & lowered_tags):
        return tags, False
    if not looks_like_booking_scenario_specialist_reference(text or ""):
        return tags, False
    if active_reply_type is None and not booking_scenario_looks_like_standalone_specialist_booking_request(text):
        return tags, False
    if booking_scenario_looks_like_generic_master_info_question(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag in {"master", "slot_compare"}:
            tag = "booking"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "booking" not in normalized:
        normalized.insert(0, "booking")
    return normalized, replaced


def booking_scenario_normalize_active_time_booking_fill_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "booking" not in lowered_tags:
        return tags, False
    if booking_scenario_looks_like_mixed_slot_question(text):
        return tags, False
    if not booking_scenario_looks_like_explicit_time_fill(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "booking":
            tag = "time"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "time" not in normalized:
        normalized.insert(0, "time")
    return normalized, replaced


def booking_scenario_normalize_booking_requested_slot_question_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "booking" not in lowered_tags:
        return tags, False
    if not booking_scenario_looks_like_requested_slot_question_without_temporal_scope(
        text
    ):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "booking":
            tag = "ask_about_requested_slot"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "ask_about_requested_slot" not in normalized:
        normalized.insert(0, "ask_about_requested_slot")
    return normalized, replaced


def booking_scenario_normalize_slot_constraint_requested_slot_question_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "slot_constraint" not in lowered_tags:
        return tags, False
    if not booking_scenario_looks_like_requested_slot_question_without_temporal_scope(
        text
    ):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "slot_constraint":
            tag = "ask_about_requested_slot"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "ask_about_requested_slot" not in normalized:
        normalized.insert(0, "ask_about_requested_slot")
    return normalized, replaced


def booking_scenario_normalize_slot_compare_requested_slot_question_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "slot_compare" not in lowered_tags:
        return tags, False
    if not booking_scenario_looks_like_non_comparative_availability_question(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "slot_compare":
            tag = "ask_about_requested_slot"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "ask_about_requested_slot" not in normalized:
        normalized.insert(0, "ask_about_requested_slot")
    return normalized, replaced


def booking_scenario_normalize_slot_compare_partial_date_constraint_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "slot_compare" not in lowered_tags:
        return tags, False
    if not booking_scenario_looks_like_partial_date_availability_slot_constraint(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "slot_compare":
            tag = "slot_constraint"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "slot_constraint" not in normalized:
        normalized.insert(0, "slot_constraint")
    return normalized, replaced


def booking_scenario_normalize_slot_constraint_answer_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "slot_constraint" not in lowered_tags:
        return tags, False
    if booking_scenario_looks_like_mixed_slot_question(text):
        return tags, False
    if not booking_scenario_looks_like_explicit_time_fill(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "slot_constraint":
            tag = "time"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "slot_constraint" in normalized:
        normalized = [tag for tag in normalized if tag != "slot_constraint"]
    return normalized, replaced


def booking_scenario_normalize_partial_date_slot_constraint_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "slot_constraint" not in lowered_tags:
        return tags, False
    if booking_scenario_looks_like_mixed_slot_question(text):
        return tags, False
    if not booking_scenario_looks_like_partial_date_fill_without_availability_query(
        text
    ):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "slot_constraint":
            tag = "time"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "slot_constraint" in normalized:
        normalized = [tag for tag in normalized if tag != "slot_constraint"]
    return normalized, replaced


def booking_scenario_normalize_partial_date_mixed_question_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "mixed_fill_plus_question" not in lowered_tags:
        return tags, False
    if not booking_scenario_looks_like_partial_date_fill_without_availability_query(
        text
    ):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "mixed_fill_plus_question":
            tag = "booking"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "booking" not in normalized:
        normalized.insert(0, "booking")
    return normalized, replaced


def booking_scenario_normalize_grounded_time_probe_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "ask_about_requested_slot" not in lowered_tags:
        return tags, False
    if not booking_scenario_looks_like_explicit_time_fill(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "ask_about_requested_slot":
            tag = "time"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "time" not in normalized:
        normalized.insert(0, "time")
    return normalized, replaced


def booking_scenario_normalize_slot_compare_exact_time_fill_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "slot_compare" not in lowered_tags:
        return tags, False
    if not booking_scenario_looks_like_explicit_time_fill(text):
        return tags, False
    if booking_scenario_looks_like_ambiguous_time_fill(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "slot_compare":
            tag = "time"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "time" not in normalized:
        normalized.insert(0, "time")
    return normalized, replaced


def booking_scenario_normalize_grounded_partial_date_mixed_fill_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
    partial_date_anchor_active: bool,
) -> tuple[list[str], bool]:
    if active_reply_type != "time" or not partial_date_anchor_active:
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "mixed_fill_plus_question" not in lowered_tags:
        return tags, False
    if not booking_scenario_looks_like_grounded_partial_date_daypart_fill(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "mixed_fill_plus_question":
            tag = "time"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "time" not in normalized:
        normalized.insert(0, "time")
    return normalized, replaced


def booking_scenario_normalize_question_like_slot_constraint_tags(
    text: str | None,
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> tuple[list[str], bool]:
    if active_reply_type != "time":
        return tags, False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "ask_about_requested_slot" not in lowered_tags:
        return tags, False
    if not booking_scenario_looks_like_question_like_slot_constraint(text):
        return tags, False

    normalized: list[str] = []
    replaced = False
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag:
            continue
        if tag == "ask_about_requested_slot":
            tag = "slot_constraint"
            replaced = True
        if tag not in normalized:
            normalized.append(tag)
    if replaced and "slot_constraint" not in normalized:
        normalized.insert(0, "slot_constraint")
    return normalized, replaced


def infer_booking_scenario_pending_question_target(
    text: str | None,
    tags: list[str],
) -> str | None:
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if not (lowered_tags & BOOKING_SCENARIO_TARGETED_PENDING_QUESTION_TAGS):
        return None
    if "master" in lowered_tags or looks_like_booking_scenario_specialist_reference(text):
        return "specialist"
    return "time"


def apply_booking_scenario_pending_question_target_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
) -> dict[str, Any]:
    target = infer_booking_scenario_pending_question_target(text, tags)
    if not target:
        return expect

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any["pending_question_target"] = [target]
    trace_contains = deepcopy(list(expect.get("trace_contains") or []))

    if target == "specialist":
        info_sections = list(expect.get("info_sections") or [])
        for section in BOOKING_SCENARIO_EXPECT_INFO_SECTIONS["master"]:
            if section not in info_sections:
                info_sections.append(section)
        expect["info_sections"] = info_sections
        meta_any.pop("pending_question_act", None)
        meta_any["booking_interrupt_info"] = [True]
        meta_any["intent"] = ["master"]
        trace_contains = [
            entry
            for entry in trace_contains
            if entry.get("stage") != "pending_question_interaction"
        ]
        specialist_trace = {
            "stage": "booking_interrupt",
            "decision": "info_reply",
            "pending_question_target": "specialist",
            "booking_interrupt_info": True,
            "info_sections": ["master"],
        }
        if specialist_trace not in trace_contains:
            trace_contains.append(specialist_trace)

    expect["meta_any"] = meta_any
    expect["trace_contains"] = trace_contains
    return expect


def has_booking_scenario_orphan_pending_question_tags(
    tags: list[str],
    *,
    active_reply_type: str | None,
) -> bool:
    lowered_tags = {
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    }
    if not (lowered_tags & BOOKING_SCENARIO_PENDING_QUESTION_TAGS):
        return False
    return active_reply_type != "time"


def rewrite_booking_scenario_orphan_pending_question_tags(tags: list[str]) -> list[str]:
    rewritten: list[str] = []
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag or tag in BOOKING_SCENARIO_PENDING_QUESTION_TAGS:
            continue
        if tag not in rewritten:
            rewritten.append(tag)
    if "booking" not in rewritten:
        rewritten.insert(0, "booking")
    return rewritten


def booking_scenario_orphan_pending_question_expect_override() -> dict[str, Any]:
    return deepcopy(_BOOKING_SCENARIO_ORPHAN_PENDING_QUESTION_EXPECT_OVERRIDE)


def rewrite_booking_scenario_reschedule_followup_tags(tags: list[str]) -> list[str]:
    rewritten: list[str] = []
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag or tag in BOOKING_SCENARIO_PENDING_QUESTION_TAGS or tag in {"booking", "time"}:
            continue
        if tag not in rewritten:
            rewritten.append(tag)
    if "reschedule" not in rewritten:
        rewritten.insert(0, "reschedule")
    return rewritten


def booking_scenario_reschedule_followup_expect_override() -> dict[str, Any]:
    return deepcopy(_BOOKING_SCENARIO_RESCHEDULE_FOLLOWUP_EXPECT_OVERRIDE)


def rewrite_booking_scenario_check_booking_followup_tags(tags: list[str]) -> list[str]:
    rewritten: list[str] = []
    for raw_tag in tags:
        if not isinstance(raw_tag, str):
            continue
        tag = raw_tag.strip().lower()
        if not tag or tag == "booking":
            continue
        if tag not in rewritten:
            rewritten.append(tag)
    if "check_booking" not in rewritten:
        rewritten.insert(0, "check_booking")
    return rewritten


def booking_scenario_check_booking_followup_expect_override() -> dict[str, Any]:
    return deepcopy(_BOOKING_SCENARIO_CHECK_BOOKING_FOLLOWUP_EXPECT_OVERRIDE)


def booking_scenario_time_collect_expect_override() -> dict[str, Any]:
    return deepcopy(_BOOKING_SCENARIO_TIME_COLLECT_EXPECT_OVERRIDE)


def apply_booking_scenario_active_time_specialist_followup_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    if active_reply_type not in {"service_choice", "time", "name"}:
        return expect

    lowered_tags = _booking_scenario_lowered_tags(tags)
    specialist_target_question = bool(
        active_reply_type == "time"
        and "ask_about_requested_slot" in lowered_tags
        and (
            infer_booking_scenario_pending_question_target(text, tags) == "specialist"
            or booking_scenario_looks_like_named_specialist_preference_availability_question(text)
        )
    )
    if specialist_target_question:
        expect["reply_type"] = "time"
        expect["info_sections"] = []

        meta = deepcopy(dict(expect.get("meta") or {}))
        if meta.get("expected_reply_type"):
            meta["expected_reply_type"] = "time"
        if meta:
            expect["meta"] = meta

        meta_any = deepcopy(dict(expect.get("meta_any") or {}))
        meta_any.pop("pending_question_act", None)
        meta_any.pop("pending_question_owner", None)
        meta_any.pop("booking_interrupt_info", None)
        meta_any.pop("intent", None)
        meta_any.pop("source", None)
        meta_any["pending_question_target"] = ["specialist"]
        meta_any["active_question_relation"] = ["referent_followup"]
        meta_any["expected_reply_type"] = ["time"]
        expect["meta_any"] = meta_any

        return compile_active_time_specialist_followup_expectations(expect)

    specialist_followup = bool(
        "booking" in lowered_tags
        and looks_like_booking_scenario_specialist_reference(text or "")
    )
    if not specialist_followup:
        return expect

    expect["reply_type"] = active_reply_type
    expect["info_sections"] = []

    meta = deepcopy(dict(expect.get("meta") or {}))
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = active_reply_type
    if meta:
        expect["meta"] = meta

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any["pending_question_target"] = ["specialist"]
    meta_any["expected_reply_type"] = [active_reply_type]
    meta_any["pending_question_interaction"] = ["specialist_followup"]
    meta_any["pending_question_owner"] = ["booking_specialist_followup"]
    meta_any["active_question_relation"] = ["referent_followup"]
    meta_any.pop("booking_interrupt_info", None)
    meta_any.pop("intent", None)
    meta_any.pop("source", None)
    expect["meta_any"] = meta_any

    trace_contains = []
    for entry in deepcopy(list(expect.get("trace_contains") or [])):
        normalized_entry = dict(entry)
        if (
            normalized_entry.get("stage") == "booking_interrupt"
            and normalized_entry.get("pending_question_target") == "specialist"
        ):
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = active_reply_type
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": active_reply_type,
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    specialist_trace = {
        "stage": "pending_question_interaction",
        "decision": "booking_specialist_followup",
        "pending_question_target": "specialist",
        "active_question_relation": "referent_followup",
        "expected_reply_type": active_reply_type,
    }
    if specialist_trace not in trace_contains:
        trace_contains.append(specialist_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def apply_booking_scenario_pending_master_info_interrupt_expectations(
    expect: dict[str, Any],
    *,
    original_tags: list[str],
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    original_lowered = _booking_scenario_lowered_tags(original_tags)
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "ask_about_requested_slot" not in original_lowered:
        return expect
    if "master" not in lowered_tags:
        return expect
    if active_reply_type != "time":
        return expect
    if not booking_scenario_looks_like_generic_master_info_question(text):
        return expect
    if booking_scenario_looks_like_specialist_availability_followup_question(text):
        return expect

    expect["reply_type"] = "time"
    expect["expected_reply"] = True

    info_sections = list(expect.get("info_sections") or [])
    for section in BOOKING_SCENARIO_EXPECT_INFO_SECTIONS["master"]:
        if section not in info_sections:
            info_sections.append(section)
    expect["info_sections"] = info_sections

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any["intent"] = ["master"]
    meta_any["source"] = ["booking_info_contract"]
    meta_any["booking_interrupt_info"] = [True]
    meta_any["pending_question_target"] = ["time"]
    meta_any["expected_reply_type"] = ["time"]
    meta_any.pop("pending_question_act", None)

    trace_contains = [
        dict(entry)
        for entry in deepcopy(list(expect.get("trace_contains") or []))
        if entry.get("stage") != "pending_question_interaction"
    ]
    booking_interrupt_trace = {
        "stage": "booking_interrupt",
        "decision": "info_reply",
        "pending_question_target": "time",
        "booking_interrupt_info": True,
    }
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "time",
    }
    if booking_interrupt_trace not in trace_contains:
        trace_contains.append(booking_interrupt_trace)
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)

    expect["meta_any"] = meta_any
    expect["trace_contains"] = trace_contains
    return expect


def apply_booking_scenario_pending_specialist_availability_followup_expectations(
    expect: dict[str, Any],
    *,
    original_tags: list[str],
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    original_lowered = _booking_scenario_lowered_tags(original_tags)
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "ask_about_requested_slot" not in original_lowered:
        return expect
    if "master" not in lowered_tags:
        return expect
    if active_reply_type != "time":
        return expect
    if not booking_scenario_looks_like_specialist_availability_followup_question(text):
        return expect

    expect["reply_type"] = "time"
    expect["expected_reply"] = True

    info_sections = list(expect.get("info_sections") or [])
    for section in BOOKING_SCENARIO_EXPECT_INFO_SECTIONS["master"]:
        if section not in info_sections:
            info_sections.append(section)
    expect["info_sections"] = info_sections

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any["source"] = ["llm_policy_core"]
    meta_any["pending_question_act"] = ["ask_about_requested_slot"]
    meta_any["pending_question_target"] = ["specialist"]
    meta_any["pending_question_interaction"] = ["specialist_availability_followup"]
    meta_any["pending_question_owner"] = ["booking_specialist_availability_followup"]
    meta_any["active_question_relation"] = ["specialist_availability_followup"]
    meta_any["expected_reply_type"] = ["time"]
    expect["meta_any"] = meta_any

    trace_contains = [
        dict(entry)
        for entry in deepcopy(list(expect.get("trace_contains") or []))
        if entry.get("stage") != "booking_interrupt"
    ]
    followup_trace = {
        "stage": "pending_question_interaction",
        "decision": "booking_specialist_availability_followup",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "specialist",
        "active_question_relation": "specialist_availability_followup",
        "expected_reply_type": "time",
    }
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "time",
    }
    if followup_trace not in trace_contains:
        trace_contains.append(followup_trace)
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    expect["trace_contains"] = trace_contains
    return expect


def apply_booking_scenario_grounded_time_specialist_availability_transition_expectations(
    expect: dict[str, Any],
    *,
    original_tags: list[str],
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    original_lowered = _booking_scenario_lowered_tags(original_tags)
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if not (original_lowered & {"ask_about_requested_slot", "slot_compare"}):
        return expect
    if "master" not in lowered_tags:
        return expect
    if active_reply_type != "time":
        return expect
    if not booking_scenario_looks_like_grounded_time_specialist_availability_transition_question(text):
        return expect

    expect["reply_type"] = "name"
    expect["expected_reply"] = True

    info_sections = list(expect.get("info_sections") or [])
    for section in BOOKING_SCENARIO_EXPECT_INFO_SECTIONS["master"]:
        if section not in info_sections:
            info_sections.append(section)
    expect["info_sections"] = info_sections

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any.pop("booking_interrupt_info", None)
    meta_any.pop("intent", None)
    meta_any["source"] = ["llm_policy_core"]
    meta_any["pending_question_act"] = ["ask_about_requested_slot"]
    meta_any["pending_question_target"] = ["specialist"]
    meta_any["pending_question_interaction"] = ["specialist_availability_followup"]
    meta_any["pending_question_owner"] = ["booking_specialist_availability_followup"]
    meta_any["active_question_relation"] = ["specialist_availability_followup"]
    meta_any["expected_reply_type"] = ["name"]
    expect["meta_any"] = meta_any

    trace_contains = [
        dict(entry)
        for entry in deepcopy(list(expect.get("trace_contains") or []))
        if entry.get("stage") not in {"booking_interrupt", "question_contract"}
    ]
    followup_trace = {
        "stage": "pending_question_interaction",
        "decision": "booking_specialist_availability_followup",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "specialist",
        "active_question_relation": "specialist_availability_followup",
        "expected_reply_type": "name",
    }
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "name",
    }
    if followup_trace not in trace_contains:
        trace_contains.append(followup_trace)
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    expect["trace_contains"] = trace_contains
    return expect


def apply_booking_scenario_active_name_master_info_interrupt_expectations(
    expect: dict[str, Any],
    *,
    original_tags: list[str],
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    original_lowered = _booking_scenario_lowered_tags(original_tags)
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "booking" not in original_lowered:
        return expect
    if "master" not in lowered_tags:
        return expect
    if active_reply_type != "name":
        return expect
    if not booking_scenario_looks_like_generic_master_info_question(text):
        return expect

    expect["reply_type"] = "name"
    expect["expected_reply"] = True

    info_sections = list(expect.get("info_sections") or [])
    for section in BOOKING_SCENARIO_EXPECT_INFO_SECTIONS["master"]:
        if section not in info_sections:
            info_sections.append(section)
    expect["info_sections"] = info_sections

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any["intent"] = ["master"]
    meta_any["source"] = ["booking_info_contract"]
    meta_any["booking_interrupt_info"] = [True]
    meta_any["pending_question_target"] = ["specialist"]
    meta_any["expected_reply_type"] = ["name"]
    meta_any.pop("pending_question_act", None)
    expect["meta_any"] = meta_any

    trace_contains = [
        dict(entry)
        for entry in deepcopy(list(expect.get("trace_contains") or []))
        if entry.get("stage") != "pending_question_interaction"
    ]
    booking_interrupt_trace = {
        "stage": "booking_interrupt",
        "decision": "info_reply",
        "pending_question_target": "specialist",
        "booking_interrupt_info": True,
        "info_sections": ["master"],
    }
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "name",
    }
    if booking_interrupt_trace not in trace_contains:
        trace_contains.append(booking_interrupt_trace)
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    expect["trace_contains"] = trace_contains
    return expect


def apply_booking_scenario_active_time_master_info_interrupt_expectations(
    expect: dict[str, Any],
    *,
    original_tags: list[str],
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    original_lowered = _booking_scenario_lowered_tags(original_tags)
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "booking" not in original_lowered:
        return expect
    if "master" not in lowered_tags:
        return expect
    if active_reply_type != "time":
        return expect
    if not booking_scenario_looks_like_generic_master_info_question(text):
        return expect
    if booking_scenario_looks_like_specialist_availability_followup_question(text):
        return expect
    if booking_scenario_looks_like_grounded_time_specialist_availability_transition_question(text):
        return expect

    expect["reply_type"] = "time"
    expect["expected_reply"] = True

    info_sections = list(expect.get("info_sections") or [])
    for section in BOOKING_SCENARIO_EXPECT_INFO_SECTIONS["master"]:
        if section not in info_sections:
            info_sections.append(section)
    expect["info_sections"] = info_sections

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any["intent"] = ["master"]
    meta_any["source"] = ["booking_info_contract"]
    meta_any["booking_interrupt_info"] = [True]
    meta_any["pending_question_target"] = ["time"]
    meta_any["expected_reply_type"] = ["time"]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_interaction", None)
    meta_any.pop("pending_question_owner", None)
    meta_any.pop("active_question_relation", None)
    expect["meta_any"] = meta_any

    trace_contains = [
        dict(entry)
        for entry in deepcopy(list(expect.get("trace_contains") or []))
        if entry.get("stage") != "pending_question_interaction"
    ]
    booking_interrupt_trace = {
        "stage": "booking_interrupt",
        "decision": "info_reply",
        "pending_question_target": "time",
        "booking_interrupt_info": True,
        "info_sections": ["master"],
    }
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "time",
    }
    if booking_interrupt_trace not in trace_contains:
        trace_contains.append(booking_interrupt_trace)
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    expect["trace_contains"] = trace_contains
    return expect


def booking_scenario_expectation_has_contract_reason(
    expect: dict[str, Any] | None,
    reason: str,
) -> bool:
    normalized_reason = str(reason or "").strip().lower()
    if not normalized_reason:
        return False

    meta = deepcopy(dict((expect or {}).get("meta") or {}))
    meta_reason = str(meta.get("expected_reply_contract_reason") or "").strip().lower()
    if meta_reason == normalized_reason:
        return True

    meta_any = deepcopy(dict((expect or {}).get("meta_any") or {}))
    meta_any_reasons = meta_any.get("expected_reply_contract_reason")
    if isinstance(meta_any_reasons, str):
        meta_any_reasons = [meta_any_reasons]
    if isinstance(meta_any_reasons, list):
        for item in meta_any_reasons:
            item_reason = str(item or "").strip().lower()
            if item_reason == normalized_reason:
                return True

    for entry in deepcopy(list((expect or {}).get("trace_contains") or [])):
        if not isinstance(entry, dict):
            continue
        entry_reason = str(entry.get("reason") or "").strip().lower()
        if entry_reason == normalized_reason:
            return True
    return False


def apply_booking_scenario_active_pending_question_info_interrupt_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    active_reply_type: str | None,
) -> dict[str, Any]:
    if active_reply_type not in {"service_choice", "time", "name"}:
        return expect

    lowered_tags = _booking_scenario_lowered_tags(tags)
    if not (lowered_tags & _BOOKING_SCENARIO_ACTIVE_PENDING_QUESTION_INFO_INTERRUPT_TAGS):
        return expect
    if lowered_tags & (
        BOOKING_SCENARIO_PENDING_QUESTION_TAGS
        | {"booking", "time", "master", "handoff", "human", "pending", "cancel", "reschedule"}
    ):
        return expect

    expect["reply_type"] = active_reply_type
    expect["expected_reply"] = True

    meta = deepcopy(dict(expect.get("meta") or {}))
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = active_reply_type
    if meta:
        expect["meta"] = meta

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any["expected_reply_type"] = [active_reply_type]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in deepcopy(list(expect.get("trace_contains") or [])):
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "pending_question_interaction":
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = active_reply_type
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": active_reply_type,
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def clear_booking_scenario_multi_service_info_interrupt_followup_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    multi_service_clarify_active: bool,
) -> dict[str, Any]:
    if not multi_service_clarify_active:
        return expect

    lowered_tags = _booking_scenario_lowered_tags(tags)
    if not (lowered_tags & _BOOKING_SCENARIO_ACTIVE_PENDING_QUESTION_INFO_INTERRUPT_TAGS):
        return expect
    if lowered_tags & (
        BOOKING_SCENARIO_PENDING_QUESTION_TAGS
        | {"booking", "time", "master", "handoff", "human", "pending", "cancel", "reschedule"}
    ):
        return expect

    expect["reply_type"] = None
    if expect.get("expected_reply") is None:
        expect["expected_reply"] = True

    meta = deepcopy(dict(expect.get("meta") or {}))
    meta.pop("expected_reply_type", None)
    meta.pop("expected_reply_contract_reason", None)
    if meta:
        expect["meta"] = meta
    elif "meta" in expect:
        expect.pop("meta", None)

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any.pop("expected_reply_type", None)
    meta_any.pop("expected_reply_contract_reason", None)
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    meta_any.pop("pending_question_interaction", None)
    meta_any.pop("pending_question_owner", None)
    meta_any.pop("active_question_relation", None)
    if meta_any:
        expect["meta_any"] = meta_any
    elif "meta_any" in expect:
        expect.pop("meta_any", None)

    trace_contains = []
    for entry in deepcopy(list(expect.get("trace_contains") or [])):
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") in {
            "question_contract",
            "pending_question_interaction",
        }:
            continue
        trace_contains.append(normalized_entry)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    elif "trace_contains" in expect:
        expect.pop("trace_contains", None)
    return expect


def apply_booking_scenario_active_pending_question_cancel_interrupt_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    active_reply_type: str | None,
) -> dict[str, Any]:
    if active_reply_type not in {"service_choice", "time", "name"}:
        return expect

    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "cancel" not in lowered_tags:
        return expect
    if lowered_tags & {"booking", "time", "master", "reschedule", "check_booking"}:
        return expect

    expect["reply_type"] = active_reply_type
    expect["expected_reply"] = True

    meta = deepcopy(dict(expect.get("meta") or {}))
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = active_reply_type
    if meta:
        expect["meta"] = meta

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any["expected_reply_type"] = [active_reply_type]
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in deepcopy(list(expect.get("trace_contains") or [])):
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = active_reply_type
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": active_reply_type,
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def apply_booking_scenario_ambiguous_time_fill_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    if active_reply_type != "time":
        return expect
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "time" not in lowered_tags:
        return expect
    if not booking_scenario_looks_like_ambiguous_time_fill(text):
        return expect

    expect["reply_type"] = "time"
    expect["expected_reply"] = True

    meta = deepcopy(dict(expect.get("meta") or {}))
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = "time"
    if meta:
        expect["meta"] = meta

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any["expected_reply_type"] = ["time"]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    meta_any.pop("pending_question_interaction", None)
    meta_any.pop("pending_question_owner", None)
    meta_any.pop("active_question_relation", None)
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in deepcopy(list(expect.get("trace_contains") or [])):
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "pending_question_interaction":
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = "time"
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "time",
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def apply_booking_scenario_service_grounded_booking_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
    service_candidates: tuple[str, ...] | list[str] = (),
    ctx: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "booking" not in lowered_tags:
        return expect
    if not booking_scenario_looks_like_service_grounded_booking(
        text,
        service_candidates=service_candidates,
        ctx=ctx,
    ):
        return expect

    expect["reply_type"] = "time"
    collect_reason = "collect:datetime"

    meta = deepcopy(dict(expect.get("meta") or {}))
    if meta.get("expected_reply_type") == "service_choice":
        meta["expected_reply_type"] = "time"
    stale_reason = _normalize_lower_token(meta.get("expected_reply_reason"))
    if stale_reason in {"booking_prompt", "collect:service"}:
        meta["expected_reply_reason"] = collect_reason
    if meta:
        expect["meta"] = meta

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    if meta_any.get("expected_reply_type"):
        meta_any["expected_reply_type"] = ["time"]
    expected_reply_reasons = meta_any.get("expected_reply_reason")
    if isinstance(expected_reply_reasons, list) and expected_reply_reasons:
        normalized_reasons = {_normalize_lower_token(item) for item in expected_reply_reasons}
        if normalized_reasons & {"booking_prompt", "collect:service"}:
            meta_any["expected_reply_reason"] = [collect_reason]
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in deepcopy(list(expect.get("trace_contains") or [])):
        normalized_entry = dict(entry)
        if (
            normalized_entry.get("stage") == "question_contract"
            and normalized_entry.get("expected_reply_type") == "service_choice"
        ):
            normalized_entry["expected_reply_type"] = "time"
        if normalized_entry.get("stage") == "question_contract":
            reason_token = _normalize_lower_token(normalized_entry.get("reason"))
            if reason_token in {"booking_prompt", "collect:service"}:
                normalized_entry["reason"] = collect_reason
        trace_contains.append(normalized_entry)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def apply_booking_scenario_multi_service_booking_clarify_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
    service_candidates: tuple[str, ...] | list[str] = (),
    ctx: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "booking" not in lowered_tags:
        return expect
    if not booking_scenario_looks_like_multi_service_booking_request(
        text,
        service_candidates=service_candidates,
        ctx=ctx,
    ):
        return expect

    expect["reply_type"] = "service_choice"
    expect["expected_reply"] = True

    meta = deepcopy(dict(expect.get("meta") or {}))
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = "service_choice"
    meta["expected_reply_contract_reason"] = "multi_service_booking_clarify"
    if meta:
        expect["meta"] = meta

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any["expected_reply_type"] = ["service_choice"]
    meta_any["expected_reply_contract_reason"] = ["multi_service_booking_clarify"]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    meta_any.pop("pending_question_interaction", None)
    meta_any.pop("pending_question_owner", None)
    meta_any.pop("active_question_relation", None)
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in deepcopy(list(expect.get("trace_contains") or [])):
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "pending_question_interaction":
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = "service_choice"
            normalized_entry["reason"] = "multi_service_booking_clarify"
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "service_choice",
        "reason": "multi_service_booking_clarify",
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def apply_booking_scenario_service_grounded_booking_progress_interrupt_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
    service_candidates: tuple[str, ...] | list[str] = (),
    ctx: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if active_reply_type != "service_choice":
        return expect

    lowered_tags = _booking_scenario_lowered_tags(tags)
    if not (lowered_tags & {"price", "duration", "promo"}):
        return expect
    if not booking_scenario_looks_like_service_grounded_booking(
        text,
        service_candidates=service_candidates,
        ctx=ctx,
    ):
        return expect

    expect["reply_type"] = "time"
    expect["expected_reply"] = True

    meta = deepcopy(dict(expect.get("meta") or {}))
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = "time"
    meta["expected_reply_contract_reason"] = "catalog_service_booking_progress"
    if meta:
        expect["meta"] = meta

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any["expected_reply_type"] = ["time"]
    meta_any["expected_reply_contract_reason"] = ["catalog_service_booking_progress"]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in deepcopy(list(expect.get("trace_contains") or [])):
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "pending_question_interaction":
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = "time"
            normalized_entry["reason"] = "catalog_service_booking_progress"
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "time",
        "reason": "catalog_service_booking_progress",
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def apply_booking_scenario_exact_time_fill_collect_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    if active_reply_type != "time":
        return expect
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "time" not in lowered_tags:
        return expect
    if not booking_scenario_looks_like_explicit_time_fill(text):
        return expect
    if booking_scenario_looks_like_ambiguous_time_fill(text):
        return expect

    expect["reply_type"] = "name"
    expect["expected_reply"] = True

    meta = deepcopy(dict(expect.get("meta") or {}))
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = "name"
    if meta:
        expect["meta"] = meta

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any["expected_reply_type"] = ["name"]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    meta_any.pop("pending_question_interaction", None)
    meta_any.pop("pending_question_owner", None)
    meta_any.pop("active_question_relation", None)
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in deepcopy(list(expect.get("trace_contains") or [])):
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "pending_question_interaction":
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = "name"
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "name",
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def apply_booking_scenario_partial_date_fill_collect_expectations(
    expect: dict[str, Any],
    *,
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    if active_reply_type != "time":
        return expect
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "time" not in lowered_tags:
        return expect
    if not booking_scenario_looks_like_partial_date_fill_without_availability_query(text):
        return expect

    expect["reply_type"] = "time"
    expect["expected_reply"] = True

    meta = deepcopy(dict(expect.get("meta") or {}))
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = "time"
    if meta:
        expect["meta"] = meta

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any["expected_reply_type"] = ["time"]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    meta_any.pop("pending_question_interaction", None)
    meta_any.pop("pending_question_owner", None)
    meta_any.pop("active_question_relation", None)
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in deepcopy(list(expect.get("trace_contains") or [])):
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "pending_question_interaction":
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = "time"
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "time",
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def apply_booking_scenario_grounded_partial_date_daypart_fill_expectations(
    expect: dict[str, Any],
    *,
    original_tags: list[str],
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
    partial_date_anchor_active: bool,
) -> dict[str, Any]:
    if active_reply_type != "time" or not partial_date_anchor_active:
        return expect
    original_lowered = _booking_scenario_lowered_tags(original_tags)
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if "mixed_fill_plus_question" not in original_lowered:
        return expect
    if "time" not in lowered_tags:
        return expect
    if not booking_scenario_looks_like_grounded_partial_date_daypart_fill(text):
        return expect

    expect["reply_type"] = "time"
    expect["expected_reply"] = True

    meta = deepcopy(dict(expect.get("meta") or {}))
    if meta.get("expected_reply_type"):
        meta["expected_reply_type"] = "time"
    if meta:
        expect["meta"] = meta

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any["expected_reply_type"] = ["time"]
    meta_any.pop("pending_question_act", None)
    meta_any.pop("pending_question_target", None)
    meta_any.pop("pending_question_interaction", None)
    meta_any.pop("pending_question_owner", None)
    meta_any.pop("active_question_relation", None)
    if meta_any:
        expect["meta_any"] = meta_any

    trace_contains = []
    for entry in deepcopy(list(expect.get("trace_contains") or [])):
        normalized_entry = dict(entry)
        if normalized_entry.get("stage") == "pending_question_interaction":
            continue
        if normalized_entry.get("stage") == "question_contract":
            normalized_entry["expected_reply_type"] = "time"
        trace_contains.append(normalized_entry)
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "time",
    }
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    if trace_contains:
        expect["trace_contains"] = trace_contains
    return expect


def apply_booking_scenario_active_name_time_availability_followup_expectations(
    expect: dict[str, Any],
    *,
    original_tags: list[str],
    tags: list[str],
    text: str | None,
    active_reply_type: str | None,
) -> dict[str, Any]:
    original_lowered = _booking_scenario_lowered_tags(original_tags)
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if active_reply_type != "name":
        return expect
    if not ({"booking", "ask_about_requested_slot"} & (original_lowered | lowered_tags)):
        return expect
    if "booking" not in lowered_tags:
        return expect
    explicit_time_followup = bool(
        "ask_about_requested_slot" in (original_lowered | lowered_tags)
        and booking_scenario_looks_like_explicit_time_fill(text)
    )
    if not (
        booking_scenario_looks_like_grounded_time_availability_probe(text)
        or booking_scenario_looks_like_requested_slot_question_without_temporal_scope(text)
        or explicit_time_followup
    ):
        return expect

    expect["reply_type"] = "name"
    expect["expected_reply"] = True

    meta_any = deepcopy(dict(expect.get("meta_any") or {}))
    meta_any.pop("booking_interrupt_info", None)
    meta_any.pop("intent", None)
    meta_any["source"] = ["llm_policy_core"]
    meta_any["pending_question_act"] = ["ask_about_requested_slot"]
    meta_any["pending_question_target"] = ["time"]
    meta_any["pending_question_interaction"] = ["ask_about_requested_slot"]
    meta_any["pending_question_owner"] = ["booking_time_availability_followup"]
    meta_any["active_question_relation"] = ["ask_about_requested_slot"]
    meta_any["expected_reply_type"] = ["name"]
    expect["meta_any"] = meta_any

    trace_contains = [
        dict(entry)
        for entry in deepcopy(list(expect.get("trace_contains") or []))
        if entry.get("stage")
        not in {"booking_interrupt", "question_contract", "pending_question_interaction"}
    ]
    followup_trace = {
        "stage": "pending_question_interaction",
        "decision": "booking_time_availability_followup",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "expected_reply_type": "name",
    }
    question_contract_trace = {
        "stage": "question_contract",
        "expected_reply_type": "name",
    }
    if followup_trace not in trace_contains:
        trace_contains.append(followup_trace)
    if question_contract_trace not in trace_contains:
        trace_contains.append(question_contract_trace)
    expect["trace_contains"] = trace_contains
    return expect


def advance_booking_scenario_pending_question_context(
    active_reply_type: str | None,
    *,
    tags: list[str],
    expect: dict[str, Any] | None,
) -> str | None:
    reply_type = str((expect or {}).get("reply_type") or "").strip().lower() or None
    if reply_type == "service_choice" and booking_scenario_expectation_has_contract_reason(
        expect,
        "multi_service_booking_clarify",
    ):
        return None
    if reply_type:
        return reply_type
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if lowered_tags & _PENDING_QUESTION_CONTEXT_PRESERVE_TAGS:
        return active_reply_type
    return None


def advance_booking_scenario_multi_service_clarify_context(
    multi_service_clarify_active: bool,
    *,
    tags: list[str],
    expect: dict[str, Any] | None,
) -> bool:
    if booking_scenario_expectation_has_contract_reason(expect, "multi_service_booking_clarify"):
        return True
    if not multi_service_clarify_active:
        return False

    lowered_tags = _booking_scenario_lowered_tags(tags)
    if lowered_tags & (
        {"booking", "time", "name", "phone", "confirm"}
        | BOOKING_SCENARIO_PENDING_QUESTION_TAGS
        | {"slot_compare", "slot_constraint"}
    ):
        return False
    return bool(
        lowered_tags
        & (_BOOKING_SCENARIO_ACTIVE_PENDING_QUESTION_INFO_INTERRUPT_TAGS | {"info", "media", "photo", "interrupt"})
    )


def advance_booking_scenario_partial_date_anchor_context(
    partial_date_anchor_active: bool,
    *,
    active_reply_type: str | None,
    tags: list[str],
    text: str | None,
    expect: dict[str, Any] | None,
) -> bool:
    if active_reply_type != "time":
        return False
    if booking_scenario_looks_like_partial_date_fill_without_availability_query(text):
        return True
    next_reply_type = str((expect or {}).get("reply_type") or "").strip().lower() or None
    if next_reply_type != "time":
        return False
    lowered_tags = _booking_scenario_lowered_tags(tags)
    if lowered_tags & _BOOKING_SCENARIO_ACTIVE_PENDING_QUESTION_INFO_INTERRUPT_TAGS:
        if not booking_scenario_expectation_has_contract_reason(
            expect,
            "catalog_service_booking_progress",
        ):
            return False
    return partial_date_anchor_active


@dataclass(frozen=True)
class BookingScenarioPostCoverageRepairState:
    active_reply_type: str | None = None
    partial_date_anchor_active: bool = False
    multi_service_clarify_active: bool = False
    active_management_tag: str | None = None


@dataclass(frozen=True)
class BookingScenarioPostCoverageRepairDecision:
    tags: list[str] = field(default_factory=list)
    expect_override: Any = None


@dataclass(frozen=True)
class BookingScenarioPostCoverageRepairCallbacks:
    service_candidates: tuple[str, ...] = field(default_factory=tuple)


def _booking_scenario_coerce_turn_tags(raw_tags: Any) -> list[str]:
    return [
        str(tag).strip().lower()
        for tag in (raw_tags or [])
        if isinstance(tag, str) and str(tag).strip()
    ]


def _booking_scenario_select_post_coverage_repair_decision(
    text: str,
    tags: list[str],
    *,
    state: BookingScenarioPostCoverageRepairState,
    callbacks: BookingScenarioPostCoverageRepairCallbacks,
) -> BookingScenarioPostCoverageRepairDecision | None:
    rewritten_check_booking_tags, malformed_check_booking_normalized = (
        booking_scenario_normalize_malformed_check_booking_tags(text, tags)
    )
    effective_tags = rewritten_check_booking_tags if malformed_check_booking_normalized else tags

    rewritten_tags, active_time_specialist_master_normalized = (
        booking_scenario_normalize_active_time_specialist_master_tags(
            text,
            effective_tags,
            active_reply_type=state.active_reply_type,
        )
    )
    rewritten_active_time_master_tags, active_time_master_info_normalized = (
        booking_scenario_normalize_active_time_master_info_tags(
            text,
            effective_tags,
            active_reply_type=state.active_reply_type,
        )
    )
    rewritten_requested_slot_tags, booking_requested_slot_normalized = (
        booking_scenario_normalize_booking_requested_slot_question_tags(
            text,
            effective_tags,
            active_reply_type=state.active_reply_type,
        )
    )
    (
        rewritten_slot_constraint_requested_slot_tags,
        slot_constraint_requested_slot_normalized,
    ) = booking_scenario_normalize_slot_constraint_requested_slot_question_tags(
        text,
        effective_tags,
        active_reply_type=state.active_reply_type,
    )
    (
        rewritten_slot_compare_requested_slot_tags,
        slot_compare_requested_slot_normalized,
    ) = booking_scenario_normalize_slot_compare_requested_slot_question_tags(
        text,
        effective_tags,
        active_reply_type=state.active_reply_type,
    )
    (
        rewritten_slot_compare_partial_date_constraint_tags,
        slot_compare_partial_date_constraint_normalized,
    ) = booking_scenario_normalize_slot_compare_partial_date_constraint_tags(
        text,
        effective_tags,
        active_reply_type=state.active_reply_type,
    )
    rewritten_slot_compare_tags, slot_compare_exact_time_normalized = (
        booking_scenario_normalize_slot_compare_exact_time_fill_tags(
            text,
            effective_tags,
            active_reply_type=state.active_reply_type,
        )
    )
    (
        rewritten_grounded_partial_date_tags,
        grounded_partial_date_mixed_fill_normalized,
    ) = booking_scenario_normalize_grounded_partial_date_mixed_fill_tags(
        text,
        effective_tags,
        active_reply_type=state.active_reply_type,
        partial_date_anchor_active=state.partial_date_anchor_active,
    )

    if slot_compare_exact_time_normalized:
        return BookingScenarioPostCoverageRepairDecision(tags=rewritten_slot_compare_tags)
    if booking_requested_slot_normalized:
        return BookingScenarioPostCoverageRepairDecision(tags=rewritten_requested_slot_tags)
    if slot_constraint_requested_slot_normalized:
        return BookingScenarioPostCoverageRepairDecision(
            tags=rewritten_slot_constraint_requested_slot_tags
        )
    if slot_compare_requested_slot_normalized:
        return BookingScenarioPostCoverageRepairDecision(
            tags=rewritten_slot_compare_requested_slot_tags
        )
    if slot_compare_partial_date_constraint_normalized:
        return BookingScenarioPostCoverageRepairDecision(
            tags=rewritten_slot_compare_partial_date_constraint_tags
        )
    if grounded_partial_date_mixed_fill_normalized:
        return BookingScenarioPostCoverageRepairDecision(
            tags=rewritten_grounded_partial_date_tags
        )
    if malformed_check_booking_normalized:
        return BookingScenarioPostCoverageRepairDecision(tags=rewritten_check_booking_tags)
    if active_time_specialist_master_normalized:
        return BookingScenarioPostCoverageRepairDecision(
            tags=rewritten_tags,
            expect_override=(
                booking_scenario_orphan_pending_question_expect_override()
                if state.active_reply_type is None
                else {}
            ),
        )
    if active_time_master_info_normalized:
        return BookingScenarioPostCoverageRepairDecision(
            tags=rewritten_active_time_master_tags
        )
    if booking_scenario_looks_like_check_booking_followup(text, effective_tags):
        return BookingScenarioPostCoverageRepairDecision(
            tags=rewrite_booking_scenario_check_booking_followup_tags(effective_tags),
            expect_override=booking_scenario_check_booking_followup_expect_override(),
        )
    if (
        state.active_management_tag == "reschedule"
        and booking_scenario_looks_like_reschedule_followup(text, effective_tags)
    ):
        return BookingScenarioPostCoverageRepairDecision(
            tags=rewrite_booking_scenario_reschedule_followup_tags(effective_tags),
            expect_override=booking_scenario_reschedule_followup_expect_override(),
        )
    if has_booking_scenario_orphan_pending_question_tags(
        effective_tags,
        active_reply_type=state.active_reply_type,
    ):
        return BookingScenarioPostCoverageRepairDecision(
            tags=rewrite_booking_scenario_orphan_pending_question_tags(effective_tags),
            expect_override=booking_scenario_orphan_pending_question_expect_override(),
        )
    return None


def repair_booking_scenario_post_coverage_dialogs(
    dialogs: list[dict[str, Any]],
    *,
    callbacks: BookingScenarioPostCoverageRepairCallbacks,
) -> list[dict[str, Any]]:
    repaired_dialogs: list[dict[str, Any]] = []
    for dialog in dialogs:
        if not isinstance(dialog, dict):
            continue
        normalized_dialog = dict(dialog)
        turns = list(normalized_dialog.get("turns") or [])
        state = BookingScenarioPostCoverageRepairState()
        repaired_turns: list[dict[str, Any]] = []
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            normalized_turn = dict(turn)
            raw_tags = normalized_turn.get("tags") or []
            text = str(normalized_turn.get("text") or "")
            tags = _booking_scenario_coerce_turn_tags(raw_tags)

            decision = _booking_scenario_select_post_coverage_repair_decision(
                text,
                tags,
                state=state,
                callbacks=callbacks,
            )
            if decision is not None:
                normalized_turn["tags"] = decision.tags
                normalized_turn["expect"] = merge_booking_scenario_expectations(
                    decision.tags,
                    decision.expect_override if decision.expect_override is not None else {},
                    text=text,
                )

            expectations = (
                normalized_turn.get("expect")
                if isinstance(normalized_turn.get("expect"), dict)
                else {}
            )
            current_tags = normalized_turn.get("tags") or []
            expectations = apply_booking_scenario_multi_service_booking_clarify_expectations(
                expectations,
                tags=current_tags,
                text=text,
                service_candidates=callbacks.service_candidates,
                ctx=None,
            )
            expectations = apply_booking_scenario_active_pending_question_info_interrupt_expectations(
                expectations,
                tags=current_tags,
                active_reply_type=state.active_reply_type,
            )
            expectations = clear_booking_scenario_multi_service_info_interrupt_followup_expectations(
                expectations,
                tags=current_tags,
                multi_service_clarify_active=state.multi_service_clarify_active,
            )
            expectations = apply_booking_scenario_service_grounded_booking_progress_interrupt_expectations(
                expectations,
                tags=current_tags,
                text=text,
                service_candidates=callbacks.service_candidates,
                ctx=None,
                active_reply_type=state.active_reply_type,
            )
            expectations = apply_booking_scenario_active_pending_question_cancel_interrupt_expectations(
                expectations,
                tags=current_tags,
                active_reply_type=state.active_reply_type,
            )
            expectations = apply_booking_scenario_exact_time_fill_collect_expectations(
                expectations,
                tags=current_tags,
                text=text,
                active_reply_type=state.active_reply_type,
            )
            expectations = apply_booking_scenario_partial_date_fill_collect_expectations(
                expectations,
                tags=current_tags,
                text=text,
                active_reply_type=state.active_reply_type,
            )
            expectations = apply_booking_scenario_grounded_partial_date_daypart_fill_expectations(
                expectations,
                original_tags=raw_tags,
                tags=current_tags,
                text=text,
                active_reply_type=state.active_reply_type,
                partial_date_anchor_active=state.partial_date_anchor_active,
            )
            expectations = apply_booking_scenario_active_time_specialist_followup_expectations(
                expectations,
                tags=current_tags,
                text=text,
                active_reply_type=state.active_reply_type,
            )
            expectations = apply_booking_scenario_active_time_master_info_interrupt_expectations(
                expectations,
                original_tags=raw_tags,
                tags=current_tags,
                text=text,
                active_reply_type=state.active_reply_type,
            )
            expectations = apply_booking_scenario_active_name_time_availability_followup_expectations(
                expectations,
                original_tags=raw_tags,
                tags=current_tags,
                text=text,
                active_reply_type=state.active_reply_type,
            )
            normalized_turn["expect"] = expectations

            next_active_reply_type = advance_booking_scenario_pending_question_context(
                state.active_reply_type,
                tags=current_tags,
                expect=expectations,
            )
            next_partial_date_anchor_active = advance_booking_scenario_partial_date_anchor_context(
                state.partial_date_anchor_active,
                active_reply_type=next_active_reply_type,
                tags=current_tags,
                text=text,
                expect=expectations,
            )
            lowered_tags = _booking_scenario_coerce_turn_tags(current_tags)
            next_multi_service_clarify_active = advance_booking_scenario_multi_service_clarify_context(
                state.multi_service_clarify_active,
                tags=current_tags,
                expect=expectations,
            )
            next_active_management_tag = state.active_management_tag
            if "reschedule" in lowered_tags:
                next_active_management_tag = "reschedule"
            elif "check_booking" in lowered_tags:
                next_active_management_tag = "check_booking"

            state = BookingScenarioPostCoverageRepairState(
                active_reply_type=next_active_reply_type,
                partial_date_anchor_active=next_partial_date_anchor_active,
                multi_service_clarify_active=next_multi_service_clarify_active,
                active_management_tag=next_active_management_tag,
            )
            repaired_turns.append(normalized_turn)
        normalized_dialog["turns"] = repaired_turns
        repaired_dialogs.append(normalized_dialog)
    return repaired_dialogs


def merge_booking_scenario_expectations(
    tags: list[str],
    override: Any,
    *,
    text: str | None = None,
) -> dict[str, Any]:
    normalized_tags = [
        str(tag).strip().lower()
        for tag in tags
        if isinstance(tag, str) and str(tag).strip()
    ]
    tag_set = set(normalized_tags)
    expect = _default_booking_scenario_expect()
    for tag in normalized_tags:
        if tag in BOOKING_SCENARIO_EXPECT_INFO_SECTIONS:
            expect["info_sections"].extend(BOOKING_SCENARIO_EXPECT_INFO_SECTIONS[tag])
        if tag in BOOKING_SCENARIO_EXPECT_ACTION_BY_TAG and expect["action"] is None:
            expect["action"] = deepcopy(BOOKING_SCENARIO_EXPECT_ACTION_BY_TAG[tag])
        if tag in BOOKING_SCENARIO_EXPECT_REPLY_TYPE_BY_TAG and expect["reply_type"] is None:
            expect["reply_type"] = BOOKING_SCENARIO_EXPECT_REPLY_TYPE_BY_TAG[tag]
        if tag in BOOKING_SCENARIO_EXPECT_STATE_BY_TAG and expect["state"] is None:
            expect["state"] = BOOKING_SCENARIO_EXPECT_STATE_BY_TAG[tag]
        if tag in BOOKING_SCENARIO_EXPECT_META_ANY_BY_TAG:
            merged_meta_any = dict(expect.get("meta_any") or {})
            for key, values in BOOKING_SCENARIO_EXPECT_META_ANY_BY_TAG[tag].items():
                bucket = list(merged_meta_any.get(key) or [])
                for value in values:
                    if value not in bucket:
                        bucket.append(value)
                if bucket:
                    merged_meta_any[key] = bucket
            if merged_meta_any:
                expect["meta_any"] = merged_meta_any
        if tag in BOOKING_SCENARIO_EXPECT_TRACE_CONTAINS_BY_TAG:
            merged_trace = list(expect.get("trace_contains") or [])
            for entry in BOOKING_SCENARIO_EXPECT_TRACE_CONTAINS_BY_TAG[tag]:
                if entry not in merged_trace:
                    merged_trace.append(deepcopy(entry))
            if merged_trace:
                expect["trace_contains"] = merged_trace
    info_sections: list[str] = []
    for item in expect["info_sections"]:
        if isinstance(item, str):
            value = item.strip().lower()
            if value and value not in info_sections:
                info_sections.append(value)
    expect["info_sections"] = info_sections
    if isinstance(override, Mapping):
        override = sanitize_booking_scenario_expect_override_for_tags(
            override,
            tags=normalized_tags,
        )
        override = normalize_booking_scenario_expect_override(override)
        for key in ("action", "reply_type", "state", "expected_reply"):
            if override.get(key) is not None:
                expect[key] = deepcopy(override.get(key))
        extra_sections = override.get("info_sections") or []
        if isinstance(extra_sections, str):
            extra_sections = [extra_sections]
        for section in extra_sections:
            if section and section not in expect["info_sections"]:
                expect["info_sections"].append(section)
        if override.get("meta"):
            merged_meta = dict(expect.get("meta") or {})
            merged_meta.update(deepcopy(override.get("meta") or {}))
            expect["meta"] = merged_meta
        for key in ("meta_any", "meta_contains"):
            if override.get(key):
                merged_mapping = dict(expect.get(key) or {})
                for item_key, item_values in (override.get(key) or {}).items():
                    bucket = list(merged_mapping.get(item_key) or [])
                    for value in item_values:
                        if value not in bucket:
                            bucket.append(value)
                    if bucket:
                        merged_mapping[item_key] = bucket
                expect[key] = merged_mapping
        if override.get("trace_contains"):
            merged_trace = list(expect.get("trace_contains") or [])
            for entry in override.get("trace_contains") or []:
                if entry not in merged_trace:
                    merged_trace.append(deepcopy(entry))
            expect["trace_contains"] = merged_trace
    expect["state"] = sanitize_booking_scenario_expect_state_by_tags(
        normalized_tags,
        expect.get("state"),
    )
    expect["action"] = sanitize_booking_scenario_expect_action_by_tags(
        normalized_tags,
        expect.get("action"),
    )
    expect = _apply_service_choice_booking_collect_expectations(
        expect,
        tags=set(normalized_tags),
    )
    if expect.get("state") is None:
        expect["state"] = "bot_active"
    if "media" in tag_set:
        expect["expected_reply"] = None
    if not any(tag in BOOKING_SCENARIO_EXPECT_INFO_SECTIONS for tag in normalized_tags):
        expect["info_sections"] = []
    return apply_booking_scenario_pending_question_target_expectations(
        expect,
        tags=normalized_tags,
        text=text,
    )


def sanitize_booking_scenario_llm_turns(
    turns: list[dict[str, Any]],
    ctx: dict[str, str],
    rng: Any,
    *,
    service_candidates: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    normalized_service_candidates = tuple(
        service_candidates or _BOOKING_SCENARIO_DEFAULT_SERVICE_CANDIDATES
    )
    sanitized: list[dict[str, Any]] = []
    state = BookingScenarioPostCoverageRepairState()
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        normalized_turn = dict(turn)
        tags = list(normalized_turn.get("tags") or [])
        text = str(normalized_turn.get("text") or "").strip()
        kind = normalized_turn.get("kind") or "text"
        if kind != "media":
            kind = "text"
            if (
                not text
                or _booking_scenario_looks_like_assistant_turn(text)
                or not _booking_scenario_text_matches_tag_contract(text, tags)
            ):
                text = _booking_scenario_fallback_text_for_tags(tags, ctx)
        if not text:
            text = _booking_scenario_fallback_text_for_tags(tags, ctx)

        original_tags = list(tags)
        tags, malformed_check_booking_normalized = (
            booking_scenario_normalize_malformed_check_booking_tags(text, tags)
        )
        tags = booking_scenario_normalize_pending_question_tags(text, tags)
        tags = booking_scenario_normalize_stateful_booking_tags(
            text,
            tags,
            active_reply_type=state.active_reply_type,
        )
        tags, active_time_specialist_master_normalized = (
            booking_scenario_normalize_active_time_specialist_master_tags(
                text,
                tags,
                active_reply_type=state.active_reply_type,
            )
        )
        tags, active_name_master_info_normalized = (
            booking_scenario_normalize_active_name_master_info_tags(
                text,
                tags,
                active_reply_type=state.active_reply_type,
            )
        )
        tags, active_time_master_info_normalized = (
            booking_scenario_normalize_active_time_master_info_tags(
                text,
                tags,
                active_reply_type=state.active_reply_type,
            )
        )
        tags, booking_time_fill_normalized = booking_scenario_normalize_active_time_booking_fill_tags(
            text,
            tags,
            active_reply_type=state.active_reply_type,
        )
        tags, booking_requested_slot_normalized = (
            booking_scenario_normalize_booking_requested_slot_question_tags(
                text,
                tags,
                active_reply_type=state.active_reply_type,
            )
        )
        (
            tags,
            slot_constraint_requested_slot_normalized,
        ) = booking_scenario_normalize_slot_constraint_requested_slot_question_tags(
            text,
            tags,
            active_reply_type=state.active_reply_type,
        )
        (
            tags,
            slot_compare_requested_slot_normalized,
        ) = booking_scenario_normalize_slot_compare_requested_slot_question_tags(
            text,
            tags,
            active_reply_type=state.active_reply_type,
        )
        (
            tags,
            slot_compare_partial_date_constraint_normalized,
        ) = booking_scenario_normalize_slot_compare_partial_date_constraint_tags(
            text,
            tags,
            active_reply_type=state.active_reply_type,
        )
        tags, slot_constraint_answer_normalized = (
            booking_scenario_normalize_slot_constraint_answer_tags(
                text,
                tags,
                active_reply_type=state.active_reply_type,
            )
        )
        tags, partial_date_slot_constraint_normalized = (
            booking_scenario_normalize_partial_date_slot_constraint_tags(
                text,
                tags,
                active_reply_type=state.active_reply_type,
            )
        )
        tags, grounded_time_probe_normalized = booking_scenario_normalize_grounded_time_probe_tags(
            text,
            tags,
            active_reply_type=state.active_reply_type,
        )
        tags, slot_compare_exact_time_normalized = (
            booking_scenario_normalize_slot_compare_exact_time_fill_tags(
                text,
                tags,
                active_reply_type=state.active_reply_type,
            )
        )
        tags, grounded_partial_date_mixed_fill_normalized = (
            booking_scenario_normalize_grounded_partial_date_mixed_fill_tags(
                text,
                tags,
                active_reply_type=state.active_reply_type,
                partial_date_anchor_active=state.partial_date_anchor_active,
            )
        )
        tags, question_like_slot_constraint_normalized = (
            booking_scenario_normalize_question_like_slot_constraint_tags(
                text,
                tags,
                active_reply_type=state.active_reply_type,
            )
        )
        tags, partial_date_mixed_normalized = (
            booking_scenario_normalize_partial_date_mixed_question_tags(
                text,
                tags,
                active_reply_type=state.active_reply_type,
            )
        )
        tags, grounded_time_specialist_availability_normalized = (
            booking_scenario_normalize_grounded_time_specialist_availability_tags(
                text,
                tags,
                active_reply_type=state.active_reply_type,
            )
        )

        check_booking_followup_normalized = booking_scenario_looks_like_check_booking_followup(
            text,
            tags,
        )
        reschedule_followup_normalized = bool(
            state.active_management_tag == "reschedule"
            and booking_scenario_looks_like_reschedule_followup(text, tags)
        )
        if check_booking_followup_normalized:
            tags = rewrite_booking_scenario_check_booking_followup_tags(tags)
            normalized_turn["expect"] = booking_scenario_check_booking_followup_expect_override()
        elif reschedule_followup_normalized:
            tags = rewrite_booking_scenario_reschedule_followup_tags(tags)
            normalized_turn["expect"] = booking_scenario_reschedule_followup_expect_override()
        elif has_booking_scenario_orphan_pending_question_tags(
            tags,
            active_reply_type=state.active_reply_type,
        ):
            tags = rewrite_booking_scenario_orphan_pending_question_tags(tags)
            normalized_turn["expect"] = booking_scenario_orphan_pending_question_expect_override()
        elif active_time_specialist_master_normalized:
            normalized_turn["expect"] = (
                booking_scenario_orphan_pending_question_expect_override()
                if state.active_reply_type is None
                else {}
            )
        elif (
            malformed_check_booking_normalized
            or active_name_master_info_normalized
            or active_time_master_info_normalized
            or booking_time_fill_normalized
            or booking_requested_slot_normalized
            or slot_constraint_requested_slot_normalized
            or slot_compare_requested_slot_normalized
            or slot_compare_partial_date_constraint_normalized
            or slot_constraint_answer_normalized
            or grounded_time_probe_normalized
            or slot_compare_exact_time_normalized
            or grounded_partial_date_mixed_fill_normalized
            or question_like_slot_constraint_normalized
            or grounded_time_specialist_availability_normalized
        ):
            normalized_turn["expect"] = {}
        elif partial_date_slot_constraint_normalized or partial_date_mixed_normalized:
            normalized_turn["expect"] = booking_scenario_time_collect_expect_override()

        normalized_turn["kind"] = kind
        normalized_turn["text"] = text
        normalized_turn["tags"] = tags
        expectations = merge_booking_scenario_expectations(
            tags,
            normalized_turn.get("expect"),
            text=text,
        )
        expectations = apply_booking_scenario_multi_service_booking_clarify_expectations(
            expectations,
            tags=tags,
            text=text,
            service_candidates=normalized_service_candidates,
            ctx=ctx,
        )
        expectations = apply_booking_scenario_service_grounded_booking_expectations(
            expectations,
            tags=tags,
            text=text,
            service_candidates=normalized_service_candidates,
            ctx=ctx,
        )
        expectations = apply_booking_scenario_ambiguous_time_fill_expectations(
            expectations,
            tags=tags,
            text=text,
            active_reply_type=state.active_reply_type,
        )
        expectations = apply_booking_scenario_exact_time_fill_collect_expectations(
            expectations,
            tags=tags,
            text=text,
            active_reply_type=state.active_reply_type,
        )
        expectations = apply_booking_scenario_partial_date_fill_collect_expectations(
            expectations,
            tags=tags,
            text=text,
            active_reply_type=state.active_reply_type,
        )
        expectations = apply_booking_scenario_grounded_partial_date_daypart_fill_expectations(
            expectations,
            original_tags=original_tags,
            tags=tags,
            text=text,
            active_reply_type=state.active_reply_type,
            partial_date_anchor_active=state.partial_date_anchor_active,
        )
        expectations = clear_booking_scenario_multi_service_info_interrupt_followup_expectations(
            expectations,
            tags=tags,
            multi_service_clarify_active=state.multi_service_clarify_active,
        )
        expectations = apply_booking_scenario_active_pending_question_info_interrupt_expectations(
            expectations,
            tags=tags,
            active_reply_type=state.active_reply_type,
        )
        expectations = apply_booking_scenario_service_grounded_booking_progress_interrupt_expectations(
            expectations,
            tags=tags,
            text=text,
            service_candidates=normalized_service_candidates,
            ctx=ctx,
            active_reply_type=state.active_reply_type,
        )
        expectations = apply_booking_scenario_active_pending_question_cancel_interrupt_expectations(
            expectations,
            tags=tags,
            active_reply_type=state.active_reply_type,
        )
        expectations = apply_booking_scenario_active_time_specialist_followup_expectations(
            expectations,
            tags=tags,
            text=text,
            active_reply_type=state.active_reply_type,
        )
        expectations = apply_booking_scenario_pending_specialist_availability_followup_expectations(
            expectations,
            original_tags=original_tags,
            tags=tags,
            text=text,
            active_reply_type=state.active_reply_type,
        )
        expectations = (
            apply_booking_scenario_grounded_time_specialist_availability_transition_expectations(
                expectations,
                original_tags=original_tags,
                tags=tags,
                text=text,
                active_reply_type=state.active_reply_type,
            )
        )
        expectations = apply_booking_scenario_pending_master_info_interrupt_expectations(
            expectations,
            original_tags=original_tags,
            tags=tags,
            text=text,
            active_reply_type=state.active_reply_type,
        )
        expectations = apply_booking_scenario_active_name_master_info_interrupt_expectations(
            expectations,
            original_tags=original_tags,
            tags=tags,
            text=text,
            active_reply_type=state.active_reply_type,
        )
        expectations = apply_booking_scenario_active_time_master_info_interrupt_expectations(
            expectations,
            original_tags=original_tags,
            tags=tags,
            text=text,
            active_reply_type=state.active_reply_type,
        )
        expectations = apply_booking_scenario_active_name_time_availability_followup_expectations(
            expectations,
            original_tags=original_tags,
            tags=tags,
            text=text,
            active_reply_type=state.active_reply_type,
        )
        normalized_turn["expect"] = expectations

        next_active_reply_type = advance_booking_scenario_pending_question_context(
            state.active_reply_type,
            tags=tags,
            expect=expectations,
        )
        next_partial_date_anchor_active = advance_booking_scenario_partial_date_anchor_context(
            state.partial_date_anchor_active,
            active_reply_type=next_active_reply_type,
            tags=tags,
            text=text,
            expect=expectations,
        )
        next_multi_service_clarify_active = advance_booking_scenario_multi_service_clarify_context(
            state.multi_service_clarify_active,
            tags=tags,
            expect=expectations,
        )
        lowered_tags = _booking_scenario_coerce_turn_tags(tags)
        next_active_management_tag = state.active_management_tag
        if "reschedule" in lowered_tags:
            next_active_management_tag = "reschedule"
        elif "check_booking" in lowered_tags:
            next_active_management_tag = "check_booking"
        state = BookingScenarioPostCoverageRepairState(
            active_reply_type=next_active_reply_type,
            partial_date_anchor_active=next_partial_date_anchor_active,
            multi_service_clarify_active=next_multi_service_clarify_active,
            active_management_tag=next_active_management_tag,
        )
        sanitized.append(normalized_turn)
    return sanitized


__all__ = [
    "BookingScenarioPostCoverageRepairCallbacks",
    "BookingScenarioPostCoverageRepairDecision",
    "BookingScenarioPostCoverageRepairState",
    "booking_scenario_looks_like_ambiguous_time_fill",
    "booking_scenario_looks_like_explicit_time_fill",
    "booking_scenario_looks_like_generic_master_info_question",
    "booking_scenario_looks_like_grounded_partial_date_daypart_fill",
    "booking_scenario_looks_like_grounded_time_availability_probe",
    "booking_scenario_looks_like_grounded_time_specialist_availability_transition_question",
    "booking_scenario_looks_like_mixed_slot_question",
    "booking_scenario_looks_like_non_comparative_availability_question",
    "booking_scenario_looks_like_partial_date_availability_slot_constraint",
    "booking_scenario_looks_like_partial_date_fill_without_availability_query",
    "booking_scenario_looks_like_question_like_slot_constraint",
    "booking_scenario_looks_like_requested_slot_question_without_temporal_scope",
    "booking_scenario_check_booking_followup_expect_override",
    "booking_scenario_normalize_active_time_booking_fill_tags",
    "booking_scenario_normalize_booking_requested_slot_question_tags",
    "booking_scenario_normalize_grounded_partial_date_mixed_fill_tags",
    "booking_scenario_normalize_grounded_time_probe_tags",
    "booking_scenario_normalize_grounded_time_specialist_availability_tags",
    "booking_scenario_normalize_partial_date_mixed_question_tags",
    "booking_scenario_normalize_partial_date_slot_constraint_tags",
    "booking_scenario_normalize_question_like_slot_constraint_tags",
    "booking_scenario_normalize_slot_compare_exact_time_fill_tags",
    "booking_scenario_normalize_slot_compare_partial_date_constraint_tags",
    "booking_scenario_normalize_slot_compare_requested_slot_question_tags",
    "booking_scenario_normalize_slot_constraint_answer_tags",
    "booking_scenario_normalize_slot_constraint_requested_slot_question_tags",
    "booking_scenario_orphan_pending_question_expect_override",
    "booking_scenario_reschedule_followup_expect_override",
    "booking_scenario_time_collect_expect_override",
    "BOOKING_SCENARIO_EXPECT_INFO_SECTIONS",
    "BOOKING_SCENARIO_PENDING_QUESTION_TAGS",
    "BOOKING_SCENARIO_TARGETED_PENDING_QUESTION_TAGS",
    "advance_booking_scenario_multi_service_clarify_context",
    "advance_booking_scenario_partial_date_anchor_context",
    "advance_booking_scenario_pending_question_context",
    "apply_booking_scenario_active_pending_question_cancel_interrupt_expectations",
    "apply_booking_scenario_active_pending_question_info_interrupt_expectations",
    "apply_booking_scenario_active_name_master_info_interrupt_expectations",
    "apply_booking_scenario_active_name_time_availability_followup_expectations",
    "apply_booking_scenario_active_time_master_info_interrupt_expectations",
    "apply_booking_scenario_active_time_specialist_followup_expectations",
    "apply_booking_scenario_ambiguous_time_fill_expectations",
    "apply_booking_scenario_exact_time_fill_collect_expectations",
    "apply_booking_scenario_grounded_partial_date_daypart_fill_expectations",
    "apply_booking_scenario_grounded_time_specialist_availability_transition_expectations",
    "apply_booking_scenario_multi_service_booking_clarify_expectations",
    "apply_booking_scenario_partial_date_fill_collect_expectations",
    "apply_booking_scenario_pending_question_target_expectations",
    "apply_booking_scenario_pending_master_info_interrupt_expectations",
    "apply_booking_scenario_pending_specialist_availability_followup_expectations",
    "apply_booking_scenario_service_grounded_booking_expectations",
    "apply_booking_scenario_service_grounded_booking_progress_interrupt_expectations",
    "build_scenario_contract_status",
    "booking_scenario_expectation_has_contract_reason",
    "booking_scenario_looks_like_check_booking_followup",
    "booking_scenario_looks_like_generic_booking_request",
    "booking_scenario_looks_like_named_specialist_preference_availability_question",
    "booking_scenario_looks_like_reschedule_followup",
    "booking_scenario_looks_like_specialist_availability_followup_question",
    "booking_scenario_looks_like_standalone_specialist_booking_request",
    "booking_scenario_looks_like_multi_service_booking_request",
    "booking_scenario_normalize_active_name_master_info_tags",
    "booking_scenario_normalize_active_time_master_info_tags",
    "booking_scenario_normalize_active_time_specialist_master_tags",
    "booking_scenario_normalize_malformed_check_booking_tags",
    "booking_scenario_normalize_pending_question_tags",
    "booking_scenario_normalize_stateful_booking_tags",
    "booking_scenario_looks_like_service_grounded_booking",
    "clear_booking_scenario_multi_service_info_interrupt_followup_expectations",
    "collect_turn_tags",
    "extract_expectations",
    "infer_booking_scenario_pending_question_target",
    "is_weak_oracle_expectation",
    "looks_like_booking_scenario_specialist_reference",
    "merge_booking_scenario_expectations",
    "normalize_booking_scenario_expect_override",
    "parse_coverage_tokens",
    "repair_booking_scenario_post_coverage_dialogs",
    "sanitize_booking_scenario_llm_turns",
    "has_booking_scenario_orphan_pending_question_tags",
    "rewrite_booking_scenario_check_booking_followup_tags",
    "rewrite_booking_scenario_orphan_pending_question_tags",
    "rewrite_booking_scenario_reschedule_followup_tags",
    "sanitize_booking_scenario_expect_action_by_tags",
    "sanitize_booking_scenario_expect_override_for_tags",
    "sanitize_booking_scenario_expect_state_by_tags",
    "sanitize_expect_action_by_tags",
    "sanitize_expect_info_sections_by_tags",
    "sanitize_expect_state_by_tags",
]
