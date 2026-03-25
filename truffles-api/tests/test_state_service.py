import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app.models import Handover, Message, User
from app.routers.webhook import _legacy as legacy
from app.routers.webhook.dedup import should_process_debounced_message
from app.routers.webhook.decision import (
    LOW_CONFIDENCE_RETRY_WINDOW_MINUTES,
    is_handover_status_question,
    should_offer_low_confidence_retry,
)
from app.services.state_machine import ConversationState
from app.services.handover_owner_service import (
    ActiveHandoverReuseRuntimeHooks,
    PendingEscalationNotificationRuntimeHooks,
    _create_pending_escalation_with_notification,
    _reuse_active_handover,
    _sync_pending_resume_on_handover_reuse,
    escalate_to_pending,
    manager_reassign,
    manager_reopen,
    manager_resolve,
    manager_return,
    manager_take,
)
from app.services.state_service import (
    HandoverConfirmationRuntimeHooks,
    PendingResumeBoundaryRuntimeHooks,
    PendingContinuityRuntimeHooks,
    _build_pending_resume_snapshot_payload,
    _capture_pending_resume_context,
    _handle_handover_confirmation_runtime,
    _prepare_pending_handoff_resume_boundary_restore,
    _prepare_resolved_handoff_resume_boundary_restore,
    _resolve_pending_ack,
    _resolve_pending_close,
    _resolve_pending_no_handover_reset,
    _restore_pending_resume_context,
    _restore_pending_resume_payload,
    _resolve_pending_resume_boundary_activation,
    _resolve_resolved_handoff_resume_boundary_restore,
    _resolve_pending_resume_session_memory_policy,
    _resolve_pending_timeout_resume_boundary_payload,
    check_invariants,
)


