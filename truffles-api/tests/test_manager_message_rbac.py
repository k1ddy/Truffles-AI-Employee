from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.services import manager_message_service as service
from app.services.result import Result


def test_prepare_handover_denies_non_assigned_active(monkeypatch):
    conversation = SimpleNamespace(client_id=uuid4(), branch_id=uuid4())
    handover = SimpleNamespace(status="active", assigned_to=str(uuid4()), id=uuid4())
    linked_agent = SimpleNamespace(
        id=uuid4(),
        name="Agent",
        role="manager",
        branch_id=conversation.branch_id,
        client_id=conversation.client_id,
    )

    monkeypatch.setattr(
        service,
        "find_conversation_by_telegram",
        lambda db, chat_id, message_thread_id: (conversation, handover),
    )
    monkeypatch.setattr(
        service,
        "resolve_linked_agent",
        lambda db, telegram_user_id, client_id, branch_id: linked_agent,
    )

    result = service._prepare_handover_for_manager(
        Mock(),
        chat_id=1,
        message_thread_id=2,
        manager_telegram_id=123,
        manager_name="Bob",
    )

    assert result[0] is None
    assert result[1] is None
    assert result[2] is None
    assert result[3] is False
    assert result[4] == "Access denied"


def test_prepare_handover_auto_take_records_audit_and_notify(monkeypatch):
    conversation = SimpleNamespace(client_id=uuid4(), branch_id=uuid4())
    handover = SimpleNamespace(status="pending", assigned_to=None, id=uuid4())
    linked_agent = SimpleNamespace(
        id=uuid4(),
        name="Agent",
        role="manager",
        branch_id=conversation.branch_id,
        client_id=conversation.client_id,
    )

    monkeypatch.setattr(
        service,
        "find_conversation_by_telegram",
        lambda db, chat_id, message_thread_id: (conversation, handover),
    )
    monkeypatch.setattr(
        service,
        "resolve_linked_agent",
        lambda db, telegram_user_id, client_id, branch_id: linked_agent,
    )

    take_mock = Mock(return_value=Result.success(True))
    audit_mock = Mock()
    notify_mock = Mock(return_value=(True, None))

    monkeypatch.setattr(service, "state_manager_take", take_mock)
    monkeypatch.setattr(service, "record_audit_event", audit_mock)
    monkeypatch.setattr(service, "notify_client_manager_status", notify_mock)

    result = service._prepare_handover_for_manager(
        Mock(),
        chat_id=1,
        message_thread_id=2,
        manager_telegram_id=123,
        manager_name="Bob",
    )

    assert result[0] is conversation
    assert result[1] is handover
    assert result[2] is linked_agent
    assert result[3] is True
    assert result[4] == ""
    take_mock.assert_called_once()
    assert audit_mock.call_count == 2
    notify_mock.assert_called_once()


def test_process_manager_message_sets_first_response_on_real_reply(monkeypatch):
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        branch_id=uuid4(),
        user_id=uuid4(),
        context={},
    )
    handover = SimpleNamespace(
        id=uuid4(),
        status="active",
        assigned_to=None,
        assigned_to_name=None,
        first_response_at=None,
        manager_response=None,
        channel_ref="777@s.whatsapp.net",
    )
    linked_agent = SimpleNamespace(id=uuid4(), name="Agent")

    monkeypatch.setattr(
        service,
        "_prepare_handover_for_manager",
        lambda *args, **kwargs: (conversation, handover, linked_agent, False, ""),
    )
    monkeypatch.setattr(service, "save_message", lambda **kwargs: None)
    monkeypatch.setattr(service, "is_simulation_context", lambda *_args, **_kwargs: True)

    before = datetime.now(timezone.utc)
    message_text = "Hello, I am here to help"
    ok, message, took_handover, returned_handover = service.process_manager_message(
        Mock(),
        chat_id=1,
        message_text=message_text,
        manager_telegram_id=123,
        manager_name="Agent",
    )

    assert ok is True
    assert "Simulation" in message
    assert took_handover is False
    assert returned_handover is handover
    assert handover.manager_response == message_text
    assert handover.assigned_to_name == "Agent"
    assert handover.first_response_at is not None
    assert handover.first_response_at >= before
