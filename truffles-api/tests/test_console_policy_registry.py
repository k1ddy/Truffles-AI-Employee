from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.capabilities import CapabilityPolicyOverrides
from app.schemas.console import (
    ConsolePolicyRegistryPublishRequest,
    ConsolePolicyRegistryRollbackRequest,
)
from app.services.console_errors import ConsoleAPIError


def _mock_context(*, role: str = "platform_admin", client_id=None, agent_id=None):
    return SimpleNamespace(
        role=role,
        agent=SimpleNamespace(id=agent_id or uuid4(), name="Agent"),
        client=SimpleNamespace(id=client_id or uuid4()),
    )


def _policy_record(*, client_id, agent_id, version_number: int = 1):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=None,
        scope="client",
        status="published",
        schema_version="v1",
        version_number=version_number,
        payload_json={"payment_info": {"response": "Оплата по счету"}},
        reason="policy update",
        source_version_id=None,
        created_by=agent_id,
        created_at=now,
        updated_at=now,
        published_by=agent_id,
        published_at=now,
    )


@pytest.mark.asyncio
async def test_get_policy_registry_requires_platform_admin(monkeypatch):
    context = _mock_context(role="owner")
    db = Mock()

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.get_policy_registry(
            request=Mock(),
            scope="client",
            branch_id=None,
            limit=20,
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_publish_policy_registry_requires_branch_id_for_branch_scope(monkeypatch):
    context = _mock_context(role="platform_admin")
    db = Mock()
    body = ConsolePolicyRegistryPublishRequest(
        scope="branch",
        reason="sync",
        payload=CapabilityPolicyOverrides.model_validate(
            {"payment_info": {"response": "Оплата только по счету"}}
        ),
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.publish_policy_registry(
            request=Mock(),
            body=body,
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_get_policy_registry_returns_active_and_history(monkeypatch):
    client_id = uuid4()
    agent_id = uuid4()
    context = _mock_context(role="platform_admin", client_id=client_id, agent_id=agent_id)
    db = Mock()
    active = _policy_record(client_id=client_id, agent_id=agent_id, version_number=3)
    history = [
        active,
        _policy_record(client_id=client_id, agent_id=agent_id, version_number=2),
    ]

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "get_latest_policy_version", lambda *args, **kwargs: active)
    monkeypatch.setattr(console_router, "list_policy_history", lambda *args, **kwargs: history)

    response = await console_router.get_policy_registry(
        request=Mock(),
        scope="client",
        branch_id=None,
        limit=20,
        db=db,
    )

    assert response.client_id == client_id
    assert response.active is not None
    assert response.active.version_number == 3
    assert len(response.history) == 2


@pytest.mark.asyncio
async def test_publish_policy_registry_platform_admin_success(monkeypatch):
    client_id = uuid4()
    agent_id = uuid4()
    context = _mock_context(role="platform_admin", client_id=client_id, agent_id=agent_id)
    db = Mock()
    record = _policy_record(client_id=client_id, agent_id=agent_id, version_number=5)
    body = ConsolePolicyRegistryPublishRequest(
        scope="client",
        reason="update policy",
        payload=CapabilityPolicyOverrides.model_validate(
            {"discounts": {"response": "Скидки по акциям недели"}}
        ),
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "publish_policy_version", lambda *args, **kwargs: record)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    response = await console_router.publish_policy_registry(
        request=Mock(),
        body=body,
        db=db,
    )

    assert response.success is True
    assert response.record.version_number == 5
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_rollback_policy_registry_returns_not_found(monkeypatch):
    client_id = uuid4()
    context = _mock_context(role="platform_admin", client_id=client_id)
    db = Mock()
    body = ConsolePolicyRegistryRollbackRequest(
        scope="client",
        target_version_id=uuid4(),
        reason="rollback to stable",
    )

    monkeypatch.setattr(console_router, "get_console_context", lambda request, db: context)
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        console_router,
        "rollback_policy_version",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("Policy version not found")),
    )

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.rollback_policy_registry(
            request=Mock(),
            body=body,
            db=db,
        )

    assert exc_info.value.code == "NOT_FOUND"
