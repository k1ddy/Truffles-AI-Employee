from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.routers import console as console_router
from app.schemas.console import (
    ConsoleBranchUpdateRequest,
    ConsoleClientCreateRequest,
    ConsoleClientLifecycleActionRequest,
    ConsoleClientUpdateRequest,
    ConsoleCompanyUpdateRequest,
)
from app.services.console_errors import ConsoleAPIError


def _mock_context(*, role: str = "platform_admin", accessible_clients=None, client_id=None):
    selected_client_id = client_id or uuid4()
    clients = accessible_clients or [SimpleNamespace(id=selected_client_id, company_id=uuid4())]
    agent = SimpleNamespace(id=uuid4(), name="Agent")
    return SimpleNamespace(
        agent=agent,
        role=role,
        client=SimpleNamespace(id=selected_client_id, company_id=clients[0].company_id),
        accessible_clients=clients,
    )


@pytest.mark.asyncio
async def test_update_company_updates_fields(monkeypatch):
    company_id = uuid4()
    company = SimpleNamespace(id=company_id, name="Old", billing_info={"plan": "A"})
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = company

    monkeypatch.setattr(console_router, "get_console_context", lambda *args, **kwargs: _mock_context())
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    response = await console_router.update_company(
        company_id,
        request=Mock(),
        body=ConsoleCompanyUpdateRequest(name="New", billing_info={"plan": "B"}),
        db=db,
    )

    assert response.id == company_id
    assert response.name == "New"
    assert response.billing_info == {"plan": "B"}
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_client_updates_fields(monkeypatch):
    client_id = uuid4()
    company_id = uuid4()
    client = SimpleNamespace(id=client_id, name="old-slug", status="active", company_id=None)
    company = SimpleNamespace(id=company_id, name="Company")

    db = Mock()
    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    existing_query = Mock()
    existing_query.filter.return_value.first.return_value = None
    company_query = Mock()
    company_query.filter.return_value.first.return_value = company
    branch_exists_query = Mock()
    branch_exists_query.filter.return_value.first.return_value = None
    db.query.side_effect = [client_query, existing_query, company_query, branch_exists_query]

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=uuid4())],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    response = await console_router.update_client(
        client_id,
        request=Mock(),
        body=ConsoleClientUpdateRequest(slug="new-slug", company_id=company_id),
        db=db,
    )

    assert response.id == client_id
    assert response.slug == "new-slug"
    assert response.status == "active"
    assert response.company_id == company_id
    assert response.company_name == "Company"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_client_blocks_company_reassignment_after_branch_created(monkeypatch):
    client_id = uuid4()
    old_company_id = uuid4()
    next_company_id = uuid4()
    client = SimpleNamespace(id=client_id, name="old-slug", status="active", company_id=old_company_id)
    company = SimpleNamespace(id=next_company_id, name="Company")
    existing_branch = SimpleNamespace(id=uuid4())

    db = Mock()
    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    company_query = Mock()
    company_query.filter.return_value.first.return_value = company
    branch_exists_query = Mock()
    branch_exists_query.filter.return_value.first.return_value = existing_branch
    db.query.side_effect = [client_query, company_query, branch_exists_query]

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=old_company_id)],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.update_client(
            client_id,
            request=Mock(),
            body=ConsoleClientUpdateRequest(company_id=next_company_id),
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"
    assert "immutable" in exc_info.value.message


@pytest.mark.asyncio
async def test_update_client_rejects_duplicate_slug(monkeypatch):
    client_id = uuid4()
    client = SimpleNamespace(id=client_id, name="old-slug", status="active", company_id=None)
    existing = SimpleNamespace(id=uuid4(), name="dup")

    db = Mock()
    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    existing_query = Mock()
    existing_query.filter.return_value.first.return_value = existing
    db.query.side_effect = [client_query, existing_query]

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=uuid4())],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.update_client(
            client_id,
            request=Mock(),
            body=ConsoleClientUpdateRequest(slug="dup"),
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_update_client_rejects_status_mutation(monkeypatch):
    client_id = uuid4()
    client = SimpleNamespace(id=client_id, name="old-slug", status="active", company_id=None)
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = client

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=uuid4())],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.update_client(
            client_id,
            request=Mock(),
            body=ConsoleClientUpdateRequest(status="deleted"),
            db=db,
        )

    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_archive_client_blocks_on_active_dependencies(monkeypatch):
    client_id = uuid4()
    client = SimpleNamespace(
        id=client_id,
        name="demo",
        status="active",
        company_id=None,
        deleted_at=None,
        updated_at=None,
    )
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = client

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=uuid4())],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        console_router,
        "_collect_client_archive_blockers",
        lambda _db, _client_id: {
            "active_agent_ids": [str(uuid4())],
            "active_membership_ids": [str(uuid4())],
            "active_branch_ids": [],
        },
    )
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.archive_client(
            client_id,
            request=Mock(),
            body=ConsoleClientLifecycleActionRequest(reason="cleanup"),
            db=db,
        )

    assert exc_info.value.code == "CLIENT_ARCHIVE_BLOCKED"
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_archive_client_sets_deleted_status(monkeypatch):
    client_id = uuid4()
    company_id = uuid4()
    client = SimpleNamespace(
        id=client_id,
        name="demo",
        status="active",
        company_id=company_id,
        deleted_at=None,
        updated_at=None,
    )
    company = SimpleNamespace(id=company_id, name="Company")
    db = Mock()

    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    company_query = Mock()
    company_query.filter.return_value.first.return_value = company
    db.query.side_effect = [client_query, company_query]

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=company_id)],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        console_router,
        "_collect_client_archive_blockers",
        lambda _db, _client_id: {
            "active_agent_ids": [],
            "active_membership_ids": [],
            "active_branch_ids": [],
        },
    )
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    response = await console_router.archive_client(
        client_id,
        request=Mock(),
        body=ConsoleClientLifecycleActionRequest(reason="cleanup"),
        db=db,
    )

    assert response.id == client_id
    assert response.status == "deleted"
    assert client.deleted_at is not None
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_restore_client_sets_active_status(monkeypatch):
    client_id = uuid4()
    company_id = uuid4()
    client = SimpleNamespace(
        id=client_id,
        name="demo",
        status="deleted",
        company_id=company_id,
        deleted_at=datetime.now(timezone.utc),
        updated_at=None,
    )
    company = SimpleNamespace(id=company_id, name="Company")
    db = Mock()
    client_query = Mock()
    client_query.filter.return_value.first.return_value = client
    company_query = Mock()
    company_query.filter.return_value.first.return_value = company
    db.query.side_effect = [client_query, company_query]

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="platform_admin",
            accessible_clients=[SimpleNamespace(id=client_id, company_id=company_id)],
            client_id=client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)

    response = await console_router.restore_client(
        client_id,
        request=Mock(),
        body=ConsoleClientLifecycleActionRequest(reason="restore"),
        db=db,
    )

    assert response.id == client_id
    assert response.status == "active"
    assert client.deleted_at is None
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_company_rejects_cross_tenant_company_for_owner(monkeypatch):
    company_id = uuid4()
    company = SimpleNamespace(id=company_id, name="Other Company", billing_info={})
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = company

    owner_client = SimpleNamespace(id=uuid4(), company_id=uuid4())
    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="owner",
            accessible_clients=[owner_client],
            client_id=owner_client.id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.update_company(
            company_id,
            request=Mock(),
            body=ConsoleCompanyUpdateRequest(name="Updated", billing_info={}),
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_create_client_rejects_cross_tenant_company_for_owner(monkeypatch):
    allowed_client = SimpleNamespace(id=uuid4(), company_id=uuid4())
    foreign_company = SimpleNamespace(id=uuid4(), name="Foreign")
    db = Mock()

    existing_query = Mock()
    existing_query.filter.return_value.first.return_value = None
    company_query = Mock()
    company_query.filter.return_value.first.return_value = foreign_company
    db.query.side_effect = [existing_query, company_query]

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="owner",
            accessible_clients=[allowed_client],
            client_id=allowed_client.id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.create_client(
            request=Mock(),
            body=ConsoleClientCreateRequest(
                slug="new-client",
                company_id=foreign_company.id,
                status="active",
            ),
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_update_client_rejects_cross_tenant_client_for_owner(monkeypatch):
    foreign_client_id = uuid4()
    foreign_client = SimpleNamespace(
        id=foreign_client_id,
        name="foreign",
        status="active",
        company_id=uuid4(),
    )
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = foreign_client

    allowed_client = SimpleNamespace(id=uuid4(), company_id=uuid4())
    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="owner",
            accessible_clients=[allowed_client],
            client_id=allowed_client.id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.update_client(
            foreign_client_id,
            request=Mock(),
            body=ConsoleClientUpdateRequest(slug="updated"),
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_archive_client_rejects_cross_tenant_client_for_owner(monkeypatch):
    foreign_client_id = uuid4()
    foreign_client = SimpleNamespace(
        id=foreign_client_id,
        name="foreign",
        status="active",
        company_id=uuid4(),
    )
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = foreign_client

    allowed_client = SimpleNamespace(id=uuid4(), company_id=uuid4())
    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="owner",
            accessible_clients=[allowed_client],
            client_id=allowed_client.id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.archive_client(
            foreign_client_id,
            request=Mock(),
            body=ConsoleClientLifecycleActionRequest(reason="cleanup"),
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_update_branch_rejects_cross_tenant_client_for_owner(monkeypatch):
    foreign_branch_id = uuid4()
    foreign_branch = SimpleNamespace(
        id=foreign_branch_id,
        client_id=uuid4(),
    )
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = foreign_branch

    allowed_client = SimpleNamespace(id=uuid4(), company_id=uuid4())
    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="owner",
            accessible_clients=[allowed_client],
            client_id=allowed_client.id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.update_branch(
            foreign_branch_id,
            request=Mock(),
            body=ConsoleBranchUpdateRequest(),
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


def test_normalize_branch_patch_payload_rejects_non_string_instance_id():
    branch = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        is_active=False,
        instance_id=None,
    )
    db = Mock()

    normalized, errors = console_router._normalize_branch_change_patch(
        db=db,
        branch=branch,
        patch_payload={"instance_id": 12345},
    )

    assert normalized == {}
    assert "instance_id must be string" in errors
