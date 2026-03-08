from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import ConsoleRoutingProfileUpsertRequest
from app.services.console_errors import ConsoleAPIError


def _mock_context(*, role: str = "admin", client_id=None, agent_id=None):
    return SimpleNamespace(
        role=role,
        agent=SimpleNamespace(id=agent_id or uuid4(), name="Supervisor", branch_id=None),
        client=SimpleNamespace(id=client_id or uuid4()),
        selected_branch_id=None,
        allowed_branch_ids=set(),
        branch_restricted=False,
    )


def test_serialize_routing_profile_sets_scope_from_branch() -> None:
    record = SimpleNamespace(
        id=uuid4(),
        agent_id=uuid4(),
        client_id=uuid4(),
        branch_id=uuid4(),
        routing_status="paused",
        max_open_case_count=3,
        updated_by_agent_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    serialized = console_router._serialize_routing_profile(record, agent_name="Agent")

    assert serialized.scope == "branch"
    assert serialized.agent_name == "Agent"
    assert serialized.routing_status == "paused"


@pytest.mark.asyncio
async def test_upsert_routing_profile_rejects_non_assignable_agent_role(monkeypatch) -> None:
    client_id = uuid4()
    agent_id = uuid4()
    context = _mock_context(client_id=client_id)
    body = ConsoleRoutingProfileUpsertRequest(
        agent_id=agent_id,
        client_id=client_id,
        routing_status="available",
    )
    agent = SimpleNamespace(id=agent_id, client_id=client_id, role="viewer", name="Viewer")

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db, **kwargs: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_require_client_access", lambda *args, **kwargs: None)

    agent_query = Mock()
    agent_query.filter.return_value.first.return_value = agent
    db = Mock()
    db.query.return_value = agent_query

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.upsert_routing_profile(
            request=Mock(),
            body=body,
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"
    assert "not eligible for case routing" in exc_info.value.message


@pytest.mark.asyncio
async def test_list_routing_profiles_serializes_agent_names(monkeypatch) -> None:
    client_id = uuid4()
    agent_id = uuid4()
    context = _mock_context(client_id=client_id)
    record = SimpleNamespace(
        id=uuid4(),
        agent_id=agent_id,
        client_id=client_id,
        branch_id=None,
        routing_status="available",
        max_open_case_count=5,
        updated_by_agent_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db, **kwargs: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_require_client_access", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_list_routing_profiles_service", lambda *args, **kwargs: [record])

    agent_query = Mock()
    agent_query.filter.return_value.all.return_value = [
        SimpleNamespace(id=agent_id, name="Agent One"),
    ]
    db = Mock()
    db.query.return_value = agent_query

    response = await console_router.list_routing_profiles(
        request=Mock(),
        client_id=str(client_id),
        agent_id=None,
        branch_id=None,
        db=db,
    )

    assert len(response.items) == 1
    assert response.items[0].agent_name == "Agent One"
    assert response.items[0].scope == "client"


@pytest.mark.asyncio
async def test_delete_routing_profile_returns_success(monkeypatch) -> None:
    client_id = uuid4()
    agent_id = uuid4()
    context = _mock_context(client_id=client_id)
    record = SimpleNamespace(
        id=uuid4(),
        agent_id=agent_id,
        client_id=client_id,
        branch_id=None,
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db, **kwargs: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_require_client_access", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_delete_routing_profile_service", lambda *args, **kwargs: record)
    audit_mock = Mock()
    monkeypatch.setattr(console_router, "record_audit_event", audit_mock)
    db = Mock()

    response = await console_router.delete_routing_profile(
        agent_id=agent_id,
        request=Mock(),
        client_id=str(client_id),
        branch_id=None,
        reason="cleanup",
        db=db,
    )

    assert response.success is True
    db.commit.assert_called_once()
    audit_mock.assert_called_once()
