from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.schemas.compliance_policy import CompliancePolicyPayload
from app.services import compliance_policy_registry_service


def test_publish_compliance_policy_version_archives_active_and_creates_new(monkeypatch):
    actor_id = uuid4()
    company_id = uuid4()
    client_id = uuid4()
    active = SimpleNamespace(status="published", updated_at=None)
    db = Mock()

    monkeypatch.setattr(
        compliance_policy_registry_service,
        "get_latest_compliance_policy_version",
        lambda *args, **kwargs: active,
    )
    monkeypatch.setattr(
        compliance_policy_registry_service,
        "_next_version_number",
        lambda *args, **kwargs: 3,
    )

    record = compliance_policy_registry_service.publish_compliance_policy_version(
        db,
        scope="client",
        data_class="learned_responses",
        company_id=company_id,
        client_id=client_id,
        payload=CompliancePolicyPayload.model_validate(
            {
                "policy_name": "learning-default",
                "legal_basis": "contract",
                "retention_days": 180,
                "export_mode": "on_demand",
                "destruction_mode": "anonymize",
            }
        ),
        actor_id=actor_id,
        reason="rotate compliance policy",
    )

    assert active.status == "archived"
    assert record.scope == "client"
    assert record.data_class == "learned_responses"
    assert record.company_id == company_id
    assert record.client_id == client_id
    assert record.status == "published"
    assert record.version_number == 3
    assert record.reason == "rotate compliance policy"
    db.add.assert_called_once()
    db.flush.assert_called_once()


def test_publish_compliance_policy_version_rejects_invalid_data_class():
    with pytest.raises(ValueError, match="data_class"):
        compliance_policy_registry_service.publish_compliance_policy_version(
            Mock(),
            scope="global",
            data_class="1bad",
            payload=CompliancePolicyPayload(),
            actor_id=uuid4(),
            reason="invalid",
        )


def test_resolve_effective_compliance_policy_version_prefers_branch_scope(monkeypatch):
    company_id = uuid4()
    client_id = uuid4()
    branch_id = uuid4()
    branch_record = SimpleNamespace(id=uuid4(), scope="branch")
    client_record = SimpleNamespace(id=uuid4(), scope="client")

    def _fake_latest(_db, *, scope, **kwargs):
        if scope == "branch":
            return branch_record
        if scope == "client":
            return client_record
        return None

    monkeypatch.setattr(
        compliance_policy_registry_service,
        "get_latest_compliance_policy_version",
        _fake_latest,
    )

    resolved = compliance_policy_registry_service.resolve_effective_compliance_policy_version(
        Mock(),
        data_class="messages",
        company_id=company_id,
        domain_key="beauty",
        client_id=client_id,
        branch_id=branch_id,
    )
    assert resolved is branch_record


def test_resolve_effective_compliance_policy_payload_merges_hierarchy(monkeypatch):
    global_record = SimpleNamespace(payload_json={"retention_days": 365})
    domain_record = SimpleNamespace(payload_json={"export_mode": "scheduled"})
    client_record = SimpleNamespace(
        payload_json={
            "policy_name": "client-policy",
            "legal_basis": "contract",
            "retention_days": 120,
            "destruction_mode": "anonymize",
        }
    )
    branch_record = SimpleNamespace(payload_json={"notes": "branch override"})

    def _fake_latest(_db, *, scope, **kwargs):
        if scope == "global":
            return global_record
        if scope == "domain":
            return domain_record
        if scope == "client":
            return client_record
        if scope == "branch":
            return branch_record
        return None

    monkeypatch.setattr(
        compliance_policy_registry_service,
        "get_latest_compliance_policy_version",
        _fake_latest,
    )

    resolved = compliance_policy_registry_service.resolve_effective_compliance_policy_payload(
        Mock(),
        data_class="messages",
        company_id=uuid4(),
        domain_key="beauty",
        client_id=uuid4(),
        branch_id=uuid4(),
    )

    assert resolved is not None
    assert resolved.policy_name == "client-policy"
    assert resolved.retention_days == 120
    assert resolved.export_mode == "scheduled"
    assert resolved.notes == "branch override"


def test_resolve_effective_compliance_policy_payload_fail_closed_on_invalid_merged_payload(monkeypatch):
    invalid_record = SimpleNamespace(payload_json={"retention_days": 0})

    def _fake_latest(_db, *, scope, **kwargs):
        if scope == "global":
            return invalid_record
        return None

    monkeypatch.setattr(
        compliance_policy_registry_service,
        "get_latest_compliance_policy_version",
        _fake_latest,
    )

    resolved = compliance_policy_registry_service.resolve_effective_compliance_policy_payload(
        Mock(),
        data_class="messages",
        company_id=None,
        domain_key=None,
        client_id=None,
        branch_id=None,
    )

    assert resolved is None