class TestEscalateToPending:
    def test_capture_pending_resume_context_creates_isolated_snapshot(self):
        context = {
            "expected_reply_type": "  time  ",
            "expected_reply_reason": "  booking_prompt  ",
            "context_manager": {"current_goal": "booking"},
            "intent_queue": ["booking"],
            "booking": {"active": True, "service": "Маникюр"},
            "session_memory": {
                "active_goal": "booking",
                "interaction_state": {
                    "resume_slot": " datetime ",
                    "interaction_target": " time ",
                    "interaction_owner": " llm_policy_core ",
                },
            },
            "last_service_hint": "  Маникюр  ",
            "last_service_hint_at": " 2026-03-15T10:00:00+00:00 ",
        }

        updated = _capture_pending_resume_context(context)
        snapshot = updated.get("pending_resume")

        context["context_manager"]["current_goal"] = "changed"
        context["intent_queue"].append("handoff")
        context["booking"]["service"] = "Педикюр"
        context["session_memory"]["interaction_state"]["resume_slot"] = "name"

        assert snapshot["context_manager"]["current_goal"] == "booking"
        assert snapshot["expected_reply_type"] == "time"
        assert snapshot["expected_reply_reason"] == "booking_prompt"
        assert snapshot["intent_queue"] == ["booking"]
        assert snapshot["booking"]["service"] == "Маникюр"
        assert snapshot["session_memory"]["interaction_state"]["resume_slot"] == "datetime"
        assert snapshot["last_service_hint"] == "Маникюр"
        assert snapshot["last_service_hint_at"] == "2026-03-15T10:00:00+00:00"

    def test_sync_pending_resume_on_handover_reuse_captures_snapshot(self):
        conversation = SimpleNamespace(
            context={
                "expected_reply_type": "time",
                "expected_reply_reason": "booking_prompt",
                "context_manager": {"current_goal": "booking"},
                "booking": {"active": True, "service": "Стрижка"},
                "session_memory": {
                    "active_goal": "booking",
                    "last_question_type": "time",
                    "interaction_state": {"resume_slot": "datetime"},
                },
                "branch_id": "branch-1",
            }
        )

        changed = _sync_pending_resume_on_handover_reuse(conversation)

        assert changed is True
        snapshot = conversation.context.get("pending_resume")
        assert snapshot["expected_reply_type"] == "time"
        assert snapshot["expected_reply_reason"] == "booking_prompt"
        assert snapshot["booking"]["service"] == "Стрижка"
        assert snapshot["session_memory"]["interaction_state"]["resume_slot"] == "datetime"
        assert conversation.context.get("branch_id") == "branch-1"
        assert "expected_reply_type" not in conversation.context
        assert "booking" not in conversation.context
        assert "session_memory" not in conversation.context
        assert "context_manager" not in conversation.context

    def test_sync_pending_resume_on_handover_reuse_preserves_existing_snapshot(self):
        existing_snapshot = {
            "expected_reply_type": "time",
            "booking": {"active": True, "service": "Стрижка"},
            "session_memory": {"last_question_type": "time"},
            "context_manager": {"current_goal": "booking"},
        }
        conversation = SimpleNamespace(
            context={
                "pending_resume": existing_snapshot,
                "expected_reply_type": "time",
                "booking": {"active": True, "service": "Стрижка"},
                "session_memory": {"last_question_type": "time"},
                "context_manager": {"current_goal": "booking"},
                "branch_id": "branch-1",
            }
        )

        changed = _sync_pending_resume_on_handover_reuse(conversation)

        assert changed is True
        assert conversation.context.get("pending_resume") == existing_snapshot
        assert conversation.context.get("branch_id") == "branch-1"
        assert "expected_reply_type" not in conversation.context
        assert "booking" not in conversation.context
        assert "session_memory" not in conversation.context
        assert "context_manager" not in conversation.context

    def test_reuse_active_handover_owner_surface_captures_pending_resume_snapshot(self):
        conversation = SimpleNamespace(
            id="conversation-1",
            state=ConversationState.BOT_ACTIVE.value,
            context={
                "expected_reply_type": "time",
                "expected_reply_reason": "booking_prompt",
                "context_manager": {
                    "current_goal": "booking",
                    "canonical_dialog_state": {
                        "interaction_state": {
                            "interaction_owner": "llm_policy_core:ask_about_requested_slot",
                        }
                    },
                },
                "booking": {"active": True, "service": "Стрижка"},
                "session_memory": {
                    "active_goal": "booking",
                    "last_question_type": "time",
                    "interaction_state": {"resume_slot": "datetime"},
                },
                "branch_id": "branch-1",
            },
            escalated_at=None,
        )
        handover = SimpleNamespace(id="handover-1", status="pending")
        user = SimpleNamespace(id="user-1")
        transition_calls: list[dict] = []
        trace_calls: list[dict] = []

        def _transition(conv, target_state, **kwargs):
            transition_calls.append(
                {
                    "target_state": target_state.value if hasattr(target_state, "value") else target_state,
                    "allow_same": kwargs["allow_same"],
                    "enforce": kwargs["enforce"],
                    "handover": kwargs["handover"],
                }
            )
            conv.state = target_state.value if hasattr(target_state, "value") else target_state
            return {
                "invalid_transition": False,
                "from_state": ConversationState.BOT_ACTIVE.value,
                "to_state": conv.state,
                "violations": [],
            }

        reused_handover, reused, telegram_sent = _reuse_active_handover(
            db=Mock(),
            conversation=conversation,
            user=user,
            message="Мне нужна помощь менеджера",
            source="test",
            intent="cancel_request",
            hooks=ActiveHandoverReuseRuntimeHooks(
                get_active_handover=lambda _db, _conversation_id: handover,
                transition_state=_transition,
                send_telegram_notification=lambda **_kwargs: True,
                record_decision_trace=lambda _conv, trace: trace_calls.append(dict(trace)),
            ),
        )

        assert reused_handover is handover
        assert reused is True
        assert telegram_sent is True
        assert conversation.state == ConversationState.PENDING.value
        assert conversation.escalated_at is not None
        assert transition_calls == [
            {
                "target_state": ConversationState.PENDING.value,
                "allow_same": True,
                "enforce": False,
                "handover": handover,
            }
        ]
        assert trace_calls[0] == {
            "stage": "pending_resume",
            "decision": "sync_on_reuse",
            "state": ConversationState.BOT_ACTIVE.value,
            "source": "test",
            "intent": "cancel_request",
        }
        assert trace_calls[1] == {
            "stage": "escalation",
            "decision": "reuse_handover",
            "state": ConversationState.PENDING.value,
            "intent": "cancel_request",
            "source": "test",
            "handover_id": "handover-1",
            "telegram_sent": True,
        }
        assert conversation.context.get("branch_id") == "branch-1"
        snapshot = conversation.context.get("pending_resume")
        assert isinstance(snapshot, dict)
        assert snapshot["expected_reply_type"] == "time"
        assert snapshot["expected_reply_reason"] == "booking_prompt"
        assert snapshot["booking"]["service"] == "Стрижка"
        assert snapshot["session_memory"]["interaction_state"]["resume_slot"] == "datetime"
        assert "expected_reply_type" not in conversation.context
        assert "booking" not in conversation.context
        assert "session_memory" not in conversation.context
        assert "context_manager" not in conversation.context

    def test_reuse_active_handover_owner_surface_preserves_existing_pending_snapshot(self):
        existing_snapshot = {
            "expected_reply_type": "time",
            "booking": {"active": True, "service": "Стрижка"},
            "session_memory": {"last_question_type": "time"},
            "context_manager": {"current_goal": "booking"},
        }
        conversation = SimpleNamespace(
            id="conversation-1",
            state=ConversationState.PENDING.value,
            context={
                "pending_resume": existing_snapshot,
                "expected_reply_type": "time",
                "booking": {"active": True, "service": "Стрижка"},
                "session_memory": {"last_question_type": "time"},
                "context_manager": {"current_goal": "booking"},
                "branch_id": "branch-1",
            },
            escalated_at=datetime.now(timezone.utc),
        )
        handover = SimpleNamespace(id="handover-2", status="pending")
        transition_state = Mock()

        reused_handover, reused, telegram_sent = _reuse_active_handover(
            db=Mock(),
            conversation=conversation,
            user=SimpleNamespace(id="user-1"),
            message="Нужен менеджер",
            source="test",
            intent="cancel_request",
            hooks=ActiveHandoverReuseRuntimeHooks(
                get_active_handover=lambda _db, _conversation_id: handover,
                transition_state=transition_state,
                send_telegram_notification=lambda **_kwargs: True,
                record_decision_trace=Mock(),
            ),
        )

        assert reused_handover is handover
        assert reused is True
        assert telegram_sent is True
        transition_state.assert_not_called()
        assert conversation.state == ConversationState.PENDING.value
        assert conversation.context.get("pending_resume") == existing_snapshot
        assert conversation.context.get("branch_id") == "branch-1"
        assert "expected_reply_type" not in conversation.context
        assert "booking" not in conversation.context
        assert "session_memory" not in conversation.context
        assert "context_manager" not in conversation.context

    def test_pending_escalation_notification_owner_surface_returns_handover_and_notification(self):
        handover = SimpleNamespace(id="handover-1", status="pending", _reopened=True)
        escalate_to_pending = Mock(return_value=SimpleNamespace(ok=True, value=handover))
        send_telegram_notification = Mock(return_value=True)

        result = _create_pending_escalation_with_notification(
            db=Mock(),
            conversation=SimpleNamespace(id="conversation-1"),
            user=SimpleNamespace(id="user-1"),
            user_message="Нужен менеджер",
            trigger_type="intent",
            trigger_value="policy_core_guard",
            hooks=PendingEscalationNotificationRuntimeHooks(
                escalate_to_pending=escalate_to_pending,
                send_telegram_notification=send_telegram_notification,
            ),
        )

        assert result.ok is True
        assert result.handover is handover
        assert result.handover_reopened is True
        assert result.telegram_sent is True
        escalate_to_pending.assert_called_once()
        send_telegram_notification.assert_called_once()

    def test_pending_escalation_notification_owner_surface_skips_notification_on_failure(self):
        escalate_to_pending = Mock(return_value=SimpleNamespace(ok=False, value=None))
        send_telegram_notification = Mock()

        result = _create_pending_escalation_with_notification(
            db=Mock(),
            conversation=SimpleNamespace(id="conversation-1"),
            user=SimpleNamespace(id="user-1"),
            user_message="Нужен менеджер",
            trigger_type="intent",
            trigger_value="policy_core_guard",
            hooks=PendingEscalationNotificationRuntimeHooks(
                escalate_to_pending=escalate_to_pending,
                send_telegram_notification=send_telegram_notification,
            ),
        )

        assert result.ok is False
        assert result.handover is None
        assert result.handover_reopened is False
        assert result.telegram_sent is False
        escalate_to_pending.assert_called_once()
        send_telegram_notification.assert_not_called()

    @patch("app.services.handover_owner_service.TelegramService")
    @patch("app.services.handover_owner_service.resolve_telegram_routing")
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

    @patch("app.services.handover_owner_service.TelegramService")
    @patch("app.services.handover_owner_service.resolve_telegram_routing")
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

    @patch("app.services.handover_owner_service.TelegramService")
    @patch("app.services.handover_owner_service.resolve_telegram_routing")
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

    @patch("app.services.handover_owner_service.TelegramService")
    @patch("app.services.handover_owner_service.resolve_telegram_routing")
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

    @patch("app.services.handover_owner_service.TelegramService")
    @patch("app.services.handover_owner_service.resolve_telegram_routing")
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

    @patch("app.services.handover_owner_service.TelegramService")
    @patch("app.services.handover_owner_service.resolve_telegram_routing")
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

    @patch("app.services.handover_owner_service.resolve_telegram_routing")
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
    def test_restore_pending_resume_context_delegates_to_dialog_state_service(self):
        now = datetime(2026, 3, 15, 18, 45, tzinfo=timezone.utc)
        restored, did_restore = _restore_pending_resume_context(
            {
                "pending_resume": {
                    "expected_reply_type": "  name  ",
                    "expected_reply_reason": "  booking_prompt  ",
                    "intent_queue": ["booking", "check_booking"],
                    "booking": {"active": True, "service": "Маникюр"},
                    "session_memory": {
                        "active_goal": "booking",
                        "interaction_state": {
                            "resume_slot": " Name ",
                            "interaction_target": " time ",
                            "interaction_relation": " slot_compare ",
                            "interaction_owner": " booking name ",
                        },
                    },
                    "service_hint": "  Маникюр  ",
                    "service_hint_at": " 2026-03-15T10:00:00+00:00 ",
                }
            },
            now=now,
        )

        assert did_restore is True
        assert restored["expected_reply_type"] == "name"
        assert restored["expected_reply_reason"] == "booking_prompt"
        assert restored["intent_queue"] == ["booking", "check_booking"]
        assert restored["booking"]["service"] == "Маникюр"
        assert restored["session_memory"]["interaction_state"]["resume_slot"] == "name"
        assert restored["session_memory"]["last_updated_at"] == now.isoformat()
        assert restored["last_service_hint"] == "Маникюр"
        assert restored["last_service_hint_at"] == "2026-03-15T10:00:00+00:00"
        assert restored["re_entry_required"]["reason"] == "pending_resume"

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

    def test_resolve_pending_no_handover_reset_uses_owner_surface(self):
        conversation = SimpleNamespace(
            state=ConversationState.PENDING.value,
            context={
                "pending_resume": {"expected_reply_type": "time"},
                "pending_sla": {"ping_sent_at": "2026-03-18T10:00:00+00:00"},
                "handover_confirmation": {"status": "asked"},
            },
        )
        saved_message = SimpleNamespace(message_metadata={})
        trace_calls: list[dict] = []

        def _transition_state(conv, to_state, **_kwargs):
            conv.state = to_state.value
            return {"invalid_transition": False}

        def _update_message_decision_metadata(message, updates):
            meta = message.message_metadata.setdefault("decision_meta", {})
            meta.update(updates)

        _resolve_pending_no_handover_reset(
            conversation=conversation,
            saved_message=saved_message,
            router_pending_meta={"router_stage": "pending"},
            hooks=PendingContinuityRuntimeHooks(
                get_conversation_context=lambda conv: dict(conv.context),
                set_conversation_context=lambda conv, context: setattr(conv, "context", context),
                transition_state=_transition_state,
                manager_resolve=Mock(),
                record_decision_trace=lambda _conv, trace: trace_calls.append(dict(trace)),
                update_message_decision_metadata=_update_message_decision_metadata,
            ),
        )

        assert conversation.state == ConversationState.BOT_ACTIVE.value
        assert conversation.context.get("pending_resume") is None
        assert conversation.context.get("pending_sla") == {}
        assert "handover_confirmation" not in conversation.context
        assert trace_calls == [
            {
                "stage": "pending_guard",
                "decision": "reset_no_handover",
                "state": ConversationState.BOT_ACTIVE.value,
                "router_stage": "pending",
            }
        ]
        assert saved_message.message_metadata.get("decision_meta") == {
            "pending_action": "pending_guard_reset",
            "pending_guard": "no_handover",
        }

    def test_resolve_pending_close_uses_owner_surface(self):
        handover = SimpleNamespace(status="pending")
        conversation = SimpleNamespace(
            state=ConversationState.PENDING.value,
            bot_status="active",
            bot_muted_until=datetime.now(timezone.utc),
        )
        saved_message = SimpleNamespace(message_metadata={})
        trace_calls: list[dict] = []
        manager_resolve = Mock()

        def _update_message_decision_metadata(message, updates):
            meta = message.message_metadata.setdefault("decision_meta", {})
            meta.update(updates)

        decision = _resolve_pending_close(
            conversation=conversation,
            handover=handover,
            saved_message=saved_message,
            router_pending_meta={"router_stage": "pending"},
            hooks=PendingContinuityRuntimeHooks(
                get_conversation_context=lambda _conv: {},
                set_conversation_context=lambda *_args, **_kwargs: None,
                transition_state=Mock(),
                manager_resolve=manager_resolve,
                record_decision_trace=lambda _conv, trace: trace_calls.append(dict(trace)),
                update_message_decision_metadata=_update_message_decision_metadata,
            ),
        )

        assert decision.handled is True
        assert decision.bot_response is None
        assert decision.success_message == "Pending closed by user"
        assert conversation.bot_status == "muted"
        assert conversation.bot_muted_until is None
        manager_resolve.assert_called_once_with(
            conversation,
            handover,
            manager_id="system",
            manager_name="system",
        )
        assert trace_calls == [
            {
                "stage": "pending_sla",
                "decision": "pending_close",
                "state": ConversationState.PENDING.value,
                "router_stage": "pending",
            }
        ]
        assert saved_message.message_metadata.get("decision_meta") == {
            "pending_action": "pending_close"
        }

    def test_resolve_pending_ack_restores_owner_surface(self):
        now = datetime(2026, 3, 18, 10, 0, tzinfo=timezone.utc)
        conversation = SimpleNamespace(
            state=ConversationState.PENDING.value,
            context={
                "pending_resume": {
                    "context_manager": {"current_goal": "booking"},
                    "expected_reply_type": "time",
                    "expected_reply_reason": "booking_prompt",
                    "intent_queue": ["booking"],
                    "booking": {"active": True, "service": "Маникюр"},
                    "session_memory": {
                        "active_goal": "booking",
                        "last_question_type": "time",
                    },
                }
            },
            bot_status="muted",
        )
        saved_message = SimpleNamespace(message_metadata={})
        trace_calls: list[dict] = []

        def _transition_state(conv, to_state, **_kwargs):
            conv.state = to_state.value
            return {"invalid_transition": False}

        def _update_message_decision_metadata(message, updates):
            meta = message.message_metadata.setdefault("decision_meta", {})
            meta.update(updates)

        decision = _resolve_pending_ack(
            conversation=conversation,
            handover=None,
            saved_message=saved_message,
            now=now,
            router_pending_meta={"router_stage": "pending"},
            msg_pending_ack="ACK",
            hooks=PendingContinuityRuntimeHooks(
                get_conversation_context=lambda conv: dict(conv.context),
                set_conversation_context=lambda conv, context: setattr(conv, "context", context),
                transition_state=_transition_state,
                manager_resolve=Mock(),
                record_decision_trace=lambda _conv, trace: trace_calls.append(dict(trace)),
                update_message_decision_metadata=_update_message_decision_metadata,
            ),
        )

        assert decision.handled is True
        assert decision.bot_response == "ACK"
        assert conversation.state == ConversationState.BOT_ACTIVE.value
        assert conversation.bot_status == "active"
        assert conversation.context.get("pending_resume") is None
        assert conversation.context.get("expected_reply_type") == "time"
        assert conversation.context.get("expected_reply_reason") == "booking_prompt"
        assert conversation.context.get("re_entry_required", {}).get("reason") == "pending_resume"
        assert trace_calls == [
            {
                "stage": "pending_resume",
                "decision": "restore",
                "reason": "pending_ack",
            },
            {
                "stage": "re_entry",
                "decision": "required",
                "reason": "pending_resume",
            },
            {
                "stage": "pending_sla",
                "decision": "pending_ack",
                "state": ConversationState.BOT_ACTIVE.value,
                "router_stage": "pending",
            },
        ]
        assert saved_message.message_metadata.get("decision_meta") == {
            "pending_action": "pending_ack",
            "pending_resume_restored": True,
        }

    def test_handle_handover_confirmation_runtime_reuses_owner_surface(self):
        now = datetime(2026, 3, 18, 11, 0, tzinfo=timezone.utc)
        conversation = SimpleNamespace(
            state=ConversationState.BOT_ACTIVE.value,
            context={
                "handover_confirmation": {
                    "asked_at": now.isoformat(),
                    "user_message": "Нужен менеджер",
                }
            },
        )
        trace_calls: list[dict] = []
        reset_low_confidence_retry = Mock()
        record_escalation_metric = Mock()

        def _set_handover_confirmation(context, payload):
            updated = dict(context)
            if payload is None:
                updated.pop("handover_confirmation", None)
            else:
                updated["handover_confirmation"] = payload
            return updated

        decision = _handle_handover_confirmation_runtime(
            db=Mock(),
            conversation=conversation,
            user=SimpleNamespace(id="user-1"),
            message_text="да",
            now=now,
            hooks=HandoverConfirmationRuntimeHooks(
                get_conversation_context=lambda conv: dict(conv.context),
                get_handover_confirmation=lambda context: context.get("handover_confirmation"),
                is_handover_confirmation_active=lambda _confirmation, _now: True,
                set_handover_confirmation=_set_handover_confirmation,
                set_conversation_context=lambda conv, context: setattr(conv, "context", context),
                reset_low_confidence_retry=reset_low_confidence_retry,
                classify_confirmation=lambda _text: "yes",
                reuse_active_handover=lambda **_kwargs: (SimpleNamespace(id="handover-1"), True, True),
                escalate_to_pending=Mock(),
                send_telegram_notification=Mock(),
                record_escalation_metric=record_escalation_metric,
                record_decision_trace=lambda _conv, trace: trace_calls.append(dict(trace)),
                msg_escalated="ESCALATED",
                msg_ai_error="AI_ERROR",
                msg_handover_declined="DECLINED",
            ),
        )

        assert decision.handled is True
        assert decision.bot_response == "ESCALATED"
        assert decision.success_message == "Handover confirmed (reused), telegram=sent"
        assert decision.failure_message == "Handover confirmed (reused), telegram=sent; response_send=failed"
        assert "handover_confirmation" not in conversation.context
        reset_low_confidence_retry.assert_called_once_with(conversation)
        record_escalation_metric.assert_not_called()
        assert trace_calls == [
            {
                "stage": "handover_confirmation",
                "decision": "confirmed",
                "reason": "user_confirmed",
                "state": ConversationState.BOT_ACTIVE.value,
                "reused": True,
            }
        ]

    def test_fails_from_bot_active(self):
        db = Mock()
        conversation = Mock()
        conversation.state = ConversationState.BOT_ACTIVE.value

        handover = Mock()

        result = manager_resolve(db, conversation, handover, "mgr-123", "Manager")

        assert result.ok is False
        assert result.error_code == "invalid_state"


