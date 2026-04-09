from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

pytest.importorskip("dateparser")

from app.routers.webhook import decision as decision_router
from app.routers.webhook.decision import MSG_PENDING_WAIT, _handle_knowledge_safe_mode_gate
from app.services.state_machine import ConversationState


def test_safe_mode_gate_sends_pending_wait_when_not_bot_active():
    branch_id = uuid4()
    branch = SimpleNamespace(
        id=branch_id,
        knowledge_safe_mode=True,
        knowledge_safe_mode_reason="sync_failed",
        knowledge_tag=None,
    )

    query = Mock()
    query.filter.return_value.first.return_value = branch

    db = Mock()
    db.query.return_value = query
    db.commit = Mock()

    conversation = SimpleNamespace(
        id=uuid4(),
        branch_id=branch_id,
        state=ConversationState.PENDING.value,
        context={},
    )

    send_and_save = Mock(return_value=("ok", True))
    response = _handle_knowledge_safe_mode_gate(
        db=db,
        conversation=conversation,
        user=SimpleNamespace(),
        saved_message=None,
        message_text="hello",
        send_and_save=send_and_save,
    )

    assert response is not None
    assert response.success is True
    send_and_save.assert_called_once_with(MSG_PENDING_WAIT)


def test_knowledge_safe_mode_records_canonical_handoff_action_when_pending(monkeypatch):
    branch_id = uuid4()
    branch = SimpleNamespace(
        id=branch_id,
        knowledge_safe_mode=True,
        knowledge_safe_mode_reason="sync_failed",
        knowledge_tag=None,
    )

    query = Mock()
    query.filter.return_value.first.return_value = branch

    db = Mock()
    db.query.return_value = query
    db.commit = Mock()

    saved_message = SimpleNamespace(meta={})
    recorded: list[dict[str, object]] = []
    monkeypatch.setattr(
        decision_router,
        "_record_message_decision_meta",
        lambda _message, **kwargs: recorded.append(kwargs),
    )

    conversation = SimpleNamespace(
        id=uuid4(),
        branch_id=branch_id,
        state=ConversationState.PENDING.value,
        context={},
    )

    send_and_save = Mock(return_value=("ok", True))
    response = _handle_knowledge_safe_mode_gate(
        db=db,
        conversation=conversation,
        user=SimpleNamespace(),
        saved_message=saved_message,
        message_text="hello",
        send_and_save=send_and_save,
    )

    assert response is not None
    assert recorded[-1]["action"] == "handoff"


def test_knowledge_safe_mode_records_canonical_handoff_action_when_reused(monkeypatch):
    branch_id = uuid4()
    branch = SimpleNamespace(
        id=branch_id,
        knowledge_safe_mode=True,
        knowledge_safe_mode_reason="sync_failed",
        knowledge_tag=None,
    )

    query = Mock()
    query.filter.return_value.first.return_value = branch

    db = Mock()
    db.query.return_value = query
    db.commit = Mock()

    saved_message = SimpleNamespace(meta={})
    recorded: list[dict[str, object]] = []
    monkeypatch.setattr(
        decision_router,
        "_record_message_decision_meta",
        lambda _message, **kwargs: recorded.append(kwargs),
    )
    monkeypatch.setattr(
        decision_router,
        "_reuse_active_handover",
        lambda **_kwargs: (SimpleNamespace(), True, True),
    )

    conversation = SimpleNamespace(
        id=uuid4(),
        branch_id=branch_id,
        state=ConversationState.BOT_ACTIVE.value,
        context={},
    )

    send_and_save = Mock(return_value=("ok", True))
    response = _handle_knowledge_safe_mode_gate(
        db=db,
        conversation=conversation,
        user=SimpleNamespace(),
        saved_message=saved_message,
        message_text="hello",
        send_and_save=send_and_save,
    )

    assert response is not None
    assert recorded[-1]["action"] == "handoff"
