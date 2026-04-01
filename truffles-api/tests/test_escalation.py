from uuid import uuid4

from app.services.telegram_service import (
    build_handover_buttons,
    format_handover_message,
)


class TestBuildHandoverButtons:
    def test_buttons_structure(self):
        handover_id = uuid4()
        buttons = build_handover_buttons(handover_id)

        assert "inline_keyboard" in buttons
        assert len(buttons["inline_keyboard"]) == 2
        assert len(buttons["inline_keyboard"][0]) == 2  # [Беру][Вернуть боту]
        assert len(buttons["inline_keyboard"][1]) == 1  # [Не могу]

    def test_button_callbacks(self):
        handover_id = uuid4()
        buttons = build_handover_buttons(handover_id)

        row1 = buttons["inline_keyboard"][0]
        assert row1[0]["text"] == "Беру ✋"
        assert row1[0]["callback_data"] == f"take_{handover_id}"
        assert row1[1]["text"] == "Вернуть боту 🤖"
        assert row1[1]["callback_data"] == f"return_{handover_id}"

        row2 = buttons["inline_keyboard"][1]
        assert row2[0]["text"] == "Не могу ❌"
        assert row2[0]["callback_data"] == f"skip_{handover_id}"


class TestFormatHandoverMessage:
    def test_message_with_all_fields(self):
        text = format_handover_message(
            user_name="Иван",
            user_phone="+77012345678",
            message="Хочу поговорить с менеджером",
            trigger_type="human_request",
        )

        assert "Иван" in text
        assert "+77012345678" in text
        assert "Хочу поговорить с менеджером" in text
        assert "Клиент попросил менеджера" in text

    def test_message_with_missing_name(self):
        text = format_handover_message(
            user_name=None,
            user_phone="+77012345678",
            message="Test",
            trigger_type="frustration",
        )

        assert "Неизвестный" in text
        assert "Клиент раздражён" in text

    def test_message_with_missing_phone(self):
        text = format_handover_message(
            user_name="Иван",
            user_phone=None,
            message="Test",
            trigger_type="intent",
        )

        assert "нет номера" in text
