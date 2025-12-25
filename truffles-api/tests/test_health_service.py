from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

from app.services.health_service import check_and_heal_conversations, get_system_health
from app.services.state_machine import ConversationState


class TestCheckAndHealConversations:
    def test_heals_pending_without_topic(self):
        conversation = Mock()
        conversation.id = "conv-123"
        conversation.user_id = "user-123"
        conversation.state = ConversationState.PENDING.value
        conversation.telegram_topic_id = None
        conversation.retry_offered_at = datetime.now(timezone.utc)

        db = MagicMock()
        # Need 3 .all() calls: broken_no_topic, open_handovers (in loop), conversations_with_state
        db.query.return_value.filter.return_value.all.side_effect = [
            [conversation],  # broken_no_topic
            [],  # open_handovers for conv-123
            [],  # conversations_with_state
        ]
        db.query.return_value.filter.return_value.first.return_value = None

        result = check_and_heal_conversations(db)

        assert result["healed_count"] >= 1
        assert conversation.state == ConversationState.BOT_ACTIVE.value
        assert conversation.retry_offered_at is None

    def test_heals_manager_active_without_handover(self):
        conversation = Mock()
        conversation.id = "conv-456"
        conversation.state = ConversationState.MANAGER_ACTIVE.value
        conversation.telegram_topic_id = 123
        conversation.retry_offered_at = datetime.now(timezone.utc)

        db = MagicMock()
        db.query.return_value.filter.return_value.all.side_effect = [
            [],  # broken_no_topic
            [conversation],  # conversations_with_state
        ]
        db.query.return_value.filter.return_value.first.return_value = None  # no active handover

        result = check_and_heal_conversations(db)

        assert result["healed_count"] == 1
        assert conversation.state == ConversationState.BOT_ACTIVE.value
        assert conversation.retry_offered_at is None

    def test_restores_topic_from_user(self):
        conversation = Mock()
        conversation.id = "conv-789"
        conversation.user_id = "user-789"
        conversation.state = ConversationState.PENDING.value
        conversation.telegram_topic_id = None

        user = Mock()
        user.id = "user-789"
        user.telegram_topic_id = 456

        db = MagicMock()
        db.query.return_value.filter.return_value.all.side_effect = [
            [conversation],  # broken_no_topic
            [],  # conversations_with_state
        ]
        db.query.return_value.filter.return_value.first.return_value = user

        result = check_and_heal_conversations(db)

        assert result["healed_count"] >= 1
        assert conversation.state == ConversationState.PENDING.value
        assert conversation.telegram_topic_id == 456

    def test_no_healing_needed(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        result = check_and_heal_conversations(db)

        assert result["healed_count"] == 0
        assert len(result["details"]) == 0

    def test_returns_checked_at_timestamp(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        result = check_and_heal_conversations(db)

        assert "checked_at" in result


class TestGetSystemHealth:
    def test_returns_conversation_counts(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.count.side_effect = [10, 2, 1, 3, 1]

        result = get_system_health(db)

        assert result["conversations"]["bot_active"] == 10
        assert result["conversations"]["pending"] == 2
        assert result["conversations"]["manager_active"] == 1
        assert result["handovers"]["pending"] == 3
        assert result["handovers"]["active"] == 1

    def test_returns_checked_at_timestamp(self):
        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 0

        result = get_system_health(db)

        assert "checked_at" in result
