"""Shared pending-state runtime helpers and response defaults."""

from __future__ import annotations

from app.services.pack_runtime_service import get_system_lexicon_list

MSG_HANDOVER_DECLINED = (
    "Ок. Напишите, что именно интересует по салону: цена/запись/адрес/мастер/жалоба."
)
MSG_PENDING_ESCALATION = (
    "Я уже передал менеджеру — сообщения уходят администратору. "
    "Пока ждём ответ, могу помочь с услугами, ценами и записью."
)
MSG_PENDING_STATUS = (
    "Да, передал. Сейчас менеджер ещё не взял заявку. "
    "Пока ждём ответ, могу помочь с услугами, ценами и записью."
)
MSG_PENDING_WAIT = "Менеджер подключится. Пока ждём ответ, могу помочь с услугами, ценами и записью."
MSG_PENDING_SLA_PING = (
    "Напоминаю: менеджер ещё не подключился. "
    "Если всё актуально — напишите детали, я передам администратору."
)
MSG_PENDING_ACK = "Хорошо. Напишите, что именно нужно: цена/запись/адрес/мастер."
PENDING_SLA_PING_MINUTES = 15
PENDING_SLA_PING_SENT_KEY = "ping_sent_at"


def is_handover_status_question(text: str) -> bool:
    """Detect 'did you forward / when manager replies' questions in pending state."""
    if not text:
        return False

    normalized = text.strip().casefold()
    keywords = get_system_lexicon_list("handover_status_keywords")
    return bool(keywords) and any(keyword in normalized for keyword in keywords)


__all__ = [
    "MSG_HANDOVER_DECLINED",
    "MSG_PENDING_ACK",
    "MSG_PENDING_ESCALATION",
    "MSG_PENDING_SLA_PING",
    "MSG_PENDING_STATUS",
    "MSG_PENDING_WAIT",
    "PENDING_SLA_PING_MINUTES",
    "PENDING_SLA_PING_SENT_KEY",
    "is_handover_status_question",
]
