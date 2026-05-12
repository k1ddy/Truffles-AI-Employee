"""LegacySummary contract tests."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.policy_core_v3_shadow import LegacySummary


def test_minimal_valid() -> None:
    s = LegacySummary(intent="fact_question", action="reply")
    assert s.tool_action is None
    assert s.message_text == ""
    assert s.rescue_flag is False
    assert s.policy_core_degrade is False
    assert s.degrade_reason is None
    assert s.latency_ms is None
    assert s.extras == {}


def test_extras_accepts_arbitrary_payload() -> None:
    s = LegacySummary(
        intent="x",
        action="y",
        extras={"raw": {"deeply": ["nested", 1]}},
    )
    assert s.extras["raw"]["deeply"] == ["nested", 1]


def test_rejects_extra_top_level_fields() -> None:
    with pytest.raises(ValidationError):
        LegacySummary.model_validate(
            {"intent": "x", "action": "y", "weird_field": True}
        )


def test_negative_latency_rejected() -> None:
    with pytest.raises(ValidationError):
        LegacySummary(intent="x", action="y", latency_ms=-1.0)
