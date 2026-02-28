from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import (
    ConsoleSlaProfileRegistryPublishRequest,
    ConsoleSlaProfileRegistryRollbackRequest,
)
from app.schemas.sla_profile import SlaProfilePayload
from app.services.console_errors import ConsoleAPIError


def _mock_context(*, role: str = "platform_admin", client_id=None, company_id=None, agent_id=None):
    return SimpleNamespace(
        role=role,
        agent=SimpleNamespace(id=agent_id or uuid4(), name="Agent"),
        client=SimpleNamespace(
            id=client_id or uuid4(),
            company_id=company_id or uuid4(),
        ),
    )


def _sla_record(*, scope: str = "client", company_id=None, domain_key=None, client_id=None, branch_id=None, agent_id=None, version_number: int = 1):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        scope=scope,
        company_id=company_id,
        domain_key=domain_key,
        client_id=client_id,
        branch_id=branch_id,
        status="published",
        schema_version="v1",
        version_number=version_number,
        payload_json=SlaProfilePayload().model_dump(),
        reason="sla update",
        source_version_id=None,
        created_by=agent_id or uuid4(),
        created_at=now,
        updated_at=now,
        published_by=agent_id or uuid4(),
        published_at=now,
    )


@pytest.mark.asyncio
async def test_get_sla_profile_registry_requires_platform_admin(monkeypatch):
    context = _mock_context(role="owner")
    db = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_sla_profile_registry(
            request=Mock(),
            scope="global",
            domain_key=None,
            branch_id=None,
            limit=20,
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_publish_sla_profile_registry_requires_domain_key_for_domain_scope(monkeypatch):
    context = _mock_context(role="platform_admin")
    db = Mock()
    body = ConsoleSlaProfileRegistryPublishRequest(
        scope="domain",
        reason="domain rollout",
        payload=SlaProfilePayload(),
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.publish_sla_profile_registry(
            request=Mock(),
            body=body,
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_get_sla_profile_registry_returns_active_and_history(monkeypatch):
    company_id = uuid4()
    domain_key = "beauty"
    db = Mock()
    context = _mock_context(role="platform_admin", company_id=company_id)
    active = _sla_record(scope="domain", domain_key=domain_key, version_number=3)
    history = [
        active,
        _sla_record(scope="domain", domain_key=domain_key, version_number=2),
    ]

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "get_latest_profile_version", lambda *args, **kwargs: active)
    monkeypatch.setattr(console_router, "list_profile_history", lambda *args, **kwargs: history)

    response = await console_router.get_sla_profile_registry(
        request=Mock(),
        scope="domain",
        domain_key=domain_key,
        branch_id=None,
        limit=20,
        db=db,
    )

    assert response.scope == "domain"
    assert response.domain_key == domain_key
    assert response.active is not None
    assert response.active.version_number == 3
    assert len(response.history) == 2


@pytest.mark.asyncio
async def test_rollback_sla_profile_registry_returns_not_found(monkeypatch):
    db = Mock()
    context = _mock_context(role="platform_admin")
    body = ConsoleSlaProfileRegistryRollbackRequest(
        scope="global",
        target_version_id=uuid4(),
        reason="rollback",
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        console_router,
        "rollback_profile_version",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("SLA profile version not found")),
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.rollback_sla_profile_registry(
            request=Mock(),
            body=body,
            db=db,
        )

    assert exc_info.value.code == "NOT_FOUND"
