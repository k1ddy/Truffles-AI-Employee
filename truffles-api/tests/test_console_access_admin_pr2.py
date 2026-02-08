from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.models.agent_membership import AgentMembership
from app.routers import console as console_router
from app.schemas.console import (
    ConsoleAgentCreateRequest,
    ConsoleBranchBootstrapAccountTemplate,
    ConsoleBranchCreateRequest,
)
from app.services.console_errors import ConsoleAPIError


def _mock_context(*, role: str = "platform_admin", accessible_clients=None, client_id=None):
    selected_client_id = client_id or uuid4()
    clients = accessible_clients or [SimpleNamespace(id=selected_client_id, company_id=uuid4())]
    return SimpleNamespace(
        agent=SimpleNamespace(id=uuid4(), name="Tester", role=role),
        role=role,
        client=SimpleNamespace(id=selected_client_id, company_id=clients[0].company_id),
        accessible_clients=clients,
        branches=[],
    )


def test_ensure_unique_oidc_subject_rejects_duplicate():
    db = Mock()
    query = Mock()
    query.filter.return_value = query
    query.first.return_value = SimpleNamespace(agent_id=uuid4())
    db.query.return_value = query

    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._ensure_unique_oidc_subject(db, "duplicate-subject")

    assert exc_info.value.code == "OIDC_SUBJECT_IN_USE"


def test_ensure_unique_oidc_subject_returns_normalized_value():
    db = Mock()
    query = Mock()
    query.filter.return_value = query
    query.first.return_value = None
    db.query.return_value = query

    value = console_router._ensure_unique_oidc_subject(db, "  clean-subject  ")

    assert value == "clean-subject"


def test_resolve_membership_target_rejects_mixed_scope_fields():
    db = Mock()
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._resolve_membership_target(
            db,
            scope="branch",
            company_id=None,
            client_id=uuid4(),
            branch_id=uuid4(),
        )
    assert exc_info.value.code == "INVALID_PARAM"


@pytest.mark.asyncio
async def test_create_agent_blocks_cross_tenant_access(monkeypatch):
    target_client_id = uuid4()
    allowed_client_id = uuid4()
    db = Mock()
    client = SimpleNamespace(id=target_client_id, company_id=uuid4())
    db.query.return_value.filter.return_value.first.return_value = client

    monkeypatch.setattr(
        console_router,
        "get_console_context",
        lambda *args, **kwargs: _mock_context(
            role="owner",
            accessible_clients=[SimpleNamespace(id=allowed_client_id, company_id=uuid4())],
            client_id=allowed_client_id,
        ),
    )
    monkeypatch.setattr(console_router, "require_console_permission", lambda *args, **kwargs: None)

    with pytest.raises(ConsoleAPIError) as exc_info:
        await console_router.create_agent(
            request=Mock(),
            body=ConsoleAgentCreateRequest(client_id=target_client_id, role="owner", name="Owner"),
            db=db,
        )

    assert exc_info.value.code == "ACCESS_DENIED"


@pytest.mark.asyncio
async def test_create_branch_bootstrap_accounts_return_created_agents(monkeypatch):
    client_id = uuid4()
    company_id = uuid4()
    db = Mock()
    client = SimpleNamespace(id=client_id, company_id=company_id)
    db.query.return_value.filter.return_value.first.return_value = client

    helper_calls = []

    def _fake_create_agent_with_membership(
        _db,
        *,
        client,
        role,
        branch,
        name,
        is_active,
        oidc_subject,
        linked_from,
        now,
    ):
        helper_calls.append(
            {
                "role": role,
                "branch_id": branch.id if branch else None,
                "name": name,
                "is_active": is_active,
                "linked_from": linked_from,
            }
        )
        return SimpleNamespace(
            id=uuid4(),
            name=name,
            role=role,
            client_id=client.id,
            branch_id=branch.id if branch else None,
            is_active=is_active,
        )

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
    monkeypatch.setattr(console_router, "_ensure_unique_branch_field", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "_create_agent_with_membership", _fake_create_agent_with_membership)
    monkeypatch.setattr(console_router, "record_audit_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(console_router, "ensure_onboarding_step", lambda *args, **kwargs: None)

    response = await console_router.create_branch(
        request=Mock(),
        body=ConsoleBranchCreateRequest(
            client_id=client_id,
            slug="branch-1",
            name="Branch 1",
            is_active=False,
            bootstrap_accounts=[
                ConsoleBranchBootstrapAccountTemplate(role="owner", name="Owner User"),
                ConsoleBranchBootstrapAccountTemplate(role="manager", name="Manager User"),
            ],
        ),
        db=db,
    )

    assert len(response.created_agents) == 2
    assert helper_calls[0]["role"] == "owner"
    assert helper_calls[0]["branch_id"] is None
    assert helper_calls[1]["role"] == "manager"
    assert helper_calls[1]["branch_id"] == response.branch.id
    db.commit.assert_called_once()


def test_membership_role_guard_rejects_platform_admin():
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._ensure_membership_role_is_assignable("platform_admin")
    assert exc_info.value.code == "INVALID_PARAM"


def test_membership_agent_guard_rejects_platform_admin_agent():
    with pytest.raises(ConsoleAPIError) as exc_info:
        console_router._ensure_membership_agent_is_mutable(
            SimpleNamespace(role="platform_admin"),
        )
    assert exc_info.value.code == "INVALID_STATE"


def test_create_agent_with_membership_skips_membership_for_platform_admin(monkeypatch):
    db = Mock()
    added = []
    db.add.side_effect = added.append
    client = SimpleNamespace(id=uuid4(), company_id=uuid4())

    monkeypatch.setattr(console_router, "_ensure_unique_oidc_subject", lambda *_args, **_kwargs: None)

    agent = console_router._create_agent_with_membership(
        db,
        client=client,
        role="platform_admin",
        branch=None,
        name="Platform Admin",
        is_active=True,
        oidc_subject=None,
        linked_from="test",
    )

    assert agent.role == "platform_admin"
    assert not any(isinstance(item, AgentMembership) for item in added)
