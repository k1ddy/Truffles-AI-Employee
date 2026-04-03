"""Legacy info helper surface kept unreachable from the live runtime boundary."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

from app.core import DialogStateService
from app.routers.webhook.booking_signal_runtime import (
    _extract_datetime,
    _has_explicit_service_signal,
)
from app.routers.webhook.class_router_runtime import (
    DomainIntent,
    build_observer_class_router_result,
    _controller_meta_updates_from_class_router,
    _resolve_class_router_result,
    _router_observability_updates_from_class_router,
)
from app.routers.webhook.runtime_primitives import (
    BOOKING_CTA_SERVICE_INTENTS,
    EXPECTED_REPLY_SERVICE,
    INFO_ANCHOR_GROUPS,
    INFO_INTENT_PRIORITY_GENERIC,
    INFO_INTENT_PRIORITY_SERVICE,
    INFO_INTENTS,
    MSG_BOOKING_ASK_DATETIME,
    MSG_BOOKING_ASK_NAME,
    MSG_ESCALATED,
    MSG_EXPECTED_SERVICE_OFF_TOPIC,
    QUESTION_WORD_PREFIXES,
    SESSION_MEMORY_SHORT_TOKENS,
    _combine_sidecar,
)
from app.schemas.webhook import WebhookResponse
from app.services.ai_service import normalize_for_matching
from app.services.booking_signal_service import (
    extract_daypart_token as _extract_daypart_token,
)
from app.services.expected_reply_contract import (
    should_override_truth_gate_off_topic_contract,
    truth_gate_expected_reply_prompt_contract,
)
from app.services.handover_owner_service import (
    ActiveHandoverReuseRuntimeHooks,
    _reuse_active_handover,
    escalate_to_pending,
    get_active_handover,
    send_telegram_notification,
)
from app.services.pack_runtime_service import (
    _build_fact_meta,
    _detect_promotion_intent,
    _has_contact_signal,
    _normalize_text,
    build_info_combined_reply,
    build_master_reply_from_pack,
    build_runtime_service_duration_reply,
    build_runtime_service_not_found_reply,
    build_runtime_service_truth_reply,
    compose_multi_truth_reply,
    ensure_resolver_meta,
    format_reply_from_truth,
    get_signal_lexicon_list,
    get_system_lexicon_list,
    load_yaml_truth,
    resolve_runtime_service_price_item,
    resolve_explicit_master_intent,
)
from app.services.signal_manifest_service import get_info_regex_pattern
from app.services.state_machine import ConversationState
from app.services.state_service import transition_state

from .trace import (
    _record_decision_trace,
    _record_message_decision_meta,
    _update_message_decision_metadata,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models import Conversation, Message, User


_TOKENIZE_WORD_RE = get_info_regex_pattern("tokenize_word_pattern") or re.compile(r"\w+")


def _context_runtime():
    from . import context_manager as context_router

    return context_router


def _guards_runtime():
    from . import guards as guards_router

    return guards_router


def _response_runtime():
    from . import response as response_router

    return response_router


def _booking_runtime():
    from . import booking as booking_router

    return booking_router


def _tokenize_for_matching(normalized: str) -> list[str]:
    return _TOKENIZE_WORD_RE.findall(normalized)


_BASE_INFO_SECTION_ORDER = ("location", "hours", "parking", "guest_policy")


def _requested_base_info_sections(
    *,
    info_intents: set[str] | list[str] | tuple[str, ...] | None,
    carryover_sections: list[str] | tuple[str, ...] | set[str] | None = None,
) -> list[str]:
    normalized_intents = {
        item.strip().casefold()
        for item in (info_intents or [])
        if isinstance(item, str) and item.strip()
    }
    normalized_carryover = {
        item.strip().casefold()
        for item in (carryover_sections or [])
        if isinstance(item, str) and item.strip()
    }
    return [
        section
        for section in _BASE_INFO_SECTION_ORDER
        if section in normalized_intents or section in normalized_carryover
    ]


def _build_requested_base_info_reply(
    *,
    requested_sections: list[str] | tuple[str, ...] | set[str],
    client_slug: str | None,
) -> tuple[str | None, dict[str, Any] | None]:
    sections = _requested_base_info_sections(info_intents=requested_sections)
    if not sections:
        return None, None

    truth = load_yaml_truth(client_slug)
    guest_policy = truth.get("guest_policy") if isinstance(truth, dict) else None
    reply_parts: list[str] = []
    info_sections: list[str] = []
    fact_intents: list[str] = []

    for section in sections:
        reply: str | None = None
        section_info_key = section
        if section == "location":
            reply = format_reply_from_truth("location", client_slug=client_slug)
            section_info_key = "address"
        elif section == "hours":
            reply = format_reply_from_truth("hours", client_slug=client_slug)
        elif section == "parking":
            reply = format_reply_from_truth("parking", client_slug=client_slug)
        elif section == "guest_policy" and isinstance(guest_policy, dict):
            guest_parts = [
                guest_policy.get("allowed_guests"),
                guest_policy.get("animals"),
                guest_policy.get("guest_limit"),
                guest_policy.get("early_arrival"),
                guest_policy.get("children_rules"),
                guest_policy.get("alcohol_policy"),
                guest_policy.get("food_drink_policy"),
            ]
            guest_text = " ".join(
                str(item).strip()
                for item in guest_parts
                if isinstance(item, str) and item.strip()
            )
            if guest_text:
                reply = guest_text if guest_text.endswith(".") else f"{guest_text}."
        if not isinstance(reply, str):
            continue
        reply = reply.strip()
        if not reply:
            continue
        reply_parts.append(reply)
        fact_intents.append(section)
        info_sections.append(section_info_key)

    if not reply_parts:
        return None, None
    meta = _build_fact_meta(
        fact_source="truth",
        fact_intents=fact_intents,
        info_sections=info_sections,
    )
    return " ".join(reply_parts), meta


def _merge_prefixed_info_meta(
    meta: dict[str, Any],
    prefix_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(prefix_meta, dict):
        return meta
    merged = dict(meta)
    for key in ("info_sections", "fact_intents", "fact_refs"):
        prefix_values = prefix_meta.get(key)
        base_values = merged.get(key)
        values: list[str] = []
        for source in (prefix_values, base_values):
            if not isinstance(source, list):
                continue
            for item in source:
                if isinstance(item, str) and item.strip() and item.strip() not in values:
                    values.append(item.strip())
        if values:
            merged[key] = values
    return merged


def _normalized_contains_any(normalized: str, phrases: tuple[str, ...] | list[str]) -> bool:
    if not normalized:
        return False
    return any(phrase and phrase in normalized for phrase in phrases)


def _signal_phrase_list(client_slug: str | None, *keys: str) -> list[str]:
    phrases: list[str] = []
    for key in keys:
        for phrase in get_signal_lexicon_list(client_slug, key):
            token = phrase.strip() if isinstance(phrase, str) else ""
            if token and token not in phrases:
                phrases.append(token)
    return phrases


def _signal_any_match(normalized: str, client_slug: str | None, *keys: str) -> bool:
    return bool(keys) and _normalized_contains_any(normalized, _signal_phrase_list(client_slug, *keys))


def _signal_all_match(normalized: str, client_slug: str | None, key: str) -> bool:
    phrases = _signal_phrase_list(client_slug, key)
    return bool(phrases) and all(phrase in normalized for phrase in phrases)


def _signal_pair_match(
    normalized: str,
    client_slug: str | None,
    key_a: str,
    key_b: str,
) -> bool:
    phrases_a = _signal_phrase_list(client_slug, key_a)
    phrases_b = _signal_phrase_list(client_slug, key_b)
    return bool(phrases_a and phrases_b) and _normalized_contains_any(
        normalized, phrases_a
    ) and _normalized_contains_any(normalized, phrases_b)


def _system_any_match(normalized: str, key: str) -> bool:
    phrases = get_system_lexicon_list(key)
    return bool(phrases) and _normalized_contains_any(normalized, phrases)


def _system_any_match_multi(normalized: str, *keys: str) -> bool:
    return any(_system_any_match(normalized, key) for key in keys)


def _has_token_prefix(tokens: list[str], prefix: str) -> bool:
    return any(token.startswith(prefix) for token in tokens)


def _tokens_have_prefixes(tokens: list[str], prefixes: tuple[str, ...]) -> bool:
    return any(_has_token_prefix(tokens, prefix) for prefix in prefixes)


def _has_anchor_prefix(tokens: list[str], prefix: str) -> bool:
    if len(prefix) <= 2:
        return any(token == prefix for token in tokens)
    return any(token.startswith(prefix) for token in tokens)


def _anchor_group_hit(tokens: list[str], group: tuple[str, ...]) -> bool:
    return all(_has_anchor_prefix(tokens, prefix) for prefix in group)


def _count_anchor_hits(tokens: list[str], groups: list[tuple[str, ...]]) -> int:
    return sum(1 for group in groups if _anchor_group_hit(tokens, group))


def _is_short_reply(message_text: str | None) -> bool:
    if not message_text:
        return False
    normalized = _normalize_text(message_text)
    if not normalized:
        return False
    tokens = _tokenize_for_matching(normalized)
    return 0 < len(tokens) <= SESSION_MEMORY_SHORT_TOKENS


def _truth_gate_expected_reply_prompt(expected_reply_type: str | None) -> tuple[str | None, str | None]:
    prompt_key, intent = truth_gate_expected_reply_prompt_contract(expected_reply_type)
    prompt_map = {
        "service_clarify": MSG_EXPECTED_SERVICE_OFF_TOPIC,
        "booking_ask_datetime": MSG_BOOKING_ASK_DATETIME,
        "booking_ask_name": MSG_BOOKING_ASK_NAME,
    }
    if not prompt_key or not intent:
        return None, None
    return prompt_map.get(prompt_key), intent


def _should_override_truth_gate_off_topic(
    *,
    expected_reply_type: str | None,
    expected_reply_matched: bool | None,
    message_text: str | None,
    current_goal: str | None,
    client_slug: str | None,
) -> bool:
    has_message_text = bool(message_text)
    is_short_reply = _is_short_reply(message_text) if has_message_text else False
    has_booking_slot_signal = (
        _booking_runtime()._is_booking_slot_signal(message_text, client_slug=client_slug)
        if has_message_text
        else False
    )
    has_service_hint = False
    has_datetime_slot = bool(_extract_datetime(message_text)) if has_message_text else False
    has_name_slot = bool(
        _booking_runtime()._validate_name_slot(
            message_text,
            allow_freeform=True,
            client_slug=client_slug,
        )
    ) if has_message_text else False
    return should_override_truth_gate_off_topic_contract(
        expected_reply_type=expected_reply_type,
        expected_reply_matched=expected_reply_matched,
        has_message_text=has_message_text,
        current_goal=current_goal,
        is_short_reply=is_short_reply,
        has_booking_slot_signal=has_booking_slot_signal,
        has_service_hint=has_service_hint,
        has_datetime_slot=has_datetime_slot,
        has_name_slot=has_name_slot,
    )


def _build_info_intent_reply(
    intent: str,
    *,
    service_query: str | None,
    client_slug: str | None,
    message_text: str | None = None,
    include_info_bundle: bool = True,
    requested_info_intents: list[str] | tuple[str, ...] | set[str] | None = None,
) -> tuple[str | None, dict | None]:
    requested_sections = {
        str(item).strip().casefold()
        for item in (requested_info_intents or [])
        if isinstance(item, str) and item.strip()
    }
    explicit_base_sections = [
        section
        for section in _BASE_INFO_SECTION_ORDER
        if section in requested_sections
    ]
    if not explicit_base_sections and intent in {"location", "hours", "parking"}:
        explicit_base_sections = [intent]
    include_explicit_base_bundle = bool(include_info_bundle and explicit_base_sections)

    def _resolverize(
        meta_payload: dict | None,
        *,
        resolved_intent: str | None = None,
        resolved_action: str = "reply",
    ) -> dict:
        return ensure_resolver_meta(
            meta_payload if isinstance(meta_payload, dict) else {},
            action=resolved_action,
            intent=resolved_intent or intent,
            resolver_id="webhook.info_intent",
            client_slug=client_slug,
        )

    def _service_query_meta_payload(
        service_name: str | None,
        *,
        source: str,
    ) -> dict[str, Any] | None:
        if not isinstance(service_name, str) or not service_name.strip():
            return None
        return {
            "service_query": service_name.strip(),
            "service_query_source": source,
            "service_query_score": 1.0 if source == "info_intent" else 0.56,
        }

    if intent == "contact":
        truth = load_yaml_truth(client_slug)
        salon = truth.get("salon", {}) if isinstance(truth, dict) else {}
        if isinstance(salon, dict):
            phone = str(salon.get("phone") or "").strip()
            whatsapp = str(salon.get("whatsapp") or "").strip()
            telegram = str(salon.get("telegram") or "").strip()
            instagram = str(salon.get("instagram") or "").strip()
            lines: list[str] = []
            if phone:
                lines.append(f"Телефон: {phone}.")
            if whatsapp:
                lines.append(f"WhatsApp: {whatsapp}.")
            if telegram:
                lines.append(f"Telegram: {telegram}.")
            if instagram:
                lines.append(f"Instagram: {instagram}.")
            if lines:
                if not phone and (whatsapp or telegram or instagram):
                    lines.insert(0, "Телефон в карточке салона не указан.")
                meta = _build_fact_meta(
                    meta={"info_sections": ["contact"]},
                    fact_source="truth",
                    fact_intents=["contact"],
                    info_sections=["contact"],
                )
                return " ".join(lines), _resolverize(meta, resolved_intent="contact")

    if intent == "hours":
        reply, meta = _build_requested_base_info_reply(
            requested_sections=explicit_base_sections,
            client_slug=client_slug,
        )
        if reply:
            return reply, _resolverize(meta)
        return None, None
    if intent == "parking":
        reply, meta = _build_requested_base_info_reply(
            requested_sections=explicit_base_sections,
            client_slug=client_slug,
        )
        if reply:
            return reply, _resolverize(meta, resolved_intent="parking")
        return None, None
    if intent == "location":
        reply, meta = _build_requested_base_info_reply(
            requested_sections=explicit_base_sections,
            client_slug=client_slug,
        )
        if reply:
            return reply, _resolverize(meta)
        return None, None
    if intent == "master":
        resolution = resolve_explicit_master_intent(
            client_slug=client_slug,
            service_query=service_query,
            force_master_intent=True,
        )
        decision = build_master_reply_from_pack(
            client_slug=client_slug,
            message_text=None,
            resolution=resolution,
        )
        if not decision:
            return None, None
        return decision.response, _resolverize(
            decision.meta,
            resolved_intent=decision.intent or "master",
            resolved_action=decision.action or "reply",
        )
    if intent == "hygiene":
        reply = format_reply_from_truth("hygiene", client_slug=client_slug)
        if not reply:
            return None, None
        meta = _build_fact_meta(
            fact_source="truth",
            fact_intents=["hygiene"],
            info_sections=["hygiene"],
        )
        return reply, _resolverize(meta, resolved_intent="hygiene")
    if intent == "prep_brows_lashes":
        reply = format_reply_from_truth("prep_brows_lashes", client_slug=client_slug)
        if not reply:
            return None, None
        meta = _build_fact_meta(
            fact_source="truth",
            fact_intents=["prep_brows_lashes"],
            info_sections=["prep_brows_lashes"],
        )
        return reply, _resolverize(meta, resolved_intent="prep_brows_lashes")
    if intent == "promotions":
        reply = format_reply_from_truth("promotions", client_slug=client_slug)
        if not reply:
            reply = format_reply_from_truth("promotions_rules", client_slug=client_slug)
        if not reply:
            return None, None
        meta = _build_fact_meta(
            fact_source="truth",
            fact_intents=["promotions"],
            info_sections=["promotions"],
        )
        return reply, _resolverize(meta, resolved_intent="promotions")
    if intent == "promotions_rules":
        reply = format_reply_from_truth("promotions_rules", client_slug=client_slug)
        if not reply:
            return None, None
        meta = _build_fact_meta(
            fact_source="truth",
            fact_intents=["promotions"],
            info_sections=["promotions"],
        )
        return reply, _resolverize(meta, resolved_intent="promotions_rules")
    resolved_service_query = (
        service_query.strip()
        if isinstance(service_query, str) and service_query.strip()
        else None
    )
    service_query_meta = _service_query_meta_payload(
        resolved_service_query,
        source="info_intent",
    )
    if intent not in {"pricing", "duration"}:
        return None, None
    info_prefix: str | None = None
    info_meta: dict | None = None
    if include_explicit_base_bundle:
        info_prefix, info_meta = _build_requested_base_info_reply(
            requested_sections=explicit_base_sections,
            client_slug=client_slug,
        )
    duration_info_sections = ["duration", "service_duration"] if intent == "duration" else None
    if intent == "pricing":
        reply = (
            build_runtime_service_truth_reply(
                resolved_service_query,
                client_slug=client_slug,
            )
            if resolved_service_query
            else format_reply_from_truth("duration_or_price_clarify", client_slug=client_slug)
        )
        price_item = (
            resolve_runtime_service_price_item(
                resolved_service_query,
                client_slug=client_slug,
            )
            if resolved_service_query
            else None
        )
        if reply:
            meta = _build_fact_meta(
                meta=info_meta,
                fact_source="truth",
                fact_intents=["pricing"],
                info_sections=["pricing"],
                service_query_meta=service_query_meta,
                price_item=price_item if isinstance(price_item, dict) else None,
            )
            meta = _merge_prefixed_info_meta(meta, info_meta)
            reply_text = f"{info_prefix} {reply}".strip() if info_prefix else reply
            return reply_text, _resolverize(
                meta,
                resolved_intent="price_query",
                resolved_action="reply",
            )
        service_not_found_reply = build_runtime_service_not_found_reply(
            client_slug=client_slug,
        )
        if service_not_found_reply:
            if info_prefix:
                service_not_found_reply = f"{info_prefix} {service_not_found_reply}".strip()
            meta = _build_fact_meta(
                meta=info_meta,
                fact_source="truth",
                fact_intents=["pricing"],
                info_sections=["pricing"],
                service_query_meta=service_query_meta,
            )
            meta = _merge_prefixed_info_meta(meta, info_meta)
            return service_not_found_reply, _resolverize(
                meta,
                resolved_intent="service_not_found",
                resolved_action="collect",
            )
    else:
        reply = build_runtime_service_duration_reply(
            service_label=resolved_service_query,
            client_slug=client_slug,
        )
        if reply:
            meta = _build_fact_meta(
                meta=info_meta,
                fact_source="truth",
                fact_intents=["service_duration", "duration"] if resolved_service_query else ["duration"],
                info_sections=duration_info_sections,
                service_query_meta=service_query_meta,
                duration_item=resolved_service_query,
            )
            meta = _merge_prefixed_info_meta(meta, info_meta)
            reply_text = f"{info_prefix} {reply}".strip() if info_prefix else reply
            return reply_text, _resolverize(
                meta,
                resolved_intent="service_duration" if resolved_service_query else "duration",
                resolved_action="reply",
            )
    fallback = format_reply_from_truth("duration_or_price_clarify", client_slug=client_slug)
    if info_prefix:
        fallback = f"{info_prefix} {fallback}".strip() if fallback else info_prefix
    meta = _build_fact_meta(
        meta=info_meta,
        fact_source="truth",
        fact_intents=[intent],
        info_sections=duration_info_sections,
        service_query_meta=service_query_meta,
    )
    meta = _merge_prefixed_info_meta(meta, info_meta)
    return fallback, _resolverize(
        meta,
        resolved_action="collect",
        resolved_intent="duration_or_price_clarify",
    )


def _extract_truth_gate_info_intents(
    message_text: str,
    *,
    policy_handler: dict | None,
    policy_type: str | None,
    client_slug: str | None,
    intent_decomp: dict | None,
) -> list[str]:
    if not message_text or not policy_handler:
        return []
    truth_gate = policy_handler.get("truth_gate")
    if not truth_gate:
        return []
    decision = truth_gate(message_text, client_slug=client_slug, intent_decomp=intent_decomp)
    if not decision or getattr(decision, "action", None) != "reply":
        return []
    intent = getattr(decision, "intent", None)
    if not isinstance(intent, str):
        return []
    intent_key = intent.strip().casefold()
    if intent_key == "hours":
        return ["hours"]
    if intent_key == "location" or intent_key.startswith("location_"):
        return ["location"]
    return []


@dataclass(frozen=True)
class InfoFlowResult:
    response: WebhookResponse | None
    force_truth_gate: bool


def _record_class_router_trace(*, conversation: Any, class_router_result: dict | None) -> None:
    if not conversation or not isinstance(class_router_result, dict):
        return
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
        _router_observability_updates_from_class_router(class_router_result)
    )
    _record_decision_trace(conversation, trace_payload)


def _handle_truth_gate_fallback(
    *,
    db: Session,
    conversation: Conversation,
    user: User,
    message_text: str | None,
    saved_message: Message | None,
    client_slug: str | None,
    routing: dict,
    booking_wants_flow: bool,
    policy_handler: dict | None,
    policy_type: str | None,
    current_goal: str | None,
    intent_decomp_used: bool,
    intent_decomp_intents: list[str],
    intent_decomp_payload: dict | None,
    llm_primary_reason: str | None,
    message_count: int,
    now: datetime,
    consult_return_pending: bool,
    consult_return_prompt: str | None,
    consult_context: dict | None,
    consult_return_reason: str | None,
    maybe_apply_fact_guard: Callable[..., Any],
    send_and_save: Callable[..., tuple[str, bool]],
    log_timing: Callable[[str, float, dict | None], None],
    record_escalation_metric: Callable[[str], None],
) -> WebhookResponse | None:
    from app.services.pack_runtime_service import PackDecision, ensure_resolver_meta

    def _build_out_of_domain_class_router_result() -> dict[str, Any]:
        return build_observer_class_router_result(
            class_name="out_of_domain",
            goal="out_of_domain",
            info_intents=[],
            booking_signal=False,
            out_of_domain_signal=True,
            out_signals=["domain_out"],
        )

    policy_t0 = time.monotonic()
    truth_gate = policy_handler.get("truth_gate") if policy_handler else None
    decision = None
    if truth_gate:
        decision = truth_gate(
            message_text,
            client_slug=client_slug,
            intent_decomp=intent_decomp_payload,
        )
    if decision:
        if decision.intent == "price_query":
            price_item_fn = policy_handler.get("price_item") if policy_handler else None
            price_item = None
            if price_item_fn and isinstance(getattr(decision, "meta", None), dict):
                service_query = decision.meta.get("service_query")
                if isinstance(service_query, str) and service_query.strip():
                    price_item = price_item_fn(service_query, client_slug=client_slug)
            if price_item:
                context = _context_runtime()._get_conversation_context(conversation)
                context = _booking_runtime()._set_service_hint(context, price_item, now)
                _context_runtime()._set_conversation_context(conversation, context)
            elif not (
                isinstance(getattr(decision, "meta", None), dict)
                and decision.meta.get("service_query")
            ):
                decision = PackDecision(
                    action="escalate",
                    response=MSG_ESCALATED,
                    intent="price_query",
                )
        if decision.intent == "service_clarify" and decision.action != "escalate":
            clarify_intent = current_goal or "info"
            context = _context_runtime()._get_conversation_context(conversation)
            context_manager = _context_runtime()._get_context_manager(context)
            if _guards_runtime()._should_escalate_for_clarify(context_manager, clarify_intent):
                clarify_count, _ = _guards_runtime()._get_clarify_attempt_state(context_manager, clarify_intent)
                _context_runtime()._record_context_manager_decision(
                    conversation,
                    saved_message,
                    decision="clarify_limit",
                    updates={
                        "clarify_attempt": {"intent": clarify_intent, "count": clarify_count},
                        "clarify_reason": "service_clarify",
                        "clarify_limit": True,
                    },
                )
                decision = PackDecision(
                    action="escalate",
                    response=MSG_ESCALATED,
                    intent="clarify_limit",
                    meta={"clarify_limit": True},
                )
            else:
                _guards_runtime()._register_clarify_attempt(
                    conversation=conversation,
                    saved_message=saved_message,
                    intent=clarify_intent,
                    now=now,
                    reason="service_clarify",
                )
        if decision.action != "escalate" and decision.intent in {
            "service_clarify",
            "duration_or_price_clarify",
        }:
            context = _context_runtime()._get_conversation_context(conversation)
            context = _context_runtime()._set_expected_reply_context(
                conversation=conversation,
                saved_message=saved_message,
                context=context,
                expected_reply_type=EXPECTED_REPLY_SERVICE,
                reason=decision.intent,
                now=now,
            )
        if decision.action == "reply":
            guard_response = maybe_apply_fact_guard(
                decision_meta=decision.meta if isinstance(decision.meta, dict) else None,
                intent=decision.intent,
                source="truth_gate",
                allow_handover=routing.get("allow_handover_create", False),
            )
            if guard_response:
                db.commit()
                return guard_response
        bot_response = decision.response
        if decision.action == "reply":
            cta_intents = set(INFO_INTENTS) | set(BOOKING_CTA_SERVICE_INTENTS) | {
                "location_directions",
                "location_signage",
                "parking",
                "guest_policy",
                "services_overview",
            }
            if decision.intent in cta_intents:
                bot_response = _response_runtime()._maybe_append_booking_cta(
                    bot_response,
                    conversation_state=conversation.state,
                    allow_booking_flow=routing["allow_booking_flow"],
                    has_followup=bool(consult_return_pending),
                )
        if consult_return_pending:
            bot_response = _context_runtime()._apply_consult_return(
                conversation=conversation,
                saved_message=saved_message,
                bot_response=bot_response,
                consult_return_prompt=consult_return_prompt,
                consult_context=consult_context,
                reason=consult_return_reason or "truth_gate",
            )
        _context_runtime()._reset_low_confidence_retry(conversation)

        result_message = "Truth gate fallback reply sent"
        if decision.action == "escalate":
            _, reused, telegram_sent = _reuse_active_handover(
                db=db,
                conversation=conversation,
                user=user,
                message=message_text,
                source="truth_gate",
                intent=decision.intent,
                hooks=ActiveHandoverReuseRuntimeHooks(
                    get_active_handover=get_active_handover,
                    transition_state=transition_state,
                    send_telegram_notification=send_telegram_notification,
                    record_decision_trace=_record_decision_trace,
                ),
            )
            if reused:
                result_message = f"Truth gate reuse, telegram={'sent' if telegram_sent else 'failed'}"
            elif conversation.state == ConversationState.BOT_ACTIVE.value:
                record_escalation_metric("intent")
                result = escalate_to_pending(
                    db=db,
                    conversation=conversation,
                    user_message=message_text,
                    trigger_type="intent",
                    trigger_value=decision.intent or "policy",
                )
                if result.ok:
                    handover = result.value
                    telegram_sent = send_telegram_notification(
                        db=db,
                        handover=handover,
                        conversation=conversation,
                        user=user,
                        message=message_text,
                    )
                    result_message = f"Truth gate escalation, telegram={'sent' if telegram_sent else 'failed'}"
                else:
                    result_message = f"Truth gate escalation failed: {result.error}"
            else:
                result_message = "Truth gate escalation skipped (already pending)"

        if decision.intent == "off_topic":
            context = _context_runtime()._get_conversation_context(conversation)
            expected_reply_type = _context_runtime()._get_expected_reply_type(context)
            saved_meta = None
            if saved_message is not None:
                # Tests may pass lightweight message doubles that only expose
                # `message_metadata` (without SQLAlchemy `.metadata`).
                raw_meta = getattr(saved_message, "message_metadata", None)
                if isinstance(raw_meta, dict):
                    saved_meta = raw_meta
                else:
                    legacy_meta = getattr(saved_message, "metadata", None)
                    if isinstance(legacy_meta, dict):
                        saved_meta = legacy_meta
            saved_decision_meta = (
                saved_meta.get("decision_meta")
                if isinstance(saved_meta, dict)
                else None
            )
            expected_reply_matched = (
                saved_decision_meta.get("expected_reply_matched")
                if isinstance(saved_decision_meta, dict)
                else None
            )
            if _should_override_truth_gate_off_topic(
                expected_reply_type=expected_reply_type,
                expected_reply_matched=expected_reply_matched,
                message_text=message_text,
                current_goal=current_goal,
                client_slug=client_slug,
            ):
                followup_prompt, followup_intent = _truth_gate_expected_reply_prompt(
                    expected_reply_type
                )
                if followup_prompt and followup_intent:
                    context = _context_runtime()._set_expected_reply_context(
                        conversation=conversation,
                        saved_message=saved_message,
                        context=context,
                        expected_reply_type=expected_reply_type,
                        reason="truth_gate_off_topic_override",
                        now=now,
                    )
                    pending_question_contract = DialogStateService().project_context_pending_question_contract(
                        context,
                        session_memory_key="__disabled_session_memory__",
                    )
                    override_meta = (
                        dict(decision.meta)
                        if isinstance(getattr(decision, "meta", None), dict)
                        else {}
                    )
                    override_meta.update(
                        {
                            "expected_reply_type": expected_reply_type,
                            "expected_reply_guard": "truth_gate_off_topic_override",
                        }
                    )
                    if pending_question_contract:
                        override_meta["pending_question_contract"] = pending_question_contract
                    if isinstance(expected_reply_matched, bool):
                        override_meta["expected_reply_matched"] = expected_reply_matched
                    decision = PackDecision(
                        action="reply",
                        response=followup_prompt,
                        intent=followup_intent,
                        meta=override_meta,
                    )
                    bot_response = decision.response
                    trace_payload = {
                        "stage": "truth_gate",
                        "decision": "expected_reply_override",
                        "expected_reply_type": expected_reply_type,
                        "expected_reply_matched": expected_reply_matched,
                    }
                    if pending_question_contract:
                        trace_payload["pending_question_contract"] = pending_question_contract
                    _record_decision_trace(conversation, trace_payload)
            context_manager = _context_runtime()._get_context_manager(context)
            class_carryover = _context_runtime()._get_class_carryover(
                context_manager,
                message_count=message_count,
            )
            carryover_sections = (
                class_carryover.get("info_sections")
                if isinstance(class_carryover, dict)
                else None
            )
        if decision.intent == "off_topic":
            class_router_result = _build_out_of_domain_class_router_result()
            _record_class_router_trace(
                conversation=conversation,
                class_router_result=class_router_result,
            )
        resolver_action = decision.action
        if decision.action != "escalate" and decision.intent in {
            "service_not_found",
            "service_clarify",
            "duration_or_price_clarify",
            "info_clarify",
        }:
            resolver_action = "collect"
        resolver_meta = ensure_resolver_meta(
            decision.meta if isinstance(decision.meta, dict) else {},
            action=resolver_action,
            intent=decision.intent,
            resolver_id="webhook.truth_gate",
            client_slug=client_slug,
        )
        decision = PackDecision(
            action=decision.action,
            response=decision.response,
            intent=decision.intent,
            collect=decision.collect,
            meta=resolver_meta,
        )
        trace_payload = {
            "stage": "truth_gate",
            "decision": decision.action,
            "intent": decision.intent,
            "state": conversation.state,
            "booking_wants_flow": booking_wants_flow,
            "policy_type": policy_type,
            "llm_fallback_reason": llm_primary_reason,
        }
        if decision.intent == "multi_truth":
            trace_payload["multi_truth"] = True
        if isinstance(getattr(decision, "meta", None), dict):
            trace_payload.update(decision.meta)
        _record_decision_trace(conversation, trace_payload)
        _record_message_decision_meta(
            saved_message,
            action=decision.action,
            intent=decision.intent,
            source="truth_gate",
            fast_intent=False,
        )
        if saved_message and isinstance(getattr(decision, "meta", None), dict):
            _update_message_decision_metadata(saved_message, decision.meta)
        if saved_message and decision.intent == "service_clarify":
            clarify_reason = None
            service_meta = getattr(decision, "meta", None)
            service_query = None
            service_source = None
            if isinstance(service_meta, dict):
                service_query = service_meta.get("service_query")
                service_source = service_meta.get("service_query_source")
            if not service_query and service_source in (None, "", "none"):
                clarify_reason = "missing_service_query"
            elif not service_query and intent_decomp_used:
                decomp_query = (
                    intent_decomp_payload.get("service_query")
                    if isinstance(intent_decomp_payload, dict)
                    else None
                )
                if not decomp_query:
                    intent_set = {intent.strip().casefold() for intent in intent_decomp_intents if intent}
                    if "pricing" in intent_set or "duration" in intent_set:
                        clarify_reason = "missing_service_query"
            if clarify_reason:
                _update_message_decision_metadata(saved_message, {"clarify_reason": clarify_reason})
        decision_meta = decision.meta if isinstance(getattr(decision, "meta", None), dict) else {}
        info_carryover_intents: list[str] = []
        if decision.intent in INFO_INTENTS:
            info_carryover_intents.append(decision.intent)
        if decision.intent in {"parking", "guest_policy"}:
            info_carryover_intents.append(decision.intent)
        if decision.intent == "service_clarify":
            question_type = decision_meta.get("question_type")
            if question_type == "pricing":
                info_carryover_intents.append("pricing")
            elif question_type == "duration":
                info_carryover_intents.append("duration")
        if info_carryover_intents or decision_meta.get("info_sections"):
            _context_runtime()._maybe_store_class_carryover(
                conversation=conversation,
                class_name="info_bundle",
                intents=info_carryover_intents,
                info_meta=decision_meta,
                message_count=message_count,
                reason="truth_gate",
            )
        _context_runtime()._maybe_store_service_carryover(
            conversation=conversation,
            service_meta=decision.meta if isinstance(decision.meta, dict) else None,
            intent=decision.intent,
            message_count=message_count,
            reason="truth_gate",
        )
        bot_response, sent = send_and_save(bot_response)
        if not sent:
            result_message = f"{result_message}; response_send=failed"
        log_timing(
            "policy_gate_ms",
            (time.monotonic() - policy_t0) * 1000,
            {"policy_type": policy_type, "booking_wants_flow": booking_wants_flow, "gate": "truth_fallback"},
        )
        db.commit()
        return WebhookResponse(
            success=True,
            message=result_message,
            conversation_id=conversation.id,
            bot_response=bot_response,
        )
    log_timing(
        "policy_gate_ms",
        (time.monotonic() - policy_t0) * 1000,
        {"policy_type": policy_type, "booking_wants_flow": booking_wants_flow, "gate": "truth_fallback"},
    )
    return None


__all__ = [
    "_anchor_group_hit",
    "_build_info_intent_reply",
    "_count_anchor_hits",
    "_extract_truth_gate_info_intents",
    "_handle_truth_gate_fallback",
    "_is_short_reply",
    "_tokenize_for_matching",
]
