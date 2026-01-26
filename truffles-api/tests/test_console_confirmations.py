from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.services.console_confirmations import create_confirmation, mark_confirmation_used, require_confirmation
from app.services.console_errors import ConsoleAPIError


def _make_context(client_id, branch_id, agent_id):
    agent = SimpleNamespace(id=agent_id, name="Agent", client_id=client_id, branch_id=branch_id)
    client = SimpleNamespace(id=client_id)
    return SimpleNamespace(agent=agent, client=client, effective_branch_id=branch_id)


def test_create_confirmation_invalid_action():
    db = Mock()
    context = _make_context(uuid4(), uuid4(), uuid4())
    with pytest.raises(ConsoleAPIError) as exc_info:
        create_confirmation(
            db,
            context,
            action="unknown",
            target_type="branch",
            target_id=uuid4(),
            reason="test",
        )
    assert exc_info.value.code == "INVALID_PARAM"


def test_create_confirmation_branch_target():
    db = Mock()
    client_id = uuid4()
    branch_id = uuid4()
    agent_id = uuid4()
    branch = SimpleNamespace(id=branch_id, client_id=client_id)
    db.query.return_value.filter.return_value.first.return_value = branch
    context = _make_context(client_id, branch_id, agent_id)

    confirmation = create_confirmation(
        db,
        context,
        action="branch_deactivate",
        target_type="branch",
        target_id=branch_id,
        reason="maintenance",
    )

    assert confirmation.action == "branch_deactivate"
    assert confirmation.target_type == "branch"
    assert confirmation.target_id == branch_id
    assert confirmation.client_id == client_id
    assert confirmation.branch_id == branch_id


def test_require_confirmation_missing():
    db = Mock()
    context = _make_context(uuid4(), uuid4(), uuid4())
    with pytest.raises(ConsoleAPIError) as exc_info:
        require_confirmation(
            db,
            context,
            confirmation_id=None,
            action="branch_deactivate",
            target_type="branch",
            target_id=uuid4(),
        )
    assert exc_info.value.code == "CONFIRMATION_REQUIRED"


def test_require_confirmation_expired():
    db = Mock()
    client_id = uuid4()
    branch_id = uuid4()
    agent_id = uuid4()
    confirmation = SimpleNamespace(
        id=uuid4(),
        action="branch_deactivate",
        target_type="branch",
        target_id=branch_id,
        actor_id=agent_id,
        client_id=client_id,
        branch_id=branch_id,
        used_at=None,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=5),
    )
    db.query.return_value.filter.return_value.first.return_value = confirmation
    context = _make_context(client_id, branch_id, agent_id)

    with pytest.raises(ConsoleAPIError) as exc_info:
        require_confirmation(
            db,
            context,
            confirmation_id=confirmation.id,
            action="branch_deactivate",
            target_type="branch",
            target_id=branch_id,
        )

    assert exc_info.value.code == "CONFIRMATION_REQUIRED"
    db.commit.assert_called_once()


def test_mark_confirmation_used_sets_timestamp():
    db = Mock()
    client_id = uuid4()
    branch_id = uuid4()
    agent_id = uuid4()
    confirmation = SimpleNamespace(
        id=uuid4(),
        action="knowledge_rollback",
        target_type="knowledge_version",
        target_id=uuid4(),
        actor_id=agent_id,
        client_id=client_id,
        branch_id=branch_id,
        used_at=None,
    )
    context = _make_context(client_id, branch_id, agent_id)

    mark_confirmation_used(
        db,
        context,
        confirmation,
        action="knowledge_rollback",
        target_type="knowledge_version",
        target_id=confirmation.target_id,
    )

    assert confirmation.used_at is not None
