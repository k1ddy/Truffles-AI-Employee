from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.models.appointment import Appointment
from app.models.branch import Branch
from app.models.service import Service
from app.schemas.capabilities import CapabilitiesPayload
from app.services import demo_salon_knowledge, tool_registry_service
from app.services.capabilities_runtime import RuntimeCapabilities, set_runtime_capabilities

pytest.importorskip("dateparser")
from app.routers.webhook import _legacy as legacy
from app.routers.webhook import booking as booking_router


def _make_query(result):
    query = Mock()
    query.filter.return_value.first.return_value = result
    return query


def test_create_booking_appointment_collect_preferences(monkeypatch):
    monkeypatch.setenv("TZ", "Asia/Almaty")
    now = datetime(2026, 1, 30, 9, 0, tzinfo=timezone.utc)
    branch_id = uuid4()
    client_id = uuid4()
    conversation = SimpleNamespace(id=uuid4(), client_id=client_id, branch_id=branch_id)
    user = SimpleNamespace(
        id=uuid4(),
        phone="+77001234567",
        remote_jid="77001234567@s.whatsapp.net",
        name="Алия",
    )
    booking_state = {
        "service": "маникюр",
        "datetime": "2026-02-02 10:00",
        "name": "Алия",
    }
    branch = SimpleNamespace(
        id=branch_id,
        timezone="Asia/Almaty",
        booking_settings={
            "booking_mode": "collect_preferences",
            "availability_provider": "none",
            "default_duration_min": 45,
        },
    )
    service = SimpleNamespace(duration_min=30)

    db = Mock()
    appointment_query = _make_query(None)
    branch_query = _make_query(branch)
    service_query = _make_query(service)

    def _query(model):
        if model is Branch:
            return branch_query
        if model is Appointment:
            return appointment_query
        if model is Service:
            return service_query
        return Mock()

    db.query.side_effect = _query

    appointment = SimpleNamespace(
        id=uuid4(),
        status="PENDING_CONFIRMATION",
        client_id=client_id,
        branch_id=branch_id,
        start_at=now + timedelta(days=1),
        end_at=now + timedelta(days=1, hours=1),
    )
    with patch("app.routers.webhook.booking.SchedulingService") as scheduling_cls:
        scheduling_cls.return_value.create_appointment.return_value = appointment

        created, meta = booking_router._create_booking_appointment(
            db=db,
            conversation=conversation,
            user=user,
            booking_state=booking_state,
            now=now,
            saved_message=None,
        )

    assert created == appointment
    assert meta["appointment_id"] == str(appointment.id)
    assert meta["booking_mode"] == "collect_preferences"
    assert meta["effective_booking_mode"] == "collect_preferences"

    _, kwargs = scheduling_cls.return_value.create_appointment.call_args
    assert kwargs["status"] == "PENDING_CONFIRMATION"
    assert kwargs["source"] == "bot"
    assert kwargs["service_type"] == "маникюр"
    assert kwargs["specialist_id"] is None
    assert kwargs["commit"] is False


def test_parse_booking_datetime_handles_dateparser_timezone_conflict():
    now = datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc)

    with patch(
        "app.routers.webhook.booking.dateparser.parse",
        side_effect=Exception("Multiple conflicting time zone configurations found"),
    ):
        parsed = booking_router._parse_booking_datetime(
            "на выходных",
            tz_name="Asia/Almaty",
            now=now,
        )

    assert parsed is None