def test_build_pending_resume_snapshot_payload_captures_pending_resume_contract() -> None:
    payload = _build_pending_resume_snapshot_payload(
        context={
            "last_service_hint": "  Маникюр  ",
            "last_service_hint_at": " 2026-03-15T10:00:00+00:00 ",
        },
        context_manager={"current_goal": "booking"},
        expected_reply_type="  time  ",
        expected_reply_reason=" booking_prompt ",
        intent_queue=["booking"],
        booking_context={"active": True, "service": "Маникюр"},
        session_memory={
            "active_goal": "booking",
            "interaction_state": {"resume_slot": " datetime "},
        },
    )

    assert payload["expected_reply_type"] == "time"
    assert payload["expected_reply_reason"] == "booking_prompt"
    assert payload["intent_queue"] == ["booking"]
    assert payload["booking"] == {"active": True, "service": "Маникюр"}
    assert payload["session_memory"] == {
        "active_goal": "booking",
        "interaction_state": {"resume_slot": "datetime"},
    }
    assert payload["last_service_hint"] == "Маникюр"
    assert payload["last_service_hint_at"] == "2026-03-15T10:00:00+00:00"
    assert payload["context_manager"]["current_goal"] == "booking"
    assert payload["context_manager"]["canonical_dialog_state"]["pending_question_contract"] == {
        "expected_reply_type": "time",
        "reason": "booking_prompt",
    }


