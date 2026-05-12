"""Deterministic, scenario-free retry policy for Policy-Core v3.

Spec: SPECS/POLICY_CORE_V3.md section 6.

This module owns the entire retry decision table. There is no per-scenario
branching anywhere. Total cap: 2 LLM calls per turn.
"""
from __future__ import annotations

from dataclasses import dataclass

from .schema import DegradeReason


MAX_ATTEMPTS = 2


@dataclass(frozen=True)
class RetryDecision:
    should_retry: bool
    retry_hint: str | None  # appended to prompt on next attempt
    degrade_reason: DegradeReason  # what to surface if retry exhausted


_RETRY_HINTS: dict[DegradeReason, str] = {
    DegradeReason.empty_response: (
        "Your previous response was empty. Reply with exactly one JSON object "
        "matching the output schema. Do not return whitespace."
    ),
    DegradeReason.schema_invalid: (
        "Your previous response did not match the required JSON schema. "
        "Return exactly one JSON object with the specified fields and types. "
        "No prose, no markdown fences."
    ),
    DegradeReason.timeout: None,
    DegradeReason.provider_error: None,
    DegradeReason.tool_not_in_contract: (
        "The tool id you proposed is not in allowed_tool_ids. Choose either "
        "'none' or a tool id from the TOOLS section."
    ),
    DegradeReason.intent_not_in_enum: (
        "The intent you returned is not in allowed_intents. Choose exactly "
        "one value from allowed_intents."
    ),
}


def classify_failure(
    *,
    raw_text: str | None,
    parse_error: str | None,
    timed_out: bool,
    provider_error: bool,
    tool_unknown: bool,
    intent_unknown: bool,
) -> DegradeReason:
    """Map an attempt's failure into a single degrade reason.

    Priority order is fixed and deterministic.
    """
    if timed_out:
        return DegradeReason.timeout
    if provider_error:
        return DegradeReason.provider_error
    if raw_text is not None and not raw_text.strip():
        return DegradeReason.empty_response
    if parse_error is not None:
        return DegradeReason.schema_invalid
    if tool_unknown:
        return DegradeReason.tool_not_in_contract
    if intent_unknown:
        return DegradeReason.intent_not_in_enum
    # fall-through: treat anything else as schema_invalid for safety
    return DegradeReason.schema_invalid


def next_retry_action(reason: DegradeReason, attempts_done: int) -> RetryDecision:
    """Decide whether to retry and which hint to add.

    Cap is 2 attempts total across all failure modes.
    """
    if attempts_done >= MAX_ATTEMPTS:
        return RetryDecision(should_retry=False, retry_hint=None, degrade_reason=reason)
    return RetryDecision(
        should_retry=True,
        retry_hint=_RETRY_HINTS.get(reason),
        degrade_reason=reason,
    )
