from enum import Enum
from typing import Optional


class ConversationState(str, Enum):
    BOT_ACTIVE = "bot_active"
    PENDING = "pending"
    MANAGER_ACTIVE = "manager_active"


VALID_TRANSITIONS = {
    ConversationState.BOT_ACTIVE: [ConversationState.PENDING],
    ConversationState.PENDING: [ConversationState.BOT_ACTIVE, ConversationState.MANAGER_ACTIVE],
    ConversationState.MANAGER_ACTIVE: [ConversationState.BOT_ACTIVE],
}


class InvalidTransitionError(Exception):
    def __init__(self, from_state: ConversationState, to_state: ConversationState):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(f"Invalid transition: {from_state.value} -> {to_state.value}")


def can_transition(from_state: ConversationState, to_state: ConversationState) -> bool:
    """Check if transition is valid."""
    allowed = VALID_TRANSITIONS.get(from_state, [])
    return to_state in allowed


def transition(from_state: ConversationState, to_state: ConversationState) -> ConversationState:
    """Perform state transition. Raises InvalidTransitionError if not allowed."""
    if not can_transition(from_state, to_state):
        raise InvalidTransitionError(from_state, to_state)
    return to_state


def escalate(current_state: ConversationState) -> ConversationState:
    """Escalate conversation to pending (waiting for manager)."""
    return transition(current_state, ConversationState.PENDING)


def manager_take(current_state: ConversationState) -> ConversationState:
    """Manager takes the conversation."""
    return transition(current_state, ConversationState.MANAGER_ACTIVE)


def manager_resolve(current_state: ConversationState) -> ConversationState:
    """Manager resolves, return to bot."""
    return transition(current_state, ConversationState.BOT_ACTIVE)


def cancel_escalation(current_state: ConversationState) -> ConversationState:
    """Cancel pending escalation, return to bot."""
    return transition(current_state, ConversationState.BOT_ACTIVE)
