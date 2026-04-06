from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from app.routers import webhook
from app.routers.webhook import response as webhook_response
from app.routers.webhook import _legacy as legacy
from app.routers.webhook.class_router_runtime import (
    DomainIntent,
    _resolve_class_router_result,
    build_observer_class_router_result,
)
from app.routers.webhook.response import (
    MSG_LOW_CONFIDENCE_RETRY,
    MSG_EXPECTED_SERVICE_OFF_TOPIC,
    _apply_locked_consult_topic_shift,
    _canonicalize_consult_decision_action,
    _canonicalize_response_metadata_action,
    _finalize_bot_response,
    _handle_consult_flow,
    _should_route_explicit_info_to_main_flow,
)
from app.routers.webhook.response_compat import _handle_ai_response_action
from app.services.intent_service import Intent
from app.services.result import Result


def _build_consult_flow_kwargs(*, message_text: str) -> dict:
    return {
        "db": Mock(),
        "conversation": SimpleNamespace(
            id=uuid4(),
            state=webhook.ConversationState.BOT_ACTIVE.value,
            context={},
            branch_id=uuid4(),
            client_id=uuid4(),
        ),
        "user": SimpleNamespace(id=uuid4(), user_metadata={}),
        "message_text": message_text,
        "saved_message": SimpleNamespace(message_metadata={}),
        "client_slug": "demo_salon",
        "policy_type": None,
        "policy_pack": {},
        "policy_handler": {},
        "routing": {
            "allow_bot_reply": True,
            "allow_handover_create": False,
            "allow_booking_flow": False,
        },
        "bypass_domain_flows": False,
        "booking_wants_flow": False,
        "booking_active": False,
        "booking_signal": False,
        "intent_decomp_set": set(),
        "consult_intent": True,
        "consult_topic": None,
        "consult_question": None,
        "intent_decomp_payload": {"consult_intent": True},
        "intent_decomp_service_query": None,
        "info_class_intents": set(),
        "intent_queue_followup": None,
        "current_goal": "booking",
        "expected_reply_type": None,
        "consult_context": None,
        "message_count": 1,
        "now": datetime.now(timezone.utc),
        "timing_context": {},
        "client_config": {},
        "send_and_save": lambda text, **_kwargs: (text, True),
        "record_escalation_metric": lambda _reason: None,
    }


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


def test_response_compat_low_confidence_info_fallback_records_canonical_fact_action() -> None:
    conversation = SimpleNamespace(
        id=uuid4(),
        state=webhook.ConversationState.BOT_ACTIVE.value,
        context={},
        retry_offered_at=None,
    )
    user = SimpleNamespace(id="user-info", user_metadata={})
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
            intent_decomp_payload={"intents": ["hours"], "service_query": ""},
            class_router_result={},
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

    assert outcome.bot_response == "Часы работы: 09:00-21:00"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "fact"
    assert meta.get("intent") == "hours"
    assert meta.get("source") == "low_confidence_guard"


