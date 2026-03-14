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


@pytest.mark.parametrize(
    ("role", "status", "no_show_followup_done", "case_id", "expected_allowed", "expected_blocked"),
    [
        (
            "manager",
            "CONFIRMED",
            False,
            "case-1",
            [
                "edit_booking",
                "cancel_booking",
                "mark_completed",
                "mark_no_show",
                "open_case_from_booking",
            ],
            [
                ("record_follow_up_contacted", "open_no_show_required"),
                ("record_follow_up_rebooked", "open_no_show_required"),
                ("manage_follow_up_governance", "permission_required"),
            ],
        ),
        (
            "owner",
            "NO_SHOW",
            False,
            "case-1",
            [
                "record_follow_up_contacted",
                "record_follow_up_rebooked",
                "manage_follow_up_governance",
                "open_case_from_booking",
            ],
            [
                ("edit_booking", "active_status_only"),
                ("cancel_booking", "active_status_only"),
                ("mark_completed", "active_status_only"),
                ("mark_no_show", "active_status_only"),
            ],
        ),
        (
            "owner",
            "NO_SHOW",
            True,
            "case-1",
            ["open_case_from_booking"],
            [
                ("edit_booking", "active_status_only"),
                ("cancel_booking", "active_status_only"),
                ("mark_completed", "active_status_only"),
                ("mark_no_show", "active_status_only"),
                ("record_follow_up_contacted", "follow_up_already_closed"),
                ("record_follow_up_rebooked", "follow_up_already_closed"),
                ("manage_follow_up_governance", "follow_up_already_closed"),
            ],
        ),
        (
            "manager",
            "COMPLETED",
            False,
            "case-1",
            ["open_case_from_booking"],
            [
                ("edit_booking", "active_status_only"),
                ("cancel_booking", "active_status_only"),
                ("mark_completed", "active_status_only"),
                ("mark_no_show", "active_status_only"),
                ("record_follow_up_contacted", "open_no_show_required"),
                ("record_follow_up_rebooked", "open_no_show_required"),
                ("manage_follow_up_governance", "permission_required"),
            ],
        ),
        (
            "manager",
            "CONFIRMED",
            False,
            None,
            [
                "edit_booking",
                "cancel_booking",
                "mark_completed",
                "mark_no_show",
            ],
            [
                ("record_follow_up_contacted", "open_no_show_required"),
                ("record_follow_up_rebooked", "open_no_show_required"),
                ("manage_follow_up_governance", "permission_required"),
                ("open_case_from_booking", "case_link_required"),
            ],
        ),
        (
            "consultant_bot",
            "CONFIRMED",
            False,
            "case-1",
            [],
            [
                ("edit_booking", "permission_required"),
                ("cancel_booking", "permission_required"),
                ("mark_completed", "permission_required"),
                ("mark_no_show", "permission_required"),
                ("record_follow_up_contacted", "permission_required"),
                ("record_follow_up_rebooked", "permission_required"),
                ("manage_follow_up_governance", "permission_required"),
                ("open_case_from_booking", "permission_required"),
            ],
        ),
    ],
)
def test_build_booking_action_fields_matches_role_status_matrix(
    role,
    status,
    no_show_followup_done,
    case_id,
    expected_allowed,
    expected_blocked,
):
    allowed_actions, blocked_actions = calendar_router._build_booking_action_fields(
        context=SimpleNamespace(role=role),
        booking=SimpleNamespace(status=status),
        no_show_followup_done=no_show_followup_done,
        case_id=case_id,
    )

    assert allowed_actions == expected_allowed
    assert [(payload.action_id, payload.reason_code) for payload in blocked_actions] == expected_blocked


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
        case_id=None,
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
        role="manager",
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
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: None)
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
    assert response.has_more is False
    assert response.cursor is None


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


