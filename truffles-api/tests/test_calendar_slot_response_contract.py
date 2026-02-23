from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from app.models.service import Service
from app.services import tool_registry_service


def test_format_slot_list_keeps_focus_time_visible_when_truncated():
    rendered = tool_registry_service._format_slot_list(
        {
            "Айгерим": ["10:00", "11:00", "12:00", "13:00", "14:00", "19:00"],
        },
        focus_time="19:00",
    )

    assert "19:00" in rendered
    assert "Свободные слоты:" in rendered


def test_tool_registry_list_slots_contract_sets_availability_claim():
    db = Mock()
    specialist = SimpleNamespace(id=uuid4(), name="Айгерим")
    specialist_query = Mock()
    specialist_query.filter.return_value.order_by.return_value.all.return_value = [specialist]
    service_query = Mock()
    service_query.filter.return_value.first.return_value = None

    def _query(model):
        if model is Service:
            return service_query
        return specialist_query

    db.query.side_effect = _query

    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "none"},
        timezone="Asia/Almaty",
    )
    slot_1000 = SimpleNamespace(start=datetime(2026, 2, 20, 10, 0, tzinfo=timezone.utc), available=True)
    slot_1100 = SimpleNamespace(start=datetime(2026, 2, 20, 11, 0, tzinfo=timezone.utc), available=True)
    slot_1200 = SimpleNamespace(start=datetime(2026, 2, 20, 12, 0, tzinfo=timezone.utc), available=True)
    slot_1300 = SimpleNamespace(start=datetime(2026, 2, 20, 13, 0, tzinfo=timezone.utc), available=True)
    slot_1400 = SimpleNamespace(start=datetime(2026, 2, 20, 14, 0, tzinfo=timezone.utc), available=True)
    slot_1900 = SimpleNamespace(start=datetime(2026, 2, 20, 19, 0, tzinfo=timezone.utc), available=True)

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service,
        "_resolve_specialist_filter",
        return_value=(None, None, None),
    ), patch.object(tool_registry_service, "SchedulingService") as scheduling_cls:
        scheduling_cls.return_value.get_available_slots.return_value = [
            slot_1000,
            slot_1100,
            slot_1200,
            slot_1300,
            slot_1400,
            slot_1900,
        ]

        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.list_slots",
            tool_args={"start_at": "2026-02-20T19:00:00+05:00"},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="Стрижка",
            message_text="Можно на 19:00?",
            expected_reply_type="name",
        )

    assert result.handled is True
    assert result.ok is True
    assert result.decision_meta.get("availability_claim") == "yes"
    assert result.decision_meta.get("requested_time") == "19:00"
    available = result.decision_meta.get("available_slots_by_specialist") or {}
    assert "19:00" in available.get("Айгерим", [])
    assert "Да, на 19:00 есть свободное окно." in (result.response_text or "")
    assert "19:00" in (result.response_text or "")


def test_tool_registry_book_slot_conflict_without_requested_time_has_no_fabricated_clock():
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "none"},
        timezone="Asia/Almaty",
    )
    specialist = SimpleNamespace(id=uuid4(), name="Алия")

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service,
        "get_provider_health",
        return_value=SimpleNamespace(ready=True, reason=None),
    ), patch.object(
        tool_registry_service,
        "_resolve_specialist_for_booking",
        return_value=(specialist, "service_default", None),
    ), patch.object(
        tool_registry_service,
        "_book_slot",
        side_effect=tool_registry_service.AppointmentConflictError("conflict"),
    ), patch.object(
        tool_registry_service,
        "_list_slots",
        return_value=("Свободные слоты: Айгерим: 10:00, 11:00.", None),
    ):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.book_slot",
            tool_args={"start_at": "2026-02-20T00:00:00+05:00"},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="Маникюр",
            message_text="Меня зовут Марина.",
            expected_reply_type="name",
        )

    assert result.handled is True
    assert result.ok is False
    assert result.error_code == "slot_unavailable"
    assert "00:00" not in (result.response_text or "")
    assert result.decision_meta.get("requested_time") is None