def test_create_booking_appointment_reuses_existing():
    now = datetime(2026, 1, 30, 9, 0, tzinfo=timezone.utc)
    branch_id = uuid4()
    client_id = uuid4()
    conversation = SimpleNamespace(id=uuid4(), client_id=client_id, branch_id=branch_id)
    user = SimpleNamespace(
        id=uuid4(),
        phone="+77001234567",
        remote_jid="77001234567@s.whatsapp.net",
        name="Алия",
    )
    booking_state = {
        "service": "маникюр",
        "datetime": "2026-02-02 10:00",
        "name": "Алия",
    }
    branch = SimpleNamespace(
        id=branch_id,
        timezone="Asia/Almaty",
        booking_settings={"booking_mode": "collect_preferences", "availability_provider": "none"},
    )
    existing = SimpleNamespace(id=uuid4(), status="CONFIRMED")

    db = Mock()
    appointment_query = _make_query(existing)
    branch_query = _make_query(branch)
    service_query = _make_query(None)

    def _query(model):
        if model is Branch:
            return branch_query
        if model is Appointment:
            return appointment_query
        if model is Service:
            return service_query
        return Mock()

    db.query.side_effect = _query

    with patch("app.routers.webhook.booking.SchedulingService") as scheduling_cls:
        created, meta = booking_router._create_booking_appointment(
            db=db,
            conversation=conversation,
            user=user,
            booking_state=booking_state,
            now=now,
            saved_message=None,
        )

    assert created == existing
    assert meta["appointment_id"] == str(existing.id)
    assert meta["appointment_reused"] is True
    assert meta["appointment_status"] == "CONFIRMED"
    scheduling_cls.assert_not_called()


def test_create_booking_appointment_missing_branch_skips():
    conversation = SimpleNamespace(id=uuid4(), client_id=uuid4(), branch_id=None)
    db = Mock()

    with patch("app.routers.webhook.booking.SchedulingService") as scheduling_cls:
        created, meta = booking_router._create_booking_appointment(
            db=db,
            conversation=conversation,
            user=None,
            booking_state={},
            now=datetime.now(timezone.utc),
            saved_message=None,
        )

    assert created is None
    assert meta["appointment_skip_reason"] == "missing_branch"
    scheduling_cls.assert_not_called()


def test_select_last_non_booking_message_ignores_booking_intake():
    messages = ["Здравствуйте! Я хочу записаться на стрижку."]

    selected = booking_router._select_last_non_booking_message(
        messages,
        client_slug="demo_salon",
    )

    assert selected is None


def test_select_booking_interrupt_text_prefers_current_info_message():
    selected = booking_router._select_booking_interrupt_text(
        message_text="Где находится ваш салон?",
        batch_non_booking_message="Сколько стоит маникюр?",
        client_slug="demo_salon",
    )

    assert selected == "Где находится ваш салон?"


def test_select_booking_interrupt_text_falls_back_for_booking_intake():
    selected = booking_router._select_booking_interrupt_text(
        message_text="Я хочу записаться на стрижку.",
        batch_non_booking_message="Сколько стоит маникюр?",
        client_slug="demo_salon",
    )

    assert selected == "Сколько стоит маникюр?"


def test_select_booking_interrupt_text_uses_batch_when_message_missing():
    selected = booking_router._select_booking_interrupt_text(
        message_text=None,
        batch_non_booking_message="Сколько стоит маникюр?",
        client_slug="demo_salon",
    )

    assert selected == "Сколько стоит маникюр?"


def test_resolve_booking_info_intents_prefers_info_class_over_intent_decomp():
    resolved = booking_router._resolve_booking_info_intents(
        intent_decomp_used=True,
        intent_decomp_set={"pricing", "duration"},
        info_class_intents={"location", "pricing"},
        expected_reply_type=legacy.EXPECTED_REPLY_TIME,
        booking_time_service_candidate=False,
        expected_reply_shortcircuit=False,
        booking_interrupt_text=None,
        client_slug="demo_salon",
    )

    assert resolved == ["location", "pricing"]


def test_resolve_booking_info_intents_uses_anchor_fallback_when_empty():
    resolved = booking_router._resolve_booking_info_intents(
        intent_decomp_used=False,
        intent_decomp_set=set(),
        info_class_intents=set(),
        expected_reply_type=legacy.EXPECTED_REPLY_TIME,
        booking_time_service_candidate=False,
        expected_reply_shortcircuit=False,
        booking_interrupt_text="Можно ли оставить машину у вас на парковке?",
        client_slug="demo_salon",
    )

    assert "parking" in resolved


