"""Compatibility-only response helper surfaces."""

from __future__ import annotations

from app.routers.webhook import response as _response


def _bind_live_response_globals() -> None:
    globals().update(
        {
            name: value
            for name, value in _response.__dict__.items()
            if not name.startswith("__") and name != "_handle_ai_response_action"
        }
    )


_bind_live_response_globals()

def _handle_ai_response_action(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str | None,
    saved_message: Message | None,
    client_slug: str | None,
    client_id: Any,
    client_config: dict | None,
    routing: dict,
    intent: Any,
    llm_primary_result: Any | None,
    append_user_message: bool,
    timing_context: dict,
    intent_decomp_payload: dict | None,
    class_router_result: dict | None,
    expected_reply_shortcircuit: bool,
    out_of_domain_signal: bool,
    booking_signal: bool,
    info_class_intents: set[str],
    current_goal: str | None,
    now: datetime,
    send_and_save: Callable[..., tuple[str | None, bool]],
    send_response: Callable[[str], bool],
    finalize_response: Callable[..., str | None],
) -> AiResponseOutcome:
    _bind_live_response_globals()

    llm_primary_used = False
    llm_primary_failed = False
    llm_primary_reason = None
    bot_response = None
    result_message = None
    gen_result = llm_primary_result
    if gen_result is None:
        _ensure_rag_rewrite(
            conversation=conversation,
            saved_message=saved_message,
            message_text=message_text,
            client_slug=client_slug,
            client_config=client_config,
            timing_context=timing_context,
        )
        gen_result = generate_bot_response(
            db,
            conversation,
            message_text,
            client_slug,
            append_user_message=append_user_message,
            pending_hint=conversation.state == ConversationState.PENDING.value,
            timing_context=timing_context,
        )
        _record_rag_meta(
            conversation=conversation,
            saved_message=saved_message,
            timing_context=timing_context,
        )

    if not gen_result.ok:
        bot_response = MSG_AI_ERROR
        _record_decision_trace(
            conversation,
            {
                "stage": "ai_response",
                "decision": "ai_error",
                "state": conversation.state,
                "error": gen_result.error,
            },
        )
        bot_response, sent = send_and_save(bot_response)
        result_message = f"AI error: {gen_result.error}"
        return AiResponseOutcome(
            response=None,
            bot_response=bot_response,
            result_message=result_message,
            llm_primary_failed=llm_primary_failed,
            llm_primary_reason=llm_primary_reason,
        )

    response_text, confidence = gen_result.value

    if confidence == "low_confidence":
        miss_type = (
            "llm_timeout"
            if timing_context and timing_context.get("llm_timeout")
            else "low_confidence"
        )
        _record_knowledge_backlog(
            db,
            client_id=client_id,
            conversation_id=conversation.id,
            message=saved_message,
            user_text=message_text,
            miss_type=miss_type,
        )
        info_intent_hint = False
        info_signal_intents = {
            "hours",
            "pricing",
            "duration",
            "location",
            "parking",
            "contact",
            "master",
            "promotions",
            "promo",
        }
        if isinstance(intent_decomp_payload, dict):
            raw_intents = intent_decomp_payload.get("intents")
            if isinstance(raw_intents, list):
                normalized_intents = {
                    item.strip().casefold()
                    for item in raw_intents
                    if isinstance(item, str) and item.strip()
                }
                info_intent_hint = bool(
                    normalized_intents & info_signal_intents
                )
        if not info_intent_hint and info_class_intents:
            normalized_info_intents = {
                item.strip().casefold()
                for item in info_class_intents
                if isinstance(item, str) and item.strip()
            }
            info_intent_hint = bool(normalized_info_intents & info_signal_intents)
        if info_intent_hint:
            direct_info_intent = None
            preferred_info_order = (
                "hours",
                "parking",
                "location",
                "contact",
                "master",
                "promotions",
                "promo",
            )
            normalized_info_class = [
                item.strip().casefold()
                for item in (info_class_intents or [])
                if isinstance(item, str) and item.strip()
            ]
            for candidate in preferred_info_order:
                if candidate in normalized_info_class:
                    direct_info_intent = candidate
                    break
            if not direct_info_intent and isinstance(intent_decomp_payload, dict):
                raw_intents = intent_decomp_payload.get("intents")
                normalized_intents = (
                    {
                        item.strip().casefold()
                        for item in raw_intents
                        if isinstance(item, str) and item.strip()
                    }
                    if isinstance(raw_intents, list)
                    else set()
                )
                for candidate in preferred_info_order:
                    if candidate in normalized_intents:
                        direct_info_intent = candidate
                        break
            if direct_info_intent == "promo":
                direct_info_intent = "promotions"
            if direct_info_intent:
                from app.services.pack_runtime_service import format_reply_from_truth

                info_reply = format_reply_from_truth(
                    direct_info_intent,
                    client_slug=client_slug,
                )
                if isinstance(info_reply, str) and info_reply.strip():
                    bot_response = info_reply.strip()
                    _reset_low_confidence_retry(conversation)
                    _record_decision_trace(
                        conversation,
                        {
                            "stage": "info_class",
                            "decision": "low_confidence_info_fallback",
                            "state": conversation.state,
                            "intent": direct_info_intent,
                        },
                    )
                    _record_message_decision_meta(
                        saved_message,
                        action="reply",
                        intent=direct_info_intent,
                        source="low_confidence_guard",
                        fast_intent=False,
                    )
                    if saved_message:
                        _update_message_decision_metadata(
                            saved_message,
                            {
                                "info_sections": [direct_info_intent],
                                "fact_intents": [direct_info_intent],
                                "low_confidence_guard": "info_fallback",
                            },
                        )
                    bot_response, sent = send_and_save(bot_response)
                    result_message = (
                        "Low-confidence info fallback sent"
                        if sent
                        else "Low-confidence info fallback send failed"
                    )
                    db.commit()
                    return AiResponseOutcome(
                        response=WebhookResponse(
                            success=True,
                            message=result_message,
                            conversation_id=conversation.id,
                            bot_response=bot_response,
                        ),
                        bot_response=bot_response,
                        result_message=result_message,
                        llm_primary_failed=llm_primary_failed,
                        llm_primary_reason=llm_primary_reason,
                    )
            llm_primary_failed = True
            llm_primary_reason = "low_confidence"
        else:
            intent_decomp_explicit_query = None
            raw_source = None
            if isinstance(intent_decomp_payload, dict):
                raw_source = intent_decomp_payload.get("service_query_source")
                raw_query = intent_decomp_payload.get("service_query")
                if (
                    isinstance(raw_query, str)
                    and raw_query.strip()
                    and raw_source != "context"
                ):
                    intent_decomp_explicit_query = raw_query.strip()
            info_only_semantic_skip = bool(
                info_intent_hint
                and not intent_decomp_explicit_query
            )
            if saved_message and info_only_semantic_skip:
                # Preserve the explicit owner-declared info interrupt, but do not
                # let downstream router/controller hints re-open service inference.
                _update_message_decision_metadata(
                    saved_message,
                    {
                        "service_query_resolution_skipped": True,
                        "service_query_resolution_skip_reason": "info_only_interrupt",
                    },
                )
            explicit_service_query = None
            service_query_source = None
            if intent_decomp_explicit_query:
                explicit_service_query = intent_decomp_explicit_query
                if isinstance(raw_source, str) and raw_source.strip():
                    service_query_source = raw_source.strip()
                else:
                    service_query_source = "intent_decomp"
            rag_scores = timing_context.get("rag_scores") if isinstance(timing_context, dict) else None
            rag_attempted = bool(
                timing_context.get("rag_attempted") if isinstance(timing_context, dict) else False
            )
            vector_count = int(rag_scores.get("vector_count") or 0) if isinstance(rag_scores, dict) else 0
            bm25_count = int(rag_scores.get("bm25_count") or 0) if isinstance(rag_scores, dict) else 0
            rag_empty = bool(rag_attempted and vector_count <= 0 and bm25_count <= 0)
            if explicit_service_query and rag_empty:
                from app.services.pack_runtime_service import (
                    _format_service_not_found_reply,
                    load_yaml_truth,
                )

                reply = _format_service_not_found_reply(
                    load_yaml_truth(client_slug),
                    client_slug=client_slug,
                )
                if reply:
                    bot_response = reply
                    _reset_low_confidence_retry(conversation)
                    _record_decision_trace(
                        conversation,
                        {
                            "stage": "truth_gate",
                            "decision": "service_not_found",
                            "state": conversation.state,
                            "service_query": explicit_service_query,
                            "service_query_source": service_query_source,
                        },
                    )
                    if saved_message:
                        llm_used = bool(timing_context.get("llm_used")) if timing_context else False
                        llm_timeout = bool(timing_context.get("llm_timeout")) if timing_context else False
                        llm_cache_hit = bool(timing_context.get("llm_cache_hit")) if timing_context else False
                        _update_message_decision_metadata(
                            saved_message,
                            {
                                "action": "reply",
                                "intent": "service_not_found",
                                "source": "truth_gate",
                                "fact_source": "truth",
                                "fact_intents": ["service_not_found"],
                                "service_query": explicit_service_query,
                                "service_query_source": service_query_source,
                                "fast_intent": False,
                                "llm_primary_used": False,
                                "llm_used": llm_used,
                                "llm_timeout": llm_timeout,
                                "llm_cache_hit": llm_cache_hit,
                            },
                        )
                    bot_response, sent = send_and_save(bot_response)
                    result_message = (
                        "Service semantic not found reply sent"
                        if sent
                        else "Service semantic not found send failed"
                    )
                    db.commit()
                    return AiResponseOutcome(
                        response=WebhookResponse(
                            success=True,
                            message=result_message,
                            conversation_id=conversation.id,
                            bot_response=bot_response,
                        ),
                        bot_response=bot_response,
                        result_message=result_message,
                        llm_primary_failed=llm_primary_failed,
                        llm_primary_reason=llm_primary_reason,
                    )
            if conversation.state == ConversationState.PENDING.value:
                bot_response = MSG_PENDING_LOW_CONFIDENCE
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "ai_response",
                        "decision": "low_confidence_pending",
                        "state": conversation.state,
                    },
                )
                bot_response, sent = send_and_save(bot_response)
                result_message = "Low confidence while pending, responded without re-escalation"
            else:
                context = _get_conversation_context(conversation)
                retry_count = _get_low_confidence_retry_count(context)
                if should_offer_low_confidence_retry(conversation, now):
                    retry_count = 0

                if retry_count < LOW_CONFIDENCE_MAX_RETRIES:
                    clarify_intent = current_goal or "info"
                    context_manager = _get_context_manager(context)
                    if _should_escalate_for_clarify(context_manager, clarify_intent):
                        clarify_count, _ = _get_clarify_attempt_state(
                            context_manager, clarify_intent
                        )
                        _record_context_manager_decision(
                            conversation,
                            saved_message,
                            decision="clarify_limit",
                            updates={
                                "clarify_attempt": {"intent": clarify_intent, "count": clarify_count},
                                "clarify_reason": "low_confidence_retry",
                                "clarify_limit": True,
                            },
                        )
                        clarify_limit_response = _handle_clarify_limit_escalation(
                            db=db,
                            conversation=conversation,
                            user=user,
                            message_text=message_text,
                            saved_message=saved_message,
                            source="ai_response",
                            allow_handover=routing.get("allow_handover_create", False),
                            send_response=send_response,
                            finalize_response=finalize_response,
                        )
                        if clarify_limit_response is not None:
                            return AiResponseOutcome(
                                response=clarify_limit_response,
                                bot_response=None,
                                result_message="Clarify limit escalation handled",
                                llm_primary_failed=llm_primary_failed,
                                llm_primary_reason=llm_primary_reason,
                            )
                        # Defensive fallback: avoid propagating empty response metadata to webhook output.
                        bot_response = MSG_ESCALATED
                        bot_response, sent = send_and_save(bot_response)
                        fallback_message = (
                            "Clarify limit fallback sent"
                            if sent
                            else "Clarify limit fallback failed"
                        )
                        return AiResponseOutcome(
                            response=None,
                            bot_response=bot_response,
                            result_message=fallback_message,
                            llm_primary_failed=llm_primary_failed,
                            llm_primary_reason=llm_primary_reason,
                        )
                    _register_clarify_attempt(
                        conversation=conversation,
                        saved_message=saved_message,
                        intent=clarify_intent,
                        now=now,
                        reason="low_confidence_retry",
                    )
                    bot_response = MSG_LOW_CONFIDENCE_RETRY
                    conversation.retry_offered_at = now
                    context = _set_low_confidence_retry_count(context, retry_count + 1)
                    _set_conversation_context(conversation, context)
                    _record_decision_trace(
                        conversation,
                        {
                            "stage": "ai_response",
                            "decision": "low_confidence_retry",
                            "state": conversation.state,
                            "retry_count": retry_count + 1,
                        },
                    )
                    bot_response, sent = send_and_save(bot_response)
                    result_message = "Low confidence: asked clarification before escalation"
                else:
                    confirmation = {
                        "status": "pending",
                        "asked_at": now.isoformat(),
                        "trigger_type": "low_confidence",
                        "trigger_value": "low_confidence",
                        "user_message": message_text,
                    }
                    context = _set_handover_confirmation(context, confirmation)
                    _set_conversation_context(conversation, context)

                    bot_response = MSG_HANDOVER_CONFIRM
                    _record_decision_trace(
                        conversation,
                        {
                            "stage": "ai_response",
                            "decision": "low_confidence_handover_confirm",
                            "state": conversation.state,
                            "retry_count": retry_count,
                        },
                    )
                    bot_response, sent = send_and_save(bot_response)
                    result_message = (
                        "Low confidence: asked for handover confirmation"
                        if sent
                        else "Low confidence: handover confirmation send failed"
                    )

    elif confidence == "bot_inactive":
        _record_decision_trace(
            conversation,
            {
                "stage": "ai_response",
                "decision": "bot_inactive",
                "state": conversation.state,
            },
        )
        result_message = f"Bot not active (state: {conversation.state})"

    elif response_text:
        bot_response = response_text
        logger.debug(
            f"bot_response: {bot_response[:100] if bot_response else 'None/Empty'}..."
        )
        _reset_low_confidence_retry(conversation)
        llm_primary_used = True
        trace = _attach_llm_cache_flag(
            {
                "stage": "ai_response",
                "decision": "bot_reply",
                "state": conversation.state,
                "confidence": confidence,
            },
            timing_context,
        )
        _record_decision_trace(conversation, trace)
        bot_response, sent = send_and_save(bot_response)
        result_message = "Message sent" if sent else "Failed to send"
    else:
        _record_knowledge_backlog(
            db,
            client_id=client_id,
            conversation_id=conversation.id,
            message=saved_message,
            user_text=message_text,
            miss_type="clarify",
        )
        intent_decomp_explicit_query = None
        info_intent_hint = False
        if isinstance(intent_decomp_payload, dict):
            raw_source = intent_decomp_payload.get("service_query_source")
            raw_query = intent_decomp_payload.get("service_query")
            if (
                isinstance(raw_query, str)
                and raw_query.strip()
                and raw_source != "context"
            ):
                intent_decomp_explicit_query = raw_query.strip()
            raw_intents = intent_decomp_payload.get("intents")
            if isinstance(raw_intents, list):
                normalized_intents = {
                    item.strip().casefold()
                    for item in raw_intents
                    if isinstance(item, str) and item.strip()
                }
                info_intent_hint = bool(
                    normalized_intents & {"hours", "pricing", "duration", "location"}
                )
        has_domain_signal = bool(
            intent_decomp_explicit_query
            or booking_signal
            or info_class_intents
            or info_intent_hint
        )
        context = _get_conversation_context(conversation)
        retry_count = _get_low_confidence_retry_count(context)
        if should_offer_low_confidence_retry(conversation, now):
            retry_count = 0

        if retry_count < LOW_CONFIDENCE_MAX_RETRIES:
            bot_response = MSG_LOW_CONFIDENCE_RETRY
            conversation.retry_offered_at = now
            context = _set_low_confidence_retry_count(context, retry_count + 1)
            _set_conversation_context(conversation, context)
            _record_decision_trace(
                conversation,
                {
                    "stage": "ai_response",
                    "decision": "no_response_retry",
                    "state": conversation.state,
                    "retry_count": retry_count + 1,
                },
            )
            bot_response, sent = send_and_save(bot_response)
            result_message = "No response: asked clarification"
        else:
            confirmation = {
                "status": "pending",
                "asked_at": now.isoformat(),
                "trigger_type": "low_confidence",
                "trigger_value": "low_confidence",
                "user_message": message_text,
            }
            context = _set_handover_confirmation(context, confirmation)
            _set_conversation_context(conversation, context)

            bot_response = MSG_HANDOVER_CONFIRM
            _record_decision_trace(
                conversation,
                {
                    "stage": "ai_response",
                    "decision": "no_response_handover_confirm",
                    "state": conversation.state,
                    "retry_count": retry_count,
                },
            )
            bot_response, sent = send_and_save(bot_response)
            result_message = (
                "No response: asked for handover confirmation"
                if sent
                else "No response: handover confirmation send failed"
            )

    if result_message is None:
        result_message = "AI fallback response skipped"

    if saved_message:
        llm_used = bool(timing_context.get("llm_used")) if timing_context else False
        llm_timeout = bool(timing_context.get("llm_timeout")) if timing_context else False
        llm_cache_hit = bool(timing_context.get("llm_cache_hit")) if timing_context else False
        _update_message_decision_metadata(
            saved_message,
            {
                "action": "ai_response",
                "intent": intent.value if intent else None,
                "source": "llm" if llm_used else "rule",
                "fast_intent": False,
                "llm_primary_used": llm_primary_used,
                "llm_used": llm_used,
                "llm_timeout": llm_timeout,
                "llm_cache_hit": llm_cache_hit,
            },
        )

    return AiResponseOutcome(
        response=None,
        bot_response=bot_response,
        result_message=result_message,
        llm_primary_failed=llm_primary_failed,
        llm_primary_reason=llm_primary_reason,
    )

__all__ = ["_handle_ai_response_action"]
