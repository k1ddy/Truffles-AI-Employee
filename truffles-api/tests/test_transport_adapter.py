from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services.transport_adapter import TransportSendRequest, resolve_transport_adapter
from app.services.transport_adapters.chatflow import ChatflowTransportAdapter
from app.services.transport_adapters.test_sink import TestSinkTransportAdapter


def _build_request(**overrides):
    base = {
        "remote_jid": "77000000000@s.whatsapp.net",
        "text": "test",
        "idempotency_key": "msg-id-1",
        "instance_id": "instance-1",
        "client_id": "client-1",
        "client_slug": "demo_salon",
        "conversation_id": "conv-1",
        "branch_id": "branch-1",
        "use_outbox_send": False,
        "simulation": False,
    }
    base.update(overrides)
    return TransportSendRequest(**base)


def test_resolve_transport_adapter_defaults_to_chatflow():
    adapter = resolve_transport_adapter(name="chatflow")
    assert isinstance(adapter, ChatflowTransportAdapter)


def test_resolve_transport_adapter_test_sink():
    adapter = resolve_transport_adapter(name="test_sink")
    assert isinstance(adapter, TestSinkTransportAdapter)


def test_test_sink_collects_events():
    adapter = TestSinkTransportAdapter()
    TestSinkTransportAdapter.clear_events()

    result = adapter.send_text(db=Mock(), request=_build_request())

    assert result.delivered is True
    assert result.status == "sent"
    events = TestSinkTransportAdapter.get_events()
    assert len(events) == 1
    assert events[0]["idempotency_key"] == "msg-id-1"


def test_chatflow_adapter_fails_without_instance_id():
    adapter = ChatflowTransportAdapter()

    result = adapter.send_text(db=Mock(), request=_build_request(instance_id=None))

    assert result.delivered is False
    assert result.status == "failed"
    assert result.reason == "instance_id_missing"


def test_chatflow_adapter_outbox_duplicate_is_idempotent_success():
    adapter = ChatflowTransportAdapter()
    with patch(
        "app.services.transport_adapters.chatflow.enqueue_outbox_message",
        return_value=False,
    ):
        result = adapter.send_text(
            db=Mock(),
            request=_build_request(use_outbox_send=True),
        )

    assert result.delivered is True
    assert result.status == "duplicate"
    assert result.reason == "outbox_duplicate"


def test_chatflow_adapter_provider_failure_returns_failed_result():
    adapter = ChatflowTransportAdapter()
    provider_result = SimpleNamespace(is_ok=lambda: False, error="provider down")

    with patch("app.services.transport_adapters.chatflow.ChatFlowAdapter") as adapter_cls:
        adapter_cls.return_value.send_text.return_value = provider_result
        result = adapter.send_text(db=Mock(), request=_build_request())

    assert result.delivered is False
    assert result.status == "failed"
    assert result.reason == "provider_send_failed"
    assert result.provider_error == "provider down"
