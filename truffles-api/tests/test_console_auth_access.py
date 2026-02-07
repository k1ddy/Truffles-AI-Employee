from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.console_auth import (
    _filter_platform_admin_clients,
    _build_access_map,
    _build_platform_admin_access_map,
    _resolve_branch_selection,
    _resolve_client_selection,
    _resolve_company_selection,
    _resolve_role,
)
from app.services.console_errors import ConsoleAPIError


def test_build_access_map_branch_membership():
    client_id = uuid4()
    branch_id = uuid4()
    agent_id = uuid4()

    branch = SimpleNamespace(id=branch_id, client_id=client_id)
    membership = SimpleNamespace(
        scope="branch",
        branch_id=branch_id,
        company_id=None,
        client_id=None,
        role="manager",
        agent_id=agent_id,
    )

    access_map = _build_access_map(
        memberships=[membership],
        legacy_agents=[],
        branches_by_id={branch_id: branch},
        clients_by_company={},
        clients_by_id={client_id: SimpleNamespace(id=client_id, name="Client A")},
    )

    entry = access_map[client_id]
    assert entry.scopes == {"branch"}
    assert entry.branch_ids == {branch_id}
    assert entry.roles == {"manager"}
    assert entry.agent_ids == {agent_id}


def test_build_access_map_company_membership_expands_clients():
    company_id = uuid4()
    agent_id = uuid4()
    client_a = SimpleNamespace(id=uuid4(), name="Client A", company_id=company_id)
    client_b = SimpleNamespace(id=uuid4(), name="Client B", company_id=company_id)

    membership = SimpleNamespace(
        scope="company",
        branch_id=None,
        company_id=company_id,
        client_id=None,
        role="owner",
        agent_id=agent_id,
    )

    access_map = _build_access_map(
        memberships=[membership],
        legacy_agents=[],
        branches_by_id={},
        clients_by_company={company_id: [client_a, client_b]},
        clients_by_id={client_a.id: client_a, client_b.id: client_b},
    )

    assert set(access_map.keys()) == {client_a.id, client_b.id}
    for entry in access_map.values():
        assert entry.scopes == {"company"}
        assert entry.roles == {"owner"}
        assert entry.agent_ids == {agent_id}


def test_build_access_map_legacy_agent_fallback():
    client_id = uuid4()
    branch_id = uuid4()
    agent = SimpleNamespace(
        id=uuid4(),
        client_id=client_id,
        branch_id=branch_id,
        role="admin",
    )

    access_map = _build_access_map(
        memberships=[],
        legacy_agents=[agent],
        branches_by_id={branch_id: SimpleNamespace(id=branch_id, client_id=client_id)},
        clients_by_company={},
        clients_by_id={client_id: SimpleNamespace(id=client_id, name="Client A")},
    )

    entry = access_map[client_id]
    assert entry.scopes == {"branch"}
    assert entry.branch_ids == {branch_id}
    assert entry.roles == {"admin"}
    assert agent.id in entry.agent_ids


def test_resolve_role_priority():
    role = _resolve_role({"manager", "owner", "support", "platform_admin"})
    assert role == "platform_admin"


def test_build_platform_admin_access_map_scopes():
    agent_id = uuid4()
    company_id = uuid4()
    client_a = SimpleNamespace(id=uuid4(), name="Client A", company_id=company_id)
    client_b = SimpleNamespace(id=uuid4(), name="Client B", company_id=None)
    agent = SimpleNamespace(id=agent_id, role="platform_admin")

    access_map = _build_platform_admin_access_map([client_a, client_b], [agent])

    entry_a = access_map[client_a.id]
    assert entry_a.roles == {"platform_admin"}
    assert entry_a.scopes == {"company"}
    assert entry_a.branch_ids == set()
    assert entry_a.agent_ids == {agent_id}

    entry_b = access_map[client_b.id]
    assert entry_b.roles == {"platform_admin"}
    assert entry_b.scopes == {"client"}
    assert entry_b.branch_ids == set()
    assert entry_b.agent_ids == {agent_id}


def test_resolve_client_selection_requires_client_when_multiple():
    client_a = SimpleNamespace(id=uuid4(), name="Client A")
    client_b = SimpleNamespace(id=uuid4(), name="Client B")

    with pytest.raises(ConsoleAPIError) as exc_info:
        _resolve_client_selection(
            {client_a.id: SimpleNamespace(), client_b.id: SimpleNamespace()},
            [client_a, client_b],
            selected_client_id=None,
            require_selection=True,
        )

    assert exc_info.value.code == "CLIENT_SELECTION_REQUIRED"


