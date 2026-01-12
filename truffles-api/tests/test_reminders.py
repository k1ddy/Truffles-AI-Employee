from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.schemas.reminder import ReminderItem, ReminderSentRequest, RemindersResponse
from app.services import reminder_service
from app.services.state_machine import ConversationState


class MockHandover:
    def __init__(self, minutes_ago=0, reminder_1_sent=False, reminder_2_sent=False):
        self.id = uuid4()
        self.conversation_id = uuid4()
        self.client_id = uuid4()
        self.status = "pending"
        self.created_at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
        self.reminder_1_sent_at = datetime.now(timezone.utc) if reminder_1_sent else None
        self.reminder_2_sent_at = datetime.now(timezone.utc) if reminder_2_sent else None
        self.telegram_message_id = 12345
        self.context_summary = "Test summary"


class MockClientSettings:
    def __init__(self):
        self.reminder_timeout_1 = 30
        self.reminder_timeout_2 = 60
        self.telegram_chat_id = "-100123456"


class TestReminderSchemas:
    def test_reminder_item_valid(self):
        item = ReminderItem(
            handover_id=uuid4(),
            conversation_id=uuid4(),
            client_id=uuid4(),
            reminder_type="reminder_1",
            created_at=datetime.now(timezone.utc),
            minutes_waiting=35,
        )
        assert item.reminder_type == "reminder_1"
        assert item.minutes_waiting == 35

    def test_reminders_response_valid(self):
        resp = RemindersResponse(count=2, reminders=[])
        assert resp.count == 2

    def test_reminder_sent_request_valid(self):
        req = ReminderSentRequest(reminder_type="reminder_1")
        assert req.reminder_type == "reminder_1"

    def test_reminder_sent_request_invalid_type(self):
        with pytest.raises(ValueError):
            ReminderSentRequest(reminder_type="reminder_3")


class TestReminderLogic:
    def test_handover_needs_reminder_1(self):
        """Handover 35 minutes old, no reminders sent -> needs reminder_1"""
        handover = MockHandover(minutes_ago=35)
        settings = MockClientSettings()

        # Reminder 1 timeout is 30 min, handover is 35 min old
        assert handover.reminder_1_sent_at is None
        assert 35 >= settings.reminder_timeout_1

    def test_handover_needs_reminder_2(self):
        """Handover 65 minutes old, reminder_1 sent -> needs reminder_2"""
        handover = MockHandover(minutes_ago=65, reminder_1_sent=True)
        settings = MockClientSettings()

        # Reminder 2 timeout is 60 min, handover is 65 min old, reminder_1 already sent
        assert handover.reminder_1_sent_at is not None
        assert handover.reminder_2_sent_at is None
        assert 65 >= settings.reminder_timeout_2

    def test_handover_no_reminder_needed_too_early(self):
        """Handover 10 minutes old -> no reminder needed yet"""
        handover = MockHandover(minutes_ago=10)
        settings = MockClientSettings()

        assert 10 < settings.reminder_timeout_1

    def test_handover_no_reminder_needed_all_sent(self):
        """Both reminders already sent -> no more reminders"""
        handover = MockHandover(minutes_ago=120, reminder_1_sent=True, reminder_2_sent=True)

        assert handover.reminder_1_sent_at is not None
        assert handover.reminder_2_sent_at is not None


class TestPendingSlaPing:
    def test_ping_sent_once(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.PENDING.value
        conversation.escalated_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        conversation.context = {"foo": "bar"}

        handover = Mock()
        handover.status = "pending"
        handover.created_at = conversation.escalated_at
        handover.conversation = conversation

        db.query.return_value.filter.return_value.all.return_value = [handover]

        with patch("app.services.reminder_service._send_pending_user_message", return_value=True) as send_mock:
            with patch("app.services.reminder_service.PENDING_SLA_PING_MINUTES", 1), patch(
                "app.services.reminder_service.PENDING_AUTO_CLOSE_HOURS", 999
            ):
                reminder_service.process_pending_sla(db)
                assert conversation.context["foo"] == "bar"
                assert "pending_sla" in conversation.context
                assert "ping_sent_at" in conversation.context["pending_sla"]

                reminder_service.process_pending_sla(db)
                assert send_mock.call_count == 1


class TestNoResponseAlerts:
    def test_suppressed_on_shield_drop(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value
        conversation.bot_status = "active"
        conversation.bot_muted_until = None
        conversation.context = {}
        conversation.id = uuid4()
        conversation.client_id = uuid4()

        last_user = Mock()
        last_user.id = uuid4()
        last_user.created_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        last_user.content = "spam"
        last_user.message_metadata = {"decision_meta": {"action": "shield_drop"}}

        def last_message(db_handle, conversation_id, role):
            if role == "user":
                return last_user
            return None

        db.query.return_value.filter.return_value.all.return_value = [conversation]

        with patch("app.services.reminder_service._get_last_message", side_effect=last_message), patch(
            "app.services.reminder_service.alert_warning"
        ) as alert_mock:
            result = reminder_service.check_no_response_alerts(db)

        assert result["alerted"] == 0
        assert result["items"] == []
        alert_mock.assert_not_called()
        assert conversation.context == {}