def test_build_pending_resume_snapshot_payload_prefers_canonical_question_contract() -> None:
    payload = _build_pending_resume_snapshot_payload(
        context={},
        context_manager={
            "current_goal": "booking",
            "canonical_dialog_state": {
                "pending_question_contract": {
                    "expected_reply_type": " time ",
                    "reason": " booking_interrupt ",
                    "next_question": " datetime ",
                    "open_questions": [" datetime "],
                }
            },
        },
        expected_reply_type=" service_choice ",
        expected_reply_reason=" stale_projection ",
        intent_queue=["booking"],
        booking_context={"active": True, "service": "Маникюр"},
        session_memory={"active_goal": "booking"},
    )

    assert payload["expected_reply_type"] == "time"
    assert payload["expected_reply_reason"] == "booking_interrupt"
    assert payload["context_manager"]["canonical_dialog_state"]["pending_question_contract"] == {
        "expected_reply_type": "time",
        "reason": "booking_interrupt",
        "next_question": "datetime",
        "open_questions": ["datetime"],
    }


def test_restore_pending_resume_payload_restores_owner_contract() -> None:
    now = datetime(2026, 3, 15, 18, 45, tzinfo=timezone.utc)

    restored = _restore_pending_resume_payload(
        context={
            "pending_sla": {"ping_sent_at": now.isoformat()},
            "handover_confirmation": {"required": True},
        },
        pending_resume={
            "expected_reply_type": "  name  ",
            "expected_reply_reason": "  booking_prompt  ",
            "intent_queue": ["booking", "check_booking"],
            "booking": {"active": True, "service": "Маникюр"},
            "session_memory": {
                "active_goal": "booking",
                "interaction_state": {
                    "resume_slot": " Name ",
                    "interaction_target": " time ",
                },
            },
            "service_hint": "  Маникюр  ",
            "service_hint_at": " 2026-03-15T10:00:00+00:00 ",
        },
        now=now,
    )

    assert restored["expected_reply_type"] == "name"
    assert restored["expected_reply_reason"] == "booking_prompt"
    assert restored["intent_queue"] == ["booking", "check_booking"]
    assert restored["booking"]["service"] == "Маникюр"
    assert restored["session_memory"]["interaction_state"]["resume_slot"] == "name"
    assert restored["session_memory"]["last_updated_at"] == now.isoformat()
    assert restored["last_service_hint"] == "Маникюр"
    assert restored["last_service_hint_at"] == "2026-03-15T10:00:00+00:00"
    assert restored["re_entry_required"]["reason"] == "pending_resume"
    assert "pending_sla" not in restored
    assert "handover_confirmation" not in restored


