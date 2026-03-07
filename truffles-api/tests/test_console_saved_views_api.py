from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import ConsoleSavedViewCreateRequest, ConsoleSavedViewUpdateRequest
from app.services import console_saved_views as saved_views_service
from app.services.console_errors import ConsoleAPIError


def _mock_context(
    *,
    role: str = "manager",
    client_id=None,
    agent_id=None,
    selected_branch_id=None,
    allowed_branch_ids=None,
):
    selected_branch_id = selected_branch_id or uuid4()
    return SimpleNamespace(
        role=role,
        agent=SimpleNamespace(id=agent_id or uuid4(), branch_id=selected_branch_id),
        client=SimpleNamespace(id=client_id or uuid4()),
        selected_branch_id=selected_branch_id,
        allowed_branch_ids=allowed_branch_ids if allowed_branch_ids is not None else {selected_branch_id},
        branch_restricted=False,
    )


def _saved_view_record(
    *,
    surface: str = "cases",
    name: str = "My open",
    is_default: bool = False,
    query_state=None,
):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        agent_id=uuid4(),
        surface=surface,
        name=name,
        version=1,
        query_state=query_state or {
            "mode_scope": "open",
            "base_view": "all_open",
            "owner_scope": {"kind": "all", "agent_id": None},
            "refinements": {},
        },
        is_default=is_default,
        created_at=now,
        updated_at=now,
    )


def test_normalize_saved_view_name_rejects_blank() -> None:
    with pytest.raises(ConsoleAPIError) as exc_info:
        saved_views_service.normalize_saved_view_name("   ")

    assert exc_info.value.code == "INVALID_PARAM"


def test_create_saved_view_rejects_duplicate_name(monkeypatch) -> None:
    db = Mock()
    duplicate = _saved_view_record()

    monkeypatch.setattr(saved_views_service, "_get_saved_view_by_name", lambda *args, **kwargs: duplicate)

    with pytest.raises(ConsoleAPIError) as exc_info:
        saved_views_service.create_saved_view(
            db,
            client_id=uuid4(),
            agent_id=uuid4(),
            surface="cases",
            name="My open",
            version=1,
            query_state={"mode_scope": "open", "base_view": "all_open", "owner_scope": {"kind": "all", "agent_id": None}, "refinements": {}},
            is_default=False,
        )

    assert exc_info.value.code == "CONFLICT"


def test_create_saved_view_clears_existing_default_when_requested(monkeypatch) -> None:
    db = Mock()
    client_id = uuid4()
    agent_id = uuid4()
    captured = {}

    monkeypatch.setattr(saved_views_service, "_get_saved_view_by_name", lambda *args, **kwargs: None)

    def _fake_clear_defaults(db_arg, *, client_id, agent_id, surface, exclude_view_id=None):
        captured["client_id"] = client_id
        captured["agent_id"] = agent_id
        captured["surface"] = surface
        captured["exclude_view_id"] = exclude_view_id

    monkeypatch.setattr(saved_views_service, "_clear_default_saved_views", _fake_clear_defaults)
    monkeypatch.setattr(
        saved_views_service,
        "ConsoleSavedView",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )

    record = saved_views_service.create_saved_view(
        db,
        client_id=client_id,
        agent_id=agent_id,
        surface="cases",
        name="Needs reply",
        version=1,
        query_state={"mode_scope": "open", "base_view": "needs_reply", "owner_scope": {"kind": "all", "agent_id": None}, "refinements": {}},
        is_default=True,
    )

    assert captured == {
        "client_id": client_id,
        "agent_id": agent_id,
        "surface": "cases",
        "exclude_view_id": None,
    }
    assert record.is_default is True


def test_update_saved_view_clears_existing_default_when_requested(monkeypatch) -> None:
    db = Mock()
    record = _saved_view_record(is_default=False)
    captured = {}

    def _fake_clear_defaults(db_arg, *, client_id, agent_id, surface, exclude_view_id=None):
        captured["client_id"] = client_id
        captured["agent_id"] = agent_id
        captured["surface"] = surface
        captured["exclude_view_id"] = exclude_view_id

    monkeypatch.setattr(saved_views_service, "_clear_default_saved_views", _fake_clear_defaults)

    updated = saved_views_service.update_saved_view(
        db,
        record=record,
        is_default=True,
    )

    assert captured == {
        "client_id": record.client_id,
        "agent_id": record.agent_id,
        "surface": record.surface,
        "exclude_view_id": record.id,
    }
    assert updated.is_default is True


