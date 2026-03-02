from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.schemas.sla_profile import SlaProfilePayload
from app.services import sla_runtime_service


def _conversation(*, minutes_ago: int = 20):
    return SimpleNamespace(
        client_id=uuid4(),
        branch_id=uuid4(),
        escalated_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )


def test_resolve_pending_sla_violation_returns_none_without_profile(monkeypatch):
    conv = _conversation(minutes_ago=30)
    db = Mock()

    monkeypatch.setattr(
        sla_runtime_service,
        "_resolve_scope_inputs",
        lambda *_args, **_kwargs: (None, None),
    )
    monkeypatch.setattr(
        sla_runtime_service,
        "resolve_effective_profile_payload",
        lambda *_args, **_kwargs: None,
    )

    decision = sla_runtime_service.resolve_pending_sla_violation(
        db,
        conversation=conv,
        now=datetime.now(timezone.utc),
    )

    assert decision is None


def test_resolve_pending_sla_violation_uses_profile_actions(monkeypatch):
    conv = _conversation(minutes_ago=25)
    db = Mock()
    profile_id = uuid4()

    payload = SlaProfilePayload.model_validate(
        {
            "profile_name": "branch-sla",
            "thresholds": {
                "first_response_minutes": 3,
                "handoff_ack_minutes": 10,
                "resolution_minutes": 20,
                "fallback_rate_max": 0.2,
            },
            "actions": {
                "warning": "notify_manager",
                "breach": "escalate",
                "severe_breach": "collect_only",
            },
        }
    )

    monkeypatch.setattr(
        sla_runtime_service,
        "_resolve_scope_inputs",
        lambda *_args, **_kwargs: (uuid4(), "salon"),
    )
    monkeypatch.setattr(
        sla_runtime_service,
        "resolve_effective_profile_payload",
        lambda *_args, **_kwargs: payload,
    )
    monkeypatch.setattr(
        sla_runtime_service,
        "resolve_effective_profile_version",
        lambda *_args, **_kwargs: SimpleNamespace(id=profile_id, version_number=4, scope="branch"),
    )

    decision = sla_runtime_service.resolve_pending_sla_violation(
        db,
        conversation=conv,
        now=datetime.now(timezone.utc),
    )

    assert decision is not None
    assert decision.severity == "severe_breach"
    assert decision.action == "collect_only"
    assert decision.threshold_minutes == 20
    assert decision.profile_id == profile_id
    assert decision.profile_version == 4
    assert decision.profile_scope == "branch"


def test_resolve_first_response_threshold_prefers_profile(monkeypatch):
    conv = _conversation(minutes_ago=5)
    db = Mock()
    payload = SlaProfilePayload.model_validate(
        {
            "thresholds": {
                "first_response_minutes": 7,
                "handoff_ack_minutes": 15,
                "resolution_minutes": 120,
                "fallback_rate_max": 0.2,
            },
            "actions": {
                "warning": "notify_manager",
                "breach": "escalate",
                "severe_breach": "collect_only",
            },
        }
    )

    monkeypatch.setattr(
        sla_runtime_service,
        "_resolve_scope_inputs",
        lambda *_args, **_kwargs: (None, "salon"),
    )
    monkeypatch.setattr(
        sla_runtime_service,
        "resolve_effective_profile_payload",
        lambda *_args, **_kwargs: payload,
    )

    threshold = sla_runtime_service.resolve_first_response_threshold_minutes(
        db,
        conversation=conv,
        default_minutes=3,
    )

    assert threshold == 7


def test_collect_only_runtime_context_helpers():
    now = datetime.now(timezone.utc)
    decision = sla_runtime_service.SlaPendingViolationDecision(
        severity="severe_breach",
        action="collect_only",
        reason_code="sla_severe_breach_collect_only",
        elapsed_minutes=40,
        threshold_minutes=20,
        profile_id=uuid4(),
        profile_version=2,
        profile_scope="client",
        domain_key="salon",
    )
    context = {
        sla_runtime_service.SLA_RUNTIME_CONTEXT_KEY: sla_runtime_service.build_collect_only_runtime_context(
            decision=decision,
            now=now,
        )
    }

    assert sla_runtime_service.is_collect_only_runtime_active(context, now=now)


def test_resolve_scope_inputs_handles_client_without_company_id(monkeypatch):
    conv = _conversation(minutes_ago=5)
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id=conv.client_id)

    monkeypatch.setattr(
        sla_runtime_service,
        "build_runtime_capabilities",
        lambda *_args, **_kwargs: SimpleNamespace(payload=SimpleNamespace(domain_slug="generic")),
    )

    company_id, domain_key = sla_runtime_service._resolve_scope_inputs(db, conversation=conv)

    assert company_id is None
    assert domain_key == "generic"
