"""Shared active-path webhook primitives and routing-neutral defaults."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.expected_reply_contract import (
    EXPECTED_REPLY_INTENT_CHOICE,
    EXPECTED_REPLY_NAME,
    EXPECTED_REPLY_PHONE,
    EXPECTED_REPLY_SERVICE,
    EXPECTED_REPLY_TIME,
)
from app.services.pack_runtime_service import get_system_anchor_groups, get_system_lexicon_list
from app.services.policy_snapshot_service import ROUTING_MATRIX_V1 as ROUTING_MATRIX
from app.services.state_machine import ConversationState

MSG_EXPECTED_SERVICE_OFF_TOPIC = "Я могу помочь по услугам салона. Какая услуга интересует?"
MSG_AI_ERROR = "Извините, произошла ошибка. Попробуйте позже."
MSG_DELIVERY_FAILED = (
    "Извините, уведомление не доставилось из-за технической ошибки. Попробуйте позже."
)
MSG_ESCALATED = (
    "Передал менеджеру — сообщения уходят администратору. Пока ждём ответ, могу помочь с услугами, ценами и записью. "
    "Если есть детали (услуга/время/имя), напишите — я передам."
)
MSG_BOOKING_ASK_SERVICE = (
    "На какую услугу хотите записаться? После этого сразу проверю свободное время."
)
MSG_BOOKING_ASK_DATETIME = "На какую дату и время вам удобно?"
MSG_BOOKING_PENDING_QUESTION_TIME_GUIDANCE = (
    "Зависит от того, как вам удобнее: можно выбрать утро, день или вечер. "
    "На какую дату и время вам удобно?"
)
MSG_BOOKING_SPECIALIST_AVAILABILITY_FOLLOWUP = (
    "Чтобы понять, кто из мастеров свободен, подскажите день или более точное время."
)
MSG_BOOKING_TIMEOUT_PENDING_QUESTION_TIME = (
    "Могу помочь подобрать свободное время. На какую дату и время вам удобно?"
)
MSG_BOOKING_ASK_NAME = "Отлично, время подходит. Как вас зовут?"
MSG_BOOKING_CTA = "Хотите записаться?"
LOW_CONFIDENCE_RETRY_WINDOW_MINUTES = 10
LOW_CONFIDENCE_MAX_RETRIES = 2
CLARIFY_MAX_ATTEMPTS = 2
QUIET_HOURS_NOTICE_TTL_MINUTES = 10
EVENING_GREETING_TTL_HOURS = 12
MSG_HANDOVER_CONFIRM = "Не уверен, что понял. Подключить менеджера? Ответьте 'да' или 'нет'."
MSG_LOW_CONFIDENCE_RETRY = "Уточните, пожалуйста: интересуют услуги/цены или запись/адрес?"
MSG_PENDING_LOW_CONFIDENCE = (
    "Я уже передал менеджеру — он скоро подключится. "
    "Пока ждём, уточните: услуги/цены или запись/адрес."
)
MSG_STYLE_REFERENCE_NEED_MEDIA = (
    "Да, конечно. Можем ориентироваться на фото/референс. Пришлите фото и кратко опишите запрос — "
    "я передам администратору для подтверждения."
)
QUIET_HOURS_NOTICE_KEY = "quiet_hours_notice"
EVENING_GREETING_KEY = "evening_greeting"

INFO_INTENTS = {
    "pricing",
    "hours",
    "duration",
    "prep_brows_lashes",
    "hygiene",
    "location",
    "parking",
    "promotions",
    "master",
    "contact",
}
INFO_SERVICE_DEPENDENT_INTENTS = {"pricing", "duration"}
INFO_NON_SERVICE_INTENTS = {
    "hours",
    "location",
    "parking",
    "promotions",
    "prep_brows_lashes",
    "hygiene",
    "master",
    "contact",
}
INFO_INTENT_PRIORITY_SERVICE = (
    "pricing",
    "duration",
    "location",
    "hours",
    "prep_brows_lashes",
    "hygiene",
    "master",
)
INFO_INTENT_PRIORITY_GENERIC = (
    "location",
    "hours",
    "pricing",
    "duration",
    "prep_brows_lashes",
    "hygiene",
    "master",
)

BOOKING_TIME_SERVICE_INTENTS = {
    "service_match",
    "service_not_found",
    "price_query",
    "price_manicure",
    "service_duration",
    "service_clarify",
    "duration_or_price_clarify",
}
BOOKING_CTA_SERVICE_INTENTS = BOOKING_TIME_SERVICE_INTENTS - {
    "service_not_found",
    "service_clarify",
    "duration_or_price_clarify",
}

SERVICE_CARRYOVER_TTL_MESSAGES = 4
CONSULT_CONTEXT_TTL_MESSAGES = 6
SESSION_MEMORY_SHORT_TOKENS = 4

INFO_ANCHOR_GROUPS: dict[str, list[tuple[str, ...]]] = {
    "pricing": get_system_anchor_groups("pricing"),
    "duration": get_system_anchor_groups("duration"),
    "hours": get_system_anchor_groups("hours"),
    "location": get_system_anchor_groups("location"),
}
QUESTION_WORD_PREFIXES = tuple(get_system_lexicon_list("question_word_prefixes"))
_CANONICAL_GATE_ACTIONS = {"collect", "fact", "handoff"}
_GATE_COLLECT_INTENTS = {
    "service_not_found",
    "service_clarify",
    "duration_or_price_clarify",
    "info_clarify",
}
_LEGACY_CANONICAL_SEMANTIC_FIELDS = frozenset(
    {
        "expected_reply_type",
        "expected_reply_reason",
        "pending_question_target",
        "active_question_relation",
        "semantic_contract",
        "semantic_frame",
    }
)


def _contains_any(normalized: str, keywords: list[str]) -> bool:
    return any(keyword in normalized for keyword in keywords)


def _combine_sidecar(primary: str, sidecar: str | None) -> str:
    if not sidecar:
        return primary
    return f"{sidecar}\n\n{primary}"


def _append_followup(primary: str, followup: str | None) -> str:
    if not followup:
        return primary
    return f"{primary}\n\n{followup}"


def _canonicalize_gate_metadata_action(
    action: str | None,
    *,
    intent: str | None = None,
) -> str | None:
    if action is None:
        return None
    if action in _CANONICAL_GATE_ACTIONS:
        return action
    if action == "escalate":
        return "handoff"
    if action == "reply":
        if intent in _GATE_COLLECT_INTENTS:
            return "collect"
        return "fact"
    return action


def _freeze_legacy_semantic_payload(
    payload: dict[str, Any] | None,
    *,
    fields: frozenset[str] = _LEGACY_CANONICAL_SEMANTIC_FIELDS,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    frozen: dict[str, Any] = {}
    for key, value in payload.items():
        if key in fields:
            if value is None:
                continue
            frozen[f"observer_{key}"] = deepcopy(value)
            continue
        frozen[key] = deepcopy(value)
    return frozen


def _observed_legacy_semantic_value(payload: dict[str, Any] | None, key: str) -> Any:
    if not isinstance(payload, dict):
        return None
    observer_key = f"observer_{key}"
    if observer_key in payload:
        return payload.get(observer_key)
    return payload.get(key)


def should_offer_low_confidence_retry(conversation: Any, now: datetime) -> bool:
    offered_at = getattr(conversation, "retry_offered_at", None)
    if not offered_at:
        return True

    if offered_at.tzinfo is None:
        offered_at = offered_at.replace(tzinfo=timezone.utc)

    return (now - offered_at) > timedelta(minutes=LOW_CONFIDENCE_RETRY_WINDOW_MINUTES)

__all__ = [
    "BOOKING_CTA_SERVICE_INTENTS",
    "BOOKING_TIME_SERVICE_INTENTS",
    "CLARIFY_MAX_ATTEMPTS",
    "CONSULT_CONTEXT_TTL_MESSAGES",
    "ConversationState",
    "EVENING_GREETING_KEY",
    "EVENING_GREETING_TTL_HOURS",
    "EXPECTED_REPLY_INTENT_CHOICE",
    "EXPECTED_REPLY_NAME",
    "EXPECTED_REPLY_PHONE",
    "EXPECTED_REPLY_SERVICE",
    "EXPECTED_REPLY_TIME",
    "INFO_ANCHOR_GROUPS",
    "INFO_INTENTS",
    "INFO_INTENT_PRIORITY_GENERIC",
    "INFO_INTENT_PRIORITY_SERVICE",
    "INFO_NON_SERVICE_INTENTS",
    "INFO_SERVICE_DEPENDENT_INTENTS",
    "LOW_CONFIDENCE_MAX_RETRIES",
    "LOW_CONFIDENCE_RETRY_WINDOW_MINUTES",
    "MSG_AI_ERROR",
    "MSG_BOOKING_ASK_DATETIME",
    "MSG_BOOKING_ASK_NAME",
    "MSG_BOOKING_PENDING_QUESTION_TIME_GUIDANCE",
    "MSG_BOOKING_SPECIALIST_AVAILABILITY_FOLLOWUP",
    "MSG_BOOKING_TIMEOUT_PENDING_QUESTION_TIME",
    "MSG_BOOKING_ASK_SERVICE",
    "MSG_BOOKING_CTA",
    "MSG_DELIVERY_FAILED",
    "MSG_ESCALATED",
    "MSG_EXPECTED_SERVICE_OFF_TOPIC",
    "MSG_HANDOVER_CONFIRM",
    "MSG_LOW_CONFIDENCE_RETRY",
    "MSG_PENDING_LOW_CONFIDENCE",
    "MSG_STYLE_REFERENCE_NEED_MEDIA",
    "QUESTION_WORD_PREFIXES",
    "QUIET_HOURS_NOTICE_KEY",
    "QUIET_HOURS_NOTICE_TTL_MINUTES",
    "ROUTING_MATRIX",
    "SERVICE_CARRYOVER_TTL_MESSAGES",
    "SESSION_MEMORY_SHORT_TOKENS",
    "_canonicalize_gate_metadata_action",
    "_append_followup",
    "_combine_sidecar",
    "_contains_any",
    "_freeze_legacy_semantic_payload",
    "_observed_legacy_semantic_value",
    "should_offer_low_confidence_retry",
]