def test_prepare_pending_handoff_resume_boundary_restore_uses_owner_surface() -> None:
    now = datetime(2026, 3, 15, 18, 45, tzinfo=timezone.utc)

    restore = _prepare_pending_handoff_resume_boundary_restore(
        {
            "pending_resume": {
                "context_manager": {"current_goal": "booking"},
                "expected_reply_reason": " booking_interrupt ",
                "booking": {
                    "active": True,
                    "service": "Маникюр",
                    "last_question": "datetime",
                },
                "session_memory": {
                    "active_goal": "booking",
                    "last_question_type": " time ",
                },
            }
        },
        now=now,
        prompt_builder=lambda expected_reply_type: {
            "service_choice": "Какая услуга вас интересует?",
            "time": "Когда вам удобно?",
            "name": "Подскажите, как к вам обращаться?",
        }.get(expected_reply_type),
    )

    assert restore.restored is True
    assert restore.pending_reason == "booking_interrupt"
    assert restore.expected_reply_type == "time"
    assert restore.apply_boundary_booking_state is True
    assert restore.boundary_payload == {
        "booking_state": {
            "active": True,
            "service": "Маникюр",
            "last_question": "datetime",
        },
        "expected_reply_type": "time",
        "prompt": "Когда вам удобно?",
        "resume_slot": "datetime",
    }
    assert restore.context.get("pending_resume") is None
    assert restore.context.get("re_entry_required", {}).get("reason") == "pending_resume"


