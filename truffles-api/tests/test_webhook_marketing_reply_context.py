from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from app.routers.webhook import decision as decision_router
from app.routers.webhook import trace as webhook_trace


def _build_marketing_query(results):
    query = Mock()
    query.join.return_value = query
    query.outerjoin.return_value = query
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    query.all.return_value = results
    return query


def test_attach_marketing_reply_context_updates_meta_trace_and_delivery() -> None:
    now = datetime.now(timezone.utc)
    campaign_id = uuid4()
    delivery_id = uuid4()

    conversation = SimpleNamespace(id=uuid4(), client_id=uuid4(), context={})
    saved_message = SimpleNamespace(content="интересно", message_metadata={})
    delivery = SimpleNamespace(
        id=delivery_id,
        campaign_id=campaign_id,
        status="queued",
        created_at=now - timedelta(hours=1),
        updated_at=None,
    )
    campaign = SimpleNamespace(id=campaign_id, client_id=conversation.client_id, name="Spring Reactivation")

    db = Mock()
    db.query.return_value = _build_marketing_query([(delivery, campaign, "SENT")])

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
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        context={
            "marketing_context": {
                "campaign_id": str(uuid4()),
                "delivery_id": str(uuid4()),
            }
        },
    )
    saved_message = SimpleNamespace(content="интересно", message_metadata={})

    db = Mock()
    db.query.return_value = _build_marketing_query([])

    attached = decision_router._maybe_attach_marketing_reply_context(
        db,
        conversation=conversation,
        saved_message=saved_message,
        now=now,
    )

    assert attached is None
    assert saved_message.message_metadata == {}
    assert "marketing_context" not in conversation.context


def test_attach_marketing_reply_context_skips_non_attachable_status() -> None:
    now = datetime.now(timezone.utc)
    campaign_id = uuid4()
    delivery_id = uuid4()

    conversation = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        context={
            "marketing_context": {
                "campaign_id": str(uuid4()),
                "delivery_id": str(uuid4()),
            }
        },
    )
    saved_message = SimpleNamespace(content="интересно", message_metadata={})
    delivery = SimpleNamespace(
        id=delivery_id,
        campaign_id=campaign_id,
        status="replied",
        created_at=now - timedelta(minutes=10),
        updated_at=None,
    )
    campaign = SimpleNamespace(id=campaign_id, client_id=conversation.client_id, name="Spring Reactivation")

    db = Mock()
    db.query.return_value = _build_marketing_query([(delivery, campaign, "SENT")])

    attached = decision_router._maybe_attach_marketing_reply_context(
        db,
        conversation=conversation,
        saved_message=saved_message,
        now=now,
    )

    assert attached is None
    assert saved_message.message_metadata == {}
    assert "marketing_context" not in conversation.context
    trace = conversation.context.get("decision_trace", [])
    assert any(
        item.get("stage") == "marketing_reply_context"
        and item.get("decision") == "skipped"
        and item.get("reason") == "no_eligible_delivery"
        for item in trace
    )
    db.add.assert_not_called()


def test_attach_marketing_reply_context_skips_empty_inbound_text() -> None:
    now = datetime.now(timezone.utc)
    conversation = SimpleNamespace(id=uuid4(), client_id=uuid4(), context={})
    saved_message = SimpleNamespace(content="", message_metadata={})

    db = Mock()

    attached = decision_router._maybe_attach_marketing_reply_context(
        db,
        conversation=conversation,
        saved_message=saved_message,
        now=now,
    )

    assert attached is None
    db.query.assert_not_called()


def test_attach_marketing_reply_context_allows_caption_text_for_image_message() -> None:
    now = datetime.now(timezone.utc)
    campaign_id = uuid4()
    delivery_id = uuid4()
    conversation = SimpleNamespace(id=uuid4(), client_id=uuid4(), context={})
    saved_message = SimpleNamespace(
        content="Хочу такой цвет, есть запись?",
        message_metadata={"message_type": "image"},
    )
    delivery = SimpleNamespace(
        id=delivery_id,
        campaign_id=campaign_id,
        status="sent",
        created_at=now - timedelta(minutes=30),
        updated_at=None,
    )
    campaign = SimpleNamespace(id=campaign_id, client_id=conversation.client_id, name="Image Campaign")

    db = Mock()
    db.query.return_value = _build_marketing_query([(delivery, campaign, "SENT")])

    attached = decision_router._maybe_attach_marketing_reply_context(
        db,
        conversation=conversation,
        saved_message=saved_message,
        now=now,
    )

    assert attached is not None
    assert attached["campaign_id"] == str(campaign_id)


def test_attach_marketing_reply_context_allows_voice_transcript() -> None:
    now = datetime.now(timezone.utc)
    campaign_id = uuid4()
    delivery_id = uuid4()
    conversation = SimpleNamespace(id=uuid4(), client_id=uuid4(), context={})
    saved_message = SimpleNamespace(
        content="Да, хочу записаться на завтра",
        message_metadata={"message_type": "voice"},
    )
    delivery = SimpleNamespace(
        id=delivery_id,
        campaign_id=campaign_id,
        status="queued",
        created_at=now - timedelta(minutes=45),
        updated_at=None,
    )
    campaign = SimpleNamespace(id=campaign_id, client_id=conversation.client_id, name="Voice Campaign")

    db = Mock()
    db.query.return_value = _build_marketing_query([(delivery, campaign, "SENT")])

    attached = decision_router._maybe_attach_marketing_reply_context(
        db,
        conversation=conversation,
        saved_message=saved_message,
        now=now,
    )

    assert attached is not None
    assert attached["delivery_id"] == str(delivery_id)


