from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.routers import webhook
from app.routers.webhook import _legacy as legacy
from app.routers.webhook.class_router_runtime import (
    DomainIntent,
    _resolve_class_router_result,
    build_observer_class_router_result,
)
from app.routers.webhook.response import (
    MSG_LOW_CONFIDENCE_RETRY,
    _finalize_bot_response,
    _should_route_explicit_info_to_main_flow,
)
from app.routers.webhook.response_compat import _handle_ai_response_action
from app.services.intent_service import Intent


def test_maybe_append_booking_cta_adds_prompt_when_needed():
    response = webhook._maybe_append_booking_cta(
        "Мы можем помочь с услугой",
        conversation_state=webhook.ConversationState.BOT_ACTIVE.value,
        allow_booking_flow=True,
        has_followup=False,
    )

    assert response.endswith(webhook.MSG_BOOKING_CTA)


def test_maybe_append_booking_cta_skips_when_already_mentions_booking():
    response = webhook._maybe_append_booking_cta(
        "Хотите записаться на процедуру?",
        conversation_state=webhook.ConversationState.BOT_ACTIVE.value,
        allow_booking_flow=True,
        has_followup=False,
    )

    assert response == "Хотите записаться на процедуру?"


def test_apply_quiet_hours_notice_adds_notice():
    response = webhook._apply_quiet_hours_notice(
        "Мы ответим утром.",
        "Салон сейчас закрыт.",
    )

    assert response == "Салон сейчас закрыт.\n\nМы ответим утром."


def test_apply_quiet_hours_notice_skips_when_notice_present():
    response = webhook._apply_quiet_hours_notice(
        "Салон сейчас закрыт. Мы ответим утром.",
        "Салон сейчас закрыт.",
    )

    assert response == "Салон сейчас закрыт. Мы ответим утром."


def test_finalize_bot_response_quiet_hours_ttl():
    conversation = SimpleNamespace(
        state=webhook.ConversationState.BOT_ACTIVE.value,
        context={},
    )
    now = datetime(2026, 1, 27, 21, 0, tzinfo=timezone.utc)
    response = _finalize_bot_response(
        "Ответ",
        conversation=conversation,
        quiet_hours_notice="Салон закрыт.",
        evening_greeting=None,
        now=now,
    )
    assert response.startswith("Салон закрыт.")

    response = _finalize_bot_response(
        "Ответ",
        conversation=conversation,
        quiet_hours_notice="Салон закрыт.",
        evening_greeting=None,
        now=now + timedelta(minutes=5),
    )
    assert response == "Ответ"

    response = _finalize_bot_response(
        "Ответ",
        conversation=conversation,
        quiet_hours_notice="Салон закрыт.",
        evening_greeting=None,
        now=now + timedelta(minutes=11),
    )
    assert response.startswith("Салон закрыт.")


def test_finalize_bot_response_evening_greeting_once():
    conversation = SimpleNamespace(
        state=webhook.ConversationState.BOT_ACTIVE.value,
        context={},
    )
    now = datetime(2026, 1, 27, 19, 0, tzinfo=timezone.utc)
    greeting = "Добрый вечер. Это виртуальный ассистент салона."
    response = _finalize_bot_response(
        "Ответ",
        conversation=conversation,
        quiet_hours_notice=None,
        evening_greeting=greeting,
        now=now,
    )
    assert response.startswith(greeting)

    response = _finalize_bot_response(
        "Ответ",
        conversation=conversation,
        quiet_hours_notice=None,
        evening_greeting=greeting,
        now=now + timedelta(hours=1),
    )
    assert response == "Ответ"


def test_time_only_guard_detection():
    assert legacy._looks_like_time_only_request("в 7") is True
    assert legacy._looks_like_time_only_request("на 7:30") is True
    assert legacy._looks_like_time_only_request("э на чассов в 7") is True
    assert legacy._looks_like_time_only_request("маникюр в 7") is False
    assert legacy._looks_like_time_only_request("на час") is False


