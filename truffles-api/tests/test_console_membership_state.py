from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.console_errors import ConsoleAPIError
from app.services.console_membership_state import (
    ensure_agent_lifecycle_is_mutable,
    ensure_membership_agent_is_mutable,
    ensure_membership_change_keeps_privileged_access,
    ensure_membership_role_is_assignable,
    ensure_role_not_deprecated_for_assignment,
    is_privileged_access_role,
)


def test_ensure_role_not_deprecated_for_assignment_rejects_legacy_roles() -> None:
    with pytest.raises(ConsoleAPIError) as exc:
        ensure_role_not_deprecated_for_assignment("support")
    assert exc.value.status_code == 400
    assert exc.value.code == "INVALID_PARAM"

    with pytest.raises(ConsoleAPIError) as exc:
        ensure_role_not_deprecated_for_assignment("specialist")
    assert exc.value.status_code == 400
    assert exc.value.code == "INVALID_PARAM"


def test_ensure_membership_role_is_assignable_rejects_platform_admin() -> None:
    with pytest.raises(ConsoleAPIError) as exc:
        ensure_membership_role_is_assignable("platform_admin")
    assert exc.value.status_code == 400
    assert exc.value.code == "INVALID_PARAM"


def test_ensure_membership_agent_is_mutable_rejects_platform_admin_agent() -> None:
    platform_admin_agent = SimpleNamespace(role="platform_admin")
    with pytest.raises(ConsoleAPIError) as exc:
        ensure_membership_agent_is_mutable(platform_admin_agent)
    assert exc.value.status_code == 409
    assert exc.value.code == "INVALID_STATE"


def test_is_privileged_access_role_matches_expected_roles() -> None:
    assert is_privileged_access_role("platform_admin") is True
    assert is_privileged_access_role("owner") is True
    assert is_privileged_access_role("admin") is True
    assert is_privileged_access_role("viewer") is False


def test_ensure_membership_change_blocks_self_privileged_downgrade() -> None:
    actor_id = uuid4()
    context = SimpleNamespace(agent=SimpleNamespace(id=actor_id))
    membership = SimpleNamespace(
        id=uuid4(),
        agent_id=actor_id,
        role="owner",
        is_active=True,
    )
    agent = SimpleNamespace(client_id=uuid4())

    with pytest.raises(ConsoleAPIError) as exc:
        ensure_membership_change_keeps_privileged_access(
            db=None,
            context=context,
            membership=membership,
            agent=agent,
            next_role="viewer",
            next_is_active=True,
        )
    assert exc.value.status_code == 409
    assert exc.value.code == "INVALID_STATE"


def test_ensure_agent_lifecycle_is_mutable_guards_platform_admin_and_self_disable() -> None:
    actor_id = uuid4()
    context = SimpleNamespace(agent=SimpleNamespace(id=actor_id))

    platform_admin_agent = SimpleNamespace(
        id=uuid4(),
        role="platform_admin",
        client_id=uuid4(),
    )
    with pytest.raises(ConsoleAPIError) as exc:
        ensure_agent_lifecycle_is_mutable(
            db=None,
            context=context,
            agent=platform_admin_agent,
            enabling=False,
        )
    assert exc.value.status_code == 409
    assert exc.value.code == "INVALID_STATE"

    same_actor_agent = SimpleNamespace(
        id=actor_id,
        role="owner",
        client_id=uuid4(),
    )
    with pytest.raises(ConsoleAPIError) as exc:
        ensure_agent_lifecycle_is_mutable(
            db=None,
            context=context,
            agent=same_actor_agent,
            enabling=False,
        )
    assert exc.value.status_code == 409
    assert exc.value.code == "INVALID_STATE"
