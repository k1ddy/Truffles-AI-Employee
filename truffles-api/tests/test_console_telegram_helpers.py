from app.routers import console as console_router


def test_build_telegram_link_private_group():
    assert (
        console_router._build_telegram_link("-1001234567890", 42)
        == "https://t.me/c/1234567890/42"
    )


def test_build_telegram_link_with_topic():
    assert (
        console_router._build_telegram_link("-1001234567890", 42, 5112)
        == "https://t.me/c/1234567890/5112"
    )


def test_build_telegram_desktop_link():
    assert (
        console_router._build_telegram_desktop_link("-1001234567890", 42)
        == "tg://openmessage?chat_id=-1001234567890&message_id=42"
    )


def test_build_telegram_desktop_link_with_topic():
    assert (
        console_router._build_telegram_desktop_link("-1001234567890", 42, 5112)
        == "tg://openmessage?chat_id=-1001234567890&message_id=5112"
    )


def test_build_telegram_desktop_link_rejects_invalid_chat():
    assert console_router._build_telegram_desktop_link("chat", 42) is None


def test_build_telegram_link_rejects_non_private_group():
    assert console_router._build_telegram_link("123456", 42) is None


def test_build_telegram_link_rejects_invalid_id():
    assert console_router._build_telegram_link("-100abc", 42) is None


def test_format_telegram_timestamp():
    value = 1700000000
    formatted = console_router._format_telegram_timestamp(value)
    assert formatted is not None
    assert formatted.endswith("+00:00")
