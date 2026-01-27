from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.provider_gateway_app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_reports_flags(client, monkeypatch):
    monkeypatch.setenv("PROVIDER_GATEWAY_INBOUND_ENABLED", "1")
    monkeypatch.setenv("PROVIDER_GATEWAY_STATUS_ENABLED", "0")
    monkeypatch.setenv("PROVIDER_GATEWAY_INBOX_ENABLED", "true")
    monkeypatch.setenv("PROVIDER_GATEWAY_OUTBOUND_ENABLED", "1")

    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["service"] == "provider_gateway"
    assert payload["inbound_enabled"] is True
    assert payload["status_enabled"] is False
    assert payload["inbox_enabled"] is True
    assert payload["outbound_enabled"] is True