def test_resolve_client_selection_rejects_mismatched_client():
    client_a = SimpleNamespace(id=uuid4(), name="Client A")
    client_b = SimpleNamespace(id=uuid4(), name="Client B")
    selected_client_id = uuid4()

    with pytest.raises(ConsoleAPIError) as exc_info:
        _resolve_client_selection(
            {client_a.id: SimpleNamespace(), client_b.id: SimpleNamespace()},
            [client_a, client_b],
            selected_client_id=selected_client_id,
            require_selection=True,
        )

    assert exc_info.value.code == "TENANT_MISMATCH"
    assert exc_info.value.status_code == 403


def test_resolve_client_selection_auto_for_single_client():
    client = SimpleNamespace(id=uuid4(), name="Client A")

    selected_client_id, selection_required = _resolve_client_selection(
        {client.id: SimpleNamespace()},
        [client],
        selected_client_id=None,
        require_selection=True,
    )

    assert selected_client_id == client.id
    assert selection_required is False


def test_resolve_company_selection_requires_company_when_multiple():
    company_a = uuid4()
    company_b = uuid4()

    with pytest.raises(ConsoleAPIError) as exc_info:
        _resolve_company_selection(
            {company_a, company_b},
            selected_company_id=None,
            require_selection=True,
        )

    assert exc_info.value.code == "COMPANY_SELECTION_REQUIRED"


def test_resolve_company_selection_rejects_mismatched_company():
    allowed_company = uuid4()
    selected_company_id = uuid4()

    with pytest.raises(ConsoleAPIError) as exc_info:
        _resolve_company_selection(
            {allowed_company},
            selected_company_id=selected_company_id,
            require_selection=True,
        )

    assert exc_info.value.code == "TENANT_MISMATCH"
    assert exc_info.value.status_code == 403


def test_resolve_company_selection_auto_for_single_company():
    company_id = uuid4()

    selected_company_id, selection_required = _resolve_company_selection(
        {company_id},
        selected_company_id=None,
        require_selection=True,
    )

    assert selected_company_id == company_id
    assert selection_required is False


def test_resolve_branch_selection_requires_branch_when_multiple():
    branch_ids = {uuid4(), uuid4()}

    with pytest.raises(ConsoleAPIError) as exc_info:
        _resolve_branch_selection(
            branch_ids,
            branch_restricted=True,
            selected_branch_id=None,
            require_selection=True,
        )

    assert exc_info.value.code == "BRANCH_SELECTION_REQUIRED"


def test_resolve_branch_selection_auto_for_single_branch():
    branch_id = uuid4()

    effective_branch_id, selection_required = _resolve_branch_selection(
        {branch_id},
        branch_restricted=True,
        selected_branch_id=None,
        require_selection=True,
    )

    assert effective_branch_id == branch_id
    assert selection_required is False


def test_resolve_branch_selection_accepts_valid_branch():
    branch_id = uuid4()

    effective_branch_id, selection_required = _resolve_branch_selection(
        {branch_id},
        branch_restricted=False,
        selected_branch_id=branch_id,
        require_selection=True,
    )

    assert effective_branch_id == branch_id
    assert selection_required is False


def test_resolve_branch_selection_rejects_out_of_scope():
    allowed_branch_id = uuid4()
    denied_branch_id = uuid4()

    with pytest.raises(ConsoleAPIError) as exc_info:
        _resolve_branch_selection(
            {allowed_branch_id},
            branch_restricted=False,
            selected_branch_id=denied_branch_id,
            require_selection=True,
        )

    assert exc_info.value.code == "BRANCH_ACCESS_DENIED"
    assert exc_info.value.status_code == 403


def test_resolve_branch_selection_ignores_out_of_scope_without_required_selection():
    allowed_branch_id = uuid4()
    denied_branch_id = uuid4()

    effective_branch_id, selection_required = _resolve_branch_selection(
        {allowed_branch_id},
        branch_restricted=False,
        selected_branch_id=denied_branch_id,
        require_selection=False,
    )

    assert effective_branch_id is None
    assert selection_required is False


def test_filter_platform_admin_clients_returns_active_only_by_default():
    active = SimpleNamespace(id=uuid4(), name="A", status="active")
    deleted = SimpleNamespace(id=uuid4(), name="B", status="deleted")

    filtered = _filter_platform_admin_clients(
        [active, deleted],
        include_inactive_tenants=False,
    )

    assert filtered == [active]


def test_filter_platform_admin_clients_fallbacks_to_full_list_when_no_active():
    archived = SimpleNamespace(id=uuid4(), name="A", status="deleted")
    suspended = SimpleNamespace(id=uuid4(), name="B", status="suspended")

    filtered = _filter_platform_admin_clients(
        [archived, suspended],
        include_inactive_tenants=False,
    )

    assert filtered == [archived, suspended]