def test_prepare_pending_handoff_resume_boundary_restore_prefers_canonical_question_contract() -> None:
    now = datetime(2026, 3, 15, 18, 45, tzinfo=timezone.utc)

    restore = _prepare_pending_handoff_resume_boundary_restore(
        {
            "pending_resume": {
                "context_manager": {
                    "current_goal": "booking",
                    "canonical_dialog_state": {
                        "pending_question_contract": {
                            "expected_reply_type": " time ",
                            "reason": " booking_interrupt ",
                            "next_question": " datetime ",
                            "open_questions": [" datetime "],
                        }
                    },
                },
                "booking": {
                    "active": True,
                    "service": "Маникюр",
                    "last_question": "datetime",
                },
                "session_memory": {
                    "active_goal": "booking",
                    "last_question_type": " service_choice ",
                },
            }
        },
        now=now,
        prompt_builder=lambda expected_reply_type: {
            "service_choice": "Какая услуга вас интересует?",
            "time": "Когда вам удобно?",
        }.get(expected_reply_type),
    )

    assert restore.restored is True
    assert restore.pending_reason == "booking_interrupt"
    assert restore.expected_reply_type == "time"
    assert restore.apply_boundary_booking_state is False
    assert restore.boundary_payload == {
        "booking_state": {
            "active": True,
            "service": "Маникюр",
            "last_question": "datetime",
        },
        "expected_reply_type": "time",
        "prompt": "Когда вам удобно?",
        "resume_slot": "datetime",
    }


def test_prepare_resolved_handoff_resume_boundary_restore_uses_owner_surface() -> None:
    now = datetime(2026, 3, 15, 18, 45, tzinfo=timezone.utc)

    restore = _prepare_resolved_handoff_resume_boundary_restore(
        {
            "context_manager": {"current_goal": "booking"},
            "expected_reply_reason": " booking_interrupt ",
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "datetime",
            },
            "session_memory": {
                "active_goal": "booking",
                "last_question_type": " time ",
            },
            "re_entry_required": {
                "required": True,
                "reason": "pending_resume",
                "set_at": now.isoformat(),
            },
        },
        now=now,
        prompt_builder=lambda expected_reply_type: {
            "service_choice": "Какая услуга вас интересует?",
            "time": "Когда вам удобно?",
            "name": "Подскажите, как к вам обращаться?",
        }.get(expected_reply_type),
    )

    assert restore.restored is True
    assert restore.pending_reason == "booking_interrupt"
    assert restore.expected_reply_type == "time"
    assert restore.apply_boundary_booking_state is True
    assert restore.boundary_payload == {
        "booking_state": {
            "active": True,
            "service": "Маникюр",
            "last_question": "datetime",
        },
        "expected_reply_type": "time",
        "prompt": "Когда вам удобно?",
        "resume_slot": "datetime",
    }


def test_prepare_resolved_handoff_resume_boundary_restore_prefers_canonical_question_contract() -> None:
    now = datetime(2026, 3, 15, 18, 45, tzinfo=timezone.utc)

    restore = _prepare_resolved_handoff_resume_boundary_restore(
        {
            "context_manager": {
                "current_goal": "booking",
                "canonical_dialog_state": {
                    "pending_question_contract": {
                        "expected_reply_type": " time ",
                        "reason": " booking_interrupt ",
                        "next_question": " datetime ",
                        "open_questions": [" datetime "],
                    }
                },
            },
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "datetime",
            },
            "session_memory": {
                "active_goal": "booking",
                "last_question_type": "service_choice",
            },
            "re_entry_required": {
                "required": True,
                "reason": "pending_resume",
                "set_at": now.isoformat(),
            },
        },
        now=now,
        prompt_builder=lambda expected_reply_type: {
            "time": "Когда вам удобно?",
        }.get(expected_reply_type),
    )

    assert restore.restored is True
    assert restore.pending_reason == "booking_interrupt"
    assert restore.expected_reply_type == "time"
    assert restore.apply_boundary_booking_state is True
    assert restore.boundary_payload == {
        "booking_state": {
            "active": True,
            "service": "Маникюр",
            "last_question": "datetime",
        },
        "expected_reply_type": "time",
        "prompt": "Когда вам удобно?",
        "resume_slot": "datetime",
    }


