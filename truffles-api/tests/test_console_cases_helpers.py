from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

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


def test_format_case_metrics():
    first_response_at = datetime.now(timezone.utc)
    resolved_at = first_response_at + timedelta(minutes=12)
    handover = SimpleNamespace(
        first_response_at=first_response_at,
        resolved_at=resolved_at,
        resolution_time_seconds=720,
    )

    metrics = console_router._format_case_metrics(handover)

    assert metrics["first_response_at"] == first_response_at.isoformat()
    assert metrics["resolved_at"] == resolved_at.isoformat()
    assert metrics["resolution_time_seconds"] == 720


def test_require_branch_access_allows_matching_branch():
    branch_id = uuid4()
    context = SimpleNamespace(
        role="manager",
        branches=[SimpleNamespace(id=branch_id)],
    )
    console_router._require_branch_access(context, branch_id, message="Access denied")


def test_require_branch_access_allows_admin():
    branch_id = uuid4()
    context = SimpleNamespace(
        role="platform_admin",
        branches=[],
    )
    console_router._require_branch_access(context, branch_id, message="Access denied")


def test_require_branch_access_denies_other_branch():
    branch_id = uuid4()
    context = SimpleNamespace(
        role="manager",
        branches=[SimpleNamespace(id=uuid4())],
    )
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._require_branch_access(context, branch_id, message="Access denied")
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "ACCESS_DENIED"
