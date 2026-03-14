import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.models import Handover, Message, User
from app.routers.webhook import (
    LOW_CONFIDENCE_RETRY_WINDOW_MINUTES,
    is_handover_status_question,
    should_offer_low_confidence_retry,
    should_process_debounced_message,
)
from app.services.state_machine import ConversationState
from app.services.state_service import (
    check_invariants,
    escalate_to_pending,
    manager_reassign,
    manager_reopen,
    manager_resolve,
    manager_return,
    manager_take,
)


class TestEscalateToPending:
    @patch("app.services.state_service.TelegramService")
    @patch("app.services.state_service.resolve_telegram_routing")
    def test_success_from_bot_active(self, mock_routing, mock_telegram_class):
        mock_routing.return_value = {"bot_token": "token", "chat_id": "chat_id"}
        mock_telegram = Mock()
        mock_telegram.create_forum_topic.return_value = 12345
        mock_telegram_class.return_value = mock_telegram

        db = Mock()
        user = Mock(name="Test User", phone="123")
        user.telegram_topic_id = None
        user_query = Mock()
        user_query.filter.return_value = user_query
        user_query.first.return_value = user
        handover_query = Mock()
        handover_query.filter.return_value = handover_query
        handover_query.order_by.return_value = handover_query
        handover_query.first.return_value = None

        def query_side_effect(model):
            if model is User:
                return user_query
            if model is Handover:
                return handover_query
            return Mock()

        db.query.side_effect = query_side_effect

        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value
        conversation.id = "conv-123"
        conversation.client_id = "client-123"
        conversation.user_id = "user-123"
        conversation.telegram_topic_id = None
        conversation.retry_offered_at = datetime.now(timezone.utc)

        result = escalate_to_pending(db, conversation, "Help me", "intent", "human_request")

        assert result.ok is True
        assert result.value is not None
        assert conversation.state == ConversationState.PENDING.value
        assert conversation.telegram_topic_id == 12345
        assert conversation.retry_offered_at is None

    @patch("app.services.state_service.TelegramService")
    @patch("app.services.state_service.resolve_telegram_routing")
    def test_handover_dedupe_reopens_recent_resolved(self, mock_routing, mock_telegram_class):
        mock_routing.return_value = {"bot_token": "token", "chat_id": "chat_id"}
        mock_telegram = Mock()
        mock_telegram.create_forum_topic.return_value = 12345
        mock_telegram_class.return_value = mock_telegram

        db = Mock()
        user = Mock(name="Test User", phone="123")
        user.telegram_topic_id = None
        user_query = Mock()
        user_query.filter.return_value = user_query
        user_query.first.return_value = user

        now = datetime.now(timezone.utc)
        handover = SimpleNamespace(
            status="resolved",
            trigger_type="intent",
            trigger_value="old",
            user_message="old",
            created_at=now - timedelta(days=1),
            resolved_at=now - timedelta(hours=2),
            resolved_by_id="mgr-1",
            resolved_by_name="Manager",
            resolution_time_seconds=3600,
            resolution_type="solved",
            resolution_notes="done",
            manager_response="ok",
            manager_id="mgr-1",
            assigned_to="mgr-1",
            assigned_to_name="Manager",
            telegram_message_id=111,
            reminder_1_sent_at=now - timedelta(hours=3),
            reminder_2_sent_at=now - timedelta(hours=2),
            skipped_by=["bot"],
            context_summary="old summary",
            channel_ref="jid",
        )
        handover_query = Mock()
        handover_query.filter.return_value = handover_query
        handover_query.order_by.return_value = handover_query
        handover_query.first.return_value = handover

        def query_side_effect(model):
            if model is User:
                return user_query
            if model is Handover:
                return handover_query
            return Mock()

        db.query.side_effect = query_side_effect

        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value
        conversation.id = "conv-123"
        conversation.client_id = "client-123"
        conversation.user_id = "user-123"
        conversation.telegram_topic_id = None
        conversation.retry_offered_at = datetime.now(timezone.utc)

        result = escalate_to_pending(db, conversation, "Help me", "intent", "human_request")

        assert result.ok is True
        assert result.value is handover
        assert conversation.state == ConversationState.PENDING.value
        assert handover.status == "pending"
        assert handover.resolved_at is None
        assert handover.assigned_to is None
        assert handover.assigned_to_name is None
        assert handover.resolution_time_seconds is None
        assert handover.created_at >= now
        assert getattr(handover, "_reopened", False) is True
        db.add.assert_not_called()

    @patch("app.services.state_service.TelegramService")
    @patch("app.services.state_service.resolve_telegram_routing")
    def test_handover_meta_binds_media_contract_from_message(self, mock_routing, mock_telegram_class):
        mock_routing.return_value = {"bot_token": "token", "chat_id": "chat_id"}
        mock_telegram = Mock()
        mock_telegram.create_forum_topic.return_value = 12345
        mock_telegram_class.return_value = mock_telegram

        db = Mock()
        user = Mock(name="Test User", phone="123")
        user.telegram_topic_id = None
        user_query = Mock()
        user_query.filter.return_value = user_query
        user_query.first.return_value = user

        trigger_message = SimpleNamespace(
            id="msg-db-id",
            message_id="msg-inbound-1",
            message_metadata={
                "media": {
                    "media_type": "photo",
                    "storage_path": "/tmp/photo.jpg",
                    "public_url": "https://example.com/photo.jpg",
                    "sha256": "abc123",
                }
            },
        )
        message_query = Mock()
        message_query.filter.return_value = message_query
        message_query.order_by.return_value = message_query
        message_query.limit.return_value = message_query
        message_query.first.return_value = trigger_message
        message_query.all.return_value = [trigger_message]

        handover_query = Mock()
        handover_query.filter.return_value = handover_query
        handover_query.order_by.return_value = handover_query
        handover_query.first.return_value = None

        def query_side_effect(model):
            if model is User:
                return user_query
            if model is Message:
                return message_query
            if model is Handover:
                return handover_query
            return Mock()

        db.query.side_effect = query_side_effect

        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value
        conversation.id = "conv-123"
        conversation.client_id = "client-123"
        conversation.user_id = "user-123"
        conversation.telegram_topic_id = None
        conversation.retry_offered_at = datetime.now(timezone.utc)
        conversation.context = {}

        result = escalate_to_pending(db, conversation, "Help me", "intent", "human_request")

        assert result.ok is True
        assert isinstance(result.value.meta, dict)
        contract = result.value.meta.get("media_handoff_contract") or {}
        assert contract.get("required") is True
        assert contract.get("bound") is True
        assert contract.get("media_refs_count") == 1
        media_refs = result.value.meta.get("media_refs") or []
        assert media_refs and media_refs[0].get("source") == "message_metadata"
        decision_meta = trigger_message.message_metadata.get("decision_meta") or {}
        assert decision_meta.get("media_handoff_required") is True
        assert decision_meta.get("media_handoff_bound") is True
        assert decision_meta.get("media_handoff_refs_count") == 1
        trace = conversation.context.get("decision_trace") or []
        assert any(item.get("stage") == "media_handoff_contract" for item in trace if isinstance(item, dict))

    @patch("app.services.state_service.TelegramService")
    @patch("app.services.state_service.resolve_telegram_routing")
    def test_handover_meta_binds_media_contract_from_style_pending(self, mock_routing, mock_telegram_class):
        mock_routing.return_value = {"bot_token": "token", "chat_id": "chat_id"}
        mock_telegram = Mock()
        mock_telegram.create_forum_topic.return_value = 12345
        mock_telegram_class.return_value = mock_telegram

        db = Mock()
        user = Mock(name="Test User", phone="123")
        user.telegram_topic_id = None
        user_query = Mock()
        user_query.filter.return_value = user_query
        user_query.first.return_value = user

        trigger_message = SimpleNamespace(
            id="msg-db-id",
            message_id="msg-inbound-2",
            message_metadata={},
        )
        message_query = Mock()
        message_query.filter.return_value = message_query
        message_query.order_by.return_value = message_query
        message_query.limit.return_value = message_query
        message_query.first.return_value = trigger_message
        message_query.all.return_value = [trigger_message]

        handover_query = Mock()
        handover_query.filter.return_value = handover_query
        handover_query.order_by.return_value = handover_query
        handover_query.first.return_value = None

        def query_side_effect(model):
            if model is User:
                return user_query
            if model is Message:
                return message_query
            if model is Handover:
                return handover_query
            return Mock()

        db.query.side_effect = query_side_effect

        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value
        conversation.id = "conv-123"
        conversation.client_id = "client-123"
        conversation.user_id = "user-123"
        conversation.telegram_topic_id = None
        conversation.retry_offered_at = None
        conversation.context = {
            "style_reference_pending": {
                "reason": "photo_only",
                "media": {
                    "media_type": "photo",
                    "url": "https://provider.example/raw.jpg",
                },
                "storage_path": "/tmp/stored.jpg",
                "public_url": "https://example.com/stored.jpg",
                "public_url_expires_at": "2026-02-17T00:00:00+00:00",
                "sha256": "style-sha",
            }
        }

        result = escalate_to_pending(db, conversation, "Help me", "intent", "human_request")

        assert result.ok is True
        assert isinstance(result.value.meta, dict)
        contract = result.value.meta.get("media_handoff_contract") or {}
        assert contract.get("required") is True
        assert contract.get("bound") is True
        media_refs = result.value.meta.get("media_refs") or []
        assert media_refs and media_refs[0].get("source") == "style_reference_pending"
        assert media_refs[0].get("storage_path") == "/tmp/stored.jpg"
        decision_meta = trigger_message.message_metadata.get("decision_meta") or {}
        assert decision_meta.get("media_handoff_bound") is True
        assert decision_meta.get("media_handoff_refs_count") == 1

    @patch("app.services.state_service.TelegramService")
    @patch("app.services.state_service.resolve_telegram_routing")
    def test_handover_meta_binds_media_contract_from_recent_media_history(
        self, mock_routing, mock_telegram_class
    ):
        mock_routing.return_value = {"bot_token": "token", "chat_id": "chat_id"}
        mock_telegram = Mock()
        mock_telegram.create_forum_topic.return_value = 12345
        mock_telegram_class.return_value = mock_telegram

        db = Mock()
        user = Mock(name="Test User", phone="123")
        user.telegram_topic_id = None
        user_query = Mock()
        user_query.filter.return_value = user_query
        user_query.first.return_value = user

        trigger_message = SimpleNamespace(
            id="msg-db-id-trigger",
            message_id="msg-inbound-trigger",
            message_metadata={},
            created_at=datetime.now(timezone.utc),
        )
        recent_media_message = SimpleNamespace(
            id="msg-db-id-media",
            message_id="msg-inbound-media",
            message_metadata={
                "media": {
                    "media_type": "photo",
                    "storage_path": "/tmp/recent-photo.jpg",
                    "public_url": "https://example.com/recent-photo.jpg",
                    "sha256": "recent-sha",
                }
            },
            created_at=datetime.now(timezone.utc),
        )
        message_query = Mock()
        message_query.filter.return_value = message_query
        message_query.order_by.return_value = message_query
        message_query.limit.return_value = message_query
        message_query.first.return_value = trigger_message
        message_query.all.return_value = [trigger_message, recent_media_message]

        handover_query = Mock()
        handover_query.filter.return_value = handover_query
        handover_query.order_by.return_value = handover_query
        handover_query.first.return_value = None

        def query_side_effect(model):
            if model is User:
                return user_query
            if model is Message:
                return message_query
            if model is Handover:
                return handover_query
            return Mock()

        db.query.side_effect = query_side_effect

        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value
        conversation.id = "conv-123"
        conversation.client_id = "client-123"
        conversation.user_id = "user-123"
        conversation.telegram_topic_id = None
        conversation.retry_offered_at = None
        conversation.context = {}

        result = escalate_to_pending(db, conversation, "Передайте менеджеру", "intent", "human_request")

        assert result.ok is True
        assert isinstance(result.value.meta, dict)
        contract = result.value.meta.get("media_handoff_contract") or {}
        assert contract.get("required") is True
        assert contract.get("bound") is True
        media_refs = result.value.meta.get("media_refs") or []
        assert media_refs
        assert media_refs[0].get("source") == "recent_message_history"
        assert media_refs[0].get("public_url") == "https://example.com/recent-photo.jpg"

    @patch("app.services.state_service.TelegramService")
    @patch("app.services.state_service.resolve_telegram_routing")
    def test_handover_context_summary_and_messages_saved(self, mock_routing, mock_telegram_class):
        mock_routing.return_value = {"bot_token": "token", "chat_id": "chat_id"}
        mock_telegram = Mock()
        mock_telegram.create_forum_topic.return_value = 12345
        mock_telegram_class.return_value = mock_telegram

        db = Mock()
        user = Mock(name="Test User", phone="77015705555")
        user.telegram_topic_id = None
        user.remote_jid = "77015705555@s.whatsapp.net"
        user_query = Mock()
        user_query.filter.return_value = user_query
        user_query.first.return_value = user

        base_time = datetime.now(timezone.utc)
        history_user = SimpleNamespace(
            id="msg-1",
            message_id="inbound-1",
            role="user",
            content="Нужен маникюр к Айгерим завтра в 12:00",
            created_at=base_time - timedelta(minutes=2),
            message_metadata={},
        )
        history_assistant = SimpleNamespace(
            id="msg-2",
            message_id=None,
            role="assistant",
            content="Свободно у Айгерим в 12:00 и 14:00. Какое время бронируем?",
            created_at=base_time - timedelta(minutes=1),
            message_metadata={},
        )
        trigger_message = SimpleNamespace(
            id="msg-3",
            message_id="inbound-2",
            role="user",
            content="Бронируй на 12:00 и передай менеджеру фото референса",
            created_at=base_time,
            message_metadata={},
        )
        message_query = Mock()
        message_query.filter.return_value = message_query
        message_query.order_by.return_value = message_query
        message_query.limit.return_value = message_query
        message_query.first.return_value = trigger_message
        message_query.all.return_value = [history_user, history_assistant, trigger_message]

        handover_query = Mock()
        handover_query.filter.return_value = handover_query
        handover_query.order_by.return_value = handover_query
        handover_query.first.return_value = None

        def query_side_effect(model):
            if model is User:
                return user_query
            if model is Message:
                return message_query
            if model is Handover:
                return handover_query
            return Mock()

        db.query.side_effect = query_side_effect

        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value
        conversation.id = "conv-123"
        conversation.client_id = "client-123"
        conversation.user_id = "user-123"
        conversation.telegram_topic_id = None
        conversation.retry_offered_at = None
        conversation.context = {}

        result = escalate_to_pending(
            db,
            conversation,
            "Бронируй и передай менеджеру",
            "intent",
            "human_request",
        )

        assert result.ok is True
        handover = result.value
        assert isinstance(handover.context_summary, str)
        assert "client: Нужен маникюр к Айгерим завтра в 12:00" in handover.context_summary
        assert "assistant: Свободно у Айгерим в 12:00 и 14:00." in handover.context_summary
        assert isinstance(handover.messages, list)
        assert len(handover.messages) == 3
        assert handover.messages[0]["role"] == "user"
        assert handover.messages[1]["role"] == "assistant"
        assert handover.messages[2]["message_id"] == "inbound-2"

    def test_fails_from_wrong_state(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.MANAGER_ACTIVE.value

        result = escalate_to_pending(db, conversation, "Help", "intent")

        assert result.ok is False
        assert result.error_code == "invalid_state"

    @patch("app.services.state_service.resolve_telegram_routing")
    def test_fails_without_telegram_credentials(self, mock_routing):
        mock_routing.return_value = {"bot_token": None, "chat_id": None}

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
        handover.first_response_at = None

        result = manager_take(db, conversation, handover, "mgr-123", "Manager Name")

        assert result.ok is True
        assert conversation.state == ConversationState.MANAGER_ACTIVE.value
        assert handover.status == "active"
        assert handover.assigned_to_name == "Manager Name"
        assert handover.first_response_at is None

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
        conversation.retry_offered_at = datetime.now(timezone.utc)

        handover = Mock()
        handover.status = "active"
        handover.created_at = datetime.now(timezone.utc)

        result = manager_resolve(db, conversation, handover, "mgr-123", "Manager Name")

        assert result.ok is True
        assert conversation.state == ConversationState.BOT_ACTIVE.value
        assert conversation.retry_offered_at is None
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

    def test_preserve_context_restores_pending_resume_snapshot(self):
        db = Mock()
        now = datetime.now(timezone.utc)
        conversation = Mock()
        conversation.state = ConversationState.MANAGER_ACTIVE.value
        conversation.id = "conv-123"
        conversation.bot_muted_until = now
        conversation.no_count = 3
        conversation.retry_offered_at = now
        conversation.context = {
            "simulation": {"mode": True, "id": "sim-1"},
            "decision_trace": [{"stage": "seed"}],
            "pending_sla": {"ping_sent_at": now.isoformat()},
            "handover_confirmation": {"required": True},
            "pending_resume": {
                "context_manager": {
                    "current_goal": "booking",
                    "canonical_dialog_state": {
                        "owner_id": "context_manager.dialog_state.v1",
                        "version": "v1",
                        "interaction_state": {
                            "resume_slot": "datetime",
                            "interaction_target": "time",
                            "interaction_relation": "ask_about_requested_slot",
                            "interaction_owner": "llm_policy_core:ask_about_requested_slot",
                            "grounded_referents": {"service": "Педикюр"},
                        },
                    },
                },
                "expected_reply_type": "time",
                "expected_reply_reason": "booking_time_availability_followup",
                "intent_queue": ["booking"],
                "booking": {"active": True, "service": "Педикюр", "datetime": "послезавтра"},
                "session_memory": {
                    "active_goal": "booking",
                    "interaction_state": {
                        "resume_slot": "datetime",
                        "interaction_target": "time",
                        "interaction_relation": "ask_about_requested_slot",
                        "interaction_owner": "llm_policy_core:ask_about_requested_slot",
                    },
                },
                "last_service_hint": "Педикюр",
                "last_service_hint_at": "2026-02-18T00:00:00+00:00",
            },
        }

        handover = Mock()
        handover.status = "active"
        handover.created_at = now - timedelta(minutes=5)

        result = manager_resolve(
            db,
            conversation,
            handover,
            "mgr-123",
            "Manager Name",
            preserve_context=True,
        )

        assert result.ok is True
        assert conversation.state == ConversationState.BOT_ACTIVE.value
        ctx = conversation.context
        assert ctx.get("pending_resume") is None
        assert ctx.get("pending_sla") is None
        assert ctx.get("handover_confirmation") is None
        assert ctx.get("context_manager", {}).get("current_goal") == "booking"
        assert (
            ctx.get("context_manager", {})
            .get("canonical_dialog_state", {})
            .get("interaction_state", {})
            .get("interaction_target")
            == "time"
        )
        assert ctx.get("expected_reply_type") == "time"
        assert ctx.get("expected_reply_reason") == "booking_time_availability_followup"
        assert ctx.get("intent_queue") == ["booking"]
        assert ctx.get("booking", {}).get("datetime") == "послезавтра"
        assert ctx.get("session_memory", {}).get("active_goal") == "booking"
        assert (
            ctx.get("session_memory", {})
            .get("interaction_state", {})
            .get("interaction_owner")
            == "llm_policy_core:ask_about_requested_slot"
        )
        assert isinstance(ctx.get("session_memory", {}).get("last_updated_at"), str)
        assert ctx.get("last_service_hint") == "Педикюр"
        assert ctx.get("last_service_hint_at") == "2026-02-18T00:00:00+00:00"
        assert ctx.get("re_entry_required", {}).get("required") is True
        assert ctx.get("re_entry_required", {}).get("reason") == "pending_resume"
        assert ctx.get("simulation", {}).get("id") == "sim-1"
        assert ctx.get("decision_trace")[0].get("stage") == "seed"

    def test_fails_from_bot_active(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value

        handover = Mock()

        result = manager_resolve(db, conversation, handover, "mgr-123", "Manager")

        assert result.ok is False
        assert result.error_code == "invalid_state"


class TestManagerReassign:
    def test_success_from_manager_active(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.MANAGER_ACTIVE.value
        conversation.id = "conv-123"

        handover = Mock()
        handover.status = "active"
        handover.assigned_to = "mgr-old"
        handover.assigned_to_name = "Old Manager"

        result = manager_reassign(
            db,
            conversation,
            handover,
            manager_id="mgr-new",
            manager_name="New Manager",
        )

        assert result.ok is True
        assert handover.assigned_to == "mgr-new"
        assert handover.assigned_to_name == "New Manager"

    def test_fails_from_pending(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.PENDING.value

        handover = Mock()
        handover.status = "pending"

        result = manager_reassign(
            db,
            conversation,
            handover,
            manager_id="mgr-new",
            manager_name="New Manager",
        )

        assert result.ok is False
        assert result.error_code == "invalid_state"


class TestManagerReturn:
    def test_success_from_manager_active(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.MANAGER_ACTIVE.value
        conversation.id = "conv-123"
        conversation.retry_offered_at = datetime.now(timezone.utc)
        conversation.context = {"keep": True}

        handover = Mock()
        handover.status = "active"
        handover.created_at = datetime.now(timezone.utc)
        handover.resolved_at = datetime.now(timezone.utc)
        handover.resolved_by_name = "Old Manager"
        handover.resolution_notes = "old"
        handover.assigned_to = "mgr-123"
        handover.assigned_to_name = "Old Manager"

        result = manager_return(db, conversation, handover, "mgr-123", "Manager Name")

        assert result.ok is True
        assert conversation.state == ConversationState.BOT_ACTIVE.value
        assert conversation.retry_offered_at is None
        assert handover.status == "bot_handling"
        assert handover.resolved_at is None
        assert handover.resolved_by_name is None
        assert handover.resolution_notes is None
        assert handover.assigned_to is None
        assert handover.assigned_to_name is None

    def test_success_from_pending(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.PENDING.value
        conversation.id = "conv-123"

        handover = Mock()
        handover.status = "pending"

        result = manager_return(db, conversation, handover, "mgr-123", "Manager")

        assert result.ok is True
        assert conversation.state == ConversationState.BOT_ACTIVE.value
        assert handover.status == "bot_handling"

    def test_preserve_context_restores_pending_resume_snapshot(self):
        db = Mock()
        now = datetime.now(timezone.utc)
        conversation = Mock()
        conversation.state = ConversationState.PENDING.value
        conversation.id = "conv-123"
        conversation.bot_muted_until = now
        conversation.no_count = 1
        conversation.retry_offered_at = now
        conversation.context = {
            "pending_resume": {
                "context_manager": {"current_goal": "booking"},
                "expected_reply_type": "name",
                "expected_reply_reason": "booking_prompt",
                "intent_queue": ["booking", "check_booking"],
                "booking": {"active": True, "service": "Маникюр"},
                "session_memory": {"active_goal": "booking"},
                "service_hint": "Маникюр",
                "service_hint_at": "2026-02-18T01:00:00+00:00",
            }
        }

        handover = Mock()
        handover.status = "pending"

        result = manager_return(
            db,
            conversation,
            handover,
            "mgr-123",
            "Manager Name",
            preserve_context=True,
        )

        assert result.ok is True
        ctx = conversation.context
        assert ctx.get("pending_resume") is None
        assert ctx.get("expected_reply_type") == "name"
        assert ctx.get("expected_reply_reason") == "booking_prompt"
        assert ctx.get("intent_queue") == ["booking", "check_booking"]
        assert ctx.get("booking", {}).get("service") == "Маникюр"
        assert ctx.get("last_service_hint") == "Маникюр"
        assert ctx.get("last_service_hint_at") == "2026-02-18T01:00:00+00:00"
        assert ctx.get("re_entry_required", {}).get("required") is True

    def test_fails_from_bot_active(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value

        handover = Mock()

        result = manager_return(db, conversation, handover, "mgr-123", "Manager")

        assert result.ok is False
        assert result.error_code == "invalid_state"


class TestManagerReopen:
    def test_success_from_resolved(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value
        conversation.id = "conv-123"

        handover = Mock()
        handover.status = "resolved"
        handover.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
        handover.resolved_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        handover.meta = {"reopen_count": 1}

        result = manager_reopen(
            db,
            conversation,
            handover,
            manager_id="mgr-123",
            manager_name="Manager Name",
        )

        assert result.ok is True
        assert conversation.state == ConversationState.MANAGER_ACTIVE.value
        assert handover.status == "active"
        assert handover.assigned_to == "mgr-123"
        assert handover.assigned_to_name == "Manager Name"
        assert handover.resolved_at is None
        assert handover.meta["reopen_count"] == 2
        assert handover.meta["last_reopened_by"] == "Manager Name"
        assert isinstance(handover.meta["last_reopened_at"], str)

    def test_fails_when_case_not_resolved(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value

        handover = Mock()
        handover.status = "active"

        result = manager_reopen(
            db,
            conversation,
            handover,
            manager_id="mgr-123",
            manager_name="Manager Name",
        )

        assert result.ok is False
        assert result.error_code == "invalid_handover"


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


class TestLowConfidenceRetryGate:
    def test_first_low_confidence_offers_retry(self):
        now = datetime.now(timezone.utc)
        conversation = SimpleNamespace(retry_offered_at=None)
        assert should_offer_low_confidence_retry(conversation, now) is True

    def test_within_window_does_not_offer_retry(self):
        now = datetime.now(timezone.utc)
        conversation = SimpleNamespace(
            retry_offered_at=now - timedelta(minutes=LOW_CONFIDENCE_RETRY_WINDOW_MINUTES - 1)
        )
        assert should_offer_low_confidence_retry(conversation, now) is False

    def test_after_window_offers_retry_again(self):
        now = datetime.now(timezone.utc)
        conversation = SimpleNamespace(
            retry_offered_at=now - timedelta(minutes=LOW_CONFIDENCE_RETRY_WINDOW_MINUTES + 1)
        )
        assert should_offer_low_confidence_retry(conversation, now) is True


class FakeRedis:
    def __init__(self):
        self.data = {}

    async def set(self, key: str, value: str, ex: int | None = None):
        self.data[key] = value
        return True

    async def get(self, key: str):
        return self.data.get(key)


class TestDebounce:
    @pytest.mark.asyncio
    async def test_only_latest_message_is_processed(self, monkeypatch):
        monkeypatch.setenv("DEBOUNCE_ENABLED", "true")

        redis_client = FakeRedis()
        pause_events: list[asyncio.Event] = []

        async def controlled_sleep(_seconds: float):
            event = asyncio.Event()
            pause_events.append(event)
            await event.wait()

        task_1 = asyncio.create_task(
            should_process_debounced_message(
                client_id="client-1",
                remote_jid="77010000000@s.whatsapp.net",
                message_id="m1",
                sleep_func=controlled_sleep,
                redis_client=redis_client,
            )
        )

        while len(pause_events) < 1:
            await asyncio.sleep(0)

        task_2 = asyncio.create_task(
            should_process_debounced_message(
                client_id="client-1",
                remote_jid="77010000000@s.whatsapp.net",
                message_id="m2",
                sleep_func=controlled_sleep,
                redis_client=redis_client,
            )
        )

        while len(pause_events) < 2:
            await asyncio.sleep(0)

        pause_events[0].set()
        pause_events[1].set()

        result_1, result_2 = await asyncio.gather(task_1, task_2)

        assert result_1 is False
        assert result_2 is True


class TestPendingStatusQuestionDetection:
    def test_detects_not_answering_phrase(self):
        assert is_handover_status_question("почему не отвечаете?") is True

    def test_detects_silence_phrase(self):
        assert is_handover_status_question("почему молчит?") is True
