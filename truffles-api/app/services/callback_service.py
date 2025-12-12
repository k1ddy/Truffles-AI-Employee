from datetime import datetime, timezone
from typing import Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Conversation, Handover
from app.services.state_machine import (
    ConversationState,
    manager_resolve,
    manager_take,
)


class CallbackError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def handle_take(db: Session, conversation: Conversation, manager_id: str, manager_name: str = None) -> Tuple[str, str]:
    """Manager takes the conversation."""
    old_state = conversation.state

    if old_state != ConversationState.PENDING.value:
        raise CallbackError(f"Cannot take conversation in state '{old_state}'. Expected 'pending'.")

    new_state = manager_take(ConversationState(old_state))
    conversation.state = new_state.value
    conversation.human_operator_id = manager_id

    # Update handover if exists
    handover = (
        db.query(Handover).filter(Handover.conversation_id == conversation.id, Handover.status == "pending").first()
    )

    if handover:
        handover.status = "active"
        handover.assigned_to = manager_id
        handover.assigned_to_name = manager_name
        handover.first_response_at = datetime.now(timezone.utc)

    return old_state, new_state.value


def handle_resolve(
    db: Session, conversation: Conversation, manager_id: str, manager_name: str = None
) -> Tuple[str, str]:
    """Manager resolves the conversation."""
    old_state = conversation.state

    if old_state != ConversationState.MANAGER_ACTIVE.value:
        raise CallbackError(f"Cannot resolve conversation in state '{old_state}'. Expected 'manager_active'.")

    new_state = manager_resolve(ConversationState(old_state))
    conversation.state = new_state.value
    conversation.human_operator_id = None

    # Update handover if exists
    handover = (
        db.query(Handover).filter(Handover.conversation_id == conversation.id, Handover.status == "active").first()
    )

    if handover:
        handover.status = "resolved"
        handover.resolution_type = "solved"
        handover.resolved_at = datetime.now(timezone.utc)
        handover.resolved_by_id = manager_id
        handover.resolved_by_name = manager_name
        if handover.first_response_at:
            delta = datetime.now(timezone.utc) - handover.first_response_at
            handover.resolution_time_seconds = int(delta.total_seconds())

    return old_state, new_state.value


def handle_skip(db: Session, conversation: Conversation, manager_id: str, manager_name: str = None) -> Tuple[str, str]:
    """Manager skips the conversation. State doesn't change, for statistics only."""
    old_state = conversation.state

    # Update handover skipped_by list
    handover = (
        db.query(Handover).filter(Handover.conversation_id == conversation.id, Handover.status == "pending").first()
    )

    if handover:
        skipped = handover.skipped_by or []
        if manager_id not in skipped:
            skipped.append(manager_id)
            handover.skipped_by = skipped

    return old_state, old_state  # State unchanged


def handle_return(
    db: Session, conversation: Conversation, manager_id: str, manager_name: str = None
) -> Tuple[str, str]:
    """Manager returns conversation to bot without resolving."""
    old_state = conversation.state

    if old_state != ConversationState.MANAGER_ACTIVE.value:
        raise CallbackError(f"Cannot return conversation in state '{old_state}'. Expected 'manager_active'.")

    new_state = manager_resolve(ConversationState(old_state))  # Same transition as resolve
    conversation.state = new_state.value
    conversation.human_operator_id = None

    # Update handover if exists
    handover = (
        db.query(Handover).filter(Handover.conversation_id == conversation.id, Handover.status == "active").first()
    )

    if handover:
        handover.status = "bot_handling"  # Different from resolved

    return old_state, new_state.value


def process_callback(
    db: Session, conversation_id: UUID, action: str, manager_id: str, manager_name: str = None
) -> Tuple[str, str]:
    """Process manager callback action."""

    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()

    if not conversation:
        raise CallbackError(f"Conversation {conversation_id} not found")

    handlers = {
        "take": handle_take,
        "resolve": handle_resolve,
        "skip": handle_skip,
        "return": handle_return,
    }

    handler = handlers.get(action)
    if not handler:
        raise CallbackError(f"Unknown action: {action}")

    return handler(db, conversation, manager_id, manager_name)
