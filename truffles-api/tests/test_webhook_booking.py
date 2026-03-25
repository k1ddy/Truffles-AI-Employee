import pytest

from app.routers import webhook
from app.routers.webhook import booking as booking_router


def test_get_set_expected_reply_type_round_trip():
    context = {
        "expected_reply_type": "  service  ",
        "expected_reply_reason": "  booking_prompt  ",
    }
    assert webhook._get_expected_reply_type(context) == "service"
    assert webhook._get_expected_reply_reason(context) == "booking_prompt"

    updated = webhook._set_expected_reply_type(context, "  time ")
    assert updated[webhook.EXPECTED_REPLY_TYPE_KEY] == "time"
    assert webhook.EXPECTED_REPLY_REASON_KEY not in updated

    cleared = webhook._set_expected_reply_type(updated, "  ")
    assert webhook.EXPECTED_REPLY_TYPE_KEY not in cleared


@pytest.mark.parametrize(
    "message_text,expected",
    [
        ("Меня зовут Маша", "Маша"),
        ("Анна", "Анна"),
    ],
)
def test_validate_name_slot_accepts_name(message_text, expected):
    result = webhook._validate_name_slot(
        message_text,
        allow_freeform=True,
        client_slug=None,
    )

    assert result == expected


@pytest.mark.parametrize(
    "message_text",
    [
        "привет",
        "да",
        "меня зовут 123",
        "проверь запись",
        "подтверди запись",
    ],
)
def test_validate_name_slot_rejects_noise(message_text):
    result = webhook._validate_name_slot(
        message_text,
        allow_freeform=True,
        client_slug=None,
    )

    assert result is None


def test_match_expected_reply_for_datetime():
    matched, value, _flags = webhook._match_expected_reply(
        expected_reply_type=webhook.EXPECTED_REPLY_TIME,
        message_text="Запишите на 12:30",
        client_slug=None,
    )

    assert matched is True
    assert value == "12:30"


def test_match_expected_reply_for_name():
    matched, value, _flags = webhook._match_expected_reply(
        expected_reply_type=webhook.EXPECTED_REPLY_NAME,
        message_text="Меня зовут Лиза",
        client_slug=None,
    )

    assert matched is True
    assert value == "Лиза"


def test_expected_reply_blocked_for_style_reference_text():
    blocked = webhook._should_block_expected_reply_by_info(
        expected_reply_type=webhook.EXPECTED_REPLY_NAME,
        message_text="Вот фото референса",
        client_slug="demo_salon",
    )

    assert blocked is True


def test_booking_confirmation_deferred_for_info_interrupt():
    deferred = booking_router._should_defer_booking_confirmation_for_info(
        confirmation={"slot": "datetime", "value": "12:58"},
        basic_info_message=True,
        message_text="Есть ли у вас парковка?",
        client_slug="demo_salon",
    )

    assert deferred is True


def test_booking_flow_deferred_for_info_interrupt():
    deferred = booking_router._should_defer_booking_flow_for_info_interrupt(
        booking_active=True,
        booking_signal=False,
        booking_related=False,
        basic_info_message=True,
    )

    assert deferred is True


@pytest.mark.parametrize(
    "message_text,expected",
    [
        ("Можно на 19:00?", True),
        ("Меня зовут Лена", True),
        ("Телефон +7 701 111 22 33", True),
        ("Сколько стоит маникюр?", False),
    ],
)
def test_booking_slot_signal(message_text, expected):
    result = webhook._is_booking_slot_signal(message_text, client_slug="demo_salon")

    assert result is expected
