from datetime import datetime, timezone
from unittest.mock import Mock, patch

from app.services.state_machine import ConversationState
from app.services.state_service import (
    check_invariants,
    escalate_to_pending,
    manager_resolve,
    manager_take,
)


class TestEscalateToPending:
    @patch("app.services.state_service.TelegramService")
    @patch("app.services.state_service.get_telegram_credentials")
    def test_success_from_bot_active(self, mock_creds, mock_telegram_class):
        mock_creds.return_value = ("token", "chat_id")
        mock_telegram = Mock()
        mock_telegram.create_forum_topic.return_value = 12345
        mock_telegram_class.return_value = mock_telegram

        db = Mock()
        db.query.return_value.filter.return_value.first.return_value = Mock(name="Test User", phone="123")

        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value
        conversation.id = "conv-123"
        conversation.client_id = "client-123"
        conversation.user_id = "user-123"

        result = escalate_to_pending(db, conversation, "Help me", "intent", "human_request")

        assert result.ok is True
        assert result.value is not None
        assert conversation.state == ConversationState.PENDING.value
        assert conversation.telegram_topic_id == 12345

    def test_fails_from_wrong_state(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.MANAGER_ACTIVE.value

        result = escalate_to_pending(db, conversation, "Help", "intent")

        assert result.ok is False
        assert result.error_code == "invalid_state"

    @patch("app.services.state_service.get_telegram_credentials")
    def test_fails_without_telegram_credentials(self, mock_creds):
        mock_creds.return_value = (None, None)

        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value
        conversation.client_id = "client-123"

        result = escalate_to_pending(db, conversation, "Help", "intent")

        assert result.ok is False
        assert result.error_code == "no_telegram"


class TestManagerTake:
    def test_success_from_pending(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.PENDING.value
        conversation.id = "conv-123"

        handover = Mock()
        handover.status = "pending"

        result = manager_take(db, conversation, handover, "mgr-123", "Manager Name")

        assert result.ok is True
        assert conversation.state == ConversationState.MANAGER_ACTIVE.value
        assert handover.status == "active"
        assert handover.assigned_to_name == "Manager Name"

    def test_fails_from_wrong_state(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value

        handover = Mock()
        handover.status = "pending"

        result = manager_take(db, conversation, handover, "mgr-123", "Manager")

        assert result.ok is False
        assert result.error_code == "invalid_state"

    def test_fails_with_wrong_handover_status(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.PENDING.value

        handover = Mock()
        handover.status = "resolved"

        result = manager_take(db, conversation, handover, "mgr-123", "Manager")

        assert result.ok is False
        assert result.error_code == "invalid_handover"


class TestManagerResolve:
    def test_success_from_manager_active(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.MANAGER_ACTIVE.value
        conversation.id = "conv-123"

        handover = Mock()
        handover.status = "active"
        handover.created_at = datetime.now(timezone.utc)

        result = manager_resolve(db, conversation, handover, "mgr-123", "Manager Name")

        assert result.ok is True
        assert conversation.state == ConversationState.BOT_ACTIVE.value
        assert handover.status == "resolved"
        assert handover.resolved_by_name == "Manager Name"

    def test_success_from_pending(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.PENDING.value
        conversation.id = "conv-123"

        handover = Mock()
        handover.status = "pending"
        handover.created_at = datetime.now(timezone.utc)

        result = manager_resolve(db, conversation, handover, "mgr-123", "Manager")

        assert result.ok is True
        assert conversation.state == ConversationState.BOT_ACTIVE.value

    def test_fails_from_bot_active(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value

        handover = Mock()

        result = manager_resolve(db, conversation, handover, "mgr-123", "Manager")

        assert result.ok is False
        assert result.error_code == "invalid_state"


class TestCheckInvariants:
    def test_manager_active_without_topic(self):
        conversation = Mock()
        conversation.state = ConversationState.MANAGER_ACTIVE.value
        conversation.telegram_topic_id = None

        violations = check_invariants(conversation)

        assert "manager_active_no_topic" in violations

    def test_pending_without_topic(self):
        conversation = Mock()
        conversation.state = ConversationState.PENDING.value
        conversation.telegram_topic_id = None

        violations = check_invariants(conversation)

        assert "pending_no_topic" in violations

    def test_no_active_handover(self):
        conversation = Mock()
        conversation.state = ConversationState.PENDING.value
        conversation.telegram_topic_id = 123

        violations = check_invariants(conversation, handover=None)

        assert "no_active_handover" in violations

    def test_valid_state(self):
        conversation = Mock()
        conversation.state = ConversationState.PENDING.value
        conversation.telegram_topic_id = 123

        handover = Mock()
        handover.status = "pending"

        violations = check_invariants(conversation, handover)

        assert len(violations) == 0
