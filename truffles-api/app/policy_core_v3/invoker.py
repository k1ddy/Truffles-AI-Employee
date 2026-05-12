"""Policy-Core v3 invoker — single semantic owner of one customer turn.

Spec: SPECS/POLICY_CORE_V3.md section 1, 6, 7.

This module performs no I/O beyond calling the LLM through a `LLMCallable`
passed in at construction time. It writes nothing, calls no tools, renders
no customer message.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Awaitable, Callable

from pydantic import ValidationError

from .prompt_builder import build_prompt
from .retry_policy import (
    MAX_ATTEMPTS,
    RetryDecision,
    classify_failure,
    next_retry_action,
)
from .schema import (
    DegradeReason,
    DegradeVerdict,
    Intent,
    PolicyDecisionV3,
    PolicyTurnInput,
)


# An LLM is any async callable that takes a fully-built prompt string and
# returns the raw text the model produced. The PoC keeps the surface tiny so
# that tests can pass a plain async function.
LLMCallable = Callable[[str], Awaitable[str]]


@dataclass
class _AttemptOutcome:
    decision: PolicyDecisionV3 | None
    raw_text: str | None
    failure_reason: DegradeReason | None


class LLMTimeout(Exception):
    """Raised by the caller's LLMCallable to signal a timeout."""


class LLMProviderError(Exception):
    """Raised by the caller's LLMCallable to signal a provider/network error."""


class PolicyCoreV3Invoker:
    """The only place where Policy-Core v3 contacts an LLM."""

    def __init__(self, llm: LLMCallable) -> None:
        self._llm = llm

    async def invoke(
        self, turn: PolicyTurnInput
    ) -> PolicyDecisionV3 | DegradeVerdict:
        attempts_done = 0
        retry_hint: str | None = None
        last_raw: str | None = None
        last_reason: DegradeReason = DegradeReason.schema_invalid

        allowed_tool_ids = {t.id for t in turn.tool_contracts} | {"none"}
        allowed_intents = {i.value for i in Intent}

        while attempts_done < MAX_ATTEMPTS:
            attempts_done += 1
            prompt = build_prompt(turn, retry_hint=retry_hint)
            outcome = await self._one_attempt(
                prompt=prompt,
                allowed_tool_ids=allowed_tool_ids,
                allowed_intents=allowed_intents,
            )
            if outcome.decision is not None:
                return outcome.decision

            last_raw = outcome.raw_text
            last_reason = outcome.failure_reason or DegradeReason.schema_invalid
            decision = next_retry_action(last_reason, attempts_done)
            if not decision.should_retry:
                break
            retry_hint = decision.retry_hint

        return DegradeVerdict(
            degrade_reason=last_reason,
            last_raw_output=_truncate(last_raw, 2000),
            attempts=attempts_done,
            notes="policy_core_v3_retry_exhausted",
        )

    async def _one_attempt(
        self,
        *,
        prompt: str,
        allowed_tool_ids: set[str],
        allowed_intents: set[str],
    ) -> _AttemptOutcome:
        # Call the LLM
        try:
            raw = await self._llm(prompt)
        except LLMTimeout:
            reason = classify_failure(
                raw_text=None,
                parse_error=None,
                timed_out=True,
                provider_error=False,
                tool_unknown=False,
                intent_unknown=False,
            )
            return _AttemptOutcome(decision=None, raw_text=None, failure_reason=reason)
        except LLMProviderError:
            reason = classify_failure(
                raw_text=None,
                parse_error=None,
                timed_out=False,
                provider_error=True,
                tool_unknown=False,
                intent_unknown=False,
            )
            return _AttemptOutcome(decision=None, raw_text=None, failure_reason=reason)

        if raw is None or not raw.strip():
            reason = classify_failure(
                raw_text=raw or "",
                parse_error=None,
                timed_out=False,
                provider_error=False,
                tool_unknown=False,
                intent_unknown=False,
            )
            return _AttemptOutcome(decision=None, raw_text=raw, failure_reason=reason)

        # Parse JSON
        candidate = _extract_json_object(raw)
        if candidate is None:
            reason = classify_failure(
                raw_text=raw,
                parse_error="json_extraction_failed",
                timed_out=False,
                provider_error=False,
                tool_unknown=False,
                intent_unknown=False,
            )
            return _AttemptOutcome(decision=None, raw_text=raw, failure_reason=reason)

        # Pre-check intent and tool against allowed sets BEFORE pydantic, so
        # we can route to the right retry hint.
        intent_value = candidate.get("intent")
        if intent_value not in allowed_intents:
            reason = classify_failure(
                raw_text=raw,
                parse_error=None,
                timed_out=False,
                provider_error=False,
                tool_unknown=False,
                intent_unknown=True,
            )
            return _AttemptOutcome(decision=None, raw_text=raw, failure_reason=reason)

        action = candidate.get("candidate_action") or {}
        tool_id = action.get("tool") if isinstance(action, dict) else None
        if tool_id is not None and tool_id not in allowed_tool_ids:
            reason = classify_failure(
                raw_text=raw,
                parse_error=None,
                timed_out=False,
                provider_error=False,
                tool_unknown=True,
                intent_unknown=False,
            )
            return _AttemptOutcome(decision=None, raw_text=raw, failure_reason=reason)

        # Pydantic validation
        try:
            decision = PolicyDecisionV3.model_validate(candidate)
        except ValidationError as exc:
            reason = classify_failure(
                raw_text=raw,
                parse_error=str(exc),
                timed_out=False,
                provider_error=False,
                tool_unknown=False,
                intent_unknown=False,
            )
            return _AttemptOutcome(decision=None, raw_text=raw, failure_reason=reason)

        return _AttemptOutcome(decision=decision, raw_text=raw, failure_reason=None)


def _extract_json_object(text: str) -> dict | None:
    """Extract a single JSON object from raw model output.

    Tolerates leading/trailing whitespace and common ```json fences. Does NOT
    do scenario-specific repair — only structural extraction.
    """
    s = text.strip()
    if s.startswith("```"):
        # strip optional fenced block
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
        s = s.strip()
    # try direct parse
    try:
        obj = json.loads(s)
    except json.JSONDecodeError:
        # fallback: find first { and last } and try
        start = s.find("{")
        end = s.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            obj = json.loads(s[start : end + 1])
        except json.JSONDecodeError:
            return None
    return obj if isinstance(obj, dict) else None


def _truncate(text: str | None, limit: int) -> str | None:
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[:limit] + "...[truncated]"
