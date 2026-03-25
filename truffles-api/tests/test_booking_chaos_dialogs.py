import asyncio
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from app.models import Client, ClientSettings, Conversation, User
from app.models.branch import Branch
from app.routers import webhook as webhook_router
from app.schemas.webhook import WebhookBody, WebhookMetadata, WebhookRequest
from app.services import handover_owner_service
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
    dialogue = [
        {"text": "привет, можно записаться?", "expect_reply_type": "service_choice"},
        {"text": "мне бы ногти сделать", "expect_reply_type": "time"},
        {"text": "а вы бот вообще?", "expect_reply_type": "time"},
        {"text": "сколько стоит примерно?", "expect_reply_type": "time"},
        {"text": "завтра после обеда можно?", "expect_reply_type": "name"},
        {"text": "ой нет, лучше к вечеру, часов в 7", "expect_reply_type": "name"},
        {"text": "ээ, имя скажу позже", "expect_reply_type": "name"},
        {"text": "меня зовут Алия", "expect_reply_type": None},
        {"text": "спасибо", "expect_reply_type": None},
    ]
    saved_messages = [Mock() for _ in range(len(dialogue))]
    for saved_message in saved_messages:
        saved_message.message_metadata = {}

    client = SimpleNamespace(id=uuid4(), name="demo_salon", config={})
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

    payloads = []
    for idx, turn in enumerate(dialogue, start=1):
        payloads.append(
            WebhookRequest(
                client_slug="demo_salon",
                body=WebhookBody(
                    message=turn["text"],
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

    def _stub_service_hint(message_text, _client_slug):
        if not message_text:
            return None
        normalized = message_text.casefold()
        if re.search(r"маникюр|ногти|ногот", normalized):
            return "маникюр"
        if "педикюр" in normalized:
            return "педикюр"
        if "ресниц" in normalized:
            return "ресницы"
        return None

    def _stub_datetime(message_text, *, client_slug=None):
        if not message_text:
            return None
        normalized = message_text.casefold()
        if "после обеда" in normalized:
            return "15:00"
        if "вечер" in normalized or "к вечеру" in normalized:
            return "19:00"
        match = re.search(r"(\d{1,2})(?:[:. ](\d{2}))?", normalized)
        if match:
            hour = int(match.group(1))
            minute = match.group(2) or "00"
            if "вечер" in normalized or "после обеда" in normalized:
                if hour < 12:
                    hour += 12
            return f"{hour:02d}:{minute}"
        if "завтра" in normalized:
            return "завтра"
        return None

    stub_answer = {
        "ok": False,
        "payload": {
            "slot": "",
            "value": "",
            "confidence": 0.0,
        },
        "error": "stubbed",
    }

    def _reuse_active_handover(*, hooks, **_kwargs):
        assert isinstance(
            hooks,
            handover_owner_service.ActiveHandoverReuseRuntimeHooks,
        )
        return None, True, False

    with patch(
        "app.routers.webhook.decision.LLM_POLICY_CORE_ENABLED",
        False,
    ), patch(
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
        "app.routers.webhook._legacy._extract_service_hint",
        side_effect=_stub_service_hint,
    ), patch(
        "app.routers.webhook._legacy._extract_datetime",
        side_effect=_stub_datetime,
    ), patch(
        "app.routers.webhook._legacy._get_recent_service_hint",
        return_value=None,
    ), patch(
        "app.routers.webhook._legacy.interpret_expected_reply",
        return_value=stub_answer,
    ), patch(
        "app.routers.webhook._legacy.generate_bot_response",
        return_value=llm_result,
    ), patch(
        "app.routers.webhook.booking._create_booking_appointment",
        return_value=(appointment_stub, dict(appointment_meta)),
    ) as create_booking, patch(
        "app.routers.webhook._legacy._reuse_active_handover",
        side_effect=_reuse_active_handover,
    ), patch(
        "app.routers.webhook._legacy.route_dialogue_controller",
        return_value={"ok": False, "error": "skipped"},
    ):
        for payload, turn in zip(payloads, dialogue):
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
            if "expect_reply_type" in turn:
                assert (
                    conversation.context.get("expected_reply_type") == turn["expect_reply_type"]
                )

    assert create_booking.call_count == 1
    booking_state = create_booking.call_args.kwargs["booking_state"]
    assert booking_state.get("service")
    assert booking_state.get("datetime")
    assert booking_state.get("name")

    trace = conversation.context.get("decision_trace") or []
    assert any(item.get("stage") == "booking_commit" for item in trace)
