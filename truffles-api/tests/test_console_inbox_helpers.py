from app.routers import console as console_router


def test_normalize_phone_digits():
    assert console_router._normalize_phone_digits("+7 (777) 123-45-67") == "77771234567"


def test_looks_like_uuid():
    assert console_router._looks_like_uuid("550e8400-e29b-41d4-a716-446655440000") is not None
    assert console_router._looks_like_uuid("not-a-uuid") is None


def test_resolve_last_activity_channel_user():
    assert console_router._resolve_last_activity_channel(
        role="user",
        metadata=None,
        conversation_channel="whatsapp",
    ) == "whatsapp"


def test_resolve_last_activity_channel_manager_sources():
    assert console_router._resolve_last_activity_channel(
        role="manager",
        metadata={"source": "telegram"},
        conversation_channel="whatsapp",
    ) == "telegram"
    assert console_router._resolve_last_activity_channel(
        role="manager",
        metadata=None,
        conversation_channel="whatsapp",
    ) == "console"


def test_resolve_last_activity_channel_system():
    assert console_router._resolve_last_activity_channel(
        role="assistant",
        metadata={"source": "system"},
        conversation_channel="whatsapp",
    ) == "system"
