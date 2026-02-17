from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from app.models import Message
from app.services.escalation_service import create_handover


def test_create_handover_populates_context_summary_and_messages():
    db = Mock()
    conversation = SimpleNamespace(
        id="conv-ctx-42",
        client_id="client-ctx-42",
        context={},
    )
    user = SimpleNamespace(
        remote_jid="77015705555@s.whatsapp.net",
        name="Aigerim",
        phone="77015705555",
    )

    base_time = datetime.now(timezone.utc)
    history_user = SimpleNamespace(
        id="msg-1",
        message_id="inbound-1",
        role="user",
        content="Хочу маникюр к Айгерим завтра",
        created_at=base_time - timedelta(minutes=2),
        message_metadata={},
    )
    history_assistant = SimpleNamespace(
        id="msg-2",
        message_id=None,
        role="assistant",
        content="Есть слот у Айгерим на 12:00",
        created_at=base_time - timedelta(minutes=1),
        message_metadata={},
    )
    trigger_message = SimpleNamespace(
        id="msg-3",
        message_id="inbound-2",
        role="user",
        content="Передайте менеджеру с фото",
        created_at=base_time,
        message_metadata={"media": {"media_type": "photo", "public_url": "https://example.com/ref.jpg"}},
    )

    message_query = Mock()
    message_query.filter.return_value = message_query
    message_query.order_by.return_value = message_query
    message_query.limit.return_value = message_query
    message_query.first.return_value = trigger_message
    message_query.all.return_value = [history_user, history_assistant, trigger_message]

    def query_side_effect(model):
        if model is Message:
            return message_query
        return Mock()

    db.query.side_effect = query_side_effect

    handover = create_handover(
        db=db,
        conversation=conversation,
        user=user,
        trigger_type="intent",
        trigger_value="human_request",
        user_message="Передайте менеджеру",
    )

    assert isinstance(handover.context_summary, str)
    assert "client: Хочу маникюр к Айгерим завтра" in handover.context_summary
    assert isinstance(handover.messages, list)
    assert len(handover.messages) == 3
    assert handover.messages[2]["message_id"] == "inbound-2"
    assert handover.meta["media_handoff_contract"]["bound"] is True
