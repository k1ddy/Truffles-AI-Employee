from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

import app.services.health_service as health_service
from app.services.health_service import check_and_alert_health, check_and_heal_conversations, get_system_health
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
    def test_returns_conversation_counts(self, monkeypatch):
        db = MagicMock()
        db.query.return_value.filter.return_value.count.side_effect = [10, 2, 1, 3, 1]
        monkeypatch.setattr(
            health_service,
            "build_minimum_data_status",
            lambda _db: {"version": "minimum_data_contract.v2"},
        )
        monkeypatch.setattr(
            health_service,
            "build_runtime_safety_snapshot",
            lambda: Mock(to_dict=lambda: {"status": "ok", "danger_flags": []}),
        )

        result = get_system_health(db)

        assert result["conversations"]["bot_active"] == 10
        assert result["conversations"]["pending"] == 2
        assert result["conversations"]["manager_active"] == 1
        assert result["handovers"]["pending"] == 3
        assert result["handovers"]["active"] == 1
        assert result["safety"]["status"] == "ok"
        assert result["minimum_data_contract"]["version"] == "minimum_data_contract.v2"

    def test_returns_checked_at_timestamp(self, monkeypatch):
        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 0
        monkeypatch.setattr(
            health_service,
            "build_minimum_data_status",
            lambda _db: {"version": "minimum_data_contract.v2"},
        )
        monkeypatch.setattr(
            health_service,
            "build_runtime_safety_snapshot",
            lambda: Mock(to_dict=lambda: {"status": "ok", "danger_flags": []}),
        )

        result = get_system_health(db)

        assert "checked_at" in result

    def test_returns_safety_danger_flags(self, monkeypatch):
        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 0
        monkeypatch.setattr(
            health_service,
            "build_minimum_data_status",
            lambda _db: {"version": "minimum_data_contract.v2"},
        )
        monkeypatch.setattr(
            health_service,
            "build_runtime_safety_snapshot",
            lambda: Mock(
                to_dict=lambda: {
                    "status": "danger",
                    "danger_flags": ["test_mode_outbox_worker_on_nonlocal_db"],
                }
            ),
        )

        result = get_system_health(db)

        assert result["safety"]["status"] == "danger"
        assert result["safety"]["danger_flags"] == ["test_mode_outbox_worker_on_nonlocal_db"]


def test_check_and_alert_health_ignores_failed_total_without_actionable_failures():
    checks = {
        "outbox": {
            "pending": 120,
            "failed_total": 3200,
            "failed": 3200,
            "failed_24h": 4,
            "thresholds": {
                "pending_warning": 500,
                "pending_critical": 1000,
                "failed_24h_warning": 30,
                "failed_24h_critical": 100,
            },
        }
    }

    alerts = check_and_alert_health(checks)

    assert alerts == []


def test_check_and_alert_health_critical_on_failed_24h_threshold():
    checks = {
        "outbox": {
            "pending": 120,
            "failed_total": 3200,
            "failed": 3200,
            "failed_24h": 140,
            "thresholds": {
                "pending_warning": 500,
                "pending_critical": 1000,
                "failed_24h_warning": 30,
                "failed_24h_critical": 100,
            },
        }
    }

    alerts = check_and_alert_health(checks)

    assert len(alerts) == 1
    assert "Outbox critical" in alerts[0]


def test_check_and_alert_health_critical_on_knowledge_activation_threshold():
    checks = {
        "knowledge_activation": {
            "status": "critical",
            "counts": {
                "queued": 2,
                "running": 1,
                "failed": 1,
                "stuck": 1,
            },
            "failed_24h": 2,
            "stale_running": 1,
            "oldest_queued_age_seconds": 1200,
        }
    }

    alerts = check_and_alert_health(checks)

    assert len(alerts) == 1
    assert "Knowledge activation critical" in alerts[0]