def test_resolve_booking_info_intents_uses_duration_signal_when_empty():
    resolved = booking_router._resolve_booking_info_intents(
        intent_decomp_used=False,
        intent_decomp_set=set(),
        info_class_intents=set(),
        expected_reply_type=legacy.EXPECTED_REPLY_TIME,
        booking_time_service_candidate=False,
        expected_reply_shortcircuit=False,
        booking_interrupt_text="Какое время займет маникюр?",
        client_slug="demo_salon",
    )

    assert "duration" in resolved


def test_resolve_booking_info_intents_uses_duration_signal_with_expected_reply_shortcircuit():
    resolved = booking_router._resolve_booking_info_intents(
        intent_decomp_used=True,
        intent_decomp_set={"other"},
        info_class_intents=set(),
        expected_reply_type=legacy.EXPECTED_REPLY_TIME,
        booking_time_service_candidate=False,
        expected_reply_shortcircuit=True,
        booking_interrupt_text="Сколько времени занимает маникюр?",
        client_slug="demo_salon",
    )

    assert "duration" in resolved


def test_resolve_booking_info_intents_uses_parking_signal_with_expected_reply_shortcircuit():
    resolved = booking_router._resolve_booking_info_intents(
        intent_decomp_used=True,
        intent_decomp_set={"other"},
        info_class_intents=set(),
        expected_reply_type=legacy.EXPECTED_REPLY_TIME,
        booking_time_service_candidate=False,
        expected_reply_shortcircuit=True,
        booking_interrupt_text="У вас есть парковка?",
        client_slug="demo_salon",
    )

    assert "parking" in resolved


def test_looks_like_booking_reschedule_request_detects_change_time_phrase():
    assert booking_router._looks_like_booking_reschedule_request(
        "Я хочу изменить время на утро."
    )


def test_looks_like_booking_reschedule_request_skips_regular_duration_question():
    assert not booking_router._looks_like_booking_reschedule_request(
        "Сколько длится процедура маникюра?"
    )


def test_validate_datetime_slot_accepts_date_only_hint():
    assert booking_router._validate_datetime_slot(
        "Я хочу выбрать время на завтра.",
        allow_freeform=True,
        client_slug="demo_salon",
    ) == "завтра"


def test_validate_datetime_slot_accepts_explicit_time_marker():
    assert booking_router._validate_datetime_slot(
        "Я хочу выбрать время на завтра в 15:00.",
        allow_freeform=True,
        client_slug="demo_salon",
    ) == "15:00"


def test_next_booking_prompt_requests_precise_time_for_date_only_slot():
    booking_state, prompt = booking_router._next_booking_prompt(
        {
            "active": True,
            "service": "Стрижка",
            "datetime": "завтра",
        }
    )

    assert booking_state.get("last_question") == "datetime"
    assert isinstance(prompt, str)
    assert "точное время" in prompt.lower()


def test_update_booking_from_message_overrides_date_only_datetime_with_exact_time():
    booking = {
        "active": True,
        "service": "Стрижка",
        "datetime": "завтра",
        "last_question": "datetime",
    }

    updated = booking_router._update_booking_from_message(
        booking,
        "Тогда в 15:00.",
        client_slug="demo_salon",
    )

    assert updated.get("datetime") == "15:00"


@pytest.mark.parametrize(
    "tool_action",
    ["calendar.get_booking", "calendar.reschedule", "calendar.cancel"],
)
def test_tool_registry_invalid_appointment_id_returns_contract_error(tool_action):
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "none"},
        timezone="Asia/Almaty",
    )

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service, "_get_booking", return_value=(None, "booking_not_found")
    ):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action=tool_action,
            tool_args={"appointment_id": "15:30"},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query=None,
        )

    assert result.handled is True
    assert result.ok is False
    assert result.error_code == "tool_args_invalid"
    assert result.decision_meta.get("tool_decision") == "invalid_args"
    assert result.decision_meta.get("tool_args_error") == "appointment_id_invalid"


