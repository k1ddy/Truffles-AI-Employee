from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import calendar as calendar_router
from app.services.console_errors import ConsoleAPIError


def _context(*, client_id=None, branch_ids=None, role="owner"):
    resolved_client_id = client_id or uuid4()
    resolved_branch_ids = list(branch_ids or [uuid4()])
    branches = [SimpleNamespace(id=branch_id) for branch_id in resolved_branch_ids]
    return SimpleNamespace(
        client=SimpleNamespace(id=resolved_client_id),
        role=role,
        branches=branches,
        effective_branch_id=resolved_branch_ids[0] if len(resolved_branch_ids) == 1 else None,
        allowed_branch_ids=set(resolved_branch_ids),
        branch_restricted=False,
    )


@pytest.mark.asyncio
async def test_list_specialists_rejects_invalid_branch_id(monkeypatch):
    context = _context()
    db = Mock()
    query = Mock()
    query.filter.return_value = query
    db.query.return_value = query

    monkeypatch.setattr(calendar_router, "get_console_context", lambda *args, **kwargs: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.list_specialists(
            request=Mock(),
            branch_id="invalid",
            include_inactive=False,
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_create_specialist_requires_branch_selection(monkeypatch):
    client_id = uuid4()
    branch_a = uuid4()
    branch_b = uuid4()
    context = _context(client_id=client_id, branch_ids=[branch_a, branch_b])
    db = Mock()

    monkeypatch.setattr(calendar_router, "get_console_context", lambda *args, **kwargs: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.create_specialist(
            request=Mock(),
            data=calendar_router.SpecialistCreate(name="New Specialist"),
            db=db,
        )

    assert exc_info.value.code == "BRANCH_SELECTION_REQUIRED"


@pytest.mark.asyncio
async def test_create_specialist_normalizes_name_and_optional_fields(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    context = _context(client_id=client_id, branch_ids=[branch_id])
    branch = SimpleNamespace(id=branch_id, client_id=client_id, name="Main")
    db = Mock()
    query = Mock()
    query.filter.return_value.first.return_value = branch
    db.query.return_value = query
    added: list[object] = []
    db.add.side_effect = added.append

    monkeypatch.setattr(calendar_router, "get_console_context", lambda *args, **kwargs: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(calendar_router, "ensure_onboarding_step", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        calendar_router.SchedulingService,
        "get_specialist_services",
        lambda self, specialist: specialist.services or [],
    )

    response = await calendar_router.create_specialist(
        request=Mock(),
        data=calendar_router.SpecialistCreate(
            name="  Alice  ",
            phone="   ",
            branch_id=str(branch_id),
        ),
        db=db,
    )

    assert response.name == "Alice"
    assert response.branch_id == str(branch_id)
    assert response.is_active is True
    assert len(added) == 1
    assert getattr(added[0], "phone") is None


@pytest.mark.asyncio
async def test_update_specialist_rejects_null_is_active(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    context = _context(client_id=client_id, branch_ids=[branch_id])
    specialist = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        branch=SimpleNamespace(id=branch_id, client_id=client_id),
        name="Alice",
        phone=None,
        email=None,
        google_calendar_id=None,
        services=[],
        working_hours={},
        is_active=True,
        updated_at=None,
    )

    monkeypatch.setattr(calendar_router, "get_console_context", lambda *args, **kwargs: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_specialist", lambda *args, **kwargs: specialist)
    monkeypatch.setattr(calendar_router, "ensure_onboarding_step", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.update_specialist(
            specialist_id=str(specialist.id),
            request=Mock(),
            data=calendar_router.SpecialistUpdate(is_active=None),
            db=Mock(),
        )

    assert exc_info.value.code == "INVALID_PARAM"
