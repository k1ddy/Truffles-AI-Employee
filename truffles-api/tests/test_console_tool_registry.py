from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import ConsoleToolRegistryUpsertRequest
from app.services.console_errors import ConsoleAPIError


def _mock_context(*, role: str = "platform_admin", client_id=None, agent_id=None):
    return SimpleNamespace(
        role=role,
        agent=SimpleNamespace(id=agent_id or uuid4(), name="Agent"),
        client=SimpleNamespace(id=client_id or uuid4()),
    )


@pytest.mark.asyncio
async def test_list_tool_registry_requires_platform_admin(monkeypatch):
    context = _mock_context(role="owner")
    db = Mock()

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda request, db, require_selection=False: context,
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_tool_registry(
            request=Mock(),
            status=None,
            certification_status=None,
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_upsert_tool_registry_creates_record(monkeypatch):
    context = _mock_context(role="platform_admin")
    db = Mock()
    now = datetime.now(timezone.utc)
    body = ConsoleToolRegistryUpsertRequest(
        title="Calendar Slots",
        certification_status="certified",
        health_status="healthy",
        allowed_scopes=["client", "branch"],
    )

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda request, db, require_selection=False: context,
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        console_router,
        "_get_tool_registry_entry_record",
        lambda *_args, **_kwargs: None,
    )

    def _assign_defaults(record):
        if getattr(record, "id", None) is None:
            record.id = uuid4()
        if getattr(record, "created_at", None) is None:
            record.created_at = now
        if getattr(record, "updated_at", None) is None:
            record.updated_at = now

    db.add.side_effect = _assign_defaults

    response = await console_router.upsert_tool_registry(
        tool_action="calendar.list_slots",
        body=body,
        request=Mock(),
        db=db,
    )

    assert response.tool_action == "calendar.list_slots"
    assert response.tool_group == "calendar"
    assert response.certification_status == "certified"
    assert response.health_status == "healthy"
    assert response.allowed_scopes == ["client", "branch"]
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_tool_registry_rejects_invalid_action(monkeypatch):
    context = _mock_context(role="platform_admin")
    db = Mock()
    body = ConsoleToolRegistryUpsertRequest()

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda request, db, require_selection=False: context,
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.upsert_tool_registry(
            tool_action="calendar.*",
            body=body,
            request=Mock(),
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"