def test_tool_registry_get_booking_reports_time_mismatch():
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "none"},
        timezone="Asia/Almaty",
    )
    appointment = SimpleNamespace(
        id=uuid4(),
        start_at=datetime(2026, 2, 14, 9, 0, tzinfo=timezone.utc),
        specialist_id=None,
    )

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service, "_get_booking", return_value=(appointment, None)
    ), patch.object(
        tool_registry_service, "_format_booking_summary", return_value="dummy-summary"
    ):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.get_booking",
            tool_args={"appointment_id": ""},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query=None,
            message_text="Можете подтвердить мою запись на 15:30?",
        )

    assert result.handled is True
    assert result.ok is False
    assert result.error_code == "booking_time_mismatch"
    assert result.decision_meta["tool_decision"] == "time_mismatch"
    assert result.decision_meta["requested_time"] == "15:30"
    assert result.decision_meta["appointment_time"] == "09:00"


def test_tool_registry_get_booking_not_found_acknowledges_photo_offer():
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "none"},
        timezone="Asia/Almaty",
    )

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service, "_get_booking", return_value=(None, "booking_not_found")
    ):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.get_booking",
            tool_args={"appointment_id": ""},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query=None,
            message_text="Могу прислать фото своего стиля",
        )

    assert result.handled is True
    assert result.ok is False
    assert result.error_code == "booking_not_found"
    assert "Спасибо за фото/референс" in (result.response_text or "")


def test_tool_registry_reschedule_not_found_echoes_requested_time():
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "none"},
        timezone="Asia/Almaty",
    )

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service, "_get_booking", return_value=(None, "booking_not_found")
    ):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.reschedule",
            tool_args={"appointment_id": ""},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query=None,
            message_text="Я хочу изменить время на 15:00",
            expected_reply_type="name",
        )

    assert result.handled is True
    assert result.ok is False
    assert result.error_code == "booking_not_found"
    assert "Время 15:00 отметил." in (result.response_text or "")
    assert "Как вас зовут?" in (result.response_text or "")
    assert result.decision_meta.get("requested_time") == "15:00"


def test_tool_registry_book_slot_allows_missing_specialist_when_not_explicit():
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "google_calendar"},
        timezone="Asia/Almaty",
    )
    appointment = SimpleNamespace(id=uuid4(), specialist_id=None)

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service,
        "get_provider_health",
        return_value=SimpleNamespace(ready=True, reason=None),
    ), patch.object(
        tool_registry_service,
        "_resolve_specialist_for_booking",
        return_value=(None, None, "specialist_not_found"),
    ), patch.object(
        tool_registry_service,
        "_book_slot",
        return_value=(appointment, None),
    ) as book_slot_mock, patch.object(
        tool_registry_service, "enqueue_appointment_sync", return_value=None
    ), patch.object(
        tool_registry_service, "schedule_default_reminders", return_value=[]
    ):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.book_slot",
            tool_args={"start_at": "2026-02-12T13:00:00", "service_query": "Маникюр"},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="Маникюр",
            user_name="Лена",
            user_phone="+77011112233",
        )

    assert result.handled is True
    assert result.ok is True
    assert result.decision_meta.get("tool_decision") == "ok"
    assert result.decision_meta.get("appointment_id") == str(appointment.id)
    assert result.decision_meta.get("specialist_selection") == "none_available"
    _, kwargs = book_slot_mock.call_args
    assert kwargs["specialist_id"] is None


