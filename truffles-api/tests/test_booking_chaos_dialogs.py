import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from app.models import Client, ClientSettings, Conversation, User
from app.models.branch import Branch
from app.routers import webhook as webhook_router
from app.schemas.webhook import WebhookBody, WebhookMetadata, WebhookRequest
from app.services.result import Result
from app.services.state_machine import ConversationState


def _make_db(client, settings, conversation, user):
    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    settings_query = Mock()
    settings_query.filter.return_value.first.return_value = settings
    conversation_query = Mock()
    conversation_query.filter.return_value.first.return_value = conversation
    user_query = Mock()
    user_query.filter.return_value.first.return_value = user
    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = None
    branch_phone_query = Mock()
    branch_phone_query.filter.return_value.all.return_value = []

    db = Mock()
    def _query(model):
        if model is Client:
            return client_query
        if model is ClientSettings:
            return settings_query
        if model is Conversation:
            return conversation_query
        if model is User:
            return user_query
        if model is Branch:
            return branch_query
        if model is Branch.phone:
            return branch_phone_query
        return Mock()

    db.query.side_effect = _query
    db.add = Mock()
    db.flush = Mock()
    db.commit = Mock()
    return db


def test_booking_chaos_dialog_suite_slot_lock_and_commit_trace():
    saved_messages = [Mock() for _ in range(7)]
    for saved_message in saved_messages:
        saved_message.message_metadata = {}

    client = SimpleNamespace(id="client-123", name="demo_salon", config={})
    settings = SimpleNamespace(
        webhook_secret=None,
        branch_resolution_mode="disabled",
        remember_branch_preference=True,
    )
    conversation_id = uuid4()
    conversation = SimpleNamespace(
        id=conversation_id,
        user_id="user-123",
        client_id=client.id,
        state=ConversationState.BOT_ACTIVE.value,
        bot_status="active",
        bot_muted_until=None,
        last_message_at=None,
        no_count=0,
        telegram_topic_id=None,
        escalated_at=None,
        branch_id=None,
        context={},
    )
    user = SimpleNamespace(id="user-123", context={})

    messages = [
        "Добрый день",
        "Нужен маникюр",
        "а вы бот?",
        "Запишите на завтра 15:00",
        "ой, пробки жесть",
        "Меня зовут Алия",
        "Спасибо",
    ]
    payloads = []
    for idx, text in enumerate(messages, start=1):
        payloads.append(
            WebhookRequest(
                client_slug="demo_salon",
                body=WebhookBody(
                    message=text,
                    messageType="text",
                    metadata=WebhookMetadata(
                        remoteJid="77000000000@s.whatsapp.net",
                        messageId=f"msg-chaos-{idx}",
                        timestamp=1234567900 + idx,
                    ),
                ),
            )
        )

    appointment_stub = SimpleNamespace(id=uuid4(), status="PENDING_CONFIRMATION")
    appointment_meta = {
        "appointment_id": str(appointment_stub.id),
        "appointment_status": appointment_stub.status,
        "booking_mode": "collect_preferences",
        "availability_provider": "none",
        "effective_booking_mode": "collect_preferences",
    }

    llm_result = Result.success((None, "low_confidence"))

    with patch(
        "app.routers.webhook._legacy._get_policy_handler", return_value=None
    ), patch(
        "app.routers.webhook._legacy.send_bot_response", return_value=True
    ), patch(
        "app.routers.webhook._legacy._find_message_by_message_id",
        side_effect=saved_messages,
    ), patch(
        "app.routers.webhook._legacy._get_user_branch_preference", return_value=None
    ), patch(
        "app.routers.webhook._legacy.should_process_debounced_message",
        AsyncMock(return_value=True),
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response",
        return_value=llm_result,
    ), patch(
        "app.routers.webhook.booking._create_booking_appointment",
        return_value=(appointment_stub, dict(appointment_meta)),
    ), patch(
        "app.routers.webhook._legacy._reuse_active_handover",
        return_value=(None, True, False),
    ):
        for payload in payloads:
            asyncio.run(
                webhook_router._handle_webhook_payload(
                    payload,
                    _make_db(client, settings, conversation, user),
                    provided_secret=None,
                    enforce_secret=False,
                    skip_persist=True,
                    conversation_id=conversation_id,
                )
            )

    booking_context = conversation.context.get("booking", {})
    assert booking_context.get("service")
    assert booking_context.get("datetime")
    assert booking_context.get("name")

    trace = conversation.context.get("decision_trace") or []
    assert any(item.get("stage") == "booking_commit" for item in trace)
