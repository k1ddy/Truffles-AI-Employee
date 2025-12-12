from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Conversation, User
from app.services.state_machine import ConversationState


def get_or_create_user(db: Session, client_id: UUID, remote_jid: str) -> User:
    """Find user by remote_jid or create new one."""
    user = db.query(User).filter(User.client_id == client_id, User.remote_jid == remote_jid).first()

    if not user:
        user = User(client_id=client_id, remote_jid=remote_jid, created_at=datetime.now(timezone.utc))
        db.add(user)
        db.flush()

    return user


def get_or_create_conversation(db: Session, client_id: UUID, user_id: UUID, channel: str) -> Conversation:
    """Find active conversation or create new one."""
    conversation = (
        db.query(Conversation)
        .filter(Conversation.client_id == client_id, Conversation.user_id == user_id, Conversation.status == "active")
        .first()
    )

    if not conversation:
        conversation = Conversation(
            client_id=client_id,
            user_id=user_id,
            channel=channel,
            status="active",
            started_at=datetime.now(timezone.utc),
            state=ConversationState.BOT_ACTIVE.value,
        )
        db.add(conversation)
        db.flush()

    return conversation


def update_conversation_state(db: Session, conversation: Conversation, new_state: ConversationState):
    """Update conversation state."""
    conversation.state = new_state.value
    conversation.last_message_at = datetime.now(timezone.utc)
    db.flush()