def test_tool_registry_book_slot_time_only_uses_runtime_relative_base():
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "google_calendar"},
        timezone="Asia/Almaty",
    )
    specialist = SimpleNamespace(id=uuid4(), name="Алия")
    appointment = SimpleNamespace(id=uuid4(), specialist_id=specialist.id)
    now = datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc)

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
        return_value=(appointment, None),
    ) as book_slot_mock, patch.object(
        tool_registry_service, "enqueue_appointment_sync", return_value=None
    ), patch.object(
        tool_registry_service, "schedule_default_reminders", return_value=[]
    ):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.book_slot",
            tool_args={"start_at": "11:00", "service_query": "Маникюр"},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="Маникюр",
            user_name="Лена",
            user_phone="+77011112233",
            now=now,
        )

    assert result.handled is True
    assert result.ok is True
    _, kwargs = book_slot_mock.call_args
    parsed_start_at = kwargs["start_at"]
    assert isinstance(parsed_start_at, datetime)
    assert parsed_start_at.year == 2026
    assert parsed_start_at.month == 2
    assert parsed_start_at.day == 18
    assert parsed_start_at.hour == 11


def test_tool_registry_list_slots_allows_sync_stale_provider_health():
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "google_calendar"},
        timezone="Asia/Almaty",
    )

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service,
        "get_provider_health",
        return_value=SimpleNamespace(ready=False, reason="sync_stale"),
    ), patch.object(
        tool_registry_service,
        "_list_slots",
        return_value=("Свободные слоты: мастер A 10:00", None),
    ) as list_slots_mock:
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.list_slots",
            tool_args={"date": "2026-02-20", "duration_min": 30},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="Маникюр",
        )

    assert result.handled is True
    assert result.ok is True
    assert result.decision_meta.get("tool_decision") == "ok"
    assert result.decision_meta.get("provider_health_reason") == "sync_stale"
    assert result.decision_meta.get("provider_health_degraded") is True
    assert result.trace.get("provider_health_reason") == "sync_stale"
    assert list_slots_mock.called


def test_tool_registry_list_slots_reports_requested_time_unavailable_explicitly():
    db = Mock()
    specialist_a = SimpleNamespace(id=uuid4(), name="Айгерим")
    specialist_b = SimpleNamespace(id=uuid4(), name="Дана")
    specialists = [specialist_a, specialist_b]

    specialist_query = Mock()
    specialist_query.filter.return_value.order_by.return_value.all.return_value = specialists
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
    slot_1745 = SimpleNamespace(start=datetime(2026, 2, 20, 17, 45, tzinfo=timezone.utc), available=True)
    slot_1800 = SimpleNamespace(start=datetime(2026, 2, 20, 18, 0, tzinfo=timezone.utc), available=True)
    slot_1900 = SimpleNamespace(start=datetime(2026, 2, 20, 19, 0, tzinfo=timezone.utc), available=True)

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service,
        "_resolve_specialist_filter",
        return_value=(None, None, None),
    ), patch.object(tool_registry_service, "SchedulingService") as scheduling_cls:
        scheduling = scheduling_cls.return_value
        scheduling.get_available_slots.side_effect = [
            [slot_1745, slot_1800],
            [slot_1900],
        ]

        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.list_slots",
            tool_args={"start_at": "2026-02-20T18:30:00+05:00"},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="Стрижка",
            message_text="Можно на 18:30?",
        )

    assert result.handled is True
    assert result.ok is True
    assert "На 18:30 свободного окна нет." in (result.response_text or "")
    assert "Доступны: 17:45, 18:00, 19:00." in (result.response_text or "")


