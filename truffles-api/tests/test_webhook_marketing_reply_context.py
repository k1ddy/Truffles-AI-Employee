from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.routers.webhook import decision as decision_router


def _build_marketing_query(result):
    query = Mock()
    query.join.return_value = query
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = result
    return query


def test_attach_marketing_reply_context_updates_meta_trace_and_delivery() -> None:
    now = datetime.now(timezone.utc)
    campaign_id = uuid4()
    delivery_id = uuid4()

    conversation = SimpleNamespace(id=uuid4(), client_id=uuid4(), context={})
    saved_message = SimpleNamespace(message_metadata={})
    delivery = SimpleNamespace(
        id=delivery_id,
        campaign_id=campaign_id,
        status="queued",
        created_at=now - timedelta(hours=1),
        updated_at=None,
    )
    campaign = SimpleNamespace(id=campaign_id, client_id=conversation.client_id, name="Spring Reactivation")

    db = Mock()
    db.query.return_value = _build_marketing_query((delivery, campaign))

    attached = decision_router._maybe_attach_marketing_reply_context(
        db,
        conversation=conversation,
        saved_message=saved_message,
        now=now,
    )

    assert attached is not None
    assert attached["campaign_id"] == str(campaign_id)
    assert attached["delivery_id"] == str(delivery_id)
    decision_meta = saved_message.message_metadata.get("decision_meta", {})
    assert decision_meta.get("marketing_reply_context") is True
    assert decision_meta.get("marketing_campaign_id") == str(campaign_id)
    assert decision_meta.get("marketing_delivery_id") == str(delivery_id)
    trace = conversation.context.get("decision_trace", [])
    assert any(item.get("stage") == "marketing_reply_context" for item in trace)
    assert delivery.status == "replied"


def test_attach_marketing_reply_context_no_delivery_returns_none() -> None:
    now = datetime.now(timezone.utc)
    conversation = SimpleNamespace(id=uuid4(), client_id=uuid4(), context={})
    saved_message = SimpleNamespace(message_metadata={})

    db = Mock()
    db.query.return_value = _build_marketing_query(None)

    attached = decision_router._maybe_attach_marketing_reply_context(
        db,
        conversation=conversation,
        saved_message=saved_message,
        now=now,
    )

    assert attached is None
    assert saved_message.message_metadata == {}