def test_response_compat_service_not_found_records_canonical_fact_action() -> None:
    conversation = SimpleNamespace(
        id=uuid4(),
        state=webhook.ConversationState.BOT_ACTIVE.value,
        context={},
        retry_offered_at=None,
    )
    user = SimpleNamespace(id="user-service", user_metadata={})
    saved_message = SimpleNamespace(message_metadata={})
    llm_primary_result = SimpleNamespace(ok=True, value=(None, "low_confidence"))
    timing_context = {
        "rag_attempted": True,
        "rag_scores": {"vector_count": 0, "bm25_count": 0},
        "llm_used": False,
        "llm_timeout": False,
        "llm_cache_hit": False,
    }

    with patch("app.routers.webhook.response._record_knowledge_backlog"):
        outcome = _handle_ai_response_action(
            db=Mock(),
            conversation=conversation,
            user=user,
            message_text="делаете стрижку?",
            saved_message=saved_message,
            client_slug="demo_salon",
            client_id="client-1",
            client_config={},
            routing={"allow_handover_create": False},
            intent=Intent.QUESTION,
            llm_primary_result=llm_primary_result,
            append_user_message=False,
            timing_context=timing_context,
            intent_decomp_payload={
                "intents": ["other"],
                "service_query": "стрижка",
                "service_query_source": "intent_decomp",
            },
            class_router_result={"in_signals": [], "anchors_in_hits": 0},
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

    assert outcome.bot_response is not None
    assert "в списке услуг нет такой позиции" in outcome.bot_response.casefold()
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "fact"
    assert meta.get("intent") == "service_not_found"
    assert meta.get("source") == "truth_gate"


def test_canonicalize_consult_decision_action_maps_reply_variants_to_canonical_actions() -> None:
    assert (
        _canonicalize_consult_decision_action(
            action="reply",
            consult_flow_decision="consult_clarify",
            consult_meta={},
        )
        == "collect"
    )
    assert (
        _canonicalize_consult_decision_action(
            action="reply",
            consult_flow_decision="consult_reply",
            consult_meta={"fact_source": "pack"},
        )
        == "fact"
    )
    assert (
        _canonicalize_consult_decision_action(
            action="reply",
            consult_flow_decision="consult_reply",
            consult_meta={"observer_expected_reply_type": webhook_response.EXPECTED_REPLY_SERVICE},
        )
        == "collect"
    )
    assert (
        _canonicalize_consult_decision_action(
            action="escalate",
            consult_flow_decision="consult_escalate",
            consult_meta={},
        )
        == "handoff"
    )


def test_apply_locked_consult_topic_shift_records_observer_expected_reply_fields() -> None:
    conversation = SimpleNamespace(
        id=uuid4(),
        state=webhook.ConversationState.BOT_ACTIVE.value,
        context={},
    )
    saved_message = SimpleNamespace(message_metadata={})
    trace_calls: list[dict[str, object]] = []
    consult_meta = {"consult_topic": "hair_repair"}

    with patch(
        "app.routers.webhook.response._record_decision_trace",
        side_effect=lambda conv, trace: trace_calls.append(dict(trace)),
    ):
        _apply_locked_consult_topic_shift(
            conversation=conversation,
            saved_message=saved_message,
            consult_meta=consult_meta,
            message_count=2,
            now=datetime.now(timezone.utc),
        )

    assert consult_meta.get("observer_expected_reply_type") == webhook_response.EXPECTED_REPLY_SERVICE
    assert consult_meta.get("observer_expected_reply_reason") == "consult_topic_shift"
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("consult_topic_shift_expected_reply") is True
    assert meta.get("observer_expected_reply_type") == webhook_response.EXPECTED_REPLY_SERVICE
    assert meta.get("observer_expected_reply_reason") == "consult_topic_shift"
    assert any(
        entry.get("stage") == "consult_flow"
        and entry.get("decision") == "consult_topic_shift_expected_reply"
        and entry.get("observer_expected_reply_type") == webhook_response.EXPECTED_REPLY_SERVICE
        and entry.get("observer_expected_reply_reason") == "consult_topic_shift"
        for entry in trace_calls
    )


def test_canonicalize_response_metadata_action_maps_legacy_labels_to_canonical_actions() -> None:
    assert _canonicalize_response_metadata_action(action="ai_response", decision="bot_reply") == "fact"
    assert (
        _canonicalize_response_metadata_action(
            action="ai_response",
            decision="low_confidence_retry",
        )
        == "collect"
    )
    assert (
        _canonicalize_response_metadata_action(
            action="ai_response",
            decision="low_confidence_handover_confirm",
        )
        == "handoff"
    )
    assert _canonicalize_response_metadata_action(action="escalate", decision="blocked_topics") == "handoff"


def test_response_compat_high_confidence_reply_records_canonical_fact_action() -> None:
    conversation = SimpleNamespace(
        id=uuid4(),
        state=webhook.ConversationState.BOT_ACTIVE.value,
        context={},
        retry_offered_at=None,
    )
    user = SimpleNamespace(id="user-fact", user_metadata={})
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
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "fact"


def test_response_compat_low_confidence_retry_records_canonical_collect_action() -> None:
    conversation = SimpleNamespace(
        id=uuid4(),
        state=webhook.ConversationState.BOT_ACTIVE.value,
        context={},
        retry_offered_at=None,
    )
    user = SimpleNamespace(id="user-collect", user_metadata={})
    saved_message = SimpleNamespace(message_metadata={})
    llm_primary_result = SimpleNamespace(ok=True, value=(None, "low_confidence"))

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

    assert outcome.bot_response == MSG_LOW_CONFIDENCE_RETRY
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "collect"


def test_handle_consult_flow_records_canonical_collect_for_clarify_reply(monkeypatch) -> None:
    kwargs = _build_consult_flow_kwargs(message_text="Мне нужна консультация")
    traces: list[dict] = []
    playbook = SimpleNamespace(
        topics=[],
        default_policy=SimpleNamespace(escalate_on_low_confidence=False, clarify_limit=None),
    )

    monkeypatch.setattr(webhook_response, "_record_decision_trace", lambda _conversation, payload: traces.append(payload))

    with patch("app.services.ai_service.generate_consult_controller_output", return_value=SimpleNamespace(ok=True, value=None, error=None, error_code=None)), patch(
        "app.services.consult_pack_service.load_consult_playbook",
        return_value=(playbook, None),
    ), patch(
        "app.services.knowledge_service.resolve_consult_topic_candidates",
        return_value=[],
    ), patch(
        "app.services.knowledge_snapshot_consumer.get_consult_snapshot_mode",
        return_value="shadow",
    ), patch(
        "app.services.knowledge_snapshot_consumer.is_snapshot_consumer_enabled",
        return_value=False,
    ), patch(
        "app.services.pack_runtime_service.has_consult_recommendation_signal",
        return_value=False,
        ):
        result = _handle_consult_flow(**kwargs)

    assert result.response is not None
    assert result.response.bot_response.startswith(MSG_EXPECTED_SERVICE_OFF_TOPIC)
    meta = kwargs["saved_message"].message_metadata.get("decision_meta", {})
    assert meta.get("action") == "collect"
    consult_trace = next(payload for payload in traces if payload.get("stage") == "consult")
    assert consult_trace.get("decision") == "collect"


def test_handle_consult_flow_records_canonical_fact_for_pack_reply(monkeypatch) -> None:
    kwargs = _build_consult_flow_kwargs(message_text="Какую именно стрижку вы рекомендуете?")
    traces: list[dict] = []
    topic = SimpleNamespace(id="hair_aftercolor", fact_requirements=[], clarify_limit=None, escalate_when=[])
    playbook = SimpleNamespace(
        topics=[topic],
        default_policy=SimpleNamespace(escalate_on_low_confidence=False, clarify_limit=None),
    )
    controller_output = SimpleNamespace(
        intent="consult",
        topic_id="hair_aftercolor",
        confidence=0.93,
        risk_class="low",
        actions=[],
    )
    pack_reply = SimpleNamespace(
        response="Для начала покажите, какой результат вам ближе по форме.",
        intent="consult_reply",
        meta={"fact_source": "pack"},
    )

    monkeypatch.setattr(webhook_response, "_record_decision_trace", lambda _conversation, payload: traces.append(payload))

    with patch("app.services.ai_service.generate_consult_controller_output", return_value=SimpleNamespace(ok=True, value=controller_output, error=None, error_code=None)), patch(
        "app.services.consult_pack_service.load_consult_playbook",
        return_value=(playbook, None),
    ), patch(
        "app.services.consult_pack_service.get_consult_topic",
        return_value=topic,
    ), patch(
        "app.services.consult_pack_service.build_consult_pack_reply",
        return_value=pack_reply,
    ), patch(
        "app.services.knowledge_service.resolve_consult_topic_candidates",
        return_value=[{"topic_id": "hair_aftercolor", "score": 0.93}],
    ), patch(
        "app.services.knowledge_snapshot_consumer.get_consult_snapshot_mode",
        return_value="shadow",
    ), patch(
        "app.services.knowledge_snapshot_consumer.is_snapshot_consumer_enabled",
        return_value=False,
    ), patch(
        "app.services.pack_runtime_service.has_consult_recommendation_signal",
        return_value=False,
        ):
        result = _handle_consult_flow(**kwargs)

    assert result.response is not None
    assert result.response.bot_response.startswith(pack_reply.response)
    meta = kwargs["saved_message"].message_metadata.get("decision_meta", {})
    assert meta.get("action") == "fact"
    consult_trace = next(payload for payload in traces if payload.get("stage") == "consult")
    assert consult_trace.get("decision") == "fact"


def test_handle_consult_flow_records_canonical_handoff_for_escalate(monkeypatch) -> None:
    kwargs = _build_consult_flow_kwargs(message_text="Мне нужна консультация по сложному случаю")
    kwargs["routing"]["allow_handover_create"] = False
    traces: list[dict] = []
    topic = SimpleNamespace(id="hair_aftercolor", fact_requirements=[], clarify_limit=None, escalate_when=[])
    playbook = SimpleNamespace(
        topics=[topic],
        default_policy=SimpleNamespace(escalate_on_low_confidence=False, clarify_limit=None),
    )
    controller_output = SimpleNamespace(
        intent="consult",
        topic_id="hair_aftercolor",
        confidence=0.92,
        risk_class="high",
        actions=["handoff"],
    )

    monkeypatch.setattr(webhook_response, "_record_decision_trace", lambda _conversation, payload: traces.append(payload))

    with patch("app.services.ai_service.generate_consult_controller_output", return_value=SimpleNamespace(ok=True, value=controller_output, error=None, error_code=None)), patch(
        "app.services.consult_pack_service.load_consult_playbook",
        return_value=(playbook, None),
    ), patch(
        "app.services.consult_pack_service.get_consult_topic",
        return_value=topic,
    ), patch(
        "app.services.knowledge_service.resolve_consult_topic_candidates",
        return_value=[{"topic_id": "hair_aftercolor", "score": 0.92}],
    ), patch(
        "app.services.knowledge_snapshot_consumer.get_consult_snapshot_mode",
        return_value="shadow",
    ), patch(
        "app.services.knowledge_snapshot_consumer.is_snapshot_consumer_enabled",
        return_value=False,
    ), patch(
        "app.services.pack_runtime_service.has_consult_recommendation_signal",
        return_value=False,
    ), patch(
        "app.routers.webhook.response._reuse_active_handover",
        return_value=(SimpleNamespace(), True, True),
    ):
        result = _handle_consult_flow(**kwargs)

    assert result.response is not None
    assert result.response.bot_response == webhook_response.MSG_ESCALATED
    meta = kwargs["saved_message"].message_metadata.get("decision_meta", {})
    assert meta.get("action") == "handoff"
    consult_trace = next(payload for payload in traces if payload.get("stage") == "consult")
    assert consult_trace.get("decision") == "handoff"


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


def test_handle_llm_primary_records_canonical_fact_for_direct_reply() -> None:
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id="client-123",
        state=webhook.ConversationState.BOT_ACTIVE.value,
        context={},
    )
    saved_message = SimpleNamespace(id="msg-1", message_metadata={})

    with patch("app.routers.webhook.response._ensure_rag_rewrite"), patch(
        "app.routers.webhook.response._record_rag_meta"
    ), patch(
        "app.routers.webhook.response.generate_bot_response",
        return_value=Result.success(("Работаем с 9 до 21.", "high")),
    ), patch(
        "app.routers.webhook.response._detect_llm_guard_topics",
        return_value=[],
    ), patch(
        "app.routers.webhook.context_manager._reset_low_confidence_retry"
    ), patch(
        "app.routers.webhook.response._record_decision_trace"
    ), patch(
        "app.routers.webhook.response._record_llm_signal_snapshot"
    ):
        outcome = webhook_response._handle_llm_primary(
            db=Mock(),
            conversation=conversation,
            user=SimpleNamespace(id="user-123"),
            message_text="Когда вы работаете?",
            saved_message=saved_message,
            client_slug="demo_salon",
            policy_type=None,
            policy_pack=None,
            routing={"allow_bot_reply": True, "allow_handover_create": False},
            append_user_message=False,
            timing_context={},
            client_config=None,
            intent=Intent.QUESTION,
            multi_intent_other_followup=None,
            send_and_save=lambda bot_response, allow_quiet_hours=False: (bot_response, True),
            record_escalation_metric=lambda *_args, **_kwargs: None,
        )

    assert outcome.response is not None
    assert outcome.response.bot_response == "Работаем с 9 до 21."
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "fact"


