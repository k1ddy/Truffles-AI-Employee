from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.schemas.capabilities import CapabilityPolicyOverrides
from app.services import policy_registry_service


def test_publish_policy_version_archives_active_and_creates_new(monkeypatch):
    client_id = uuid4()
    actor_id = uuid4()
    active = SimpleNamespace(status="published", updated_at=None)
    db = Mock()

    monkeypatch.setattr(
        policy_registry_service,
        "get_latest_policy_version",
        lambda *args, **kwargs: active,
    )
    monkeypatch.setattr(
        policy_registry_service,
        "_next_version_number",
        lambda *args, **kwargs: 4,
    )

    record = policy_registry_service.publish_policy_version(
        db,
        client_id=client_id,
        scope="client",
        branch_id=None,
        payload=CapabilityPolicyOverrides.model_validate(
            {"payment_info": {"response": "Оплата по счету"}}
        ),
        actor_id=actor_id,
        reason="rotate policy",
    )

    assert active.status == "archived"
    assert record.client_id == client_id
    assert record.scope == "client"
    assert record.status == "published"
    assert record.version_number == 4
    assert record.reason == "rotate policy"
    db.add.assert_called_once()
    db.flush.assert_called_once()


def test_resolve_effective_policy_version_prefers_branch_scope(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    branch_record = SimpleNamespace(id=uuid4())
    client_record = SimpleNamespace(id=uuid4())

    def _fake_latest(_db, *, client_id, scope, branch_id, status):
        assert status == "published"
        if scope == "branch":
            return branch_record
        return client_record

    monkeypatch.setattr(policy_registry_service, "get_latest_policy_version", _fake_latest)

    resolved = policy_registry_service.resolve_effective_policy_version(
        Mock(),
        client_id=client_id,
        branch_id=branch_id,
    )

    assert resolved is branch_record


def test_resolve_effective_policy_overrides_fail_closed_for_invalid_payload(monkeypatch):
    bad_record = SimpleNamespace(payload_json={"hard_law": {"response": "forbidden"}})

    monkeypatch.setattr(
        policy_registry_service,
        "resolve_effective_policy_version",
        lambda *args, **kwargs: bad_record,
    )

    resolved = policy_registry_service.resolve_effective_policy_overrides(
        Mock(),
        client_id=uuid4(),
        branch_id=None,
    )

    assert resolved is None