def test_tool_registry_list_slots_reports_requested_time_available_explicitly():
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
    slot_1745 = SimpleNamespace(start=datetime(2026, 2, 20, 17, 45, tzinfo=timezone.utc), available=True)
    slot_1800 = SimpleNamespace(start=datetime(2026, 2, 20, 18, 0, tzinfo=timezone.utc), available=True)

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service,
        "_resolve_specialist_filter",
        return_value=(None, None, None),
    ), patch.object(tool_registry_service, "SchedulingService") as scheduling_cls:
        scheduling_cls.return_value.get_available_slots.return_value = [slot_1745, slot_1800]

        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.list_slots",
            tool_args={"start_at": "2026-02-20T17:45:00+05:00"},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="Стрижка",
            message_text="Можно на 17:45?",
        )

    assert result.handled is True
    assert result.ok is True
    assert "Да, на 17:45 есть свободное окно." in (result.response_text or "")
    assert "Свободные слоты:" in (result.response_text or "")


def test_tool_registry_book_slot_allows_sync_missing_provider_health():
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "google_calendar"},
        timezone="Asia/Almaty",
    )
    specialist = SimpleNamespace(id=uuid4(), name="Алия")
    appointment = SimpleNamespace(id=uuid4(), specialist_id=specialist.id)

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service,
        "get_provider_health",
        return_value=SimpleNamespace(ready=False, reason="sync_missing"),
    ), patch.object(
        tool_registry_service,
        "_resolve_specialist_for_booking",
        return_value=(specialist, "service_default", None),
    ), patch.object(
        tool_registry_service,
        "_book_slot",
        return_value=(appointment, None),
    ), patch.object(
        tool_registry_service, "enqueue_appointment_sync", return_value=None
    ), patch.object(
        tool_registry_service, "schedule_default_reminders", return_value=[]
    ):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.book_slot",
            tool_args={"start_at": "2026-02-20T10:00:00"},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="Маникюр",
            user_name="Лена",
            user_phone="+77011112233",
        )

    assert result.handled is True
    assert result.ok is True
    assert result.decision_meta.get("tool_decision") == "ok"
    assert result.decision_meta.get("provider_health_reason") == "sync_missing"
    assert result.decision_meta.get("provider_health_degraded") is True
    assert result.trace.get("provider_health_reason") == "sync_missing"


def test_tool_registry_book_slot_pending_status_uses_non_confirming_reply_template():
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "google_calendar"},
        timezone="Asia/Almaty",
    )
    specialist = SimpleNamespace(id=uuid4(), name="Алия")
    appointment = SimpleNamespace(
        id=uuid4(),
        specialist_id=specialist.id,
        status="PENDING_CONFIRMATION",
    )

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
        return_value=(appointment, None),
    ), patch.object(
        tool_registry_service, "enqueue_appointment_sync", return_value=None
    ), patch.object(
        tool_registry_service, "schedule_default_reminders", return_value=[]
    ):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.book_slot",
            tool_args={"start_at": "2026-02-20T10:00:00"},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="Маникюр",
        )

    assert result.handled is True
    assert result.ok is True
    assert result.response_text == "Заявка на запись принята. Менеджер подтвердит время."
    assert result.decision_meta.get("appointment_status") == "PENDING_CONFIRMATION"
    assert result.decision_meta.get("booking_blocked_reason") is None


def test_tool_registry_book_slot_blocks_on_token_expired_provider_health():
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "google_calendar"},
        timezone="Asia/Almaty",
    )

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service,
        "get_provider_health",
        return_value=SimpleNamespace(ready=False, reason="token_expired"),
    ), patch.object(tool_registry_service, "_book_slot") as book_slot_mock:
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.book_slot",
            tool_args={"start_at": "2026-02-20T10:00:00"},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="Маникюр",
        )

    assert result.handled is True
    assert result.ok is False
    assert result.error_code == "provider_unavailable"
    assert result.decision_meta.get("provider_reason") == "token_expired"
    assert book_slot_mock.called is False


