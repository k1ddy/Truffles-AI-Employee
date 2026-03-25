from datetime import datetime, timezone

from app.routers.webhook import decision as decision_router
from app.services import tool_registry_service


def test_extract_datetime_normalizes_tomorrow_adjective_phrase():
    value = decision_router._extract_datetime(
        "Я хочу записаться на завтрашний день.",
        client_slug="demo_salon",
        relative_base=datetime(2026, 2, 22, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert isinstance(value, str)
    assert "завтра" in value


def test_parse_datetime_accepts_relative_day_with_daypart():
    parsed = tool_registry_service._parse_datetime(
        "завтра днем",
        fallback_tz="Asia/Almaty",
        now=datetime(2026, 2, 22, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert parsed is not None
    assert parsed.hour == 14