def test_route_explicit_info_to_main_flow_flag():
    assert _should_route_explicit_info_to_main_flow(
        consult_short_circuit=True,
        consult_short_circuit_reason="explicit_info",
    )
    assert _should_route_explicit_info_to_main_flow(
        consult_short_circuit=True,
        consult_short_circuit_reason="explicit_info_unknown_topic",
    )
    assert not _should_route_explicit_info_to_main_flow(
        consult_short_circuit=True,
        consult_short_circuit_reason="consult_overrides_info",
    )
    assert not _should_route_explicit_info_to_main_flow(
        consult_short_circuit=False,
        consult_short_circuit_reason="explicit_info",
    )


def test_class_router_result_keeps_owner_info_intents_when_controller_disagrees():
    result = _resolve_class_router_result(
        info_intents={"hours"},
        info_meta=None,
        booking_signal=False,
        class_carryover=None,
        domain_intent=DomainIntent.UNKNOWN,
        domain_meta=None,
        router_state={
            "used": True,
            "attempted": True,
            "fallback": False,
            "confidence": 0.95,
            "error": None,
            "fallback_reason": None,
            "signal_class": "info_bundle",
            "signal_match": False,
            "used_reason": "controller",
            "output": {
                "class": "out_of_domain",
                "goal": "out_of_domain",
                "intents": ["pricing"],
                "controller_llm_ms": 12.0,
                "controller_error": "none",
                "controller_retry": False,
            },
            "sla": None,
        },
        explicit_service_signal=False,
    )

    assert result.get("classes") == ["info_bundle"]
    assert result.get("intents") == ["hours"]
    assert result.get("controller", {}).get("goal") == "out_of_domain"


def test_class_router_result_does_not_fabricate_deterministic_controller_goal() -> None:
    result = _resolve_class_router_result(
        info_intents=set(),
        info_meta=None,
        booking_signal=True,
        class_carryover=None,
        domain_intent=DomainIntent.UNKNOWN,
        domain_meta=None,
        router_state={
            "used": False,
            "attempted": False,
            "fallback": False,
            "confidence": 0.0,
            "error": "skipped",
            "fallback_reason": "skipped",
            "signal_class": "booking",
            "signal_match": False,
            "used_reason": None,
            "output": {
                "class": None,
                "goal": None,
                "intents": [],
                "controller_llm_ms": 0.0,
                "controller_error": "skipped",
                "controller_retry": False,
            },
            "sla": None,
        },
        explicit_service_signal=False,
    )

    assert result.get("classes") == ["booking"]
    assert result.get("controller", {}).get("used") is False
    assert result.get("controller", {}).get("goal") is None
    assert result.get("controller", {}).get("used_reason") is None


def test_build_observer_class_router_result_marks_snapshot_observer_only() -> None:
    result = build_observer_class_router_result(
        class_name="consult",
        goal="consult",
        info_intents={"pricing"},
        in_signals=["consult_signal"],
    )

    assert result.get("classes") == ["consult"]
    assert result.get("intents") == ["pricing"]
    assert result.get("observer_only") is True
    assert result.get("controller", {}).get("used") is False
    assert result.get("controller", {}).get("used_reason") == "observer_only"
    assert result.get("controller", {}).get("goal") == "consult"


