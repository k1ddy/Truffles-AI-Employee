import ast
from pathlib import Path

from app.services import reasoning_core


def _stage_order_hash(stage_order):
    return reasoning_core.stage_order_hash(stage_order)

def _load_stage_order_snapshot():
    trace_path = Path(__file__).resolve().parents[1] / "app/routers/webhook/trace.py"
    module = ast.parse(trace_path.read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "DECISION_STAGE_ORDER_SNAPSHOT":
                    return ast.literal_eval(node.value)
    raise AssertionError("DECISION_STAGE_ORDER_SNAPSHOT not found")


def test_outbox_payload_contract_valid_minimal():
    from app.schemas.outbox_payload import validate_outbox_payload

    payload = {
        "client_slug": "demo_salon",
        "body": {
            "messageType": "text",
            "message": "hello",
            "metadata": {
                "remoteJid": "77015705555@s.whatsapp.net",
                "messageId": "MSG-1",
                "timestamp": 1700000000,
            },
        },
    }

    contract, error = validate_outbox_payload(payload, expected_client_slug="demo_salon")
    assert error is None
    assert contract is not None
    assert contract.client_slug == "demo_salon"
    assert contract.body.metadata.remoteJid == "77015705555@s.whatsapp.net"


def test_outbox_payload_contract_requires_remote_jid():
    from app.schemas.outbox_payload import validate_outbox_payload

    payload = {
        "client_slug": "demo_salon",
        "body": {
            "messageType": "text",
            "message": "hello",
            "metadata": {
                "messageId": "MSG-2",
                "timestamp": 1700000001,
            },
        },
    }

    contract, error = validate_outbox_payload(payload)
    assert contract is None
    assert error is not None


def test_outbox_payload_contract_requires_message_or_media():
    from app.schemas.outbox_payload import validate_outbox_payload

    payload = {
        "client_slug": "demo_salon",
        "body": {
            "messageType": "text",
            "message": " ",
            "metadata": {
                "remoteJid": "77015705555@s.whatsapp.net",
                "messageId": "MSG-3",
            },
        },
    }

    contract, error = validate_outbox_payload(payload)
    assert contract is None
    assert error is not None


def test_outbox_payload_contract_client_slug_mismatch():
    from app.schemas.outbox_payload import validate_outbox_payload

    payload = {
        "client_slug": "demo_salon",
        "body": {
            "messageType": "text",
            "message": "hello",
            "metadata": {"remoteJid": "77015705555@s.whatsapp.net"},
        },
    }

    contract, error = validate_outbox_payload(payload, expected_client_slug="other")
    assert contract is None
    assert error == "client_slug_mismatch"


def test_semantic_service_match_passes_client_slug(monkeypatch):
    from app.services import demo_salon_knowledge as knowledge

    def fake_search(text, client_slug, limit):
        return [
            {
                "score": knowledge._SERVICE_MATCH_THRESHOLD + 0.05,
                "payload": {"canonical_name": "Test"},
            }
        ]

    captured = {}

    def fake_format(payload, client_slug):
        captured["client_slug"] = client_slug
        return "ok"

    monkeypatch.setattr(knowledge, "_search_services_index", fake_search)
    monkeypatch.setattr(knowledge, "_format_semantic_service_reply", fake_format)

    result = knowledge.semantic_service_match("test service?", "demo_salon")
    assert result is not None
    assert captured.get("client_slug") == "demo_salon"


def test_stage_order_snapshot_hash():
    expected = "b6c87735e12b96f11eca885a2d908cfb562385456d5ed2b34678b695834410dd"
    stage_order = _load_stage_order_snapshot()
    assert _stage_order_hash(stage_order) == expected
