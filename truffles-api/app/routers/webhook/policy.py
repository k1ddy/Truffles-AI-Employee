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


def _is_hard_law_intent(intent: str | None) -> bool:
    if not isinstance(intent, str):
        return False
    from . import _legacy as legacy

    return intent.strip().casefold() in legacy.HARD_LAW_INTENTS


def _looks_like_policy_topic(message_text: str | None) -> bool:
    from . import _legacy as legacy

    normalized = legacy._normalize_text(message_text)
    if not normalized:
        return False
    for topic in ("payment", "medical", "complaint", "discount"):
        keywords = legacy.LLM_GUARD_TOPICS.get(topic) or []
        if any(keyword in normalized for keyword in keywords):
            return True
    return False


def _detect_llm_guard_topics(response_text: str) -> list[str]:
    from . import _legacy as legacy

    normalized = legacy._normalize_text(response_text)
    if not normalized:
        return []
    hits: list[str] = []
    for topic, keywords in legacy.LLM_GUARD_TOPICS.items():
        if any(keyword in normalized for keyword in keywords):
            hits.append(topic)
    return hits


def _looks_like_promotions_request(message_text: str | None) -> bool:
    from . import _legacy as legacy

    if not message_text:
        return False
    normalized = legacy._normalize_text(message_text)
    if not normalized:
        return False
    keywords = legacy.LLM_GUARD_TOPICS.get("discount") or []
    if legacy._contains_any(normalized, keywords):
        return True
    if "до после" in normalized and legacy._contains_any(normalized, ["дней", "дня", "день"]):
        return True
    return False


def _load_discount_policy_payload(*, policy_type: str | None) -> dict | None:
    if policy_type != "demo_salon":
        return None
    from app.services.demo_salon_knowledge import load_yaml_truth

    truth = load_yaml_truth()
    if not isinstance(truth, dict):
        return None
    client_pack = truth.get("client_pack")
    if not isinstance(client_pack, dict):
        return None
    discounts = client_pack.get("discounts")
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
    rules = discounts.get("rules")
    if isinstance(rules, list) and rules:
        parts = [str(rule).strip() for rule in rules if str(rule).strip()]
        if parts:
            return " ".join(parts)
    fallback_text = discounts.get("value_text") or discounts.get("text") or discounts.get("notes")
    if isinstance(fallback_text, str) and fallback_text.strip():
        return fallback_text.strip()
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
    return legacy._POLICY_HANDLERS.get(policy_type)
