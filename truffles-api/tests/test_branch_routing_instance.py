from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import Mock

from app.routers.webhook.branch_selection import _handle_branch_selection_gate
from app.services.chatflow_service import get_instance_id
from app.services.state_machine import ConversationState


def test_instance_id_overrides_existing_branch():
    client_id = uuid4()
    branch_a_id = uuid4()
    branch_b_id = uuid4()

    conversation = SimpleNamespace(
        id=uuid4(),
        branch_id=branch_a_id,
        context={},
        state=ConversationState.BOT_ACTIVE.value,
    )
    user = SimpleNamespace(user_metadata={})
    settings = SimpleNamespace(branch_resolution_mode="hybrid", remember_branch_preference=True)
    metadata = SimpleNamespace(instanceId="instance-b")
    branch_b = SimpleNamespace(
        id=branch_b_id,
        client_id=client_id,
        instance_id="instance-b",
        is_active=True,
        name="Branch B",
        slug="branch_b",
    )

    query = Mock()
    query.filter.return_value.first.return_value = branch_b
    db = Mock()
    db.query.return_value = query

    result = _handle_branch_selection_gate(
        db=db,
        client_id=client_id,
        settings=settings,
        conversation=conversation,
        user=user,
        metadata=metadata,
        message_text="hello",
        now=datetime.now(timezone.utc),
        send_and_save=Mock(return_value=("ok", True)),
    )

    assert result is None
    assert conversation.branch_id == branch_b_id
    assert user.user_metadata.get("branch_id") == str(branch_b_id)


def test_get_instance_id_prefers_branch_id():
    client_id = uuid4()
    branch_id = uuid4()

    branch = SimpleNamespace(id=branch_id, client_id=client_id, instance_id="inst-branch")
    client = SimpleNamespace(id=client_id, config={"instance_id": "inst-client"})

    branch_query = Mock()
    branch_query.filter.return_value.first.return_value = branch
    client_query = Mock()
    client_query.filter.return_value.first.return_value = client

    db = Mock()
    db.query.side_effect = [branch_query, client_query]

    instance_id = get_instance_id(db, client_id, branch_id=branch_id)

    assert instance_id == "inst-branch"
