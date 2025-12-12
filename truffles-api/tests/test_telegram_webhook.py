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
