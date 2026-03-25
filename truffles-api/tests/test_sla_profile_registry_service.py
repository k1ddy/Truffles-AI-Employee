from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.schemas.sla_profile import SlaProfilePayload
from app.services import sla_profile_registry_service


def test_publish_profile_version_archives_active_and_creates_new(monkeypatch):
    actor_id = uuid4()
    company_id = uuid4()
    client_id = uuid4()
    active = SimpleNamespace(status="published", updated_at=None)
    db = Mock()

    monkeypatch.setattr(
        sla_profile_registry_service,
        "get_latest_profile_version",
        lambda *args, **kwargs: active,
    )
    monkeypatch.setattr(
        sla_profile_registry_service,
        "_next_version_number",
        lambda *args, **kwargs: 3,
    )

    record = sla_profile_registry_service.publish_profile_version(
        db,
        scope="client",
        company_id=company_id,
        client_id=client_id,
        payload=SlaProfilePayload.model_validate(
            {
                "profile_name": "client-default",
                "thresholds": {"first_response_minutes": 4},
                "actions": {"warning": "notify_manager", "breach": "escalate", "severe_breach": "collect_only"},
            }
        ),
        actor_id=actor_id,
        reason="rotate client sla profile",
    )

    assert active.status == "archived"
    assert record.scope == "client"
    assert record.company_id == company_id
    assert record.client_id == client_id
    assert record.status == "published"
    assert record.version_number == 3
    assert record.reason == "rotate client sla profile"
    db.add.assert_called_once()
    db.flush.assert_called_once()


def test_resolve_effective_profile_version_prefers_branch_scope(monkeypatch):
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

    monkeypatch.setattr(sla_profile_registry_service, "get_latest_profile_version", _fake_latest)

    resolved = sla_profile_registry_service.resolve_effective_profile_version(
        Mock(),
        company_id=company_id,
        domain_key="beauty",
        client_id=client_id,
        branch_id=branch_id,
    )
    assert resolved is branch_record


def test_resolve_effective_profile_payload_merges_hierarchy(monkeypatch):
    global_record = SimpleNamespace(payload_json={"thresholds": {"first_response_minutes": 8}})
    domain_record = SimpleNamespace(payload_json={"thresholds": {"fallback_rate_max": 0.35}})
    client_record = SimpleNamespace(
        payload_json={
            "profile_name": "client-profile",
            "thresholds": {"first_response_minutes": 3},
            "actions": {"warning": "notify_manager", "breach": "escalate", "severe_breach": "collect_only"},
        }
    )
    branch_record = SimpleNamespace(payload_json={"thresholds": {"handoff_ack_minutes": 7}})

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

    monkeypatch.setattr(sla_profile_registry_service, "get_latest_profile_version", _fake_latest)

    resolved = sla_profile_registry_service.resolve_effective_profile_payload(
        Mock(),
        company_id=uuid4(),
        domain_key="beauty",
        client_id=uuid4(),
        branch_id=uuid4(),
    )

    assert resolved is not None
    assert resolved.profile_name == "client-profile"
    assert resolved.thresholds.first_response_minutes == 3
    assert resolved.thresholds.handoff_ack_minutes == 7
    assert resolved.thresholds.fallback_rate_max == 0.35


def test_resolve_effective_profile_payload_fail_closed_on_invalid_merged_payload(monkeypatch):
    invalid_record = SimpleNamespace(
        payload_json={
            "profile_name": "bad",
            "thresholds": {"first_response_minutes": 0},
            "actions": {"warning": "notify_manager", "breach": "escalate", "severe_breach": "collect_only"},
        }
    )

    def _fake_latest(_db, *, scope, **kwargs):
        if scope == "global":
            return invalid_record
        return None

    monkeypatch.setattr(sla_profile_registry_service, "get_latest_profile_version", _fake_latest)

    resolved = sla_profile_registry_service.resolve_effective_profile_payload(
        Mock(),
        company_id=None,
        domain_key=None,
        client_id=None,
        branch_id=None,
    )

    assert resolved is None