@pytest.mark.asyncio
async def test_list_bookings_accepts_cursor_lane_and_case_filters(monkeypatch):
    client_id = uuid4()
    specialist_id = uuid4()
    case_id = uuid4()
    booking_id = uuid4()
    cursor_id = uuid4()
    start_at = datetime(2026, 3, 6, 10, 0, tzinfo=timezone.utc)

    booking = SimpleNamespace(
        id=booking_id,
        specialist_id=specialist_id,
        start_at=start_at,
        end_at=datetime(2026, 3, 6, 11, 0, tzinfo=timezone.utc),
        customer_name="Queue User",
        customer_phone="+77001230000",
        status="NO_SHOW",
        created_at=datetime(2026, 3, 6, 9, 0, tzinfo=timezone.utc),
        conversation_id=None,
        case_id=case_id,
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
        role="manager",
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
        return _QueryStub(rows=[])

    db = SimpleNamespace(query=_query_side_effect)
    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "SchedulingService", _SchedulingServiceStub)

    response = await calendar_router.list_bookings(
        request=SimpleNamespace(),
        specialist_id=str(specialist_id),
        case_id=str(case_id),
        lane="attention",
        needs_action=True,
        status="scheduled",
        cursor=f"{start_at.isoformat()}|{cursor_id}",
        db=db,
    )

    assert captured["specialist_id"] == specialist_id
    assert captured["case_id"] == case_id
    assert captured["lane"] == "attention"
    assert captured["needs_action"] is True
    assert captured["status"] is None
    assert "CONFIRMED" in (captured["status_filters"] or [])
    assert captured["cursor_start_at"] == start_at
    assert captured["cursor_id"] == cursor_id
    assert response.items[0].case_id == str(case_id)


