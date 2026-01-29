"""CTA/quiet-hours/text assembly helpers."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.models import Conversation, Message, User
from app.routers.webhook.trace import (
    _attach_llm_cache_flag,
    _record_decision_trace,
    _record_message_decision_meta,
    _update_message_decision_metadata,
)
from app.schemas.webhook import WebhookResponse


def _maybe_append_booking_cta(
    bot_response: str | None,
    *,
    conversation_state: str,
    allow_booking_flow: bool,
    has_followup: bool = False,
) -> str | None:
    if not _should_append_booking_cta(
        bot_response,
        conversation_state=conversation_state,
        allow_booking_flow=allow_booking_flow,
        has_followup=has_followup,
    ):
        return bot_response
    from . import _legacy as legacy

    return f"{bot_response}\n\n{legacy.MSG_BOOKING_CTA}"


def _collect_response_items(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _merge_response_composer_dicts(base: dict | None, override: dict | None) -> dict[str, Any]:
    merged = dict(base) if isinstance(base, dict) else {}
    if not isinstance(override, dict):
        return merged
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_response_composer_dicts(merged.get(key), value)
        else:
            merged[key] = value
    return merged


@lru_cache(maxsize=16)
def _load_response_composer_config(client_slug: str | None) -> dict[str, Any]:
    from app.services.demo_salon_knowledge import load_yaml_truth

    truth = load_yaml_truth(client_slug)
    if not isinstance(truth, dict):
        return {}
    domain_pack = truth.get("domain_pack") if isinstance(truth.get("domain_pack"), dict) else {}
    client_pack = truth.get("client_pack") if isinstance(truth.get("client_pack"), dict) else {}
    domain_config = domain_pack.get("response_composer") if isinstance(domain_pack, dict) else None
    client_config = client_pack.get("response_composer") if isinstance(client_pack, dict) else None
    return _merge_response_composer_dicts(domain_config, client_config)


def _resolve_response_composer_section(config: dict[str, Any], response_tag: str) -> dict[str, Any]:
    defaults = config.get("defaults") if isinstance(config.get("defaults"), dict) else {}
    variants = config.get("variants") if isinstance(config.get("variants"), dict) else {}
    selected = variants.get(response_tag) if isinstance(variants, dict) else None
    return _merge_response_composer_dicts(defaults, selected)


def _build_response_variant_seed(
    *,
    conversation_id: str | None,
    response_tag: str,
) -> tuple[str, int]:
    base = conversation_id or "conversation"
    key = f"{base}:{response_tag}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    variant_id = digest[:8]
    return variant_id, int(variant_id, 16)


def _select_response_variant(items: list[str], seed: int, offset: int = 0) -> str | None:
    if not items:
        return None
    if len(items) == 1:
        return items[0]
    index = (seed + offset) % len(items)
    return items[index]


def _should_append_booking_cta(
    bot_response: str | None,
    *,
    conversation_state: str,
    allow_booking_flow: bool,
    has_followup: bool,
) -> bool:
    if not bot_response:
        return False
    from . import _legacy as legacy

    if conversation_state != legacy.ConversationState.BOT_ACTIVE.value:
        return False
    if not allow_booking_flow or has_followup:
        return False
    normalized = legacy._normalize_text(bot_response)
    if not normalized or "запис" in normalized:
        return False
    return True


def _compose_fact_response(
    bot_response: str | None,
    *,
    client_slug: str | None,
    conversation_id: str | None,
    response_tag: str,
    conversation_state: str,
    allow_booking_flow: bool,
    has_followup: bool,
    include_ack: bool = True,
    include_next_step: bool = True,
) -> tuple[str | None, dict[str, Any] | None]:
    if not bot_response:
        return bot_response, None
    config = _load_response_composer_config(client_slug)
    if not config:
        return bot_response, None
    response_tag = response_tag.strip() if isinstance(response_tag, str) else ""
    if not response_tag:
        response_tag = "response"
    section = _resolve_response_composer_section(config, response_tag)
    ack_items = _collect_response_items(section.get("ack"))
    next_steps = _collect_response_items(section.get("next_steps"))
    if not ack_items and not next_steps:
        return bot_response, None

    variant_id, seed = _build_response_variant_seed(
        conversation_id=str(conversation_id) if conversation_id else None,
        response_tag=response_tag,
    )
    parts: list[str] = []
    ack_text = None
    if include_ack and ack_items:
        ack_text = _select_response_variant(ack_items, seed, offset=0)
        if ack_text:
            parts.append(ack_text)
    parts.append(bot_response.strip())

    next_step = None
    if include_next_step and _should_append_booking_cta(
        bot_response,
        conversation_state=conversation_state,
        allow_booking_flow=allow_booking_flow,
        has_followup=has_followup,
    ):
        next_step = _select_response_variant(next_steps, seed, offset=7)
        if not next_step:
            from . import _legacy as legacy

            next_step = legacy.MSG_BOOKING_CTA
        if next_step:
            parts.append(next_step)

    composed = "\n\n".join([part for part in parts if part])
    if not composed:
        return bot_response, None
    if composed == bot_response and not ack_text and not next_step:
        return bot_response, None
    return composed, {"response_variant_id": variant_id, "response_variant_tag": response_tag}


def _apply_quiet_hours_notice(text: str, notice: str | None) -> str:
    if not text or not notice:
        return text
    from . import _legacy as legacy

    normalized_text = legacy._normalize_text(text)
    normalized_notice = legacy._normalize_text(notice)
    if normalized_notice and normalized_notice in normalized_text:
        return text
    if "салон закрыт" in normalized_text:
        return text
    return f"{notice}\n\n{text}"


def _apply_evening_greeting(text: str, greeting: str | None) -> str:
    if not text or not greeting:
        return text
    from . import _legacy as legacy

    normalized_text = legacy._normalize_text(text)
    normalized_greeting = legacy._normalize_text(greeting)
    if normalized_greeting and normalized_greeting in normalized_text:
        return text
    return f"{greeting}\n\n{text}"


def _parse_notice_time(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _should_emit_notice(payload: dict | None, *, now: datetime, ttl: timedelta) -> bool:
    if not isinstance(payload, dict):
        return True
    last_sent_at = _parse_notice_time(payload.get("last_sent_at"))
    if not last_sent_at:
        return True
    return (now - last_sent_at) >= ttl


def _finalize_bot_response(
    text: str | None,
    *,
    conversation: Conversation,
    quiet_hours_notice: str | None,
    evening_greeting: str | None = None,
    allow_quiet_hours: bool = True,
    now: datetime | None = None,
) -> str | None:
    if not text:
        return text
    from . import _legacy as legacy

    if not allow_quiet_hours:
        return text
    if conversation.state != legacy.ConversationState.BOT_ACTIVE.value:
        return text
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    from app.routers.webhook.context_manager import _get_conversation_context, _set_conversation_context

    context = _get_conversation_context(conversation)
    context_changed = False

    if quiet_hours_notice:
        if _should_emit_notice(
            context.get(legacy.QUIET_HOURS_NOTICE_KEY),
            now=now,
            ttl=timedelta(minutes=legacy.QUIET_HOURS_NOTICE_TTL_MINUTES),
        ):
            text = _apply_quiet_hours_notice(text, quiet_hours_notice)
            context[legacy.QUIET_HOURS_NOTICE_KEY] = {"last_sent_at": now.isoformat()}
            context_changed = True
    else:
        if context.pop(legacy.QUIET_HOURS_NOTICE_KEY, None) is not None:
            context_changed = True

    if evening_greeting:
        if _should_emit_notice(
            context.get(legacy.EVENING_GREETING_KEY),
            now=now,
            ttl=timedelta(hours=legacy.EVENING_GREETING_TTL_HOURS),
        ):
            text = _apply_evening_greeting(text, evening_greeting)
            context[legacy.EVENING_GREETING_KEY] = {"last_sent_at": now.isoformat()}
            context_changed = True

    if context_changed:
        _set_conversation_context(conversation, context)

    return text


def _send_response(
    *,
    db: Session,
    client_id: Any,
    remote_jid: str,
    text: str,
    idempotency_key: str | None,
    skip_persist: bool,
    log_timing: Callable[[str, float, dict | None], None],
) -> bool:
    from app.adapters.chatflow import ChatFlowAdapter
    from app.ports.messaging import MessageOptions
    from app.services.chatflow_service import get_instance_id

    send_start = time.monotonic()
    # Resolve instance_id
    instance_id = get_instance_id(db, client_id)
    if not instance_id:
        sent = False
    else:
        adapter = ChatFlowAdapter()
        options = MessageOptions(
            instance_id=instance_id,
            idempotency_key=idempotency_key
        )
        result = adapter.send_text(remote_jid, text, options)
        sent = result.is_ok()

        if not sent and skip_persist:
             raise RuntimeError(f"ChatFlow delivery failed: {result.error}")
    log_timing("send_ms", (time.monotonic() - send_start) * 1000, {"send_ok": sent})
    return sent


def _send_and_save(
    *,
    text: str | None,
    db: Session,
    conversation: Conversation,
    client_id: Any,
    finalize_response: Callable[..., str | None],
    record_contract_traces: Callable[[], None],
    send_response: Callable[[str], bool],
    save_message: Callable[..., Message],
    allow_quiet_hours: bool = True,
) -> tuple[str | None, bool]:
    final_text = finalize_response(text, allow_quiet_hours=allow_quiet_hours)
    record_contract_traces()
    save_message(db, conversation.id, client_id, role="assistant", content=final_text)
    sent = send_response(final_text)
    return final_text, sent


def _record_llm_budget_trace(*, conversation: Conversation, timing_context: dict) -> None:
    events = timing_context.get("llm_budget_events") if isinstance(timing_context, dict) else None
    if not isinstance(events, list) or not events:
        return
    for event in events:
        if not isinstance(event, dict):
            continue
        allowed = bool(event.get("allowed", True))
        active = bool(event.get("active"))
        if not active and allowed:
            continue
        scope = event.get("scope") or "unknown"
        trace_payload = {
            "stage": "budget_gate",
            "decision": "allow" if allowed else "deny",
            "llm_scope": scope,
        }
        reason = event.get("reason")
        if isinstance(reason, str) and reason:
            trace_payload["reason"] = reason
        limit = event.get("limit")
        count = event.get("count")
        if isinstance(limit, int):
            trace_payload["budget_limit"] = limit
        if isinstance(count, int):
            trace_payload["budget_count"] = count
        if not allowed:
            trace_payload["llm_degradation_reason"] = "budget_exceeded"
        _record_decision_trace(conversation, trace_payload)
    timing_context["llm_budget_events"] = []


def _record_llm_degradation(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    timing_context: dict,
) -> None:
    reason = timing_context.get("llm_degradation_reason") if isinstance(timing_context, dict) else None
    if not isinstance(reason, str) or not reason:
        return
    if saved_message:
        metadata = saved_message.message_metadata if isinstance(saved_message.message_metadata, dict) else {}
        decision_meta = metadata.get("decision_meta") if isinstance(metadata, dict) else None
        existing_reason = (
            decision_meta.get("llm_degradation_reason") if isinstance(decision_meta, dict) else None
        )
        if not existing_reason:
            _update_message_decision_metadata(
                saved_message, {"llm_degradation_reason": reason}
            )
    if reason != "budget_exceeded":
        _record_decision_trace(
            conversation,
            {
                "stage": "llm_degradation",
                "decision": "fallback",
                "llm_degradation_reason": reason,
            },
        )
    timing_context["llm_degradation_reason"] = None


def _ensure_rag_rewrite(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    message_text: str | None,
    client_slug: str | None,
    client_config: dict | None,
    timing_context: dict,
) -> None:
    if timing_context.get("rag_rewrite_logged"):
        return
    from app.services.ai_service import rewrite_query_for_retrieval

    rag_rewrite_meta = rewrite_query_for_retrieval(
        message_text,
        client_slug=client_slug,
        client_config=client_config,
        timing_context=timing_context,
    )
    _record_llm_budget_trace(conversation=conversation, timing_context=timing_context)
    if not isinstance(rag_rewrite_meta, dict):
        return
    timing_context["rag_rewrite"] = rag_rewrite_meta
    timing_context["rag_rewrite_logged"] = True
    rewrite_used = rag_rewrite_meta.get("rewrite_used") is True
    rewrite_text = rag_rewrite_meta.get("rewrite_text") if rewrite_used else ""
    _record_decision_trace(
        conversation,
        {
            "stage": "rewrite",
            "decision": "used" if rewrite_used else "skipped",
            "rewrite_used": rewrite_used,
            "rewrite_text": rewrite_text,
            "reason": rag_rewrite_meta.get("reason"),
        },
    )
    if saved_message:
        _update_message_decision_metadata(
            saved_message,
            {"rewrite_used": rewrite_used, "rewrite_text": rewrite_text},
        )


def _record_rag_meta(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    timing_context: dict,
) -> None:
    _record_llm_budget_trace(conversation=conversation, timing_context=timing_context)
    _record_llm_degradation(
        conversation=conversation,
        saved_message=saved_message,
        timing_context=timing_context,
    )
    rag_trace = timing_context.get("rag_trace") if isinstance(timing_context, dict) else None
    if isinstance(rag_trace, list) and rag_trace:
        for entry in rag_trace:
            if isinstance(entry, dict):
                _record_decision_trace(conversation, entry)
        timing_context["rag_trace"] = []
    rag_scores = timing_context.get("rag_scores") if isinstance(timing_context, dict) else None
    from . import _legacy as legacy

    rag_scores = legacy._merge_rag_scores(rag_scores if isinstance(rag_scores, dict) else None)
    if saved_message:
        branch_id = None
        knowledge_tag = None
        if isinstance(timing_context, dict):
            branch_id = timing_context.get("branch_id")
            knowledge_tag = timing_context.get("knowledge_tag")
        decision_meta = {}
        if isinstance(saved_message.message_metadata, dict):
            decision_meta = saved_message.message_metadata.get("decision_meta") or {}
        rag_confident, rag_reason = legacy._derive_rag_status(
            rag_scores=rag_scores,
            rag_best_score=(
                timing_context.get("rag_best_score") if isinstance(timing_context, dict) else None
            ),
            rag_attempted=bool(
                timing_context.get("rag_attempted") if isinstance(timing_context, dict) else False
            ),
        )
        meta_updates = {
            "rag_scores": rag_scores,
            "rag_confident": rag_confident,
            "rag_reason": rag_reason,
        }
        if branch_id and "branch_id" not in decision_meta:
            meta_updates["branch_id"] = branch_id
        if knowledge_tag and "knowledge_tag" not in decision_meta:
            meta_updates["knowledge_tag"] = knowledge_tag
        _update_message_decision_metadata(
            saved_message,
            meta_updates,
        )


def _maybe_apply_consult_return(
    *,
    conversation: Conversation,
    saved_message: Message | None,
    bot_response: str | None,
    consult_return_pending: bool,
    consult_return_prompt: str | None,
    consult_context: dict | None,
    reason: str,
) -> str | None:
    if not consult_return_pending:
        return bot_response
    from app.routers.webhook.context_manager import _apply_consult_return

    return _apply_consult_return(
        conversation=conversation,
        saved_message=saved_message,
        bot_response=bot_response,
        consult_return_prompt=consult_return_prompt,
        consult_context=consult_context,
        reason=reason,
    )


@dataclass(frozen=True)
class LlmPrimaryOutcome:
    response: WebhookResponse | None
    llm_primary_result: Any | None
    llm_primary_failed: bool
    llm_primary_reason: str | None


@dataclass(frozen=True)
class AiResponseOutcome:
    response: WebhookResponse | None
    bot_response: str | None
    result_message: str | None
    llm_primary_failed: bool
    llm_primary_reason: str | None


@dataclass(frozen=True)
class ConsultFlowResult:
    response: WebhookResponse | None
    consult_intent: bool | None
    consult_topic: str | None
    consult_question: str | None
    intent_decomp_payload: dict[str, Any] | None


def _record_class_router_trace_from_result(
    *,
    conversation: Conversation,
    class_router_result: dict | None,
) -> None:
    if not isinstance(class_router_result, dict):
        return
    from . import _legacy as legacy

    controller_meta = class_router_result.get("controller") if isinstance(class_router_result, dict) else None
    controller_used = bool(controller_meta.get("used")) if isinstance(controller_meta, dict) else False
    controller_attempted = bool(controller_meta.get("attempted")) if isinstance(controller_meta, dict) else False
    controller_fallback = bool(controller_meta.get("fallback")) if isinstance(controller_meta, dict) else False
    controller_low_confidence = (
        bool(controller_meta.get("low_confidence")) if isinstance(controller_meta, dict) else False
    )
    controller_used_reason = (
        controller_meta.get("used_reason") if isinstance(controller_meta, dict) else None
    )
    controller_confidence = (
        controller_meta.get("confidence") if isinstance(controller_meta, dict) else None
    )
    controller_error = controller_meta.get("error") if isinstance(controller_meta, dict) else None
    controller_goal = controller_meta.get("goal") if isinstance(controller_meta, dict) else None
    trace_payload = {
        "stage": "class_router",
        "classes": class_router_result.get("classes"),
        "intents": class_router_result.get("intents"),
        "carryover_intents": class_router_result.get("carryover_intents"),
        "in_signals": class_router_result.get("in_signals"),
        "out_signals": class_router_result.get("out_signals"),
        "anchors_in_hits": class_router_result.get("anchors_in_hits"),
        "anchors_out_hits": class_router_result.get("anchors_out_hits"),
        "out_of_domain_signal": class_router_result.get("out_of_domain_signal"),
        "carryover_class": class_router_result.get("carryover_class"),
        "carryover_info_sections": class_router_result.get("carryover_info_sections"),
        "router_fallback_reason": class_router_result.get("router_fallback_reason"),
        "controller_fallback_reason": class_router_result.get("controller_fallback_reason"),
        "router": class_router_result.get("router"),
        "controller": controller_meta,
        "controller_used": controller_used,
        "controller_attempted": controller_attempted,
        "controller_fallback": controller_fallback,
        "controller_low_confidence": controller_low_confidence,
        "controller_used_reason": controller_used_reason,
        "controller_confidence": controller_confidence,
        "controller_error": controller_error,
        "controller_goal": controller_goal,
    }
    trace_payload.update(
        legacy._router_observability_updates_from_class_router(class_router_result)
    )
    _record_decision_trace(conversation, trace_payload)


def _handle_consult_flow(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str | None,
    saved_message: Message | None,
    client_slug: str | None,
    policy_type: str | None,
    policy_pack: dict | None,
    policy_handler: dict | None,
    routing: dict,
    bypass_domain_flows: bool,
    booking_wants_flow: bool,
    booking_active: bool,
    booking_signal: bool,
    intent_decomp_set: set[str],
    consult_intent: bool | None,
    consult_topic: str | None,
    consult_question: str | None,
    intent_decomp_payload: dict[str, Any] | None,
    intent_decomp_service_query: str | None,
    info_class_intents: set[str],
    intent_queue_followup: str | None,
    current_goal: str | None,
    expected_reply_type: str | None,
    consult_context: dict | None,
    message_count: int,
    now: datetime,
    timing_context: dict | None,
    client_config: dict | None,
    send_and_save: Callable[..., tuple[str, bool]],
    record_escalation_metric: Callable[[str], None],
) -> ConsultFlowResult:
    from app.services.ai_service import generate_consult_controller_output
    from app.services.consult_pack_service import (
        build_consult_pack_reply,
        get_consult_topic,
        load_consult_playbook,
        select_consult_question,
    )
    from app.services.demo_salon_knowledge import (
        DemoSalonDecision,
        get_demo_salon_service_decision,
    )
    from app.services.knowledge_service import resolve_consult_topic_candidates
    from app.services.knowledge_snapshot_consumer import (
        build_consult_snapshot,
        build_consult_snapshot_shadow,
        get_consult_snapshot_mode,
        is_consult_snapshot_allowlisted,
        is_snapshot_consumer_enabled,
    )

    from . import _legacy as legacy

    def _build_consult_class_router_result() -> dict[str, Any]:
        controller_output = legacy._build_controller_meta_output(error="skipped")
        controller_output["class"] = "consult"
        controller_output["goal"] = "consult"
        controller_output["confidence"] = max(legacy.CONTROLLER_CONFIDENCE_THRESHOLD, 0.5)
        controller_output = legacy._ensure_controller_output_meta(
            controller_output, error="skipped"
        )
        router_state = {
            "used": True,
            "attempted": False,
            "fallback": False,
            "confidence": controller_output["confidence"],
            "error": "skipped",
            "fallback_reason": None,
            "signal_class": legacy._resolve_controller_signal_class(
                intent_decomp_set=intent_decomp_set,
                booking_signal=booking_signal,
            ),
            "signal_match": False,
            "used_reason": "deterministic",
            "output": controller_output,
            "sla": None,
        }
        return legacy._resolve_class_router_result(
            info_intents=info_class_intents,
            info_meta=None,
            booking_signal=booking_signal,
            class_carryover=None,
            domain_intent=legacy.DomainIntent.UNKNOWN,
            domain_meta=None,
            router_state=router_state,
        )

    if not (routing.get("allow_bot_reply") and not bypass_domain_flows and message_text):
        return ConsultFlowResult(
            response=None,
            consult_intent=consult_intent,
            consult_topic=consult_topic,
            consult_question=consult_question,
            intent_decomp_payload=intent_decomp_payload,
        )

    consult_decision = None
    consult_candidate = None
    consult_meta: dict[str, Any] = {}
    consult_signal = False
    consult_flow_decision = None
    consult_short_circuit = False
    consult_short_circuit_reason = None
    consult_short_circuit_service = None
    consult_llm_used = False
    service_availability_used = False
    service_availability_decision = None
    consult_context_active = bool(current_goal == "consult")
    if not consult_context_active and isinstance(consult_context, dict):
        if consult_context.get("topic") or consult_context.get("question") or consult_context.get("questions"):
            consult_context_active = True
    consult_interrupt_intents = (
        intent_decomp_set & legacy.CONSULT_INTERRUPT_INTENTS if intent_decomp_set else set()
    )
    consult_interrupt_text = False
    if message_text:
        normalized = legacy.normalize_for_matching(message_text)
        if normalized:
            if (
                ("совмещ" in normalized or "в один день" in normalized)
                and "чистк" in normalized
                and "пилинг" in normalized
            ):
                consult_interrupt_text = True
            elif any(
                token in normalized
                for token in (
                    "инструмент",
                    "стерилиз",
                    "линз",
                    "подготов",
                    "перед процедур",
                )
            ):
                consult_interrupt_text = True
    consult_interrupt_signal = bool(
        consult_interrupt_intents or consult_interrupt_text or booking_signal
    )
    if consult_context_active and consult_interrupt_signal and not consult_intent:
        consult_context_active = False
    elif consult_context_active and not consult_intent:
        consult_intent = True
        if isinstance(intent_decomp_payload, dict):
            intent_decomp_payload = dict(intent_decomp_payload)
            intent_decomp_payload["consult_intent"] = True
    if consult_context_active and not consult_topic and isinstance(consult_context, dict):
        context_topic = consult_context.get("topic")
        if isinstance(context_topic, str) and context_topic.strip():
            consult_topic = context_topic.strip()
            if isinstance(consult_context.get("question"), str) and not consult_question:
                consult_question = consult_context.get("question").strip() or None
            if isinstance(intent_decomp_payload, dict):
                intent_decomp_payload = dict(intent_decomp_payload)
                intent_decomp_payload["consult_topic"] = consult_topic
                if consult_question:
                    intent_decomp_payload["consult_question"] = consult_question
    consult_intent_signal = bool(consult_intent or consult_context_active)
    booking_goal_locked = bool(
        booking_wants_flow
        or booking_active
        or booking_signal
        or current_goal == "booking"
        or (
            expected_reply_type
            in {
                legacy.EXPECTED_REPLY_SERVICE,
                legacy.EXPECTED_REPLY_TIME,
                legacy.EXPECTED_REPLY_NAME,
            }
            and not consult_intent
        )
    )
    consult_blocked = bool(booking_wants_flow or booking_active or booking_signal)
    if consult_intent or consult_context_active:
        consult_blocked = False
    elif intent_decomp_set & {"booking", "pricing", "duration", "location", "hours"}:
        consult_blocked = True

    if message_text and policy_type == "demo_salon" and routing.get("allow_truth_gate_reply"):
        from app.services.demo_salon_knowledge import _normalize_text

        normalized = _normalize_text(message_text)
        aftercare_trigger = bool(
            normalized
            and "гель лак" in normalized
            and any(token in normalized for token in ("ухаж", "продл", "держ", "нос", "срок"))
        )
        if aftercare_trigger:
            from app.services.demo_salon_knowledge import get_demo_salon_decision

            truth_decision = get_demo_salon_decision(
                message_text,
                client_slug=client_slug,
                intent_decomp=intent_decomp_payload,
            )
            if (
                truth_decision
                and truth_decision.action == "reply"
                and truth_decision.intent == "aftercare_gel_lac"
            ):
                bot_response = truth_decision.response
                legacy._reset_low_confidence_retry(conversation)
                trace_payload = {
                    "stage": "truth_gate",
                    "decision": truth_decision.action,
                    "intent": truth_decision.intent,
                    "state": conversation.state,
                    "booking_wants_flow": booking_wants_flow,
                    "policy_type": policy_type,
                    "consult_override": True,
                }
                if isinstance(getattr(truth_decision, "meta", None), dict):
                    trace_payload.update(truth_decision.meta)
                _record_decision_trace(conversation, trace_payload)
                _record_message_decision_meta(
                    saved_message,
                    action=truth_decision.action,
                    intent=truth_decision.intent,
                    source="truth_gate",
                    fast_intent=False,
                )
                if saved_message and isinstance(getattr(truth_decision, "meta", None), dict):
                    _update_message_decision_metadata(saved_message, truth_decision.meta)
                bot_response, sent = send_and_save(bot_response)
                result_message = "Truth gate override reply sent"
                if not sent:
                    result_message = f"{result_message}; response_send=failed"
                db.commit()
                return ConsultFlowResult(
                    response=WebhookResponse(
                        success=True,
                        message=result_message,
                        conversation_id=conversation.id,
                        bot_response=bot_response,
                    ),
                    consult_intent=consult_intent,
                    consult_topic=consult_topic,
                    consult_question=consult_question,
                    intent_decomp_payload=intent_decomp_payload,
                )

    consult_flow_override = None
    consult_pack_used = False
    consult_selector = None
    consult_confidence = None
    consult_risk_class = None
    consult_guard: dict[str, Any] | None = None
    consult_pack_intent_signal = bool(consult_intent or consult_context_active)
    consult_snapshot_result = None
    consult_snapshot_meta: dict[str, Any] | None = None
    consult_snapshot_mode = "shadow"
    consult_snapshot_source = None
    consult_snapshot_cutover = False

    def _build_consult_snapshot_trace(result, *, mode: str) -> dict[str, Any]:
        error = result.error or result.playbook_error
        trace: dict[str, Any] = {
            "stage": "consult_snapshot",
            "decision": "ok" if not error else "error",
            "mode": mode,
            "consult_playbook_present": result.playbook_present,
        }
        if result.snapshot_id:
            trace["snapshot_id"] = result.snapshot_id
        if result.version_id:
            trace["version_id"] = result.version_id
        if result.sha256:
            trace["sha256"] = result.sha256
        if result.error:
            trace["error"] = result.error
        if result.playbook_error:
            trace["consult_playbook_error"] = result.playbook_error
        return trace

    def _build_consult_snapshot_meta(result, *, mode: str, source: str | None) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "consult_snapshot_mode": mode,
            "consult_snapshot_source": source or mode,
            "consult_snapshot_playbook_present": result.playbook_present,
        }
        if result.snapshot_id:
            meta["consult_snapshot_id"] = result.snapshot_id
        if result.version_id:
            meta["consult_snapshot_version_id"] = result.version_id
        if result.sha256:
            meta["consult_snapshot_sha256"] = result.sha256
        if result.error:
            meta["consult_snapshot_error"] = result.error
        if result.playbook_error:
            meta["consult_snapshot_playbook_error"] = result.playbook_error
        return meta

    playbook = None
    _pack_error = None

    def _resolve_branch_id() -> str | None:
        branch_id = None
        if isinstance(timing_context, dict):
            branch_id = timing_context.get("branch_id")
        if not branch_id and conversation.branch_id:
            branch_id = conversation.branch_id
        return str(branch_id) if branch_id else None

    if consult_pack_intent_signal:
        consult_snapshot_mode = get_consult_snapshot_mode()
        consult_snapshot_cutover = bool(
            consult_snapshot_mode in {"fallback", "strict"}
            and is_consult_snapshot_allowlisted(client_slug)
        )
        if consult_snapshot_cutover:
            consult_snapshot_result = build_consult_snapshot(
                db,
                client_id=str(conversation.client_id) if conversation.client_id else None,
                branch_id=_resolve_branch_id(),
                client_slug=client_slug,
            )
            consult_snapshot_source = "snapshot"
            consult_snapshot_meta = _build_consult_snapshot_meta(
                consult_snapshot_result,
                mode=consult_snapshot_mode,
                source=consult_snapshot_source,
            )
            legacy._record_decision_trace(
                conversation,
                _build_consult_snapshot_trace(
                    consult_snapshot_result,
                    mode=consult_snapshot_mode,
                ),
            )
            if consult_snapshot_result.playbook:
                playbook = consult_snapshot_result.playbook
            elif consult_snapshot_mode == "fallback":
                playbook, _pack_error = load_consult_playbook(client_slug)
                consult_snapshot_source = "fallback" if playbook else "missing"
                consult_snapshot_meta["consult_snapshot_source"] = consult_snapshot_source
            else:
                consult_snapshot_source = "missing"
                consult_snapshot_meta["consult_snapshot_source"] = consult_snapshot_source
                consult_guard = {"reason": "snapshot_missing"}
                if message_text:
                    clarify_prompt = legacy.MSG_EXPECTED_SERVICE_OFF_TOPIC
                    clarify_count = legacy._register_clarify_attempt(
                        conversation=conversation,
                        saved_message=saved_message,
                        intent="consult",
                        now=now,
                        reason="snapshot_missing",
                    )
                    consult_meta = {
                        "consult_intent": True,
                        "consult_question": consult_question or message_text,
                        "consult_guard": consult_guard,
                        "clarify_attempt": {"intent": "consult", "count": clarify_count},
                        "clarify_reason": "snapshot_missing",
                        "consult_source": "pack",
                        "source": "pack",
                    }
                    if not booking_goal_locked or consult_intent_signal:
                        context = legacy._get_conversation_context(conversation)
                        context = legacy._set_expected_reply_context(
                            conversation=conversation,
                            saved_message=saved_message,
                            context=context,
                            expected_reply_type=legacy.EXPECTED_REPLY_SERVICE,
                            reason="snapshot_missing",
                            now=now,
                        )
                        consult_meta["expected_reply_type"] = legacy.EXPECTED_REPLY_SERVICE
                    consult_decision = DemoSalonDecision(
                        action="reply",
                        response=clarify_prompt,
                        intent="consult_reply",
                        meta=consult_meta,
                    )
                    consult_flow_override = "consult_clarify"
                    consult_signal = True
                    consult_intent = True
                    consult_pack_used = True
        elif is_snapshot_consumer_enabled():
            consult_snapshot_result = build_consult_snapshot_shadow(
                db,
                client_id=str(conversation.client_id) if conversation.client_id else None,
                branch_id=_resolve_branch_id(),
                client_slug=client_slug,
            )
            consult_snapshot_meta = _build_consult_snapshot_meta(
                consult_snapshot_result,
                mode="shadow",
                source="shadow",
            )
            legacy._record_decision_trace(
                conversation,
                _build_consult_snapshot_trace(
                    consult_snapshot_result,
                    mode="shadow",
                ),
            )

    if consult_pack_intent_signal and playbook is None and not consult_snapshot_cutover:
        playbook, _pack_error = load_consult_playbook(client_slug)

    def _missing_fact_requirements(requirements: list[str]) -> list[str]:
        missing: list[str] = []
        for requirement in requirements:
            if requirement == "policy_present":
                if not isinstance(policy_pack, dict) or not policy_pack:
                    missing.append(requirement)
            elif requirement in {"price_allowed", "duration_allowed"}:
                if not isinstance(policy_pack, dict) or not policy_pack:
                    missing.append(requirement)
            elif requirement == "service_exists":
                missing.append(requirement)
        return missing

    if message_text and consult_pack_intent_signal:
        if playbook:
            short_circuit_service = (
                str(intent_decomp_service_query).strip()
                if isinstance(intent_decomp_service_query, str)
                else ""
            )
            price_or_duration_signal = False
            if message_text:
                from app.services.demo_salon_knowledge import (
                    _has_duration_signal,
                    _has_price_signal,
                    _normalize_text,
                )

                normalized_message = _normalize_text(message_text)
                price_or_duration_signal = _has_price_signal(
                    normalized_message,
                    message_text,
                ) or _has_duration_signal(normalized_message, message_text)
            explicit_info_signal = price_or_duration_signal
            explicit_info_intent = bool(
                explicit_info_signal
                or info_class_intents & {"location", "hours"}
            )
            service_matcher = None
            handler_override = legacy._get_policy_handler(None, client_slug=client_slug)
            if isinstance(handler_override, dict):
                service_matcher = handler_override.get("service_matcher")
            if service_matcher is None and isinstance(policy_handler, dict):
                service_matcher = policy_handler.get("service_matcher")
            if short_circuit_service and service_availability_decision is None and price_or_duration_signal:
                if service_matcher:
                    service_availability_decision = service_matcher(
                        message_text,
                        client_slug=client_slug,
                        intent_decomp=intent_decomp_payload,
                    )
                elif policy_type == "demo_salon":
                    service_availability_decision = get_demo_salon_service_decision(
                        message_text,
                        client_slug=client_slug,
                        intent_decomp=intent_decomp_payload,
                    )
            if (
                consult_intent
                and short_circuit_service
                and service_availability_decision is None
                and service_matcher
            ):
                service_availability_decision = service_matcher(
                    message_text,
                    client_slug=client_slug,
                    intent_decomp=intent_decomp_payload,
                )
            topic_map = {topic.id: topic for topic in playbook.topics}
            topic_candidates = resolve_consult_topic_candidates(
                message_text,
                playbook.topics,
                client_slug=client_slug,
                top_k=5,
                timing_context=timing_context,
            )
            if topic_candidates:
                legacy._record_decision_trace(
                    conversation,
                    {
                        "stage": "consult_topic_resolver",
                        "decision": "rank",
                        "candidates": topic_candidates[:3],
                    },
                )
            controller_result = generate_consult_controller_output(
                message_text=message_text,
                topics=playbook.topics,
                candidates=topic_candidates,
                consult_question=consult_question,
                timing_context=timing_context,
            )
            controller_output = controller_result.value if controller_result.ok else None
            controller_trace = {
                "stage": "consult_controller",
                "decision": "ok" if controller_result.ok else "error",
                "error": controller_result.error,
                "error_code": controller_result.error_code,
            }
            if controller_output:
                controller_trace.update(
                    {
                        "intent": controller_output.intent,
                        "topic_id": controller_output.topic_id,
                        "confidence": controller_output.confidence,
                        "risk_class": controller_output.risk_class,
                        "actions": list(controller_output.actions),
                    }
                )
            legacy._record_decision_trace(conversation, controller_trace)

            consult_pack_topic_id = None
            if controller_output and controller_output.topic_id in topic_map:
                consult_pack_topic_id = controller_output.topic_id
                consult_selector = "controller"
                consult_confidence = controller_output.confidence
                consult_risk_class = controller_output.risk_class
            elif topic_candidates:
                best_candidate = topic_candidates[0]
                score = best_candidate.get("score")
                if isinstance(score, (int, float)) and score >= 0.6:
                    consult_pack_topic_id = best_candidate.get("topic_id")
                    consult_selector = "semantic"
                    consult_confidence = float(score)
            if not consult_pack_topic_id and consult_topic and consult_topic in topic_map:
                consult_pack_topic_id = consult_topic
                consult_selector = "intent_decomp"

            if explicit_info_intent:
                consult_short_circuit = True
                consult_short_circuit_reason = "explicit_info"
                consult_short_circuit_service = short_circuit_service
                consult_pack_used = True
                consult_flow_trace = {
                    "stage": "consult_flow",
                    "decision": "short_circuit",
                    "state": conversation.state,
                    "reason": consult_short_circuit_reason,
                    "explicit_info": True,
                    "service_query": short_circuit_service,
                }
                if consult_pack_topic_id:
                    consult_flow_trace["consult_playbook_id"] = consult_pack_topic_id
                if consult_question:
                    consult_flow_trace["consult_question"] = consult_question
                legacy._record_decision_trace(conversation, consult_flow_trace)

            guard_reason = None
            non_consult_intent = (
                controller_output.intent
                if controller_output and controller_output.intent != "consult"
                else None
            )
            if controller_output:
                if controller_output.risk_class in {"high", "blocked"}:
                    guard_reason = "risk_high"
                elif "handoff" in controller_output.actions:
                    guard_reason = "needs_human"
            if non_consult_intent and not guard_reason and not consult_intent:
                consult_intent = False
                if isinstance(intent_decomp_payload, dict):
                    intent_decomp_payload = dict(intent_decomp_payload)
                    intent_decomp_payload["consult_intent"] = False
                consult_pack_used = True
            else:
                if not guard_reason and not consult_pack_topic_id:
                    guard_reason = "unknown_topic"
                topic = (
                    get_consult_topic(playbook, consult_pack_topic_id)
                    if consult_pack_topic_id
                    else None
                )
                if not guard_reason and topic:
                    missing_requirements = _missing_fact_requirements(topic.fact_requirements)
                    if missing_requirements:
                        guard_reason = "missing_fact"
                        consult_guard = {"missing": missing_requirements}
                if not guard_reason and consult_confidence is not None and consult_confidence < 0.6:
                    guard_reason = "low_confidence"

                if guard_reason:
                    consult_guard = consult_guard or {}
                    consult_guard["reason"] = guard_reason

                should_escalate = False
                if guard_reason in {"risk_high", "needs_human"}:
                    should_escalate = True
                elif guard_reason in {"unknown_topic", "missing_fact", "low_confidence"}:
                    policy_escalate = (
                        playbook.default_policy.escalate_on_low_confidence
                        if playbook.default_policy
                        else False
                    )
                    if policy_escalate and guard_reason in {"unknown_topic", "low_confidence"}:
                        should_escalate = True
                    if topic and guard_reason in topic.escalate_when:
                        should_escalate = True

                if guard_reason and not should_escalate:
                    context = legacy._get_conversation_context(conversation)
                    context_manager = legacy._get_context_manager(context)
                    clarify_limit = (
                        topic.clarify_limit
                        if topic
                        else playbook.default_policy.clarify_limit
                        if playbook.default_policy and playbook.default_policy.clarify_limit is not None
                        else legacy.CLARIFY_MAX_ATTEMPTS
                    )
                    clarify_count, _ = legacy._get_clarify_attempt_state(context_manager, "consult")
                    if clarify_count >= clarify_limit:
                        consult_guard = consult_guard or {}
                        consult_guard["reason"] = "clarify_limit_exceeded"
                        should_escalate = True

                if guard_reason and should_escalate:
                    consult_meta = {
                        "consult_intent": True,
                        "consult_topic": consult_pack_topic_id,
                        "consult_topic_id": consult_pack_topic_id,
                        "consult_question": consult_question or message_text,
                        "consult_selector": consult_selector,
                        "consult_confidence": consult_confidence,
                        "consult_risk_class": consult_risk_class,
                        "consult_guard": consult_guard,
                        "consult_controller_used": controller_result.ok,
                        "consult_controller_error": controller_result.error or controller_result.error_code,
                        "consult_playbook_id": consult_pack_topic_id,
                        "consult_source": "pack",
                        "source": "pack",
                    }
                    consult_decision = DemoSalonDecision(
                        action="escalate",
                        response=legacy.MSG_ESCALATED,
                        intent="consult_escalate",
                        meta=consult_meta,
                    )
                    consult_signal = True
                    consult_intent = True
                    if consult_pack_topic_id:
                        consult_topic = consult_pack_topic_id
                    consult_pack_used = True
                elif guard_reason:
                    clarify_prompt = None
                    if topic:
                        clarify_prompt = select_consult_question(
                            playbook,
                            topic_id=topic.id,
                            conversation_id=str(conversation.id),
                        )
                    if not clarify_prompt:
                        clarify_prompt = legacy.MSG_EXPECTED_SERVICE_OFF_TOPIC
                    clarify_count = legacy._register_clarify_attempt(
                        conversation=conversation,
                        saved_message=saved_message,
                        intent="consult",
                        now=now,
                        reason="consult_pack",
                    )
                    consult_meta = {
                        "consult_intent": True,
                        "consult_topic": consult_pack_topic_id,
                        "consult_topic_id": consult_pack_topic_id,
                        "consult_question": consult_question or message_text,
                        "consult_questions": [clarify_prompt],
                        "consult_selector": consult_selector,
                        "consult_confidence": consult_confidence,
                        "consult_risk_class": consult_risk_class,
                        "consult_guard": consult_guard,
                        "clarify_attempt": {"intent": "consult", "count": clarify_count},
                        "clarify_reason": guard_reason,
                        "consult_controller_used": controller_result.ok,
                        "consult_controller_error": controller_result.error or controller_result.error_code,
                        "consult_playbook_id": consult_pack_topic_id,
                        "consult_source": "pack",
                        "source": "pack",
                    }
                    if not booking_goal_locked or consult_intent_signal:
                        context = legacy._get_conversation_context(conversation)
                        context = legacy._set_expected_reply_context(
                            conversation=conversation,
                            saved_message=saved_message,
                            context=context,
                            expected_reply_type=legacy.EXPECTED_REPLY_SERVICE,
                            reason="consult_clarify",
                            now=now,
                        )
                        consult_meta["expected_reply_type"] = legacy.EXPECTED_REPLY_SERVICE
                    consult_decision = DemoSalonDecision(
                        action="reply",
                        response=clarify_prompt,
                        intent="consult_reply",
                        meta=consult_meta,
                    )
                    consult_flow_override = "consult_clarify"
                    consult_signal = True
                    consult_intent = True
                    if consult_pack_topic_id:
                        consult_topic = consult_pack_topic_id
                    consult_pack_used = True
                elif consult_pack_topic_id:
                    pack_decision = build_consult_pack_reply(
                        playbook=playbook,
                        topic_id=consult_pack_topic_id,
                        conversation_id=str(conversation.id),
                        consult_question=consult_question,
                    )
                    if pack_decision:
                        consult_meta = (
                            pack_decision.meta
                            if isinstance(pack_decision.meta, dict)
                            else {}
                        )
                        consult_meta = dict(consult_meta)
                        consult_meta.update(
                            {
                                "consult_selector": consult_selector,
                                "consult_confidence": consult_confidence,
                                "consult_risk_class": consult_risk_class,
                                "consult_guard": consult_guard,
                                "consult_controller_used": controller_result.ok,
                                "consult_controller_error": controller_result.error
                                or controller_result.error_code,
                                "consult_source": "pack",
                            }
                        )
                        consult_decision = DemoSalonDecision(
                            action="reply",
                            response=pack_decision.response,
                            intent=pack_decision.intent,
                            meta=consult_meta,
                        )
                        consult_signal = True
                        consult_intent = True
                        if consult_pack_topic_id:
                            consult_topic = consult_pack_topic_id
                        consult_pack_used = True
    if consult_decision:
        consult_meta = consult_decision.meta if isinstance(consult_decision.meta, dict) else {}
        consult_meta = dict(consult_meta)
        consult_signal = True
    if consult_intent and not consult_short_circuit:
        consult_signal = True
        consult_meta["consult_intent"] = True
        if consult_topic:
            consult_meta["consult_topic"] = consult_topic
        if consult_question:
            consult_meta["consult_question"] = consult_question
    short_circuit_intents = (
        consult_interrupt_intents - {"booking"} if consult_interrupt_intents else set()
    )
    if (
        consult_decision
        and consult_decision.action == "reply"
        and consult_pack_used
        and short_circuit_intents
    ):
        consult_short_circuit = True
        consult_short_circuit_reason = "consult_overrides_info"
        consult_short_circuit_service = consult_meta.get("service_query")
    if consult_decision and consult_snapshot_meta:
        consult_meta.update(consult_snapshot_meta)
    if service_availability_decision and service_availability_decision.action == "reply":
        service_reply = service_availability_decision.response
        if service_reply:
            service_availability_used = True
            service_meta = (
                service_availability_decision.meta
                if isinstance(service_availability_decision.meta, dict)
                else {}
            )
            service_fact_source = service_meta.get("fact_source")
            if service_fact_source in {"truth", "service_matcher", "multi_truth"}:
                if service_fact_source == "truth":
                    matcher_trace = {
                        "stage": "truth_gate",
                        "decision": service_availability_decision.action,
                        "intent": service_availability_decision.intent,
                        "state": conversation.state,
                    }
                elif service_fact_source == "service_matcher":
                    matcher_trace = {
                        "stage": "service_matcher",
                        "decision": service_availability_decision.intent,
                        "state": conversation.state,
                    }
                else:
                    matcher_trace = {
                        "stage": "multi_truth",
                        "decision": "reply",
                        "state": conversation.state,
                    }
                matcher_trace.update(service_meta)
                legacy._record_decision_trace(conversation, matcher_trace)
            consult_meta.setdefault("source", "service_availability")
            consult_meta["service_decision_intent"] = service_availability_decision.intent
            if service_meta:
                consult_meta.setdefault("service_query", service_meta.get("service_query"))
                consult_meta.setdefault("service_query_source", service_meta.get("service_query_source"))
                # Preserve fact metadata from service_matcher replies for downstream contracts/tests.
                for key in (
                    "fact_source",
                    "fact_intents",
                    "info_sections",
                    "info_combined",
                    "question_type",
                    "question_type_score",
                    "service_query_score",
                    "price_item",
                    "duration_item",
                    "info_signals",
                    "anchor_intents",
                    "anchor_hits",
                    "anchor_boost",
                ):
                    value = service_meta.get(key)
                    if value is not None and consult_meta.get(key) is None:
                        consult_meta[key] = value
            if consult_decision and consult_decision.action == "reply":
                combined_response = legacy._append_followup(consult_decision.response, service_reply)
                consult_decision = DemoSalonDecision(
                    action="reply",
                    response=combined_response,
                    intent=consult_decision.intent or "consult_reply",
                    meta=consult_meta,
                )
            else:
                consult_decision = DemoSalonDecision(
                    action="reply",
                    response=service_reply,
                    intent="consult_reply",
                    meta=consult_meta,
                )
                consult_signal = True
    if consult_meta and consult_meta.get("fact_source") is None:
        if consult_llm_used:
            consult_meta["fact_source"] = "llm"
        elif consult_meta.get("consult_source") == "pack" or consult_meta.get("source") == "pack":
            consult_meta["fact_source"] = "pack"
    if consult_intent_signal and not consult_signal and not consult_short_circuit:
        consult_signal = True

    if consult_signal and not consult_short_circuit:
        context = legacy._get_conversation_context(conversation)
        context_manager = legacy._get_context_manager(context)
        if consult_flow_override:
            consult_flow_decision = consult_flow_override
        elif consult_decision:
            if consult_short_circuit:
                consult_flow_decision = "short_circuit"
            else:
                consult_flow_decision = (
                    "consult_escalate" if consult_decision.action == "escalate" else "consult_reply"
                )
            if consult_decision.action == "reply" and consult_llm_used:
                consult_flow_decision = "consult_llm"
        elif legacy._should_escalate_for_clarify(context_manager, "consult"):
            clarify_count, _ = legacy._get_clarify_attempt_state(context_manager, "consult")
            legacy._record_context_manager_decision(
                conversation,
                saved_message,
                decision="clarify_limit",
                updates={
                    "clarify_attempt": {"intent": "consult", "count": clarify_count},
                    "clarify_reason": "consult_no_service",
                    "clarify_limit": True,
                },
            )
            consult_meta["clarify_limit"] = True
            consult_meta["clarify_reason"] = "consult_no_service"
            consult_meta["clarify_attempt"] = {"intent": "consult", "count": clarify_count}
            consult_decision = DemoSalonDecision(
                action="escalate",
                response=legacy.MSG_ESCALATED,
                intent="consult_no_service",
                meta=consult_meta,
            )
            consult_flow_decision = "consult_escalate"
        else:
            clarify_count = legacy._register_clarify_attempt(
                conversation=conversation,
                saved_message=saved_message,
                intent="consult",
                now=now,
                reason="consult",
            )
            consult_meta["consult_questions"] = [legacy.MSG_EXPECTED_SERVICE_OFF_TOPIC]
            consult_meta["clarify_attempt"] = {"intent": "consult", "count": clarify_count}
            consult_meta["clarify_reason"] = "consult"
            if booking_goal_locked and not consult_intent_signal:
                consult_meta["clarify_suppressed"] = True
            else:
                context = legacy._get_conversation_context(conversation)
                context = legacy._set_expected_reply_context(
                    conversation=conversation,
                    saved_message=saved_message,
                    context=context,
                    expected_reply_type=legacy.EXPECTED_REPLY_SERVICE,
                    reason="consult_clarify",
                    now=now,
                )
                consult_meta["expected_reply_type"] = legacy.EXPECTED_REPLY_SERVICE
            consult_decision = DemoSalonDecision(
                action="reply",
                response=legacy.MSG_EXPECTED_SERVICE_OFF_TOPIC,
                intent="consult_reply",
                meta=consult_meta,
            )
            consult_flow_decision = "consult_clarify"

    if consult_decision:
        class_router_result = _build_consult_class_router_result()
        _record_class_router_trace_from_result(
            conversation=conversation,
            class_router_result=class_router_result,
        )
        if consult_flow_decision:
            consult_flow_trace = {
                "stage": "consult_flow",
                "decision": consult_flow_decision,
                "state": conversation.state,
            }
            if consult_flow_decision == "consult_clarify":
                consult_flow_trace["expected_reply_type"] = legacy.EXPECTED_REPLY_SERVICE
                consult_flow_trace["reason"] = "consult_clarify"
            elif consult_flow_decision == "consult_escalate":
                guard_reason = None
                if isinstance(consult_meta, dict):
                    guard = consult_meta.get("consult_guard")
                    if isinstance(guard, dict):
                        guard_reason = guard.get("reason")
                consult_flow_trace["reason"] = guard_reason or "consult_no_service"
            elif consult_flow_decision == "short_circuit":
                consult_flow_trace["reason"] = consult_short_circuit_reason or "consult_short_circuit"
                if consult_short_circuit_service:
                    consult_flow_trace["service_query"] = consult_short_circuit_service
            elif consult_flow_decision == "consult_llm":
                consult_flow_trace["reason"] = "consult_llm"
            elif service_availability_used and not consult_candidate:
                consult_flow_trace["reason"] = "service_availability"
            else:
                consult_flow_trace["reason"] = "consult_pack"
            consult_playbook_id = consult_meta.get("consult_playbook_id")
            if consult_playbook_id:
                consult_flow_trace["consult_playbook_id"] = consult_playbook_id
            consult_variant_id = consult_meta.get("consult_variant_id")
            if consult_variant_id:
                consult_flow_trace["consult_variant_id"] = consult_variant_id
            legacy._record_decision_trace(conversation, consult_flow_trace)
        if consult_decision.action == "reply":
            if not booking_goal_locked:
                context = legacy._get_conversation_context(conversation)
                context_manager = legacy._get_context_manager(context)
                context_manager["current_goal"] = "consult"
                context_manager = legacy._set_consult_context(
                    context_manager,
                    consult_meta=consult_meta,
                    message_count=message_count,
                )
                context = legacy._set_context_manager(context, context_manager)
                legacy._set_conversation_context(conversation, context)
                context, memory = legacy._update_session_memory_goal(
                    context, active_goal="consult", now=now
                )
                legacy._set_conversation_context(conversation, context)
                legacy._record_session_memory_update(
                    conversation,
                    saved_message,
                    memory=memory,
                    reason="active_goal",
                )
                consult_trace = {
                    "stage": "consult_context",
                    "decision": "set",
                    "current_goal": "consult",
                    "ttl": legacy.CONSULT_CONTEXT_TTL_MESSAGES,
                }
                consult_topic = consult_meta.get("consult_topic")
                if consult_topic:
                    consult_trace["consult_topic"] = consult_topic
                legacy._record_decision_trace(conversation, consult_trace)
                if saved_message:
                    legacy._update_message_decision_metadata(saved_message, {"current_goal": "consult"})
        consult_trace = {
            "stage": "consult",
            "decision": consult_decision.action,
            "intent": consult_decision.intent,
            "state": conversation.state,
        }
        consult_trace.update(consult_meta)
        legacy._record_decision_trace(conversation, consult_trace)
        legacy._record_message_decision_meta(
            saved_message,
            action=consult_decision.action,
            intent=consult_decision.intent,
            source="consult",
            fast_intent=False,
        )
        if saved_message and consult_meta:
            legacy._update_message_decision_metadata(saved_message, consult_meta)

        if consult_decision.action == "escalate":
            bot_response = consult_decision.response or legacy.MSG_ESCALATED
            legacy._reset_low_confidence_retry(conversation)

            result_message = "Consult escalation"
            _, reused, telegram_sent = legacy._reuse_active_handover(
                db=db,
                conversation=conversation,
                user=user,
                message=message_text,
                source="consult",
                intent=consult_decision.intent,
            )
            if reused:
                result_message = f"Consult reuse, telegram={'sent' if telegram_sent else 'failed'}"
            elif conversation.state == legacy.ConversationState.BOT_ACTIVE.value and routing.get(
                "allow_handover_create"
            ):
                record_escalation_metric("intent")
                result = legacy.escalate_to_pending(
                    db=db,
                    conversation=conversation,
                    user_message=message_text,
                    trigger_type="intent",
                    trigger_value=consult_decision.intent or "consult",
                )
                if result.ok:
                    handover = result.value
                    telegram_sent = legacy.send_telegram_notification(
                        db=db,
                        handover=handover,
                        conversation=conversation,
                        user=user,
                        message=message_text,
                    )
                    result_message = f"Consult escalation, telegram={'sent' if telegram_sent else 'failed'}"
                else:
                    result_message = f"Consult escalation failed: {result.error}"
            else:
                result_message = "Consult escalation skipped (already pending)"

            bot_response, sent = send_and_save(bot_response)
            if not sent:
                result_message = f"{result_message}; response_send=failed"
            db.commit()
            return ConsultFlowResult(
                response=WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                ),
                consult_intent=consult_intent,
                consult_topic=consult_topic,
                consult_question=consult_question,
                intent_decomp_payload=intent_decomp_payload,
            )

        bot_response = consult_decision.response
        bot_response = legacy._combine_sidecar(bot_response, intent_queue_followup)
        booking_followup = None
        if booking_goal_locked and consult_flow_decision != "consult_clarify":
            if expected_reply_type == legacy.EXPECTED_REPLY_SERVICE:
                booking_followup = legacy.MSG_BOOKING_ASK_SERVICE
            elif expected_reply_type == legacy.EXPECTED_REPLY_TIME:
                booking_followup = legacy.MSG_BOOKING_ASK_DATETIME
            elif expected_reply_type == legacy.EXPECTED_REPLY_NAME:
                booking_followup = legacy.MSG_BOOKING_ASK_NAME
            else:
                context = legacy._get_conversation_context(conversation)
                context_manager = legacy._get_context_manager(context)
                refusal_flags = (
                    context_manager.get("refusal_flags") if isinstance(context_manager, dict) else None
                )
                booking_state = legacy._get_booking_context(context)
                _, booking_followup = legacy._next_booking_prompt(
                    booking_state,
                    refusal_flags=refusal_flags,
                )
        if booking_followup:
            consult_meta["booking_followup"] = True
        bot_response = legacy._append_followup(bot_response, booking_followup)
        bot_response = _maybe_append_booking_cta(
            bot_response,
            conversation_state=conversation.state,
            allow_booking_flow=routing["allow_booking_flow"],
            has_followup=bool(booking_followup or intent_queue_followup),
        )
        legacy._reset_low_confidence_retry(conversation)
        bot_response, sent = send_and_save(bot_response)
        result_message = "Consult reply sent" if sent else "Consult reply send failed"
        db.commit()
        return ConsultFlowResult(
            response=WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            ),
            consult_intent=consult_intent,
            consult_topic=consult_topic,
            consult_question=consult_question,
            intent_decomp_payload=intent_decomp_payload,
        )

    return ConsultFlowResult(
        response=None,
        consult_intent=consult_intent,
        consult_topic=consult_topic,
        consult_question=consult_question,
        intent_decomp_payload=intent_decomp_payload,
    )


def _handle_llm_primary(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str | None,
    saved_message: Message | None,
    client_slug: str | None,
    policy_type: str | None,
    policy_pack: dict | None,
    routing: dict,
    append_user_message: bool,
    timing_context: dict,
    client_config: dict | None,
    intent: Any,
    multi_intent_other_followup: str | None,
    send_and_save: Callable[..., tuple[str | None, bool]],
    record_escalation_metric: Callable[[str], None],
) -> LlmPrimaryOutcome:
    from . import _legacy as legacy

    llm_primary_result = None
    llm_primary_failed = False
    llm_primary_reason = None

    if not routing.get("allow_bot_reply"):
        return LlmPrimaryOutcome(
            response=None,
            llm_primary_result=llm_primary_result,
            llm_primary_failed=llm_primary_failed,
            llm_primary_reason=llm_primary_reason,
        )

    _ensure_rag_rewrite(
        conversation=conversation,
        saved_message=saved_message,
        message_text=message_text,
        client_slug=client_slug,
        client_config=client_config,
        timing_context=timing_context,
    )
    llm_primary_result = legacy.generate_bot_response(
        db,
        conversation,
        message_text,
        client_slug,
        append_user_message=append_user_message,
        pending_hint=conversation.state == legacy.ConversationState.PENDING.value,
        timing_context=timing_context,
    )
    _record_rag_meta(
        conversation=conversation,
        saved_message=saved_message,
        timing_context=timing_context,
    )
    if not llm_primary_result.ok:
        llm_primary_failed = True
        llm_primary_reason = "ai_error"
        return LlmPrimaryOutcome(
            response=None,
            llm_primary_result=llm_primary_result,
            llm_primary_failed=llm_primary_failed,
            llm_primary_reason=llm_primary_reason,
        )

    response_text, confidence = llm_primary_result.value
    if confidence == "bot_inactive":
        llm_primary_failed = True
        llm_primary_reason = "bot_inactive"
        return LlmPrimaryOutcome(
            response=None,
            llm_primary_result=llm_primary_result,
            llm_primary_failed=llm_primary_failed,
            llm_primary_reason=llm_primary_reason,
        )
    if response_text and confidence != "low_confidence":
        blocked_topics = legacy._detect_llm_guard_topics(
            response_text,
            policy_type=policy_type,
            policy_pack=policy_pack,
        )
        if blocked_topics:
            bot_response = legacy.MSG_ESCALATED
            legacy._reset_low_confidence_retry(conversation)

            result_message = "LLM guard escalation"
            _, reused, telegram_sent = legacy._reuse_active_handover(
                db=db,
                conversation=conversation,
                user=user,
                message=message_text,
                source="llm_guard",
                intent="llm_guard",
            )
            if reused:
                result_message = f"LLM guard reuse, telegram={'sent' if telegram_sent else 'failed'}"
            elif conversation.state == legacy.ConversationState.BOT_ACTIVE.value and routing.get(
                "allow_handover_create"
            ):
                record_escalation_metric("intent")
                result = legacy.escalate_to_pending(
                    db=db,
                    conversation=conversation,
                    user_message=message_text,
                    trigger_type="intent",
                    trigger_value="llm_guard",
                )
                if result.ok:
                    handover = result.value
                    telegram_sent = legacy.send_telegram_notification(
                        db=db,
                        handover=handover,
                        conversation=conversation,
                        user=user,
                        message=message_text,
                    )
                    result_message = f"LLM guard escalation, telegram={'sent' if telegram_sent else 'failed'}"
                else:
                    result_message = f"LLM guard escalation failed: {result.error}"
            else:
                result_message = "LLM guard escalation skipped (already pending)"

            _record_decision_trace(
                conversation,
                {
                    "stage": "llm_guard",
                    "decision": "blocked_topics",
                    "state": conversation.state,
                    "blocked_topics": blocked_topics,
                },
            )
            if saved_message:
                llm_used = bool(timing_context.get("llm_used")) if timing_context else False
                llm_timeout = bool(timing_context.get("llm_timeout")) if timing_context else False
                llm_cache_hit = bool(timing_context.get("llm_cache_hit")) if timing_context else False
                _update_message_decision_metadata(
                    saved_message,
                    {
                        "action": "escalate",
                        "intent": "llm_guard",
                        "source": "llm_guard",
                        "fast_intent": False,
                        "llm_primary_used": False,
                        "llm_used": llm_used,
                        "llm_timeout": llm_timeout,
                        "llm_cache_hit": llm_cache_hit,
                    },
                )
            bot_response, sent = send_and_save(bot_response, allow_quiet_hours=False)
            if not sent:
                result_message = f"{result_message}; response_send=failed"
            db.commit()
            return LlmPrimaryOutcome(
                response=WebhookResponse(
                    success=True,
                    message=result_message,
                    conversation_id=conversation.id,
                    bot_response=bot_response,
                ),
                llm_primary_result=llm_primary_result,
                llm_primary_failed=llm_primary_failed,
                llm_primary_reason=llm_primary_reason,
            )

        bot_response = response_text
        bot_response = legacy._combine_sidecar(bot_response, multi_intent_other_followup)
        legacy._reset_low_confidence_retry(conversation)
        trace = _attach_llm_cache_flag(
            {
                "stage": "ai_response",
                "decision": "bot_reply",
                "state": conversation.state,
                "confidence": confidence,
                "llm_primary_used": True,
            },
            timing_context,
        )
        _record_decision_trace(conversation, trace)
        bot_response, sent = send_and_save(bot_response)
        result_message = "Message sent" if sent else "Failed to send"
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
                    "llm_primary_used": True,
                    "llm_used": llm_used,
                    "llm_timeout": llm_timeout,
                    "llm_cache_hit": llm_cache_hit,
                },
            )
        db.commit()
        return LlmPrimaryOutcome(
            response=WebhookResponse(
                success=True,
                message=result_message,
                conversation_id=conversation.id,
                bot_response=bot_response,
            ),
            llm_primary_result=llm_primary_result,
            llm_primary_failed=llm_primary_failed,
            llm_primary_reason=llm_primary_reason,
        )

    llm_primary_failed = True
    llm_primary_reason = "low_confidence" if confidence == "low_confidence" else "no_response"
    return LlmPrimaryOutcome(
        response=None,
        llm_primary_result=llm_primary_result,
        llm_primary_failed=llm_primary_failed,
        llm_primary_reason=llm_primary_reason,
    )


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
    from . import _legacy as legacy

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
        gen_result = legacy.generate_bot_response(
            db,
            conversation,
            message_text,
            client_slug,
            append_user_message=append_user_message,
            pending_hint=conversation.state == legacy.ConversationState.PENDING.value,
            timing_context=timing_context,
        )
        _record_rag_meta(
            conversation=conversation,
            saved_message=saved_message,
            timing_context=timing_context,
        )

    if not gen_result.ok:
        bot_response = legacy.MSG_AI_ERROR
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
        legacy._record_knowledge_backlog(
            db,
            client_id=client_id,
            conversation_id=conversation.id,
            message=saved_message,
            user_text=message_text,
            miss_type=miss_type,
        )
        semantic_result = None
        rewrite_query = None
        info_intent_hint = False
        if isinstance(intent_decomp_payload, dict):
            raw_intents = intent_decomp_payload.get("intents")
            if isinstance(raw_intents, list):
                normalized_intents = {
                    item.strip().casefold()
                    for item in raw_intents
                    if isinstance(item, str) and item.strip()
                }
                info_intent_hint = bool(normalized_intents & {"hours", "pricing", "duration"})
        if info_intent_hint:
            llm_primary_failed = True
            llm_primary_reason = "low_confidence"
        else:
            router_meta = None
            router_output = None
            router_output_class = None
            if isinstance(class_router_result, dict):
                router_meta = class_router_result.get("router")
                if isinstance(router_meta, dict):
                    router_output = router_meta.get("output")
                    if isinstance(router_output, dict):
                        router_output_class = router_output.get("class")
            if (
                router_output_class == "out_of_domain"
                and not (class_router_result.get("in_signals") or [])
                and not expected_reply_shortcircuit
            ):
                bot_response = legacy.OUT_OF_DOMAIN_RESPONSE
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "out_of_domain",
                        "decision": "router_low_confidence",
                        "state": conversation.state,
                    },
                )
                _record_message_decision_meta(
                    saved_message,
                    action="out_of_domain",
                    intent="out_of_domain",
                    source="router_low_confidence",
                    fast_intent=False,
                )
                bot_response, sent = send_and_save(bot_response)
                result_message = (
                    "Router OOD reply sent" if sent else "Router OOD reply send failed"
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
            if out_of_domain_signal and not expected_reply_shortcircuit:
                bot_response = legacy.OUT_OF_DOMAIN_RESPONSE
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "out_of_domain",
                        "decision": "domain_anchor",
                        "state": conversation.state,
                    },
                )
                _record_message_decision_meta(
                    saved_message,
                    action="out_of_domain",
                    intent="out_of_domain",
                    source="domain_anchor",
                    fast_intent=False,
                )
                bot_response, sent = send_and_save(bot_response)
                result_message = (
                    "Domain anchor OOD reply sent"
                    if sent
                    else "Domain anchor OOD reply send failed"
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
            if legacy._looks_like_time_only_request(message_text):
                bot_response = legacy.MSG_EXPECTED_SERVICE_OFF_TOPIC
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "time_only_guard",
                        "decision": "service_clarify",
                        "state": conversation.state,
                    },
                )
                _record_message_decision_meta(
                    saved_message,
                    action="reply",
                    intent="service_clarify",
                    source="time_only_guard",
                    fast_intent=False,
                )
                if saved_message:
                    _update_message_decision_metadata(
                        saved_message, {"time_only_guard": True}
                    )
                bot_response, sent = send_and_save(bot_response)
                result_message = (
                    "Time-only guard reply sent" if sent else "Time-only guard send failed"
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
            if not out_of_domain_signal:
                explicit_service_hint = None
                if message_text and client_slug:
                    explicit_service_hint = legacy._extract_service_hint(
                        message_text, client_slug
                    )
                intent_decomp_explicit_query = None
                if isinstance(intent_decomp_payload, dict):
                    raw_source = intent_decomp_payload.get("service_query_source")
                    raw_query = intent_decomp_payload.get("service_query")
                    if (
                        isinstance(raw_query, str)
                        and raw_query.strip()
                        and raw_source != "context"
                    ):
                        intent_decomp_explicit_query = raw_query.strip()
                controller_service_query = None
                for state_key in ("router", "controller"):
                    state = (
                        class_router_result.get(state_key)
                        if isinstance(class_router_result, dict)
                        else None
                    )
                    if not isinstance(state, dict):
                        continue
                    output = state.get("output")
                    if not isinstance(output, dict):
                        continue
                    slots = output.get("slots")
                    if not isinstance(slots, dict):
                        continue
                    candidate = slots.get("service_query")
                    if isinstance(candidate, str) and candidate.strip():
                        controller_service_query = candidate.strip()
                        break
                in_signals = class_router_result.get("in_signals") or []
                anchors_in_hits = int(class_router_result.get("anchors_in_hits") or 0)
                service_semantic_allowed = bool(
                    explicit_service_hint
                    or intent_decomp_explicit_query
                    or controller_service_query
                    or booking_signal
                    or info_intent_hint
                    or in_signals
                    or anchors_in_hits > 0
                )
                if not service_semantic_allowed:
                    bot_response = legacy.OUT_OF_DOMAIN_RESPONSE
                    _record_decision_trace(
                        conversation,
                        {
                            "stage": "out_of_domain",
                            "decision": "service_semantic_guard",
                            "state": conversation.state,
                        },
                    )
                    _record_message_decision_meta(
                        saved_message,
                        action="out_of_domain",
                        intent="out_of_domain",
                        source="service_semantic_guard",
                        fast_intent=False,
                    )
                    if saved_message:
                        _update_message_decision_metadata(
                            saved_message,
                            {
                                "service_semantic_match_skipped": True,
                                "service_semantic_match_skip_reason": "low_signal",
                            },
                        )
                    bot_response, sent = send_and_save(bot_response)
                    result_message = (
                        "Service semantic guard reply sent"
                        if sent
                        else "Service semantic guard reply send failed"
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
                semantic_result = legacy.semantic_service_match(message_text, client_slug)
                if not semantic_result:
                    rewrite_query = legacy.rewrite_for_service_match(
                        message_text,
                        client_slug,
                        client_config=client_config,
                        timing_context=timing_context,
                    )
                    _record_llm_budget_trace(
                        conversation=conversation,
                        timing_context=timing_context,
                    )
                    if rewrite_query:
                        semantic_result = legacy.semantic_service_match(rewrite_query, client_slug)
            if semantic_result:
                rewrite_used = bool(rewrite_query)
                bot_response = semantic_result.response
                legacy._reset_low_confidence_retry(conversation)
                _record_decision_trace(
                    conversation,
                    {
                        "stage": "service_semantic_matcher",
                        "decision": semantic_result.action,
                        "state": conversation.state,
                        "score": semantic_result.score,
                        "canonical_name": semantic_result.canonical_name,
                        "suggestions": semantic_result.suggestions or [],
                        "rewrite_used": rewrite_used,
                        "rewrite_query": rewrite_query,
                    },
                )
                if saved_message:
                    llm_used = bool(timing_context.get("llm_used")) if timing_context else False
                    llm_timeout = bool(timing_context.get("llm_timeout")) if timing_context else False
                    llm_cache_hit = bool(timing_context.get("llm_cache_hit")) if timing_context else False
                    _update_message_decision_metadata(
                        saved_message,
                        {
                            "action": semantic_result.action,
                            "intent": "service_semantic",
                            "source": "service_semantic_matcher",
                            "service_semantic_score": semantic_result.score,
                            "service_semantic_rewrite_used": rewrite_used,
                            "service_semantic_rewrite_query": rewrite_query,
                            "fast_intent": False,
                            "llm_primary_used": False,
                            "llm_used": llm_used,
                            "llm_timeout": llm_timeout,
                            "llm_cache_hit": llm_cache_hit,
                        },
                    )
                bot_response, sent = send_and_save(bot_response)
                result_message = (
                    "Service semantic matcher reply sent"
                    if sent
                    else "Service semantic matcher send failed"
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
            if conversation.state == legacy.ConversationState.PENDING.value:
                bot_response = legacy.MSG_PENDING_LOW_CONFIDENCE
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
                context = legacy._get_conversation_context(conversation)
                retry_count = legacy._get_low_confidence_retry_count(context)
                if legacy.should_offer_low_confidence_retry(conversation, now):
                    retry_count = 0

                if retry_count < legacy.LOW_CONFIDENCE_MAX_RETRIES:
                    clarify_intent = current_goal or "info"
                    context_manager = legacy._get_context_manager(context)
                    if legacy._should_escalate_for_clarify(context_manager, clarify_intent):
                        clarify_count, _ = legacy._get_clarify_attempt_state(
                            context_manager, clarify_intent
                        )
                        legacy._record_context_manager_decision(
                            conversation,
                            saved_message,
                            decision="clarify_limit",
                            updates={
                                "clarify_attempt": {"intent": clarify_intent, "count": clarify_count},
                                "clarify_reason": "low_confidence_retry",
                                "clarify_limit": True,
                            },
                        )
                        return AiResponseOutcome(
                            response=legacy._handle_clarify_limit_escalation(
                                db=db,
                                conversation=conversation,
                                user=user,
                                message_text=message_text,
                                saved_message=saved_message,
                                source="ai_response",
                                allow_handover=routing.get("allow_handover_create", False),
                                send_response=send_response,
                                finalize_response=finalize_response,
                            ),
                            bot_response=None,
                            result_message=None,
                            llm_primary_failed=llm_primary_failed,
                            llm_primary_reason=llm_primary_reason,
                        )
                    legacy._register_clarify_attempt(
                        conversation=conversation,
                        saved_message=saved_message,
                        intent=clarify_intent,
                        now=now,
                        reason="low_confidence_retry",
                    )
                    bot_response = legacy.MSG_LOW_CONFIDENCE_RETRY
                    conversation.retry_offered_at = now
                    context = legacy._set_low_confidence_retry_count(context, retry_count + 1)
                    legacy._set_conversation_context(conversation, context)
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
                    context = legacy._set_handover_confirmation(context, confirmation)
                    legacy._set_conversation_context(conversation, context)

                    bot_response = legacy.MSG_HANDOVER_CONFIRM
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
        legacy.logger.debug(
            f"bot_response: {bot_response[:100] if bot_response else 'None/Empty'}..."
        )
        legacy._reset_low_confidence_retry(conversation)
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
        legacy._record_knowledge_backlog(
            db,
            client_id=client_id,
            conversation_id=conversation.id,
            message=saved_message,
            user_text=message_text,
            miss_type="clarify",
        )
        explicit_service_hint = None
        if message_text and client_slug:
            explicit_service_hint = legacy._extract_service_hint(message_text, client_slug)
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
            explicit_service_hint
            or intent_decomp_explicit_query
            or booking_signal
            or info_class_intents
            or info_intent_hint
            or int(class_router_result.get("anchors_in_hits") or 0) > 0
        )
        if not has_domain_signal and not expected_reply_shortcircuit:
            bot_response = legacy.OUT_OF_DOMAIN_RESPONSE
            _record_decision_trace(
                conversation,
                {
                    "stage": "out_of_domain",
                    "decision": "no_response_guard",
                    "state": conversation.state,
                },
            )
            _record_message_decision_meta(
                saved_message,
                action="out_of_domain",
                intent="out_of_domain",
                source="no_response_guard",
                fast_intent=False,
            )
            bot_response, sent = send_and_save(bot_response)
            result_message = (
                "No-response OOD reply sent" if sent else "No-response OOD reply send failed"
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
        context = legacy._get_conversation_context(conversation)
        retry_count = legacy._get_low_confidence_retry_count(context)
        if legacy.should_offer_low_confidence_retry(conversation, now):
            retry_count = 0

        if retry_count < legacy.LOW_CONFIDENCE_MAX_RETRIES:
            bot_response = legacy.MSG_LOW_CONFIDENCE_RETRY
            conversation.retry_offered_at = now
            context = legacy._set_low_confidence_retry_count(context, retry_count + 1)
            legacy._set_conversation_context(conversation, context)
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
            context = legacy._set_handover_confirmation(context, confirmation)
            legacy._set_conversation_context(conversation, context)

            bot_response = legacy.MSG_HANDOVER_CONFIRM
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


__all__ = [
    "AiResponseOutcome",
    "ConsultFlowResult",
    "LlmPrimaryOutcome",
    "_apply_quiet_hours_notice",
    "_compose_fact_response",
    "_ensure_rag_rewrite",
    "_finalize_bot_response",
    "_handle_ai_response_action",
    "_handle_consult_flow",
    "_handle_llm_primary",
    "_maybe_apply_consult_return",
    "_maybe_append_booking_cta",
    "_record_rag_meta",
    "_send_and_save",
    "_send_response",
]
