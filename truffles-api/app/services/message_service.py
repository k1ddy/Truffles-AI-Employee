from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Conversation, Message
from app.services.state_machine import ConversationState


def save_message(db: Session, conversation_id: UUID, client_id: UUID, role: str, content: str) -> Message:
    """Save message to database."""
    message = Message(
        conversation_id=conversation_id,
        client_id=client_id,
        role=role,
        content=content,
        created_at=datetime.now(timezone.utc),
    )
    db.add(message)
    db.flush()
    return message


def generate_bot_response(
    db: Session,
    conversation: Conversation,
    user_message: str,
    client_slug: str = "truffles",
) -> Optional[str]:
    """Generate bot response using AI."""
    # Bot responds in bot_active and pending states
    allowed_states = [ConversationState.BOT_ACTIVE.value, ConversationState.PENDING.value]
    if conversation.state not in allowed_states:
        return None

    from app.services.ai_service import generate_ai_response

    return generate_ai_response(
        db=db,
        client_id=conversation.client_id,
        client_slug=client_slug,
        conversation_id=conversation.id,
        user_message=user_message,
    )
