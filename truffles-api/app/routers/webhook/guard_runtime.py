"""Narrow runtime owner for guard, mute, and timeout helper behavior."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ClientSettings

DEFAULT_MUTE_DURATION_FIRST_MINUTES = 30
DEFAULT_MUTE_DURATION_SECOND_HOURS = 24
SESSION_TIMEOUT_HOURS = 24
MSG_MUTED_TEMP = "Хорошо, напишите если понадоблюсь."
MSG_MUTED_LONG = "Понял! Если ответа от менеджеров долго нет — лучше звоните напрямую: +7 775 984 19 26"
MSG_REENGAGE_CONFIRM = "Вы просили не писать. Хотите снова общаться? Ответьте 'да' или 'нет'."
MSG_REENGAGE_DECLINED = "Хорошо, не буду писать. Если передумаете — напишите снова."
MSG_FACT_GUARD_CLARIFY = "Подскажите, пожалуйста, что именно вас интересует?"
MULTI_INTENT_LABELS = {
    "booking": "записи",
    "pricing": "цене",
    "duration": "длительности",
    "location": "адресу",
    "hours": "времени",
    "other": "другому вопросу",
}


def _coerce_batch_messages(message_text: str, batch_messages: list[str] | None) -> list[str]:
    raw_messages = batch_messages if batch_messages else ([message_text] if message_text else [])
    cleaned: list[str] = []
    for msg in raw_messages:
        if not msg:
            continue
        text = msg.strip()
        if text:
            cleaned.append(text)
    if not cleaned and message_text:
        fallback = message_text.strip()
        if fallback:
            cleaned.append(fallback)
    return cleaned


def get_mute_settings(db: Session, client_id) -> tuple[int, int]:
    settings = db.query(ClientSettings).filter(ClientSettings.client_id == client_id).first()

    if settings:
        mute_first = settings.mute_duration_first_minutes or DEFAULT_MUTE_DURATION_FIRST_MINUTES
        mute_second = settings.mute_duration_second_hours or DEFAULT_MUTE_DURATION_SECOND_HOURS
    else:
        mute_first = DEFAULT_MUTE_DURATION_FIRST_MINUTES
        mute_second = DEFAULT_MUTE_DURATION_SECOND_HOURS

    return mute_first, mute_second


__all__ = [
    "DEFAULT_MUTE_DURATION_FIRST_MINUTES",
    "DEFAULT_MUTE_DURATION_SECOND_HOURS",
    "MSG_FACT_GUARD_CLARIFY",
    "MSG_MUTED_LONG",
    "MSG_MUTED_TEMP",
    "MSG_REENGAGE_CONFIRM",
    "MSG_REENGAGE_DECLINED",
    "MULTI_INTENT_LABELS",
    "SESSION_TIMEOUT_HOURS",
    "_coerce_batch_messages",
    "get_mute_settings",
]