def test_ai_response_low_confidence_ignores_class_router_info_fallback() -> None:
    conversation = SimpleNamespace(
        id="conv-low-confidence",
        state=webhook.ConversationState.BOT_ACTIVE.value,
        context={},
        retry_offered_at=None,
    )
    user = SimpleNamespace(id="user-1", user_metadata={})
    saved_message = SimpleNamespace(message_metadata={})
    llm_primary_result = SimpleNamespace(ok=True, value=(None, "low_confidence"))

    with patch("app.routers.webhook.response._record_knowledge_backlog"), patch(
        "app.services.pack_runtime_service.format_reply_from_truth",
        return_value="Часы работы: 09:00-21:00",
    ):
        outcome = _handle_ai_response_action(
            db=Mock(),
            conversation=conversation,
            user=user,
            message_text="что у вас по часам",
            saved_message=saved_message,
            client_slug="demo_salon",
            client_id="client-1",
            client_config={},
            routing={"allow_handover_create": False},
            intent=Intent.QUESTION,
            llm_primary_result=llm_primary_result,
            append_user_message=False,
            timing_context={},
            intent_decomp_payload={"intents": ["other"], "service_query": ""},
            class_router_result={"intents": ["hours"]},
            expected_reply_shortcircuit=False,
            out_of_domain_signal=False,
            booking_signal=False,
            info_class_intents=set(),
            current_goal=None,
            now=datetime.now(timezone.utc),
            send_and_save=lambda text, **_kwargs: (text, True),
            send_response=lambda text: True,
            finalize_response=lambda **_kwargs: None,
        )

    assert outcome.bot_response == MSG_LOW_CONFIDENCE_RETRY


def test_ai_response_no_response_does_not_mint_ood_from_router_signals() -> None:
    conversation = SimpleNamespace(
        id="conv-no-response",
        state=webhook.ConversationState.BOT_ACTIVE.value,
        context={},
        retry_offered_at=None,
    )
    user = SimpleNamespace(id="user-2", user_metadata={})
    saved_message = SimpleNamespace(message_metadata={})
    llm_primary_result = SimpleNamespace(ok=True, value=(None, "high"))

    with patch("app.routers.webhook.response._record_knowledge_backlog"):
        outcome = _handle_ai_response_action(
            db=Mock(),
            conversation=conversation,
            user=user,
            message_text="непонятно",
            saved_message=saved_message,
            client_slug="demo_salon",
            client_id="client-1",
            client_config={},
            routing={"allow_handover_create": False},
            intent=Intent.QUESTION,
            llm_primary_result=llm_primary_result,
            append_user_message=False,
            timing_context={},
            intent_decomp_payload={"intents": ["other"], "service_query": ""},
            class_router_result={"in_signals": ["anchor_in"], "anchors_in_hits": 1},
            expected_reply_shortcircuit=False,
            out_of_domain_signal=True,
            booking_signal=False,
            info_class_intents=set(),
            current_goal=None,
            now=datetime.now(timezone.utc),
            send_and_save=lambda text, **_kwargs: (text, True),
            send_response=lambda text: True,
            finalize_response=lambda **_kwargs: None,
        )

    assert outcome.bot_response == MSG_LOW_CONFIDENCE_RETRY


def test_ai_response_low_signal_no_longer_short_circuits_to_ood() -> None:
    conversation = SimpleNamespace(
        id="conv-low-signal",
        state=webhook.ConversationState.BOT_ACTIVE.value,
        context={},
        retry_offered_at=None,
    )
    user = SimpleNamespace(id="user-3", user_metadata={})
    saved_message = SimpleNamespace(message_metadata={})
    llm_primary_result = SimpleNamespace(ok=True, value=("Уточню и помогу дальше.", "high"))

    outcome = _handle_ai_response_action(
        db=Mock(),
        conversation=conversation,
        user=user,
        message_text="...",
        saved_message=saved_message,
        client_slug="demo_salon",
        client_id="client-1",
        client_config={},
        routing={"allow_handover_create": False},
        intent=Intent.QUESTION,
        llm_primary_result=llm_primary_result,
        append_user_message=False,
        timing_context={},
        intent_decomp_payload={"intents": ["other"], "service_query": ""},
        class_router_result={},
        expected_reply_shortcircuit=False,
        out_of_domain_signal=True,
        booking_signal=False,
        info_class_intents=set(),
        current_goal=None,
        now=datetime.now(timezone.utc),
        send_and_save=lambda text, **_kwargs: (text, True),
        send_response=lambda text: True,
        finalize_response=lambda **_kwargs: None,
    )

    assert outcome.bot_response == "Уточню и помогу дальше."
