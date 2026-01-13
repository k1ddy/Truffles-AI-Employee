"""LAW/policy gates and policy-topic detection helpers."""

from __future__ import annotations

from copy import deepcopy
import re

from app.models import Client
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

_FALLBACK_POLICY_KEYWORDS = {
    "payment_info": [
        "\u043e\u043f\u043b\u0430\u0442",
        "\u043f\u0440\u0435\u0434\u043e\u043f\u043b\u0430\u0442",
        "\u043a\u0430\u0440\u0442",
        "\u043a\u0430\u0441\u0441",
        "\u0442\u0435\u0440\u043c\u0438\u043d\u0430\u043b",
        "\u043f\u0435\u0440\u0435\u0432\u043e\u0434",
        "kaspi",
        "iban",
        "swift",
        "\u0441\u0447\u0435\u0442",
        "\u0441\u0447\u0451\u0442",
        "qr",
    ],
    "reschedule": [
        "\u043f\u0435\u0440\u0435\u043d\u043e\u0441",
        "\u043f\u0435\u0440\u0435\u043d\u0435\u0441\u0442",
        "\u043f\u0435\u0440\u0435\u0437\u0430\u043f\u0438\u0441",
        "\u0441\u0434\u0432\u0438\u043d",
        "\u043f\u0435\u0440\u0435\u0434\u0432\u0438\u043d",
        "\u043f\u0435\u0440\u0435\u043c\u0435\u0441\u0442",
    ],
    "cancel": [
        "\u043e\u0442\u043c\u0435\u043d",
        "\u043e\u0442\u043a\u0430\u0437",
    ],
    "medical": [
        "\u0431\u0435\u0440\u0435\u043c\u0435\u043d",
        "\u0430\u043b\u043b\u0435\u0440\u0433",
        "\u043f\u0440\u043e\u0442\u0438\u0432\u043e\u043f\u043e\u043a\u0430\u0437",
        "\u043c\u0435\u0434\u0438\u0446\u0438\u043d",
        "\u0432\u0440\u0430\u0447",
    ],
    "legal": [
        "\u0441\u0443\u0434",
        "\u0437\u0430\u043a\u043e\u043d",
        "\u044e\u0440\u0438\u0441\u0442",
        "\u043f\u0440\u043e\u043a\u0443\u0440\u0430\u0442\u0443\u0440",
        "\u0438\u0441\u043a",
    ],
    "complaint": [
        "\u0436\u0430\u043b\u043e\u0431",
        "\u043f\u0440\u0435\u0442\u0435\u043d\u0437",
        "\u043d\u0435\u0434\u043e\u0432\u043e\u043b\u044c",
        "\u0440\u0430\u0437\u043e\u0447\u0430\u0440",
    ],
    "refund": [
        "\u0432\u043e\u0437\u0432\u0440\u0430\u0442",
        "\u0432\u0435\u0440\u043d\u0443\u0442",
        "refund",
    ],
    "discounts": [
        "\u0441\u043a\u0438\u0434\u043a",
        "\u0430\u043a\u0446\u0438",
        "\u043f\u0440\u043e\u043c\u043e\u043a\u043e\u0434",
        "\u043a\u0443\u043f\u043e\u043d",
        "\u0434\u0435\u0448\u0435\u0432\u043b",
    ],
}

_FALLBACK_POLICY_PACK = {
    "hard_law": {
        "action": "escalate",
        "risk_level": "high",
        "sections": [
            "payment_info",
            "reschedule",
            "cancel",
            "medical",
            "legal",
            "complaint",
            "refund",
        ],
    },
    "payment_info": {
        "action": "escalate",
        "risk_level": "high",
        "intent": "payment",
        "keywords": _FALLBACK_POLICY_KEYWORDS["payment_info"],
    },
    "reschedule": {
        "action": "escalate",
        "risk_level": "high",
        "intent": "reschedule",
        "keywords": _FALLBACK_POLICY_KEYWORDS["reschedule"],
    },
    "cancel": {
        "action": "escalate",
        "risk_level": "high",
        "intent": "cancel_request",
        "keywords": _FALLBACK_POLICY_KEYWORDS["cancel"],
    },
    "medical": {
        "action": "escalate",
        "risk_level": "high",
        "intent": "medical",
        "keywords": _FALLBACK_POLICY_KEYWORDS["medical"],
    },
    "legal": {
        "action": "escalate",
        "risk_level": "high",
        "intent": "legal",
        "keywords": _FALLBACK_POLICY_KEYWORDS["legal"],
    },
    "complaint": {
        "action": "escalate",
        "risk_level": "high",
        "intent": "complaint",
        "keywords": _FALLBACK_POLICY_KEYWORDS["complaint"],
        "explicit_keywords": _FALLBACK_POLICY_KEYWORDS["complaint"],
        "consult_override_keywords": [],
    },
    "refund": {
        "action": "escalate",
        "risk_level": "high",
        "intent": "refund",
        "keywords": _FALLBACK_POLICY_KEYWORDS["refund"],
    },
    "discounts": {
        "action": "escalate",
        "risk_level": "low",
        "intent": "discounts",
        "keywords": _FALLBACK_POLICY_KEYWORDS["discounts"],
    },
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


def _load_policy_pack(*, policy_type: str | None) -> dict | None:
    if policy_type != "demo_salon":
        return None
    from app.services.demo_salon_knowledge import load_policy_pack

    policy_pack = load_policy_pack()
    return policy_pack if isinstance(policy_pack, dict) and policy_pack else None


def _get_policy_pack(client: Client | None) -> dict | None:
    if not client or not isinstance(client.config, dict):
        return None
    policy_pack = _extract_policy_pack_from_config(client.config)
    if policy_pack:
        return policy_pack
    policy_type = _get_policy_type(client)
    if policy_type:
        return _load_policy_pack(policy_type=policy_type)
    return None


def _get_policy_gate_pack(policy_pack: dict | None) -> tuple[dict | None, bool]:
    if isinstance(policy_pack, dict) and policy_pack:
        return policy_pack, False
    return deepcopy(_FALLBACK_POLICY_PACK), True


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
    hard_law_sections = _resolve_hard_law_sections(policy_pack)
    match = _detect_policy_section(
        message_text,
        policy_pack=policy_pack,
        sections=hard_law_sections,
    )
    if match:
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
    if not intents:
        return False
    return normalized in {value.casefold() for value in intents}


def _looks_like_policy_topic(
    message_text: str | None,
    *,
    policy_type: str | None = None,
    policy_pack: dict | None = None,
) -> bool:
    policy_pack = (
        policy_pack
        if isinstance(policy_pack, dict)
        else _load_policy_pack(policy_type=policy_type)
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
    return False


def _load_discount_policy_payload(
    *,
    policy_pack: dict | None = None,
    policy_type: str | None = None,
) -> dict | None:
    policy_pack = (
        policy_pack
        if isinstance(policy_pack, dict)
        else _load_policy_pack(policy_type=policy_type)
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
    return None


def _get_policy_handler(client: Client | None) -> dict | None:
    from . import _legacy as legacy

    policy_type = _get_policy_type(client)
    if not policy_type:
        return None
    handler = legacy._POLICY_HANDLERS.get(policy_type)
    if not handler:
        return None
    policy_pack = _get_policy_pack(client)
    payload = dict(handler)
    payload["policy_pack"] = policy_pack
    return payload
