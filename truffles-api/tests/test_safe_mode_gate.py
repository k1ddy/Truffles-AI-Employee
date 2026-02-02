from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

pytest.importorskip("dateparser")

from app.routers.webhook.decision import MSG_PENDING_WAIT, _handle_minimum_data_safe_mode_gate
from app.services.knowledge_validation import MinimumDataContractStatus
from app.services.state_machine import ConversationState


def test_minimum_data_safe_mode_skips_when_ready():
    status = MinimumDataContractStatus(ready=True, missing_fields=[])
    response = _handle_minimum_data_safe_mode_gate(
        db=Mock(),
        conversation=SimpleNamespace(
            id=uuid4(),
            branch_id=uuid4(),
            state=ConversationState.BOT_ACTIVE.value,
            context={},
        ),
        user=SimpleNamespace(),
        saved_message=None,
        message_text="hello",
        status=status,
        send_and_save=Mock(),
    )
    assert response is None


def test_minimum_data_safe_mode_sends_pending_wait_when_not_bot_active():
    branch_id = uuid4()
    status = MinimumDataContractStatus(
        ready=False,
        missing_fields=["client_pack.price_list"],
    )

    db = Mock()
    db.commit = Mock()
    send_and_save = Mock(return_value=("ok", True))
    response = _handle_minimum_data_safe_mode_gate(
        db=db,
        conversation=SimpleNamespace(
            id=uuid4(),
            branch_id=branch_id,
            state=ConversationState.PENDING.value,
            context={},
        ),
        user=SimpleNamespace(),
        saved_message=None,
        message_text="hello",
        status=status,
        send_and_save=send_and_save,
    )

    assert response is not None
    assert response.success is True
    send_and_save.assert_called_once_with(MSG_PENDING_WAIT)
