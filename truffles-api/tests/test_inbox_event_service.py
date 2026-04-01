from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.schemas.provider_gateway import ProviderInbound
from app.services.inbox_event_service import record_inbox_event


def _payload_dict(client_slug: str = "demo_salon") -> dict:
    return {
        "provider": "chatflow",
        "channel": "whatsapp",
        "provider_message_id": "msg-123",
        "tenant_context": {
            "client_id": str(uuid4()),
            "client_slug": client_slug,
            "instance_id": "demo-instance",
        },
        "received_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sender": {
            "id": "77770000000",
            "phone": "77770000000",
            "jid": "77770000000@s.whatsapp.net",
            "display_name": "Tester",
        },
        "receiver": {"id": "salon-number", "phone": "77778889999"},
        "message": {"type": "text", "text": "Привет"},
    }


def test_record_inbox_event_duplicate_returns_duplicate():
    db = Mock()
    client = SimpleNamespace(name="demo_salon")
    db.query.return_value.filter.return_value.first.return_value = client
    db.execute.return_value.rowcount = 0

    payload = ProviderInbound.model_validate(_payload_dict())
    ok, result = record_inbox_event(db, payload=payload, raw_payload=_payload_dict())

    assert ok is False
    assert result == "duplicate"
    db.commit.assert_called_once()


def test_record_inbox_event_invalid_received_at():
    db = Mock()
    client = SimpleNamespace(name="demo_salon")
    db.query.return_value.filter.return_value.first.return_value = client
    payload_dict = _payload_dict()
    payload_dict["received_at"] = "not-a-date"
    payload = ProviderInbound.model_validate(payload_dict)

    ok, result = record_inbox_event(db, payload=payload, raw_payload=payload_dict)

    assert ok is False
    assert result == "invalid_received_at"


def test_record_inbox_event_serializes_tenant_context():
    db = Mock()
    client = SimpleNamespace(name="demo_salon")
    db.query.return_value.filter.return_value.first.return_value = client

    def _execute(stmt):
        params = stmt.compile().params
        json.dumps(params["tenant_context"])
        return SimpleNamespace(rowcount=1)

    db.execute.side_effect = _execute

    payload_dict = _payload_dict()
    payload = ProviderInbound.model_validate(payload_dict)

    ok, result = record_inbox_event(db, payload=payload, raw_payload=payload_dict)

    assert ok is True
    assert result not in {"duplicate", "db_error"}
    db.commit.assert_called_once()
