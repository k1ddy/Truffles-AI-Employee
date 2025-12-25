from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

import re

from app.models import Conversation, Message
from app.services.ai_service import (
    classify_confirmation,
    is_acknowledgement_message,
    is_bot_status_question,
    is_greeting_message,
    is_low_signal_message,
    is_thanks_message,
    normalize_for_matching,
)
from app.services.result import Result
from app.services.state_machine import ConversationState


def save_message(
    db: Session,
    conversation_id: UUID,
    client_id: UUID,
    role: str,
    content: str,
    message_metadata: Optional[dict] = None,
) -> Message:
    """Save message to database."""
    message = Message(
        conversation_id=conversation_id,
        client_id=client_id,
        role=role,
        content=content,
        message_metadata=message_metadata or {},
        created_at=datetime.now(timezone.utc),
    )
    db.add(message)
    db.flush()
    return message


_HUMAN_REQUEST_PATTERNS = (
    re.compile(r"\b(менеджер|оператор|админ|администратор|человек|живой|консультант|поддержк|саппорт)\b"),
    re.compile(r"\b(позов|соедин|переключ)\w*\b"),
)


def _looks_like_human_request(text: str) -> bool:
    normalized = normalize_for_matching(text)
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in _HUMAN_REQUEST_PATTERNS)


def select_handover_user_message(
    db: Session,
    conversation_id: UUID,
    fallback_text: str,
    *,
    max_lookback: int = 8,
) -> str:
    """
    Pick the last meaningful user message for handover context.

    Skips meta requests (manager/operator), greetings, thanks, confirmations,
    and low-signal messages. Falls back to the current text if nothing better.
    """
    fallback_text = (fallback_text or "").strip()
    fallback_normalized = normalize_for_matching(fallback_text) if fallback_text else ""

    rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id, Message.role == "user")
        .order_by(Message.created_at.desc())
        .limit(max_lookback + 1)
        .all()
    )

    for msg in rows:
        text = (msg.content or "").strip()
        if not text:
            continue
        if fallback_normalized and normalize_for_matching(text) == fallback_normalized:
            continue
        if _looks_like_human_request(text):
            continue
        if is_greeting_message(text) or is_thanks_message(text):
            continue
        if is_acknowledgement_message(text) or is_bot_status_question(text):
            continue
        if classify_confirmation(text) in {"yes", "no"}:
            continue
        if is_low_signal_message(text):
            continue
        return text

    return fallback_text


def generate_bot_response(
    db: Session,
    conversation: Conversation,
    user_message: str,
    client_slug: str = "truffles",
    append_user_message: bool = True,
) -> Result[Tuple[Optional[str], str]]:
    """
    Generate bot response using AI.

    Returns Result with tuple:
    - (response_text, "high") — уверенный ответ
    - (None, "low_confidence") — нужна эскалация
    - (None, "bot_inactive") — бот не активен
    """
    # Bot responds in bot_active and pending states
    allowed_states = [ConversationState.BOT_ACTIVE.value, ConversationState.PENDING.value]
    if conversation.state not in allowed_states:
        return Result.success((None, "bot_inactive"))

    from app.services.ai_service import generate_ai_response

    return generate_ai_response(
        db=db,
        client_id=conversation.client_id,
        client_slug=client_slug,
        conversation_id=conversation.id,
        user_message=user_message,
        append_user_message=append_user_message,
    )
