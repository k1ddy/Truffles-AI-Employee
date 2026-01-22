from types import SimpleNamespace
from uuid import uuid4

from app.services.console_auth import _build_access_map, _resolve_role


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
    role = _resolve_role({"manager", "owner", "support"})
    assert role == "owner"