@pytest.mark.asyncio
async def test_create_booking_normalizes_operator_grade_fields(monkeypatch):
    client_id = uuid4()
    agent_id = uuid4()
    specialist_id = uuid4()
    branch_id = uuid4()
    booking_id = uuid4()
    captured = {}

    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=agent_id, name="Manager"),
    )
    specialist = SimpleNamespace(
        id=specialist_id,
        client_id=client_id,
        branch_id=branch_id,
        branch=None,
        name="Spec",
    )

    class _SchedulingServiceStub:
        def __init__(self, _db):
            pass

        def create_appointment(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(id=booking_id)

    db = SimpleNamespace(
        query=lambda model: _QueryStub(rows=[specialist]) if model is calendar_router.Specialist else _QueryStub(rows=[]),
    )

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "SchedulingService", _SchedulingServiceStub)
    monkeypatch.setattr(calendar_router, "schedule_default_reminders", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        calendar_router,
        "_build_booking_response_for_context",
        lambda **_kwargs: calendar_router.BookingResponse(
            id=str(booking_id),
            specialist_id=str(specialist_id),
            specialist_name="Spec",
            start_at="2026-03-06T10:00:00+00:00",
            end_at="2026-03-06T11:00:00+00:00",
            customer_name=captured["customer_name"],
            customer_phone=captured["customer_phone"],
            service_type=captured["service_type"],
            status="CONFIRMED",
            created_at="2026-03-06T09:00:00+00:00",
        ),
    )

    response = await calendar_router.create_booking(
        request=SimpleNamespace(),
        data=calendar_router.BookingCreate(
            specialist_id=str(specialist_id),
            start_at=datetime(2026, 3, 6, 10, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 3, 6, 11, 0, tzinfo=timezone.utc),
            customer_name="  Айгуль  ",
            customer_phone="8 (700) 123-45-67",
            service_type="  Маникюр  ",
            notes="  Позвонить за час  ",
        ),
        db=db,
    )

    assert response.success is True
    assert captured["customer_name"] == "Айгуль"
    assert captured["customer_phone"] == "+77001234567"
    assert captured["service_type"] == "Маникюр"
    assert captured["notes"] == "Позвонить за час"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("customer_name", " "),
        ("service_type", "\t"),
    ],
)
async def test_create_booking_rejects_blank_operator_fields(monkeypatch, field_name, field_value):
    client_id = uuid4()
    specialist_id = uuid4()
    branch_id = uuid4()
    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )
    specialist = SimpleNamespace(
        id=specialist_id,
        client_id=client_id,
        branch_id=branch_id,
        branch=None,
        name="Spec",
    )

    class _SchedulingServiceGuard:
        def __init__(self, _db):
            pass

        def create_appointment(self, **_kwargs):  # pragma: no cover
            raise AssertionError("create_appointment must not run for invalid operator fields")

    db = SimpleNamespace(
        query=lambda model: _QueryStub(rows=[specialist]) if model is calendar_router.Specialist else _QueryStub(rows=[]),
    )

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "SchedulingService", _SchedulingServiceGuard)

    payload = {
        "specialist_id": str(specialist_id),
        "start_at": datetime(2026, 3, 6, 10, 0, tzinfo=timezone.utc),
        "end_at": datetime(2026, 3, 6, 11, 0, tzinfo=timezone.utc),
        "customer_name": "Айгуль",
        "customer_phone": "+77001234567",
        "service_type": "Маникюр",
    }
    payload[field_name] = field_value

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.create_booking(
            request=SimpleNamespace(),
            data=calendar_router.BookingCreate(**payload),
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_create_booking_rejects_invalid_customer_phone(monkeypatch):
    client_id = uuid4()
    specialist_id = uuid4()
    branch_id = uuid4()
    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )
    specialist = SimpleNamespace(
        id=specialist_id,
        client_id=client_id,
        branch_id=branch_id,
        branch=None,
        name="Spec",
    )

    class _SchedulingServiceGuard:
        def __init__(self, _db):
            pass

        def create_appointment(self, **_kwargs):  # pragma: no cover
            raise AssertionError("create_appointment must not run for invalid phone")

    db = SimpleNamespace(
        query=lambda model: _QueryStub(rows=[specialist]) if model is calendar_router.Specialist else _QueryStub(rows=[]),
    )

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "SchedulingService", _SchedulingServiceGuard)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.create_booking(
            request=SimpleNamespace(),
            data=calendar_router.BookingCreate(
                specialist_id=str(specialist_id),
                start_at=datetime(2026, 3, 6, 10, 0, tzinfo=timezone.utc),
                end_at=datetime(2026, 3, 6, 11, 0, tzinfo=timezone.utc),
                customer_name="Айгуль",
                customer_phone="abc-123",
                service_type="Маникюр",
            ),
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "customer_phone",
    [
        "8 (700) 123-45-6",
        "+7 700 123 45 6",
        "7 700 123 45 6",
    ],
)
async def test_create_booking_rejects_partial_prefixed_customer_phone(monkeypatch, customer_phone):
    client_id = uuid4()
    specialist_id = uuid4()
    branch_id = uuid4()
    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )
    specialist = SimpleNamespace(
        id=specialist_id,
        client_id=client_id,
        branch_id=branch_id,
        branch=None,
        name="Spec",
    )

    class _SchedulingServiceGuard:
        def __init__(self, _db):
            pass

        def create_appointment(self, **_kwargs):  # pragma: no cover
            raise AssertionError("create_appointment must not run for partial prefixed phone")

    db = SimpleNamespace(
        query=lambda model: _QueryStub(rows=[specialist]) if model is calendar_router.Specialist else _QueryStub(rows=[]),
    )

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "SchedulingService", _SchedulingServiceGuard)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.create_booking(
            request=SimpleNamespace(),
            data=calendar_router.BookingCreate(
                specialist_id=str(specialist_id),
                start_at=datetime(2026, 3, 6, 10, 0, tzinfo=timezone.utc),
                end_at=datetime(2026, 3, 6, 11, 0, tzinfo=timezone.utc),
                customer_name="Айгуль",
                customer_phone=customer_phone,
                service_type="Маникюр",
            ),
            db=db,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_update_booking_normalizes_operator_grade_fields(monkeypatch):
    client_id = uuid4()
    agent_id = uuid4()
    specialist_id = uuid4()
    branch_id = uuid4()
    booking_id = uuid4()
    captured = {}

    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=agent_id, name="Manager"),
    )
    specialist = SimpleNamespace(
        id=specialist_id,
        client_id=client_id,
        branch_id=branch_id,
        branch=None,
        name="Spec",
    )

    class _DbStub:
        def __init__(self):
            self.committed = False
            self.refreshed = []

        def query(self, model):
            if model is calendar_router.Specialist:
                return _QueryStub(rows=[specialist])
            return _QueryStub(rows=[])

        def commit(self):
            self.committed = True

        def refresh(self, booking):
            self.refreshed.append(booking)

    class _SchedulingServiceStub:
        def __init__(self, _db):
            pass

        def update_appointment(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(id=booking_id, branch=None, notes=kwargs["notes"], status="PENDING_CONFIRMATION")

    db = _DbStub()

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "SchedulingService", _SchedulingServiceStub)
    monkeypatch.setattr(calendar_router, "enqueue_appointment_sync", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        calendar_router,
        "_build_booking_response_for_context",
        lambda **_kwargs: calendar_router.BookingResponse(
            id=str(booking_id),
            specialist_id=str(specialist_id),
            specialist_name="Spec",
            start_at="2026-03-06T14:00:00+00:00",
            end_at="2026-03-06T15:00:00+00:00",
            customer_name=captured["customer_name"],
            customer_phone=captured["customer_phone"],
            service_type=captured["service_type"],
            notes=captured["notes"],
            status="PENDING_CONFIRMATION",
            created_at="2026-03-06T09:00:00+00:00",
        ),
    )

    response = await calendar_router.update_booking(
        request=SimpleNamespace(),
        booking_id=str(booking_id),
        data=calendar_router.BookingUpdate(
            specialist_id=str(specialist_id),
            start_at=datetime(2026, 3, 6, 14, 0, tzinfo=timezone.utc),
            end_at=datetime(2026, 3, 6, 15, 0, tzinfo=timezone.utc),
            customer_name="  Айгуль  ",
            customer_phone="8 (701) 555-44-33",
            service_type="  Маникюр  ",
            notes="  Перенесли по просьбе клиента  ",
            version=4,
        ),
        db=db,
    )

    assert response.success is True
    assert captured["appointment_id"] == booking_id
    assert captured["client_id"] == client_id
    assert captured["specialist_id"] == specialist_id
    assert captured["customer_name"] == "Айгуль"
    assert captured["customer_phone"] == "+77015554433"
    assert captured["service_type"] == "Маникюр"
    assert captured["notes"] == "Перенесли по просьбе клиента"
    assert captured["actor_id"] == agent_id
    assert captured["actor_type"] == "agent"
    assert captured["channel"] == "console"
    assert captured["expected_version"] == 4
    assert captured["commit"] is False
    assert response.booking.notes == "Перенесли по просьбе клиента"
    assert db.committed is True
    assert len(db.refreshed) == 1


