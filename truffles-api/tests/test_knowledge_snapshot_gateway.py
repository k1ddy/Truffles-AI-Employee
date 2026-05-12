from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.schemas.outbox_payload import TenantContext
from app.services.knowledge_snapshot_service import build_knowledge_snapshot
from app.services.pack_compiler_service import compile_pack_payload, inject_compiled_artifacts


@pytest.fixture
def client():
    return TestClient(app)


def _snapshot_request():
    return {
        "tenant_context": {
            "client_id": str(uuid4()),
            "branch_id": str(uuid4()),
        }
    }


def test_snapshot_disabled_returns_404(client, monkeypatch):
    monkeypatch.delenv("KNOWLEDGE_SNAPSHOT_ENABLED", raising=False)
    response = client.post("/knowledge/snapshot", json=_snapshot_request())
    assert response.status_code == 404


def test_snapshot_enabled_calls_builder(client, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_SNAPSHOT_ENABLED", "1")

    db = Mock()

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with patch(
            "app.routers.knowledge_gateway.build_knowledge_snapshot",
            return_value=({"snapshot_id": "s1", "version_id": "v1", "schema_version": "knowledge_snapshot.v1"}, None),
        ):
            response = client.post("/knowledge/snapshot", json=_snapshot_request())
            assert response.status_code == 200
            assert response.json()["snapshot_id"] == "s1"
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_build_knowledge_snapshot_happy_path():
    db = Mock()
    client_id = uuid4()
    branch_id = uuid4()
    branch = SimpleNamespace(
        id=branch_id,
        client_id=client_id,
        slug="branch-1",
        instance_id="demo-instance",
        client=SimpleNamespace(name="demo_salon"),
    )
    query = Mock()
    query.filter.return_value.first.return_value = branch
    db.query.return_value = query

    base_payload = {
        "client_pack": {
            "services_catalog": {"services": []},
            "policy": {
                "hard_law": {},
                "payment_info": {},
                "reschedule": {},
                "cancel": {},
                "medical": {},
                "legal": {},
                "complaint": {},
                "discounts": {},
                "guard_topics": {"refund": ["refund"]},
            },
        }
    }
    compiled = compile_pack_payload(base_payload)
    version = SimpleNamespace(
        id=uuid4(),
        payload_json=inject_compiled_artifacts(base_payload, compiled),
    )

    tenant_context = TenantContext(client_id=client_id, branch_id=branch_id)
    with patch(
        "app.services.knowledge_snapshot_service.get_active_knowledge_version",
        return_value=version,
    ):
        snapshot, error = build_knowledge_snapshot(db, tenant_context=tenant_context)

    assert error is None
    assert snapshot is not None
    assert snapshot["tenant_context"]["client_slug"] == "demo_salon"
    assert snapshot["tenant_context"]["branch_slug"] == "branch-1"
    compiled_pack = snapshot["packs"]["compiled_pack"]
    effective_pack = compiled_pack["effective_pack"]
    assert effective_pack["client_pack"]["services_catalog"]["services"] == []


def test_build_knowledge_snapshot_requires_compiled_pack():
    db = Mock()
    client_id = uuid4()
    branch_id = uuid4()
    branch = SimpleNamespace(
        id=branch_id,
        client_id=client_id,
        slug="branch-1",
        instance_id="demo-instance",
        client=SimpleNamespace(name="demo_salon"),
    )
    query = Mock()
    query.filter.return_value.first.return_value = branch
    db.query.return_value = query

    version = SimpleNamespace(
        id=uuid4(),
        payload_json={"client_pack": {"services_catalog": {"services": []}}},
    )

    tenant_context = TenantContext(client_id=client_id, branch_id=branch_id)
    with patch(
        "app.services.knowledge_snapshot_service.get_active_knowledge_version",
        return_value=version,
    ):
        snapshot, error = build_knowledge_snapshot(db, tenant_context=tenant_context)

    assert snapshot is None
    assert error == "compiled_pack_missing"