def test_handle_llm_primary_records_canonical_handoff_for_llm_guard() -> None:
    conversation = SimpleNamespace(
        id=uuid4(),
        client_id="client-123",
        state=webhook.ConversationState.BOT_ACTIVE.value,
        context={},
    )
    saved_message = SimpleNamespace(id="msg-2", message_metadata={})

    with patch("app.routers.webhook.response._ensure_rag_rewrite"), patch(
        "app.routers.webhook.response._record_rag_meta"
    ), patch(
        "app.routers.webhook.response.generate_bot_response",
        return_value=Result.success(("медицинский ответ", "high")),
    ), patch(
        "app.routers.webhook.response._detect_llm_guard_topics",
        return_value=["medical"],
    ), patch(
        "app.routers.webhook.response._reuse_active_handover",
        return_value=(None, True, True),
    ), patch(
        "app.routers.webhook.context_manager._reset_low_confidence_retry"
    ), patch(
        "app.routers.webhook.response._record_decision_trace"
    ), patch(
        "app.routers.webhook.response._record_llm_signal_snapshot"
    ):
        outcome = webhook_response._handle_llm_primary(
            db=Mock(),
            conversation=conversation,
            user=SimpleNamespace(id="user-123"),
            message_text="Нужен совет",
            saved_message=saved_message,
            client_slug="demo_salon",
            policy_type=None,
            policy_pack=None,
            routing={"allow_bot_reply": True, "allow_handover_create": False},
            append_user_message=False,
            timing_context={},
            client_config=None,
            intent=None,
            multi_intent_other_followup=None,
            send_and_save=lambda bot_response, allow_quiet_hours=False: (bot_response, True),
            record_escalation_metric=lambda *_args, **_kwargs: None,
        )

    assert outcome.response is not None
    assert outcome.response.bot_response == legacy.MSG_ESCALATED
    meta = saved_message.message_metadata.get("decision_meta", {})
    assert meta.get("action") == "handoff"