@pytest.mark.asyncio
async def test_update_booking_maps_lifecycle_denied_error(monkeypatch):
    client_id = uuid4()
    specialist_id = uuid4()
    branch_id = uuid4()
    booking_id = uuid4()

    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )
    specialist = SimpleNamespace(
        id=specialist_id,
        client_id=client_id,
        branch_id=branch_id,
        branch=None,
        name="Spec",
    )

    class _DbStub:
        def query(self, model):
            if model is calendar_router.Specialist:
                return _QueryStub(rows=[specialist])
            return _QueryStub(rows=[])

    class _SchedulingServiceStub:
        def __init__(self, _db):
            pass

        def update_appointment(self, **_kwargs):
            raise calendar_router.AppointmentLifecycleActionDeniedError("update", "COMPLETED")

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "SchedulingService", _SchedulingServiceStub)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.update_booking(
            request=SimpleNamespace(),
            booking_id=str(booking_id),
            data=calendar_router.BookingUpdate(
                specialist_id=str(specialist_id),
                start_at=datetime(2026, 3, 6, 14, 0, tzinfo=timezone.utc),
                end_at=datetime(2026, 3, 6, 15, 0, tzinfo=timezone.utc),
                customer_name="Айгуль",
                customer_phone="+77015554433",
                service_type="Маникюр",
                version=1,
            ),
            db=_DbStub(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "BOOKING_UPDATE_DENIED"


@pytest.mark.asyncio
async def test_update_booking_maps_version_conflict_error(monkeypatch):
    client_id = uuid4()
    specialist_id = uuid4()
    branch_id = uuid4()
    booking_id = uuid4()

    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )
    specialist = SimpleNamespace(
        id=specialist_id,
        client_id=client_id,
        branch_id=branch_id,
        branch=None,
        name="Spec",
    )

    class _DbStub:
        def query(self, model):
            if model is calendar_router.Specialist:
                return _QueryStub(rows=[specialist])
            return _QueryStub(rows=[])

    class _SchedulingServiceStub:
        def __init__(self, _db):
            pass

        def update_appointment(self, **_kwargs):
            raise calendar_router.AppointmentVersionConflictError(3, 4)

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "SchedulingService", _SchedulingServiceStub)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.update_booking(
            request=SimpleNamespace(),
            booking_id=str(booking_id),
            data=calendar_router.BookingUpdate(
                specialist_id=str(specialist_id),
                start_at=datetime(2026, 3, 6, 14, 0, tzinfo=timezone.utc),
                end_at=datetime(2026, 3, 6, 15, 0, tzinfo=timezone.utc),
                customer_name="Айгуль",
                customer_phone="+77015554433",
                service_type="Маникюр",
                version=3,
            ),
            db=_DbStub(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "BOOKING_VERSION_CONFLICT"


@pytest.mark.asyncio
async def test_cancel_booking_passes_reason_and_actor_context(monkeypatch):
    client_id = uuid4()
    agent_id = uuid4()
    booking_id = uuid4()
    captured = {}

    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=agent_id, name="Manager"),
    )

    class _DbStub:
        def __init__(self):
            self.committed = False
            self.refreshed = []

        def query(self, _model):
            return _QueryStub(rows=[])

        def commit(self):
            self.committed = True

        def refresh(self, booking):
            self.refreshed.append(booking)

    class _SchedulingServiceStub:
        def __init__(self, _db):
            pass

        def cancel_appointment(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(id=booking_id, branch=None, notes="Cancel: Клиент отменил визит", status="CANCELLED")

    db = _DbStub()

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "SchedulingService", _SchedulingServiceStub)
    monkeypatch.setattr(
        calendar_router,
        "_build_booking_response_for_context",
        lambda **_kwargs: calendar_router.BookingResponse(
            id=str(booking_id),
            specialist_id=str(uuid4()),
            specialist_name="Spec",
            start_at="2026-03-06T10:00:00+00:00",
            end_at="2026-03-06T11:00:00+00:00",
            customer_name="Айгуль",
            customer_phone="+77015554433",
            service_type="Маникюр",
            notes="Cancel: Клиент отменил визит",
            status="CANCELLED",
            created_at="2026-03-06T09:00:00+00:00",
        ),
    )

    response = await calendar_router.cancel_booking(
        request=SimpleNamespace(),
        booking_id=str(booking_id),
        data=calendar_router.BookingCancelRequest(reason="  Клиент отменил визит  ", version=3),
        db=db,
    )

    assert response.success is True
    assert captured["appointment_id"] == booking_id
    assert captured["client_id"] == client_id
    assert captured["reason"] == "Клиент отменил визит"
    assert captured["actor_id"] == agent_id
    assert captured["actor_type"] == "agent"
    assert captured["channel"] == "console"
    assert captured["expected_version"] == 3
    assert captured["commit"] is False
    assert db.committed is True
    assert len(db.refreshed) == 1