def test_tool_registry_blocks_action_when_capabilities_deny_token():
    db = Mock()
    runtime = RuntimeCapabilities(
        payload=CapabilitiesPayload.model_validate({"tools": {"deny": ["calendar.*"]}}),
        client_id=uuid4(),
        branch_id=None,
        source="client_capabilities",
        has_records=True,
    )
    set_runtime_capabilities(runtime)
    try:
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="calendar.list_slots",
            tool_args={},
            conversation_id=uuid4(),
            branch_id=None,
            client_slug="demo_salon",
            service_query=None,
        )
    finally:
        set_runtime_capabilities(None)

    assert result.handled is True
    assert result.ok is False
    assert result.error_code == "tool_action_disabled"
    assert result.decision_meta.get("tool_decision") == "capability_blocked"
    assert result.decision_meta.get("capability_reason") == "deny:calendar.*"


def test_tool_registry_blocks_action_on_allowlist_miss():
    db = Mock()
    runtime = RuntimeCapabilities(
        payload=CapabilitiesPayload.model_validate({"tools": {"allow": ["catalog.location"]}}),
        client_id=uuid4(),
        branch_id=None,
        source="client_capabilities",
        has_records=True,
    )
    set_runtime_capabilities(runtime)
    try:
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="catalog.portfolio",
            tool_args={},
            conversation_id=uuid4(),
            branch_id=None,
            client_slug="demo_salon",
            service_query=None,
        )
    finally:
        set_runtime_capabilities(None)

    assert result.handled is True
    assert result.ok is False
    assert result.error_code == "tool_action_disabled"
    assert result.decision_meta.get("tool_decision") == "capability_blocked"
    assert result.decision_meta.get("capability_reason") == "allowlist_miss"


def test_tool_registry_skips_capability_block_when_enforcement_disabled(monkeypatch):
    monkeypatch.setenv("TOOL_POLICY_ENFORCEMENT", "0")
    db = Mock()
    runtime = RuntimeCapabilities(
        payload=CapabilitiesPayload.model_validate({"tools": {"allow": ["catalog.location"]}}),
        client_id=uuid4(),
        branch_id=None,
        source="client_capabilities",
        has_records=True,
    )
    set_runtime_capabilities(runtime)
    try:
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="catalog.portfolio",
            tool_args={},
            conversation_id=uuid4(),
            branch_id=None,
            client_slug="demo_salon",
            service_query=None,
        )
    finally:
        set_runtime_capabilities(None)

    assert result.error_code != "tool_action_disabled"
    assert result.decision_meta.get("tool_decision") != "capability_blocked"


def test_tool_registry_rejects_invalid_args_contract_for_book_slot():
    db = Mock()

    result = tool_registry_service.execute_tool_action(
        db,
        tool_action="calendar.book_slot",
        tool_args={"start_at": {"date": "2026-02-20"}},
        conversation_id=uuid4(),
        branch_id=uuid4(),
        client_slug="demo_salon",
        service_query="Маникюр",
    )

    assert result.handled is True
    assert result.ok is False
    assert result.error_code == "tool_args_invalid"
    assert result.decision_meta.get("tool_decision") == "invalid_args"
    assert result.decision_meta.get("tool_args_contract") == "invalid"
    assert result.decision_meta.get("tool_args_error") == "start_at_type_invalid"


def test_tool_registry_rejects_invalid_args_contract_for_get_booking():
    db = Mock()

    result = tool_registry_service.execute_tool_action(
        db,
        tool_action="calendar.get_booking",
        tool_args={"appointment_id": "not-a-uuid"},
        conversation_id=uuid4(),
        branch_id=uuid4(),
        client_slug="demo_salon",
        service_query=None,
    )

    assert result.handled is True
    assert result.ok is False
    assert result.error_code == "tool_args_invalid"
    assert result.decision_meta.get("tool_decision") == "invalid_args"
    assert result.decision_meta.get("tool_args_error") == "appointment_id_invalid"
    assert result.decision_meta.get("tool_args_error_field") == "appointment_id"


