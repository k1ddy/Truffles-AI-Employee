from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services.escalation_service import send_telegram_notification


@patch("app.services.escalation_service._refresh_handover_media_contract")
@patch("app.services.escalation_service.get_or_create_topic")
@patch("app.services.escalation_service.TelegramService")
def test_send_telegram_notification_forwards_handover_media_refs(
    mock_telegram_class,
    mock_get_or_create_topic,
    mock_refresh_contract,
):
    mock_refresh_contract.return_value = None
    mock_get_or_create_topic.return_value = 12345

    mock_telegram = Mock()
    mock_telegram.send_message.return_value = {"ok": True, "result": {"message_id": 777}}
    mock_telegram.pin_message.return_value = {"ok": True}
    mock_telegram.send_photo.return_value = {"ok": True, "result": {"message_id": 778}}
    mock_telegram_class.return_value = mock_telegram

    db = Mock()
    handover = SimpleNamespace(
        id="handover-1",
        client_id="client-1",
        trigger_type="intent",
        trigger_value="human_request",
        telegram_message_id=None,
        notified_at=None,
        meta={
            "media_handoff_contract": {"required": True, "bound": True, "media_refs_count": 1},
            "media_refs": [
                {
                    "media_type": "photo",
                    "public_url": "https://example.com/ref.jpg",
                    "caption": "Вот фото референса",
                }
            ],
        },
    )
    conversation = SimpleNamespace(
        id="conv-1",
        client_id="client-1",
        telegram_topic_id=12345,
        context={},
    )
    user = SimpleNamespace(name="Aigerim", phone="77015705555", telegram_topic_id=12345)

    ok = send_telegram_notification(
        db=db,
        handover=handover,
        conversation=conversation,
        user=user,
        message="Передайте менеджеру",
        routing_meta={"bot_token": "token", "chat_id": "chat-id"},
    )

    assert ok is True
    mock_telegram.send_message.assert_called_once()
    mock_telegram.send_photo.assert_called_once()
    assert handover.telegram_message_id == 777
    delivery = (handover.meta or {}).get("media_handoff_delivery") or {}
    telegram_delivery = delivery.get("telegram") or {}
    assert telegram_delivery.get("status") == "sent"
    assert telegram_delivery.get("sent_count") == 1


@patch("app.services.escalation_service._refresh_handover_media_contract")
@patch("app.services.escalation_service.TelegramService")
def test_send_telegram_notification_fails_when_required_media_refs_missing(
    mock_telegram_class,
    mock_refresh_contract,
):
    mock_refresh_contract.return_value = None

    db = Mock()
    handover = SimpleNamespace(
        id="handover-2",
        client_id="client-2",
        trigger_type="intent",
        trigger_value="human_request",
        telegram_message_id=None,
        notified_at=None,
        meta={
            "media_handoff_contract": {
                "required": True,
                "bound": False,
                "media_refs_count": 0,
            }
        },
    )
    conversation = SimpleNamespace(
        id="conv-2",
        client_id="client-2",
        telegram_topic_id=None,
        context={},
    )
    user = SimpleNamespace(name="Dana", phone="77015706666", telegram_topic_id=None)

    ok = send_telegram_notification(
        db=db,
        handover=handover,
        conversation=conversation,
        user=user,
        message="Передайте менеджеру",
        routing_meta={"bot_token": "token", "chat_id": "chat-id"},
    )

    assert ok is False
    mock_telegram_class.assert_not_called()
    delivery = (handover.meta or {}).get("media_handoff_delivery") or {}
    telegram_delivery = delivery.get("telegram") or {}
    assert telegram_delivery.get("status") == "failed"
    assert telegram_delivery.get("reason") == "media_refs_missing"
    assert isinstance(telegram_delivery.get("updated_at"), str)
