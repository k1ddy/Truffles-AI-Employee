from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.services.console_errors import ConsoleAPIError


def test_parse_outbox_status_param_defaults_to_failed():
    assert console_router._parse_outbox_status_param(None) == ["FAILED"]
    assert console_router._parse_outbox_status_param("") == ["FAILED"]


def test_parse_outbox_status_param_all():
    assert console_router._parse_outbox_status_param("all") is None


def test_parse_outbox_status_param_invalid():
    with pytest.raises(ConsoleAPIError):
        console_router._parse_outbox_status_param("oops")


def test_summarize_outbox_payload_contract():
    payload = {
        "client_slug": "demo_salon",
        "tenant_context": {
            "client_id": str(uuid4()),
            "branch_id": str(uuid4()),
        },
        "body": {
            "messageType": "text",
            "message": "Hello there",
            "metadata": {
                "remoteJid": "77000000000@s.whatsapp.net",
                "instanceId": "demo",
                "forwarded_to_telegram": True,
            },
        },
    }
    summary = console_router._summarize_outbox_payload(payload)
    assert summary["message_type"] == "text"
    assert summary["message_preview"] == "Hello there"
    assert summary["remote_jid"] == "77000000000@s.whatsapp.net"
    assert summary["instance_id"] == "demo"
    assert summary["forwarded_to_telegram"] is True
    assert summary["channel"] == "whatsapp"


def test_summarize_outbox_payload_fallback():
    payload = {
        "body": {
            "message": "Fallback message",
            "metadata": {"remoteJid": "77000000000@s.whatsapp.net"},
        }
    }
    summary = console_router._summarize_outbox_payload(payload)
    assert summary["message_preview"] == "Fallback message"
    assert summary["remote_jid"] == "77000000000@s.whatsapp.net"
    assert summary["channel"] == "whatsapp"
