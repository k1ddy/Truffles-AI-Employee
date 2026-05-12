"""Retry policy decision-table tests for policy_core_v3."""
from __future__ import annotations

import pytest

from app.policy_core_v3.retry_policy import (
    MAX_ATTEMPTS,
    classify_failure,
    next_retry_action,
)
from app.policy_core_v3.schema import DegradeReason


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        (dict(raw_text=None, parse_error=None, timed_out=True, provider_error=False, tool_unknown=False, intent_unknown=False), DegradeReason.timeout),
        (dict(raw_text=None, parse_error=None, timed_out=False, provider_error=True, tool_unknown=False, intent_unknown=False), DegradeReason.provider_error),
        (dict(raw_text="   ", parse_error=None, timed_out=False, provider_error=False, tool_unknown=False, intent_unknown=False), DegradeReason.empty_response),
        (dict(raw_text="not json", parse_error="json", timed_out=False, provider_error=False, tool_unknown=False, intent_unknown=False), DegradeReason.schema_invalid),
        (dict(raw_text="{}", parse_error=None, timed_out=False, provider_error=False, tool_unknown=True, intent_unknown=False), DegradeReason.tool_not_in_contract),
        (dict(raw_text="{}", parse_error=None, timed_out=False, provider_error=False, tool_unknown=False, intent_unknown=True), DegradeReason.intent_not_in_enum),
        (dict(raw_text="{}", parse_error=None, timed_out=False, provider_error=False, tool_unknown=False, intent_unknown=False), DegradeReason.schema_invalid),
    ],
)
def test_classify_failure(kwargs, expected) -> None:
    assert classify_failure(**kwargs) == expected


def test_retry_within_cap() -> None:
    d = next_retry_action(DegradeReason.empty_response, attempts_done=1)
    assert d.should_retry is True
    assert d.retry_hint is not None
    assert "JSON" in d.retry_hint


def test_no_retry_at_cap() -> None:
    d = next_retry_action(DegradeReason.empty_response, attempts_done=MAX_ATTEMPTS)
    assert d.should_retry is False
    assert d.degrade_reason == DegradeReason.empty_response


def test_timeout_has_no_hint() -> None:
    d = next_retry_action(DegradeReason.timeout, attempts_done=1)
    assert d.should_retry is True
    assert d.retry_hint is None


def test_max_attempts_is_two() -> None:
    """Spec: total cap of 2 LLM calls per turn."""
    assert MAX_ATTEMPTS == 2
