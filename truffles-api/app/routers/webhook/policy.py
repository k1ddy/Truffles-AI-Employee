"""LAW/policy gates and policy-pack-driven detection helpers."""

from __future__ import annotations

import re
import time

from sqlalchemy.orm import Session

from app.models import Client, Conversation, Message, User
from app.schemas.webhook import WebhookResponse
from app.services.demo_salon_knowledge import DemoSalonDecision
from app.services.intent_service import Intent

_POLICY_SECTIONS = (
    "payment_info",
    "reschedule",
    "cancel",
    "medical",
    "legal",
    "complaint",
    "discounts",
    "refund",
)

_HARD_LAW_INTENT_MAP = {
    "payment": "payment_info",
    "reschedule": "reschedule",
    "cancel_request": "cancel",
    "cancel": "cancel",
    "medical": "medical",
    "legal": "legal",
    "complaint": "complaint",
    "refund": "refund",
}

_SECTION_GUARD_TOPIC = {
    "payment_info": "payment",
    "medical": "medical",
    "complaint": "complaint",
    "discounts": "discount",
    "refund": "refund",
}

_SECTION_DEFAULT_INTENT = {
    "payment_info": "payment",
    "reschedule": "reschedule",
    "cancel": "cancel_request",
    "medical": "medical",
    "legal": "legal",
    "complaint": "complaint",
    "discounts": "discounts",
    "refund": "refund",
}


