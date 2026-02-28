from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from app.routers.webhook import decision as webhook_router
from app.routers.webhook import pending as pending_router
from app.services import ai_service
from app.services.state_machine import ConversationState


def test_pending_status_keywords_support_kk():
    assert webhook_router.is_handover_status_question("менеджер жауап бере ме?") is True


def test_pending_wait_uses_pack_lexicon():
    db = Mock()
    now = datetime.now(timezone.utc)
    conversation = SimpleNamespace(
        state=ConversationState.PENDING.value,
        context={},
        escalated_at=None,
        id=uuid4(),
        bot_status="active",
        bot_muted_until=None,
    )
    handover = SimpleNamespace(trigger_value=None)

    def send_and_save(text: str):
        return text, True

    with patch(
        "app.routers.webhook._legacy.get_active_handover", return_value=handover
    ), patch(
        "app.routers.webhook._legacy._record_decision_trace"
    ), patch(
        "app.routers.webhook._legacy._set_conversation_context"
    ):
        for message_text in ("рахмет", "понял"):
            saved_message = SimpleNamespace(message_metadata={})
            response = pending_router._handle_pending_gate(
                db=db,
                conversation=conversation,
                message_text=message_text,
                saved_message=saved_message,
                now=now,
                send_and_save=send_and_save,
            )

            assert response is not None
            assert response.bot_response == webhook_router.MSG_PENDING_WAIT
            decision_meta = saved_message.message_metadata.get("decision_meta") or {}
            assert decision_meta.get("pending_action") == "pending_wait"


def test_thanks_phrases_from_pack():
    assert ai_service.is_thanks_message("үлкен рахмет капец") is True
    assert ai_service.is_thanks_message("раххет") is True


def test_pending_sla_collect_only_sets_runtime_mode():
    db = Mock()
    now = datetime.now(timezone.utc)
    conversation = SimpleNamespace(
        state=ConversationState.PENDING.value,
        context={},
        escalated_at=now - timedelta(minutes=30),
        id=uuid4(),
        bot_status="active",
        bot_muted_until=None,
    )
    handover = SimpleNamespace(trigger_value=None)
    saved_message = SimpleNamespace(message_metadata={})

    def send_and_save(text: str):
        return text, True

    decision = SimpleNamespace(
        severity="severe_breach",
        action="collect_only",
        reason_code="sla_severe_breach_collect_only",
        elapsed_minutes=30,
        threshold_minutes=20,
        profile_id=uuid4(),
        profile_version=2,
        profile_scope="branch",
        domain_key="salon",
    )

    with patch(
        "app.routers.webhook.pending.resolve_pending_sla_violation", return_value=decision
    ), patch(
        "app.routers.webhook._legacy.get_active_handover", return_value=handover
    ), patch(
        "app.routers.webhook._legacy._record_decision_trace"
    ), patch(
        "app.routers.webhook._legacy._set_conversation_context",
        side_effect=lambda conv, ctx: setattr(conv, "context", ctx),
    ):
        response = pending_router._handle_pending_gate(
            db=db,
            conversation=conversation,
            message_text="хочу записаться на маникюр",
            saved_message=saved_message,
            now=now,
            send_and_save=send_and_save,
        )

    assert response is not None
    assert response.bot_response == webhook_router.MSG_PENDING_WAIT
    decision_meta = saved_message.message_metadata.get("decision_meta") or {}
    assert decision_meta.get("pending_action") == "pending_sla_collect_only"
    assert "sla_runtime" in conversation.context
