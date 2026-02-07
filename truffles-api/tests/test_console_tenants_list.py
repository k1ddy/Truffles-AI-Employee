from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from app.routers import console as console_router
from app.services.console_errors import ConsoleAPIError


def test_parse_uuid_param_accepts_valid() -> None:
    value = str(uuid4())

    parsed = console_router._parse_uuid_param("company_id", value)

    assert parsed == UUID(value)


def test_parse_uuid_param_rejects_invalid() -> None:
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._parse_uuid_param("company_id", "not-a-uuid")

    assert exc_info.value.code == "INVALID_PARAM"


def test_parse_tenant_lifecycle_param_defaults_to_active() -> None:
    assert console_router._parse_tenant_lifecycle_param(None) == "active"


@pytest.mark.parametrize("value", ["active", "archived", "all"])
def test_parse_tenant_lifecycle_param_accepts_allowed_values(value: str) -> None:
    assert console_router._parse_tenant_lifecycle_param(value) == value


def test_parse_tenant_lifecycle_param_rejects_invalid() -> None:
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._parse_tenant_lifecycle_param("inactive")

    assert exc_info.value.code == "INVALID_PARAM"


def _build_list_query_mock() -> Mock:
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = []
    return query


@pytest.mark.asyncio
async def test_list_clients_defaults_to_active_lifecycle(monkeypatch) -> None:
    query = _build_list_query_mock()
    db = Mock()
    db.query.return_value = query
    request = SimpleNamespace(query_params={})
    captured: dict[str, object] = {}

    def _fake_context(_request, _db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(role="platform_admin")

    monkeypatch.setattr(console_router, "get_console_context", _fake_context)

    await console_router.list_clients(
        request=request,
        db=db,
    )

    assert captured["require_selection"] is False
    assert captured["include_inactive_tenants"] is False
    first_filter = query.filter.call_args_list[0].args[0]
    assert str(first_filter) == "clients.status = :status_1"


@pytest.mark.asyncio
async def test_list_clients_archived_lifecycle_enables_inactive_scope(monkeypatch) -> None:
    query = _build_list_query_mock()
    db = Mock()
    db.query.return_value = query
    request = SimpleNamespace(query_params={"lifecycle": "archived"})
    captured: dict[str, object] = {}

    def _fake_context(_request, _db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(role="platform_admin")

    monkeypatch.setattr(console_router, "get_console_context", _fake_context)

    await console_router.list_clients(
        request=request,
        lifecycle="archived",
        db=db,
    )

    assert captured["include_inactive_tenants"] is True
    first_filter = query.filter.call_args_list[0].args[0]
    assert str(first_filter) == "clients.status != :status_1"


@pytest.mark.asyncio
async def test_list_branches_defaults_to_active_lifecycle(monkeypatch) -> None:
    query = _build_list_query_mock()
    db = Mock()
    db.query.return_value = query
    request = SimpleNamespace(query_params={})
    captured: dict[str, object] = {}

    def _fake_context(_request, _db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(role="platform_admin")

    monkeypatch.setattr(console_router, "get_console_context", _fake_context)

    await console_router.list_branches(
        request=request,
        db=db,
    )

    assert captured["include_inactive_tenants"] is False
    first_filter = query.filter.call_args_list[0].args[0]
    assert str(first_filter) == "branches.is_active IS true"


@pytest.mark.asyncio
async def test_list_branches_archived_lifecycle_filters_inactive(monkeypatch) -> None:
    query = _build_list_query_mock()
    db = Mock()
    db.query.return_value = query
    request = SimpleNamespace(query_params={"lifecycle": "archived"})
    captured: dict[str, object] = {}

    def _fake_context(_request, _db, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(role="platform_admin")

    monkeypatch.setattr(console_router, "get_console_context", _fake_context)

    await console_router.list_branches(
        request=request,
        lifecycle="archived",
        db=db,
    )

    assert captured["include_inactive_tenants"] is True
    first_filter = query.filter.call_args_list[0].args[0]
    assert str(first_filter) == "branches.is_active IS false"
