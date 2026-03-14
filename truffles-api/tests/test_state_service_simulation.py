from types import SimpleNamespace
from uuid import uuid4

from app.services import state_service


def test_apply_simulation_context_rejects_non_test_traffic_and_clears_existing(monkeypatch):
    monkeypatch.delenv("TEST_MODE", raising=False)
    monkeypatch.delenv("SIMULATION_ALLOWLIST_JIDS", raising=False)
    monkeypatch.delenv("OUTBOUND_ALLOWLIST_JIDS", raising=False)

    conversation = SimpleNamespace(
        id=uuid4(),
        context={"simulation": {"mode": True, "id": "old"}},
    )
    metadata = SimpleNamespace(
        remoteJid="77000000000@s.whatsapp.net",
        simulation_mode=True,
        simulation_id="sim-1",
        simulation_llm=True,
        simulation_time=None,
    )

    applied = state_service.apply_simulation_context(conversation, metadata)

    assert applied is None
    assert "simulation" not in conversation.context


def test_apply_simulation_context_allows_when_test_mode_enabled(monkeypatch):
    monkeypatch.setenv("TEST_MODE", "1")
    monkeypatch.delenv("SIMULATION_ALLOWLIST_JIDS", raising=False)

    conversation = SimpleNamespace(id=uuid4(), context={})
    metadata = SimpleNamespace(
        remoteJid="77000000000@s.whatsapp.net",
        simulation_mode=True,
        simulation_id="sim-2",
        simulation_llm=True,
        simulation_time="2026-02-08T00:00:00Z",
    )

    applied = state_service.apply_simulation_context(conversation, metadata)

    assert isinstance(applied, dict)
    assert applied.get("mode") is True
    assert conversation.context.get("simulation", {}).get("id") == "sim-2"


def test_apply_simulation_context_allows_allowlisted_jid(monkeypatch):
    monkeypatch.setenv("TEST_MODE", "0")
    monkeypatch.setenv("SIMULATION_ALLOWLIST_JIDS", "77011112233@s.whatsapp.net")

    conversation = SimpleNamespace(id=uuid4(), context={})
    metadata = SimpleNamespace(
        remoteJid="77011112233@s.whatsapp.net",
        simulation_mode=True,
        simulation_id="sim-3",
        simulation_llm=False,
        simulation_time=None,
    )

    applied = state_service.apply_simulation_context(conversation, metadata)

    assert isinstance(applied, dict)
    assert applied.get("id") == "sim-3"


def test_apply_simulation_context_allows_internal_console_source(monkeypatch):
    monkeypatch.setenv("TEST_MODE", "0")
    monkeypatch.delenv("SIMULATION_ALLOWLIST_JIDS", raising=False)
    monkeypatch.delenv("OUTBOUND_ALLOWLIST_JIDS", raising=False)

    conversation = SimpleNamespace(id=uuid4(), context={})
    metadata = SimpleNamespace(
        remoteJid="77015557777@s.whatsapp.net",
        simulation_mode=True,
        simulation_id="sim-console",
        simulation_llm=True,
        simulation_time=None,
    )

    applied = state_service.apply_simulation_context(
        conversation,
        metadata,
        allow_internal_source=True,
    )

    assert isinstance(applied, dict)
    assert applied.get("id") == "sim-console"
    assert conversation.context.get("simulation", {}).get("mode") is True
