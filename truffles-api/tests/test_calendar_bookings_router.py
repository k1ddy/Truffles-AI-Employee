from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.routers import calendar as calendar_router
from app.services.console_errors import ConsoleAPIError


class _QueryStub:
    def __init__(self, *, rows=None, scalar_value=None):
        self._rows = rows or []
        self._scalar = scalar_value

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def all(self):
        return list(self._rows)

    def first(self):
        if not self._rows:
            return None
        return self._rows[0]

    def scalar(self):
        return self._scalar


@pytest.mark.asyncio
async def test_list_bookings_includes_case_linkage_and_conversation_filter(monkeypatch):
    client_id = uuid4()
    specialist_id = uuid4()
    conversation_id = uuid4()
    booking_id = uuid4()
    case_id = uuid4()

    booking = SimpleNamespace(
        id=booking_id,
        specialist_id=specialist_id,
        start_at=datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 3, 5, 11, 0, tzinfo=timezone.utc),
        customer_name="Test User",
        customer_phone="+77000000000",
        status="CONFIRMED",
        created_at=datetime(2026, 3, 5, 9, 0, tzinfo=timezone.utc),
        conversation_id=conversation_id,
    )

    captured = {}

    class _SchedulingServiceStub:
        def __init__(self, _db):
            pass

        def get_appointments(self, **kwargs):
            captured.update(kwargs)
            return [booking]

    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        branch_restricted=False,
        allowed_branch_ids=set(),
    )

    def _query_side_effect(model):
        if model is calendar_router.Specialist:
            return _QueryStub(rows=[SimpleNamespace(id=specialist_id, name="Spec")])
        if model is calendar_router.AppointmentServiceModel:
            return _QueryStub(rows=[])
        if model is calendar_router.AppointmentSyncState:
            return _QueryStub(rows=[])
        if model is calendar_router.AppointmentAudit:
            return _QueryStub(rows=[])
        if model is calendar_router.Handover:
            return _QueryStub(rows=[SimpleNamespace(id=case_id, conversation_id=conversation_id)])
        return _QueryStub(rows=[])

    db = SimpleNamespace(query=_query_side_effect)

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "SchedulingService", _SchedulingServiceStub)

    response = await calendar_router.list_bookings(
        request=SimpleNamespace(),
        specialist_id=str(specialist_id),
        conversation_id=str(conversation_id),
        db=db,
    )

    assert captured["conversation_id"] == conversation_id
    assert response.items[0].conversation_id == str(conversation_id)
    assert response.items[0].case_id == str(case_id)


@pytest.mark.asyncio
async def test_list_bookings_rejects_invalid_conversation_filter(monkeypatch):
    context = SimpleNamespace(
        client=SimpleNamespace(id=uuid4()),
        branch_restricted=False,
        allowed_branch_ids=set(),
    )
    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)

    class _SchedulingServiceGuard:
        def __init__(self, _db):
            pass

        def get_appointments(self, **_kwargs):  # pragma: no cover
            raise AssertionError("service must not be called for invalid filters")

    monkeypatch.setattr(calendar_router, "SchedulingService", _SchedulingServiceGuard)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.list_bookings(
            request=SimpleNamespace(),
            conversation_id="not-a-uuid",
            db=SimpleNamespace(query=lambda *_args, **_kwargs: _QueryStub(rows=[])),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_PARAM"