@pytest.mark.asyncio
async def test_cancel_booking_maps_version_conflict_error(monkeypatch):
    client_id = uuid4()
    booking_id = uuid4()

    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )

    class _DbStub:
        def query(self, _model):
            return _QueryStub(rows=[])

    class _SchedulingServiceStub:
        def __init__(self, _db):
            pass

        def cancel_appointment(self, **_kwargs):
            raise calendar_router.AppointmentVersionConflictError(2, 3)

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "SchedulingService", _SchedulingServiceStub)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.cancel_booking(
            request=SimpleNamespace(),
            booking_id=str(booking_id),
            data=calendar_router.BookingCancelRequest(version=2),
            db=_DbStub(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "BOOKING_VERSION_CONFLICT"


@pytest.mark.asyncio
async def test_cancel_booking_maps_lifecycle_denied_error(monkeypatch):
    client_id = uuid4()
    booking_id = uuid4()

    context = SimpleNamespace(
        client=SimpleNamespace(id=client_id),
        agent=SimpleNamespace(id=uuid4(), name="Manager"),
    )

    class _DbStub:
        def query(self, _model):
            return _QueryStub(rows=[])

    class _SchedulingServiceStub:
        def __init__(self, _db):
            pass

        def cancel_appointment(self, **_kwargs):
            raise calendar_router.AppointmentLifecycleActionDeniedError("cancel", "NO_SHOW")

    monkeypatch.setattr(calendar_router, "get_console_context", lambda _request, _db: context)
    monkeypatch.setattr(calendar_router, "require_console_permission", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "_resolve_booking_for_context", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(calendar_router, "SchedulingService", _SchedulingServiceStub)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await calendar_router.cancel_booking(
            request=SimpleNamespace(),
            booking_id=str(booking_id),
            data=calendar_router.BookingCancelRequest(version=1),
            db=_DbStub(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "BOOKING_CANCEL_DENIED"
