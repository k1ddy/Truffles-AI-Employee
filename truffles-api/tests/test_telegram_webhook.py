import asyncio
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from app.routers import telegram_webhook
from app.schemas.telegram import TelegramCallbackQuery, TelegramChat, TelegramMessage, TelegramUpdate, TelegramUser


class TestTelegramSchemas:
    def test_telegram_user(self):
        user = TelegramUser(id=123456, first_name="Иван", last_name="Петров", username="ivan_petrov")
        assert user.id == 123456
        assert user.first_name == "Иван"
        assert user.is_bot is False

    def test_telegram_chat(self):
        chat = TelegramChat(id=-1001234567890, type="supergroup", title="Менеджеры", is_forum=True)
        assert chat.id == -1001234567890
        assert chat.type == "supergroup"
        assert chat.is_forum is True

    def test_telegram_message(self):
        msg = TelegramMessage(
            message_id=100,
            date=1702000000,
            chat=TelegramChat(id=-1001234567890, type="supergroup"),
            text="Здравствуйте, чем могу помочь?",
            message_thread_id=42,
            **{"from": TelegramUser(id=123, first_name="Менеджер")},
        )
        assert msg.message_id == 100
        assert msg.text == "Здравствуйте, чем могу помочь?"
        assert msg.message_thread_id == 42
        assert msg.from_user.first_name == "Менеджер"

    def test_telegram_update_with_message(self):
        update = TelegramUpdate(
            update_id=1,
            message=TelegramMessage(
                message_id=100, date=1702000000, chat=TelegramChat(id=-100, type="supergroup"), text="Test"
            ),
        )
        assert update.update_id == 1
        assert update.message is not None
        assert update.callback_query is None

    def test_telegram_callback_query(self):
        callback = TelegramCallbackQuery(
            id="query123", data="take:uuid-here", **{"from": TelegramUser(id=123, first_name="Manager")}
        )
        assert callback.id == "query123"
        assert callback.data == "take:uuid-here"
        assert callback.from_user.id == 123


class TestTelegramUpdateParsing:
    def test_parse_full_update(self):
        raw = {
            "update_id": 123456789,
            "message": {
                "message_id": 100,
                "date": 1702000000,
                "chat": {"id": -1001234567890, "type": "supergroup", "title": "Test Group", "is_forum": True},
                "from": {"id": 111222333, "is_bot": False, "first_name": "Иван", "last_name": "Петров"},
                "text": "Привет, это ответ менеджера",
                "message_thread_id": 42,
            },
        }

        update = TelegramUpdate(**raw)
        assert update.update_id == 123456789
        assert update.message.chat.id == -1001234567890
        assert update.message.from_user.first_name == "Иван"
        assert update.message.text == "Привет, это ответ менеджера"
        assert update.message.message_thread_id == 42

    def test_parse_callback_query(self):
        raw = {
            "update_id": 123456790,
            "callback_query": {
                "id": "query_123",
                "from": {"id": 111222333, "is_bot": False, "first_name": "Manager"},
                "data": "take:550e8400-e29b-41d4-a716-446655440000",
            },
        }

        update = TelegramUpdate(**raw)
        assert update.callback_query is not None
        assert update.callback_query.data == "take:550e8400-e29b-41d4-a716-446655440000"


def test_simulation_resolve_uses_preserve_context():
    conversation_id = uuid4()
    handover = SimpleNamespace(id=str(uuid4()), conversation_id=conversation_id, status="pending")
    conversation = SimpleNamespace(
        id=conversation_id,
        client_id="client-1",
        branch_id=None,
        telegram_topic_id=None,
    )
    linked_agent = SimpleNamespace(id="agent-1", name="Manager", role="owner")

    db = Mock()

    def _query(model):
        query = Mock()
        model_name = getattr(model, "__name__", None)
        if model_name == "Handover":
            query.filter.return_value.first.return_value = handover
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        else:
            query.filter.return_value.first.return_value = None
        return query

    db.query.side_effect = _query
    db.commit = Mock()

    callback = TelegramCallbackQuery(
        id="cb-1",
        data="resolve_handover-1",
        message=TelegramMessage(
            message_id=10,
            date=1702000000,
            chat=TelegramChat(id=-1001234567890, type="supergroup"),
        ),
        **{"from": TelegramUser(id=101, is_bot=False, first_name="Sim")},
    )
    update = TelegramUpdate(update_id=1, callback_query=callback)
    resolve_result = SimpleNamespace(ok=True, error=None)

    with patch("app.services.callback_dedup.is_callback_processed", return_value=False), patch(
        "app.routers.telegram_webhook.resolve_linked_agent",
        return_value=linked_agent,
    ), patch(
        "app.routers.telegram_webhook._is_simulation_handover",
        return_value=True,
    ), patch(
        "app.routers.telegram_webhook.state_manager_resolve",
        return_value=resolve_result,
    ) as resolve_mock:
        response = asyncio.run(telegram_webhook.handle_callback_query(update, db))

    assert response.success is True
    assert response.message == "Resolved (simulation)"
    assert resolve_mock.call_args.kwargs.get("preserve_context") is True


def test_resolve_uses_preserve_context():
    conversation_id = uuid4()
    handover_id = uuid4()
    handover = SimpleNamespace(
        id=handover_id,
        conversation_id=conversation_id,
        status="pending",
        telegram_message_id=None,
        assigned_to=None,
        assigned_to_name=None,
    )
    conversation = SimpleNamespace(
        id=conversation_id,
        client_id="client-1",
        branch_id=None,
        telegram_topic_id=None,
    )
    linked_agent = SimpleNamespace(id=uuid4(), name="Manager", role="owner")

    db = Mock()

    def _query(model):
        query = Mock()
        model_name = getattr(model, "__name__", None)
        if model_name == "Handover":
            query.filter.return_value.first.return_value = handover
        elif model_name == "Conversation":
            query.filter.return_value.first.return_value = conversation
        else:
            query.filter.return_value.first.return_value = None
        return query

    db.query.side_effect = _query
    db.commit = Mock()

    callback = TelegramCallbackQuery(
        id="cb-2",
        data=f"resolve_{handover_id}",
        message=TelegramMessage(
            message_id=11,
            date=1702000000,
            chat=TelegramChat(id=-1001234567890, type="supergroup"),
        ),
        **{"from": TelegramUser(id=102, is_bot=False, first_name="Sim")},
    )
    update = TelegramUpdate(update_id=2, callback_query=callback)
    resolve_result = SimpleNamespace(ok=True, error=None)
    telegram = Mock()

    with patch("app.services.callback_dedup.is_callback_processed", return_value=False), patch(
        "app.routers.telegram_webhook.resolve_linked_agent",
        return_value=linked_agent,
    ), patch(
        "app.routers.telegram_webhook._is_simulation_handover",
        return_value=False,
    ), patch(
        "app.routers.telegram_webhook.get_bot_token_by_chat",
        return_value="token",
    ), patch(
        "app.routers.telegram_webhook.TelegramService",
        return_value=telegram,
    ), patch(
        "app.routers.telegram_webhook.state_manager_resolve",
        return_value=resolve_result,
    ) as resolve_mock, patch(
        "app.routers.telegram_webhook.record_audit_event",
    ), patch(
        "app.routers.telegram_webhook.notify_client_manager_status",
        return_value=(True, None),
    ):
        response = asyncio.run(telegram_webhook.handle_callback_query(update, db))

    assert response.success is True
    assert response.message == "Resolved"
    assert resolve_mock.call_args.kwargs.get("preserve_context") is True
