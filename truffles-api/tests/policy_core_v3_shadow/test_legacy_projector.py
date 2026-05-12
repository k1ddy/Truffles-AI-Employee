"""Defensive projector tests."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from app.policy_core_v3_shadow import LegacySummary, project_legacy_decision


@dataclass
class _MinimalDecision:
    intent: str
    action: str
    message_text: str = ""
    rescue: bool = False
    policy_core_degrade: bool = False


@dataclass
class _RichDecision:
    intent: str
    action: str
    tool_action: str | None
    message_text: str
    rescue: bool
    policy_core_degrade: bool
    policy_core_degrade_reason: str | None = None
    latency_ms: float | None = None


class _IntentEnum(Enum):
    booking_request = "booking_request"
    fact_question = "fact_question"


@dataclass
class _EnumDecision:
    intent: _IntentEnum
    action: str


def test_minimal_object_projects_with_defaults() -> None:
    src = _MinimalDecision(intent="booking_request", action="collect")
    out = project_legacy_decision(src)
    assert isinstance(out, LegacySummary)
    assert out.intent == "booking_request"
    assert out.action == "collect"
    assert out.tool_action is None
    assert out.message_text == ""
    assert out.rescue_flag is False
    assert out.policy_core_degrade is False
    assert out.degrade_reason is None
    assert out.latency_ms is None
    assert out.extras == {}


def test_rich_object_carries_all_fields() -> None:
    src = _RichDecision(
        intent="booking_manage",
        action="reply",
        tool_action="calendar.get_booking",
        message_text="Подскажите имя.",
        rescue=True,
        policy_core_degrade=True,
        policy_core_degrade_reason="empty_response",
        latency_ms=345.6,
    )
    out = project_legacy_decision(src, extras={"raw": "blob"})
    assert out.tool_action == "calendar.get_booking"
    assert out.message_text == "Подскажите имя."
    assert out.rescue_flag is True
    assert out.policy_core_degrade is True
    assert out.degrade_reason == "empty_response"
    assert out.latency_ms == 345.6
    assert out.extras == {"raw": "blob"}


def test_enum_intent_uses_value() -> None:
    src = _EnumDecision(intent=_IntentEnum.booking_request, action="collect")
    out = project_legacy_decision(src)
    assert out.intent == "booking_request"


def test_alternative_attribute_names_supported() -> None:
    """Caller may use legacy-style names like `tool_id`, `reply_text`,
    `is_degraded`, `degrade_reason`."""

    class _Alt:
        intent_value = "fact_question"
        action_kind = "reply"
        tool_id = "catalog.location"
        reply_text = "Адрес: Абая 1."
        is_rescue = False
        is_degraded = True
        degrade_reason = "schema_invalid"
        elapsed_ms = 12.0

    out = project_legacy_decision(_Alt())
    assert out.intent == "fact_question"
    assert out.action == "reply"
    assert out.tool_action == "catalog.location"
    assert out.message_text == "Адрес: Абая 1."
    assert out.policy_core_degrade is True
    assert out.degrade_reason == "schema_invalid"
    assert out.latency_ms == 12.0


def test_missing_intent_falls_back_to_unknown() -> None:
    class _Empty:
        pass

    out = project_legacy_decision(_Empty())
    assert out.intent == "unknown"
    assert out.action == ""


def test_negative_latency_is_normalized_to_none() -> None:
    @dataclass
    class _Bad:
        intent: str
        action: str
        latency_ms: Any

    out = project_legacy_decision(_Bad("x", "y", -42.0))
    assert out.latency_ms is None


def test_non_numeric_latency_is_normalized_to_none() -> None:
    @dataclass
    class _Bad:
        intent: str
        action: str
        latency_ms: Any

    out = project_legacy_decision(_Bad("x", "y", "not-a-number"))
    assert out.latency_ms is None


def test_extras_are_copied_not_referenced() -> None:
    extras = {"a": 1}
    src = _MinimalDecision(intent="x", action="y")
    out = project_legacy_decision(src, extras=extras)
    extras["b"] = 2
    assert out.extras == {"a": 1}
