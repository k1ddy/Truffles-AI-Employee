from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import ConsoleOnboardingContractPatchRequest, ConsoleReferencePackUpsertRequest
from app.schemas.onboarding_contract import OnboardingContractPayload
from app.services.console_errors import ConsoleAPIError


def _mock_context(*, role: str = "platform_admin", client_id=None, agent_id=None):
    return SimpleNamespace(
        role=role,
        agent=SimpleNamespace(id=agent_id or uuid4(), name="Agent"),
        client=SimpleNamespace(id=client_id or uuid4()),
    )


@pytest.mark.asyncio
async def test_patch_onboarding_contract_payment_requires_platform_admin(monkeypatch):
    context = _mock_context(role="admin")
    db = Mock()
    body = ConsoleOnboardingContractPatchRequest(
        scope="client",
        payment_status="confirmed",
        payload=OnboardingContractPayload.model_validate({"purchased": {}}),
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.patch_onboarding_contract(request=Mock(), body=body, db=db)

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_patch_onboarding_contract_updates_existing_payment_fields(monkeypatch):
    context = _mock_context(role="platform_admin")
    now = datetime.now(timezone.utc)
    record = SimpleNamespace(
        id=uuid4(),
        client_id=context.client.id,
        branch_id=None,
        scope="client",
        status="active",
        schema_version="v1",
        payment_status="pending",
        payment_confirmed_at=None,
        payment_confirmed_by=None,
        payload_json={"purchased": {}},
        created_by=context.agent.id,
        created_at=now,
        updated_at=now,
    )
    db = Mock()
    body = ConsoleOnboardingContractPatchRequest(
        scope="client",
        payment_status="confirmed",
        payload=OnboardingContractPayload.model_validate(
            {
                "domain_slug": "beauty",
                "purchased": {"channels": {"whatsapp": True}},
            }
        ),
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_get_latest_onboarding_contract", lambda *args, **kwargs: record)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    response = await console_router.patch_onboarding_contract(request=Mock(), body=body, db=db)

    assert response.payment_status == "confirmed"
    assert response.payment_confirmed_by == context.agent.id
    assert response.payment_confirmed_at is not None
    assert response.payload.domain_slug == "beauty"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_onboarding_contract_reports_capability_mismatches(monkeypatch):
    client_id = uuid4()
    agent_id = uuid4()
    now = datetime.now(timezone.utc)
    context = _mock_context(role="owner", client_id=client_id, agent_id=agent_id)

    contract_record = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=None,
        scope="client",
        status="active",
        schema_version="v1",
        payment_status="pending",
        payment_confirmed_at=None,
        payment_confirmed_by=None,
        payload_json={"domain_slug": "beauty", "purchased": {"channels": {"whatsapp": False}}},
        created_by=agent_id,
        created_at=now,
        updated_at=now,
    )
    capability_record = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=None,
        scope="client",
        status="active",
        schema_version="v1",
        payload_json={"channels": {"whatsapp": True}, "providers": {}, "features": {}},
        created_by=agent_id,
        created_at=now,
        updated_at=now,
    )
    db = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    def fake_get_contract(_db, *, client_id, scope, branch_id):
        assert client_id == context.client.id
        if scope == "client":
            return contract_record
        return None

    def fake_get_capability(_db, *, client_id, scope, branch_id):
        assert client_id == context.client.id
        if scope == "client":
            return capability_record
        return None

    monkeypatch.setattr(console_router, "_get_latest_onboarding_contract", fake_get_contract)
    monkeypatch.setattr(console_router, "_get_latest_capability", fake_get_capability)

    response = await console_router.get_onboarding_contract(request=Mock(), branch_id=None, db=db)

    assert response.payment_status == "pending"
    assert response.effective.domain_slug == "beauty"
    assert "channels.whatsapp" in response.capability_mismatches


@pytest.mark.asyncio
async def test_upsert_reference_pack_requires_platform_admin(monkeypatch):
    context = _mock_context(role="admin")
    db = Mock()
    body = ConsoleReferencePackUpsertRequest(title="Beauty base")

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda request, db, require_selection=False: context,
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.upsert_reference_pack(
            domain_slug="beauty",
            body=body,
            request=Mock(),
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_get_webhook_secret_generates_and_returns_value(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    context = _mock_context(role="owner", client_id=client_id)
    branch = SimpleNamespace(id=branch_id, client_id=client_id, instance_id="instance-123")
    client = SimpleNamespace(id=client_id, name="demo_salon")
    db = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_resolve_branch_for_onboarding", lambda _context, branch_id=None: branch)
    monkeypatch.setattr(
        console_router,
        "_ensure_client_webhook_secret_from_instance",
        lambda *_args, **_kwargs: ("whs_v1_test", "https://api.truffles.kz/webhook/demo_salon?webhook_secret=whs_v1_test", True),
    )
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    fake_query = Mock()
    fake_query.filter.return_value.first.return_value = client
    db.query.return_value = fake_query

    response = await console_router.get_webhook_secret(request=Mock(), branch_id=branch_id, db=db)

    assert response.client_id == client_id
    assert response.branch_id == branch_id
    assert response.webhook_secret == "whs_v1_test"
    assert response.webhook_url.endswith("webhook_secret=whs_v1_test")
    db.commit.assert_called_once()
