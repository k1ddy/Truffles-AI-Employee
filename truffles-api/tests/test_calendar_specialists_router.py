from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import calendar as calendar_router
from app.services.appointment_service import SchedulingService
from app.services.console_errors import ConsoleAPIError


def _context(*, client_id=None, branch_ids=None, role="owner", branch_restricted=False):
    resolved_client_id = client_id or uuid4()
    resolved_branch_ids = list(branch_ids or [uuid4()])
    branches = [SimpleNamespace(id=branch_id) for branch_id in resolved_branch_ids]
    return SimpleNamespace(
        client=SimpleNamespace(id=resolved_client_id),
        role=role,
        branches=branches,
        effective_branch_id=resolved_branch_ids[0] if len(resolved_branch_ids) == 1 else None,
        allowed_branch_ids=set(resolved_branch_ids),
        branch_restricted=branch_restricted,
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
async def test_get_slots_uses_fastapi_converted_uuid_without_rewrapping(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    specialist_id = uuid4()
    context = _context(client_id=client_id, branch_ids=[branch_id])
    specialist = SimpleNamespace(
        id=specialist_id,
        client_id=client_id,
        branch_id=branch_id,
        branch=SimpleNamespace(timezone="Asia/Almaty"),
        name="Alice",
    )
    query = Mock()
    query.filter.return_value.first.return_value = specialist
    db = Mock()
    db.query.return_value = query
    captured = {}

    class SchedulingServiceStub:
        def __init__(self, db):
            self.db = db

        def get_available_slots(self, *, specialist_id, date, duration_minutes, client_id):
            captured["specialist_id"] = specialist_id
            captured["date"] = date
            captured["duration_minutes"] = duration_minutes
            captured["client_id"] = client_id
            return [
                SimpleNamespace(
                    start=datetime(2026, 5, 1, 10, 0, tzinfo=timezone.utc),
                    end=datetime(2026, 5, 1, 11, 0, tzinfo=timezone.utc),
                    available=True,
                )
            ]

    monkeypatch.setattr(calendar_router, "get_console_context", lambda *args, **kwargs: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(calendar_router, "SchedulingService", SchedulingServiceStub)

    response = await calendar_router.get_slots(
        request=Mock(),
        specialist_id=specialist_id,
        date="2026-05-01",
        duration=60,
        db=db,
    )

    assert captured["specialist_id"] == specialist_id
    assert captured["client_id"] == client_id
    assert response.specialist_id == str(specialist_id)
    assert response.slots[0].start_time == "10:00"


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


def test_resolve_booking_for_context_rejects_cross_branch():
    client_id = uuid4()
    allowed_branch = uuid4()
    foreign_branch = uuid4()
    context = _context(client_id=client_id, branch_ids=[allowed_branch], branch_restricted=True)
    booking_id = uuid4()
    booking = SimpleNamespace(id=booking_id, client_id=client_id, branch_id=foreign_branch)

    db = Mock()
    query = Mock()
    query.filter.return_value.first.return_value = booking
    db.query.return_value = query

    with pytest.raises(ConsoleAPIError) as exc_info:
        calendar_router._resolve_booking_for_context(
            context=context,
            db=db,
            booking_id=booking_id,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


def test_resolve_booking_for_context_returns_booking():
    client_id = uuid4()
    branch_id = uuid4()
    context = _context(client_id=client_id, branch_ids=[branch_id], branch_restricted=True)
    booking_id = uuid4()
    booking = SimpleNamespace(id=booking_id, client_id=client_id, branch_id=branch_id)

    db = Mock()
    query = Mock()
    query.filter.return_value.first.return_value = booking
    db.query.return_value = query

    resolved = calendar_router._resolve_booking_for_context(
        context=context,
        db=db,
        booking_id=booking_id,
    )

    assert resolved == booking


class _SpecialistServicesQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filter_args = ()

    def join(self, *args, **kwargs):
        return self

    def filter(self, *args):
        self.filter_args = args
        return self

    def all(self):
        return self.rows


class _SpecialistServicesDB:
    def __init__(self, rows):
        self.query_obj = _SpecialistServicesQuery(rows)

    def query(self, *args):
        return self.query_obj


def test_get_specialist_services_filters_to_specialist_client_and_branch():
    client_id = uuid4()
    branch_id = uuid4()
    link = SimpleNamespace(duration_min=45, price=5000)
    service = SimpleNamespace(name="Стрижка", duration_min=60, price=6000)
    db = _SpecialistServicesDB([(link, service)])
    specialist = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        services=[{"name": "JSON fallback"}],
    )

    resolved = SchedulingService(db).get_specialist_services(specialist)

    filter_sql = "\n".join(str(arg) for arg in db.query_obj.filter_args)
    assert "specialist_services.specialist_id" in filter_sql
    assert "specialist_services.is_active" in filter_sql
    assert "services.client_id" in filter_sql
    assert "services.branch_id" in filter_sql
    assert "services.is_active" in filter_sql
    assert resolved == [{"name": "Стрижка", "duration_min": 45, "price": 5000}]


def test_get_specialist_services_falls_back_when_no_branch_owned_links():
    db = _SpecialistServicesDB([])
    specialist = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=uuid4(),
        services=[{"name": "Маникюр", "duration_min": 60, "price": 5000}],
    )

    resolved = SchedulingService(db).get_specialist_services(specialist)

    assert resolved == [{"name": "Маникюр", "duration_min": 60, "price": 5000}]
