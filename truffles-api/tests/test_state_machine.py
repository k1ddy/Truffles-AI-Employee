import pytest
from app.services.state_machine import (
    ConversationState,
    can_transition,
    transition,
    escalate,
    manager_take,
    manager_resolve,
    cancel_escalation,
    InvalidTransitionError,
)


class TestValidTransitions:
    def test_bot_active_to_pending(self):
        result = transition(ConversationState.BOT_ACTIVE, ConversationState.PENDING)
        assert result == ConversationState.PENDING

    def test_pending_to_manager_active(self):
        result = transition(ConversationState.PENDING, ConversationState.MANAGER_ACTIVE)
        assert result == ConversationState.MANAGER_ACTIVE

    def test_pending_to_bot_active(self):
        result = transition(ConversationState.PENDING, ConversationState.BOT_ACTIVE)
        assert result == ConversationState.BOT_ACTIVE

    def test_manager_active_to_bot_active(self):
        result = transition(ConversationState.MANAGER_ACTIVE, ConversationState.BOT_ACTIVE)
        assert result == ConversationState.BOT_ACTIVE


class TestInvalidTransitions:
    def test_bot_active_to_manager_active(self):
        with pytest.raises(InvalidTransitionError):
            transition(ConversationState.BOT_ACTIVE, ConversationState.MANAGER_ACTIVE)

    def test_manager_active_to_pending(self):
        with pytest.raises(InvalidTransitionError):
            transition(ConversationState.MANAGER_ACTIVE, ConversationState.PENDING)

    def test_same_state(self):
        with pytest.raises(InvalidTransitionError):
            transition(ConversationState.BOT_ACTIVE, ConversationState.BOT_ACTIVE)


class TestHelperFunctions:
    def test_escalate(self):
        result = escalate(ConversationState.BOT_ACTIVE)
        assert result == ConversationState.PENDING

    def test_escalate_from_pending_fails(self):
        with pytest.raises(InvalidTransitionError):
            escalate(ConversationState.PENDING)

    def test_manager_take(self):
        result = manager_take(ConversationState.PENDING)
        assert result == ConversationState.MANAGER_ACTIVE

    def test_manager_take_from_bot_active_fails(self):
        with pytest.raises(InvalidTransitionError):
            manager_take(ConversationState.BOT_ACTIVE)

    def test_manager_resolve(self):
        result = manager_resolve(ConversationState.MANAGER_ACTIVE)
        assert result == ConversationState.BOT_ACTIVE

    def test_cancel_escalation(self):
        result = cancel_escalation(ConversationState.PENDING)
        assert result == ConversationState.BOT_ACTIVE


class TestCanTransition:
    def test_valid_returns_true(self):
        assert can_transition(ConversationState.BOT_ACTIVE, ConversationState.PENDING) is True

    def test_invalid_returns_false(self):
        assert can_transition(ConversationState.BOT_ACTIVE, ConversationState.MANAGER_ACTIVE) is False
