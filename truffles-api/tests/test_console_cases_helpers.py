from datetime import datetime, timedelta, timezone

import pytest

from app.routers import console as console_router
from app.services.console_errors import ConsoleAPIError


def test_parse_sort_param_defaults_to_last_activity():
    assert console_router._parse_sort_param("sort_by", None) == "last_activity"
    assert console_router._parse_sort_param("sort_by", "") == "last_activity"
    assert console_router._parse_sort_param("sort_by", "last_activity") == "last_activity"


def test_parse_sort_param_accepts_created_at():
    assert console_router._parse_sort_param("sort_by", "created_at") == "created_at"
    assert console_router._parse_sort_param("sort_by", "CREATED_AT") == "created_at"


def test_parse_sort_param_accepts_sla():
    assert console_router._parse_sort_param("sort_by", "sla") == "sla"
    assert console_router._parse_sort_param("sort_by", "SLA") == "sla"


def test_parse_sort_param_rejects_invalid():
    with pytest.raises(ConsoleAPIError):
        console_router._parse_sort_param("sort_by", "oops")


def test_case_status_open_param():
    assert console_router._parse_case_status_param("status", None) is None
    assert console_router._parse_case_status_param("status", "") is None
    assert console_router._parse_case_status_param("status", "open") == ["pending", "active"]
    assert console_router._parse_case_status_param("status", "OPEN") == ["pending", "active"]
    assert console_router._parse_case_status_param("status", "pending") == ["pending"]
    assert console_router._parse_case_status_param("status", "active") == ["active"]
    assert console_router._parse_case_status_param("status", "resolved") == ["resolved"]


def test_parse_case_status_param_rejects_invalid():
    with pytest.raises(ConsoleAPIError):
        console_router._parse_case_status_param("status", "oops")


def test_normalize_search_query():
    assert console_router._normalize_search_query("q", None) is None
    assert console_router._normalize_search_query("q", "   ") is None
    assert console_router._normalize_search_query("q", "  Alice  ") == "Alice"


def test_normalize_search_query_rejects_invalid():
    with pytest.raises(ConsoleAPIError):
        console_router._normalize_search_query("q", "a" * 129)
    with pytest.raises(ConsoleAPIError):
        console_router._normalize_search_query("q", "bad\x00value")
    with pytest.raises(ConsoleAPIError):
        console_router._normalize_search_query("q", "line\nbreak")


def test_resolve_case_sort_cursor():
    created_at = datetime.now(timezone.utc)
    last_activity = created_at - timedelta(minutes=5)

    assert console_router._resolve_case_sort_cursor(
        sort_by="last_activity",
        last_activity_at=last_activity,
        created_at=created_at,
    ) == last_activity
    assert console_router._resolve_case_sort_cursor(
        sort_by="last_activity",
        last_activity_at=None,
        created_at=created_at,
    ) == created_at
    assert console_router._resolve_case_sort_cursor(
        sort_by="created_at",
        last_activity_at=last_activity,
        created_at=created_at,
    ) == created_at
    assert console_router._resolve_case_sort_cursor(
        sort_by="sla",
        last_activity_at=last_activity,
        created_at=created_at,
    ) == created_at