def test_resolve_resolved_handoff_resume_boundary_restore_uses_owner_surface() -> None:
    now = datetime(2026, 3, 15, 18, 45, tzinfo=timezone.utc)
    conversation = SimpleNamespace(context={})
    saved_message = Mock()
    saved_message.message_metadata = {}

    def _set_expected_reply_context(**kwargs):
        updated = dict(kwargs["context"])
        updated["expected_reply_type"] = kwargs["expected_reply_type"]
        updated["expected_reply_reason"] = kwargs["reason"]
        updated["re_entry_required"] = {
            "required": False,
            "reason": kwargs["reason"],
            "set_at": kwargs["now"].isoformat(),
        }
        kwargs["conversation"].context = updated
        return updated

    def _update_message_decision_metadata(message, updates):
        meta = message.message_metadata.setdefault("decision_meta", {})
        meta.update(updates)

    trace_calls: list[dict] = []

    restore = _resolve_resolved_handoff_resume_boundary_restore(
        conversation=conversation,
        saved_message=saved_message,
        context={
            "context_manager": {"current_goal": "booking"},
            "expected_reply_reason": " booking_interrupt ",
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "datetime",
            },
            "session_memory": {
                "active_goal": "booking",
                "last_question_type": " time ",
            },
            "re_entry_required": {
                "required": True,
                "reason": "pending_resume",
                "set_at": now.isoformat(),
            },
        },
        conversation_state=ConversationState.BOT_ACTIVE.value,
        now=now,
        prompt_builder=lambda expected_reply_type: {
            "time": "Когда вам удобно?",
        }.get(expected_reply_type),
        hooks=PendingResumeBoundaryRuntimeHooks(
            set_booking_context=lambda context, booking: {**dict(context), "booking": booking},
            set_expected_reply_context=_set_expected_reply_context,
            set_conversation_context=lambda conv, context: setattr(conv, "context", context),
            record_decision_trace=lambda _conv, trace: trace_calls.append(dict(trace)),
            update_message_decision_metadata=_update_message_decision_metadata,
        ),
    )

    assert restore.restored is True
    assert restore.context.get("expected_reply_type") == "time"
    assert restore.context.get("expected_reply_reason") == "booking_interrupt"
    assert restore.context.get("booking") == {
        "active": True,
        "service": "Маникюр",
        "last_question": "datetime",
    }
    assert trace_calls == [
        {
            "stage": "pending_resume",
            "decision": "restore_resolved_handoff_boundary",
            "reason": "resolved_handoff_resume_boundary",
        }
    ]
    assert saved_message.message_metadata.get("decision_meta", {}) == {
        "pending_resume_restored": True,
        "pending_resume_restore_reason": "resolved_handoff_resume_boundary",
        "resolved_handoff_resume_boundary": True,
    }


def test_resolve_pending_resume_boundary_activation_skips_control_messages() -> None:
    now = datetime(2026, 3, 15, 18, 45, tzinfo=timezone.utc)
    conversation = SimpleNamespace(context={})
    saved_message = Mock()
    saved_message.message_metadata = {}

    set_expected_reply_context = Mock(side_effect=lambda **kwargs: kwargs["context"])
    record_decision_trace = Mock()
    update_message_decision_metadata = Mock()

    activation = _resolve_pending_resume_boundary_activation(
        conversation=conversation,
        saved_message=saved_message,
        context={
            "pending_resume": {
                "context_manager": {"current_goal": "booking"},
                "booking": {
                    "active": True,
                    "service": "Маникюр",
                    "last_question": "datetime",
                },
                "session_memory": {
                    "active_goal": "booking",
                    "last_question_type": "time",
                },
            }
        },
        conversation_state=ConversationState.PENDING.value,
        message_text="Когда ответит менеджер?",
        now=now,
        prompt_builder=lambda expected_reply_type: {
            "time": "Когда вам удобно?",
        }.get(expected_reply_type),
        is_handover_status_question=lambda _text: True,
        is_opt_out_message=lambda _text: False,
        hooks=PendingResumeBoundaryRuntimeHooks(
            set_booking_context=lambda context, booking: {**dict(context), "booking": booking},
            set_expected_reply_context=set_expected_reply_context,
            set_conversation_context=lambda conv, context: setattr(conv, "context", context),
            record_decision_trace=record_decision_trace,
            update_message_decision_metadata=update_message_decision_metadata,
        ),
    )

    assert activation.boundary_active is False
    assert activation.boundary_restored is False
    assert activation.boundary_payload is not None
    set_expected_reply_context.assert_not_called()
    record_decision_trace.assert_not_called()
    update_message_decision_metadata.assert_not_called()


def test_resolve_pending_resume_boundary_activation_restores_pending_handoff_boundary() -> None:
    now = datetime(2026, 3, 15, 18, 45, tzinfo=timezone.utc)
    conversation = SimpleNamespace(context={})
    saved_message = Mock()
    saved_message.message_metadata = {}

    def _set_expected_reply_context(**kwargs):
        updated = dict(kwargs["context"])
        updated["expected_reply_type"] = kwargs["expected_reply_type"]
        updated["expected_reply_reason"] = kwargs["reason"]
        kwargs["conversation"].context = updated
        return updated

    def _update_message_decision_metadata(message, updates):
        meta = message.message_metadata.setdefault("decision_meta", {})
        meta.update(updates)

    trace_calls: list[dict] = []

    activation = _resolve_pending_resume_boundary_activation(
        conversation=conversation,
        saved_message=saved_message,
        context={
            "pending_resume": {
                "context_manager": {"current_goal": "booking"},
                "expected_reply_reason": " booking_interrupt ",
                "booking": {
                    "active": True,
                    "service": "Маникюр",
                    "last_question": "datetime",
                },
                "session_memory": {
                    "active_goal": "booking",
                    "last_question_type": " time ",
                },
            }
        },
        conversation_state=ConversationState.PENDING.value,
        message_text="Сколько стоит маникюр?",
        now=now,
        prompt_builder=lambda expected_reply_type: {
            "time": "Когда вам удобно?",
        }.get(expected_reply_type),
        is_handover_status_question=lambda _text: False,
        is_opt_out_message=lambda _text: False,
        hooks=PendingResumeBoundaryRuntimeHooks(
            set_booking_context=lambda context, booking: {**dict(context), "booking": booking},
            set_expected_reply_context=_set_expected_reply_context,
            set_conversation_context=lambda conv, context: setattr(conv, "context", context),
            record_decision_trace=lambda _conv, trace: trace_calls.append(dict(trace)),
            update_message_decision_metadata=_update_message_decision_metadata,
        ),
    )

    assert activation.boundary_active is True
    assert activation.boundary_restored is True
    assert activation.context.get("pending_resume") is None
    assert activation.context.get("expected_reply_type") == "time"
    assert activation.boundary_payload == {
        "booking_state": {
            "active": True,
            "service": "Маникюр",
            "last_question": "datetime",
        },
        "expected_reply_type": "time",
        "prompt": "Когда вам удобно?",
        "resume_slot": "datetime",
    }
    assert trace_calls == [
        {
            "stage": "pending_resume",
            "decision": "restore_soft_pass",
            "reason": "handover_soft_pass",
        }
    ]
    assert saved_message.message_metadata.get("decision_meta", {}) == {
        "pending_resume_restored": True,
        "pending_resume_restore_reason": "handover_soft_pass",
    }


