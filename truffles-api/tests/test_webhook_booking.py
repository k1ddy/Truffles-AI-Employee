import pytest

from app.routers import webhook


def test_get_set_expected_reply_type_round_trip():
    context = {"expected_reply_type": "  service  "}
    assert webhook._get_expected_reply_type(context) == "service"

    updated = webhook._set_expected_reply_type(context, "  time ")
    assert updated[webhook.EXPECTED_REPLY_TYPE_KEY] == "time"

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