def _looks_like_policy_pack(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    if value.get("hard_law") or value.get("guard_topics"):
        return True
    return any(key in value for key in _POLICY_SECTIONS)


def _extract_policy_pack_from_config(config: dict | None) -> dict | None:
    if not isinstance(config, dict):
        return None
    direct = config.get("policy_pack")
    if _looks_like_policy_pack(direct):
        return dict(direct)
    client_pack = config.get("client_pack")
    if isinstance(client_pack, dict):
        policy = client_pack.get("policy")
        if _looks_like_policy_pack(policy):
            return dict(policy)
    legacy = config.get("policy")
    if _looks_like_policy_pack(legacy):
        return dict(legacy)
    return None


def _get_routing_policy(state: str) -> dict[str, bool]:
    from . import _legacy as legacy

    policy = legacy.ROUTING_MATRIX.get(state)
    if policy:
        return dict(policy)
    return {
        "allow_booking_flow": False,
        "allow_truth_gate_reply": False,
        "allow_handover_create": False,
        "allow_bot_reply": False,
    }


def _should_run_booking_flow(
    policy: dict[str, bool],
    *,
    booking_active: bool,
    booking_signal: bool,
) -> bool:
    return bool(policy.get("allow_booking_flow")) and (booking_active or booking_signal)


def _should_run_truth_gate(policy: dict[str, bool], booking_wants_flow: bool) -> bool:
    return bool(policy.get("allow_truth_gate_reply")) and not booking_wants_flow


def _should_run_demo_truth_gate(policy: dict[str, bool], booking_wants_flow: bool) -> bool:
    return _should_run_truth_gate(policy, booking_wants_flow)


def _should_escalate_to_pending(policy: dict[str, bool], intent: Intent) -> bool:
    from . import _legacy as legacy

    return bool(policy.get("allow_handover_create")) and legacy.should_escalate(intent)


def _load_policy_pack(*, policy_type: str | None, client_slug: str | None) -> dict | None:
    from app.services.demo_salon_knowledge import load_policy_pack

    slug = policy_type or client_slug
    if not slug:
        return None
    policy_pack = load_policy_pack(slug)
    return policy_pack if isinstance(policy_pack, dict) and policy_pack else None


def _get_policy_pack(client: Client | None, *, client_slug: str | None) -> dict | None:
    if not client or not isinstance(client.config, dict):
        return None
    policy_pack = _extract_policy_pack_from_config(client.config)
    if policy_pack:
        return policy_pack
    policy_type = _get_policy_type(client, client_slug=client_slug)
    if policy_type:
        return _load_policy_pack(policy_type=policy_type, client_slug=client_slug)
    return None




def _policy_str_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def _get_policy_section(policy_pack: dict | None, key: str) -> dict | None:
    if not isinstance(policy_pack, dict):
        return None
    section = policy_pack.get(key)
    return section if isinstance(section, dict) else None


def _get_guard_topics(policy_pack: dict | None) -> dict[str, list[str]]:
    guard_topics = policy_pack.get("guard_topics") if isinstance(policy_pack, dict) else None
    if not isinstance(guard_topics, dict):
        return {}
    topics: dict[str, list[str]] = {}
    for topic, keywords in guard_topics.items():
        normalized = _policy_str_list(keywords)
        if normalized:
            topics[str(topic)] = normalized
    return topics


def _matches_policy_keywords(normalized: str, keywords: list[str]) -> bool:
    for keyword in keywords:
        if not keyword:
            continue
        if len(keyword) <= 3:
            if re.search(rf"\\b{re.escape(keyword)}\\b", normalized):
                return True
            continue
        if keyword in normalized:
            return True
    return False


def _matches_policy_section(normalized: str, section: dict | None) -> bool:
    if not section:
        return False
    keywords = _policy_str_list(section.get("keywords") if isinstance(section, dict) else None)
    if keywords and _matches_policy_keywords(normalized, keywords):
        return True
    return False


def _resolve_policy_intent(section_key: str, section: dict | None) -> str | None:
    if section:
        intent = section.get("intent")
        if isinstance(intent, str) and intent.strip():
            return intent.strip()
    return _SECTION_DEFAULT_INTENT.get(section_key)


def _resolve_policy_risk_level(section: dict | None) -> str | None:
    if not section:
        return None
    risk_level = section.get("risk_level")
    if isinstance(risk_level, str) and risk_level.strip():
        return risk_level.strip()
    return None


def _resolve_hard_law_sections(policy_pack: dict | None) -> list[str]:
    hard_law = _get_policy_section(policy_pack, "hard_law")
    sections = _policy_str_list(hard_law.get("sections") if isinstance(hard_law, dict) else None)
    if sections:
        return [section for section in sections if section in _POLICY_SECTIONS]
    intents = _policy_str_list(hard_law.get("intents") if isinstance(hard_law, dict) else None)
    resolved: list[str] = []
    for intent in intents:
        mapped = _HARD_LAW_INTENT_MAP.get(intent.casefold())
        if mapped and mapped not in resolved:
            resolved.append(mapped)
    if resolved:
        return resolved
    return list(dict.fromkeys(_HARD_LAW_INTENT_MAP.values()))


def _detect_policy_section(
    message_text: str | None,
    *,
    policy_pack: dict | None,
    sections: list[str],
) -> tuple[str, dict | None] | None:
    from . import _legacy as legacy

    normalized = legacy._normalize_text(message_text)
    if not normalized or not sections:
        return None
    for section_key in sections:
        if section_key == "medical" and "подруг" in normalized and "у меня" not in normalized:
            continue
        section = _get_policy_section(policy_pack, section_key)
        if _matches_policy_section(normalized, section):
            return section_key, section
        guard_topic = _SECTION_GUARD_TOPIC.get(section_key)
        if guard_topic:
            guard_keywords = _get_guard_topics(policy_pack).get(guard_topic)
            if guard_keywords and _matches_policy_keywords(normalized, guard_keywords):
                return section_key, section
    return None


def _detect_hard_law_match(
    message_text: str | None,
    *,
    policy_pack: dict | None,
    intent_hints: list[str] | None = None,
) -> tuple[str, dict | None] | None:
    from . import _legacy as legacy

    hard_law_sections = _resolve_hard_law_sections(policy_pack)
    match = _detect_policy_section(
        message_text,
        policy_pack=policy_pack,
        sections=hard_law_sections,
    )
    if match:
        section_key, section = match
        if section_key == "complaint":
            normalized = legacy._normalize_text(message_text)
            if normalized and legacy._contains_any(
                normalized,
                ["без задерж", "без опозд", "без опоз"],
            ):
                return None
        if section_key == "medical":
            normalized = legacy._normalize_text(message_text)
            consult_override = _policy_str_list(
                section.get("consult_override_keywords") if isinstance(section, dict) else None
            )
            if normalized and consult_override and legacy._contains_any(normalized, consult_override):
                return None
        return match
    if not intent_hints:
        return None
    intent_set = {intent.strip().casefold() for intent in intent_hints if isinstance(intent, str)}
    if not intent_set:
        return None
    for intent in intent_set:
        mapped = _HARD_LAW_INTENT_MAP.get(intent)
        if mapped and mapped in hard_law_sections:
            return mapped, _get_policy_section(policy_pack, mapped)
    return None


def _detect_policy_gate_section(
    message_text: str | None,
    *,
    policy_pack: dict | None,
    hard_law_sections: set[str] | None = None,
) -> tuple[str, dict | None] | None:
    sections = [section for section in _POLICY_SECTIONS if section not in (hard_law_sections or set())]
    return _detect_policy_section(
        message_text,
        policy_pack=policy_pack,
        sections=sections,
    )


def _resolve_complaint_guard(policy_pack: dict | None) -> tuple[list[str], list[str]]:
    complaint = _get_policy_section(policy_pack, "complaint")
    explicit_keywords = _policy_str_list(
        complaint.get("explicit_keywords") if isinstance(complaint, dict) else None
    )
    consult_override = _policy_str_list(
        complaint.get("consult_override_keywords") if isinstance(complaint, dict) else None
    )
    return explicit_keywords, consult_override


def _detect_booking_cancel(message_text: str | None, *, policy_pack: dict | None) -> bool:
    from . import _legacy as legacy

    normalized = legacy._normalize_text(message_text)
    if not normalized:
        return False
    section = _get_policy_section(policy_pack, "cancel")
    keywords = _policy_str_list(section.get("keywords") if isinstance(section, dict) else None)
    if not keywords:
        return False
    return _matches_policy_keywords(normalized, keywords)


def _is_hard_law_intent(
    intent: str | None,
    *,
    policy_type: str | None = None,
    policy_pack: dict | None = None,
    client_slug: str | None = None,
) -> bool:
    if not isinstance(intent, str):
        return False
    normalized = intent.strip().casefold()
    policy_pack = (
        policy_pack
        if isinstance(policy_pack, dict)
        else _load_policy_pack(policy_type=policy_type, client_slug=client_slug)
    )
    hard_law = _get_policy_section(policy_pack, "hard_law")
    intents = _policy_str_list(hard_law.get("intents") if isinstance(hard_law, dict) else None)
    if not intents:
        return False
    return normalized in {value.casefold() for value in intents}


def _looks_like_policy_topic(
    message_text: str | None,
    *,
    policy_type: str | None = None,
    policy_pack: dict | None = None,
    client_slug: str | None = None,
) -> bool:
    policy_pack = (
        policy_pack
        if isinstance(policy_pack, dict)
        else _load_policy_pack(policy_type=policy_type, client_slug=client_slug)
    )
    hard_law_sections = set(_resolve_hard_law_sections(policy_pack))
    return bool(
        _detect_policy_gate_section(
            message_text,
            policy_pack=policy_pack,
            hard_law_sections=hard_law_sections,
        )
    )


def _detect_llm_guard_topics(
    response_text: str,
    *,
    policy_type: str | None = None,
    policy_pack: dict | None = None,
    client_slug: str | None = None,
) -> list[str]:
    from . import _legacy as legacy

    normalized = legacy._normalize_text(response_text)
    if not normalized:
        return []
    policy_pack = (
        policy_pack
        if isinstance(policy_pack, dict)
        else _load_policy_pack(policy_type=policy_type, client_slug=client_slug)
    )
    guard_topics = _get_guard_topics(policy_pack)
    hits: list[str] = []
    if not guard_topics:
        return hits
    for topic, keywords in guard_topics.items():
        if any(keyword in normalized for keyword in keywords):
            hits.append(topic)
    return hits


def _looks_like_promotions_request(
    message_text: str | None,
    *,
    policy_type: str | None = None,
    policy_pack: dict | None = None,
    client_slug: str | None = None,
) -> bool:
    from . import _legacy as legacy

    if not message_text:
        return False
    normalized = legacy._normalize_text(message_text)
    if not normalized:
        return False
    policy_pack = (
        policy_pack
        if isinstance(policy_pack, dict)
        else _load_policy_pack(policy_type=policy_type, client_slug=client_slug)
    )
    discounts = _get_policy_section(policy_pack, "discounts")
    keywords = _policy_str_list(discounts.get("keywords") if isinstance(discounts, dict) else None)
    if keywords and legacy._contains_any(normalized, keywords):
        return True
    birthday_window = discounts.get("birthday_window") if isinstance(discounts, dict) else None
    if isinstance(birthday_window, dict):
        phrase = birthday_window.get("phrase")
        day_words = _policy_str_list(birthday_window.get("day_words"))
        if isinstance(phrase, str) and phrase.strip():
            if phrase in normalized and legacy._contains_any(normalized, day_words):
                return True
    return False


def _load_discount_policy_payload(
    *,
    policy_pack: dict | None = None,
    policy_type: str | None = None,
    client_slug: str | None = None,
) -> dict | None:
    policy_pack = (
        policy_pack
        if isinstance(policy_pack, dict)
        else _load_policy_pack(policy_type=policy_type, client_slug=client_slug)
    )
    if not isinstance(policy_pack, dict):
        return None
    discounts = policy_pack.get("discounts")
    if not isinstance(discounts, dict):
        return None
    if discounts.get("enabled") is False:
        return None
    return discounts


def _has_discount_policy_rules(
    *,
    policy_pack: dict | None = None,
    policy_type: str | None = None,
) -> bool:
    discounts = _load_discount_policy_payload(policy_pack=policy_pack, policy_type=policy_type)
    if not discounts:
        return False
    rules = discounts.get("rules")
    if isinstance(rules, list) and rules:
        return True
    items = discounts.get("items")
    if isinstance(items, list) and items:
        return True
    stacking = discounts.get("stacking") or discounts.get("stacking_notes")
    if isinstance(stacking, str) and stacking.strip():
        return True
    fallback_text = discounts.get("value_text") or discounts.get("text") or discounts.get("notes")
    if isinstance(fallback_text, str) and fallback_text.strip():
        return True
    return False


def _format_discounts_policy_reply(
    *,
    policy_pack: dict | None = None,
    policy_type: str | None = None,
) -> str | None:
    discounts = _load_discount_policy_payload(policy_pack=policy_pack, policy_type=policy_type)
    if not discounts:
        return None
    stacking_parts = [
        str(value).strip().rstrip(".")
        for value in (discounts.get("stacking"), discounts.get("stacking_notes"))
        if isinstance(value, str) and value.strip()
    ]
    stacking_text = f" {'. '.join(stacking_parts)}." if stacking_parts else ""
    items = discounts.get("items")
    if not isinstance(items, list):
        items = []
    parts: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        percent = item.get("discount_percent") or item.get("discount")
        if name and percent:
            parts.append(f"{name}: {percent}%")
    if parts:
        return "Официальные акции: " + "; ".join(parts) + "." + stacking_text
    rules = discounts.get("rules")
    if isinstance(rules, list) and rules:
        parts = [str(rule).strip() for rule in rules if str(rule).strip()]
        if parts:
            return " ".join(parts)
    fallback_text = discounts.get("value_text") or discounts.get("text") or discounts.get("notes")
    if isinstance(fallback_text, str) and fallback_text.strip():
        return fallback_text.strip()
    if stacking_parts:
        return ". ".join(stacking_parts) + "."
    return None


def _pack_escalation_gate(messages: list[str], *, client_slug: str | None):
    from app.services.demo_salon_knowledge import get_pack_decision

    from . import _legacy as legacy

    for message in messages:
        decision = get_pack_decision(message, client_slug=client_slug)
        if not decision or decision.action != "escalate":
            continue
        if decision.intent in {"medical"} and legacy._is_hygiene_context_text(message):
            continue
        return decision
    return None


def _pack_price_sidecar(
    messages: list[str],
    *,
    client_slug: str | None,
) -> tuple[str | None, str | None]:
    from app.services.demo_salon_knowledge import get_pack_price_item, get_pack_price_reply

    for message in messages:
        price_reply = get_pack_price_reply(message, client_slug=client_slug)
        if price_reply:
            return price_reply, get_pack_price_item(message, client_slug=client_slug)
    return None, None


# Backward-compatible aliases while call sites migrate from demo-specific names.
def _demo_salon_escalation_gate(messages: list[str], *, client_slug: str | None):
    return _pack_escalation_gate(messages, client_slug=client_slug)


def _demo_salon_price_sidecar(
    messages: list[str],
    *,
    client_slug: str | None,
) -> tuple[str | None, str | None]:
    return _pack_price_sidecar(messages, client_slug=client_slug)


def _get_policy_type(client: Client | None, *, client_slug: str | None) -> str | None:
    if not client or not isinstance(client.config, dict):
        return None
    policy = client.config.get("policy")
    if isinstance(policy, dict):
        policy_type = policy.get("type") or policy.get("policy_type")
        if isinstance(policy_type, str) and policy_type.strip():
            return policy_type.strip()
    legacy = client.config.get("policy_type")
    if isinstance(legacy, str) and legacy.strip():
        return legacy.strip()
    if isinstance(client_slug, str) and client_slug.strip():
        return client_slug.strip()
    return None


def _get_policy_handler(client: Client | None, *, client_slug: str | None) -> dict | None:
    from . import _legacy as legacy

    policy_type = _get_policy_type(client, client_slug=client_slug)
    if not policy_type:
        return None
    handler = legacy._POLICY_HANDLERS.get(policy_type) or legacy._POLICY_HANDLERS.get("default")
    if not handler:
        return None
    policy_pack = _get_policy_pack(client, client_slug=client_slug)
    payload = dict(handler)
    payload["policy_type"] = policy_type
    payload["policy_pack"] = policy_pack
    return payload


def _apply_policy_decision(
    decision: DemoSalonDecision,
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str,
    saved_message: Message | None,
    policy_gate: str,
    policy_section: str | None,
    risk_level: str | None,
    sidecar: str | None,
    policy_t0: float | None,
    gate_label: str,
    booking_wants_flow: bool | None,
    policy_type: str | None,
    policy_source: str,
    policy_pack_missing: bool,
    routing: dict,
    client_slug: str,
    send_and_save,
    record_policy_count,
    record_escalation_metric,
    log_timing,
) -> WebhookResponse:
    from . import _legacy as legacy

    bot_response = decision.response or legacy.MSG_ESCALATED
    if sidecar:
        bot_response = legacy._combine_sidecar(bot_response, sidecar)
    legacy._reset_low_confidence_retry(conversation)
    record_policy_count(client_slug, policy_gate)
    if decision.action == "escalate":
        record_escalation_metric(policy_gate)

    result_message = "Policy reply sent"
    if decision.action == "escalate":
        _, reused, telegram_sent = legacy._reuse_active_handover(
            db=db,
            conversation=conversation,
            user=user,
            message=message_text,
            source=policy_source,
            intent=decision.intent,
        )
        if reused:
            result_message = f"Policy reuse, telegram={'sent' if telegram_sent else 'failed'}"
        elif conversation.state == legacy.ConversationState.BOT_ACTIVE.value and routing.get(
            "allow_handover_create", False
        ):
            result = legacy.escalate_to_pending(
                db=db,
                conversation=conversation,
                user_message=message_text,
                trigger_type="intent",
                trigger_value=decision.intent or "policy",
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
                result_message = f"Policy escalation, telegram={'sent' if telegram_sent else 'failed'}"
            else:
                result_message = f"Policy escalation failed: {result.error}"
        else:
            result_message = "Policy escalation skipped (already pending)"

    router_skip_reason = "law_gate" if policy_gate == "hard_law" else "policy_gate"
    router_gate_meta = legacy._set_router_observability(
        saved_message,
        eligible=False,
        reason=router_skip_reason,
    )
    trace_payload = {
        "stage": "policy_gate",
        "decision": decision.action,
        "intent": decision.intent,
        "state": conversation.state,
        "policy_type": policy_type,
        "policy_gate": policy_gate,
        "source": policy_source,
    }
    if policy_section:
        trace_payload["policy_section"] = policy_section
    if isinstance(risk_level, str) and risk_level:
        trace_payload["risk_level"] = risk_level
    if booking_wants_flow is not None:
        trace_payload["booking_wants_flow"] = booking_wants_flow
    trace_payload.update(router_gate_meta)
    legacy._record_decision_trace(conversation, trace_payload)
    legacy._record_message_decision_meta(
        saved_message,
        action=decision.action,
        intent=decision.intent,
        source=policy_source,
        fast_intent=False,
    )
    if saved_message:
        meta_updates = {"policy_gate": policy_gate, "source": policy_source}
        if policy_pack_missing:
            meta_updates["policy_pack_missing"] = True
        if policy_section:
            meta_updates["policy_section"] = policy_section
        if isinstance(risk_level, str) and risk_level:
            meta_updates["risk_level"] = risk_level
        legacy._update_message_decision_metadata(saved_message, meta_updates)
    bot_response, sent = send_and_save(bot_response, allow_quiet_hours=False)
    if not sent:
        result_message = f"{result_message}; response_send=failed"
    if policy_t0 is not None:
        log_timing(
            "policy_gate_ms",
            (time.monotonic() - policy_t0) * 1000,
            {
                "policy_type": policy_type,
                "booking_wants_flow": booking_wants_flow,
                "gate": gate_label,
            },
        )
    db.commit()
    return WebhookResponse(
        success=True,
        message=result_message,
        conversation_id=conversation.id,
        bot_response=bot_response,
    )


def _handle_hard_law_gate(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str | None,
    saved_message: Message | None,
    policy_pack: dict | None,
    bypass_domain_flows: bool,
    routing: dict,
    policy_type: str | None,
    policy_source: str,
    policy_pack_missing: bool,
    client_slug: str,
    send_and_save,
    record_policy_count,
    record_escalation_metric,
    log_timing,
) -> WebhookResponse | None:
    if not policy_pack or bypass_domain_flows or not routing["allow_truth_gate_reply"] or not message_text:
        return None

    hard_law_t0 = time.monotonic()
    hard_law_match = _detect_hard_law_match(message_text, policy_pack=policy_pack)
    if not hard_law_match:
        return None
    from . import _legacy as legacy

    section_key, section = hard_law_match
    if section_key == "medical":
        normalized = legacy._normalize_text(message_text)
        consult_override = _policy_str_list(
            section.get("consult_override_keywords") if isinstance(section, dict) else None
        )
        if normalized and consult_override and legacy._contains_any(normalized, consult_override):
            return None
    risk_level = _resolve_policy_risk_level(section) or "high"
    intent = _resolve_policy_intent(section_key, section)
    response = section.get("response") if isinstance(section, dict) else None
    decision = DemoSalonDecision(
        action="escalate",
        response=response or _get_escalation_fallback(),
        intent=intent,
    )
    return _apply_policy_decision(
        decision,
        db=db,
        conversation=conversation,
        user=user,
        message_text=message_text,
        saved_message=saved_message,
        policy_gate="hard_law",
        policy_section=section_key,
        risk_level=risk_level,
        sidecar=None,
        policy_t0=hard_law_t0,
        gate_label="hard_law",
        booking_wants_flow=None,
        policy_type=policy_type,
        policy_source=policy_source,
        policy_pack_missing=policy_pack_missing,
        routing=routing,
        client_slug=client_slug,
        send_and_save=send_and_save,
        record_policy_count=record_policy_count,
        record_escalation_metric=record_escalation_metric,
        log_timing=log_timing,
    )


def _handle_policy_escalation_gate(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str | None,
    saved_message: Message | None,
    policy_pack: dict | None,
    hard_law_sections: set[str],
    bypass_domain_flows: bool,
    routing: dict,
    policy_type: str | None,
    policy_source: str,
    policy_pack_missing: bool,
    booking_wants_flow: bool | None,
    intent_hints: list[str] | None,
    consult_intent: bool,
    current_goal: str | None,
    multi_intent_other_followup: str | None,
    client_slug: str,
    guard_only: bool = False,
    send_and_save,
    record_policy_count,
    record_escalation_metric,
    log_timing,
) -> WebhookResponse | None:
    from . import _legacy as legacy

    if bypass_domain_flows or not routing["allow_truth_gate_reply"] or not message_text:
        return None

    policy_t0 = time.monotonic()
    intent_hints = intent_hints if policy_pack else None
    hard_law_match = _detect_hard_law_match(
        message_text,
        policy_pack=policy_pack,
        intent_hints=intent_hints or None,
    )
    if hard_law_match:
        section_key, section = hard_law_match
        risk_level = _resolve_policy_risk_level(section) or "high"
        intent = _resolve_policy_intent(section_key, section)
        response = section.get("response") if isinstance(section, dict) else None
        decision = DemoSalonDecision(
            action="escalate",
            response=response or _get_escalation_fallback(),
            intent=intent,
        )
        return _apply_policy_decision(
            decision,
            db=db,
            conversation=conversation,
            user=user,
            message_text=message_text,
            saved_message=saved_message,
            policy_gate="hard_law",
            policy_section=section_key,
            risk_level=risk_level,
            sidecar=None,
            policy_t0=policy_t0,
            gate_label="hard_law",
            booking_wants_flow=booking_wants_flow,
            policy_type=policy_type,
            policy_source=policy_source,
            policy_pack_missing=policy_pack_missing,
            routing=routing,
            client_slug=client_slug,
            send_and_save=send_and_save,
            record_policy_count=record_policy_count,
            record_escalation_metric=record_escalation_metric,
            log_timing=log_timing,
        )

    policy_match = _detect_policy_gate_section(
        message_text,
        policy_pack=policy_pack,
        hard_law_sections=hard_law_sections | {"discounts"},
    )
    if policy_match:
        section_key, section = policy_match
        if guard_only and section_key not in hard_law_sections:
            risk_level = _resolve_policy_risk_level(section)
            intent = _resolve_policy_intent(section_key, section)
            router_gate_meta = legacy._set_router_observability(
                saved_message,
                eligible=False,
                reason="policy_guard_only",
            )
            trace_payload = {
                "stage": "policy_gate",
                "decision": "guard_only",
                "intent": intent,
                "state": conversation.state,
                "policy_type": policy_type,
                "policy_gate": section_key,
                "policy_section": section_key,
                "source": policy_source,
            }
            if isinstance(risk_level, str) and risk_level:
                trace_payload["risk_level"] = risk_level
            if booking_wants_flow is not None:
                trace_payload["booking_wants_flow"] = booking_wants_flow
            trace_payload.update(router_gate_meta)
            legacy._record_decision_trace(conversation, trace_payload)
            if saved_message:
                meta_updates = {
                    "policy_guard_only": True,
                    "policy_gate": section_key,
                    "policy_section": section_key,
                    "source": policy_source,
                }
                if policy_pack_missing:
                    meta_updates["policy_pack_missing"] = True
                if isinstance(risk_level, str) and risk_level:
                    meta_updates["risk_level"] = risk_level
                legacy._update_message_decision_metadata(saved_message, meta_updates)
            return None
        if section_key == "complaint":
            normalized_text = legacy._normalize_text(message_text)
            explicit_keywords, consult_override_keywords = _resolve_complaint_guard(policy_pack)
            complaint_signal = bool(
                normalized_text
                and explicit_keywords
                and legacy._contains_any(normalized_text, explicit_keywords)
            )
            consult_override = bool(
                (consult_intent or current_goal == "consult")
                and normalized_text
                and consult_override_keywords
                and legacy._contains_any(normalized_text, consult_override_keywords)
            )
            if saved_message:
                legacy._update_message_decision_metadata(
                    saved_message,
                    {
                        "complaint_signal": complaint_signal,
                        "consult_override": consult_override,
                    },
                )
            legacy._record_decision_trace(
                conversation,
                {
                    "stage": "complaint_guard",
                    "decision": "suppressed"
                    if (consult_override or not complaint_signal)
                    else "accepted",
                    "complaint_signal": complaint_signal,
                    "consult_override": consult_override,
                },
            )
            if consult_override or not complaint_signal:
                section_key = ""

        if section_key:
            action = section.get("action") if isinstance(section, dict) else None
            if not isinstance(action, str) or not action.strip():
                action = "escalate"
            response = section.get("response") if isinstance(section, dict) else None
            intent = _resolve_policy_intent(section_key, section)
            risk_level = _resolve_policy_risk_level(section)
            decision = DemoSalonDecision(
                action=action,
                response=response or _get_escalation_fallback(),
                intent=intent,
            )
            return _apply_policy_decision(
                decision,
                db=db,
                conversation=conversation,
                user=user,
                message_text=message_text,
                saved_message=saved_message,
                policy_gate=section_key,
                policy_section=section_key,
                risk_level=risk_level,
                sidecar=multi_intent_other_followup,
                policy_t0=policy_t0,
                gate_label="policy_gate",
                booking_wants_flow=booking_wants_flow,
                policy_type=policy_type,
                policy_source=policy_source,
                policy_pack_missing=policy_pack_missing,
                routing=routing,
                client_slug=client_slug,
                send_and_save=send_and_save,
                record_policy_count=record_policy_count,
                record_escalation_metric=record_escalation_metric,
                log_timing=log_timing,
            )

    log_timing(
        "policy_gate_ms",
        (time.monotonic() - policy_t0) * 1000,
        {"policy_type": policy_type, "booking_wants_flow": booking_wants_flow, "gate": "escalation"},
    )
    return None


def _get_escalation_fallback() -> str:
    from . import _legacy as legacy

    return legacy.MSG_ESCALATED
