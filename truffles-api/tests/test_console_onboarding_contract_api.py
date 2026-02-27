from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import (
    ConsoleOnboardingAutopilotRequest,
    ConsoleOnboardingContractPatchRequest,
    ConsoleReferencePackUpsertRequest,
)
from app.schemas.onboarding_contract import OnboardingContractPayload
from app.services.console_errors import ConsoleAPIError
from app.services.reference_pack_integrity import (
    REFERENCE_PACK_INTEGRITY_VERSION,
    REFERENCE_PACK_SCHEMA_VERSION,
    build_required_fields_checksum,
)


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
async def test_patch_onboarding_contract_requires_platform_admin(monkeypatch):
    context = _mock_context(role="owner")
    db = Mock()
    body = ConsoleOnboardingContractPatchRequest(
        scope="client",
        payload=OnboardingContractPayload.model_validate({"purchased": {}}),
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.patch_onboarding_contract(request=Mock(), body=body, db=db)

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_get_onboarding_contract_requires_platform_admin(monkeypatch):
    context = _mock_context(role="owner")
    db = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_onboarding_contract(request=Mock(), branch_id=None, db=db)

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
                "provider_binding": {
                    "whatsapp": {
                        "provider": "chatflow",
                        "instance_id": "instance-123",
                        "webhook_status": "configured",
                        "paid_until": "2030-01-01",
                        "owner": "platform-admin",
                        "next_renewal_at": "2030-01-01",
                        "last_rebind_at": "2026-02-01",
                        "rebind_required": False,
                        "alert_state": "warn",
                    }
                },
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
    assert response.payload.provider_binding.whatsapp is not None
    assert response.payload.provider_binding.whatsapp.provider == "chatflow"
    assert response.payload.provider_binding.whatsapp.owner == "platform-admin"
    assert response.payload.provider_binding.whatsapp.next_renewal_at == "2030-01-01"
    assert response.payload.provider_binding.whatsapp.last_rebind_at == "2026-02-01"
    assert response.payload.provider_binding.whatsapp.rebind_required is False
    assert response.payload.provider_binding.whatsapp.alert_state == "warn"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_onboarding_contract_reports_capability_mismatches(monkeypatch):
    client_id = uuid4()
    agent_id = uuid4()
    now = datetime.now(timezone.utc)
    context = _mock_context(role="platform_admin", client_id=client_id, agent_id=agent_id)

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
async def test_upsert_reference_pack_enforces_integrity_metadata(monkeypatch):
    context = _mock_context(role="platform_admin")
    db = Mock()
    body = ConsoleReferencePackUpsertRequest(
        title="Beauty base",
        metadata={"source": "manual"},
    )

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda request, db, require_selection=False: context,
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    def _assign_id(record):
        if getattr(record, "id", None) is None:
            record.id = uuid4()

    db.add.side_effect = _assign_id
    db.query.return_value.filter.return_value.first.return_value = None

    response = await console_router.upsert_reference_pack(
        domain_slug="beauty",
        body=body,
        request=Mock(),
        db=db,
    )

    assert response.schema_version == REFERENCE_PACK_SCHEMA_VERSION
    assert response.metadata["source"] == "manual"
    assert response.metadata["integrity"]["version"] == REFERENCE_PACK_INTEGRITY_VERSION
    assert response.metadata["integrity"]["required_fields_checksum"] == build_required_fields_checksum(
        response.metadata["integrity"]["required_fields"]
    )
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_reference_pack_rejects_unsupported_schema_version(monkeypatch):
    context = _mock_context(role="platform_admin")
    db = Mock()
    body = ConsoleReferencePackUpsertRequest(
        title="Beauty base",
        schema_version="v1",
    )

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

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_list_onboarding_blueprints_requires_platform_admin(monkeypatch):
    context = _mock_context(role="owner")
    db = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db, require_selection=False: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_onboarding_blueprints_api(
            request=Mock(),
            domain_slug=None,
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_list_reference_packs_requires_platform_admin(monkeypatch):
    context = _mock_context(role="owner")
    db = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db, require_selection=False: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_reference_packs(
            request=Mock(),
            domain_slug=None,
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_get_webhook_secret_requires_platform_admin(monkeypatch):
    context = _mock_context(role="owner")
    db = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_webhook_secret(request=Mock(), branch_id=uuid4(), db=db)

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_get_webhook_secret_generates_and_returns_value(monkeypatch):
    client_id = uuid4()
    branch_id = uuid4()
    context = _mock_context(role="platform_admin", client_id=client_id)
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


@pytest.mark.asyncio
async def test_run_onboarding_autopilot_requires_platform_admin(monkeypatch):
    context = _mock_context(role="owner")
    db = Mock()
    body = ConsoleOnboardingAutopilotRequest(
        phone="+77011111111",
        instance_id="instance-123",
    )

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda request, db, require_selection=False: context,
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.run_onboarding_autopilot(
            request=Mock(),
            body=body,
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"