def test_list_slots_missing_date_does_not_emit_slot_date_resolution_miss():
    contract_meta = {}
    branch = SimpleNamespace(timezone="Asia/Almaty")

    _, error = tool_registry_service._list_slots(
        Mock(),
        branch=branch,
        specialist_id=None,
        date_value=None,
        duration_min=60,
        contract_meta=contract_meta,
    )

    assert error == "missing_date"
    assert contract_meta.get("slot_contract_error") is None


def test_list_slots_daypart_token_without_date_does_not_emit_slot_date_resolution_miss():
    contract_meta = {}
    branch = SimpleNamespace(timezone="Asia/Almaty")

    _, error = tool_registry_service._list_slots(
        Mock(),
        branch=branch,
        specialist_id=None,
        date_value="днем",
        duration_min=60,
        contract_meta=contract_meta,
    )

    assert error == "invalid_date"
    assert contract_meta.get("slot_contract_error") is None


def test_list_slots_invalid_explicit_date_emits_slot_date_resolution_miss():
    contract_meta = {}
    branch = SimpleNamespace(timezone="Asia/Almaty")

    _, error = tool_registry_service._list_slots(
        Mock(),
        branch=branch,
        specialist_id=None,
        date_value="32.13.2026",
        duration_min=60,
        contract_meta=contract_meta,
    )

    assert error == "invalid_date"
    assert contract_meta.get("slot_contract_error") == "slot_date_resolution_miss"


def test_execute_list_slots_prefers_relative_date_over_time_only_start_at():
    db = Mock()
    specialist = SimpleNamespace(id=uuid4(), name="Айгерим")
    specialist_query = Mock()
    specialist_query.filter.return_value.order_by.return_value.all.return_value = [specialist]
    service_query = Mock()
    service_query.filter.return_value.first.return_value = None

    def _query(model):
        if model is Service:
            return service_query
        return specialist_query

    db.query.side_effect = _query

    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "none"},
        timezone="Asia/Almaty",
    )
    slot_1100 = SimpleNamespace(start=datetime(2026, 2, 23, 11, 0, tzinfo=timezone.utc), available=True)

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service,
        "_resolve_specialist_filter",
        return_value=(None, None, None),
    ), patch.object(tool_registry_service, "SchedulingService") as scheduling_cls:
        scheduling_cls.return_value.get_available_slots.return_value = [slot_1100]

        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.list_slots",
            tool_args={"start_at": "16:30"},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="Стрижка",
            message_text="Я хочу записаться на завтрашний день.",
            expected_reply_type="time",
            now=datetime(2026, 2, 22, 12, 0, tzinfo=timezone.utc),
        )

    assert result.handled is True
    assert result.ok is True
    assert result.decision_meta.get("requested_date") == "завтра"
    assert result.decision_meta.get("resolved_date") == "2026-02-23"


def test_execute_list_slots_time_only_start_at_keeps_requested_date_empty():
    db = Mock()
    specialist = SimpleNamespace(id=uuid4(), name="Айгерим")
    specialist_query = Mock()
    specialist_query.filter.return_value.order_by.return_value.all.return_value = [specialist]
    service_query = Mock()
    service_query.filter.return_value.first.return_value = None

    def _query(model):
        if model is Service:
            return service_query
        return specialist_query

    db.query.side_effect = _query

    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "none"},
        timezone="Asia/Almaty",
    )
    slot_1830 = SimpleNamespace(start=datetime(2026, 2, 22, 18, 30, tzinfo=timezone.utc), available=True)

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service,
        "_resolve_specialist_filter",
        return_value=(None, None, None),
    ), patch.object(tool_registry_service, "SchedulingService") as scheduling_cls:
        scheduling_cls.return_value.get_available_slots.return_value = [slot_1830]

        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.list_slots",
            tool_args={"start_at": "18:30"},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="Маникюр",
            message_text="Можно на 18:30?",
            expected_reply_type="time",
            now=datetime(2026, 2, 22, 12, 0, tzinfo=timezone.utc),
        )

    assert result.handled is True
    assert result.ok is True
    assert result.decision_meta.get("requested_date") is None
    assert result.decision_meta.get("requested_time") == "18:30"