def test_tool_registry_rejects_invalid_args_contract_for_catalog_location():
    db = Mock()

    result = tool_registry_service.execute_tool_action(
        db,
        tool_action="catalog.location",
        tool_args={"info_refs": "parking"},
        conversation_id=uuid4(),
        branch_id=None,
        client_slug="demo_salon",
        service_query=None,
    )

    assert result.handled is True
    assert result.ok is False
    assert result.error_code == "tool_args_invalid"
    assert result.decision_meta.get("tool_decision") == "invalid_args"
    assert result.decision_meta.get("tool_args_error") == "info_refs_type_invalid"
    assert result.decision_meta.get("tool_args_error_field") == "info_refs"


def test_tool_registry_catalog_location_includes_parking_section():
    db = Mock()

    with patch.object(tool_registry_service, "_resolve_branch", return_value=None):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="catalog.location",
            tool_args={},
            conversation_id=uuid4(),
            branch_id=None,
            client_slug="demo_salon",
            service_query=None,
            message_text="У вас есть парковка?",
        )

    assert result.handled is True
    assert result.ok is True
    assert "parking" in (result.decision_meta.get("info_sections") or [])


def test_tool_registry_catalog_location_uses_parking_hint_without_message_text():
    db = Mock()

    with patch.object(tool_registry_service, "_resolve_branch", return_value=None):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="catalog.location",
            tool_args={},
            conversation_id=uuid4(),
            branch_id=None,
            client_slug="demo_salon",
            service_query=None,
            info_sections_hint=["parking"],
            message_text=None,
        )

    assert result.handled is True
    assert result.ok is True
    assert "parking" in (result.decision_meta.get("info_sections") or [])


def test_tool_registry_catalog_service_query_avoids_unrelated_semantic_fallback():
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "none"},
        timezone="Asia/Almaty",
    )

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service, "_catalog_service_query", return_value=(None, "service_not_found")
    ), patch(
        "app.services.demo_salon_knowledge._match_service",
        return_value={"name": "Окрашивание", "aliases": [["окрашивание"]]},
    ):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="catalog.service_query",
            tool_args={},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="криомассаж",
        )

    assert result.handled is True
    assert result.ok is True
    assert result.decision_meta.get("tool_decision") == "not_found_fallback"


def test_tool_registry_catalog_service_query_pricing_uses_price_item_fallback():
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "none"},
        timezone="Asia/Almaty",
    )

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch), patch.object(
        tool_registry_service, "_catalog_service_query", return_value=(None, "service_not_found")
    ):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="catalog.service_query",
            tool_args={},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="укладка",
            info_sections_hint=["pricing"],
            message_text="А сколько стоит укладка?",
        )

    assert result.handled is True
    assert result.ok is True
    assert result.decision_meta.get("tool_decision") == "price_item_fallback"
    assert "укладка" in (result.response_text or "").lower()


def test_tool_registry_catalog_service_query_duration_prefers_message_service_over_stale_slot():
    db = Mock()
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        booking_settings={"availability_provider": "none"},
        timezone="Asia/Almaty",
    )

    with patch.object(tool_registry_service, "_resolve_branch", return_value=branch):
        result = tool_registry_service.execute_tool_action(
            db,
            tool_action="catalog.service_query",
            tool_args={},
            conversation_id=uuid4(),
            branch_id=branch.id,
            client_slug="demo_salon",
            service_query="Маникюр",
            info_sections_hint=["duration"],
            message_text="Сколько времени занимает укладка?",
        )

    assert result.handled is True
    assert result.ok is True
    assert result.decision_meta.get("tool_decision") == "duration"
    assert "укладка" in (result.response_text or "").lower()
    assert "маникюр" not in (result.response_text or "").lower()


def test_demo_salon_price_item_match_ignores_booking_datetime_phrase():
    matched = demo_salon_knowledge._find_best_price_item("в субботу вечером", "demo_salon")
    assert matched is None


def test_demo_salon_price_item_match_rejects_unrelated_fuzzy_overlap():
    matched = demo_salon_knowledge._find_best_price_item("подравнять бороду сколько стоит", "demo_salon")
    assert matched is None