@pytest.mark.asyncio
async def test_create_queue_state_view_normalizes_cases_payload(monkeypatch) -> None:
    branch_id = uuid4()
    context = _mock_context(selected_branch_id=branch_id, allowed_branch_ids={branch_id})
    saved_at = datetime.now(timezone.utc)
    body = ConsoleSavedViewCreateRequest(
        surface="cases",
        name="  Needs reply  ",
        query_state={
            "mode_scope": "open",
            "base_view": "needs_reply",
            "owner_scope": {"kind": "unassigned"},
            "refinements": {
                "branch_id": str(branch_id),
                "query": "  follow up  ",
                "has_delivery_error": True,
            },
        },
        is_default=True,
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    captured = {}

    def _fake_create(db, *, client_id, agent_id, surface, name, version, query_state, is_default):
        captured["client_id"] = client_id
        captured["agent_id"] = agent_id
        captured["surface"] = surface
        captured["name"] = name
        captured["version"] = version
        captured["query_state"] = query_state
        captured["is_default"] = is_default
        return SimpleNamespace(
            id=uuid4(),
            surface=surface,
            name=name,
            version=version,
            query_state=query_state,
            is_default=is_default,
            created_at=saved_at,
            updated_at=saved_at,
        )

    monkeypatch.setattr(console_router, "_create_saved_view", _fake_create)

    response = await console_router.create_queue_state_view(
        body=body,
        request=Mock(),
        db=Mock(),
    )

    assert captured["client_id"] == context.client.id
    assert captured["agent_id"] == context.agent.id
    assert captured["surface"] == "cases"
    assert captured["name"] == "  Needs reply  "
    assert captured["query_state"]["owner_scope"] == {"kind": "all", "agent_id": None}
    assert captured["query_state"]["refinements"]["query"] == "follow up"
    assert response.name == "  Needs reply  "
    assert response.is_default is True


@pytest.mark.asyncio
async def test_list_queue_state_views_requires_surface_permission(monkeypatch) -> None:
    context = _mock_context(role="viewer")
    record = _saved_view_record(surface="calendar", name="No-show")

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    permission_calls = []

    def _fake_require_permission(context_arg, section, action, **_kwargs):
        permission_calls.append((section, action, context_arg.role))

    monkeypatch.setattr(console_router, "require_console_permission", _fake_require_permission)
    monkeypatch.setattr(console_router, "_list_saved_views", lambda *args, **kwargs: [record])

    response = await console_router.list_queue_state_views(
        request=Mock(query_params={"surface": "calendar"}),
        surface="calendar",
        db=Mock(),
    )

    assert permission_calls == [("calendar", "read", "viewer")]
    assert len(response.items) == 1
    assert response.items[0].surface == "calendar"


@pytest.mark.asyncio
async def test_update_queue_state_view_returns_not_found(monkeypatch) -> None:
    context = _mock_context()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "_get_saved_view_for_owner", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.update_queue_state_view(
            view_id=uuid4(),
            body=ConsoleSavedViewUpdateRequest(name="Updated"),
            request=Mock(),
            db=Mock(),
        )

    assert exc_info.value.code == "NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_queue_state_view_calls_delete(monkeypatch) -> None:
    context = _mock_context()
    record = _saved_view_record()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_get_saved_view_for_owner", lambda *args, **kwargs: record)

    deleted = {}

    def _fake_delete(db, *, record):
        deleted["record"] = record

    monkeypatch.setattr(console_router, "_delete_saved_view", _fake_delete)

    response = await console_router.delete_queue_state_view(
        view_id=record.id,
        request=Mock(),
        db=Mock(),
    )

    assert deleted["record"] is record
    assert response.status_code == 200
