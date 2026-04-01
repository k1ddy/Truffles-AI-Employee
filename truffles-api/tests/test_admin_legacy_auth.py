from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import admin as admin_router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(admin_router.router)

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    def _override_get_db():
        yield db

    app.dependency_overrides[admin_router.get_db] = _override_get_db
    app.state.test_db = db
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/admin/prompt/demo_salon", None),
        ("PUT", "/admin/prompt/demo_salon", {"text": "hello"}),
        ("GET", "/admin/settings/demo_salon", None),
        ("PUT", "/admin/settings/demo_salon", {"mute_duration_first_minutes": 30}),
        ("POST", "/admin/heal", None),
    ],
)
def test_guarded_legacy_admin_routes_require_token(client, monkeypatch, method, path, payload):
    monkeypatch.setenv("ALERTS_ADMIN_TOKEN", "secret-token")
    response = client.request(method, path, json=payload)
    assert response.status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/admin/prompt/demo_salon", None),
        ("PUT", "/admin/prompt/demo_salon", {"text": "hello"}),
        ("GET", "/admin/settings/demo_salon", None),
        ("PUT", "/admin/settings/demo_salon", {"mute_duration_first_minutes": 30}),
    ],
)
def test_guarded_legacy_admin_routes_accept_valid_token(client, monkeypatch, method, path, payload):
    monkeypatch.setenv("ALERTS_ADMIN_TOKEN", "secret-token")
    response = client.request(
        method,
        path,
        json=payload,
        headers={"X-Admin-Token": "secret-token"},
    )
    # Fake DB returns no client, so guarded routes continue into handler and return 404.
    assert response.status_code == 404


def test_heal_accepts_valid_token(client, monkeypatch):
    monkeypatch.setenv("ALERTS_ADMIN_TOKEN", "secret-token")
    monkeypatch.setattr(
        admin_router,
        "check_and_heal_conversations",
        lambda _db: {"fixed": 1, "errors": []},
    )
    response = client.post("/admin/heal", headers={"X-Admin-Token": "secret-token"})
    assert response.status_code == 200
    assert response.json() == {"fixed": 1, "errors": []}


def test_admin_outbox_process_requires_token(client, monkeypatch):
    monkeypatch.setenv("ALERTS_ADMIN_TOKEN", "secret-token")
    response = client.post("/admin/outbox/process")
    assert response.status_code == 401


def test_admin_outbox_process_accepts_valid_token(client, monkeypatch):
    monkeypatch.setenv("ALERTS_ADMIN_TOKEN", "secret-token")
    async def _fake_run_default_outbox_process(_db, include_reminders=False):
        assert include_reminders is False
        return {"processed": 0, "results": {"processed": 0, "failed": 0}}

    monkeypatch.setattr(
        admin_router,
        "run_default_outbox_process",
        _fake_run_default_outbox_process,
    )
    response = client.post("/admin/outbox/process", headers={"X-Admin-Token": "secret-token"})
    assert response.status_code == 200
    assert response.json() == {"processed": 0, "results": {"processed": 0, "failed": 0}}


def test_health_and_version_remain_public(client, monkeypatch):
    monkeypatch.setenv("ALERTS_ADMIN_TOKEN", "secret-token")
    health_response = client.get("/admin/health")
    version_response = client.get("/admin/version")

    assert health_response.status_code == 200
    assert version_response.status_code == 200
