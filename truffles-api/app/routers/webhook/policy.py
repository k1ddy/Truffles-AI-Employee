"""LAW/policy gates and policy-topic detection helpers."""

from __future__ import annotations

from app.models import Client
from app.services.intent_service import Intent


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


def _load_policy_pack(*, policy_type: str | None) -> dict | None:
    if policy_type != "demo_salon":
        return None
    from app.services.demo_salon_knowledge import load_policy_pack

    policy_pack = load_policy_pack()
    return policy_pack if isinstance(policy_pack, dict) and policy_pack else None


def _policy_allows_keyword_fallback(policy_pack: dict | None) -> bool:
    if not isinstance(policy_pack, dict):
        return False
    return bool(policy_pack.get("allow_keyword_fallback"))


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


def _is_hard_law_intent(
    intent: str | None,
    *,
    policy_type: str | None = None,
    policy_pack: dict | None = None,
) -> bool:
    if not isinstance(intent, str):
        return False
    normalized = intent.strip().casefold()
    policy_pack = (
        policy_pack
        if isinstance(policy_pack, dict)
        else _load_policy_pack(policy_type=policy_type)
    )
    hard_law = _get_policy_section(policy_pack, "hard_law")
    intents = _policy_str_list(hard_law.get("intents") if isinstance(hard_law, dict) else None)
    if intents:
        return normalized in {value.casefold() for value in intents}

    from . import _legacy as legacy

    return normalized in legacy.HARD_LAW_INTENTS


def _looks_like_policy_topic(
    message_text: str | None,
    *,
    policy_type: str | None = None,
    policy_pack: dict | None = None,
) -> bool:
    from . import _legacy as legacy

    normalized = legacy._normalize_text(message_text)
    if not normalized:
        return False
    policy_pack = (
        policy_pack
        if isinstance(policy_pack, dict)
        else _load_policy_pack(policy_type=policy_type)
    )
    for section_key in ("payment_info", "medical", "complaint", "discounts"):
        section = _get_policy_section(policy_pack, section_key)
        keywords = _policy_str_list(section.get("keywords") if isinstance(section, dict) else None)
        if any(keyword in normalized for keyword in keywords):
            return True
    if not policy_pack or not _policy_allows_keyword_fallback(policy_pack):
        return False
    for topic in ("payment", "medical", "complaint", "discount"):
        keywords = legacy.LLM_GUARD_TOPICS.get(topic) or []
        if any(keyword in normalized for keyword in keywords):
            return True
    return False


def _detect_llm_guard_topics(
    response_text: str,
    *,
    policy_type: str | None = None,
    policy_pack: dict | None = None,
) -> list[str]:
    from . import _legacy as legacy

    normalized = legacy._normalize_text(response_text)
    if not normalized:
        return []
    policy_pack = (
        policy_pack
        if isinstance(policy_pack, dict)
        else _load_policy_pack(policy_type=policy_type)
    )
    guard_topics = _get_guard_topics(policy_pack)
    hits: list[str] = []
    if guard_topics:
        for topic, keywords in guard_topics.items():
            if any(keyword in normalized for keyword in keywords):
                hits.append(topic)
        return hits
    if not policy_pack or not _policy_allows_keyword_fallback(policy_pack):
        return []
    for topic, keywords in legacy.LLM_GUARD_TOPICS.items():
        if any(keyword in normalized for keyword in keywords):
            hits.append(topic)
    return hits


def _looks_like_promotions_request(
    message_text: str | None,
    *,
    policy_type: str | None = None,
    policy_pack: dict | None = None,
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
        else _load_policy_pack(policy_type=policy_type)
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
    if not policy_pack or not _policy_allows_keyword_fallback(policy_pack):
        return False
    keywords = legacy.LLM_GUARD_TOPICS.get("discount") or []
    if legacy._contains_any(normalized, keywords):
        return True
    if "до после" in normalized and legacy._contains_any(normalized, ["дней", "дня", "день"]):
        return True
    return False


def _load_discount_policy_payload(*, policy_type: str | None) -> dict | None:
    policy_pack = _load_policy_pack(policy_type=policy_type)
    if not isinstance(policy_pack, dict):
        return None
    discounts = policy_pack.get("discounts")
    if not isinstance(discounts, dict):
        return None
    if discounts.get("enabled") is False:
        return None
    return discounts


def _has_discount_policy_rules(*, policy_type: str | None) -> bool:
    discounts = _load_discount_policy_payload(policy_type=policy_type)
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


def _format_discounts_policy_reply(*, policy_type: str | None) -> str | None:
    discounts = _load_discount_policy_payload(policy_type=policy_type)
    if not discounts:
        return None
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
        stacking = discounts.get("stacking") or discounts.get("stacking_notes")
        stacking_text = ""
        if isinstance(stacking, str) and stacking.strip():
            stacking_text = f" {stacking}."
        return "Официальные акции: " + "; ".join(parts) + "." + stacking_text
    rules = discounts.get("rules")
    if isinstance(rules, list) and rules:
        parts = [str(rule).strip() for rule in rules if str(rule).strip()]
        if parts:
            return " ".join(parts)
    fallback_text = discounts.get("value_text") or discounts.get("text") or discounts.get("notes")
    if isinstance(fallback_text, str) and fallback_text.strip():
        return fallback_text.strip()
    stacking = discounts.get("stacking") or discounts.get("stacking_notes")
    if isinstance(stacking, str) and stacking.strip():
        return stacking.strip()
    return None


def _demo_salon_escalation_gate(messages: list[str]):
    from app.services.demo_salon_knowledge import get_demo_salon_decision

    from . import _legacy as legacy

    for message in messages:
        decision = get_demo_salon_decision(message)
        if not decision or decision.action != "escalate":
            continue
        if decision.intent in {"medical"} and legacy._is_hygiene_context_text(message):
            continue
        return decision
    return None


def _demo_salon_price_sidecar(messages: list[str]) -> tuple[str | None, str | None]:
    from app.services.demo_salon_knowledge import get_demo_salon_price_item, get_demo_salon_price_reply

    for message in messages:
        price_reply = get_demo_salon_price_reply(message)
        if price_reply:
            return price_reply, get_demo_salon_price_item(message)
    return None, None


def _get_policy_type(client: Client | None) -> str | None:
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
    # Legacy fallback to preserve behavior until policy config is set.
    if client.name == "demo_salon":
        return "demo_salon"
    return None


def _get_policy_handler(client: Client | None) -> dict | None:
    from . import _legacy as legacy

    policy_type = _get_policy_type(client)
    if not policy_type:
        return None
    handler = legacy._POLICY_HANDLERS.get(policy_type)
    if not handler:
        return None
    policy_pack = _load_policy_pack(policy_type=policy_type)
    payload = dict(handler)
    payload["policy_pack"] = policy_pack
    return payload
