"""Shared active-path webhook primitives and routing-neutral defaults."""

from __future__ import annotations

from app.services.expected_reply_contract import (
    EXPECTED_REPLY_INTENT_CHOICE,
    EXPECTED_REPLY_NAME,
    EXPECTED_REPLY_PHONE,
    EXPECTED_REPLY_SERVICE,
    EXPECTED_REPLY_TIME,
)
from app.services.pack_runtime_service import get_system_anchor_groups, get_system_lexicon_list
from app.services.state_machine import ConversationState

MSG_EXPECTED_SERVICE_OFF_TOPIC = "Я могу помочь по услугам салона. Какая услуга интересует?"
MSG_AI_ERROR = "Извините, произошла ошибка. Попробуйте позже."
MSG_DELIVERY_FAILED = (
    "Извините, уведомление не доставилось из-за технической ошибки. Попробуйте позже."
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

INFO_INTENTS = {
    "pricing",
    "hours",
    "duration",
    "location",
    "parking",
    "promotions",
    "master",
    "contact",
}
INFO_SERVICE_DEPENDENT_INTENTS = {"pricing", "duration"}
INFO_NON_SERVICE_INTENTS = {"hours", "location", "parking", "promotions", "master", "contact"}
INFO_INTENT_PRIORITY_SERVICE = ("pricing", "duration", "location", "hours", "master")
INFO_INTENT_PRIORITY_GENERIC = ("location", "hours", "pricing", "duration", "master")

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
SESSION_MEMORY_SHORT_TOKENS = 4

INFO_ANCHOR_GROUPS: dict[str, list[tuple[str, ...]]] = {
    "pricing": get_system_anchor_groups("pricing"),
    "duration": get_system_anchor_groups("duration"),
    "hours": get_system_anchor_groups("hours"),
    "location": get_system_anchor_groups("location"),
}
QUESTION_WORD_PREFIXES = tuple(get_system_lexicon_list("question_word_prefixes"))

__all__ = [
    "BOOKING_CTA_SERVICE_INTENTS",
    "BOOKING_TIME_SERVICE_INTENTS",
    "ConversationState",
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
    "MSG_AI_ERROR",
    "MSG_BOOKING_ASK_DATETIME",
    "MSG_BOOKING_ASK_NAME",
    "MSG_BOOKING_PENDING_QUESTION_TIME_GUIDANCE",
    "MSG_BOOKING_SPECIALIST_AVAILABILITY_FOLLOWUP",
    "MSG_BOOKING_TIMEOUT_PENDING_QUESTION_TIME",
    "MSG_BOOKING_ASK_SERVICE",
    "MSG_BOOKING_CTA",
    "MSG_DELIVERY_FAILED",
    "MSG_EXPECTED_SERVICE_OFF_TOPIC",
    "QUESTION_WORD_PREFIXES",
    "SERVICE_CARRYOVER_TTL_MESSAGES",
    "SESSION_MEMORY_SHORT_TOKENS",
]
