from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.capabilities import CapabilitiesPayload
from app.schemas.console import ConsoleDomainCatalogUpsertRequest
from app.services.console_errors import ConsoleAPIError


def _mock_context(*, role: str = "platform_admin", client_id=None, agent_id=None):
    return SimpleNamespace(
        role=role,
        agent=SimpleNamespace(id=agent_id or uuid4(), name="Agent"),
        client=SimpleNamespace(id=client_id or uuid4()),
    )


@pytest.mark.asyncio
async def test_list_domain_catalog_requires_platform_admin(monkeypatch):
    context = _mock_context(role="owner")
    db = Mock()

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda request, db, require_selection=False: context,
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.list_domain_catalog(
            request=Mock(),
            status=None,
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_upsert_domain_catalog_persists_template(monkeypatch):
    context = _mock_context(role="platform_admin")
    db = Mock()
    body = ConsoleDomainCatalogUpsertRequest(
        title="Beauty",
        summary="Beauty services",
        capability_template=CapabilitiesPayload.model_validate(
            {"features": {"booking_mode": "collect_preferences"}, "channels": {"whatsapp": True}}
        ),
    )

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda request, db, require_selection=False: context,
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        console_router,
        "_get_domain_capability_template_record",
        lambda *args, **kwargs: None,
    )

    def _assign_id(record):
        if getattr(record, "id", None) is None:
            record.id = uuid4()

    db.add.side_effect = _assign_id

    response = await console_router.upsert_domain_catalog(
        domain_slug="beauty",
        body=body,
        request=Mock(),
        db=db,
    )

    assert response.domain_slug == "beauty"
    assert response.title == "Beauty"
    assert response.capability_template.domain_slug == "beauty"
    assert response.capability_template.features.booking_mode == "collect_preferences"
    assert response.capability_template.channels.whatsapp is True
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_domain_catalog_rejects_template_domain_mismatch(monkeypatch):
    context = _mock_context(role="platform_admin")
    db = Mock()
    body = ConsoleDomainCatalogUpsertRequest(
        title="Beauty",
        capability_template=CapabilitiesPayload.model_validate({"domain_slug": "clinic"}),
    )

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda request, db, require_selection=False: context,
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.upsert_domain_catalog(
            domain_slug="beauty",
            body=body,
            request=Mock(),
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_get_capabilities_applies_domain_layer_before_client_branch(monkeypatch):
    now = datetime.now(timezone.utc)
    client_id = uuid4()
    branch_id = uuid4()
    context = _mock_context(role="owner", client_id=client_id)
    db = Mock()

    branch = SimpleNamespace(id=branch_id, client_id=client_id)
    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = branch
    db.query.return_value = branch_query

    client_record = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=None,
        scope="client",
        status="active",
        schema_version="v1",
        payload_json={
            "domain_slug": "beauty",
            "channels": {"telegram": True},
            "features": {"analytics": True},
        },
        created_by=context.agent.id,
        created_at=now,
        updated_at=now,
    )
    branch_record = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        scope="branch",
        status="active",
        schema_version="v1",
        payload_json={
            "channels": {"whatsapp": False},
        },
        created_by=context.agent.id,
        created_at=now,
        updated_at=now,
    )
    domain_record = SimpleNamespace(
        id=uuid4(),
        domain_slug="beauty",
        title="Beauty",
        summary="",
        schema_version="v1",
        status="active",
        capability_template_json={
            "domain_slug": "beauty",
            "channels": {"whatsapp": True},
            "features": {"booking_mode": "collect_preferences"},
        },
        metadata_json={},
        created_by=context.agent.id,
        created_at=now,
        updated_at=now,
    )

    def _fake_get_latest_capability(_db, *, client_id, scope, branch_id):
        if scope == "client":
            return client_record
        if scope == "branch":
            return branch_record
        return None

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda request, db: context,
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_get_latest_capability", _fake_get_latest_capability)
    monkeypatch.setattr(
        console_router,
        "_get_domain_capability_template_record",
        lambda *_args, **_kwargs: domain_record,
    )

    response = await console_router.get_capabilities(
        request=Mock(),
        branch_id=branch_id,
        db=db,
    )

    assert response.effective.domain_slug == "beauty"
    assert response.effective.features.booking_mode == "collect_preferences"
    assert response.effective.features.analytics is True
    assert response.effective.channels.telegram is True
    assert response.effective.channels.whatsapp is False