def test_resolve_pending_resume_session_memory_policy_preserves_only_active_boundary() -> None:
    preserve_policy = _resolve_pending_resume_session_memory_policy(
        conversation_state=ConversationState.PENDING.value,
        resume_boundary_active=True,
        boundary_restored=True,
    )
    reset_policy = _resolve_pending_resume_session_memory_policy(
        conversation_state=ConversationState.MANAGER_ACTIVE.value,
        resume_boundary_active=False,
        boundary_restored=False,
    )

    assert preserve_policy.preserve_session_memory is True
    assert preserve_policy.reset_reason is None
    assert preserve_policy.trace_payload == {
        "stage": "session_memory",
        "decision": "preserve",
        "reason": "pending_handoff_resume_boundary",
        "state": ConversationState.PENDING.value,
        "restored_from_pending_resume": True,
    }
    assert preserve_policy.decision_meta_updates == {
        "session_memory_reset_skipped": "pending_handoff_resume_boundary",
        "pending_handoff_resume_boundary": True,
    }
    assert reset_policy.preserve_session_memory is False
    assert reset_policy.reset_reason == "handover"


def test_resolve_pending_timeout_resume_boundary_payload_requires_time() -> None:
    now = datetime(2026, 3, 15, 18, 45, tzinfo=timezone.utc)

    payload = _resolve_pending_timeout_resume_boundary_payload(
        {
            "context_manager": {"current_goal": "booking"},
            "booking": {
                "active": True,
                "service": "Маникюр",
                "last_question": "name",
            },
            "expected_reply_type": "name",
            "session_memory": {
                "active_goal": "booking",
                "last_question_type": "name",
            },
        },
        conversation_state=ConversationState.PENDING.value,
        policy_core_timeout_degrade=True,
        resume_boundary_active=True,
        now=now,
        prompt_builder=lambda expected_reply_type: {
            "name": "Как к вам обращаться?",
            "time": "Когда вам удобно?",
        }.get(expected_reply_type),
        required_expected_reply_type="time",
    )

    assert payload is None


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

    def test_reset_clears_counter_and_retry_timestamp(self):
        now = datetime.now(timezone.utc)
        conversation = SimpleNamespace(
            context={"low_confidence_retry_count": "oops", "other": "value"},
            retry_offered_at=now,
        )

        legacy._reset_low_confidence_retry(conversation)

        assert conversation.context == {
            "low_confidence_retry_count": 0,
            "other": "value",
        }
        assert conversation.retry_offered_at is None

    def test_update_compact_summary_routes_through_bridge_without_changing_payload_shape(self):
        now = datetime.now(timezone.utc)
        saved_message = SimpleNamespace(message_metadata={})
        conversation = SimpleNamespace(
            context={
                "booking": {
                    "service": "  Стрижка  ",
                    "datetime": " завтра после 15:00 ",
                },
                "context_manager": {
                    "refusal_flags": {
                        "phone": {"value": True},
                    }
                },
            },
            retry_offered_at=None,
        )

        with patch("app.routers.webhook._legacy._resolve_backlog_language", return_value="ru"):
            legacy._update_compact_summary(
                conversation=conversation,
                saved_message=saved_message,
                reason="clarify_limit",
                now=now,
            )

        compact_summary = conversation.context["context_manager"]["compact_summary"]

        assert compact_summary == {
            "text": "Услуга: Стрижка; Время: завтра после 15:00; Телефон: отказ; Язык: ru",
            "updated_at": now.isoformat(),
            "reason": "clarify_limit",
        }
        assert saved_message.message_metadata["decision_meta"]["summary_updated"] == "clarify_limit"
        trace = conversation.context["decision_trace"]
        assert trace[-1]["stage"] == "context_manager"
        assert trace[-1]["decision"] == "summary_updated"
        assert trace[-1]["summary_text"] == compact_summary["text"]

    def test_register_clarify_attempt_routes_state_through_bridge(self):
        now = datetime.now(timezone.utc)
        saved_message = SimpleNamespace(message_metadata={})
        conversation = SimpleNamespace(
            context={
                "context_manager": {
                    "clarify_attempts": {
                        "info": {
                            "count": "oops",
                            "last_at": "2026-03-15T09:00:00+00:00",
                        }
                    }
                }
            },
            retry_offered_at=None,
        )

        count = legacy._register_clarify_attempt(
            conversation=conversation,
            saved_message=saved_message,
            intent="info",
            now=now,
            reason="low_confidence_retry",
        )

        attempts = conversation.context["context_manager"]["clarify_attempts"]

        assert count == 1
        assert attempts["info"] == {
            "count": 1,
            "last_at": now.isoformat(),
        }
        meta = saved_message.message_metadata["decision_meta"]
        assert "summary_updated" not in meta
        trace = conversation.context["decision_trace"]
        assert trace[-1]["stage"] == "context_manager"
        assert trace[-1]["decision"] == "clarify_attempt"
        assert trace[-1]["clarify_attempt"] == {
            "intent": "info",
            "count": 1,
            "last_at": now.isoformat(),
        }
        assert trace[-1]["clarify_reason"] == "low_confidence_retry"


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