def test_attach_marketing_reply_context_skips_failed_outbox_status() -> None:
    now = datetime.now(timezone.utc)
    campaign_id = uuid4()
    delivery_id = uuid4()
    conversation = SimpleNamespace(id=uuid4(), client_id=uuid4(), context={})
    saved_message = SimpleNamespace(content="интересно", message_metadata={})
    delivery = SimpleNamespace(
        id=delivery_id,
        campaign_id=campaign_id,
        status="queued",
        created_at=now - timedelta(minutes=10),
        updated_at=None,
    )
    campaign = SimpleNamespace(id=campaign_id, client_id=conversation.client_id, name="Failed Outbox Campaign")

    db = Mock()
    db.query.return_value = _build_marketing_query([(delivery, campaign, "FAILED")])

    attached = decision_router._maybe_attach_marketing_reply_context(
        db,
        conversation=conversation,
        saved_message=saved_message,
        now=now,
    )

    assert attached is None
    db.add.assert_not_called()
    trace = conversation.context.get("decision_trace", [])
    assert any(
        item.get("stage") == "marketing_reply_context" and item.get("reason") == "no_eligible_delivery"
        for item in trace
    )


def test_attach_marketing_reply_context_skips_stale_delivery() -> None:
    now = datetime.now(timezone.utc)
    campaign_id = uuid4()
    delivery_id = uuid4()
    conversation = SimpleNamespace(id=uuid4(), client_id=uuid4(), context={})
    saved_message = SimpleNamespace(content="интересно", message_metadata={})
    delivery = SimpleNamespace(
        id=delivery_id,
        campaign_id=campaign_id,
        status="queued",
        created_at=now - timedelta(days=5),
        updated_at=None,
    )
    campaign = SimpleNamespace(id=campaign_id, client_id=conversation.client_id, name="Stale Campaign")

    db = Mock()
    db.query.return_value = _build_marketing_query([(delivery, campaign, "SENT")])

    attached = decision_router._maybe_attach_marketing_reply_context(
        db,
        conversation=conversation,
        saved_message=saved_message,
        now=now,
    )

    assert attached is None
    db.add.assert_not_called()


def test_attach_marketing_reply_context_skips_ambiguous_recent_deliveries() -> None:
    now = datetime.now(timezone.utc)
    campaign_id_a = uuid4()
    campaign_id_b = uuid4()
    delivery_id_a = uuid4()
    delivery_id_b = uuid4()
    conversation = SimpleNamespace(id=uuid4(), client_id=uuid4(), context={})
    saved_message = SimpleNamespace(content="давайте", message_metadata={})
    delivery_a = SimpleNamespace(
        id=delivery_id_a,
        campaign_id=campaign_id_a,
        status="sent",
        created_at=now - timedelta(minutes=20),
        updated_at=None,
    )
    delivery_b = SimpleNamespace(
        id=delivery_id_b,
        campaign_id=campaign_id_b,
        status="queued",
        created_at=now - timedelta(hours=1),
        updated_at=None,
    )
    campaign_a = SimpleNamespace(id=campaign_id_a, client_id=conversation.client_id, name="Campaign A")
    campaign_b = SimpleNamespace(id=campaign_id_b, client_id=conversation.client_id, name="Campaign B")

    db = Mock()
    db.query.return_value = _build_marketing_query(
        [
            (delivery_a, campaign_a, "SENT"),
            (delivery_b, campaign_b, "SENT"),
        ]
    )

    attached = decision_router._maybe_attach_marketing_reply_context(
        db,
        conversation=conversation,
        saved_message=saved_message,
        now=now,
    )

    assert attached is None
    db.add.assert_not_called()
    trace = conversation.context.get("decision_trace", [])
    assert any(
        item.get("stage") == "marketing_reply_context"
        and item.get("decision") == "skipped"
        and item.get("reason") == "ambiguous_recent_deliveries"
        for item in trace
    )


def test_marketing_reply_context_stage_survives_trace_retention_overflow() -> None:
    now = datetime.now(timezone.utc)
    campaign_id = uuid4()
    delivery_id = uuid4()

    existing_trace = [
        {"stage": "policy_gate", "decision": "seed", "recorded_at": f"seed-{idx}"}
        for idx in range(webhook_trace.DECISION_TRACE_MAX + 10)
    ]
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id=uuid4(),
        context={"decision_trace": existing_trace},
    )
    saved_message = SimpleNamespace(content="интересно", message_metadata={})
    delivery = SimpleNamespace(
        id=delivery_id,
        campaign_id=campaign_id,
        status="queued",
        created_at=now - timedelta(minutes=20),
        updated_at=None,
    )
    campaign = SimpleNamespace(
        id=campaign_id,
        client_id=conversation.client_id,
        name="Trace Retention Campaign",
    )

    db = Mock()
    db.query.return_value = _build_marketing_query([(delivery, campaign, "SENT")])

    attached = decision_router._maybe_attach_marketing_reply_context(
        db,
        conversation=conversation,
        saved_message=saved_message,
        now=now,
    )
    assert attached is not None

    for _ in range(webhook_trace.DECISION_TRACE_MAX + 10):
        decision_router._record_decision_trace(
            conversation,
            {"stage": "policy_gate", "decision": "post_attach"},
        )

    trace = conversation.context.get("decision_trace", [])
    assert len(trace) == webhook_trace.DECISION_TRACE_MAX
    assert any(item.get("stage") == "marketing_reply_context" for item in trace)
