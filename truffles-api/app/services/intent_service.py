import json
import math
import os
import re
import time
from copy import deepcopy
from enum import Enum
from typing import Any, Iterable, Mapping, Tuple

import httpx

from app.core.policy_tool_projector import build_binding_plan
from app.core.semantic_decision import SemanticDecisionV1
from app.logging_config import get_logger, record_llm_time
from app.schemas.intent import (
    LlmPolicyCoreOutput,
    validate_llm_plan_output,
    validate_llm_policy_core_output,
)
from app.services.ai_service import (
    FAST_MODEL,
    INTENT_TIMEOUT_SECONDS,
    _append_llm_budget_event,
    _current_openai_api_key,
    _record_pipeline_budget_skip,
    _remaining_pipeline_budget_ms,
    _should_attempt_llm,
    consume_llm_budget,
    get_llm_provider,
    normalize_for_matching,
)
from app.services.knowledge_service import QDRANT_COLLECTION as KNOWLEDGE_QDRANT_COLLECTION

logger = get_logger("intent_service")
_SECONDARY_SEMANTIC_OWNER_REMOVED = "secondary_semantic_owner_removed"
_BOOKING_MANAGE_REFERENCE_INTENTS = {
    "check_booking",
    "verify_booking",
    "confirm_booking",
    "booking_confirmation",
}
_POLICY_CORE_EXPLICIT_CLOCK_TIME_PATTERN = re.compile(
    r"(?<!\d)(?:[01]?\d|2[0-3])[:.][0-5]\d(?!\d)"
)
_POLICY_CORE_HOUR_TIME_PATTERN = re.compile(
    r"\b(?:в|к|на)\s*(?:[01]?\d|2[0-3])(?:\s*час(?:а|ов)?)?\b",
    re.IGNORECASE,
)
_POLICY_CORE_GENERIC_AVAILABILITY_QUERY_PATTERNS = (
    re.compile(
        r"\b(?:когда|какое|на какое|во сколько)\b.*\b(?:время|слот(?:ы|ов)?|окн(?:о|а|е)?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:есть(?:\s+ли)?|будет(?:\s+ли)?)\b.*\b(?:время|слот(?:ы|ов)?|окн(?:о|а|е)?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:свободн\w*|доступн\w*)\b.*\b(?:время|слот(?:ы|ов)?|окн(?:о|а|е)?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bкогда\b.*\bзаписа(?:ться|т[ья])\b", re.IGNORECASE),
)
_POLICY_CORE_SERVICE_PRESENCE_QUERY_PATTERNS = (
    re.compile(r"\bзанимает(?:есь|ся)\b", re.IGNORECASE),
    re.compile(r"\bделаете\b", re.IGNORECASE),
    re.compile(r"\bоказываете\b", re.IGNORECASE),
    re.compile(r"\bпредлагаете\b", re.IGNORECASE),
    re.compile(r"\bкакие\b.*\b(?:услуг\w*|процедур\w*|сервис\w*)\b", re.IGNORECASE),
    re.compile(r"\bwhat\b.*\bservices?\b", re.IGNORECASE),
    re.compile(r"\bservices?\b.*\b(?:available|have|offer)\b", re.IGNORECASE),
)
_POLICY_CORE_PROMOTIONS_QUERY_PATTERNS = (
    re.compile(r"\bскидк\w*\b", re.IGNORECASE),
    re.compile(r"\bакци\w*\b", re.IGNORECASE),
    re.compile(r"\bпромо(?:код\w*)?\b", re.IGNORECASE),
    re.compile(r"\bpromo(?:code|codes)?\b", re.IGNORECASE),
    re.compile(r"\bpromotion(?:s)?\b", re.IGNORECASE),
)
_POLICY_CORE_LOCATION_SIDE_ASK_PATTERNS = (
    re.compile(r"\bадрес\w*\b", re.IGNORECASE),
    re.compile(r"\bгде\b.*\bнаходит\w*\b", re.IGNORECASE),
    re.compile(r"\bкак\s+вас\s+найти\b", re.IGNORECASE),
    re.compile(r"\bhow\s+to\s+find\b", re.IGNORECASE),
)
_POLICY_CORE_HOURS_ASK_PATTERNS = (
    re.compile(r"\bработа(?:ете|ет|ют)\b", re.IGNORECASE),
    re.compile(r"\b(?:часы|режим)\s+работы\b", re.IGNORECASE),
    re.compile(r"\bдо\s+скольк(?:и|о)\b", re.IGNORECASE),
    re.compile(r"\bсо\s+скольк(?:и|о)\b", re.IGNORECASE),
    re.compile(r"\bopening\s+hours\b", re.IGNORECASE),
)
_POLICY_CORE_BOOKING_SIDE_ASK_PATTERNS = (
    re.compile(r"\bзапис", re.IGNORECASE),
    re.compile(r"\bbook\b", re.IGNORECASE),
    re.compile(r"\bappointment\b", re.IGNORECASE),
)
_POLICY_CORE_MESSAGE_GROUNDED_TEMPORAL_CLUE_PATTERNS = (
    re.compile(
        r"\b(?:сегодня|завтра|послезавтра|утр(?:о|ом)|вечер(?:ом)?|дн[её]м|ноч(?:ь|ью)|после|до)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:понедельник(?:а|у|е)?|вторник(?:а|у|е)?|сред(?:а|у|е|ы)|четверг(?:а|у|е)?|пятниц(?:а|у|е|ы)|суббот(?:а|у|е|ы)|воскресень(?:е|я|ю))\b",
        re.IGNORECASE,
    ),
)
_POLICY_CORE_MESSAGE_RELATIVE_DAY_PATTERN = re.compile(
    r"\b(?:сегодня|завтра|послезавтра)\b",
    re.IGNORECASE,
)
_POLICY_CORE_MESSAGE_WEEKDAY_PATTERN = re.compile(
    r"\b(?:понедельник(?:а|у|е)?|вторник(?:а|у|е)?|сред(?:а|у|е|ы)|четверг(?:а|у|е)?|пятниц(?:а|у|е|ы)|суббот(?:а|у|е|ы)|воскресень(?:е|я|ю))\b",
    re.IGNORECASE,
)
_POLICY_CORE_MESSAGE_NUMERIC_DATE_PATTERN = re.compile(
    r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b",
    re.IGNORECASE,
)
_POLICY_CORE_EXPLICIT_CUSTOMER_NAME_INTRO_PATTERNS = (
    re.compile(r"\bменя\s+зовут\b", re.IGNORECASE),
    re.compile(r"\bмо[её]\s+имя\b", re.IGNORECASE),
    re.compile(r"\bmy\s+name\s+is\b", re.IGNORECASE),
    re.compile(r"\bi\s+am\b", re.IGNORECASE),
    re.compile(r"\bi['’]m\b", re.IGNORECASE),
    re.compile(
        r"^\s*я\s+[A-Za-zА-Яа-яЁё-]+(?:\s+[A-Za-zА-Яа-яЁё-]+){0,2}[.!?]?\s*$",
        re.IGNORECASE,
    ),
)
_POLICY_CORE_HYPOTHETICAL_CANCEL_QUERY_PATTERNS = (
    re.compile(r"^\s*(?:а\s+)?если\b", re.IGNORECASE),
    re.compile(r"\bзахочу\b", re.IGNORECASE),
    re.compile(r"^\s*как\b", re.IGNORECASE),
    re.compile(r"\bможно\s+ли\b", re.IGNORECASE),
    re.compile(r"\bwhat\s+if\b", re.IGNORECASE),
    re.compile(r"\bcan\s+i\b", re.IGNORECASE),
)
_POLICY_CORE_CYRILLIC_PATTERN = re.compile(r"[А-Яа-яЁё]")
_POLICY_CORE_LATIN_PATTERN = re.compile(r"[A-Za-z]")


def _log_timing(
    stage: str,
    elapsed_ms: float,
    *,
    timing_context: dict | None = None,
    extra: dict | None = None,
) -> None:
    context: dict = {}
    if isinstance(timing_context, dict):
        context.update(timing_context)
    if extra:
        context.update(extra)
    context["stage"] = stage
    context["elapsed_ms"] = round(elapsed_ms, 2)
    for key in ("message_id", "outbox_id", "trace_id"):
        context.setdefault(key, None)
    if isinstance(timing_context, dict):
        timing = timing_context.get("timing")
        if not isinstance(timing, dict):
            timing = {}
        stages = timing.get("stages")
        if not isinstance(stages, dict):
            stages = {}
        stages[stage] = context["elapsed_ms"]
        timing["stages"] = stages
        timing_context["timing"] = timing
    logger.info("Timing", extra={"context": context})


def _classify_llm_error(exc: Exception) -> str:
    raw = str(exc or "")
    token = normalize_for_matching(raw)
    combined = " ".join(part for part in (raw.casefold(), token) if part).strip()
    if not combined:
        return "error"
    if any(
        marker in combined
        for marker in (
            "deadline_exceeded",
            "timed out",
            "timeout",
            "readtimeout",
            "connecttimeout",
        )
    ):
        return "timeout"
    if "insufficient_quota" in combined or "insufficient quota" in combined:
        return "insufficient_quota"
    if "rate_limit" in combined or "rate limit" in combined:
        return "rate_limit"
    if "invalid_api_key" in combined or "invalid api key" in combined:
        return "invalid_api_key"
    if (
        "unauthorized" in combined
        or "authentication" in combined
        or " 401 " in f" {combined} "
    ):
        return "unauthorized"
    if (
        "model_not_found" in combined
        or "does not exist" in combined
        or "unknown model" in combined
    ):
        return "model_not_found"
    if (
        "context_length_exceeded" in combined
        or "maximum context length" in combined
        or "too many tokens" in combined
    ):
        return "context_length"
    if (
        "invalid_request_error" in combined
        or "invalid request" in combined
        or "unsupported value" in combined
        or "bad request" in combined
        or " 400 " in f" {combined} "
    ):
        return "invalid_request"
    if (
        "connection refused" in combined
        or "connection reset" in combined
        or "connection aborted" in combined
        or "temporarily unavailable" in combined
        or "name or service not known" in combined
        or "nodename nor servname" in combined
    ):
        return "connection_error"
    if (
        "service unavailable" in combined
        or "server overloaded" in combined
        or "overloaded" in combined
        or " 503 " in f" {combined} "
    ):
        return "service_unavailable"
    return "error"

QDRANT_HOST = os.environ.get("QDRANT_HOST", "http://qdrant:6333")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION") or KNOWLEDGE_QDRANT_COLLECTION

RAG_BM25_LIMIT = int(os.environ.get("RAG_BM25_LIMIT", "5"))
RAG_BM25_MAX_DOCS = int(os.environ.get("RAG_BM25_MAX_DOCS", "200"))
RAG_BM25_TIMEOUT_SECONDS = float(os.environ.get("RAG_BM25_TIMEOUT_SECONDS", "0.8"))
RAG_HYBRID_VECTOR_WEIGHT = float(os.environ.get("RAG_HYBRID_VECTOR_WEIGHT", "0.6"))
RAG_HYBRID_BM25_WEIGHT = float(os.environ.get("RAG_HYBRID_BM25_WEIGHT", "0.4"))

CONTROLLER_TIMEOUT_SECONDS = float(os.environ.get("ROUTER_TIMEOUT_SECONDS", "3.0"))
CONTROLLER_MAX_TOKENS = int(os.environ.get("ROUTER_MAX_TOKENS", "140"))
CONTROLLER_CONFIDENCE_THRESHOLD = float(os.environ.get("ROUTER_CONFIDENCE_THRESHOLD", "0.30"))
_DEFAULT_CONTROLLER_MODEL = FAST_MODEL
CONTROLLER_MODEL = os.environ.get("ROUTER_MODEL", _DEFAULT_CONTROLLER_MODEL).strip()
PLAN_TIMEOUT_SECONDS = float(os.environ.get("LLM_PLAN_TIMEOUT_SECONDS", "3.0"))
PLAN_MAX_TOKENS = int(os.environ.get("LLM_PLAN_MAX_TOKENS", "220"))
PLAN_MODEL = os.environ.get("LLM_PLAN_MODEL", CONTROLLER_MODEL).strip()
PLAN_CONFIDENCE_THRESHOLD = float(os.environ.get("LLM_PLAN_CONFIDENCE_THRESHOLD", "0.3"))
POLICY_CORE_TIMEOUT_SECONDS = float(
    os.environ.get("LLM_POLICY_CORE_TIMEOUT_SECONDS", "15.0")
)
POLICY_CORE_MIN_TIMEOUT_SECONDS = max(
    float(os.environ.get("LLM_POLICY_CORE_MIN_TIMEOUT_SECONDS", "1.2")),
    0.1,
)
POLICY_CORE_BUDGET_GUARD_MS = max(
    float(os.environ.get("LLM_POLICY_CORE_BUDGET_GUARD_MS", "200")),
    0.0,
)
POLICY_CORE_RETRY_TIMEOUT_SECONDS = max(
    float(os.environ.get("LLM_POLICY_CORE_TIMEOUT_RETRY_SECONDS", "4.0")),
    0.1,
)
POLICY_CORE_FALLBACK_TIMEOUT_SECONDS = max(
    float(os.environ.get("LLM_POLICY_CORE_TIMEOUT_FALLBACK_SECONDS", "6.0")),
    0.1,
)
POLICY_CORE_RETRY_ON_TIMEOUT = os.environ.get("LLM_POLICY_CORE_RETRY_ON_TIMEOUT")
POLICY_CORE_RETRY_ON_TRANSIENT = os.environ.get("LLM_POLICY_CORE_RETRY_ON_TRANSIENT")
POLICY_CORE_MAX_TOKENS = int(os.environ.get("LLM_POLICY_CORE_MAX_TOKENS", "240"))
_DEFAULT_POLICY_CORE_MODEL = (
    os.environ.get("LLM_SEMANTIC_OWNER_MODEL", "gpt-5.4-nano-2026-03-17").strip()
    or "gpt-5.4-nano-2026-03-17"
)
POLICY_CORE_MODEL = os.environ.get("LLM_POLICY_CORE_MODEL", _DEFAULT_POLICY_CORE_MODEL).strip()
POLICY_CORE_TIMEOUT_FALLBACK_MODEL = os.environ.get(
    "LLM_POLICY_CORE_TIMEOUT_FALLBACK_MODEL",
    "",
).strip()
POLICY_CORE_REASONING_EFFORT = (
    os.environ.get("LLM_POLICY_CORE_REASONING_EFFORT", "low").strip().lower()
)
POLICY_CORE_GPT5_MIN_MAX_TOKENS = max(
    int(os.environ.get("LLM_POLICY_CORE_GPT5_MIN_MAX_TOKENS", "800")),
    1,
)
POLICY_CORE_GPT5_COMPACT_MIN_MAX_TOKENS = max(
    int(os.environ.get("LLM_POLICY_CORE_GPT5_COMPACT_MIN_MAX_TOKENS", "560")),
    1,
)
POLICY_CORE_CONFIDENCE_THRESHOLD = float(
    os.environ.get("LLM_POLICY_CORE_CONFIDENCE_THRESHOLD", "0.3")
)
POLICY_CORE_COMPACT_TRIGGER_TIMEOUT_SECONDS = max(
    float(os.environ.get("LLM_POLICY_CORE_COMPACT_TRIGGER_TIMEOUT_SECONDS", "1.8")),
    0.2,
)
POLICY_CORE_COMPACT_MESSAGE_MAX_CHARS = max(
    int(os.environ.get("LLM_POLICY_CORE_COMPACT_MESSAGE_MAX_CHARS", "420")),
    120,
)
POLICY_CORE_COMPACT_MEMORY_SUMMARY_MAX_CHARS = max(
    int(os.environ.get("LLM_POLICY_CORE_COMPACT_MEMORY_SUMMARY_MAX_CHARS", "180")),
    80,
)
POLICY_CORE_COMPACT_PROFILE_ITEMS_MAX = max(
    int(os.environ.get("LLM_POLICY_CORE_COMPACT_PROFILE_ITEMS_MAX", "3")),
    1,
)
POLICY_CORE_COMPACT_REF_LIMIT = max(
    int(os.environ.get("LLM_POLICY_CORE_COMPACT_REF_LIMIT", "6")),
    1,
)
POLICY_CORE_MEMORY_SUMMARY_MAX_CHARS = max(
    int(os.environ.get("LLM_POLICY_CORE_MEMORY_SUMMARY_MAX_CHARS", "360")),
    80,
)
POLICY_CORE_MEMORY_PROFILE_MAX_ITEMS = max(
    int(os.environ.get("LLM_POLICY_CORE_MEMORY_PROFILE_MAX_ITEMS", "8")),
    1,
)
POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS = max(
    int(os.environ.get("LLM_POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS", "120")),
    40,
)
POLICY_CORE_CONTEXT_CARD_LIMIT = max(
    int(os.environ.get("LLM_POLICY_CORE_CONTEXT_CARD_LIMIT", "6")),
    1,
)
POLICY_CORE_STRUCTURED_OUTPUT = os.environ.get("LLM_POLICY_CORE_STRUCTURED_OUTPUT")
POLICY_CORE_MICRO_TIMEOUT_SECONDS = max(
    float(os.environ.get("LLM_POLICY_CORE_MICRO_TIMEOUT_SECONDS", "0.8")),
    0.2,
)
POLICY_CORE_MICRO_MIN_REMAINING_MS = max(
    float(os.environ.get("LLM_POLICY_CORE_MICRO_MIN_REMAINING_MS", "350")),
    0.0,
)
SPECIALIST_HINT_TIMEOUT_SECONDS = max(
    float(os.environ.get("LLM_SPECIALIST_HINT_TIMEOUT_SECONDS", "1.4")),
    0.2,
)
SPECIALIST_HINT_MIN_TIMEOUT_SECONDS = max(
    float(os.environ.get("LLM_SPECIALIST_HINT_MIN_TIMEOUT_SECONDS", "0.35")),
    0.1,
)
SPECIALIST_HINT_BUDGET_GUARD_MS = max(
    float(os.environ.get("LLM_SPECIALIST_HINT_BUDGET_GUARD_MS", "120")),
    0.0,
)
SPECIALIST_HINT_MAX_TOKENS = max(
    int(os.environ.get("LLM_SPECIALIST_HINT_MAX_TOKENS", "90")),
    32,
)
SPECIALIST_HINT_CONFIDENCE_THRESHOLD = min(
    max(float(os.environ.get("LLM_SPECIALIST_HINT_CONFIDENCE_THRESHOLD", "0.55")), 0.0),
    1.0,
)
SPECIALIST_HINT_MODEL = os.environ.get(
    "LLM_SPECIALIST_HINT_MODEL",
    POLICY_CORE_MODEL,
).strip()
CUSTOMER_NAME_HINT_TIMEOUT_SECONDS = max(
    float(os.environ.get("LLM_CUSTOMER_NAME_HINT_TIMEOUT_SECONDS", "1.4")),
    0.2,
)
CUSTOMER_NAME_HINT_MIN_TIMEOUT_SECONDS = max(
    float(os.environ.get("LLM_CUSTOMER_NAME_HINT_MIN_TIMEOUT_SECONDS", "0.35")),
    0.1,
)
CUSTOMER_NAME_HINT_BUDGET_GUARD_MS = max(
    float(os.environ.get("LLM_CUSTOMER_NAME_HINT_BUDGET_GUARD_MS", "120")),
    0.0,
)
CUSTOMER_NAME_HINT_MAX_TOKENS = max(
    int(os.environ.get("LLM_CUSTOMER_NAME_HINT_MAX_TOKENS", "90")),
    32,
)
CUSTOMER_NAME_HINT_CONFIDENCE_THRESHOLD = min(
    max(float(os.environ.get("LLM_CUSTOMER_NAME_HINT_CONFIDENCE_THRESHOLD", "0.55")), 0.0),
    1.0,
)
CUSTOMER_NAME_HINT_MODEL = os.environ.get(
    "LLM_CUSTOMER_NAME_HINT_MODEL",
    POLICY_CORE_MODEL,
).strip()
SERVICE_QUERY_HINT_TIMEOUT_SECONDS = max(
    float(os.environ.get("LLM_SERVICE_QUERY_HINT_TIMEOUT_SECONDS", "1.4")),
    0.2,
)
SERVICE_QUERY_HINT_MIN_TIMEOUT_SECONDS = max(
    float(os.environ.get("LLM_SERVICE_QUERY_HINT_MIN_TIMEOUT_SECONDS", "0.35")),
    0.1,
)
SERVICE_QUERY_HINT_BUDGET_GUARD_MS = max(
    float(os.environ.get("LLM_SERVICE_QUERY_HINT_BUDGET_GUARD_MS", "120")),
    0.0,
)
SERVICE_QUERY_HINT_MAX_TOKENS = max(
    int(os.environ.get("LLM_SERVICE_QUERY_HINT_MAX_TOKENS", "90")),
    32,
)
SERVICE_QUERY_HINT_CONFIDENCE_THRESHOLD = min(
    max(float(os.environ.get("LLM_SERVICE_QUERY_HINT_CONFIDENCE_THRESHOLD", "0.55")), 0.0),
    1.0,
)
SERVICE_QUERY_HINT_MODEL = os.environ.get(
    "LLM_SERVICE_QUERY_HINT_MODEL",
    POLICY_CORE_MODEL,
).strip()
ANSWER_INTERPRETER_TIMEOUT_SECONDS = float(
    os.environ.get("ANSWER_INTERPRETER_TIMEOUT_SECONDS", "2.5")
)
ANSWER_INTERPRETER_MAX_TOKENS = int(os.environ.get("ANSWER_INTERPRETER_MAX_TOKENS", "120"))
ANSWER_INTERPRETER_MODEL = os.environ.get("ANSWER_INTERPRETER_MODEL", CONTROLLER_MODEL).strip()


def _resolve_policy_core_timeout_seconds(timing_context: dict | None) -> float:
    remaining_ms = _remaining_pipeline_budget_ms(timing_context)
    if remaining_ms is None:
        return max(POLICY_CORE_TIMEOUT_SECONDS, 0.0)
    available_ms = max(0.0, remaining_ms - POLICY_CORE_BUDGET_GUARD_MS)
    if available_ms <= 0:
        return 0.0
    return min(max(POLICY_CORE_TIMEOUT_SECONDS, 0.0), available_ms / 1000.0)


def _resolve_policy_core_micro_timeout_seconds(timing_context: dict | None) -> float:
    remaining_ms = _remaining_pipeline_budget_ms(timing_context)
    if remaining_ms is None:
        return 0.0
    soft_guard_ms = max(POLICY_CORE_BUDGET_GUARD_MS * 0.5, 0.0)
    available_ms = max(0.0, remaining_ms - soft_guard_ms)
    if available_ms < POLICY_CORE_MICRO_MIN_REMAINING_MS:
        return 0.0
    return min(POLICY_CORE_MICRO_TIMEOUT_SECONDS, max(available_ms / 1000.0, 0.0))


def _resolve_policy_core_max_tokens(timeout_seconds: float) -> int:
    return _resolve_policy_core_max_tokens_with_cap(timeout_seconds, None)


def _resolve_policy_core_max_tokens_with_cap(
    timeout_seconds: float,
    max_tokens_override: int | None,
    model_name: str | None = None,
    *,
    compact_mode: bool = False,
) -> int:
    max_tokens_cap = POLICY_CORE_MAX_TOKENS
    if max_tokens_override is not None:
        try:
            max_tokens_cap = int(max_tokens_override)
        except (TypeError, ValueError):
            max_tokens_cap = POLICY_CORE_MAX_TOKENS
    max_tokens_cap = max(1, min(POLICY_CORE_MAX_TOKENS, max_tokens_cap))
    if timeout_seconds <= 0:
        return min(max_tokens_cap, 120)
    if timeout_seconds < 1.4:
        return min(max_tokens_cap, 120)
    if timeout_seconds < 2.2:
        resolved = min(max_tokens_cap, 160)
    elif timeout_seconds < 3.0:
        resolved = min(max_tokens_cap, 200)
    else:
        resolved = max_tokens_cap
    if (
        isinstance(model_name, str)
        and model_name.strip().lower().startswith("gpt-5")
    ):
        if max_tokens_override is not None:
            return max(resolved, POLICY_CORE_GPT5_MIN_MAX_TOKENS)
        min_tokens = (
            POLICY_CORE_GPT5_COMPACT_MIN_MAX_TOKENS
            if compact_mode
            else POLICY_CORE_GPT5_MIN_MAX_TOKENS
        )
        return max(resolved, min_tokens)
    return resolved


def _resolve_policy_core_reasoning_effort(model_name: str | None) -> str | None:
    normalized = (model_name or "").strip().lower()
    if not normalized.startswith("gpt-5"):
        return None
    if POLICY_CORE_REASONING_EFFORT == "minimal":
        return "low"
    if POLICY_CORE_REASONING_EFFORT in {"none", "low", "medium", "high", "xhigh"}:
        return POLICY_CORE_REASONING_EFFORT
    return "low"


def _resolve_model_temperature(model_name: str | None) -> float | None:
    normalized = (model_name or "").strip().lower()
    if normalized.startswith("gpt-5"):
        return None
    return 0.0


def _policy_core_structured_output_enabled() -> bool:
    return _is_env_enabled(POLICY_CORE_STRUCTURED_OUTPUT, default=True)


def _policy_core_uses_response_format(error: Exception) -> bool:
    message = normalize_for_matching(str(error or ""))
    if not message:
        return False
    return any(
        marker in message
        for marker in (
            "response format",
            "response_format",
            "json_schema",
            "json schema",
        )
    )



def _build_policy_core_messages(prompt: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def _build_policy_core_compact_input(policy_input: dict[str, Any]) -> dict[str, Any]:
    compact_input: dict[str, Any] = dict(policy_input)
    pending_expected_reply_type: str | None = None

    raw_message = compact_input.get("message")
    if isinstance(raw_message, str):
        compact_input["message"] = " ".join(raw_message.split())[
            :POLICY_CORE_COMPACT_MESSAGE_MAX_CHARS
        ]

    allowed_payload = compact_input.get("allowed")
    if isinstance(allowed_payload, dict):
        normalized_allowed = dict(allowed_payload)
        for refs_key in ("info_refs", "consult_refs"):
            refs = normalized_allowed.get(refs_key)
            if isinstance(refs, list):
                cleaned_refs = [
                    ref.strip()
                    for ref in refs
                    if isinstance(ref, str) and ref.strip()
                ]
                normalized_allowed[refs_key] = cleaned_refs[:POLICY_CORE_COMPACT_REF_LIMIT]
        compact_input["allowed"] = normalized_allowed

    memory_payload = compact_input.get("memory")
    if isinstance(memory_payload, dict):
        normalized_memory = dict(memory_payload)
        summary = normalized_memory.get("summary")
        if isinstance(summary, str):
            normalized_memory["summary"] = " ".join(summary.split())[
                :POLICY_CORE_COMPACT_MEMORY_SUMMARY_MAX_CHARS
            ]
        profile = normalized_memory.get("profile")
        if isinstance(profile, dict):
            normalized_profile = dict(profile)
            pending_contract = normalized_profile.get("pending_question_contract")
            if isinstance(pending_contract, dict):
                raw_expected_reply_type = pending_contract.get("expected_reply_type")
                if isinstance(raw_expected_reply_type, str) and raw_expected_reply_type.strip():
                    pending_expected_reply_type = raw_expected_reply_type.strip().casefold()
            retrieved_items = normalized_profile.get("retrieved_items")
            if isinstance(retrieved_items, list):
                normalized_profile["retrieved_items"] = retrieved_items[
                    :POLICY_CORE_COMPACT_PROFILE_ITEMS_MAX
                ]
            stored_keys = normalized_profile.get("stored_keys")
            if isinstance(stored_keys, list):
                normalized_profile["stored_keys"] = stored_keys[
                    :POLICY_CORE_COMPACT_PROFILE_ITEMS_MAX
                ]
            active_slots = normalized_profile.get("active_slots")
            if isinstance(active_slots, list):
                normalized_profile["active_slots"] = active_slots[:3]
            normalized_memory["profile"] = normalized_profile
        compact_input["memory"] = normalized_memory

    context_payload = compact_input.get("context")
    if isinstance(context_payload, dict):
        normalized_context = _compact_policy_core_context(context_payload)
        if pending_expected_reply_type and pending_expected_reply_type != "media":
            normalized_allowed = compact_input.get("allowed")
            if isinstance(normalized_allowed, dict):
                narrowed_allowed = dict(normalized_allowed)
                narrowed_allowed.pop("consult_refs", None)
                compact_input["allowed"] = narrowed_allowed
            if isinstance(normalized_context, dict):
                normalized_context.pop("consult_cards", None)
        if normalized_context:
            compact_input["context"] = normalized_context
        else:
            compact_input.pop("context", None)

    return compact_input


def _policy_core_prefers_compact_first_attempt(memory_profile: dict[str, Any] | None) -> bool:
    if not isinstance(memory_profile, dict):
        return False
    pending_contract = memory_profile.get("pending_question_contract")
    if not isinstance(pending_contract, dict):
        return False
    expected_reply_type = pending_contract.get("expected_reply_type")
    if not isinstance(expected_reply_type, str) or not expected_reply_type.strip():
        return False
    return expected_reply_type.strip().casefold() != "media"


def _sanitize_policy_core_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    sanitized_payload = dict(payload)
    sanitized = False
    if "tool_args" in sanitized_payload:
        sanitized_payload.pop("tool_args", None)
        sanitized = True
    if "tool_action_hint" not in sanitized_payload and "tool_action" in sanitized_payload:
        sanitized_payload["tool_action_hint"] = sanitized_payload.get("tool_action")
        sanitized = True
    if "tool_action" in sanitized_payload:
        sanitized_payload.pop("tool_action", None)
        sanitized = True

    def _token(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip().casefold()
        return cleaned or None

    tool_action_hint = _token(sanitized_payload.get("tool_action_hint"))
    action = _token(sanitized_payload.get("action"))
    intent = _token(sanitized_payload.get("intent"))
    subject_kind = _token(sanitized_payload.get("subject_kind"))
    capability = _token(sanitized_payload.get("capability"))
    reason = _token(sanitized_payload.get("reason"))
    next_question = _token(sanitized_payload.get("next_question"))
    open_questions = {
        _token(item)
        for item in sanitized_payload.get("open_questions") or []
        if _token(item) is not None
    }
    if (
        tool_action_hint == "calendar.get_booking"
        and subject_kind == "booking"
        and capability == "booking_manage"
        and reason is not None
        and reason.startswith("calendar_get_booking_collect_reference")
        and (next_question == "name" or "name" in open_questions)
    ):
        for field_name in (
            "pending_question_act",
            "pending_question_target",
            "active_question_relation",
        ):
            if sanitized_payload.pop(field_name, None) is not None:
                sanitized = True

    if intent == "master_query" and action == "fact":
        normalized_pack_refs_for_master = {
            _token(item)
            for item in sanitized_payload.get("pack_refs") or []
            if _token(item) is not None
        }
        if "master" in normalized_pack_refs_for_master and capability in {None, "portfolio", "master"}:
            if sanitized_payload.get("capability") != "master":
                sanitized_payload["capability"] = "master"
                sanitized = True
            capability = "master"

    if tool_action_hint == "catalog.service_query" and action == "fact":
        normalized_pack_refs = []
        for item in sanitized_payload.get("pack_refs") or []:
            if not isinstance(item, str) or not item.strip():
                continue
            normalized = item.strip().casefold()
            if (
                normalized
                in {
                    "pricing",
                    "duration",
                    "promotions",
                    "master",
                    "services_overview",
                    "contact",
                    "parking",
                }
                and normalized not in normalized_pack_refs
            ):
                normalized_pack_refs.append(normalized)
        supported_multi_refs = [
            ref for ref in _SERVICE_QUERY_MULTI_FACT_REFS if ref in normalized_pack_refs
        ]
        if (
            len(supported_multi_refs) > 1
            and set(supported_multi_refs) == set(normalized_pack_refs)
        ):
            if normalized_pack_refs != supported_multi_refs:
                sanitized_payload["pack_refs"] = supported_multi_refs
                sanitized = True
            return sanitized_payload, sanitized
        expected_pack_ref = None
        if len(normalized_pack_refs) == 1:
            expected_pack_ref = normalized_pack_refs[0]
        elif capability == "live_availability" or intent == "master_query":
            expected_pack_ref = "master"
        elif capability in {"pricing", "duration", "promotions", "master"}:
            expected_pack_ref = capability
        elif intent in {"pricing", "duration", "promotions"}:
            expected_pack_ref = intent
        if expected_pack_ref and normalized_pack_refs != [expected_pack_ref]:
            sanitized_payload["pack_refs"] = [expected_pack_ref]
            sanitized = True

    return sanitized_payload, sanitized


def _policy_core_has_grounded_referent(
    referents: Mapping[str, Any],
    key: str,
) -> bool:
    payload = referents.get(key) if isinstance(referents, Mapping) else None
    if not isinstance(payload, Mapping):
        return False
    for field_name in ("entity_id", "value"):
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip():
            return True
    return False


def _policy_core_active_pending_contract(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(normalized_memory_profile, Mapping):
        return {}
    pending = normalized_memory_profile.get("pending_question_contract")
    return dict(pending) if isinstance(pending, Mapping) else {}


def _policy_core_resume_pending_contract(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(normalized_memory_profile, Mapping):
        return {}
    pending = normalized_memory_profile.get("resume_pending_question_contract")
    return dict(pending) if isinstance(pending, Mapping) else {}


def _policy_core_expected_open_questions(contract_payload: Mapping[str, Any]) -> list[str]:
    raw_open_questions = contract_payload.get("open_questions") or []
    open_questions = [
        item
        for item in raw_open_questions
        if isinstance(item, str) and item.strip()
    ]
    if open_questions:
        return open_questions
    next_question = contract_payload.get("next_question")
    if isinstance(next_question, str) and next_question.strip():
        return [next_question]
    return []


def _policy_core_payload_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().casefold()
    return normalized or None


def _policy_core_payload_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        item.strip().casefold()
        for item in value
        if isinstance(item, str) and item.strip()
    ]


def _policy_core_payload_grounded_service(
    payload: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    slots = payload.get("slots")
    if isinstance(slots, Mapping):
        raw_value = slots.get("service")
        if isinstance(raw_value, str) and raw_value.strip():
            return " ".join(raw_value.split())
    referents = payload.get("referents")
    if isinstance(referents, Mapping):
        referent_payload = referents.get("service")
        if isinstance(referent_payload, Mapping):
            raw_value = referent_payload.get("value") or referent_payload.get("entity_id")
            if isinstance(raw_value, str) and raw_value.strip():
                return " ".join(raw_value.split())
    return None


def _policy_core_is_booking_time_followup_contract(
    contract_payload: Mapping[str, Any] | None,
) -> bool:
    if not isinstance(contract_payload, Mapping):
        return False
    pending_target = _policy_core_payload_token(contract_payload.get("pending_question_target"))
    pending_act = _policy_core_payload_token(contract_payload.get("pending_question_act"))
    expected_reply_type = _policy_core_payload_token(contract_payload.get("expected_reply_type"))
    next_question = _policy_core_payload_token(contract_payload.get("next_question"))
    return bool(
        pending_target == "time"
        or (
            pending_act == "ask_about_requested_slot"
            and (
                expected_reply_type in {"time", "name"}
                or next_question in {"datetime", "name"}
            )
        )
    )


def _policy_core_current_message_has_explicit_clock_time(
    current_message: str | None,
) -> bool:
    if not isinstance(current_message, str):
        return False
    normalized = " ".join(current_message.split())
    if not normalized:
        return False
    return bool(
        _POLICY_CORE_EXPLICIT_CLOCK_TIME_PATTERN.search(normalized)
        or _POLICY_CORE_HOUR_TIME_PATTERN.search(normalized)
    )


def _policy_core_current_message_has_message_grounded_temporal_clue(
    current_message: str | None,
) -> bool:
    if not isinstance(current_message, str):
        return False
    normalized = " ".join(current_message.split())
    if not normalized:
        return False
    if _policy_core_current_message_has_explicit_clock_time(normalized):
        return True
    return any(
        pattern.search(normalized)
        for pattern in _POLICY_CORE_MESSAGE_GROUNDED_TEMPORAL_CLUE_PATTERNS
    )


def _policy_core_current_message_has_explicit_customer_name_intro(
    current_message: str | None,
) -> bool:
    if not isinstance(current_message, str):
        return False
    normalized = " ".join(current_message.split())
    if not normalized:
        return False
    return any(
        pattern.search(normalized)
        for pattern in _POLICY_CORE_EXPLICIT_CUSTOMER_NAME_INTRO_PATTERNS
    )


def _policy_core_current_message_grounded_temporal_scope_hint(
    current_message: str | None,
) -> str | None:
    if not isinstance(current_message, str):
        return None
    normalized = " ".join(current_message.split())
    if not normalized:
        return None
    if _policy_core_current_message_has_explicit_clock_time(normalized):
        return "specific_time"
    if _POLICY_CORE_MESSAGE_WEEKDAY_PATTERN.search(normalized):
        return "weekday"
    if _POLICY_CORE_MESSAGE_RELATIVE_DAY_PATTERN.search(normalized):
        return "day"
    return None


def _policy_core_current_message_has_day_or_date_clue(
    current_message: str | None,
) -> bool:
    if not isinstance(current_message, str):
        return False
    normalized = " ".join(current_message.split())
    if not normalized:
        return False
    return bool(
        _POLICY_CORE_MESSAGE_RELATIVE_DAY_PATTERN.search(normalized)
        or _POLICY_CORE_MESSAGE_WEEKDAY_PATTERN.search(normalized)
        or _POLICY_CORE_MESSAGE_NUMERIC_DATE_PATTERN.search(normalized)
    )


def _policy_core_current_message_exact_datetime_surface(
    current_message: str | None,
) -> str | None:
    if not isinstance(current_message, str):
        return None
    normalized = " ".join(current_message.split())
    if not normalized:
        return None
    if not _policy_core_current_message_has_explicit_clock_time(normalized):
        return None
    starts = [
        match.start()
        for pattern in (
            _POLICY_CORE_MESSAGE_RELATIVE_DAY_PATTERN,
            _POLICY_CORE_MESSAGE_WEEKDAY_PATTERN,
            _POLICY_CORE_MESSAGE_NUMERIC_DATE_PATTERN,
        )
        for match in [pattern.search(normalized)]
        if match is not None
    ]
    if not starts:
        return None
    surface = normalized[min(starts):]
    clock_match = _POLICY_CORE_EXPLICIT_CLOCK_TIME_PATTERN.search(surface)
    if clock_match is not None:
        return surface[: clock_match.end()].strip(" ,.!?;:")
    hour_match = _POLICY_CORE_HOUR_TIME_PATTERN.search(surface)
    if hour_match is not None:
        return surface[: hour_match.end()].strip(" ,.!?;:")
    return surface.strip(" ,.!?:") or None


def _policy_core_temporal_clue_requires_message_grounded_alternate_datetime(
    alternate_datetime: str | None,
    current_message: str | None,
) -> bool:
    if not isinstance(alternate_datetime, str):
        return False
    normalized_alternate_datetime = " ".join(alternate_datetime.split())
    if not normalized_alternate_datetime:
        return False
    if not isinstance(current_message, str):
        return False
    normalized_message = " ".join(current_message.split())
    if not normalized_message:
        return False
    if normalized_alternate_datetime.casefold() in normalized_message.casefold():
        return False
    if not _policy_core_current_message_has_message_grounded_temporal_clue(normalized_message):
        return False
    if not _POLICY_CORE_CYRILLIC_PATTERN.search(normalized_message):
        return False
    return bool(
        _POLICY_CORE_LATIN_PATTERN.search(normalized_alternate_datetime)
        and not _POLICY_CORE_CYRILLIC_PATTERN.search(normalized_alternate_datetime)
    )


def _policy_core_current_message_is_generic_booking_availability_question(
    current_message: str | None,
) -> bool:
    if not isinstance(current_message, str):
        return False
    normalized = " ".join(current_message.split())
    if not normalized:
        return False
    if _policy_core_current_message_has_message_grounded_temporal_clue(normalized):
        return False
    return any(
        pattern.search(normalized)
        for pattern in _POLICY_CORE_GENERIC_AVAILABILITY_QUERY_PATTERNS
    )


def _policy_core_current_message_is_hypothetical_cancel_query(
    current_message: str | None,
) -> bool:
    if not isinstance(current_message, str):
        return False
    normalized = " ".join(current_message.split())
    if not normalized:
        return False
    return any(
        pattern.search(normalized)
        for pattern in _POLICY_CORE_HYPOTHETICAL_CANCEL_QUERY_PATTERNS
    )


def _policy_core_current_message_has_service_presence_query(
    current_message: str | None,
) -> bool:
    if not isinstance(current_message, str):
        return False
    normalized = " ".join(current_message.split())
    if not normalized:
        return False
    return any(
        pattern.search(normalized)
        for pattern in _POLICY_CORE_SERVICE_PRESENCE_QUERY_PATTERNS
    )


def _policy_core_current_message_has_location_side_ask(
    current_message: str | None,
) -> bool:
    if not isinstance(current_message, str):
        return False
    normalized = " ".join(current_message.split())
    if not normalized:
        return False
    return any(
        pattern.search(normalized)
        for pattern in _POLICY_CORE_LOCATION_SIDE_ASK_PATTERNS
    )


def _policy_core_current_message_has_hours_ask(
    current_message: str | None,
) -> bool:
    if not isinstance(current_message, str):
        return False
    normalized = " ".join(current_message.split())
    if not normalized:
        return False
    return any(
        pattern.search(normalized)
        for pattern in _POLICY_CORE_HOURS_ASK_PATTERNS
    )


def _policy_core_current_message_has_booking_side_ask(
    current_message: str | None,
) -> bool:
    if not isinstance(current_message, str):
        return False
    normalized = " ".join(current_message.split())
    if not normalized:
        return False
    return any(
        pattern.search(normalized)
        for pattern in _POLICY_CORE_BOOKING_SIDE_ASK_PATTERNS
    )


def _policy_core_current_message_has_temporal_booking_side_ask(
    current_message: str | None,
) -> bool:
    if _policy_core_current_message_has_booking_side_ask(current_message):
        return True
    if not _policy_core_current_message_has_message_grounded_temporal_clue(current_message):
        return False
    if not isinstance(current_message, str):
        return False
    normalized = " ".join(current_message.split())
    if not normalized:
        return False
    return bool(re.search(r"\bможно\b", normalized, re.IGNORECASE))


def _policy_core_current_message_hours_service_fact_pack_refs(
    current_message: str | None,
    *,
    client_slug: str | None = None,
) -> list[str] | None:
    if not isinstance(current_message, str) or not current_message.strip():
        return None
    if not _policy_core_current_message_has_hours_ask(current_message):
        return None
    normalized_message = _normalize_text(current_message)
    if not normalized_message:
        return None
    from app.services.pack_runtime_service import get_pack_runtime

    try:
        pack_runtime = get_pack_runtime(client_slug)
    except Exception:
        pack_runtime = None
    refs = ["hours"]
    if pack_runtime is not None:
        try:
            if _policy_core_current_message_has_promotions_query(current_message):
                refs.append("promotions")
        except Exception:
            pass
        try:
            if pack_runtime.has_price_signal(normalized_message, message=current_message):
                refs.append("pricing")
        except Exception:
            pass
        try:
            if pack_runtime.has_duration_signal(normalized_message, message=current_message):
                refs.append("duration")
        except Exception:
            pass
        try:
            if pack_runtime.has_master_signal(current_message):
                refs.append("master")
        except Exception:
            pass
        try:
            if pack_runtime.has_parking_signal(normalized_message):
                refs.append("parking")
        except Exception:
            pass
        try:
            if pack_runtime.has_contact_signal(normalized_message, message=current_message):
                refs.append("contact")
        except Exception:
            pass
    if (
        _policy_core_current_message_has_service_presence_query(current_message)
        and "services_overview" not in refs
    ):
        refs.append("services_overview")
    if len(refs) == 1:
        return None
    return refs


def _policy_core_current_message_location_service_fact_pack_refs(
    current_message: str | None,
    *,
    client_slug: str | None = None,
) -> list[str] | None:
    if not isinstance(current_message, str) or not current_message.strip():
        return None
    if not _policy_core_current_message_has_location_side_ask(current_message):
        return None
    normalized_message = _normalize_text(current_message)
    if not normalized_message:
        return None
    refs = ["location"]
    from app.services.pack_runtime_service import get_pack_runtime

    try:
        pack_runtime = get_pack_runtime(client_slug)
    except Exception:
        pack_runtime = None
    if pack_runtime is not None:
        try:
            if pack_runtime.has_price_signal(normalized_message, message=current_message):
                refs.append("pricing")
        except Exception:
            pass
        try:
            if pack_runtime.has_duration_signal(normalized_message, message=current_message):
                refs.append("duration")
        except Exception:
            pass
        try:
            if pack_runtime.has_master_signal(current_message):
                refs.append("master")
        except Exception:
            pass
        try:
            if pack_runtime.has_parking_signal(normalized_message):
                refs.append("parking")
        except Exception:
            pass
        try:
            if pack_runtime.has_contact_signal(normalized_message, message=current_message):
                refs.append("contact")
        except Exception:
            pass
    if (
        _policy_core_current_message_has_service_presence_query(current_message)
        and "services_overview" not in refs
    ):
        refs.append("services_overview")
    if len(refs) == 1:
        return None
    return refs


def _policy_core_current_message_hours_location_service_fact_pack_refs(
    current_message: str | None,
    *,
    client_slug: str | None = None,
) -> list[str] | None:
    hours_refs = _policy_core_current_message_hours_service_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if hours_refs is None:
        return None
    if not _policy_core_current_message_has_location_side_ask(current_message):
        return None
    refs_set = {
        item.strip().casefold()
        for item in [*hours_refs, "location"]
        if isinstance(item, str) and item.strip()
    }
    refs = [
        ref
        for ref in (
            "hours",
            "location",
            "parking",
            "contact",
            "pricing",
            "promotions",
            "duration",
            "master",
            "services_overview",
        )
        if ref in refs_set
    ]
    if len(refs) <= 2:
        return None
    return refs


def _policy_core_current_message_hours_location_fact_pack_refs(
    current_message: str | None,
    *,
    client_slug: str | None = None,
) -> list[str] | None:
    if not isinstance(current_message, str) or not current_message.strip():
        return None
    if not _policy_core_current_message_has_hours_ask(
        current_message
    ) or not _policy_core_current_message_has_location_side_ask(current_message):
        return None
    if _policy_core_current_message_has_service_presence_query(current_message):
        return None
    normalized_message = _normalize_text(current_message)
    if not normalized_message:
        return None
    from app.services.pack_runtime_service import get_pack_runtime

    try:
        pack_runtime = get_pack_runtime(client_slug)
    except Exception:
        pack_runtime = None
    if pack_runtime is not None:
        try:
            if pack_runtime.has_price_signal(normalized_message, message=current_message):
                return None
        except Exception:
            pass
        try:
            if pack_runtime.has_duration_signal(normalized_message, message=current_message):
                return None
        except Exception:
            pass
    refs = ["hours", "location"]
    if _policy_core_current_message_has_promotions_query(current_message):
        refs.append("promotions")
    if pack_runtime is not None:
        try:
            if pack_runtime.has_parking_signal(normalized_message):
                refs.append("parking")
        except Exception:
            pass
        try:
            if pack_runtime.has_contact_signal(normalized_message, message=current_message):
                refs.append("contact")
        except Exception:
            pass
    return refs


def _policy_core_current_message_promotions_location_pack_refs(
    current_message: str | None,
) -> list[str] | None:
    if not isinstance(current_message, str) or not current_message.strip():
        return None
    if not _policy_core_current_message_has_promotions_query(current_message):
        return None
    if _policy_core_current_message_has_hours_ask(current_message):
        return None
    if not _policy_core_current_message_has_location_side_ask(current_message):
        return None
    return ["promotions", "location"]


def _policy_core_current_message_promotions_booking_collect_pack_refs(
    current_message: str | None,
    *,
    client_slug: str | None = None,
) -> list[str] | None:
    if not isinstance(current_message, str) or not current_message.strip():
        return None
    if not _policy_core_current_message_has_promotions_query(current_message):
        return None
    if not _policy_core_current_message_has_booking_side_ask(current_message):
        return None
    refs = ["promotions"]
    normalized_message = _normalize_text(current_message)
    if _policy_core_current_message_has_location_side_ask(current_message):
        refs.append("location")
    if normalized_message and isinstance(client_slug, str) and client_slug.strip():
        from app.services.pack_runtime_service import get_pack_runtime

        try:
            pack_runtime = get_pack_runtime(client_slug)
        except Exception:
            pack_runtime = None
        if pack_runtime is not None:
            try:
                if pack_runtime.has_contact_signal(normalized_message, message=current_message):
                    refs.append("contact")
            except Exception:
                pass
            try:
                if pack_runtime.has_parking_signal(normalized_message):
                    refs.append("parking")
            except Exception:
                pass
    return refs


def _policy_core_current_message_service_scoped_fact_pack_refs(
    current_message: str | None,
    *,
    client_slug: str | None = None,
) -> list[str] | None:
    if not isinstance(current_message, str) or not current_message.strip():
        return None
    if not _policy_core_current_message_has_temporal_booking_side_ask(current_message):
        return None
    normalized_message = _normalize_text(current_message)
    if not normalized_message:
        return None
    refs: list[str] = []
    from app.services.pack_runtime_service import get_pack_runtime

    try:
        pack_runtime = get_pack_runtime(client_slug)
    except Exception:
        pack_runtime = None
    if pack_runtime is not None:
        try:
            if pack_runtime.has_price_signal(normalized_message, message=current_message):
                refs.append("pricing")
        except Exception:
            pass
        try:
            if pack_runtime.has_duration_signal(normalized_message, message=current_message):
                refs.append("duration")
        except Exception:
            pass
    if len(refs) != 1:
        return None
    return refs


def _policy_core_current_message_service_multifact_pack_refs(
    current_message: str | None,
    *,
    client_slug: str | None = None,
) -> list[str] | None:
    if not isinstance(current_message, str) or not current_message.strip():
        return None
    if _policy_core_current_message_has_location_side_ask(current_message):
        return None
    if (
        _policy_core_current_message_hours_service_fact_pack_refs(
            current_message,
            client_slug=client_slug,
        )
        is not None
    ):
        return None
    normalized_message = _normalize_text(current_message)
    if not normalized_message:
        return None
    refs: list[str] = []
    from app.services.pack_runtime_service import get_pack_runtime

    try:
        pack_runtime = get_pack_runtime(client_slug)
    except Exception:
        pack_runtime = None
    if pack_runtime is not None:
        if _policy_core_current_message_has_promotions_query(current_message):
            refs.append("promotions")
        try:
            if pack_runtime.has_price_signal(normalized_message, message=current_message):
                refs.append("pricing")
        except Exception:
            pass
        try:
            if pack_runtime.has_duration_signal(normalized_message, message=current_message):
                refs.append("duration")
        except Exception:
            pass
        try:
            if pack_runtime.has_master_signal(current_message):
                refs.append("master")
        except Exception:
            pass
        try:
            if pack_runtime.has_contact_signal(normalized_message, message=current_message):
                refs.append("contact")
        except Exception:
            pass
        try:
            if pack_runtime.has_parking_signal(normalized_message):
                refs.append("parking")
        except Exception:
            pass
    if (
        _policy_core_current_message_has_service_presence_query(current_message)
        and "services_overview" not in refs
    ):
        refs.append("services_overview")
    if len(refs) <= 1:
        return None
    return [ref for ref in _SERVICE_QUERY_MULTI_FACT_REFS if ref in refs]


def _policy_core_current_message_has_promotions_query(
    current_message: str | None,
) -> bool:
    if not isinstance(current_message, str):
        return False
    normalized = " ".join(current_message.split())
    if not normalized:
        return False
    return any(
        pattern.search(normalized)
        for pattern in _POLICY_CORE_PROMOTIONS_QUERY_PATTERNS
    )


def _policy_core_current_message_has_booking_or_location_side_ask(
    current_message: str | None,
) -> bool:
    if not isinstance(current_message, str):
        return False
    normalized = " ".join(current_message.split())
    if not normalized:
        return False
    if _policy_core_current_message_has_location_side_ask(current_message):
        return True
    return _policy_core_current_message_has_booking_side_ask(current_message)


_SERVICE_SCOPED_OWNER_INTENTS = {"pricing", "duration", "master_query", "promotions"}
_SERVICE_SCOPED_OWNER_CAPABILITIES = {"pricing", "duration", "master", "live_availability", "promotions"}
_SERVICE_QUERY_MULTI_FACT_REFS = (
    "pricing",
    "promotions",
    "duration",
    "master",
    "services_overview",
    "contact",
    "parking",
)


def _policy_core_contract_grounded_service(
    contract: LlmPolicyCoreOutput,
) -> str | None:
    slot_service = contract.slots.get("service")
    if isinstance(slot_service, str) and slot_service.strip():
        return " ".join(slot_service.split())
    referent_payload = contract.referents.get("service") if isinstance(contract.referents, Mapping) else None
    if isinstance(referent_payload, Mapping):
        raw_value = referent_payload.get("value") or referent_payload.get("entity_id")
        if isinstance(raw_value, str) and raw_value.strip():
            return " ".join(raw_value.split())
    return None


def _policy_core_contract_grounded_specialist(
    contract: LlmPolicyCoreOutput,
) -> str | None:
    referent_payload = (
        contract.referents.get("specialist") if isinstance(contract.referents, Mapping) else None
    )
    if isinstance(referent_payload, Mapping):
        raw_value = referent_payload.get("value") or referent_payload.get("entity_id")
        if isinstance(raw_value, str) and raw_value.strip():
            return " ".join(raw_value.split())
    return None


def _policy_core_memory_grounded_service(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(normalized_memory_profile, Mapping):
        return None
    semantic_contract = (
        normalized_memory_profile.get("semantic_contract")
        if isinstance(normalized_memory_profile.get("semantic_contract"), Mapping)
        else None
    )
    if isinstance(semantic_contract, Mapping):
        referents = semantic_contract.get("referents")
        referent_payload = referents.get("service") if isinstance(referents, Mapping) else None
        if isinstance(referent_payload, Mapping):
            raw_value = referent_payload.get("value") or referent_payload.get("entity_id")
            if isinstance(raw_value, str) and raw_value.strip():
                return " ".join(raw_value.split())
    slot_state = normalized_memory_profile.get("slot_state")
    if isinstance(slot_state, Mapping):
        raw_slot = slot_state.get("service")
        if isinstance(raw_slot, str) and raw_slot.strip():
            return " ".join(raw_slot.split())
    return None


def _policy_core_memory_grounded_specialist(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(normalized_memory_profile, Mapping):
        return None
    semantic_contract = (
        normalized_memory_profile.get("semantic_contract")
        if isinstance(normalized_memory_profile.get("semantic_contract"), Mapping)
        else None
    )
    if isinstance(semantic_contract, Mapping):
        referents = semantic_contract.get("referents")
        referent_payload = referents.get("specialist") if isinstance(referents, Mapping) else None
        if isinstance(referent_payload, Mapping):
            raw_value = referent_payload.get("value") or referent_payload.get("entity_id")
            if isinstance(raw_value, str) and raw_value.strip():
                return " ".join(raw_value.split())
    return None


def _policy_core_memory_slot_value(
    normalized_memory_profile: Mapping[str, Any] | None,
    key: str,
) -> str | None:
    if not isinstance(normalized_memory_profile, Mapping):
        return None
    slot_state = normalized_memory_profile.get("slot_state")
    if not isinstance(slot_state, Mapping):
        return None
    value = slot_state.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _policy_core_normalize_surface_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    return normalized or None


def _policy_core_memory_alternate_datetime(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(normalized_memory_profile, Mapping):
        return None
    semantic_contract = (
        normalized_memory_profile.get("semantic_contract")
        if isinstance(normalized_memory_profile.get("semantic_contract"), Mapping)
        else None
    )
    if not isinstance(semantic_contract, Mapping):
        return None
    return _policy_core_normalize_surface_text(semantic_contract.get("alternate_datetime"))


def _policy_core_memory_temporal_scope(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(normalized_memory_profile, Mapping):
        return None
    semantic_contract = (
        normalized_memory_profile.get("semantic_contract")
        if isinstance(normalized_memory_profile.get("semantic_contract"), Mapping)
        else None
    )
    if not isinstance(semantic_contract, Mapping):
        return None
    return _policy_core_payload_token(semantic_contract.get("temporal_scope"))


def _policy_core_memory_has_datetime_context(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    if _policy_core_memory_slot_value(normalized_memory_profile, "datetime"):
        return True
    if not isinstance(normalized_memory_profile, Mapping):
        return False
    semantic_contract = (
        normalized_memory_profile.get("semantic_contract")
        if isinstance(normalized_memory_profile.get("semantic_contract"), Mapping)
        else None
    )
    temporal_scope = _policy_core_payload_token(
        semantic_contract.get("temporal_scope") if isinstance(semantic_contract, Mapping) else None
    )
    return temporal_scope in {"specific_time", "day", "weekday", "weekend", "date_range"}


def _policy_core_has_customer_identity(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    return bool(
        _policy_core_has_grounded_referent(contract.referents, "customer")
        or contract.slots.get("name")
        or _policy_core_memory_slot_value(normalized_memory_profile, "name")
    )


def _policy_core_contract_customer_entity_name(
    contract: LlmPolicyCoreOutput,
) -> str | None:
    for raw_ref in list(contract.entity_refs or []):
        if not isinstance(raw_ref, Mapping):
            continue
        entity_type = _policy_core_payload_token(raw_ref.get("entity_type"))
        if entity_type != "customer":
            continue
        value = raw_ref.get("value")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _policy_core_booking_commit_ready(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    grounded_service = _policy_core_contract_grounded_service(contract) or _policy_core_memory_grounded_service(
        normalized_memory_profile
    )
    has_datetime = bool(contract.slots.get("datetime")) or bool(
        _policy_core_memory_slot_value(normalized_memory_profile, "datetime")
    )
    has_customer = _policy_core_has_grounded_referent(contract.referents, "customer") or bool(
        contract.slots.get("name")
    ) or bool(_policy_core_memory_slot_value(normalized_memory_profile, "name"))
    return bool(grounded_service and has_datetime and has_customer)


def _policy_core_existing_booking_lookup_context(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    slot_state = (
        normalized_memory_profile.get("slot_state")
        if isinstance(normalized_memory_profile, Mapping)
        and isinstance(normalized_memory_profile.get("slot_state"), Mapping)
        else {}
    )
    contract_customer = contract.slots.get("name")
    memory_customer = slot_state.get("name")
    contract_datetime = contract.slots.get("datetime")
    memory_datetime = slot_state.get("datetime")
    has_customer = any(
        isinstance(value, str) and value.strip()
        for value in (contract_customer, memory_customer)
    )
    has_datetime = any(
        isinstance(value, str) and value.strip()
        for value in (contract_datetime, memory_datetime)
    )
    return has_customer and has_datetime


def _policy_core_contract_supplies_lookup_datetime(
    contract: LlmPolicyCoreOutput,
) -> bool:
    return any(
        isinstance(value, str) and value.strip()
        for value in (
            contract.slots.get("datetime"),
            _policy_core_payload_token(contract.alternate_datetime),
        )
    )


def _policy_core_booking_manage_reference_direct_lookup_context(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if (
        _policy_core_payload_token(carry_contract.get("expected_reply_type")) == "name"
        and not _policy_core_contract_supplies_lookup_datetime(contract)
    ):
        return False
    return _policy_core_existing_booking_lookup_context(contract, normalized_memory_profile)


def _policy_core_memory_booking_manage_reference_context(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    if not isinstance(normalized_memory_profile, Mapping):
        return False
    semantic_contract = normalized_memory_profile.get("semantic_contract")
    if not isinstance(semantic_contract, Mapping):
        return False
    if _policy_core_payload_token(semantic_contract.get("capability")) != "booking_manage":
        return False
    if _policy_core_payload_token(semantic_contract.get("subject_kind")) != "booking":
        return False
    referents = semantic_contract.get("referents")
    return not _policy_core_has_grounded_referent(
        referents if isinstance(referents, Mapping) else None,
        "booking_ref",
    )


def _policy_core_is_explicit_manager_handoff_contract(
    contract: LlmPolicyCoreOutput,
) -> bool:
    return bool(
        contract.intent == "booking"
        and contract.action == "handoff"
        and contract.tool_action_hint == "handoff"
        and contract.needs_manager
        and contract.capability == "booking_manage"
        and contract.subject_kind == "booking"
    )


def _policy_core_is_booking_manage_reference_followup_shape(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    if contract.subject_kind != "booking":
        return False
    if _policy_core_is_explicit_manager_handoff_contract(contract):
        return False
    contract_booking_manage_context = contract.capability == "booking_manage"
    memory_booking_manage_context = _policy_core_memory_booking_manage_reference_context(
        normalized_memory_profile
    )
    if not (contract_booking_manage_context or memory_booking_manage_context):
        return False
    referents = contract.referents if isinstance(contract.referents, dict) else {}
    if _policy_core_has_grounded_referent(referents, "booking_ref"):
        return False
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not (
        memory_booking_manage_context
        or _policy_core_is_booking_time_followup_contract(carry_contract)
    ):
        return False
    expected_reply_type = _policy_core_payload_token(contract.expected_reply_type)
    if expected_reply_type == "name":
        return contract.next_question == "name" and list(contract.open_questions or []) == ["name"]
    if expected_reply_type == "time":
        return contract.next_question == "datetime" and list(contract.open_questions or []) == ["datetime"]
    return False


def _policy_core_is_booking_manage_name_fill_followup_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    contract_booking_manage_context = (
        contract.capability == "booking_manage" and contract.subject_kind == "booking"
    )
    if not (
        contract_booking_manage_context
        or _policy_core_memory_booking_manage_reference_context(normalized_memory_profile)
    ):
        return False
    referents = contract.referents if isinstance(contract.referents, dict) else {}
    if contract_booking_manage_context and _policy_core_has_grounded_referent(
        referents,
        "booking_ref",
    ):
        return False
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if _policy_core_payload_token(carry_contract.get("expected_reply_type")) != "name":
        return False
    if not _policy_core_has_customer_identity(contract, normalized_memory_profile):
        return False
    if _policy_core_booking_manage_reference_direct_lookup_context(
        contract,
        normalized_memory_profile,
    ):
        return False
    if contract.intent != "check_booking":
        return True
    if contract.action != "fact":
        return True
    if contract.tool_action_hint != "calendar.get_booking":
        return True
    if contract.expected_reply_type != "time":
        return True
    if contract.next_question != "datetime":
        return True
    if list(contract.open_questions or []) != ["datetime"]:
        return True
    if any(
        (
            contract.pending_question_act,
            contract.pending_question_target,
            contract.active_question_relation,
        )
    ):
        return True
    return False


def _policy_core_service_token_variants(token: str) -> set[str]:
    normalized = _normalize_text(token)
    if not normalized:
        return set()
    variants = {normalized}
    for suffix in (
        "иями",
        "ями",
        "ами",
        "ого",
        "его",
        "ому",
        "ему",
        "ыми",
        "ими",
        "ую",
        "юю",
        "ой",
        "ей",
        "ом",
        "ем",
        "ах",
        "ях",
        "ов",
        "ев",
        "а",
        "я",
        "у",
        "ю",
        "ы",
        "и",
        "е",
        "о",
    ):
        if normalized.endswith(suffix) and len(normalized) - len(suffix) >= 4:
            variants.add(normalized[: -len(suffix)])
    if len(normalized) >= 5:
        variants.add(normalized[:-1])
    return {item for item in variants if item}


def _policy_core_service_phrase_matches_message(
    normalized_phrase: str,
    *,
    normalized_message: str,
    padded_message: str,
) -> bool:
    if f" {normalized_phrase} " in padded_message:
        return True
    phrase_tokens = [token for token in normalized_phrase.split() if token]
    message_tokens = [token for token in normalized_message.split() if token]
    if not phrase_tokens or len(message_tokens) < len(phrase_tokens):
        return False
    phrase_variants = [_policy_core_service_token_variants(token) for token in phrase_tokens]
    if not all(phrase_variants):
        return False
    window_size = len(phrase_tokens)
    for start_index in range(len(message_tokens) - window_size + 1):
        window = message_tokens[start_index : start_index + window_size]
        if all(
            phrase_variants[offset]
            & _policy_core_service_token_variants(window[offset])
            for offset in range(window_size)
        ):
            return True
    return False


def _policy_core_context_service_hint(
    message: str | None,
    context_payload: Mapping[str, Any] | None,
    *,
    client_slug: str | None = None,
) -> str | None:
    if not isinstance(message, str) or not message.strip():
        return None
    if not isinstance(context_payload, Mapping):
        return None
    raw_cards = context_payload.get("service_cards")
    if not isinstance(raw_cards, list):
        return None
    normalized_message = _normalize_text(message)
    if not normalized_message:
        return None
    padded_message = f" {normalized_message} "
    matches: list[tuple[int, str]] = []
    seen: set[str] = set()
    for raw_card in raw_cards:
        if not isinstance(raw_card, Mapping):
            continue
        includes = raw_card.get("includes")
        if not isinstance(includes, list):
            continue
        for raw_include in includes:
            if not isinstance(raw_include, str) or not raw_include.strip():
                continue
            normalized_include = _normalize_text(raw_include)
            if not normalized_include or not _policy_core_service_phrase_matches_message(
                normalized_include,
                normalized_message=normalized_message,
                padded_message=padded_message,
            ):
                continue
            fingerprint = normalized_include.casefold()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            matches.append((len(normalized_include), " ".join(raw_include.split())))
    if not matches:
        return None
    matches.sort(key=lambda item: (-item[0], item[1]))
    return matches[0][1]


def _policy_core_is_service_scoped_owner_query(
    contract: LlmPolicyCoreOutput,
) -> bool:
    if contract.intent in _SERVICE_SCOPED_OWNER_INTENTS:
        return True
    if contract.capability in _SERVICE_SCOPED_OWNER_CAPABILITIES:
        return True
    if contract.tool_action_hint == "catalog.service_query":
        return True
    return "master" in {
        item.strip().casefold()
        for item in list(contract.pack_refs or [])
        if isinstance(item, str) and item.strip()
    }


def _policy_core_has_active_media_resume(
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    pending_contract = _policy_core_active_pending_contract(normalized_memory_profile)
    resume_contract = _policy_core_resume_pending_contract(normalized_memory_profile)
    return pending_contract.get("expected_reply_type") == "media" and bool(
        resume_contract.get("expected_reply_type")
    )


def _policy_core_is_media_reason_family(reason: str | None) -> bool:
    if not isinstance(reason, str) or not reason.strip():
        return False
    normalized = reason.strip().casefold()
    return normalized.startswith(
        (
            "user_offers_photo_reference",
            "user_offers_photos_for_style_reference",
        )
    )


def _policy_core_is_pending_media_time_interrupt_reason(reason: str | None) -> bool:
    if not isinstance(reason, str) or not reason.strip():
        return False
    normalized = reason.strip().casefold()
    return normalized.startswith("pending_media_reference_contract_interrupted_by_time_")


def _policy_core_reason_indicates_followup_interrupt(reason: str | None) -> bool:
    if not isinstance(reason, str) or not reason.strip():
        return False
    normalized = reason.strip().casefold()
    return "_query" in normalized or "_interrupt" in normalized


def _policy_core_is_active_followup_info_interrupt(
    contract: LlmPolicyCoreOutput,
) -> bool:
    if contract.action != "fact":
        return False
    if contract.capability == "booking_manage":
        return False
    if contract.active_question_relation == "generic_info_interrupt":
        return True
    if contract.intent in {
        "pricing",
        "hours",
        "location",
        "parking",
        "duration",
        "promotions",
        "contact",
        "master_query",
    }:
        return True
    if contract.capability in {
        "pricing",
        "hours",
        "location",
        "parking",
        "duration",
        "promotions",
        "master",
        "contact",
        "portfolio",
    }:
        return True
    pack_refs = {
        item.strip().casefold()
        for item in list(contract.pack_refs or [])
        if isinstance(item, str) and item.strip()
    }
    return bool(pack_refs & {"pricing", "hours", "location", "parking", "promotions", "contact", "master"})


def _policy_core_catalog_location_pack_refs(contract: LlmPolicyCoreOutput) -> list[str]:
    refs: list[str] = []
    for item in list(contract.pack_refs or []):
        if not isinstance(item, str):
            continue
        normalized = item.strip().casefold()
        if normalized in {"location", "hours", "parking", "contact"} and normalized not in refs:
            refs.append(normalized)
    return refs


def _policy_core_catalog_service_pack_refs(contract: LlmPolicyCoreOutput) -> list[str]:
    refs: list[str] = []
    for item in list(contract.pack_refs or []):
        if not isinstance(item, str):
            continue
        normalized = item.strip().casefold()
        if (
            normalized
            in {"pricing", "duration", "promotions", "master", "services_overview", "location", "contact", "parking"}
            and normalized not in refs
        ):
            refs.append(normalized)
    return refs


def _policy_core_expected_catalog_service_pack_ref(
    contract: LlmPolicyCoreOutput,
) -> str | None:
    service_pack_refs = _policy_core_catalog_service_pack_refs(contract)
    if len(service_pack_refs) == 1:
        return service_pack_refs[0]
    if contract.intent == "master_query" or contract.capability == "live_availability":
        return "master"
    if contract.capability in {"pricing", "duration", "promotions", "master"}:
        return contract.capability
    if contract.intent in {"pricing", "duration", "promotions"}:
        return contract.intent
    return None


def _policy_core_is_master_query_time_collect(
    contract: LlmPolicyCoreOutput,
) -> bool:
    if contract.intent != "master_query" or contract.action != "collect":
        return False
    open_questions = {
        item.strip().casefold()
        for item in list(contract.open_questions or [])
        if isinstance(item, str) and item.strip()
    }
    if contract.next_question == "service" or "service" in open_questions:
        return False
    return bool(
        contract.expected_reply_type == "time"
        or contract.next_question == "datetime"
        or contract.capability == "live_availability"
        or contract.resolution_mode == "live_calendar"
        or contract.pending_question_target == "time"
    )


def _policy_core_is_active_followup_master_query_shape(
    *,
    intent: str | None,
    next_question: str | None,
    open_questions: Iterable[str],
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    if intent != "master_query":
        return False
    if not _policy_core_has_active_media_resume(normalized_memory_profile):
        return False
    normalized_open_questions = {
        item.strip().casefold()
        for item in open_questions
        if isinstance(item, str) and item.strip()
    }
    if next_question == "service" or "service" in normalized_open_questions:
        return False
    return True


def _policy_core_schema_requires_master_query_reclassification(
    *,
    payload: Mapping[str, Any] | None,
    schema_error: str | None,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    if not isinstance(schema_error, str):
        return False
    normalized_schema_error = schema_error.casefold()
    if "master_query" not in normalized_schema_error or "tool_action_invalid" not in normalized_schema_error:
        return False
    if not isinstance(payload, Mapping):
        return False
    intent = _policy_core_payload_token(payload.get("intent"))
    next_question = _policy_core_payload_token(payload.get("next_question"))
    open_questions = _policy_core_payload_string_list(payload.get("open_questions"))
    return _policy_core_is_active_followup_master_query_shape(
        intent=intent,
        next_question=next_question,
        open_questions=open_questions,
        normalized_memory_profile=normalized_memory_profile,
    )


def _policy_core_schema_requires_booking_live_availability_reclassification(
    *,
    payload: Mapping[str, Any] | None,
    schema_error: str | None,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    if not isinstance(schema_error, str):
        return False
    normalized_schema_error = schema_error.casefold()
    if "master_query_collect_tool_action_invalid" not in normalized_schema_error:
        return False
    if not isinstance(payload, Mapping):
        return False
    intent = _policy_core_payload_token(payload.get("intent"))
    if intent != "master_query":
        return False
    tool_action = _policy_core_payload_token(
        payload.get("tool_action_hint") or payload.get("tool_action")
    )
    capability = _policy_core_payload_token(payload.get("capability"))
    if tool_action != "calendar.list_slots" and capability != "live_availability":
        return False
    carry_contract = _policy_core_resume_pending_contract(normalized_memory_profile) or _policy_core_active_pending_contract(
        normalized_memory_profile
    )
    if not _policy_core_is_booking_time_followup_contract(carry_contract):
        return False
    grounded_service = _policy_core_payload_grounded_service(payload) or _policy_core_memory_grounded_service(
        normalized_memory_profile
    )
    if not grounded_service:
        return False
    next_question = _policy_core_payload_token(payload.get("next_question"))
    open_questions = _policy_core_payload_string_list(payload.get("open_questions"))
    if next_question == "service" or "service" in open_questions:
        return False
    return True


def _policy_core_resolve_message_grounded_service_hint(
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
    client_slug: str | None,
) -> str | None:
    grounded_service_hint = _policy_core_context_service_hint(
        current_message,
        context_payload,
        client_slug=client_slug,
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service_hint and isinstance(client_slug, str) and client_slug.strip():
        from app.services.policy_context_snapshot_service import build_policy_core_context_snapshot

        fallback_context_payload = build_policy_core_context_snapshot(
            client_slug=client_slug,
            info_refs=None,
            consult_refs=None,
        ).as_context_payload()
        grounded_service_hint = _policy_core_context_service_hint(
            current_message,
            fallback_context_payload,
            client_slug=client_slug,
        )
    return grounded_service_hint


def _policy_core_build_mixed_first_turn_location_service_fact_boundary_payload(
    *,
    payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return None
    expected_pack_refs = _policy_core_current_message_location_service_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return None
    grounded_service = _policy_core_payload_grounded_service(payload)
    grounded_service_hint = _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    effective_service = grounded_service or grounded_service_hint
    if not effective_service:
        return None
    normalized_slots: dict[str, Any] = {"service": effective_service}
    normalized_referents: dict[str, Any] = {}
    if isinstance(payload, Mapping):
        referents = payload.get("referents")
        if isinstance(referents, Mapping) and isinstance(referents.get("service"), Mapping):
            normalized_referents["service"] = dict(referents["service"])
    reason = "standalone_location_head_intent_with_service_fact_requests"
    if isinstance(payload, Mapping):
        raw_reason = payload.get("reason")
        if isinstance(raw_reason, str) and raw_reason.strip():
            reason = " ".join(raw_reason.split())
    return {
        "intent": "location",
        "action": "fact",
        "tool_action_hint": "info",
        "pack_refs": list(expected_pack_refs),
        "slots": normalized_slots,
        "expected_reply_type": None,
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "language": payload.get("language") if isinstance(payload, Mapping) else None,
        "confidence": payload.get("confidence") if isinstance(payload, Mapping) else None,
        "reason": reason,
        "goal": None,
        "entity_refs": [],
        "referents": normalized_referents,
        "subject_kind": "service",
        "capability": "location",
        "temporal_scope": "none",
        "alternate_datetime": None,
        "resolution_mode": "policy_fact",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "resolver_id": None,
        "resolver_version": None,
    }


def _policy_core_build_mixed_first_turn_hours_location_fact_boundary_payload(
    *,
    payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return None
    expected_pack_refs = _policy_core_current_message_hours_location_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return None
    grounded_service = _policy_core_payload_grounded_service(payload)
    grounded_service_hint = _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if grounded_service or grounded_service_hint:
        return None
    intent_token = _policy_core_payload_token(payload.get("intent")) if isinstance(payload, Mapping) else None
    capability_token = _policy_core_payload_token(payload.get("capability")) if isinstance(payload, Mapping) else None
    head_ref = next(
        (token for token in (intent_token, capability_token) if token in {"hours", "location"}),
        "hours",
    )
    reason = "standalone_hours_location_fact_request"
    if isinstance(payload, Mapping):
        raw_reason = payload.get("reason")
        if isinstance(raw_reason, str) and raw_reason.strip():
            reason = " ".join(raw_reason.split())
    return {
        "intent": head_ref,
        "action": "fact",
        "tool_action_hint": "info",
        "pack_refs": list(expected_pack_refs),
        "slots": {},
        "expected_reply_type": None,
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "language": payload.get("language") if isinstance(payload, Mapping) else None,
        "confidence": payload.get("confidence") if isinstance(payload, Mapping) else None,
        "reason": reason,
        "goal": None,
        "entity_refs": [],
        "referents": {},
        "subject_kind": "general",
        "capability": head_ref,
        "temporal_scope": "none",
        "alternate_datetime": None,
        "resolution_mode": "policy_fact",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "resolver_id": None,
        "resolver_version": None,
    }


def _policy_core_build_mixed_first_turn_hours_service_fact_boundary_payload(
    *,
    payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return None
    expected_pack_refs = _policy_core_current_message_hours_service_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return None
    grounded_service = _policy_core_payload_grounded_service(payload)
    grounded_service_hint = _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    effective_service = grounded_service or grounded_service_hint
    if not effective_service:
        return None
    normalized_pack_refs = (
        {
            item.strip().casefold()
            for item in list(payload.get("pack_refs") or [])
            if isinstance(item, str) and item.strip()
        }
        if isinstance(payload, Mapping)
        else set()
    )
    if normalized_pack_refs != {
        item.strip().casefold()
        for item in expected_pack_refs
        if isinstance(item, str) and item.strip()
    }:
        return None
    intent_token = _policy_core_payload_token(payload.get("intent")) if isinstance(payload, Mapping) else None
    capability_token = _policy_core_payload_token(payload.get("capability")) if isinstance(payload, Mapping) else None
    tool_action_hint = _policy_core_payload_token(payload.get("tool_action_hint")) if isinstance(payload, Mapping) else None
    if intent_token != "hours" and capability_token != "hours" and "hours" not in normalized_pack_refs:
        return None
    if tool_action_hint not in {None, "info", "catalog.location"}:
        return None
    if (
        grounded_service
        and payload.get("subject_kind") == "service"
        and capability_token == "hours"
        and _policy_core_payload_token(payload.get("resolution_mode")) == "policy_fact"
        and payload.get("expected_reply_type") is None
        and payload.get("next_question") is None
        and not list(payload.get("open_questions") or [])
        and payload.get("pending_question_act") is None
        and payload.get("pending_question_target") is None
        and payload.get("active_question_relation") is None
    ):
        return None
    normalized_slots: dict[str, Any] = {"service": effective_service}
    normalized_referents: dict[str, Any] = {}
    if isinstance(payload, Mapping):
        referents = payload.get("referents")
        if isinstance(referents, Mapping) and isinstance(referents.get("service"), Mapping):
            normalized_referents["service"] = dict(referents["service"])
    if "service" not in normalized_referents:
        normalized_referents["service"] = {
            "value": effective_service,
            "entity_type": "service",
            "source_ref": "carryover",
        }
    reason = "standalone_hours_head_intent_with_service_fact_requests"
    if isinstance(payload, Mapping):
        raw_reason = payload.get("reason")
        if isinstance(raw_reason, str) and raw_reason.strip():
            reason = " ".join(raw_reason.split())
    return {
        "intent": "hours",
        "action": "fact",
        "tool_action_hint": "info",
        "pack_refs": list(expected_pack_refs),
        "slots": normalized_slots,
        "expected_reply_type": None,
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "language": payload.get("language") if isinstance(payload, Mapping) else None,
        "confidence": payload.get("confidence") if isinstance(payload, Mapping) else None,
        "reason": reason,
        "goal": None,
        "entity_refs": [],
        "referents": normalized_referents,
        "subject_kind": "service",
        "capability": "hours",
        "temporal_scope": "none",
        "alternate_datetime": None,
        "resolution_mode": "policy_fact",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "resolver_id": None,
        "resolver_version": None,
    }


def _policy_core_build_mixed_first_turn_hours_location_service_fact_boundary_payload(
    *,
    payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return None
    expected_pack_refs = _policy_core_current_message_hours_location_service_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return None
    grounded_service = _policy_core_payload_grounded_service(payload)
    grounded_service_hint = _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    effective_service = grounded_service or grounded_service_hint
    if not effective_service:
        return None
    normalized_pack_refs = (
        {
            item.strip().casefold()
            for item in list(payload.get("pack_refs") or [])
            if isinstance(item, str) and item.strip()
        }
        if isinstance(payload, Mapping)
        else set()
    )
    expected_pack_ref_set = {
        item.strip().casefold()
        for item in expected_pack_refs
        if isinstance(item, str) and item.strip()
    }
    intent_token = _policy_core_payload_token(payload.get("intent")) if isinstance(payload, Mapping) else None
    capability_token = _policy_core_payload_token(payload.get("capability")) if isinstance(payload, Mapping) else None
    tool_action_hint = _policy_core_payload_token(payload.get("tool_action_hint")) if isinstance(payload, Mapping) else None
    if intent_token not in {"hours", "location", None} and capability_token not in {"hours", "location", None}:
        return None
    if tool_action_hint not in {None, "info", "catalog.location"}:
        return None
    if (
        normalized_pack_refs == expected_pack_ref_set
        and payload.get("subject_kind") == "service"
        and payload.get("expected_reply_type") is None
        and payload.get("next_question") is None
        and not list(payload.get("open_questions") or [])
        and payload.get("pending_question_act") is None
        and payload.get("pending_question_target") is None
        and payload.get("active_question_relation") is None
        and _policy_core_payload_token(payload.get("resolution_mode")) == "policy_fact"
        and capability_token in {"hours", "location"}
    ):
        return None
    head_ref = next(
        (token for token in (intent_token, capability_token) if token in {"hours", "location"}),
        "hours",
    )
    normalized_slots: dict[str, Any] = {"service": effective_service}
    normalized_referents: dict[str, Any] = {}
    if isinstance(payload, Mapping):
        referents = payload.get("referents")
        if isinstance(referents, Mapping) and isinstance(referents.get("service"), Mapping):
            normalized_referents["service"] = dict(referents["service"])
    if "service" not in normalized_referents:
        normalized_referents["service"] = {
            "value": effective_service,
            "entity_type": "service",
            "source_ref": "carryover",
        }
    reason = "standalone_hours_location_head_intent_with_service_fact_requests"
    if isinstance(payload, Mapping):
        raw_reason = payload.get("reason")
        if isinstance(raw_reason, str) and raw_reason.strip():
            reason = " ".join(raw_reason.split())
    return {
        "intent": head_ref,
        "action": "fact",
        "tool_action_hint": "info",
        "pack_refs": list(expected_pack_refs),
        "slots": normalized_slots,
        "expected_reply_type": None,
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "language": payload.get("language") if isinstance(payload, Mapping) else None,
        "confidence": payload.get("confidence") if isinstance(payload, Mapping) else None,
        "reason": reason,
        "goal": None,
        "entity_refs": [],
        "referents": normalized_referents,
        "subject_kind": "service",
        "capability": head_ref,
        "temporal_scope": "none",
        "alternate_datetime": None,
        "resolution_mode": "policy_fact",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "resolver_id": None,
        "resolver_version": None,
    }


def _policy_core_apply_prevalidate_boundary_normalizations(
    *,
    payload: dict[str, Any],
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> dict[str, Any]:
    normalized_promotions_location_booking_payload = (
        _policy_core_build_promotions_location_booking_followup_boundary_payload(
            payload=payload,
            normalized_memory_profile=normalized_memory_profile,
            current_message=current_message,
            context_payload=context_payload,
            client_slug=client_slug,
        )
    )
    if normalized_promotions_location_booking_payload is not None:
        return normalized_promotions_location_booking_payload
    normalized_promotions_grounded_booking_payload = (
        _policy_core_build_promotions_grounded_service_booking_followup_boundary_payload(
            payload=payload,
            normalized_memory_profile=normalized_memory_profile,
            current_message=current_message,
            context_payload=context_payload,
            client_slug=client_slug,
        )
    )
    if normalized_promotions_grounded_booking_payload is not None:
        return normalized_promotions_grounded_booking_payload
    normalized_promotions_booking_payload = (
        _policy_core_build_promotions_booking_fact_followup_boundary_payload(
            payload=payload,
            normalized_memory_profile=normalized_memory_profile,
            current_message=current_message,
            context_payload=context_payload,
            client_slug=client_slug,
        )
    )
    if normalized_promotions_booking_payload is not None:
        return normalized_promotions_booking_payload
    normalized_hours_location_service_payload = (
        _policy_core_build_mixed_first_turn_hours_location_service_fact_boundary_payload(
            payload=payload,
            normalized_memory_profile=normalized_memory_profile,
            current_message=current_message,
            context_payload=context_payload,
            client_slug=client_slug,
        )
    )
    if normalized_hours_location_service_payload is not None:
        return normalized_hours_location_service_payload
    normalized_hours_service_payload = _policy_core_build_mixed_first_turn_hours_service_fact_boundary_payload(
        payload=payload,
        normalized_memory_profile=normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    )
    if normalized_hours_service_payload is not None:
        return normalized_hours_service_payload
    normalized_service_fact_side_booking_payload = (
        _policy_core_build_mixed_first_turn_service_fact_booking_side_boundary_payload(
            payload=payload,
            normalized_memory_profile=normalized_memory_profile,
            current_message=current_message,
            context_payload=context_payload,
            client_slug=client_slug,
        )
    )
    if normalized_service_fact_side_booking_payload is not None:
        return normalized_service_fact_side_booking_payload
    return payload


def _policy_core_build_mixed_first_turn_service_fact_booking_side_boundary_payload(
    *,
    payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return None
    expected_pack_refs = _policy_core_current_message_service_scoped_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return None
    expected_ref = expected_pack_refs[0]
    grounded_service = _policy_core_payload_grounded_service(payload)
    grounded_service_hint = _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    effective_service = grounded_service or grounded_service_hint
    if not effective_service:
        return None
    normalized_slots: dict[str, Any] = {"service": effective_service}
    normalized_referents: dict[str, Any] = {}
    if isinstance(payload, Mapping):
        referents = payload.get("referents")
        if isinstance(referents, Mapping) and isinstance(referents.get("service"), Mapping):
            normalized_referents["service"] = dict(referents["service"])
    reason = "standalone_service_fact_head_intent_with_side_booking_request"
    if isinstance(payload, Mapping):
        raw_reason = payload.get("reason")
        if isinstance(raw_reason, str) and raw_reason.strip():
            reason = " ".join(raw_reason.split())
    return {
        "intent": expected_ref,
        "action": "fact",
        "tool_action_hint": "catalog.service_query",
        "pack_refs": [expected_ref],
        "slots": normalized_slots,
        "expected_reply_type": None,
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "language": payload.get("language") if isinstance(payload, Mapping) else None,
        "confidence": payload.get("confidence") if isinstance(payload, Mapping) else None,
        "reason": reason,
        "goal": None,
        "entity_refs": [],
        "referents": normalized_referents,
        "subject_kind": "service",
        "capability": expected_ref,
        "temporal_scope": "none",
        "alternate_datetime": None,
        "resolution_mode": "policy_fact",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "resolver_id": None,
        "resolver_version": None,
    }


def _policy_core_build_service_query_multifact_boundary_payload(
    *,
    payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return None
    expected_pack_refs = _policy_core_current_message_service_multifact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return None
    grounded_service = _policy_core_payload_grounded_service(payload)
    grounded_service_hint = _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    effective_service = grounded_service or grounded_service_hint
    if not effective_service:
        return None
    intent_token = _policy_core_payload_token(payload.get("intent")) if isinstance(payload, Mapping) else None
    capability_token = _policy_core_payload_token(payload.get("capability")) if isinstance(payload, Mapping) else None
    head_ref = next(
        (token for token in (intent_token, capability_token) if token in expected_pack_refs),
        expected_pack_refs[0],
    )
    head_intent = "master_query" if head_ref == "master" else head_ref
    normalized_slots: dict[str, Any] = {"service": effective_service}
    normalized_referents: dict[str, Any] = {}
    if isinstance(payload, Mapping):
        referents = payload.get("referents")
        if isinstance(referents, Mapping) and isinstance(referents.get("service"), Mapping):
            normalized_referents["service"] = dict(referents["service"])
    reason = "standalone_same_service_multifact_fact_request"
    if isinstance(payload, Mapping):
        raw_reason = payload.get("reason")
        if isinstance(raw_reason, str) and raw_reason.strip():
            reason = " ".join(raw_reason.split())
    return {
        "intent": head_intent,
        "action": "fact",
        "tool_action_hint": "catalog.service_query",
        "pack_refs": list(expected_pack_refs),
        "slots": normalized_slots,
        "expected_reply_type": None,
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "language": payload.get("language") if isinstance(payload, Mapping) else None,
        "confidence": payload.get("confidence") if isinstance(payload, Mapping) else None,
        "reason": reason,
        "goal": None,
        "entity_refs": [],
        "referents": normalized_referents,
        "subject_kind": "service",
        "capability": head_ref,
        "temporal_scope": "none",
        "alternate_datetime": None,
        "resolution_mode": "policy_fact",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "resolver_id": None,
        "resolver_version": None,
    }


def _policy_core_build_start_booking_exact_datetime_boundary_payload(
    *,
    payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_is_booking_time_followup_contract(
        _policy_core_resume_pending_contract(normalized_memory_profile)
        or _policy_core_active_pending_contract(normalized_memory_profile)
    ):
        return None
    exact_datetime = _policy_core_current_message_exact_datetime_surface(current_message)
    if not exact_datetime:
        return None
    if _policy_core_current_message_service_scoped_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    ) is not None:
        return None
    if _policy_core_current_message_service_multifact_pack_refs(
        current_message,
        client_slug=client_slug,
    ) is not None:
        return None
    grounded_service = _policy_core_payload_grounded_service(payload)
    grounded_service_hint = _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    effective_service = grounded_service or grounded_service_hint
    if not effective_service:
        return None
    normalized_slots: dict[str, Any] = {"service": effective_service, "datetime": exact_datetime}
    if isinstance(payload, Mapping):
        slots = payload.get("slots")
        if isinstance(slots, Mapping):
            for key in ("name", "phone"):
                value = slots.get(key)
                if isinstance(value, str) and value.strip():
                    normalized_slots[key] = " ".join(value.split())
    normalized_referents: dict[str, Any] = {}
    if isinstance(payload, Mapping):
        referents = payload.get("referents")
        if isinstance(referents, Mapping) and isinstance(referents.get("service"), Mapping):
            normalized_referents["service"] = dict(referents["service"])
    if "service" not in normalized_referents:
        normalized_referents["service"] = {
            "value": effective_service,
            "entity_type": "service",
            "source_ref": "carryover",
        }
    reason = "start_booking_exact_datetime_progression_after_service_carryover"
    if isinstance(payload, Mapping):
        raw_reason = payload.get("reason")
        if isinstance(raw_reason, str) and raw_reason.strip():
            reason = " ".join(raw_reason.split())
    return {
        "intent": "booking",
        "action": "collect",
        "tool_action_hint": "collect",
        "pack_refs": [],
        "slots": normalized_slots,
        "expected_reply_type": "name",
        "next_question": "name",
        "open_questions": ["name"],
        "needs_manager": False,
        "risk_signals": [],
        "language": payload.get("language") if isinstance(payload, Mapping) else None,
        "confidence": payload.get("confidence") if isinstance(payload, Mapping) else None,
        "reason": reason,
        "goal": "booking",
        "entity_refs": [],
        "referents": normalized_referents,
        "subject_kind": "booking",
        "capability": "bookability",
        "temporal_scope": "specific_time",
        "alternate_datetime": exact_datetime,
        "resolution_mode": "direct",
        "pending_question_act": "fill_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "fill_requested_slot",
        "resolver_id": None,
        "resolver_version": None,
    }


def _policy_core_build_mixed_first_turn_promotions_boundary_payload(
    *,
    payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
) -> dict[str, Any] | None:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return None
    if not _policy_core_current_message_has_promotions_query(current_message):
        return None
    if not _policy_core_current_message_has_booking_or_location_side_ask(current_message):
        return None
    expected_pack_refs = _policy_core_current_message_promotions_location_pack_refs(
        current_message
    ) or ["promotions"]
    grounded_service = _policy_core_payload_grounded_service(payload)
    normalized_slots: dict[str, Any] = {}
    normalized_referents: dict[str, Any] = {}
    if grounded_service:
        normalized_slots["service"] = grounded_service
        if isinstance(payload, Mapping):
            referents = payload.get("referents")
            if isinstance(referents, Mapping) and isinstance(referents.get("service"), Mapping):
                normalized_referents["service"] = dict(referents["service"])
    reason = "standalone_promotions_head_intent_with_side_requests"
    if isinstance(payload, Mapping):
        raw_reason = payload.get("reason")
        if isinstance(raw_reason, str) and raw_reason.strip():
            reason = " ".join(raw_reason.split())
    return {
        "intent": "promotions",
        "action": "fact",
        "tool_action_hint": "catalog.service_query",
        "pack_refs": list(expected_pack_refs),
        "slots": normalized_slots,
        "expected_reply_type": None,
        "next_question": None,
        "open_questions": [],
        "needs_manager": False,
        "risk_signals": [],
        "language": payload.get("language") if isinstance(payload, Mapping) else None,
        "confidence": payload.get("confidence") if isinstance(payload, Mapping) else None,
        "reason": reason,
        "goal": None,
        "entity_refs": [],
        "referents": normalized_referents,
        "subject_kind": "service" if grounded_service else "general",
        "capability": "promotions",
        "temporal_scope": "none",
        "alternate_datetime": None,
        "resolution_mode": "policy_fact",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "resolver_id": None,
        "resolver_version": None,
    }


def _policy_core_build_promotions_booking_fact_followup_boundary_payload(
    *,
    payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return None
    expected_pack_refs = _policy_core_current_message_promotions_booking_collect_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return None
    grounded_service = _policy_core_payload_grounded_service(payload) or _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if grounded_service:
        return None
    reason = "standalone_promotions_head_with_missing_service_booking_request"
    if isinstance(payload, Mapping):
        raw_reason = payload.get("reason")
        if isinstance(raw_reason, str) and raw_reason.strip():
            reason = " ".join(raw_reason.split())
    return {
        "intent": "promotions",
        "action": "fact",
        "tool_action_hint": "catalog.service_query",
        "pack_refs": list(expected_pack_refs),
        "slots": {},
        "expected_reply_type": "service_choice",
        "next_question": "service",
        "open_questions": ["service"],
        "needs_manager": False,
        "risk_signals": [],
        "language": payload.get("language") if isinstance(payload, Mapping) else None,
        "confidence": payload.get("confidence") if isinstance(payload, Mapping) else None,
        "reason": reason,
        "goal": "booking",
        "entity_refs": [],
        "referents": {},
        "subject_kind": "general",
        "capability": "promotions",
        "temporal_scope": "none",
        "alternate_datetime": None,
        "resolution_mode": "policy_fact",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "resolver_id": None,
        "resolver_version": None,
    }


def _policy_core_build_promotions_location_booking_followup_boundary_payload(
    *,
    payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return None
    expected_pack_refs = _policy_core_current_message_promotions_location_pack_refs(current_message)
    if expected_pack_refs is None or not _policy_core_current_message_has_booking_side_ask(current_message):
        return None
    grounded_service = _policy_core_payload_grounded_service(payload) or _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if grounded_service:
        return None
    return {
        "intent": "promotions",
        "action": "fact",
        "tool_action_hint": "catalog.service_query",
        "pack_refs": list(expected_pack_refs),
        "slots": {},
        "expected_reply_type": "service_choice",
        "next_question": "service",
        "open_questions": ["service"],
        "needs_manager": False,
        "risk_signals": [],
        "language": payload.get("language") if isinstance(payload, Mapping) else None,
        "confidence": payload.get("confidence") if isinstance(payload, Mapping) else None,
        "reason": "standalone_promotions_location_head_with_missing_service_booking_request",
        "goal": "booking",
        "entity_refs": [],
        "referents": {},
        "subject_kind": "general",
        "capability": "promotions",
        "temporal_scope": "none",
        "alternate_datetime": None,
        "resolution_mode": "policy_fact",
        "pending_question_act": None,
        "pending_question_target": None,
        "active_question_relation": None,
        "resolver_id": None,
        "resolver_version": None,
    }


def _policy_core_build_promotions_grounded_service_booking_followup_boundary_payload(
    *,
    payload: Mapping[str, Any] | None,
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> dict[str, Any] | None:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return None
    expected_pack_refs = _policy_core_current_message_promotions_booking_collect_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return None
    if _policy_core_current_message_has_message_grounded_temporal_clue(current_message):
        return None
    grounded_service = _policy_core_payload_grounded_service(payload) or _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if not grounded_service:
        return None
    normalized_referents: dict[str, Any] = {}
    if isinstance(payload, Mapping):
        referents = payload.get("referents")
        if isinstance(referents, Mapping) and isinstance(referents.get("service"), Mapping):
            normalized_referents["service"] = dict(referents["service"])
    if "service" not in normalized_referents:
        normalized_referents["service"] = {
            "value": grounded_service,
            "entity_type": "service",
            "source_ref": "user_text",
        }
    return {
        "intent": "promotions",
        "action": "fact",
        "tool_action_hint": "catalog.service_query",
        "pack_refs": list(expected_pack_refs),
        "slots": {"service": grounded_service},
        "expected_reply_type": "time",
        "next_question": "datetime",
        "open_questions": ["datetime"],
        "needs_manager": False,
        "risk_signals": [],
        "language": payload.get("language") if isinstance(payload, Mapping) else None,
        "confidence": payload.get("confidence") if isinstance(payload, Mapping) else None,
        "reason": "standalone_promotions_head_with_grounded_service_booking_request",
        "goal": "booking",
        "entity_refs": [],
        "referents": normalized_referents,
        "subject_kind": "service",
        "capability": "promotions",
        "temporal_scope": "none",
        "alternate_datetime": None,
        "resolution_mode": "policy_fact",
        "pending_question_act": "ask_about_requested_slot",
        "pending_question_target": "time",
        "active_question_relation": "ask_about_requested_slot",
        "resolver_id": None,
        "resolver_version": None,
    }


def _policy_core_is_active_booking_live_availability_followup_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    if contract.intent != "master_query" or contract.action != "collect":
        return False
    carry_contract = _policy_core_resume_pending_contract(normalized_memory_profile) or _policy_core_active_pending_contract(
        normalized_memory_profile
    )
    if not _policy_core_is_booking_time_followup_contract(carry_contract):
        return False
    if not (
        contract.tool_action_hint == "calendar.list_slots"
        or contract.capability == "live_availability"
    ):
        return False
    grounded_service = _policy_core_contract_grounded_service(contract) or _policy_core_memory_grounded_service(
        normalized_memory_profile
    )
    if not grounded_service:
        return False
    open_questions = {
        item.strip().casefold()
        for item in list(contract.open_questions or [])
        if isinstance(item, str) and item.strip()
    }
    if contract.next_question == "service" or "service" in open_questions:
        return False
    return True


def _policy_core_is_active_booking_temporal_clue_followup_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None = None,
) -> bool:
    if contract.intent != "booking" or contract.action != "collect":
        return False
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_booking_time_followup_contract(carry_contract):
        return False
    if contract.tool_action_hint != "collect":
        return False
    grounded_service = _policy_core_contract_grounded_service(
        contract
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service:
        return False
    message_has_grounded_temporal_clue = (
        _policy_core_current_message_has_message_grounded_temporal_clue(current_message)
    )
    grounded_specialist = _policy_core_contract_grounded_specialist(
        contract
    ) or _policy_core_memory_grounded_specialist(normalized_memory_profile)
    if grounded_specialist and not message_has_grounded_temporal_clue:
        return False
    if _policy_core_current_message_is_generic_booking_availability_question(current_message):
        return False
    temporal_scope = _policy_core_payload_token(contract.temporal_scope)
    if temporal_scope in {None, "none"} and not message_has_grounded_temporal_clue:
        return False
    if (
        contract.pending_question_act == "fill_requested_slot"
        and contract.active_question_relation == "fill_requested_slot"
    ):
        return False
    if contract.pending_question_target not in {None, "time"}:
        if not (
            message_has_grounded_temporal_clue
            and contract.pending_question_target == "specialist"
        ):
            return False
    alternate_datetime = _policy_core_payload_token(contract.alternate_datetime)
    if _policy_core_temporal_clue_requires_message_grounded_alternate_datetime(
        alternate_datetime,
        current_message,
    ):
        return True
    if temporal_scope in {None, "none"}:
        return True
    if not alternate_datetime:
        return True
    if contract.pending_question_act != "slot_constraint":
        return True
    if contract.active_question_relation != "slot_constraint":
        return True
    if contract.subject_kind != "booking":
        return True
    return False


def _policy_core_is_active_booking_requested_slot_availability_followup_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
) -> bool:
    if not _policy_core_current_message_is_generic_booking_availability_question(
        current_message
    ):
        return False
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_booking_time_followup_contract(carry_contract):
        return False
    grounded_service = _policy_core_contract_grounded_service(
        contract
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service:
        return False
    expected_reply_type = carry_contract.get("expected_reply_type")
    expected_next_question = carry_contract.get("next_question")
    expected_open_questions = _policy_core_expected_open_questions(carry_contract)
    if contract.intent != "booking" or contract.action != "collect":
        return True
    if contract.tool_action_hint != "collect":
        return True
    if contract.subject_kind != "booking":
        return True
    if isinstance(expected_reply_type, str) and expected_reply_type.strip():
        if contract.expected_reply_type != expected_reply_type:
            return True
    if isinstance(expected_next_question, str) and expected_next_question.strip():
        if contract.next_question != expected_next_question:
            return True
    if list(contract.open_questions or []) != expected_open_questions:
        return True
    if contract.pending_question_act != "ask_about_requested_slot":
        return True
    if contract.pending_question_target != "time":
        return True
    if contract.active_question_relation != "ask_about_requested_slot":
        return True
    return False


def _policy_core_is_booking_missing_service_availability_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if contract.intent != "booking" or contract.action != "collect":
        return False
    if not isinstance(current_message, str):
        return False
    normalized_message = " ".join(current_message.split())
    if not normalized_message:
        return False
    if not any(
        pattern.search(normalized_message)
        for pattern in _POLICY_CORE_GENERIC_AVAILABILITY_QUERY_PATTERNS
    ):
        return False
    if not _policy_core_current_message_has_message_grounded_temporal_clue(
        normalized_message
    ):
        return False
    grounded_service_hint = _policy_core_context_service_hint(
        normalized_message,
        context_payload,
        client_slug=client_slug,
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)
    if grounded_service_hint:
        return False
    open_questions = {
        item.strip().casefold()
        for item in list(contract.open_questions or [])
        if isinstance(item, str) and item.strip()
    }
    temporal_scope_hint = _policy_core_current_message_grounded_temporal_scope_hint(
        normalized_message
    )
    if _policy_core_contract_grounded_service(contract):
        return True
    if contract.expected_reply_type != "service_choice":
        return True
    if contract.next_question != "service" or "service" not in open_questions:
        return True
    if contract.pending_question_act is not None:
        return True
    if contract.pending_question_target is not None:
        return True
    if contract.active_question_relation is not None:
        return True
    if contract.subject_kind not in {None, "general"}:
        return True
    if contract.capability != "bookability":
        return True
    if contract.resolution_mode != "clarify_missing_subject":
        return True
    if temporal_scope_hint and contract.temporal_scope != temporal_scope_hint:
        return True
    return False


def _policy_core_is_canonical_promotions_booking_fact_followup_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return False
    expected_pack_refs = _policy_core_current_message_promotions_booking_collect_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return False
    grounded_service = _policy_core_contract_grounded_service(contract) or _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if grounded_service:
        return False
    open_questions = {
        item.strip().casefold()
        for item in list(contract.open_questions or [])
        if isinstance(item, str) and item.strip()
    }
    if contract.intent not in {"promotions", "booking"}:
        return False
    if contract.action != "fact":
        return False
    if contract.tool_action_hint not in {"catalog.service_query", "info"}:
        return False
    if _policy_core_catalog_service_pack_refs(contract) != expected_pack_refs:
        return False
    if contract.expected_reply_type != "service_choice":
        return False
    if contract.next_question != "service" or "service" not in open_questions:
        return False
    if contract.pending_question_act is not None:
        return False
    if contract.pending_question_target is not None:
        return False
    if contract.active_question_relation is not None:
        return False
    if contract.subject_kind not in {None, "general"}:
        return False
    if contract.capability != "promotions":
        return False
    if contract.resolution_mode != "policy_fact":
        return False
    if _policy_core_payload_token(contract.goal) != "booking":
        return False
    return True


def _policy_core_is_canonical_promotions_location_booking_followup_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return False
    expected_pack_refs = _policy_core_current_message_promotions_location_pack_refs(current_message)
    if expected_pack_refs is None or not _policy_core_current_message_has_booking_side_ask(current_message):
        return False
    grounded_service = _policy_core_contract_grounded_service(contract) or _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if grounded_service:
        return False
    open_questions = {
        item.strip().casefold()
        for item in list(contract.open_questions or [])
        if isinstance(item, str) and item.strip()
    }
    if contract.intent != "promotions":
        return False
    if contract.action != "fact":
        return False
    if contract.tool_action_hint not in {"catalog.service_query", "info"}:
        return False
    if _policy_core_catalog_service_pack_refs(contract) != expected_pack_refs:
        return False
    if contract.expected_reply_type != "service_choice":
        return False
    if contract.next_question != "service" or "service" not in open_questions:
        return False
    if contract.pending_question_act is not None:
        return False
    if contract.pending_question_target is not None:
        return False
    if contract.active_question_relation is not None:
        return False
    if contract.subject_kind not in {None, "general"}:
        return False
    if contract.capability != "promotions":
        return False
    if contract.resolution_mode != "policy_fact":
        return False
    if _policy_core_payload_token(contract.goal) != "booking":
        return False
    return True


def _policy_core_is_promotions_location_booking_followup_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return False
    expected_pack_refs = _policy_core_current_message_promotions_location_pack_refs(current_message)
    if expected_pack_refs is None or not _policy_core_current_message_has_booking_side_ask(current_message):
        return False
    grounded_service = _policy_core_contract_grounded_service(contract) or _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if grounded_service:
        return False
    return not _policy_core_is_canonical_promotions_location_booking_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    )


def _policy_core_is_promotions_booking_fact_followup_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return False
    expected_pack_refs = _policy_core_current_message_promotions_booking_collect_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return False
    grounded_service = _policy_core_contract_grounded_service(contract) or _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if grounded_service:
        return False
    return not _policy_core_is_canonical_promotions_booking_fact_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    )


def _policy_core_is_canonical_promotions_grounded_service_booking_followup_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return False
    expected_pack_refs = _policy_core_current_message_promotions_booking_collect_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return False
    if _policy_core_current_message_has_message_grounded_temporal_clue(current_message):
        return False
    grounded_service = _policy_core_contract_grounded_service(contract) or _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if not grounded_service:
        return False
    if contract.intent not in {"promotions", "booking"}:
        return False
    if contract.action != "fact":
        return False
    if contract.tool_action_hint not in {"catalog.service_query", "info"}:
        return False
    if _policy_core_catalog_service_pack_refs(contract) != expected_pack_refs:
        return False
    if contract.expected_reply_type != "time":
        return False
    if contract.next_question != "datetime":
        return False
    if list(contract.open_questions or []) != ["datetime"]:
        return False
    if contract.pending_question_act != "ask_about_requested_slot":
        return False
    if contract.pending_question_target != "time":
        return False
    if contract.active_question_relation != "ask_about_requested_slot":
        return False
    if contract.subject_kind != "service":
        return False
    if contract.capability != "promotions":
        return False
    if contract.resolution_mode != "policy_fact":
        return False
    if _policy_core_payload_token(contract.goal) != "booking":
        return False
    return True


def _policy_core_is_promotions_grounded_service_booking_followup_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return False
    expected_pack_refs = _policy_core_current_message_promotions_booking_collect_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return False
    if _policy_core_current_message_has_message_grounded_temporal_clue(current_message):
        return False
    grounded_service = _policy_core_contract_grounded_service(contract) or _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if not grounded_service:
        return False
    return not _policy_core_is_canonical_promotions_grounded_service_booking_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    )


def _policy_core_is_mixed_first_turn_hours_service_fact_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_is_canonical_hours_location_service_fact_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return False
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return False
    expected_pack_refs = _policy_core_current_message_hours_service_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return False
    grounded_service = _policy_core_contract_grounded_service(contract)
    grounded_service_hint = _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if not grounded_service and not grounded_service_hint:
        return False
    normalized_pack_refs = {
        item.strip().casefold()
        for item in list(contract.pack_refs or [])
        if isinstance(item, str) and item.strip()
    }
    asks_hours = (
        contract.intent == "hours"
        or contract.capability == "hours"
        or "hours" in _policy_core_catalog_location_pack_refs(contract)
    )
    if not asks_hours:
        return False
    if not grounded_service:
        return True
    if contract.action != "fact":
        return True
    if contract.tool_action_hint != "info":
        return True
    if normalized_pack_refs != set(expected_pack_refs):
        return True
    if contract.subject_kind != "service":
        return True
    if contract.capability != "hours":
        return True
    if contract.resolution_mode != "policy_fact":
        return True
    if contract.expected_reply_type is not None:
        return True
    if contract.next_question is not None:
        return True
    if list(contract.open_questions or []):
        return True
    if contract.pending_question_act is not None:
        return True
    if contract.pending_question_target is not None:
        return True
    if contract.active_question_relation is not None:
        return True
    return False


def _policy_core_is_canonical_hours_location_service_fact_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return False
    expected_pack_refs = _policy_core_current_message_hours_location_service_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return False
    grounded_service = _policy_core_contract_grounded_service(contract)
    grounded_service_hint = _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if not grounded_service and not grounded_service_hint:
        return False
    normalized_pack_refs = {
        item.strip().casefold()
        for item in list(contract.pack_refs or [])
        if isinstance(item, str) and item.strip()
    }
    if contract.action != "fact":
        return False
    if contract.tool_action_hint != "info":
        return False
    if normalized_pack_refs != set(expected_pack_refs):
        return False
    if contract.subject_kind != "service":
        return False
    if contract.resolution_mode != "policy_fact":
        return False
    if contract.expected_reply_type is not None:
        return False
    if contract.next_question is not None:
        return False
    if list(contract.open_questions or []):
        return False
    if contract.pending_question_act is not None:
        return False
    if contract.pending_question_target is not None:
        return False
    if contract.active_question_relation is not None:
        return False
    return (contract.intent, contract.capability) in {
        ("hours", "hours"),
        ("location", "location"),
    }


def _policy_core_is_canonical_hours_location_fact_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return False
    expected_pack_refs = _policy_core_current_message_hours_location_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return False
    grounded_service = _policy_core_contract_grounded_service(contract)
    grounded_service_hint = _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if grounded_service or grounded_service_hint:
        return False
    normalized_pack_refs = [
        item.strip().casefold()
        for item in list(contract.pack_refs or [])
        if isinstance(item, str) and item.strip()
    ]
    if contract.action != "fact":
        return False
    if contract.tool_action_hint != "info":
        return False
    if normalized_pack_refs != list(expected_pack_refs):
        return False
    if contract.intent not in {"hours", "location"}:
        return False
    if contract.capability != contract.intent:
        return False
    if contract.subject_kind != "general":
        return False
    if contract.resolution_mode != "policy_fact":
        return False
    if contract.expected_reply_type is not None:
        return False
    if contract.next_question is not None:
        return False
    if list(contract.open_questions or []):
        return False
    if contract.pending_question_act is not None:
        return False
    if contract.pending_question_target is not None:
        return False
    if contract.active_question_relation is not None:
        return False
    return True


def _policy_core_is_mixed_first_turn_hours_location_fact_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return False
    expected_pack_refs = _policy_core_current_message_hours_location_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return False
    grounded_service = _policy_core_contract_grounded_service(contract)
    grounded_service_hint = _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if grounded_service or grounded_service_hint:
        return False
    return not _policy_core_is_canonical_hours_location_fact_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    )


def _policy_core_is_mixed_first_turn_location_service_fact_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_is_canonical_promotions_grounded_service_booking_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return False
    if _policy_core_is_canonical_hours_location_service_fact_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return False
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return False
    expected_pack_refs = _policy_core_current_message_location_service_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return False
    grounded_service = _policy_core_contract_grounded_service(contract)
    grounded_service_hint = _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if not grounded_service and not grounded_service_hint:
        return False
    normalized_pack_refs = [
        item.strip().casefold()
        for item in list(contract.pack_refs or [])
        if isinstance(item, str) and item.strip()
    ]
    if contract.action != "fact":
        return True
    if contract.tool_action_hint != "info":
        return True
    if normalized_pack_refs != list(expected_pack_refs):
        return True
    if contract.intent != "location":
        return True
    if contract.subject_kind != "service":
        return True
    if contract.capability != "location":
        return True
    if contract.resolution_mode != "policy_fact":
        return True
    if contract.expected_reply_type is not None:
        return True
    if contract.next_question is not None:
        return True
    if list(contract.open_questions or []):
        return True
    if contract.pending_question_act is not None:
        return True
    if contract.pending_question_target is not None:
        return True
    if contract.active_question_relation is not None:
        return True
    return grounded_service is None


def _policy_core_is_mixed_first_turn_service_fact_booking_side_precedence_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return False
    expected_pack_refs = _policy_core_current_message_service_scoped_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return False
    expected_ref = expected_pack_refs[0]
    grounded_service = _policy_core_contract_grounded_service(contract)
    grounded_service_hint = _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if not grounded_service and not grounded_service_hint:
        return False
    normalized_pack_refs = [
        item.strip().casefold()
        for item in list(contract.pack_refs or [])
        if isinstance(item, str) and item.strip()
    ]
    if contract.action != "fact":
        return True
    if contract.tool_action_hint != "catalog.service_query":
        return True
    if normalized_pack_refs != [expected_ref]:
        return True
    if contract.intent != expected_ref:
        return True
    if contract.subject_kind != "service":
        return True
    if contract.capability != expected_ref:
        return True
    if contract.resolution_mode != "policy_fact":
        return True
    if contract.expected_reply_type is not None:
        return True
    if contract.next_question is not None:
        return True
    if list(contract.open_questions or []):
        return True
    if contract.pending_question_act is not None:
        return True
    if contract.pending_question_target is not None:
        return True
    if contract.active_question_relation is not None:
        return True
    return grounded_service is None


def _policy_core_is_service_query_multifact_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return False
    expected_pack_refs = _policy_core_current_message_service_multifact_pack_refs(
        current_message,
        client_slug=client_slug,
    )
    if expected_pack_refs is None:
        return False
    grounded_service = _policy_core_contract_grounded_service(contract)
    grounded_service_hint = _policy_core_resolve_message_grounded_service_hint(
        current_message=current_message,
        context_payload=context_payload,
        normalized_memory_profile=normalized_memory_profile,
        client_slug=client_slug,
    )
    if not grounded_service and not grounded_service_hint:
        return False
    if _policy_core_is_canonical_promotions_grounded_service_booking_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return False
    normalized_pack_refs = _policy_core_catalog_service_pack_refs(contract)
    if contract.action != "fact":
        return True
    if contract.tool_action_hint != "catalog.service_query":
        return True
    if normalized_pack_refs != expected_pack_refs:
        return True
    contract_intent_ref = "master" if contract.intent == "master_query" else contract.intent
    if contract_intent_ref not in expected_pack_refs:
        return True
    if contract.subject_kind != "service":
        return True
    if contract.capability not in expected_pack_refs:
        return True
    if contract.resolution_mode != "policy_fact":
        return True
    if contract.temporal_scope != "none":
        return True
    if contract.alternate_datetime is not None:
        return True
    if contract.expected_reply_type is not None:
        return True
    if contract.next_question is not None:
        return True
    if list(contract.open_questions or []):
        return True
    if contract.pending_question_act is not None:
        return True
    if contract.pending_question_target is not None:
        return True
    if contract.active_question_relation is not None:
        return True
    return grounded_service is None


def _policy_core_is_canonical_standalone_promotions_fact_contract(
    contract: LlmPolicyCoreOutput,
) -> bool:
    if contract.action != "fact":
        return False
    if contract.intent in {"out_of_domain", "other"}:
        return False
    normalized_pack_refs = {
        item.strip().casefold()
        for item in list(contract.pack_refs or [])
        if isinstance(item, str) and item.strip()
    }
    if "promotions" not in normalized_pack_refs:
        return False
    if contract.tool_action_hint not in {"info", "catalog.service_query"}:
        return False
    if contract.capability != "promotions":
        return False
    if contract.resolution_mode != "policy_fact":
        return False
    if contract.expected_reply_type is not None:
        return False
    if contract.next_question is not None:
        return False
    if list(contract.open_questions or []):
        return False
    if contract.pending_question_act is not None:
        return False
    if contract.pending_question_target is not None:
        return False
    if contract.active_question_relation is not None:
        return False
    grounded_service = _policy_core_contract_grounded_service(contract)
    expected_subject_kind = "service" if grounded_service else "general"
    return contract.subject_kind == expected_subject_kind


def _policy_core_is_mixed_first_turn_promotions_precedence_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    context_payload: Mapping[str, Any] | None,
    client_slug: str | None,
) -> bool:
    if _policy_core_active_pending_contract(normalized_memory_profile) or _policy_core_resume_pending_contract(
        normalized_memory_profile
    ):
        return False
    if not _policy_core_current_message_has_promotions_query(current_message):
        return False
    if not _policy_core_current_message_has_booking_or_location_side_ask(current_message):
        return False
    if contract.action == "handoff":
        return False
    if _policy_core_is_canonical_hours_location_fact_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return False
    if _policy_core_is_canonical_hours_location_service_fact_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return False
    if _policy_core_is_canonical_promotions_grounded_service_booking_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return False
    if _policy_core_is_canonical_promotions_location_booking_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return False
    if _policy_core_is_canonical_promotions_booking_fact_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return False
    expected_pack_refs = _policy_core_current_message_promotions_location_pack_refs(current_message)
    if expected_pack_refs is not None:
        normalized_pack_refs = _policy_core_catalog_service_pack_refs(contract)
        if normalized_pack_refs != expected_pack_refs:
            return True
    return not _policy_core_is_canonical_standalone_promotions_fact_contract(contract)


def _policy_core_is_start_booking_temporal_clue_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
) -> bool:
    if contract.intent != "booking" or contract.action != "collect":
        return False
    if contract.tool_action_hint != "collect":
        return False
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if _policy_core_is_booking_time_followup_contract(carry_contract):
        return False
    grounded_service = _policy_core_contract_grounded_service(
        contract
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service:
        return False
    if not _policy_core_current_message_has_message_grounded_temporal_clue(
        current_message
    ):
        return False
    if _policy_core_current_message_has_explicit_clock_time(current_message):
        return False
    temporal_scope = _policy_core_payload_token(contract.temporal_scope)
    alternate_datetime = _policy_core_payload_token(contract.alternate_datetime)
    if _policy_core_temporal_clue_requires_message_grounded_alternate_datetime(
        alternate_datetime,
        current_message,
    ):
        return True
    if contract.expected_reply_type != "time":
        return True
    if contract.next_question != "datetime":
        return True
    if list(contract.open_questions or []) != ["datetime"]:
        return True
    if contract.pending_question_act != "slot_constraint":
        return True
    if contract.pending_question_target != "time":
        return True
    if contract.active_question_relation != "slot_constraint":
        return True
    if contract.subject_kind != "booking":
        return True
    if temporal_scope in {None, "none"}:
        return True
    if not alternate_datetime:
        return True
    return False


def _policy_core_is_start_booking_exact_datetime_progression_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
    client_slug: str | None = None,
) -> bool:
    if contract.intent != "booking":
        return False
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if _policy_core_is_booking_time_followup_contract(carry_contract):
        return False
    if not _policy_core_current_message_exact_datetime_surface(current_message):
        return False
    if _policy_core_current_message_service_scoped_fact_pack_refs(
        current_message,
        client_slug=client_slug,
    ) is not None:
        return False
    if _policy_core_current_message_service_multifact_pack_refs(
        current_message,
        client_slug=client_slug,
    ) is not None:
        return False
    grounded_service = _policy_core_contract_grounded_service(
        contract
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service:
        return False
    if _policy_core_has_customer_identity(contract, normalized_memory_profile):
        return False
    if contract.action != "collect" or contract.tool_action_hint != "collect":
        return True
    contract_datetime = _policy_core_normalize_surface_text(contract.slots.get("datetime"))
    if not contract_datetime:
        return True
    if contract.expected_reply_type != "name":
        return True
    if contract.next_question != "name":
        return True
    if list(contract.open_questions or []) != ["name"]:
        return True
    if contract.pending_question_act != "fill_requested_slot":
        return True
    if contract.pending_question_target != "time":
        return True
    if contract.active_question_relation != "fill_requested_slot":
        return True
    if contract.subject_kind != "booking":
        return True
    if contract.capability != "bookability":
        return True
    if contract.temporal_scope != "specific_time":
        return True
    if not _policy_core_normalize_surface_text(contract.alternate_datetime):
        return True
    return False


def _policy_core_is_active_booking_subject_info_interrupt_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_booking_time_followup_contract(carry_contract):
        return False
    grounded_service = _policy_core_contract_grounded_service(
        contract
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service:
        return False
    if contract.action != "fact":
        return False
    if contract.tool_action_hint != "info":
        return False
    if contract.subject_kind != "booking":
        return False
    if contract.capability not in {"bookability", "booking_manage"}:
        return False
    return contract.active_question_relation == "generic_info_interrupt"


def _policy_core_is_active_booking_manage_interrupt_handoff_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    if _policy_core_is_explicit_manager_handoff_contract(contract):
        return False
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_booking_time_followup_contract(carry_contract):
        return False
    grounded_service = _policy_core_contract_grounded_service(
        contract
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service:
        return False
    if contract.action != "handoff":
        return False
    if contract.tool_action_hint != "handoff":
        return False
    if contract.subject_kind != "booking":
        return False
    if contract.capability != "booking_manage":
        return False
    return bool(contract.needs_manager)


def _policy_core_is_active_booking_specialist_preference_followup_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None = None,
) -> bool:
    if contract.intent != "booking" or contract.action != "collect":
        return False
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_booking_time_followup_contract(carry_contract):
        return False
    grounded_service = _policy_core_contract_grounded_service(
        contract
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service:
        return False
    grounded_specialist = _policy_core_contract_grounded_specialist(
        contract
    ) or _policy_core_memory_grounded_specialist(normalized_memory_profile)
    if not grounded_specialist:
        return False
    if _policy_core_current_message_has_explicit_customer_name_intro(current_message):
        return False
    if _policy_core_contract_customer_entity_name(contract):
        return False
    if (
        _policy_core_current_message_has_message_grounded_temporal_clue(current_message)
        and not _policy_core_has_customer_identity(contract, normalized_memory_profile)
    ):
        return False
    if (
        _policy_core_current_message_has_explicit_clock_time(current_message)
        and _policy_core_memory_has_datetime_context(normalized_memory_profile)
        and not _policy_core_has_customer_identity(contract, normalized_memory_profile)
    ):
        return False
    expected_reply_type = carry_contract.get("expected_reply_type")
    expected_next_question = carry_contract.get("next_question")
    if isinstance(expected_reply_type, str) and expected_reply_type.strip():
        if contract.expected_reply_type != expected_reply_type:
            return True
    if isinstance(expected_next_question, str) and expected_next_question.strip():
        if contract.next_question != expected_next_question:
            return True
        if list(contract.open_questions or []) != _policy_core_expected_open_questions(carry_contract):
            return True
    if contract.subject_kind != "specialist":
        return True
    if contract.capability != "bookability":
        return True
    if contract.resolution_mode != "referent_followup":
        return True
    if contract.pending_question_target != "specialist":
        return True
    if contract.active_question_relation != "referent_followup":
        return True
    return False


def _policy_core_is_active_booking_time_fill_progression_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
) -> bool:
    if contract.intent != "booking" or contract.action != "collect":
        return False
    if _policy_core_payload_token(contract.capability) == "live_availability":
        return False
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_booking_time_followup_contract(carry_contract):
        return False
    grounded_service = _policy_core_contract_grounded_service(
        contract
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service:
        return False
    if _policy_core_has_customer_identity(contract, normalized_memory_profile):
        return False
    if not _policy_core_memory_has_datetime_context(normalized_memory_profile):
        return False
    if not _policy_core_current_message_has_explicit_clock_time(current_message):
        return False
    if contract.expected_reply_type != "name":
        return True
    if contract.next_question != "name":
        return True
    if list(contract.open_questions or []) != ["name"]:
        return True
    if contract.pending_question_act != "fill_requested_slot":
        return True
    if contract.pending_question_target != "time":
        return True
    if contract.active_question_relation != "fill_requested_slot":
        return True
    return False


def _policy_core_is_active_booking_commit_progression_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
) -> bool:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_booking_time_followup_contract(carry_contract):
        return False
    grounded_service = _policy_core_contract_grounded_service(
        contract
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service:
        return False
    if not _policy_core_memory_has_datetime_context(normalized_memory_profile):
        return False
    if not _policy_core_current_message_has_explicit_clock_time(current_message):
        return False
    if _policy_core_current_message_is_generic_booking_availability_question(current_message):
        return False
    if not _policy_core_has_customer_identity(contract, normalized_memory_profile):
        return False
    if contract.intent != "booking" or contract.action != "fact":
        return True
    if contract.tool_action_hint != "calendar.book_slot":
        return True
    if contract.subject_kind != "booking":
        return True
    if contract.capability != "bookability":
        return True
    if contract.resolution_mode != "live_calendar":
        return True
    contract_datetime = _policy_core_payload_token(contract.slots.get("datetime"))
    if not contract_datetime or not _policy_core_current_message_has_explicit_clock_time(
        contract_datetime
    ):
        return True
    if not _policy_core_payload_token(contract.slots.get("name")):
        return True
    if not _policy_core_booking_commit_ready(contract, normalized_memory_profile):
        return True
    if contract.expected_reply_type is not None:
        return True
    if contract.next_question is not None:
        return True
    if list(contract.open_questions or []) != []:
        return True
    if any(
        (
            contract.pending_question_act,
            contract.pending_question_target,
            contract.active_question_relation,
        )
    ):
        return True
    return False


def _policy_core_is_active_booking_customer_name_carryover_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
    *,
    current_message: str | None,
) -> bool:
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_booking_time_followup_contract(carry_contract):
        return False
    grounded_service = _policy_core_contract_grounded_service(
        contract
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service:
        return False
    has_explicit_name_intro = _policy_core_current_message_has_explicit_customer_name_intro(
        current_message
    )
    customer_name = _policy_core_contract_customer_entity_name(contract)
    if not (customer_name or has_explicit_name_intro):
        return False
    if (
        has_explicit_name_intro
        and not _policy_core_current_message_has_message_grounded_temporal_clue(current_message)
    ):
        carried_alternate_datetime = _policy_core_memory_alternate_datetime(
            normalized_memory_profile
        )
        contract_alternate_datetime = _policy_core_normalize_surface_text(
            contract.alternate_datetime
        )
        if isinstance(carried_alternate_datetime, str) and carried_alternate_datetime:
            carried_signature = carried_alternate_datetime.casefold()
            contract_signature = contract_alternate_datetime.casefold() if isinstance(contract_alternate_datetime, str) else None
            if contract_signature != carried_signature:
                return True
        carried_temporal_scope = _policy_core_memory_temporal_scope(normalized_memory_profile)
        if (
            isinstance(carried_temporal_scope, str)
            and carried_temporal_scope
            and _policy_core_payload_token(contract.temporal_scope) != carried_temporal_scope
        ):
            return True
    if (
        _policy_core_current_message_has_explicit_clock_time(current_message)
        and _policy_core_memory_has_datetime_context(normalized_memory_profile)
        and contract.intent == "booking"
        and contract.action == "fact"
        and contract.tool_action_hint == "calendar.book_slot"
        and contract.subject_kind == "booking"
        and contract.capability == "bookability"
        and contract.resolution_mode == "live_calendar"
        and _policy_core_booking_commit_ready(contract, normalized_memory_profile)
    ):
        return False
    if contract.intent != "booking" or contract.action != "collect":
        return True
    if _policy_core_payload_token(contract.capability) == "live_availability":
        return True
    if contract.tool_action_hint != "collect":
        return True
    if contract.subject_kind != "booking":
        return True
    if contract.resolution_mode == "referent_followup":
        return True
    if not _policy_core_has_customer_identity(contract, normalized_memory_profile):
        return True
    expected_reply_type = carry_contract.get("expected_reply_type")
    expected_next_question = carry_contract.get("next_question")
    if isinstance(expected_reply_type, str) and expected_reply_type.strip():
        if contract.expected_reply_type != expected_reply_type:
            return True
    if isinstance(expected_next_question, str) and expected_next_question.strip():
        if contract.next_question != expected_next_question:
            return True
        if list(contract.open_questions or []) != _policy_core_expected_open_questions(carry_contract):
            return True
    pending_act = carry_contract.get("pending_question_act")
    if isinstance(pending_act, str) and pending_act.strip():
        if contract.pending_question_act != pending_act:
            return True
    pending_target = carry_contract.get("pending_question_target")
    if isinstance(pending_target, str) and pending_target.strip():
        if contract.pending_question_target != pending_target:
            return True
    active_relation = carry_contract.get("active_question_relation")
    if isinstance(active_relation, str) and active_relation.strip():
        if contract.active_question_relation != active_relation:
            return True
    return False


def _policy_core_is_active_booking_generic_specialist_query_followup_contract(
    contract: LlmPolicyCoreOutput,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> bool:
    if contract.intent != "booking" or contract.action != "collect":
        return False
    if contract.subject_kind != "specialist":
        return False
    if not _policy_core_reason_indicates_followup_interrupt(contract.reason):
        return False
    carry_contract = _policy_core_resume_pending_contract(
        normalized_memory_profile
    ) or _policy_core_active_pending_contract(normalized_memory_profile)
    if not _policy_core_is_booking_time_followup_contract(carry_contract):
        return False
    grounded_service = _policy_core_contract_grounded_service(
        contract
    ) or _policy_core_memory_grounded_service(normalized_memory_profile)
    if not grounded_service:
        return False
    grounded_specialist = _policy_core_contract_grounded_specialist(
        contract
    ) or _policy_core_memory_grounded_specialist(normalized_memory_profile)
    if grounded_specialist:
        return False
    open_questions = {
        item.strip().casefold()
        for item in list(contract.open_questions or [])
        if isinstance(item, str) and item.strip()
    }
    if contract.next_question == "service" or "service" in open_questions:
        return False
    return True


def _validate_policy_core_runtime_contract(
    contract: LlmPolicyCoreOutput,
    *,
    normalized_memory_profile: Mapping[str, Any] | None,
    current_message: str | None = None,
    context_payload: Mapping[str, Any] | None = None,
    client_slug: str | None = None,
) -> str | None:
    referents = contract.referents if isinstance(contract.referents, dict) else {}
    has_booking_ref = _policy_core_has_grounded_referent(referents, "booking_ref")
    has_customer = _policy_core_has_grounded_referent(referents, "customer") or bool(
        contract.slots.get("name")
    )
    grounded_service = _policy_core_contract_grounded_service(contract)
    service_hint = _policy_core_context_service_hint(
        current_message,
        context_payload,
        client_slug=client_slug,
    ) or (
        _policy_core_memory_grounded_service(normalized_memory_profile)
    )

    if _policy_core_is_booking_manage_name_fill_followup_contract(
        contract,
        normalized_memory_profile,
    ):
        return "llm_policy_core_error:booking_manage_name_fill_followup_invalid"

    booking_manage_reference_followup_shape = _policy_core_is_booking_manage_reference_followup_shape(
        contract,
        normalized_memory_profile,
    )
    explicit_manager_handoff = _policy_core_is_explicit_manager_handoff_contract(contract)
    if (
        not has_booking_ref
        and not explicit_manager_handoff
        and (
            (
                contract.capability == "booking_manage"
                and contract.subject_kind == "booking"
                and contract.intent in _BOOKING_MANAGE_REFERENCE_INTENTS
            )
            or booking_manage_reference_followup_shape
        )
    ):
        direct_lookup_context = _policy_core_booking_manage_reference_direct_lookup_context(
            contract,
            normalized_memory_profile,
        )
        expected_reply_type = None if direct_lookup_context else ("time" if has_customer else "name")
        expected_next_question = None if direct_lookup_context else ("datetime" if has_customer else "name")
        expected_open_questions = [] if direct_lookup_context else [expected_next_question]
        if contract.action != "fact":
            return "llm_policy_core_error:booking_manage_reference_action_invalid"
        if contract.tool_action_hint != "calendar.get_booking":
            return "llm_policy_core_error:booking_manage_reference_tool_action_invalid"
        if contract.expected_reply_type != expected_reply_type:
            return "llm_policy_core_error:booking_manage_reference_expected_reply_invalid"
        if contract.next_question != expected_next_question:
            return "llm_policy_core_error:booking_manage_reference_next_question_invalid"
        if list(contract.open_questions or []) != expected_open_questions:
            return "llm_policy_core_error:booking_manage_reference_open_questions_invalid"
        if direct_lookup_context and any(
            (
                contract.pending_question_act,
                contract.pending_question_target,
                contract.active_question_relation,
            )
        ):
            return "llm_policy_core_error:booking_manage_reference_stale_axes"
        if (
            not direct_lookup_context
            and not has_customer
            and any(
                (
                    contract.pending_question_act,
                    contract.pending_question_target,
                    contract.active_question_relation,
                )
            )
        ):
            return "llm_policy_core_error:booking_manage_reference_stale_axes"

    if (
        has_booking_ref
        and contract.capability == "booking_manage"
        and contract.subject_kind == "booking"
        and contract.action == "fact"
        and contract.tool_action_hint == "calendar.cancel"
        and _policy_core_current_message_is_hypothetical_cancel_query(
            current_message
        )
    ):
        return "llm_policy_core_error:booking_manage_grounded_ref_cancel_requires_direct_commit"

    if (
        contract.tool_action_hint == "calendar.book_slot"
        and _policy_core_booking_commit_ready(contract, normalized_memory_profile)
        and contract.action != "fact"
    ):
        return "llm_policy_core_error:booking_commit_action_invalid"

    pending_contract = _policy_core_active_pending_contract(normalized_memory_profile)
    resume_contract = _policy_core_resume_pending_contract(normalized_memory_profile)
    carry_contract = resume_contract or pending_contract

    if _policy_core_is_media_reason_family(contract.reason):
        if resume_contract and _policy_core_reason_indicates_followup_interrupt(contract.reason):
            return "llm_policy_core_error:active_followup_interrupt_reclassification_required"
        if contract.intent != "consult":
            return "llm_policy_core_error:consult_media_intent_invalid"
        if contract.action != "collect":
            return "llm_policy_core_error:consult_media_action_invalid"
        if contract.tool_action_hint != "consult":
            return "llm_policy_core_error:consult_media_tool_action_invalid"
        if contract.capability not in {"consultation", "bookability"}:
            return "llm_policy_core_error:consult_media_capability_invalid"
        if "style_reference" not in list(contract.pack_refs or []):
            return "llm_policy_core_error:consult_media_pack_refs_invalid"
        if contract.expected_reply_type != "media":
            return "llm_policy_core_error:consult_media_expected_reply_invalid"
        if contract.next_question != "media":
            return "llm_policy_core_error:consult_media_next_question_invalid"
        if list(contract.open_questions or []) != ["media"]:
            return "llm_policy_core_error:consult_media_open_questions_invalid"
        expected_pending_act = resume_contract.get("pending_question_act")
        if expected_pending_act and contract.pending_question_act != expected_pending_act:
            return "llm_policy_core_error:consult_media_pending_act_invalid"
        expected_pending_target = resume_contract.get("pending_question_target")
        if expected_pending_target and contract.pending_question_target != expected_pending_target:
            return "llm_policy_core_error:consult_media_pending_target_invalid"
        expected_relation = resume_contract.get("active_question_relation")
        if expected_relation and contract.active_question_relation != expected_relation:
            return "llm_policy_core_error:consult_media_relation_invalid"

    if _policy_core_is_active_booking_manage_interrupt_handoff_contract(
        contract,
        normalized_memory_profile,
    ):
        return "llm_policy_core_error:active_booking_manage_interrupt_reclassification_required"

    if _policy_core_is_active_booking_subject_info_interrupt_contract(
        contract,
        normalized_memory_profile,
    ):
        return "llm_policy_core_error:active_booking_manage_interrupt_reclassification_required"

    carry_reply_type = carry_contract.get("expected_reply_type")
    carry_next_question = carry_contract.get("next_question")
    if (
        _policy_core_is_active_followup_info_interrupt(contract)
        and isinstance(carry_reply_type, str)
        and carry_reply_type.strip()
        and isinstance(carry_next_question, str)
        and carry_next_question.strip()
    ):
        active_followup_master_query = _policy_core_is_active_followup_master_query_shape(
            intent=contract.intent,
            next_question=contract.next_question,
            open_questions=list(contract.open_questions or []),
            normalized_memory_profile=normalized_memory_profile,
        )
        expected_open_questions = _policy_core_expected_open_questions(carry_contract)
        if contract.expected_reply_type != carry_reply_type:
            return (
                "llm_policy_core_error:active_followup_master_query_reclassification_required"
                if active_followup_master_query
                else "llm_policy_core_error:generic_info_interrupt_expected_reply_invalid"
            )
        if contract.next_question != carry_next_question:
            return (
                "llm_policy_core_error:active_followup_master_query_reclassification_required"
                if active_followup_master_query
                else "llm_policy_core_error:generic_info_interrupt_next_question_invalid"
            )
        if list(contract.open_questions or []) != expected_open_questions:
            return (
                "llm_policy_core_error:active_followup_master_query_reclassification_required"
                if active_followup_master_query
                else "llm_policy_core_error:generic_info_interrupt_open_questions_invalid"
            )
        expected_pending_act = carry_contract.get("pending_question_act")
        if expected_pending_act and contract.pending_question_act != expected_pending_act:
            return (
                "llm_policy_core_error:active_followup_master_query_reclassification_required"
                if active_followup_master_query
                else "llm_policy_core_error:generic_info_interrupt_pending_act_invalid"
            )
        expected_pending_target = carry_contract.get("pending_question_target")
        if expected_pending_target and contract.pending_question_target != expected_pending_target:
            return (
                "llm_policy_core_error:active_followup_master_query_reclassification_required"
                if active_followup_master_query
                else "llm_policy_core_error:generic_info_interrupt_pending_target_invalid"
            )
        if active_followup_master_query and contract.active_question_relation != "generic_info_interrupt":
            return "llm_policy_core_error:active_followup_master_query_reclassification_required"

    if (
        _policy_core_has_active_media_resume(normalized_memory_profile)
        and _policy_core_is_master_query_time_collect(contract)
    ):
        return "llm_policy_core_error:active_followup_master_query_reclassification_required"

    if (
        _policy_core_has_active_media_resume(normalized_memory_profile)
        and _policy_core_is_pending_media_time_interrupt_reason(contract.reason)
        and (
            contract.expected_reply_type == "media"
            or contract.next_question == "media"
            or "media"
            in {
                item.strip().casefold()
                for item in list(contract.open_questions or [])
                if isinstance(item, str) and item.strip()
            }
        )
    ):
        return "llm_policy_core_error:active_media_time_interrupt_reclassification_required"

    if _policy_core_is_active_booking_live_availability_followup_contract(
        contract,
        normalized_memory_profile,
    ):
        return "llm_policy_core_error:active_booking_live_availability_reclassification_required"

    if _policy_core_is_start_booking_temporal_clue_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
    ):
        return "llm_policy_core_error:start_booking_temporal_clue_reclassification_required"

    if _policy_core_is_start_booking_exact_datetime_progression_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        client_slug=client_slug,
    ):
        return "llm_policy_core_error:start_booking_exact_datetime_progression_required"

    if _policy_core_is_active_booking_requested_slot_availability_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
    ):
        return "llm_policy_core_error:active_booking_requested_slot_availability_resolution_required"

    if _policy_core_is_active_booking_time_fill_progression_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
    ):
        return "llm_policy_core_error:active_booking_time_fill_progression_required"

    if _policy_core_is_active_booking_commit_progression_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
    ):
        return "llm_policy_core_error:active_booking_commit_progression_required"

    if _policy_core_is_active_booking_customer_name_carryover_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
    ):
        return "llm_policy_core_error:active_booking_customer_name_carryover_required"

    if _policy_core_is_active_booking_specialist_preference_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
    ):
        return "llm_policy_core_error:active_booking_specialist_followup_reclassification_required"

    if _policy_core_is_active_booking_generic_specialist_query_followup_contract(
        contract,
        normalized_memory_profile,
    ):
        return "llm_policy_core_error:active_booking_generic_specialist_query_reclassification_required"

    if _policy_core_is_booking_missing_service_availability_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return "llm_policy_core_error:booking_availability_missing_service_reclassification_required"

    if _policy_core_is_mixed_first_turn_hours_location_fact_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return "llm_policy_core_error:mixed_first_turn_hours_location_fact_scope_required"

    if _policy_core_is_mixed_first_turn_location_service_fact_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return "llm_policy_core_error:mixed_first_turn_location_service_fact_reclassification_required"

    if _policy_core_is_mixed_first_turn_service_fact_booking_side_precedence_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return "llm_policy_core_error:mixed_first_turn_service_fact_booking_side_precedence_required"

    if _policy_core_is_mixed_first_turn_hours_service_fact_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return "llm_policy_core_error:mixed_first_turn_hours_service_fact_reclassification_required"

    if _policy_core_is_promotions_grounded_service_booking_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return "llm_policy_core_error:promotions_grounded_service_booking_followup_reclassification_required"

    if _policy_core_is_promotions_location_booking_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return "llm_policy_core_error:promotions_location_booking_followup_reclassification_required"

    if _policy_core_is_promotions_booking_fact_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return "llm_policy_core_error:promotions_booking_followup_reclassification_required"

    if _policy_core_is_service_query_multifact_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return "llm_policy_core_error:service_query_multifact_reclassification_required"

    if _policy_core_is_mixed_first_turn_promotions_precedence_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
        context_payload=context_payload,
        client_slug=client_slug,
    ):
        return "llm_policy_core_error:mixed_first_turn_promotions_precedence_reclassification_required"

    if _policy_core_is_active_booking_temporal_clue_followup_contract(
        contract,
        normalized_memory_profile,
        current_message=current_message,
    ):
        return "llm_policy_core_error:active_booking_temporal_clue_followup_reclassification_required"

    if contract.action == "fact" and contract.tool_action_hint == "catalog.location":
        location_pack_refs = _policy_core_catalog_location_pack_refs(contract)
        if not location_pack_refs:
            return "llm_policy_core_error:catalog_location_pack_refs_missing"
        if contract.intent == "hours" and "hours" not in location_pack_refs:
            return "llm_policy_core_error:catalog_location_pack_refs_invalid"
        if contract.capability == "hours" and "hours" not in location_pack_refs:
            return "llm_policy_core_error:catalog_location_pack_refs_invalid"

    if contract.action == "fact" and contract.tool_action_hint == "catalog.service_query":
        expected_service_pack_ref = _policy_core_expected_catalog_service_pack_ref(contract)
        service_pack_refs = _policy_core_catalog_service_pack_refs(contract)
        expected_service_multifact_pack_refs = _policy_core_current_message_service_multifact_pack_refs(
            current_message,
            client_slug=client_slug,
        )
        expected_promotions_location_pack_refs = _policy_core_current_message_promotions_location_pack_refs(
            current_message
        )
        if (
            expected_service_multifact_pack_refs
            and service_pack_refs == expected_service_multifact_pack_refs
        ):
            expected_service_pack_ref = None
        if (
            expected_promotions_location_pack_refs
            and service_pack_refs == expected_promotions_location_pack_refs
        ):
            expected_service_pack_ref = None
        if expected_service_pack_ref and service_pack_refs != [expected_service_pack_ref]:
            return "llm_policy_core_error:catalog_service_query_pack_refs_invalid"

    if (
        contract.action == "fact"
        and contract.tool_action_hint in {"catalog.location", "catalog.service_query", "catalog.portfolio"}
    ):
        has_followup_contract = any(
            (
                contract.expected_reply_type,
                contract.next_question,
                list(contract.open_questions or []),
                contract.pending_question_act,
                contract.pending_question_target,
                contract.active_question_relation,
            )
        )
        carried_followup_contract = (
            _policy_core_is_active_followup_info_interrupt(contract)
            and isinstance(carry_reply_type, str)
            and carry_reply_type.strip()
            and isinstance(carry_next_question, str)
            and carry_next_question.strip()
        )
        promotions_booking_followup_contract = _policy_core_is_canonical_promotions_booking_fact_followup_contract(
            contract,
            normalized_memory_profile,
            current_message=current_message,
            context_payload=context_payload,
            client_slug=client_slug,
        )
        if (
            has_followup_contract
            and not carried_followup_contract
            and not promotions_booking_followup_contract
            and not _policy_core_is_canonical_promotions_location_booking_followup_contract(
                contract,
                normalized_memory_profile,
                current_message=current_message,
                context_payload=context_payload,
                client_slug=client_slug,
            )
            and not _policy_core_is_canonical_promotions_grounded_service_booking_followup_contract(
                contract,
                normalized_memory_profile,
                current_message=current_message,
                context_payload=context_payload,
                client_slug=client_slug,
            )
        ):
            return "llm_policy_core_error:standalone_fact_followup_contract_invalid"

    if (
        service_hint
        and not grounded_service
        and _policy_core_is_service_scoped_owner_query(contract)
    ):
        if contract.action == "collect":
            return "llm_policy_core_error:service_scoped_query_collect_invalid"
        if contract.action == "fact":
            return "llm_policy_core_error:service_scoped_query_grounding_missing"

    return None


def _build_policy_core_contract_repair_instruction(
    *,
    schema_error: str,
    normalized_memory_profile: Mapping[str, Any] | None,
    contract: LlmPolicyCoreOutput | None = None,
    current_message: str | None = None,
    context_payload: Mapping[str, Any] | None = None,
    client_slug: str | None = None,
) -> str | None:
    if not isinstance(schema_error, str) or not schema_error.strip():
        return None

    token = schema_error.removeprefix("llm_policy_core_error:")
    pending_contract = _policy_core_active_pending_contract(normalized_memory_profile)
    resume_contract = _policy_core_resume_pending_contract(normalized_memory_profile)
    carry_contract = resume_contract or pending_contract
    carry_reply_type = carry_contract.get("expected_reply_type")
    carry_next_question = carry_contract.get("next_question")
    service_hint = _policy_core_context_service_hint(
        current_message,
        context_payload,
        client_slug=client_slug,
    ) or (
        _policy_core_memory_grounded_service(normalized_memory_profile)
    )
    location_scope_parts: list[str] = []
    if contract is not None and contract.tool_action_hint == "catalog.location":
        location_scope_parts = [
            "For `catalog.location`, `pack_refs` must encode the exact requested location-family scope.",
            'Use `pack_refs=["parking"]` for parking-only questions, `pack_refs=["hours"]` for working-hours-only questions, and `pack_refs=["location"]` for address/location-only questions.',
            "Combine refs only when the user explicitly asked multiple location-family sections in the same turn.",
        ]

    if token.startswith("booking_manage_reference_"):
        direct_lookup_context = (
            isinstance(contract, LlmPolicyCoreOutput)
            and _policy_core_existing_booking_lookup_context(
                contract,
                normalized_memory_profile,
            )
        )
        has_customer = _policy_core_memory_slot_value(normalized_memory_profile, "name") is not None
        if (
            not has_customer
            and isinstance(pending_contract, dict)
            and pending_contract.get("expected_reply_type") == "time"
            and _policy_core_memory_booking_manage_reference_context(
                normalized_memory_profile
            )
        ):
            has_customer = True
        expected_reply_type = "time" if has_customer else "name"
        expected_next_question = "datetime" if has_customer else "name"
        if direct_lookup_context:
            return (
                "The previous JSON violated the governed booking-manage reference contract. "
                "When existing booking context already carries customer + datetime for "
                "a `calendar.get_booking` lookup, keep `action=\"fact\"` and "
                '`tool_action_hint="calendar.get_booking"`. '
                "Use `expected_reply_type=null`, `next_question=null`, "
                "`open_questions=[]`, and omit `pending_question_act`, "
                "`pending_question_target`, and `active_question_relation`. "
                "Return corrected JSON only."
            )
        return (
            "The previous JSON violated the governed booking-manage reference contract. "
            "For existing booking lookup without `referents.booking_ref`, keep "
            '`action="fact"` and `tool_action_hint="calendar.get_booking"`. '
            f"Use `expected_reply_type=\"{expected_reply_type}\"`, "
            f"`next_question=\"{expected_next_question}\"`, "
            f"`open_questions=[\"{expected_next_question}\"]`. "
            "If the missing follow-up is `name`, omit "
            "`pending_question_act`, `pending_question_target`, and "
            "`active_question_relation`. Return corrected JSON only."
        )

    if token == "booking_manage_grounded_ref_cancel_requires_direct_commit":
        return (
            "The previous JSON attempted to cancel an existing booking on a "
            "hypothetical/question-form turn. With grounded `referents.booking_ref`, "
            "do NOT execute `calendar.cancel` for messages like "
            '`"А если я захочу отменить запись?"` or `"Как отменить эту запись?"`. '
            'Keep `intent="check_booking"`, `action="fact"`, '
            '`tool_action_hint="calendar.get_booking"`, `subject_kind="booking"`, '
            '`capability="booking_manage"`, and `resolution_mode="direct"`. '
            "Preserve grounded `referents.booking_ref` and leave "
            "`expected_reply_type=null`, `next_question=null`, `open_questions=[]`. "
            "Omit `pending_question_act`, `pending_question_target`, and "
            "`active_question_relation`. Return corrected JSON only."
        )

    if token == "booking_manage_name_fill_followup_invalid":
        grounded_service = (
            _policy_core_contract_grounded_service(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or service_hint
        customer_name = (
            contract.slots.get("name")
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or _policy_core_memory_slot_value(normalized_memory_profile, "name")
        parts: list[str] = [
            "The previous JSON broke the governed booking-manage name-fill follow-up contract.",
            "Once the customer name is already grounded for an existing-booking lookup without `referents.booking_ref`, the turn must stay on the booking-manage fact path.",
            'Return `intent="check_booking"`, `action="fact"`, `tool_action_hint="calendar.get_booking"`, `subject_kind="booking"`, and `capability="booking_manage"`.',
            'Use `expected_reply_type="time"`, `next_question="datetime"`, and `open_questions=["datetime"]`.',
            "Do NOT switch to booking `collect` and do NOT put natural-language prompt text into `next_question`.",
            "Omit `pending_question_act`, `pending_question_target`, and `active_question_relation` for this reference follow-up.",
        ]
        if isinstance(customer_name, str) and customer_name.strip():
            parts.append(
                f'Preserve the grounded customer name through `slots.name="{customer_name.strip()}"`.'
            )
        if isinstance(grounded_service, str) and grounded_service:
            parts.append(
                f'Preserve the grounded service through `slots.service="{grounded_service}"` or `referents.service.value="{grounded_service}"`.'
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token == "booking_commit_action_invalid":
        return (
            "The previous JSON violated the governed booking-commit contract. "
            "When service, datetime, and customer name are already grounded and the turn is ready "
            "to create the booking, return `action=\"fact\"` and "
            '`tool_action_hint="calendar.book_slot"`. '
            "Do not keep the turn on `action=\"collect\"` once booking inputs are complete. "
            "Preserve the grounded service/datetime/name slots and return corrected JSON only."
        )

    if token in {
        "service_scoped_query_collect_invalid",
        "service_scoped_query_grounding_missing",
    }:
        grounded_service = service_hint or "service_from_current_turn"
        intent = contract.intent if isinstance(contract, LlmPolicyCoreOutput) else "duration"
        capability = (
            contract.capability
            if isinstance(contract, LlmPolicyCoreOutput) and isinstance(contract.capability, str)
            else intent
        )
        resolution_mode = (
            contract.resolution_mode
            if isinstance(contract, LlmPolicyCoreOutput) and isinstance(contract.resolution_mode, str)
            else "policy_fact"
        )
        pack_ref_clause = ""
        if intent == "master_query":
            pack_ref_clause = ', `pack_refs=["master"]`'
        continuity_parts: list[str] = []
        if isinstance(carry_reply_type, str) and carry_reply_type.strip():
            continuity_parts.append(f'`expected_reply_type="{carry_reply_type}"`')
        if isinstance(carry_next_question, str) and carry_next_question.strip():
            continuity_parts.append(f'`next_question="{carry_next_question}"`')
            continuity_parts.append(
                f'`open_questions={json.dumps(_policy_core_expected_open_questions(carry_contract), ensure_ascii=False)}`'
            )
        pending_act = carry_contract.get("pending_question_act")
        if isinstance(pending_act, str) and pending_act.strip():
            continuity_parts.append(f'`pending_question_act="{pending_act}"`')
        pending_target = carry_contract.get("pending_question_target")
        if isinstance(pending_target, str) and pending_target.strip():
            continuity_parts.append(f'`pending_question_target="{pending_target}"`')
        if continuity_parts:
            continuity_parts.append('`active_question_relation="generic_info_interrupt"`')
        continuity_clause = ""
        if continuity_parts:
            continuity_clause = " Preserve active continuity with " + ", ".join(continuity_parts) + "."
        corrected_resolution_mode = (
            "policy_fact" if resolution_mode == "clarify_missing_subject" else resolution_mode
        )
        return (
            "The previous JSON violated the single semantic-owner service grounding law. "
            f"The owner input already grounds service `{grounded_service}`. "
            "Do not ask the user to choose the service again and do not leave service grounding empty. "
            "Runtime will not infer or recover the service later. "
            f'Return `intent="{intent}"`, `action="fact"`, `tool_action_hint="catalog.service_query"`'
            f"{pack_ref_clause}, "
            f'`subject_kind="service"`, `capability="{capability}"`, '
            f'`resolution_mode="{corrected_resolution_mode}"`, '
            f'and ground the service through `slots.service="{grounded_service}"` '
            f'or `referents.service.value="{grounded_service}"`.{continuity_clause} '
            'Forbidden: `action="collect"`, `next_question="service"`, `reason="service_missing_for_duration_query"`. '
            "Return corrected JSON only."
        )

    if token.startswith("consult_media_"):
        preserve_parts: list[str] = []
        pending_act = resume_contract.get("pending_question_act")
        if isinstance(pending_act, str) and pending_act.strip():
            preserve_parts.append(f'Keep `pending_question_act="{pending_act}"`.')
        pending_target = resume_contract.get("pending_question_target")
        if isinstance(pending_target, str) and pending_target.strip():
            preserve_parts.append(f'Keep `pending_question_target="{pending_target}"`.')
        relation = resume_contract.get("active_question_relation")
        if isinstance(relation, str) and relation.strip():
            preserve_parts.append(f'Keep `active_question_relation="{relation}"`.')
        return (
            "The previous JSON violated the governed consult-media follow-up contract. "
            "For the governed photo/style-reference continuation reason family "
            "(`user_offers_photo_reference*` / `user_offers_photos_for_style_reference*`), keep "
            '`intent=\"consult\"`, `action=\"collect\"`, '
            '`tool_action_hint=\"consult\"`, and `capability` inside '
            '`{\"consultation\",\"bookability\"}`. '
            '`pack_refs=[\"style_reference\"]`, `expected_reply_type=\"media\"`, '
            '`next_question=\"media\"`, and `open_questions=[\"media\"]`. '
            + (" ".join(preserve_parts) + " " if preserve_parts else "")
            + "Return corrected JSON only."
        )

    if token.startswith("generic_info_interrupt_"):
        if not isinstance(carry_reply_type, str) or not isinstance(carry_next_question, str):
            return None
        open_questions = _policy_core_expected_open_questions(carry_contract)
        pending_parts: list[str] = [
            "The previous JSON violated the governed active-followup info-interrupt contract.",
            "When a fact-side side question interrupts an active follow-up,",
            "preserve the active resume contract exactly:",
            f'`expected_reply_type="{carry_reply_type}"`,',
            f'`next_question="{carry_next_question}"`,',
            f"`open_questions={json.dumps(open_questions, ensure_ascii=False)}`.",
        ]
        source_ref = "memory.profile.resume_pending_question_contract"
        if not resume_contract:
            source_ref = "memory.profile.pending_question_contract"
        pending_parts.append(f"Use `{source_ref}` as the carryover source of truth.")
        pending_act = carry_contract.get("pending_question_act")
        if isinstance(pending_act, str) and pending_act.strip():
            pending_parts.append(f'Keep `pending_question_act="{pending_act}"`.')
        pending_target = carry_contract.get("pending_question_target")
        if isinstance(pending_target, str) and pending_target.strip():
            pending_parts.append(f'Keep `pending_question_target="{pending_target}"`.')
        pending_parts.extend(location_scope_parts)
        pending_parts.append("Return corrected JSON only.")
        return " ".join(pending_parts)

    if token.startswith("catalog_location_pack_refs_"):
        parts: list[str] = list(location_scope_parts) or [
            "For `catalog.location`, `pack_refs` must encode the exact requested location-family scope.",
            'Use `pack_refs=["parking"]` for parking-only questions, `pack_refs=["hours"]` for working-hours-only questions, and `pack_refs=["location"]` for address/location-only questions.',
            "Combine refs only when the user explicitly asked multiple location-family sections in the same turn.",
        ]
        if isinstance(carry_reply_type, str) and carry_reply_type.strip() and isinstance(carry_next_question, str) and carry_next_question.strip():
            open_questions = _policy_core_expected_open_questions(carry_contract)
            parts.extend(
                [
                    "Preserve the active follow-up contract exactly:",
                    f'`expected_reply_type="{carry_reply_type}"`,',
                    f'`next_question="{carry_next_question}"`,',
                    f"`open_questions={json.dumps(open_questions, ensure_ascii=False)}`.",
                ]
            )
            pending_act = carry_contract.get("pending_question_act")
            if isinstance(pending_act, str) and pending_act.strip():
                parts.append(f'Keep `pending_question_act="{pending_act}"`.')
            pending_target = carry_contract.get("pending_question_target")
            if isinstance(pending_target, str) and pending_target.strip():
                parts.append(f'Keep `pending_question_target="{pending_target}"`.')
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("catalog_service_query_pack_refs_"):
        expected_service_pack_ref = (
            _policy_core_expected_catalog_service_pack_ref(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        )
        parts: list[str] = [
            "For `catalog.service_query`, `pack_refs` must encode only the exact current service fact family.",
            'Use `pack_refs=["pricing"]` for price questions, `pack_refs=["duration"]` for duration questions, `pack_refs=["promotions"]` for promo questions, and `pack_refs=["master"]` for specialist/master questions.',
            "Do not carry previous info refs into the new fact turn unless the current turn explicitly asks multiple service fact families in the same message.",
        ]
        if isinstance(expected_service_pack_ref, str) and expected_service_pack_ref:
            parts.append(f'In this turn, use `pack_refs=["{expected_service_pack_ref}"]` exactly.')
        if isinstance(carry_reply_type, str) and carry_reply_type.strip() and isinstance(carry_next_question, str) and carry_next_question.strip():
            open_questions = _policy_core_expected_open_questions(carry_contract)
            parts.extend(
                [
                    "Preserve the active follow-up contract exactly:",
                    f'`expected_reply_type="{carry_reply_type}"`,',
                    f'`next_question="{carry_next_question}"`,',
                    f"`open_questions={json.dumps(open_questions, ensure_ascii=False)}`.",
                ]
            )
            pending_act = carry_contract.get("pending_question_act")
            if isinstance(pending_act, str) and pending_act.strip():
                parts.append(f'Keep `pending_question_act="{pending_act}"`.')
            pending_target = carry_contract.get("pending_question_target")
            if isinstance(pending_target, str) and pending_target.strip():
                parts.append(f'Keep `pending_question_target="{pending_target}"`.')
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("standalone_fact_followup_contract_"):
        return (
            "Standalone fact turns may not invent a follow-up contract. "
            "If the input profile does not carry an active follow-up contract for this fact turn, "
            "set `expected_reply_type=null`, `next_question=null`, `open_questions=[]`, "
            "`pending_question_act=null`, `pending_question_target=null`, and `active_question_relation=null`. "
            "Only active follow-up info interrupts may preserve a carried contract from `memory.profile.pending_question_contract` or `memory.profile.resume_pending_question_contract`. "
            "Return corrected JSON only."
        )

    if token.startswith("active_followup_interrupt_reclassification_required"):
        if not isinstance(carry_reply_type, str) or not isinstance(carry_next_question, str):
            return None
        open_questions = _policy_core_expected_open_questions(carry_contract)
        parts: list[str] = [
            "The previous JSON incorrectly kept a media/style-reference continuation active.",
            "The owner reason already signals a later side-question (`...query` / `...interrupt`),",
            "so reclassify this turn as the correct interrupt family instead of continuing media.",
            "Do NOT return `expected_reply_type=\"media\"` or `next_question=\"media\"`.",
            "Preserve the active booking resume contract exactly:",
            f'`expected_reply_type="{carry_reply_type}"`,',
            f'`next_question="{carry_next_question}"`,',
            f"`open_questions={json.dumps(open_questions, ensure_ascii=False)}`.",
        ]
        pending_act = carry_contract.get("pending_question_act")
        if isinstance(pending_act, str) and pending_act.strip():
            parts.append(f'Keep `pending_question_act="{pending_act}"`.')
        pending_target = carry_contract.get("pending_question_target")
        if isinstance(pending_target, str) and pending_target.strip():
            parts.append(f'Keep `pending_question_target="{pending_target}"`.')
        parts.extend(
            [
                "If the user is asking which specialist/master performs the service without temporal scope,",
                "emit the generic master/specialist info interrupt instead of consult-media continuation.",
                "Use carried service grounding from memory when available.",
                "Return corrected JSON only.",
            ]
        )
        return " ".join(parts)

    if token.startswith("active_followup_master_query_reclassification_required"):
        if not isinstance(carry_reply_type, str) or not isinstance(carry_next_question, str):
            return None
        open_questions = _policy_core_expected_open_questions(carry_contract)
        parts: list[str] = [
            "The previous JSON incorrectly turned a specialist/master side-question into live availability collection during an active media follow-up.",
            "Do NOT ask for time availability and do NOT use live-calendar resolution for this turn.",
            "Reclassify it as the master/specialist info interrupt instead:",
            '`intent="master_query"`, `action="fact"`, `tool_action_hint="info"`, `pack_refs=["master"]`.',
            "Keep the booking resume contract explicit:",
            f'`expected_reply_type="{carry_reply_type}"`,',
            f'`next_question="{carry_next_question}"`,',
            f"`open_questions={json.dumps(open_questions, ensure_ascii=False)}`.",
            'Set `active_question_relation="generic_info_interrupt"`.',
            "Keep carried service grounding from memory when available.",
        ]
        pending_act = carry_contract.get("pending_question_act")
        if isinstance(pending_act, str) and pending_act.strip():
            parts.append(f'Keep `pending_question_act="{pending_act}"`.')
        pending_target = carry_contract.get("pending_question_target")
        if isinstance(pending_target, str) and pending_target.strip():
            parts.append(f'Keep `pending_question_target="{pending_target}"`.')
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("active_media_time_interrupt_reclassification_required"):
        if not isinstance(carry_reply_type, str) or not isinstance(carry_next_question, str):
            return None
        open_questions = _policy_core_expected_open_questions(carry_contract)
        parts: list[str] = [
            "The previous JSON incorrectly kept the media follow-up active after a later booking time question.",
            "Do NOT keep `expected_reply_type=\"media\"`, `next_question=\"media\"`, or `open_questions=[\"media\"]` for this turn.",
            "Reclassify it back to the active booking collect contract:",
            '`intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, `capability="bookability"`.',
            f'Preserve `expected_reply_type="{carry_reply_type}"`,',
            f'`next_question="{carry_next_question}"`,',
            f"`open_questions={json.dumps(open_questions, ensure_ascii=False)}`.",
        ]
        pending_act = carry_contract.get("pending_question_act")
        if isinstance(pending_act, str) and pending_act.strip():
            parts.append(f'Keep `pending_question_act="{pending_act}"`.')
        pending_target = carry_contract.get("pending_question_target")
        if isinstance(pending_target, str) and pending_target.strip():
            parts.append(f'Keep `pending_question_target="{pending_target}"`.')
        relation = carry_contract.get("active_question_relation")
        if isinstance(relation, str) and relation.strip():
            parts.append(f'Keep `active_question_relation="{relation}"`.')
        parts.extend(
            [
                "Use the resume booking contract from `memory.profile.resume_pending_question_contract` as the source of truth.",
                "Keep grounded service from memory when available.",
                "Return corrected JSON only.",
            ]
        )
        return " ".join(parts)

    if token.startswith("active_booking_live_availability_reclassification_required"):
        if not isinstance(carry_reply_type, str) or not isinstance(carry_next_question, str):
            return None
        open_questions = _policy_core_expected_open_questions(carry_contract)
        parts: list[str] = [
            "The previous JSON incorrectly turned an active booking availability follow-up into `master_query`.",
            "This turn must stay inside the current booking continuity, not specialist/master info ownership.",
            'Return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`.',
            'Keep `subject_kind="booking"`.',
            "If the user mentions a candidate time, you may keep `capability=\"live_availability\"` and `temporal_scope=\"specific_time\"`,",
            "but do NOT switch to `intent=\"master_query\"` and do NOT emit `calendar.list_slots` while the requested booking slot is still incomplete.",
            "Preserve the active booking follow-up contract exactly:",
            f'`expected_reply_type="{carry_reply_type}"`,',
            f'`next_question="{carry_next_question}"`,',
            f"`open_questions={json.dumps(open_questions, ensure_ascii=False)}`.",
        ]
        pending_act = carry_contract.get("pending_question_act")
        if isinstance(pending_act, str) and pending_act.strip():
            parts.append(f'Keep `pending_question_act="{pending_act}"`.')
        pending_target = carry_contract.get("pending_question_target")
        if isinstance(pending_target, str) and pending_target.strip():
            parts.append(f'Keep `pending_question_target="{pending_target}"`.')
        active_relation = carry_contract.get("active_question_relation")
        if isinstance(active_relation, str) and active_relation.strip():
            parts.append(f'Keep `active_question_relation="{active_relation}"`.')
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("active_booking_manage_interrupt_reclassification_required"):
        parts: list[str] = [
            "The previous JSON incorrectly treated a booking-subject interrupt as generic `info` during an active booking time follow-up.",
            "Re-read the current user message and classify it as either existing-booking management or the original booking collect, but do NOT keep `intent=\"other\"`, `tool_action_hint=\"info\"`, or `capability=\"bookability\"` for this interrupt.",
            "If the user explicitly asks to contact a manager or human, return `subject_kind=\"booking\"`, `capability=\"booking_manage\"`, `intent=\"booking\"`, `action=\"handoff\"`, `tool_action_hint=\"handoff\"`, and `needs_manager=true`.",
            "If the user is asking to cancel, reschedule, confirm, check, verify, or otherwise manage an existing booking without `referents.booking_ref`, return `subject_kind=\"booking\"`, `capability=\"booking_manage\"`, `intent=\"check_booking\"` or `intent=\"verify_booking\"`, `action=\"fact\"`, and `tool_action_hint=\"calendar.get_booking\"`.",
            "When `referents.customer` is still missing, preserve the governed lookup follow-up: `expected_reply_type=\"name\"`, `next_question=\"name\"`, `open_questions=[\"name\"]`.",
            "When the customer referent is already grounded but the booking reference is still missing, preserve the governed lookup follow-up: `expected_reply_type=\"time\"`, `next_question=\"datetime\"`, `open_questions=[\"datetime\"]`.",
            "Only if the current message is still about the new booking slot should you keep the active booking collect contract.",
            "Return corrected JSON only.",
        ]
        return " ".join(parts)

    if token.startswith("active_booking_temporal_clue_followup_reclassification_required"):
        if not isinstance(carry_reply_type, str) or not isinstance(carry_next_question, str):
            return None
        open_questions = _policy_core_expected_open_questions(carry_contract)
        temporal_scope_hint = _policy_core_current_message_grounded_temporal_scope_hint(
            current_message
        )
        grounded_specialist = _policy_core_contract_grounded_specialist(
            contract
        ) or _policy_core_memory_grounded_specialist(normalized_memory_profile)
        parts: list[str] = [
            "The previous JSON kept an active booking temporal-clue follow-up on the generic datetime collect path.",
            "The user already supplied a partial candidate slot in the current message, so this turn must stay in booking collect but become a slot-constraint follow-up.",
            'Return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, and `subject_kind="booking"`.',
            'Set `pending_question_act="slot_constraint"`, `pending_question_target="time"`, and `active_question_relation="slot_constraint"`.',
            f'Preserve `expected_reply_type="{carry_reply_type}"`,',
            f'`next_question="{carry_next_question}"`,',
            f"`open_questions={json.dumps(open_questions, ensure_ascii=False)}`.",
            'Copy the user-provided candidate slot into `alternate_datetime` as a short grounded value (for example `пятницу утром`, `завтра вечером`, `после 17:00`).',
            "Do NOT fall back to the generic booking prompt that asks again for both date and time, even if the previous JSON left `temporal_scope` as `none`.",
        ]
        if temporal_scope_hint:
            parts.append(
                f'Set `temporal_scope="{temporal_scope_hint}"`; do NOT leave `temporal_scope="none"` for this turn.'
            )
        else:
            parts.append(
                "Set `temporal_scope` to the grounded non-`none` scope implied by the current message."
            )
        pending_act = carry_contract.get("pending_question_act")
        if isinstance(pending_act, str) and pending_act.strip():
            parts.append(
                f'The carried booking follow-up was `pending_question_act="{pending_act}"`; only tighten it to `slot_constraint` for this temporal clue turn.'
            )
        if grounded_specialist:
            parts.append(
                f'Preserve the carried specialist preference through `referents.specialist.value="{grounded_specialist}"`, but do NOT switch `subject_kind`, `active_question_relation`, or `resolution_mode` back to a specialist follow-up.'
            )
        if isinstance(current_message, str) and current_message.strip():
            parts.append(
                f'Ground `alternate_datetime` from the current message: "{current_message.strip()}".'
            )
            parts.append(
                "Do NOT translate `alternate_datetime` into another language; preserve the user-language surface from the current message."
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("booking_availability_missing_service_reclassification_required"):
        temporal_scope_hint = _policy_core_current_message_grounded_temporal_scope_hint(
            current_message
        )
        parts: list[str] = [
            "The previous JSON treated a booking availability question with a day/date clue as if the service were already grounded.",
            "The current message still lacks a grounded service, so booking must stay incomplete and ask for the missing service instead of tightening into a time follow-up.",
            'Return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, `capability="bookability"`, `subject_kind="general"`, and `resolution_mode="clarify_missing_subject"`.',
            'Set `expected_reply_type="service_choice"`, `next_question="service"`, and `open_questions=["service"]`.',
            "Do NOT emit `slots.service` or `referents.service` unless the service is grounded in the current message or canonical memory.",
            "Clear `pending_question_act`, `pending_question_target`, and `active_question_relation` for this missing-service collect turn.",
            "Preserve the message-grounded day/date clue in semantic constraints instead of dropping it.",
        ]
        if temporal_scope_hint:
            parts.append(
                f'Set `temporal_scope="{temporal_scope_hint}"` so the day clue stays grounded while service is still missing.'
            )
        else:
            parts.append(
                "Keep the grounded non-`none` `temporal_scope` implied by the current message."
            )
        if isinstance(current_message, str) and current_message.strip():
            parts.append(
                f'If you keep `alternate_datetime`, ground it directly from the current message surface: "{current_message.strip()}".'
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("mixed_first_turn_location_service_fact_reclassification_required"):
        grounded_service = (
            _policy_core_contract_grounded_service(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or _policy_core_resolve_message_grounded_service_hint(
            current_message=current_message,
            context_payload=context_payload,
            normalized_memory_profile=normalized_memory_profile,
            client_slug=client_slug,
        )
        expected_pack_refs = _policy_core_current_message_location_service_fact_pack_refs(
            current_message,
            client_slug=client_slug,
        ) or ["location", "pricing"]
        parts: list[str] = [
            "This standalone first turn explicitly asks about location/address and one or more grounded service facts.",
            "Keep the explicit location scope as the head fact family and do not fabricate working-hours intent.",
            'Return `intent="location"` and `action="fact"`.',
            'Use `tool_action_hint="info"` so runtime keeps the mixed fact scope together.',
            f"Set `pack_refs={json.dumps(expected_pack_refs, ensure_ascii=False)}` exactly.",
            '`subject_kind="service"`, `capability="location"`, and `resolution_mode="policy_fact"`.',
            'Clear standalone follow-up fields: `expected_reply_type=null`, `next_question=null`, `open_questions=[]`, `pending_question_act=null`, `pending_question_target=null`, and `active_question_relation=null`.',
            'Do NOT switch this turn to `intent="hours"` and do NOT convert it into booking collect.',
        ]
        if isinstance(grounded_service, str) and grounded_service:
            parts.append(
                f'Preserve the grounded service through `referents.service.value="{grounded_service}"` or `slots.service="{grounded_service}"`.'
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("mixed_first_turn_hours_location_fact_scope_required"):
        expected_pack_refs = _policy_core_current_message_hours_location_fact_pack_refs(
            current_message,
            client_slug=client_slug,
        ) or ["hours", "location"]
        head_ref = (
            contract.intent
            if isinstance(contract, LlmPolicyCoreOutput) and contract.intent in {"hours", "location"}
            else "hours"
        )
        requested_promotions = "promotions" in expected_pack_refs
        scope_line = (
            "This standalone first turn explicitly asks working hours, location/address, and promotions/discounts."
            if requested_promotions
            else "This standalone first turn explicitly asks only working hours and location/address."
        )
        extra_scope_line = (
            "Preserve the explicit promotions ask in the same mixed fact scope; do not collapse this turn to only hours/location or to promotions-only."
            if requested_promotions
            else "Do not add service overview, contact, pricing, duration, or booking scopes unless the user explicitly asked for them."
        )
        parts: list[str] = [
            scope_line,
            extra_scope_line,
            f'Return `intent="{head_ref}"`, `action="fact"`, and `tool_action_hint="info"`.',
            f"Set `pack_refs={json.dumps(expected_pack_refs, ensure_ascii=False)}` exactly.",
            f'Use `subject_kind="general"`, `capability="{head_ref}"`, `resolution_mode="policy_fact"`, and `temporal_scope="none"`.',
            'Set `alternate_datetime=null`.',
            'Clear standalone follow-up fields: `expected_reply_type=null`, `next_question=null`, `open_questions=[]`, `pending_question_act=null`, `pending_question_target=null`, and `active_question_relation=null`.',
            "Return corrected JSON only.",
        ]
        return " ".join(parts)

    if token.startswith("mixed_first_turn_service_fact_booking_side_precedence_required"):
        grounded_service = (
            _policy_core_contract_grounded_service(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or _policy_core_resolve_message_grounded_service_hint(
            current_message=current_message,
            context_payload=context_payload,
            normalized_memory_profile=normalized_memory_profile,
            client_slug=client_slug,
        )
        expected_pack_refs = _policy_core_current_message_service_scoped_fact_pack_refs(
            current_message,
            client_slug=client_slug,
        ) or ["pricing"]
        expected_ref = expected_pack_refs[0]
        parts: list[str] = [
            "This standalone first turn asks for a grounded service fact and only adds booking as a side request.",
            "Keep the service fact as the head intent even if the side request mentions a concrete time/date.",
            f'Return `intent="{expected_ref}"`, `action="fact"`, and `tool_action_hint="catalog.service_query"`.',
            f"Set `pack_refs={json.dumps([expected_ref], ensure_ascii=False)}` exactly.",
            f'Use `capability="{expected_ref}"`, `subject_kind="service"`, and `resolution_mode="policy_fact"`.',
            'Clear standalone follow-up fields: `expected_reply_type=null`, `next_question=null`, `open_questions=[]`, `pending_question_act=null`, `pending_question_target=null`, and `active_question_relation=null`.',
            'Do NOT switch this turn to booking collect or `calendar.book_slot`.',
        ]
        if isinstance(grounded_service, str) and grounded_service:
            parts.append(
                f'Preserve the grounded service through `referents.service.value="{grounded_service}"` or `slots.service="{grounded_service}"`.'
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("service_query_multifact_reclassification_required"):
        grounded_service = (
            _policy_core_contract_grounded_service(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or _policy_core_resolve_message_grounded_service_hint(
            current_message=current_message,
            context_payload=context_payload,
            normalized_memory_profile=normalized_memory_profile,
            client_slug=client_slug,
        )
        expected_pack_refs = _policy_core_current_message_service_multifact_pack_refs(
            current_message,
            client_slug=client_slug,
        ) or list(_SERVICE_QUERY_MULTI_FACT_REFS)
        head_ref = (
            contract.intent
            if isinstance(contract, LlmPolicyCoreOutput) and contract.intent in expected_pack_refs
            else expected_pack_refs[0]
        )
        head_intent = "master_query" if head_ref == "master" else head_ref
        parts: list[str] = [
            "This standalone turn explicitly asks multiple fact families for the grounded service and related business info.",
            f'Return `intent="{head_intent}"`, `action="fact"`, and `tool_action_hint="catalog.service_query"`.',
            f"Set `pack_refs={json.dumps(expected_pack_refs, ensure_ascii=False)}` exactly.",
            f'Use `capability="{head_ref}"`, `subject_kind="service"`, `resolution_mode="policy_fact"`, and `temporal_scope="none"`.',
            'Set `alternate_datetime=null`.',
            'Clear standalone follow-up fields: `expected_reply_type=null`, `next_question=null`, `open_questions=[]`, `pending_question_act=null`, `pending_question_target=null`, and `active_question_relation=null`.',
            "Do NOT collapse this turn to only one service fact family.",
        ]
        if isinstance(grounded_service, str) and grounded_service:
            parts.append(
                f'Preserve the grounded service through `referents.service.value="{grounded_service}"` or `slots.service="{grounded_service}"`.'
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("mixed_first_turn_hours_service_fact_reclassification_required"):
        grounded_service = (
            _policy_core_contract_grounded_service(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or service_hint
        expected_pack_refs = _policy_core_current_message_hours_service_fact_pack_refs(
            current_message,
            client_slug=client_slug,
        ) or ["hours", "services_overview"]
        parts: list[str] = [
            "This standalone first turn asks working hours plus another service fact for a concrete service already named in the current message.",
            "Do not answer only the hours part and do not reopen missing-service collect.",
            'Keep `intent="hours"` and `action="fact"`.',
            'Use `tool_action_hint="info"` so runtime preserves the mixed fact scope instead of a partial single-family answer.',
            f"Set `pack_refs={json.dumps(expected_pack_refs, ensure_ascii=False)}` exactly.",
            '`subject_kind="service"`, `capability="hours"`, and `resolution_mode="policy_fact"`.',
            'Clear standalone follow-up fields: `expected_reply_type=null`, `next_question=null`, `open_questions=[]`, `pending_question_act=null`, `pending_question_target=null`, and `active_question_relation=null`.',
        ]
        if isinstance(grounded_service, str) and grounded_service:
            parts.append(
                f'Preserve the grounded service through `referents.service.value="{grounded_service}"` or `slots.service="{grounded_service}"`.'
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("mixed_first_turn_promotions_precedence_reclassification_required"):
        grounded_service = (
            _policy_core_contract_grounded_service(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        )
        expected_pack_refs = _policy_core_current_message_promotions_location_pack_refs(
            current_message
        ) or ["promotions"]
        parts: list[str] = [
            "This standalone first turn explicitly asks about promotions or discounts and also includes side booking/location asks.",
            "Keep the promotions/discounts question as the head intent instead of answering only the side ask.",
            f'Return `intent="promotions"`, `action="fact"`, `tool_action_hint="catalog.service_query"`, `pack_refs={json.dumps(expected_pack_refs, ensure_ascii=False)}`, `capability="promotions"`, and `resolution_mode="policy_fact"`.',
            "If the current message explicitly asks for address/location, preserve that fact in the same response scope instead of dropping it.",
            'Clear standalone follow-up fields: `expected_reply_type=null`, `next_question=null`, `open_questions=[]`, `pending_question_act=null`, `pending_question_target=null`, and `active_question_relation=null`.',
            "Do NOT switch this turn to `catalog.location`, do NOT convert it into booking collect, and do NOT use `intent=\"out_of_domain\"` or `intent=\"other\"`.",
        ]
        if isinstance(grounded_service, str) and grounded_service:
            parts.append(
                f'Preserve the grounded service through `referents.service.value="{grounded_service}"` or `slots.service="{grounded_service}"`, and keep `subject_kind="service"`.'
            )
        else:
            parts.append(
                'If no concrete service is grounded, keep `subject_kind="general"` and leave `slots.service` / `referents.service` empty.'
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("promotions_booking_followup_reclassification_required"):
        parts: list[str] = [
            "This standalone first turn asks about promotions or discounts and also explicitly asks to book, but the service is still missing.",
            "Keep the promotions fact in this same turn and preserve booking progression instead of dropping booking or switching to collect-only output.",
            'Return `intent="promotions"`, `action="fact"`, `tool_action_hint="catalog.service_query"`, `pack_refs=["promotions"]`, `capability="promotions"`, `goal="booking"`, and `resolution_mode="policy_fact"`.',
            'Set `expected_reply_type="service_choice"`, `next_question="service"`, and `open_questions=["service"]` so runtime asks for the missing service after the promotions fact.',
            'Keep `subject_kind="general"` and leave `slots.service` / `referents.service` empty because no concrete service is grounded yet.',
            'Clear `pending_question_act`, `pending_question_target`, and `active_question_relation` for this standalone fact follow-up.',
            "Do NOT drop the booking ask, do NOT answer with promotions only, and do NOT switch this turn to pure collect.",
            "Return corrected JSON only.",
        ]
        return " ".join(parts)

    if token.startswith("promotions_location_booking_followup_reclassification_required"):
        parts: list[str] = [
            "This standalone first turn asks about promotions or discounts, explicitly asks for address/location, and also asks to book without grounding the service.",
            "Keep the promotions and location facts in the same turn and preserve booking progression instead of dropping the follow-up.",
            'Return `intent="promotions"`, `action="fact"`, `tool_action_hint="catalog.service_query"`, `pack_refs=["promotions","location"]`, `capability="promotions"`, `goal="booking"`, and `resolution_mode="policy_fact"`.',
            'Set `expected_reply_type="service_choice"`, `next_question="service"`, and `open_questions=["service"]` so runtime asks only for the missing service after the promotions + location fact response.',
            'Keep `subject_kind="general"` and leave `slots.service` / `referents.service` empty because no concrete service is grounded yet.',
            'Clear `pending_question_act`, `pending_question_target`, and `active_question_relation` for this standalone fact follow-up.',
            "Do NOT answer with promotions+location only, do NOT switch this family to pure collect, and do NOT drop the booking ask.",
            "Return corrected JSON only.",
        ]
        return " ".join(parts)

    if token.startswith("promotions_grounded_service_booking_followup_reclassification_required"):
        grounded_service = (
            _policy_core_contract_grounded_service(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or _policy_core_resolve_message_grounded_service_hint(
            current_message=current_message,
            context_payload=context_payload,
            normalized_memory_profile=normalized_memory_profile,
            client_slug=client_slug,
        )
        parts: list[str] = [
            "This standalone first turn asks about promotions or discounts, already grounds the service in the current message, and also asks to book.",
            "Do not reopen service-choice collect because the service is already known.",
            'Return `intent="promotions"`, `action="fact"`, `tool_action_hint="catalog.service_query"`, `pack_refs=["promotions"]`, `capability="promotions"`, `goal="booking"`, and `resolution_mode="policy_fact"`.',
            'Set `expected_reply_type="time"`, `next_question="datetime"`, and `open_questions=["datetime"]` so booking continues by asking only for date/time.',
            'Set `pending_question_act="ask_about_requested_slot"`, `pending_question_target="time"`, and `active_question_relation="ask_about_requested_slot"`.',
            'Keep `subject_kind="service"` and preserve the grounded service in `slots.service` or `referents.service`.',
            "Do NOT ask the user to choose the service again and do NOT drop the promotions fact.",
        ]
        if isinstance(grounded_service, str) and grounded_service:
            parts.append(
                f'Use `slots.service="{grounded_service}"` or `referents.service.value="{grounded_service}"`.'
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("start_booking_temporal_clue_reclassification_required"):
        temporal_scope_hint = _policy_core_current_message_grounded_temporal_scope_hint(
            current_message
        )
        parts: list[str] = [
            "The previous JSON kept a first-turn booking request with a grounded day/date clue on the generic datetime collect path.",
            "The current message already narrows the requested slot, so this turn must start booking on the slot-constraint path instead of asking for both date and time again.",
            'Return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, and `subject_kind="booking"`.',
            'Set `expected_reply_type="time"`, `next_question="datetime"`, and `open_questions=["datetime"]`.',
            'Set `pending_question_act="slot_constraint"`, `pending_question_target="time"`, and `active_question_relation="slot_constraint"`.',
            'Copy the message-grounded partial slot into `alternate_datetime` as a short user-surface value (for example `понедельник`, `завтра вечером`, `в пятницу`).',
            "Do NOT fall back to the generic booking prompt that asks again for both date and time.",
        ]
        if temporal_scope_hint:
            parts.append(
                f'Set `temporal_scope="{temporal_scope_hint}"`; do NOT leave `temporal_scope="none"` for this turn.'
            )
        else:
            parts.append(
                "Set `temporal_scope` to the grounded non-`none` scope implied by the current message."
            )
        if isinstance(service_hint, str) and service_hint:
            parts.append(
                f'Preserve the grounded service through `slots.service="{service_hint}"` or `referents.service.value="{service_hint}"`.'
            )
        if isinstance(current_message, str) and current_message.strip():
            parts.append(
                f'Ground `alternate_datetime` from the current message: "{current_message.strip()}".'
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("start_booking_exact_datetime_progression_required"):
        grounded_service = (
            _policy_core_contract_grounded_service(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or service_hint
        exact_datetime = _policy_core_current_message_exact_datetime_surface(current_message)
        parts = [
            "The previous JSON kept a start-booking turn on a non-canonical path even though the current message already supplied a full requested datetime.",
            "Because the service is already grounded, this turn must advance to the next missing booking slot: customer name.",
            "Do not commit calendar.book_slot until customer identity is grounded.",
            'Return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, and `subject_kind="booking"`.',
            'Set `expected_reply_type="name"`, `next_question="name"`, and `open_questions=["name"]`.',
            'Set `pending_question_act="fill_requested_slot"`, `pending_question_target="time"`, and `active_question_relation="fill_requested_slot"`.',
            'Set `temporal_scope="specific_time"` and preserve the exact current-message datetime in `slots.datetime` and `alternate_datetime`.',
            "Do NOT ask for date/time again.",
        ]
        if isinstance(grounded_service, str) and grounded_service:
            parts.append(
                f'Preserve the grounded service through `slots.service="{grounded_service}"` or `referents.service.value="{grounded_service}"`.'
            )
        if isinstance(exact_datetime, str) and exact_datetime:
            parts.append(f'Use `slots.datetime="{exact_datetime}"`.')
            parts.append(f'Use `alternate_datetime="{exact_datetime}"`.')
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("active_booking_requested_slot_availability_resolution_required"):
        if not isinstance(carry_reply_type, str) or not isinstance(carry_next_question, str):
            return None
        open_questions = _policy_core_expected_open_questions(carry_contract)
        parts: list[str] = [
            "The previous JSON misresolved a generic availability question during an active booking time follow-up.",
            "This turn must stay inside the current booking collect owner and keep the requested-slot contract.",
            'Return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, and `subject_kind="booking"`.',
            f'Preserve `expected_reply_type="{carry_reply_type}"`,',
            f'`next_question="{carry_next_question}"`,',
            f"`open_questions={json.dumps(open_questions, ensure_ascii=False)}`.",
            'Set `pending_question_act="ask_about_requested_slot"`, `pending_question_target="time"`, and `active_question_relation="ask_about_requested_slot"`.',
            "Do NOT switch to `intent=\"hours\"` or any location fact tool for this surface.",
            "Do NOT tighten the turn to `slot_constraint` unless the current message itself provides a new grounded candidate slot.",
        ]
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("active_booking_time_fill_progression_required"):
        grounded_service = (
            _policy_core_contract_grounded_service(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or service_hint
        specialist_name = (
            _policy_core_contract_grounded_specialist(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or _policy_core_memory_grounded_specialist(normalized_memory_profile)
        parts: list[str] = [
            "The previous JSON kept an active booking on the datetime follow-up even though the current turn already supplied a concrete clock time.",
            "This turn must advance the booking slot-fill contract instead of asking for date/time again.",
            'Return `intent="booking"`, `action="collect"`, and `tool_action_hint="collect"`.',
            'Set `expected_reply_type="name"`, `next_question="name"`, and `open_questions=["name"]`.',
            'Set `pending_question_act="fill_requested_slot"`, `pending_question_target="time"`, and `active_question_relation="fill_requested_slot"`.',
            "Do NOT keep `pending_question_target=\"specialist\"` or `active_question_relation=\"referent_followup\"` once the requested time is grounded.",
        ]
        if isinstance(grounded_service, str) and grounded_service:
            parts.append(
                f'Preserve the grounded service through `slots.service="{grounded_service}"` or `referents.service.value="{grounded_service}"`.'
            )
        if isinstance(specialist_name, str) and specialist_name:
            parts.append(
                f'Preserve the grounded specialist through `referents.specialist.value="{specialist_name}"`.'
            )
        if isinstance(current_message, str) and current_message.strip():
            parts.append(
                f'Ground the fulfilled time from the current message "{current_message.strip()}" together with the carried date/day context.'
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("active_booking_commit_progression_required"):
        grounded_service = (
            _policy_core_contract_grounded_service(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or service_hint
        specialist_name = (
            _policy_core_contract_grounded_specialist(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or _policy_core_memory_grounded_specialist(normalized_memory_profile)
        customer_name = (
            _policy_core_payload_token(contract.slots.get("name"))
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or (
            _policy_core_contract_customer_entity_name(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or _policy_core_memory_slot_value(normalized_memory_profile, "name")
        parts: list[str] = [
            "The previous JSON kept an active booking time follow-up on collect even though the current turn completed the requested booking slot.",
            "Service, carried date/day context, and customer identity are already grounded, so this turn must advance to booking commit.",
            'Return `intent="booking"`, `action="fact"`, `tool_action_hint="calendar.book_slot"`, `subject_kind="booking"`, `capability="bookability"`, and `resolution_mode="live_calendar"`.',
            'Clear stale collect follow-up fields: `expected_reply_type=null`, `next_question=null`, `open_questions=[]`, `pending_question_act=null`, `pending_question_target=null`, and `active_question_relation=null`.',
            'Do NOT keep `action="collect"` or `tool_action_hint="collect"` once booking inputs are complete.',
        ]
        if isinstance(grounded_service, str) and grounded_service:
            parts.append(
                f'Preserve the grounded service through `slots.service="{grounded_service}"` or `referents.service.value="{grounded_service}"`.'
            )
        if isinstance(customer_name, str) and customer_name:
            parts.append(
                f'Ground the customer canonically through `slots.name="{customer_name}"`.'
            )
        if isinstance(current_message, str) and current_message.strip():
            parts.append(
                f'Ground `slots.datetime` by combining the explicit clock time from "{current_message.strip()}" with the carried date/day context already in memory.'
            )
        if isinstance(specialist_name, str) and specialist_name:
            parts.append(
                f'Preserve the grounded specialist through `referents.specialist.value="{specialist_name}"`.'
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("active_booking_customer_name_carryover_required"):
        if not isinstance(carry_reply_type, str) or not isinstance(carry_next_question, str):
            return None
        open_questions = _policy_core_expected_open_questions(carry_contract)
        grounded_service = (
            _policy_core_contract_grounded_service(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or service_hint
        specialist_name = (
            _policy_core_contract_grounded_specialist(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or _policy_core_memory_grounded_specialist(normalized_memory_profile)
        customer_name = (
            _policy_core_contract_customer_entity_name(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or _policy_core_memory_slot_value(normalized_memory_profile, "name")
        carried_alternate_datetime = _policy_core_memory_alternate_datetime(
            normalized_memory_profile
        )
        carried_temporal_scope = _policy_core_memory_temporal_scope(normalized_memory_profile)
        parts: list[str] = [
            "The previous JSON kept an active booking time follow-up but left the provided customer name only as an auxiliary entity.",
            "When the current turn already grounds the customer's own name, canonicalize it in the booking contract instead of ignoring it.",
            'Return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, and `subject_kind="booking"`.',
            f'Preserve `expected_reply_type="{carry_reply_type}"`,',
            f'`next_question="{carry_next_question}"`,',
            f"`open_questions={json.dumps(open_questions, ensure_ascii=False)}`.",
            "Do NOT switch the turn to booking-manage.",
            "Do NOT keep `subject_kind=\"specialist\"` or `resolution_mode=\"referent_followup\"` just because a specialist preference is already carried in memory.",
            "Do NOT change the active booking time contract just because the customer name arrived out of order.",
        ]
        pending_act = carry_contract.get("pending_question_act")
        if isinstance(pending_act, str) and pending_act.strip():
            parts.append(f'Keep `pending_question_act="{pending_act}"`.')
        pending_target = carry_contract.get("pending_question_target")
        if isinstance(pending_target, str) and pending_target.strip():
            parts.append(f'Keep `pending_question_target="{pending_target}"`.')
        active_relation = carry_contract.get("active_question_relation")
        if isinstance(active_relation, str) and active_relation.strip():
            parts.append(f'Keep `active_question_relation="{active_relation}"`.')
        if isinstance(customer_name, str) and customer_name:
            parts.append(
                f'Ground the customer name through `slots.name="{customer_name}"`.'
            )
        elif _policy_core_current_message_has_explicit_customer_name_intro(current_message):
            parts.append(
                "Ground the customer's own name from the current message through `slots.name`."
            )
        if isinstance(carried_temporal_scope, str) and carried_temporal_scope:
            parts.append(
                f'Keep carried `temporal_scope="{carried_temporal_scope}"`.'
            )
        if isinstance(carried_alternate_datetime, str) and carried_alternate_datetime:
            parts.append(
                f'Keep carried `alternate_datetime="{carried_alternate_datetime}"`.'
            )
            parts.append(
                "Do NOT rewrite `alternate_datetime` from the current self-intro text when this turn only adds customer identity."
            )
        if isinstance(grounded_service, str) and grounded_service:
            parts.append(
                f'Preserve the grounded service through `slots.service="{grounded_service}"` or `referents.service.value="{grounded_service}"`.'
            )
        if isinstance(specialist_name, str) and specialist_name:
            parts.append(
                f'Preserve the grounded specialist through `referents.specialist.value="{specialist_name}"`.'
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("active_booking_specialist_followup_reclassification_required"):
        if not isinstance(carry_reply_type, str) or not isinstance(carry_next_question, str):
            return None
        open_questions = _policy_core_expected_open_questions(carry_contract)
        specialist_name = (
            _policy_core_contract_grounded_specialist(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or _policy_core_memory_grounded_specialist(normalized_memory_profile)
        grounded_service = (
            _policy_core_contract_grounded_service(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or service_hint
        parts: list[str] = [
            "The previous JSON kept a named specialist preference on the generic booking time-collect path.",
            "This turn must stay inside booking continuity, but its semantic axes must become a specialist referent follow-up.",
            'Return `intent="booking"`, `action="collect"`, `tool_action_hint="collect"`, `subject_kind="specialist"`, `capability="bookability"`, and `resolution_mode="referent_followup"`.',
            f'Preserve `expected_reply_type="{carry_reply_type}"`,',
            f'`next_question="{carry_next_question}"`,',
            f"`open_questions={json.dumps(open_questions, ensure_ascii=False)}`.",
            'Set `pending_question_target="specialist"` and `active_question_relation="referent_followup"`.',
            "Do not keep generic `subject_kind=\"service\"` or `active_question_relation=\"ask_about_requested_slot\"` once the specialist referent is grounded.",
            "Omit `pending_question_act` or keep it null for this referent follow-up turn.",
        ]
        if isinstance(grounded_service, str) and grounded_service:
            parts.append(
                f'Keep grounded service through `slots.service="{grounded_service}"` or `referents.service.value="{grounded_service}"`.'
            )
        if isinstance(specialist_name, str) and specialist_name:
            parts.append(
                f'Ground the specialist through `referents.specialist.value="{specialist_name}"`.'
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    if token.startswith("active_booking_generic_specialist_query_reclassification_required"):
        if not isinstance(carry_reply_type, str) or not isinstance(carry_next_question, str):
            return None
        open_questions = _policy_core_expected_open_questions(carry_contract)
        grounded_service = (
            _policy_core_contract_grounded_service(contract)
            if isinstance(contract, LlmPolicyCoreOutput)
            else None
        ) or service_hint
        parts: list[str] = [
            "The previous JSON incorrectly kept a generic specialist/master side-question under booking collect.",
            "Do NOT ask for datetime directly on this turn and do NOT keep `intent=\"booking\"` with `action=\"collect\"`.",
            "Reclassify it as the generic master/specialist info interrupt instead:",
            '`intent="master_query"`, `action="fact"`, `tool_action_hint="info"`, `pack_refs=["master"]`.',
            '`subject_kind="service"`, `capability="portfolio"`, `resolution_mode="policy_fact"`.',
            "Preserve the active booking resume contract exactly:",
            f'`expected_reply_type="{carry_reply_type}"`,',
            f'`next_question="{carry_next_question}"`,',
            f"`open_questions={json.dumps(open_questions, ensure_ascii=False)}`.",
            'Set `active_question_relation="generic_info_interrupt"`.',
        ]
        pending_act = carry_contract.get("pending_question_act")
        if isinstance(pending_act, str) and pending_act.strip():
            parts.append(f'Keep `pending_question_act="{pending_act}"`.')
        pending_target = carry_contract.get("pending_question_target")
        if isinstance(pending_target, str) and pending_target.strip():
            parts.append(f'Keep `pending_question_target="{pending_target}"`.')
        if isinstance(grounded_service, str) and grounded_service:
            parts.append(
                f'Keep grounded service through `slots.service="{grounded_service}"` or `referents.service.value="{grounded_service}"`.'
            )
        parts.append("Return corrected JSON only.")
        return " ".join(parts)

    return None


def _parse_policy_core_content(content: str) -> dict[str, Any] | None:
    payload = None
    try:
        payload = json.loads(content)
    except Exception:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                payload = json.loads(match.group(0))
            except Exception:
                payload = None
    return payload if isinstance(payload, dict) else None


def _resolve_specialist_hint_timeout_seconds(timing_context: dict | None) -> float:
    remaining_ms = _remaining_pipeline_budget_ms(timing_context)
    if remaining_ms is None:
        return SPECIALIST_HINT_TIMEOUT_SECONDS
    available_ms = max(0.0, remaining_ms - SPECIALIST_HINT_BUDGET_GUARD_MS)
    if available_ms <= 0:
        return 0.0
    return min(SPECIALIST_HINT_TIMEOUT_SECONDS, available_ms / 1000.0)


def _build_specialist_hint_response_format() -> dict[str, Any]:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["specialist_name", "confidence", "reason", "language"],
        "properties": {
            "specialist_name": {
                "anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]
            },
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "reason": {"type": "string"},
            "language": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        },
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "specialist_hint_output",
            "strict": True,
            "schema": schema,
        },
    }


def _resolve_customer_name_hint_timeout_seconds(timing_context: dict | None) -> float:
    remaining_ms = _remaining_pipeline_budget_ms(timing_context)
    if remaining_ms is None:
        return CUSTOMER_NAME_HINT_TIMEOUT_SECONDS
    available_ms = max(0.0, remaining_ms - CUSTOMER_NAME_HINT_BUDGET_GUARD_MS)
    if available_ms <= 0:
        return 0.0
    return min(CUSTOMER_NAME_HINT_TIMEOUT_SECONDS, available_ms / 1000.0)


def _build_customer_name_hint_response_format() -> dict[str, Any]:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["customer_name", "confidence", "reason", "language"],
        "properties": {
            "customer_name": {"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "reason": {"type": "string"},
            "language": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        },
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "customer_name_hint_output",
            "strict": True,
            "schema": schema,
        },
    }


def _resolve_service_query_hint_timeout_seconds(timing_context: dict | None) -> float:
    remaining_ms = _remaining_pipeline_budget_ms(timing_context)
    if remaining_ms is None:
        return SERVICE_QUERY_HINT_TIMEOUT_SECONDS
    available_ms = max(0.0, remaining_ms - SERVICE_QUERY_HINT_BUDGET_GUARD_MS)
    if available_ms <= 0:
        return 0.0
    return min(SERVICE_QUERY_HINT_TIMEOUT_SECONDS, available_ms / 1000.0)


def _build_service_query_hint_response_format() -> dict[str, Any]:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["service_query", "confidence", "reason", "language"],
        "properties": {
            "service_query": {
                "anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]
            },
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "reason": {"type": "string"},
            "language": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        },
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "service_query_hint_output",
            "strict": True,
            "schema": schema,
        },
    }


def extract_specialist_hint_llm(
    message: str,
    *,
    client_slug: str | None = None,
    timing_context: dict | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "specialist_name": None,
        "confidence": 0.0,
        "reason": "",
        "language": None,
        "error": None,
        "raw": None,
        "attempted": False,
        "elapsed_ms": 0.0,
    }
    if not isinstance(message, str) or not message.strip():
        result["error"] = "empty_message"
        return result

    timeout_seconds = _resolve_specialist_hint_timeout_seconds(timing_context)
    if timeout_seconds < SPECIALIST_HINT_MIN_TIMEOUT_SECONDS:
        result["error"] = "deadline_exceeded"
        return result

    prompt = (
        "Extract specialist (master) name from user text in any language (kk/ru/en/mixed). "
        "Return specialist_name only if explicitly requested. If uncertain, return null. "
        "Never infer a name from service words or time/date."
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": message},
    ]

    try:
        llm = get_llm_provider()
    except RuntimeError as exc:
        if "OPENAI_API_KEY missing" in str(exc):
            result["error"] = "no_api_key"
            return result
        result["error"] = _classify_llm_error(exc)
        return result

    result["attempted"] = True
    response_format = _build_specialist_hint_response_format()
    llm_start = time.monotonic()
    error = None
    response = None
    structured_output_fallback_used = False
    try:
        response = llm.generate(
            messages=messages,
            max_tokens=SPECIALIST_HINT_MAX_TOKENS,
            model=SPECIALIST_HINT_MODEL,
            timeout_seconds=timeout_seconds,
            temperature=0.0,
            response_format=response_format,
        )
    except httpx.TimeoutException:
        error = "timeout"
    except Exception as exc:
        classified_error = _classify_llm_error(exc)
        if (
            classified_error == "invalid_request"
            and _policy_core_uses_response_format(exc)
        ):
            try:
                response = llm.generate(
                    messages=messages,
                    max_tokens=SPECIALIST_HINT_MAX_TOKENS,
                    model=SPECIALIST_HINT_MODEL,
                    timeout_seconds=timeout_seconds,
                    temperature=0.0,
                )
                structured_output_fallback_used = True
            except httpx.TimeoutException:
                error = "timeout"
            except Exception as plain_exc:
                error = _classify_llm_error(plain_exc)
        else:
            error = classified_error

    elapsed_ms = round((time.monotonic() - llm_start) * 1000, 2)
    result["elapsed_ms"] = elapsed_ms
    _log_timing(
        "specialist_hint_llm_ms",
        elapsed_ms,
        timing_context=timing_context,
        extra={
            "model_name": SPECIALIST_HINT_MODEL,
            "model_tier": "fast",
            "timeout": error == "timeout",
            "timeout_seconds": timeout_seconds,
            "max_tokens": SPECIALIST_HINT_MAX_TOKENS,
            "structured_output_fallback_used": structured_output_fallback_used,
        },
    )
    record_llm_time(client_slug, "specialist_hint_llm_ms", elapsed_ms)

    if error:
        result["error"] = error
        return result

    content = (response.content or "").strip() if response else ""
    result["raw"] = content
    if not content:
        result["error"] = "empty_response"
        logger.warning(
            "LLM policy core returned empty response",
            extra={"context": {"model_name": SPECIALIST_HINT_MODEL, "elapsed_ms": elapsed_ms}},
        )
        return result

    payload = None
    try:
        payload = json.loads(content)
    except Exception:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                payload = json.loads(match.group(0))
            except Exception:
                payload = None
    if not isinstance(payload, dict):
        result["error"] = "invalid_json"
        return result

    raw_name = payload.get("specialist_name")
    specialist_name = None
    if isinstance(raw_name, str):
        candidate = re.sub(r"\s+", " ", raw_name).strip(" \t\n\r,.;:!?\"'()[]{}")
        if candidate:
            specialist_name = candidate
    raw_confidence = payload.get("confidence")
    confidence = 0.0
    if isinstance(raw_confidence, (int, float)):
        confidence = max(0.0, min(float(raw_confidence), 1.0))
    reason = payload.get("reason")
    if not isinstance(reason, str):
        reason = ""
    language = payload.get("language")
    if not isinstance(language, str):
        language = None
    elif language.strip():
        language = language.strip().lower()
    else:
        language = None

    result["confidence"] = confidence
    result["reason"] = reason
    result["language"] = language
    if specialist_name and confidence >= SPECIALIST_HINT_CONFIDENCE_THRESHOLD:
        result["ok"] = True
        result["specialist_name"] = specialist_name
        return result

    result["error"] = "low_confidence_or_empty"
    return result


def extract_customer_name_hint_llm(
    message: str,
    *,
    client_slug: str | None = None,
    timing_context: dict | None = None,
    specialist_name: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "customer_name": None,
        "confidence": 0.0,
        "reason": "",
        "language": None,
        "error": None,
        "raw": None,
        "attempted": False,
        "elapsed_ms": 0.0,
    }
    if not isinstance(message, str) or not message.strip():
        result["error"] = "empty_message"
        return result

    timeout_seconds = _resolve_customer_name_hint_timeout_seconds(timing_context)
    if timeout_seconds < CUSTOMER_NAME_HINT_MIN_TIMEOUT_SECONDS:
        result["error"] = "deadline_exceeded"
        return result

    specialist_clause = ""
    if isinstance(specialist_name, str) and specialist_name.strip():
        specialist_clause = f" Known specialist name: {specialist_name.strip()}."
    prompt = (
        "Extract customer's own name from user text in any language (kk/ru/en/mixed). "
        "Return customer_name only if user explicitly provides own name "
        "(e.g. 'меня зовут', 'имя', 'my name is'). "
        "Do not return specialist/master name or inferred names."
        f"{specialist_clause}"
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": message},
    ]

    try:
        llm = get_llm_provider()
    except RuntimeError as exc:
        if "OPENAI_API_KEY missing" in str(exc):
            result["error"] = "no_api_key"
            return result
        result["error"] = _classify_llm_error(exc)
        return result

    result["attempted"] = True
    response_format = _build_customer_name_hint_response_format()
    llm_start = time.monotonic()
    error = None
    response = None
    structured_output_fallback_used = False
    try:
        response = llm.generate(
            messages=messages,
            max_tokens=CUSTOMER_NAME_HINT_MAX_TOKENS,
            model=CUSTOMER_NAME_HINT_MODEL,
            timeout_seconds=timeout_seconds,
            temperature=0.0,
            response_format=response_format,
        )
    except httpx.TimeoutException:
        error = "timeout"
    except Exception as exc:
        classified_error = _classify_llm_error(exc)
        if classified_error == "invalid_request" and _policy_core_uses_response_format(exc):
            try:
                response = llm.generate(
                    messages=messages,
                    max_tokens=CUSTOMER_NAME_HINT_MAX_TOKENS,
                    model=CUSTOMER_NAME_HINT_MODEL,
                    timeout_seconds=timeout_seconds,
                    temperature=0.0,
                )
                structured_output_fallback_used = True
            except httpx.TimeoutException:
                error = "timeout"
            except Exception as plain_exc:
                error = _classify_llm_error(plain_exc)
        else:
            error = classified_error

    elapsed_ms = round((time.monotonic() - llm_start) * 1000, 2)
    result["elapsed_ms"] = elapsed_ms
    _log_timing(
        "customer_name_hint_llm_ms",
        elapsed_ms,
        timing_context=timing_context,
        extra={
            "model_name": CUSTOMER_NAME_HINT_MODEL,
            "model_tier": "fast",
            "timeout": error == "timeout",
            "timeout_seconds": timeout_seconds,
            "max_tokens": CUSTOMER_NAME_HINT_MAX_TOKENS,
            "structured_output_fallback_used": structured_output_fallback_used,
        },
    )
    record_llm_time(client_slug, "customer_name_hint_llm_ms", elapsed_ms)

    if error:
        result["error"] = error
        return result

    content = (response.content or "").strip() if response else ""
    result["raw"] = content
    if not content:
        result["error"] = "empty_response"
        return result

    payload = None
    try:
        payload = json.loads(content)
    except Exception:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                payload = json.loads(match.group(0))
            except Exception:
                payload = None
    if not isinstance(payload, dict):
        result["error"] = "invalid_json"
        return result

    raw_name = payload.get("customer_name")
    customer_name = None
    if isinstance(raw_name, str):
        candidate = re.sub(r"\s+", " ", raw_name).strip(" \t\n\r,.;:!?\"'()[]{}")
        if candidate:
            customer_name = candidate
    raw_confidence = payload.get("confidence")
    confidence = 0.0
    if isinstance(raw_confidence, (int, float)):
        confidence = max(0.0, min(float(raw_confidence), 1.0))
    reason = payload.get("reason")
    if not isinstance(reason, str):
        reason = ""
    language = payload.get("language")
    if not isinstance(language, str):
        language = None
    elif language.strip():
        language = language.strip().lower()
    else:
        language = None

    result["confidence"] = confidence
    result["reason"] = reason
    result["language"] = language
    if isinstance(customer_name, str) and customer_name.strip():
        if isinstance(specialist_name, str) and specialist_name.strip():
            if normalize_for_matching(customer_name) == normalize_for_matching(specialist_name):
                result["error"] = "matches_specialist"
                return result
    if customer_name and confidence >= CUSTOMER_NAME_HINT_CONFIDENCE_THRESHOLD:
        result["ok"] = True
        result["customer_name"] = customer_name
        return result

    result["error"] = "low_confidence_or_empty"
    return result


def extract_service_query_hint_llm(
    message: str,
    *,
    client_slug: str | None = None,
    timing_context: dict | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "service_query": None,
        "confidence": 0.0,
        "reason": "",
        "language": None,
        "error": None,
        "raw": None,
        "attempted": False,
        "elapsed_ms": 0.0,
    }
    if not isinstance(message, str) or not message.strip():
        result["error"] = "empty_message"
        return result

    timeout_seconds = _resolve_service_query_hint_timeout_seconds(timing_context)
    if timeout_seconds < SERVICE_QUERY_HINT_MIN_TIMEOUT_SECONDS:
        result["error"] = "deadline_exceeded"
        return result

    prompt = (
        "Extract service/procedure name from user text in any language (kk/ru/en/mixed). "
        "Return service_query only if service is explicitly present in user text. "
        "Keep exact user wording, 1-6 words. If uncertain, return null. "
        "Do not infer service from specialist names, date, time, or generic booking verbs."
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": message},
    ]

    try:
        llm = get_llm_provider()
    except RuntimeError as exc:
        if "OPENAI_API_KEY missing" in str(exc):
            result["error"] = "no_api_key"
            return result
        result["error"] = _classify_llm_error(exc)
        return result

    result["attempted"] = True
    response_format = _build_service_query_hint_response_format()
    llm_start = time.monotonic()
    error = None
    response = None
    structured_output_fallback_used = False
    try:
        response = llm.generate(
            messages=messages,
            max_tokens=SERVICE_QUERY_HINT_MAX_TOKENS,
            model=SERVICE_QUERY_HINT_MODEL,
            timeout_seconds=timeout_seconds,
            temperature=0.0,
            response_format=response_format,
        )
    except httpx.TimeoutException:
        error = "timeout"
    except Exception as exc:
        classified_error = _classify_llm_error(exc)
        if (
            classified_error == "invalid_request"
            and _policy_core_uses_response_format(exc)
        ):
            try:
                response = llm.generate(
                    messages=messages,
                    max_tokens=SERVICE_QUERY_HINT_MAX_TOKENS,
                    model=SERVICE_QUERY_HINT_MODEL,
                    timeout_seconds=timeout_seconds,
                    temperature=0.0,
                )
                structured_output_fallback_used = True
            except httpx.TimeoutException:
                error = "timeout"
            except Exception as plain_exc:
                error = _classify_llm_error(plain_exc)
        else:
            error = classified_error

    elapsed_ms = round((time.monotonic() - llm_start) * 1000, 2)
    result["elapsed_ms"] = elapsed_ms
    _log_timing(
        "service_query_hint_llm_ms",
        elapsed_ms,
        timing_context=timing_context,
        extra={
            "model_name": SERVICE_QUERY_HINT_MODEL,
            "model_tier": "fast",
            "timeout": error == "timeout",
            "timeout_seconds": timeout_seconds,
            "max_tokens": SERVICE_QUERY_HINT_MAX_TOKENS,
            "structured_output_fallback_used": structured_output_fallback_used,
        },
    )
    record_llm_time(client_slug, "service_query_hint_llm_ms", elapsed_ms)

    if error:
        result["error"] = error
        return result

    content = (response.content or "").strip() if response else ""
    result["raw"] = content
    if not content:
        result["error"] = "empty_response"
        return result

    payload = None
    try:
        payload = json.loads(content)
    except Exception:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                payload = json.loads(match.group(0))
            except Exception:
                payload = None
    if not isinstance(payload, dict):
        result["error"] = "invalid_json"
        return result

    raw_service = payload.get("service_query")
    service_query = None
    if isinstance(raw_service, str):
        candidate = _clean_controller_service_query(raw_service)
        if isinstance(candidate, str) and candidate.strip():
            service_query = candidate.strip()
    raw_confidence = payload.get("confidence")
    confidence = 0.0
    if isinstance(raw_confidence, (int, float)):
        confidence = max(0.0, min(float(raw_confidence), 1.0))
    reason = payload.get("reason")
    if not isinstance(reason, str):
        reason = ""
    language = payload.get("language")
    if not isinstance(language, str):
        language = None
    elif language.strip():
        language = language.strip().lower()
    else:
        language = None

    result["confidence"] = confidence
    result["reason"] = reason
    result["language"] = language
    if service_query and confidence >= SERVICE_QUERY_HINT_CONFIDENCE_THRESHOLD:
        result["ok"] = True
        result["service_query"] = service_query
        return result

    result["error"] = "low_confidence_or_empty"
    return result


def _normalize_policy_core_memory_summary(summary: str | None) -> str | None:
    if not isinstance(summary, str):
        return None
    compact = " ".join(summary.split())
    if not compact:
        return None
    return compact[:POLICY_CORE_MEMORY_SUMMARY_MAX_CHARS]


def _normalize_policy_core_slot_state(slot_state: dict[str, Any] | None) -> dict[str, str] | None:
    if not isinstance(slot_state, dict):
        return None
    normalized: dict[str, str] = {}
    for field_name in ("service", "datetime", "name", "phone"):
        value = slot_state.get(field_name)
        if not isinstance(value, str):
            continue
        cleaned = " ".join(value.split())
        if cleaned:
            normalized[field_name] = cleaned[:POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS]
    return normalized or None


def _normalize_policy_core_pending_contract_payload(
    payload: dict[str, Any] | None,
    *,
    allowed_next_questions: set[str],
    allowed_expected_reply_types: set[str],
    allowed_pending_question_acts: set[str],
    allowed_pending_question_targets: set[str],
    allowed_active_question_relations: set[str],
) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    cleaned_pending: dict[str, Any] = {}
    next_question = payload.get("next_question") or payload.get("slot")
    if isinstance(next_question, str) and next_question.strip():
        slot_token = next_question.strip().casefold()
        slot_token = {"time": "datetime", "date": "datetime"}.get(slot_token, slot_token)
        if slot_token in allowed_next_questions:
            cleaned_pending["next_question"] = slot_token
    open_questions = payload.get("open_questions")
    if isinstance(open_questions, list):
        cleaned_questions: list[str] = []
        seen_questions: set[str] = set()
        for raw_question in open_questions:
            if len(cleaned_questions) >= POLICY_CORE_MEMORY_PROFILE_MAX_ITEMS:
                break
            if not isinstance(raw_question, str) or not raw_question.strip():
                continue
            question_token = raw_question.strip().casefold()
            question_token = {"time": "datetime", "date": "datetime"}.get(
                question_token,
                question_token,
            )
            if question_token not in allowed_next_questions:
                continue
            if question_token in seen_questions:
                continue
            cleaned_questions.append(question_token)
            seen_questions.add(question_token)
        if cleaned_questions:
            cleaned_pending["open_questions"] = cleaned_questions
    pending_expected_reply_type = payload.get("expected_reply_type")
    if isinstance(pending_expected_reply_type, str) and pending_expected_reply_type.strip():
        expected_token = pending_expected_reply_type.strip().casefold()
        if expected_token in allowed_expected_reply_types:
            cleaned_pending["expected_reply_type"] = expected_token
    reason = payload.get("reason")
    if isinstance(reason, str) and reason.strip():
        cleaned_pending["reason"] = " ".join(reason.split())[
            :POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS
        ]
    pending_question_act = payload.get("pending_question_act")
    if isinstance(pending_question_act, str) and pending_question_act.strip():
        act_token = pending_question_act.strip().casefold()
        if act_token in allowed_pending_question_acts:
            cleaned_pending["pending_question_act"] = act_token
    pending_question_target = payload.get("pending_question_target")
    if isinstance(pending_question_target, str) and pending_question_target.strip():
        target_token = pending_question_target.strip().casefold()
        if target_token in allowed_pending_question_targets:
            cleaned_pending["pending_question_target"] = target_token
    active_question_relation = payload.get("active_question_relation")
    if isinstance(active_question_relation, str) and active_question_relation.strip():
        relation_token = active_question_relation.strip().casefold()
        if relation_token in allowed_active_question_relations:
            cleaned_pending["active_question_relation"] = relation_token
    value = payload.get("value")
    if isinstance(value, str) and value.strip():
        cleaned_pending["value"] = " ".join(value.split())[
            :POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS
        ]
    return cleaned_pending or None


def _normalize_policy_core_memory_profile(profile: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(profile, dict):
        return None
    normalized: dict[str, Any] = {}
    consent_status = profile.get("consent_status")
    if isinstance(consent_status, str) and consent_status.strip():
        normalized["consent_status"] = consent_status.strip().casefold()
    active_goal = profile.get("active_goal")
    if isinstance(active_goal, str) and active_goal.strip():
        normalized["active_goal"] = active_goal.strip().casefold()
    active_slots = profile.get("active_slots")
    if isinstance(active_slots, list):
        cleaned_slots: list[str] = []
        seen_slots: set[str] = set()
        for raw_slot in active_slots:
            if len(cleaned_slots) >= POLICY_CORE_MEMORY_PROFILE_MAX_ITEMS:
                break
            if not isinstance(raw_slot, str):
                continue
            slot = raw_slot.strip().casefold()
            if slot not in {"service", "datetime", "name", "phone"}:
                continue
            if slot in seen_slots:
                continue
            cleaned_slots.append(slot)
            seen_slots.add(slot)
        if cleaned_slots:
            normalized["active_slots"] = cleaned_slots
    slot_state = _normalize_policy_core_slot_state(profile.get("slot_state"))
    if slot_state:
        normalized["slot_state"] = slot_state
    stored_keys = profile.get("stored_keys")
    if isinstance(stored_keys, list):
        cleaned_keys: list[str] = []
        seen_keys: set[str] = set()
        for raw_key in stored_keys:
            if len(cleaned_keys) >= POLICY_CORE_MEMORY_PROFILE_MAX_ITEMS:
                break
            if not isinstance(raw_key, str):
                continue
            key = raw_key.strip()
            if not key or key in seen_keys:
                continue
            cleaned_keys.append(key[:80])
            seen_keys.add(key)
        if cleaned_keys:
            normalized["stored_keys"] = cleaned_keys
    retrieved_items = profile.get("retrieved_items")
    if isinstance(retrieved_items, list):
        cleaned_items: list[dict[str, str]] = []
        seen_items: set[tuple[str, str]] = set()
        for raw_item in retrieved_items:
            if len(cleaned_items) >= POLICY_CORE_MEMORY_PROFILE_MAX_ITEMS:
                break
            if not isinstance(raw_item, dict):
                continue
            raw_key = raw_item.get("key")
            raw_value = raw_item.get("value")
            if not isinstance(raw_key, str) or not isinstance(raw_value, str):
                continue
            key = raw_key.strip()
            value = " ".join(raw_value.split())
            if not key or not value:
                continue
            key = key[:80]
            value = value[:POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS]
            fingerprint = (key, value)
            if fingerprint in seen_items:
                continue
            item_payload = {"key": key, "value": value}
            raw_source = raw_item.get("source")
            if isinstance(raw_source, str) and raw_source.strip():
                item_payload["source"] = raw_source.strip().casefold()[:24]
            cleaned_items.append(item_payload)
            seen_items.add(fingerprint)
        if cleaned_items:
            normalized["retrieved_items"] = cleaned_items
    from app.services.policy_vocabulary_snapshot_service import (
        build_policy_core_vocabulary_snapshot,
        policy_core_semantic_contract_allowlists,
    )

    vocabulary_snapshot = build_policy_core_vocabulary_snapshot()
    allowed_next_questions = set(vocabulary_snapshot.next_questions)
    allowed_expected_reply_types = set(vocabulary_snapshot.expected_reply_types)
    allowed_pending_question_acts = set(vocabulary_snapshot.pending_question_acts)
    allowed_pending_question_targets = set(vocabulary_snapshot.pending_question_targets)
    allowed_active_question_relations = set(vocabulary_snapshot.active_question_relations)

    pending_question_contract = _normalize_policy_core_pending_contract_payload(
        profile.get("pending_question_contract"),
        allowed_next_questions=allowed_next_questions,
        allowed_expected_reply_types=allowed_expected_reply_types,
        allowed_pending_question_acts=allowed_pending_question_acts,
        allowed_pending_question_targets=allowed_pending_question_targets,
        allowed_active_question_relations=allowed_active_question_relations,
    )
    if pending_question_contract:
        normalized["pending_question_contract"] = pending_question_contract
    resume_pending_question_contract = _normalize_policy_core_pending_contract_payload(
        profile.get("resume_pending_question_contract"),
        allowed_next_questions=allowed_next_questions,
        allowed_expected_reply_types=allowed_expected_reply_types,
        allowed_pending_question_acts=allowed_pending_question_acts,
        allowed_pending_question_targets=allowed_pending_question_targets,
        allowed_active_question_relations=allowed_active_question_relations,
    )
    if resume_pending_question_contract:
        normalized["resume_pending_question_contract"] = resume_pending_question_contract
    semantic_contract = profile.get("semantic_contract")
    if isinstance(semantic_contract, dict):
        cleaned_contract: dict[str, Any] = {}
        for field_name, allowed in policy_core_semantic_contract_allowlists().items():
            value = semantic_contract.get(field_name)
            if isinstance(value, str) and value.strip():
                token = value.strip().casefold()
                if token in allowed:
                    cleaned_contract[field_name] = token
        raw_entity_refs = semantic_contract.get("entity_refs")
        if isinstance(raw_entity_refs, list):
            cleaned_entity_refs: list[dict[str, Any]] = []
            for raw_row in raw_entity_refs[:POLICY_CORE_MEMORY_PROFILE_MAX_ITEMS]:
                if not isinstance(raw_row, dict):
                    continue
                row: dict[str, Any] = {}
                for source_key, target_key in (
                    ("entity_id", "entity_id"),
                    ("entity_type", "entity_type"),
                    ("source_ref", "source_ref"),
                    ("value", "value"),
                ):
                    raw_value = raw_row.get(source_key)
                    if isinstance(raw_value, str) and raw_value.strip():
                        row[target_key] = " ".join(raw_value.split())[
                            :POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS
                        ]
                confidence = raw_row.get("confidence")
                if isinstance(confidence, (int, float)):
                    row["confidence"] = max(0.0, min(float(confidence), 1.0))
                if row:
                    cleaned_entity_refs.append(row)
            if cleaned_entity_refs:
                cleaned_contract["entity_refs"] = cleaned_entity_refs
        referents = semantic_contract.get("referents")
        if isinstance(referents, dict):
            cleaned_referents: dict[str, dict[str, Any]] = {}
            for referent_key in ("service", "specialist", "branch", "booking_ref", "customer"):
                raw_payload = referents.get(referent_key)
                if not isinstance(raw_payload, dict):
                    continue
                row: dict[str, Any] = {}
                for source_key, target_key in (
                    ("value", "value"),
                    ("entity_id", "entity_id"),
                    ("entity_type", "entity_type"),
                    ("source_ref", "source_ref"),
                ):
                    raw_value = raw_payload.get(source_key)
                    if isinstance(raw_value, str) and raw_value.strip():
                        row[target_key] = " ".join(raw_value.split())[
                            :POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS
                        ]
                if row:
                    cleaned_referents[referent_key] = row
            if cleaned_referents:
                cleaned_contract["referents"] = cleaned_referents
        grounding_provenance = semantic_contract.get("grounding_provenance")
        if isinstance(grounding_provenance, dict):
            cleaned_grounding: dict[str, Any] = {}
            for field_name in ("pack_id", "entity_id", "source_ref", "resolver_id", "resolver_version"):
                raw_value = grounding_provenance.get(field_name)
                if isinstance(raw_value, str) and raw_value.strip():
                    cleaned_grounding[field_name] = " ".join(raw_value.split())[
                        :POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS
                    ]
            confidence = grounding_provenance.get("confidence")
            if isinstance(confidence, (int, float)):
                cleaned_grounding["confidence"] = max(0.0, min(float(confidence), 1.0))
            if cleaned_grounding:
                cleaned_contract["grounding_provenance"] = cleaned_grounding
        alternate_datetime = semantic_contract.get("alternate_datetime")
        if isinstance(alternate_datetime, str) and alternate_datetime.strip():
            cleaned_contract["alternate_datetime"] = " ".join(alternate_datetime.split())[
                :POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS
            ]
        if cleaned_contract:
            cleaned_contract["contract_version"] = "semantic_contract.v1"
            normalized["semantic_contract"] = cleaned_contract
    consult_state = profile.get("consult_state")
    if isinstance(consult_state, dict):
        cleaned_consult_state: dict[str, Any] = {}
        active = consult_state.get("active")
        if isinstance(active, bool):
            cleaned_consult_state["active"] = active
        topic = consult_state.get("topic")
        if isinstance(topic, str) and topic.strip():
            cleaned_consult_state["topic"] = " ".join(topic.split())[
                :POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS
            ]
        question = consult_state.get("question")
        if isinstance(question, str) and question.strip():
            cleaned_consult_state["question"] = " ".join(question.split())[
                :POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS
            ]
        questions = consult_state.get("questions")
        if isinstance(questions, list):
            cleaned_questions: list[str] = []
            for raw_question in questions:
                if len(cleaned_questions) >= POLICY_CORE_MEMORY_PROFILE_MAX_ITEMS:
                    break
                if not isinstance(raw_question, str):
                    continue
                normalized_question = " ".join(raw_question.split())
                if normalized_question:
                    cleaned_questions.append(
                        normalized_question[:POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS]
                    )
            if cleaned_questions:
                cleaned_consult_state["questions"] = cleaned_questions
        if cleaned_consult_state:
            normalized["consult_state"] = cleaned_consult_state
    return normalized or None


def _trim_policy_core_context_text(
    value: Any,
    *,
    max_chars: int = POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS,
) -> str | None:
    if not isinstance(value, str):
        return None
    compact = " ".join(value.split())
    if not compact:
        return None
    return compact[:max_chars]


def _compact_policy_core_context(context_payload: dict[str, Any]) -> dict[str, Any] | None:
    normalized_context: dict[str, Any] = {}
    for key in ("capability_cards", "policy_cards", "consult_cards"):
        raw_cards = context_payload.get(key)
        if not isinstance(raw_cards, list):
            continue
        compact_cards: list[dict[str, Any]] = []
        for raw_card in raw_cards[:POLICY_CORE_CONTEXT_CARD_LIMIT]:
            if not isinstance(raw_card, dict):
                continue
            compact_card: dict[str, Any] = {}
            for field_name, raw_value in raw_card.items():
                if isinstance(raw_value, str):
                    compact_value = _trim_policy_core_context_text(
                        raw_value,
                        max_chars=POLICY_CORE_COMPACT_MEMORY_SUMMARY_MAX_CHARS,
                    )
                    if compact_value:
                        compact_card[field_name] = compact_value
                elif isinstance(raw_value, bool):
                    compact_card[field_name] = raw_value
                elif isinstance(raw_value, list):
                    compact_items: list[str] = []
                    for raw_item in raw_value[:POLICY_CORE_COMPACT_PROFILE_ITEMS_MAX]:
                        compact_item = _trim_policy_core_context_text(raw_item, max_chars=64)
                        if compact_item and compact_item not in compact_items:
                            compact_items.append(compact_item)
                    if compact_items:
                        compact_card[field_name] = compact_items
            if compact_card:
                compact_cards.append(compact_card)
        if compact_cards:
            normalized_context[key] = compact_cards
    return normalized_context or None


def _build_policy_core_pending_contract_from_expected_reply_type(
    expected_reply_type: str | None,
) -> dict[str, Any] | None:
    if not isinstance(expected_reply_type, str) or not expected_reply_type.strip():
        return None
    expected_token = expected_reply_type.strip().casefold()
    next_question = {
        "service_choice": "service",
        "time": "datetime",
        "name": "name",
        "phone": "phone",
        "media": "media",
    }.get(expected_token)
    if next_question is None:
        return None
    return {
        "expected_reply_type": expected_token,
        "next_question": next_question,
        "open_questions": [next_question],
    }


ANSWER_INTERPRETER_SLOTS = {"service", "datetime", "name"}
ANSWER_INTERPRETER_SLOT_ALIASES = {
    "service": "service",
    "service_choice": "service",
    "service_query": "service",
    "time": "datetime",
    "datetime": "datetime",
    "date": "datetime",
    "name": "name",
}
ANSWER_INTERPRETER_SLOT_BY_REPLY_TYPE = {
    "service_choice": "service",
    "time": "datetime",
    "name": "name",
}
CONTROLLER_ALLOWED_CLASSES = {
    "booking",
    "info_bundle",
    "consult",
    "greeting",
    "out_of_domain",
    "other",
}
CONTROLLER_ALLOWED_INTENTS = {
    "booking",
    "pricing",
    "duration",
    "location",
    "hours",
    "consult",
    "greeting",
    "out_of_domain",
    "other",
}
CONTROLLER_ALLOWED_GOALS = {
    "booking",
    "info",
    "consult",
    "greeting",
    "out_of_domain",
    "other",
}
OFFLINE_CONTROLLER_CLASS = "other"
OFFLINE_CONTROLLER_GOAL = "other"
def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _load_controller_prompt() -> str:
    from app.services.controller_plan_prompt_snapshot_service import (
        load_controller_prompt_snapshot,
    )

    return load_controller_prompt_snapshot().prompt_text


def _load_plan_prompt() -> str:
    from app.services.controller_plan_prompt_snapshot_service import load_plan_prompt_snapshot

    return load_plan_prompt_snapshot().prompt_text


def _load_policy_core_prompt() -> str:
    from app.services.policy_prompt_snapshot_service import load_policy_core_prompt_snapshot

    return load_policy_core_prompt_snapshot().prompt_text


def _load_policy_core_compact_prompt() -> str:
    from app.services.policy_prompt_snapshot_service import load_policy_core_compact_prompt_snapshot

    return load_policy_core_compact_prompt_snapshot().prompt_text


def _clean_controller_class(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().casefold()
    if not cleaned:
        return None
    if cleaned in {"info", "info_bundle"}:
        return "info_bundle"
    if cleaned in CONTROLLER_ALLOWED_CLASSES:
        return cleaned
    return None


def _clean_controller_intents(values: Any) -> list[str]:
    cleaned: list[str] = []
    if not isinstance(values, list):
        return cleaned
    seen = set()
    for item in values:
        if not isinstance(item, str):
            continue
        value = item.strip().casefold()
        if not value or value not in CONTROLLER_ALLOWED_INTENTS or value in seen:
            continue
        cleaned.append(value)
        seen.add(value)
    return cleaned


def _clean_controller_service_query(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = re.sub(r"\s+", " ", value).strip()
    if len(cleaned) < 2:
        return ""
    tokens = cleaned.split()
    if len(tokens) > 6:
        cleaned = " ".join(tokens[:6])
    return cleaned


def _clean_controller_goal(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().casefold()
    if cleaned in CONTROLLER_ALLOWED_GOALS:
        return cleaned
    return None


def _clean_controller_followups(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    followups: list[str] = []
    seen: set[str] = set()
    for item in values:
        if not isinstance(item, str):
            continue
        cleaned = re.sub(r"\s+", " ", item).strip()
        if not cleaned or cleaned in seen:
            continue
        followups.append(cleaned[:120])
        seen.add(cleaned)
    return followups


def _clean_controller_safety_flags(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    flags: list[str] = []
    seen: set[str] = set()
    for item in values:
        if not isinstance(item, str):
            continue
        cleaned = re.sub(r"\s+", " ", item).strip().casefold()
        if not cleaned or cleaned in seen:
            continue
        flags.append(cleaned[:64])
        seen.add(cleaned)
    return flags


def _clean_answer_slot(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().casefold()
    if not cleaned:
        return None
    return ANSWER_INTERPRETER_SLOT_ALIASES.get(cleaned)


def _clean_answer_value(value: Any, *, slot: str) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned:
        return ""
    if slot == "service":
        return _clean_controller_service_query(cleaned)
    if len(cleaned) > 80:
        cleaned = cleaned[:80].strip()
    return cleaned


def _controller_retry_max_tokens(max_tokens: int) -> int:
    if max_tokens <= 1:
        return 1
    fallback = max(20, int(max_tokens * 0.6))
    if fallback >= max_tokens:
        fallback = max(1, max_tokens - 1)
    return fallback


def _build_controller_carryover(carryover: dict | None) -> dict:
    if not isinstance(carryover, dict):
        return {}
    payload: dict[str, Any] = {}
    carryover_class = carryover.get("class")
    if isinstance(carryover_class, str) and carryover_class.strip():
        payload["class"] = carryover_class.strip()
    intents = carryover.get("intents")
    if isinstance(intents, list):
        payload["intents"] = [item for item in intents if isinstance(item, str) and item.strip()]
    info_sections = carryover.get("info_sections")
    if isinstance(info_sections, list):
        payload["info_sections"] = [
            item for item in info_sections if isinstance(item, str) and item.strip()
        ]
    ttl_remaining = carryover.get("remaining")
    if isinstance(ttl_remaining, int):
        payload["ttl_remaining"] = ttl_remaining
    return payload


class Intent(str, Enum):
    HUMAN_REQUEST = "human_request"  # Клиент просит менеджера/человека
    FRUSTRATION = "frustration"  # Клиент раздражён, ругается
    REJECTION = "rejection"  # Клиент отказывается от помощи бота ("нет", "не надо")
    QUESTION = "question"  # Вопрос о продукте/услуге
    GREETING = "greeting"  # Приветствие
    THANKS = "thanks"  # Благодарность
    OUT_OF_DOMAIN = "out_of_domain"  # Вопрос не по теме
    OTHER = "other"  # Всё остальное


class DomainIntent(str, Enum):
    IN_DOMAIN = "in_domain"
    OUT_OF_DOMAIN = "out_of_domain"
    UNKNOWN = "unknown"


ESCALATION_INTENTS = {Intent.HUMAN_REQUEST, Intent.FRUSTRATION}
REJECTION_INTENTS = {Intent.REJECTION}

CLASSIFY_PROMPT = """Классифицируй сообщение клиента. Верни ТОЛЬКО одно слово из списка:
- human_request — клиент просит человека/менеджера/оператора
- frustration — клиент раздражён, ругается, использует мат
- rejection — клиент отказывается от помощи бота (нет, не надо, не нужно, сам разберусь)
- question — вопрос о продукте, услуге, цене, доставке
- greeting — приветствие (привет, здравствуйте, добрый день)
- thanks — благодарность (спасибо, благодарю)
- out_of_domain — сообщение не по теме (погода, рецепты, программирование)
- other — всё остальное

Примеры:
"Позови менеджера" → human_request
"Хочу поговорить с человеком" → human_request
"Да блять, сколько можно ждать!" → frustration
"Нет" → rejection
"Не надо" → rejection
"Нет, подожду менеджера" → rejection
"Какая цена?" → question
"Привет!" → greeting
"Спасибо за помощь" → thanks
"Какая погода в Алматы?" → out_of_domain

Сообщение: {message}

Ответ (одно слово):"""

HUMAN_REQUEST_PATTERNS = (
    re.compile(
        r"\b(менеджер\w*|оператор\w*|админ\w*|администратор\w*|человек\w*|консультант\w*|поддержк\w*|саппорт\w*|жив(ой|ым|ому|ого|ые|ых|ую)\w*)\b"
    ),
    re.compile(r"\b(позов|позв|соедин|переключ)\w*\b"),
)

OPT_OUT_EXACT = {
    "стоп",
    "stop",
    "unsubscribe",
    "отпишись",
    "отписаться",
    "mute",
    "не пиши",
    "не пишите",
    "заткнись",
    "заткнитесь",
}

OPT_OUT_SUBSTRINGS = [
    "не хочу чтобы ты писал",
    "не хочу чтобы вы писали",
    "не хочу чтобы ты писала",
    "не хочу чтобы вы писали",
    "не пиши мне",
    "не пишите мне",
    "хватит писать",
    "перестань писать",
    "перестаньте писать",
    "больше не пиши",
    "больше не пишите",
    "не надо писать",
    "не нужно писать",
    "удали меня",
    "заткнис",
]

FRUSTRATION_PATTERNS = (
    re.compile(r"\bзаткни(сь)?\b"),
    re.compile(r"\bотъ?еб\w*\b"),
    re.compile(r"\bза[её]б\w*\b"),
    re.compile(r"\bнахуй\b"),
    re.compile(r"\bиди нах\w*\b"),
    re.compile(r"\bпош[её]л нах\w*\b"),
    re.compile(r"\bотвали\b"),
    re.compile(r"\bебан\w*\b"),
)


def is_human_request_message(message: str) -> bool:
    normalized = normalize_for_matching(message)
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in HUMAN_REQUEST_PATTERNS)


def is_opt_out_message(message: str) -> bool:
    normalized = normalize_for_matching(message)
    if not normalized:
        return False
    if normalized in OPT_OUT_EXACT:
        return True
    return any(phrase in normalized for phrase in OPT_OUT_SUBSTRINGS)


def is_frustration_message(message: str) -> bool:
    normalized = normalize_for_matching(message)
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in FRUSTRATION_PATTERNS)


def classify_intent(message: str, *, timing_context: dict | None = None) -> Intent:
    """Classify user message intent using LLM."""
    try:
        if is_opt_out_message(message):
            return Intent.REJECTION

        if is_frustration_message(message):
            return Intent.FRUSTRATION

        if is_human_request_message(message):
            return Intent.HUMAN_REQUEST

        if not _current_openai_api_key():
            logger.info("Intent classification skipped: OPENAI_API_KEY missing")
            return Intent.OTHER
        if not _should_attempt_llm(
            timing_context,
            timeout_seconds=INTENT_TIMEOUT_SECONDS,
            stage="intent_llm",
        ):
            return Intent.OTHER

        llm = get_llm_provider()

        prompt = CLASSIFY_PROMPT.format(message=message)
        messages = [{"role": "user", "content": prompt}]

        llm_start = time.monotonic()
        try:
            response = llm.generate(
                messages,
                temperature=1.0,
                max_tokens=100,
                model=FAST_MODEL,
                timeout_seconds=INTENT_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException as exc:
            logger.info(
                "Timing",
                extra={
                    "context": {
                        "stage": "intent_llm_ms",
                        "elapsed_ms": round((time.monotonic() - llm_start) * 1000, 2),
                        "model_name": FAST_MODEL,
                        "model_tier": "fast",
                        "timeout": True,
                        "timeout_seconds": INTENT_TIMEOUT_SECONDS,
                    }
                },
            )
            record_llm_time(None, "intent_llm_ms", (time.monotonic() - llm_start) * 1000)
            logger.warning(f"Intent LLM timeout after {INTENT_TIMEOUT_SECONDS}s: {exc}")
            return Intent.OTHER

        logger.info(
            "Timing",
            extra={
                "context": {
                    "stage": "intent_llm_ms",
                    "elapsed_ms": round((time.monotonic() - llm_start) * 1000, 2),
                    "model_name": FAST_MODEL,
                    "model_tier": "fast",
                    "timeout": False,
                }
            },
        )
        record_llm_time(None, "intent_llm_ms", (time.monotonic() - llm_start) * 1000)
        result = response.content.strip().lower()

        # Parse response
        for intent in Intent:
            if intent.value in result:
                return intent

        return Intent.OTHER

    except Exception as e:
        logger.error(f"Intent classification error: {e}")
        return Intent.OTHER


def route_dialogue_controller(
    message: str,
    *,
    carryover: dict | None = None,
    expected_reply_type: str | None = None,
    client_slug: str | None = None,
    client_config: dict | None = None,
    timing_context: dict | None = None,
) -> dict:
    carryover_input = _build_controller_carryover(carryover)
    logger.warning(
        "Dialogue controller retired; semantic ownership lives in policy-core",
        extra={"context": {"client_slug": client_slug, "timing_context_present": bool(timing_context)}},
    )
    return {
        "ok": False,
        "payload": {
            "class": None,
            "goal": None,
            "intents": [],
            "slots": {},
            "followups": [],
            "safety_flags": [],
            "confidence": 0.0,
            "reason": _SECONDARY_SEMANTIC_OWNER_REMOVED,
            "carryover": dict(carryover_input),
            "controller_llm_ms": 0.0,
            "controller_error": _SECONDARY_SEMANTIC_OWNER_REMOVED,
            "controller_retry": False,
        },
        "error": _SECONDARY_SEMANTIC_OWNER_REMOVED,
        "raw": None,
    }


def route_llm_plan(
    message: str,
    *,
    expected_reply_type: str | None = None,
    current_goal: str | None = None,
    slot_state: dict | None = None,
    info_refs: list[str] | None = None,
    consult_refs: list[str] | None = None,
    client_slug: str | None = None,
    client_config: dict | None = None,
    timing_context: dict | None = None,
) -> dict:
    logger.warning(
        "route_llm_plan is retired; use route_llm_policy_core",
        extra={
            "context": {
                "expected_reply_type": expected_reply_type,
                "current_goal": current_goal,
                "client_slug": client_slug,
            }
        },
    )
    if isinstance(timing_context, dict):
        _log_timing("plan_llm_ms", 0.0, timing_context=timing_context, extra={"retired": True})
    return {
        "ok": False,
        "payload": None,
        "error": "legacy_retired_use_policy_core",
        "raw": None,
        "attempted": False,
        "elapsed_ms": 0.0,
    }


def route_llm_policy_core(
    message: str,
    *,
    expected_reply_type: str | None = None,
    current_goal: str | None = None,
    slot_state: dict | None = None,
    info_refs: list[str] | None = None,
    consult_refs: list[str] | None = None,
    memory_summary: str | None = None,
    memory_profile: dict[str, Any] | None = None,
    client_slug: str | None = None,
    client_config: dict | None = None,
    timing_context: dict | None = None,
    max_tokens_override: int | None = None,
) -> dict:
    result: dict[str, Any] = {
        "ok": False,
        "payload": None,
        "error": None,
        "raw": None,
        "attempted": False,
        "elapsed_ms": 0.0,
        "compact_input_used": False,
        "compact_retry_used": False,
        "structured_output_enabled": False,
        "structured_output_fallback_used": False,
        "structured_output_fallback_reason": None,
        "response_format_error": None,
        "policy_input": None,
        "schema_error": None,
        "binding": None,
        "projection_error": None,
        "projection_trace": None,
        "model_name": None,
        "attempt_count": 0,
        "contract_repair_retry_used": False,
        "contract_repair_reason": None,
        "contract_repair_input": None,
    }
    normalized = (message or "").strip()
    if not normalized:
        result["error"] = "empty_message"
        return result
    prompt = _load_policy_core_prompt()
    if not prompt:
        result["error"] = "prompt_missing"
        return result
    compact_prompt = _load_policy_core_compact_prompt() or prompt
    if not _current_openai_api_key():
        result["error"] = "no_api_key"
        return result
    policy_timeout_seconds = _resolve_policy_core_timeout_seconds(timing_context)
    micro_deadline_mode = False
    if policy_timeout_seconds < POLICY_CORE_MIN_TIMEOUT_SECONDS:
        micro_timeout_seconds = _resolve_policy_core_micro_timeout_seconds(timing_context)
        if micro_timeout_seconds >= 0.2:
            policy_timeout_seconds = micro_timeout_seconds
            micro_deadline_mode = True
        else:
            remaining_ms = _remaining_pipeline_budget_ms(timing_context)
            if remaining_ms is not None:
                _record_pipeline_budget_skip(
                    timing_context=timing_context,
                    stage="policy_core_llm",
                    required_ms=(POLICY_CORE_MIN_TIMEOUT_SECONDS * 1000) + POLICY_CORE_BUDGET_GUARD_MS,
                    remaining_ms=remaining_ms,
                )
            result["error"] = "deadline_exceeded"
            return result
    if not _should_attempt_llm(
        timing_context,
        timeout_seconds=policy_timeout_seconds,
        stage="policy_core_llm",
    ):
        result["error"] = "deadline_exceeded"
        return result

    budget_meta = consume_llm_budget(
        client_slug=client_slug or "unknown",
        client_config=client_config,
        scope="policy_core",
    )
    _append_llm_budget_event(timing_context, budget_meta)
    if not budget_meta.get("allowed", True):
        result["error"] = "budget_exceeded"
        return result

    normalized_memory_profile = _normalize_policy_core_memory_profile(memory_profile) or {}
    if (
        isinstance(current_goal, str)
        and current_goal.strip()
        and not normalized_memory_profile.get("active_goal")
    ):
        normalized_memory_profile["active_goal"] = current_goal.strip().casefold()
    legacy_slot_state = _normalize_policy_core_slot_state(slot_state)
    if legacy_slot_state and not normalized_memory_profile.get("slot_state"):
        normalized_memory_profile["slot_state"] = legacy_slot_state
    if not normalized_memory_profile.get("pending_question_contract"):
        pending_contract = _build_policy_core_pending_contract_from_expected_reply_type(
            expected_reply_type,
        )
        if pending_contract:
            normalized_memory_profile["pending_question_contract"] = pending_contract

    # Assemble the owner envelope from a governed context snapshot rather than
    # letting the owner gateway compile refs/cards locally.
    from app.services.policy_context_snapshot_service import build_policy_core_context_snapshot

    context_snapshot = build_policy_core_context_snapshot(
        client_slug=client_slug,
        info_refs=info_refs,
        consult_refs=consult_refs,
    )
    allowed_payload = context_snapshot.as_allowed_payload()
    context_payload = context_snapshot.as_context_payload()
    allowed_tool_actions = list(allowed_payload.get("tool_actions") or [])
    allowed_info_refs = list(allowed_payload.get("info_refs") or [])
    allowed_consult_refs = list(allowed_payload.get("consult_refs") or [])
    policy_input: dict[str, Any] = {
        "task": "llm_policy_core",
        "message": message,
        "allowed": dict(allowed_payload),
    }
    if context_payload:
        policy_input["context"] = context_payload
    normalized_memory_summary = _normalize_policy_core_memory_summary(memory_summary)
    if normalized_memory_summary or normalized_memory_profile:
        policy_input["memory"] = {}
        if normalized_memory_summary:
            policy_input["memory"]["summary"] = normalized_memory_summary
        if normalized_memory_profile:
            policy_input["memory"]["profile"] = normalized_memory_profile
    result["policy_input"] = deepcopy(policy_input)

    try:
        llm = get_llm_provider()
    except RuntimeError as exc:
        if "OPENAI_API_KEY missing" in str(exc):
            logger.info("Policy core skipped: OPENAI_API_KEY missing")
            result["error"] = "no_api_key"
            return result
        logger.warning(f"Policy core provider init failed: {exc}")
        result["error"] = _classify_llm_error(exc)
        return result
    temperature = _resolve_model_temperature(POLICY_CORE_MODEL)

    messages = _build_policy_core_messages(prompt, policy_input)
    compact_messages: list[dict[str, str]] | None = None
    compact_input_used = False
    compact_retry_used = False
    compact_first_attempt = (
        policy_timeout_seconds <= POLICY_CORE_COMPACT_TRIGGER_TIMEOUT_SECONDS
        or _policy_core_prefers_compact_first_attempt(normalized_memory_profile)
    )
    use_compact_messages = compact_first_attempt
    structured_output_enabled = _policy_core_structured_output_enabled()
    result["structured_output_enabled"] = structured_output_enabled
    from app.services.policy_vocabulary_snapshot_service import build_policy_core_response_format

    policy_response_format = (
        build_policy_core_response_format(allowed_tool_actions)
        if structured_output_enabled
        else None
    )
    retry_on_timeout = _is_env_enabled(POLICY_CORE_RETRY_ON_TIMEOUT, default=True)
    retry_on_transient = _is_env_enabled(POLICY_CORE_RETRY_ON_TRANSIENT, default=True)
    if micro_deadline_mode:
        retry_on_timeout = False
        retry_on_transient = False
    fallback_model = POLICY_CORE_TIMEOUT_FALLBACK_MODEL.strip()
    if fallback_model.casefold() == POLICY_CORE_MODEL.strip().casefold():
        fallback_model = ""
    timeout_attempts = [policy_timeout_seconds]
    if retry_on_timeout and not fallback_model:
        retry_timeout = min(POLICY_CORE_RETRY_TIMEOUT_SECONDS, policy_timeout_seconds)
        if retry_timeout > 0 and retry_timeout not in timeout_attempts:
            timeout_attempts.append(retry_timeout)
    if retry_on_transient and len(timeout_attempts) == 1 and not fallback_model:
        timeout_attempts.append(timeout_attempts[0])

    llm_start = time.monotonic()
    response = None
    error = None
    attempt_count = 0
    last_messages_for_attempt: list[dict[str, str]] = messages
    model_name_used = POLICY_CORE_MODEL
    temperature_used = temperature
    reasoning_effort_used = _resolve_policy_core_reasoning_effort(POLICY_CORE_MODEL)
    fallback_model_attempted = False
    timeout_seconds_used = policy_timeout_seconds
    max_tokens_used = _resolve_policy_core_max_tokens_with_cap(
        policy_timeout_seconds,
        max_tokens_override,
        POLICY_CORE_MODEL,
    )
    transient_retry_used = False
    structured_output_fallback_used = False
    last_attempt_used_compact = False

    def _retry_full_prompt_after_compact_failure() -> str | None:
        nonlocal response
        nonlocal attempt_count
        nonlocal last_messages_for_attempt
        nonlocal compact_retry_used
        nonlocal max_tokens_used
        nonlocal structured_output_fallback_used
        nonlocal last_attempt_used_compact
        if not last_attempt_used_compact:
            return None
        if not _should_attempt_llm(
            timing_context,
            timeout_seconds=timeout_seconds_used,
            stage="policy_core_full_prompt_retry",
        ):
            return None
        full_max_tokens = _resolve_policy_core_max_tokens_with_cap(
            timeout_seconds_used,
            max_tokens_override,
            model_name_used,
            compact_mode=False,
        )
        last_messages_for_attempt = messages
        compact_retry_used = True
        result["compact_retry_used"] = True
        try:
            response = llm.generate(
                messages=messages,
                max_tokens=full_max_tokens,
                model=model_name_used,
                timeout_seconds=timeout_seconds_used,
                temperature=temperature_used,
                response_format=policy_response_format,
                reasoning_effort=reasoning_effort_used,
            )
            attempt_count += 1
            max_tokens_used = full_max_tokens
            last_attempt_used_compact = False
            retry_content = (response.content or "").strip() if response else ""
            if not retry_content and policy_response_format is not None:
                retry_plain_response = llm.generate(
                    messages=messages,
                    max_tokens=full_max_tokens,
                    model=model_name_used,
                    timeout_seconds=timeout_seconds_used,
                    temperature=temperature_used,
                    reasoning_effort=reasoning_effort_used,
                )
                attempt_count += 1
                response = retry_plain_response
                retry_content = (retry_plain_response.content or "").strip() if retry_plain_response else ""
                if retry_content:
                    structured_output_fallback_used = True
                    result["structured_output_fallback_used"] = True
            result["elapsed_ms"] = round((time.monotonic() - llm_start) * 1000, 2)
            result["attempt_count"] = attempt_count
            return retry_content or None
        except httpx.TimeoutException:
            return None
        except Exception as exc:
            logger.warning("LLM policy core full-prompt retry after compact failure failed: %s", exc)
            return None

    for attempt_idx, timeout_seconds in enumerate(timeout_attempts):
        attempt_count = attempt_idx + 1
        timeout_seconds_used = timeout_seconds
        attempt_uses_compact = use_compact_messages
        last_attempt_used_compact = attempt_uses_compact
        max_tokens_used = _resolve_policy_core_max_tokens_with_cap(
            timeout_seconds,
            max_tokens_override,
            POLICY_CORE_MODEL,
            compact_mode=attempt_uses_compact,
        )
        if attempt_uses_compact and compact_messages is None:
            compact_input = _build_policy_core_compact_input(policy_input)
            compact_messages = _build_policy_core_messages(compact_prompt, compact_input)
        messages_for_attempt = compact_messages if attempt_uses_compact else messages
        last_messages_for_attempt = messages_for_attempt
        if attempt_uses_compact:
            compact_input_used = True
        if attempt_idx > 0 and not _should_attempt_llm(
            timing_context,
            timeout_seconds=timeout_seconds,
            stage="policy_core_llm_retry",
        ):
            error = "deadline_exceeded"
            break
        try:
            response = llm.generate(
                messages=messages_for_attempt,
                max_tokens=max_tokens_used,
                model=POLICY_CORE_MODEL,
                timeout_seconds=timeout_seconds,
                temperature=temperature,
                response_format=policy_response_format,
                reasoning_effort=reasoning_effort_used,
            )
            model_name_used = POLICY_CORE_MODEL
            error = None
            break
        except httpx.TimeoutException:
            error = "timeout"
            if not retry_on_timeout:
                break
            if attempt_idx + 1 < len(timeout_attempts):
                if not attempt_uses_compact:
                    use_compact_messages = True
                    compact_retry_used = True
                logger.warning(
                    "LLM policy core timeout; retrying",
                    extra={
                        "context": {
                            "attempt": attempt_count,
                            "retry_timeout_seconds": POLICY_CORE_RETRY_TIMEOUT_SECONDS,
                        }
                    },
                )
            continue
        except Exception as exc:
            classified_error = _classify_llm_error(exc)
            logger.warning(f"LLM policy core failed: {exc}")
            if (
                policy_response_format is not None
                and classified_error == "invalid_request"
                and _policy_core_uses_response_format(exc)
            ):
                try:
                    result["response_format_error"] = str(exc)
                    result["structured_output_fallback_reason"] = "response_format_invalid_request"
                    response = llm.generate(
                        messages=messages_for_attempt,
                        max_tokens=max_tokens_used,
                        model=POLICY_CORE_MODEL,
                        timeout_seconds=timeout_seconds,
                        temperature=temperature,
                        reasoning_effort=reasoning_effort_used,
                    )
                    model_name_used = POLICY_CORE_MODEL
                    error = None
                    structured_output_fallback_used = True
                    break
                except httpx.TimeoutException:
                    error = "timeout"
                    if not retry_on_timeout:
                        break
                    if attempt_idx + 1 < len(timeout_attempts):
                        if not attempt_uses_compact:
                            use_compact_messages = True
                            compact_retry_used = True
                        logger.warning(
                            "LLM policy core timeout after response_format fallback; retrying",
                            extra={
                                "context": {
                                    "attempt": attempt_count,
                                    "retry_timeout_seconds": POLICY_CORE_RETRY_TIMEOUT_SECONDS,
                                }
                            },
                        )
                    continue
                except Exception as plain_exc:
                    classified_error = _classify_llm_error(plain_exc)
                    logger.warning(
                        "LLM policy core fallback without response_format failed: %s",
                        plain_exc,
                    )
                    if classified_error == "exception":
                        raise
                    error = classified_error
                    if (
                        retry_on_transient
                        and not transient_retry_used
                        and classified_error
                        in {"connection_error", "provider_unavailable", "service_unavailable"}
                        and attempt_idx + 1 < len(timeout_attempts)
                    ):
                        transient_retry_used = True
                        logger.warning(
                            "LLM policy core transient error after response_format fallback; retrying",
                            extra={
                                "context": {
                                    "attempt": attempt_count,
                                    "error": classified_error,
                                }
                            },
                        )
                        continue
                    break
            error = classified_error
            if (
                retry_on_transient
                and not transient_retry_used
                and classified_error in {"connection_error", "provider_unavailable", "service_unavailable"}
                and attempt_idx + 1 < len(timeout_attempts)
            ):
                transient_retry_used = True
                logger.warning(
                    "LLM policy core transient error; retrying",
                    extra={
                        "context": {
                            "attempt": attempt_count,
                            "error": classified_error,
                        }
                    },
                )
                continue
            break

    if error == "timeout" and fallback_model:
        fallback_timeout_seconds = min(
            max(POLICY_CORE_FALLBACK_TIMEOUT_SECONDS, POLICY_CORE_RETRY_TIMEOUT_SECONDS),
            policy_timeout_seconds,
        )
        fallback_use_compact = use_compact_messages or compact_input_used
        if not fallback_use_compact:
            fallback_use_compact = True
            compact_retry_used = True
        if fallback_use_compact and compact_messages is None:
            compact_input = _build_policy_core_compact_input(policy_input)
            compact_messages = _build_policy_core_messages(compact_prompt, compact_input)
        fallback_messages = compact_messages if fallback_use_compact else messages
        last_messages_for_attempt = fallback_messages
        if fallback_use_compact:
            compact_input_used = True
        if _should_attempt_llm(
            timing_context,
            timeout_seconds=fallback_timeout_seconds,
            stage="policy_core_llm_fallback",
        ):
            attempt_count += 1
            timeout_seconds_used = fallback_timeout_seconds
            temperature_used = _resolve_model_temperature(fallback_model)
            reasoning_effort_used = _resolve_policy_core_reasoning_effort(fallback_model)
            max_tokens_used = _resolve_policy_core_max_tokens_with_cap(
                fallback_timeout_seconds,
                max_tokens_override,
                fallback_model,
                compact_mode=fallback_use_compact,
            )
            fallback_model_attempted = True
            last_attempt_used_compact = fallback_use_compact
            try:
                response = llm.generate(
                    messages=fallback_messages,
                    max_tokens=max_tokens_used,
                    model=fallback_model,
                    timeout_seconds=fallback_timeout_seconds,
                    temperature=temperature_used,
                    response_format=policy_response_format,
                    reasoning_effort=reasoning_effort_used,
                )
                model_name_used = fallback_model
                error = None
            except httpx.TimeoutException:
                error = "timeout"
            except Exception as exc:
                classified_error = _classify_llm_error(exc)
                logger.warning(f"LLM policy core fallback model failed: {exc}")
                if (
                    policy_response_format is not None
                    and classified_error == "invalid_request"
                    and _policy_core_uses_response_format(exc)
                ):
                    try:
                        result["response_format_error"] = str(exc)
                        result["structured_output_fallback_reason"] = "response_format_invalid_request"
                        response = llm.generate(
                            messages=fallback_messages,
                            max_tokens=max_tokens_used,
                            model=fallback_model,
                            timeout_seconds=fallback_timeout_seconds,
                            temperature=temperature_used,
                            reasoning_effort=reasoning_effort_used,
                        )
                        model_name_used = fallback_model
                        error = None
                        structured_output_fallback_used = True
                    except httpx.TimeoutException:
                        error = "timeout"
                    except Exception as plain_exc:
                        logger.warning(
                            "LLM policy core fallback model without response_format failed: %s",
                            plain_exc,
                        )
                        error = _classify_llm_error(plain_exc)
                else:
                    error = classified_error
        else:
            error = "deadline_exceeded"

    elapsed_ms = round((time.monotonic() - llm_start) * 1000, 2)
    result["attempted"] = True
    result["elapsed_ms"] = elapsed_ms
    result["compact_input_used"] = compact_input_used
    result["compact_retry_used"] = compact_retry_used
    result["structured_output_fallback_used"] = structured_output_fallback_used
    result["model_name"] = model_name_used
    result["attempt_count"] = attempt_count
    _log_timing(
        "policy_core_llm_ms",
        elapsed_ms,
        timing_context=timing_context,
        extra={
            "model_name": model_name_used,
            "model_tier": "fast",
            "timeout": error == "timeout",
            "timeout_seconds": timeout_seconds_used,
            "attempt_count": attempt_count,
            "retry_on_timeout": retry_on_timeout,
            "retry_on_transient": retry_on_transient,
            "transient_retry_used": transient_retry_used,
            "fallback_model_attempted": fallback_model_attempted,
            "fallback_model": fallback_model or None,
            "max_tokens": max_tokens_used,
            "max_tokens_override": max_tokens_override,
            "timeout_budgeted": policy_timeout_seconds,
            "temperature": temperature_used,
            "micro_deadline_mode": micro_deadline_mode,
            "compact_first_attempt": compact_first_attempt,
            "compact_input_used": compact_input_used,
            "compact_retry_used": compact_retry_used,
            "compact_trigger_timeout_seconds": POLICY_CORE_COMPACT_TRIGGER_TIMEOUT_SECONDS,
            "structured_output_enabled": structured_output_enabled,
            "structured_output_fallback_used": structured_output_fallback_used,
            "reasoning_effort": reasoning_effort_used,
        },
    )
    record_llm_time(client_slug, "policy_core_llm_ms", elapsed_ms)

    if error is not None:
        result["error"] = error
        return result

    content = (response.content or "").strip() if response else ""
    if not content and policy_response_format is not None:
        try:
            result["structured_output_fallback_reason"] = "response_format_empty_response"
            response = llm.generate(
                messages=last_messages_for_attempt,
                max_tokens=max_tokens_used,
                model=model_name_used,
                timeout_seconds=timeout_seconds_used,
                temperature=temperature_used,
                reasoning_effort=reasoning_effort_used,
            )
            attempt_count += 1
            content = (response.content or "").strip() if response else ""
            if content:
                structured_output_fallback_used = True
                result["structured_output_fallback_used"] = True
        except httpx.TimeoutException:
            result["error"] = "timeout"
            return result
        except Exception as plain_exc:
            logger.warning(
                "LLM policy core empty-response fallback without response_format failed: %s",
                plain_exc,
            )
            result["error"] = _classify_llm_error(plain_exc)
            return result
    if attempt_count != result.get("attempt_count") or (
        structured_output_fallback_used != result.get("structured_output_fallback_used")
    ):
        result["elapsed_ms"] = round((time.monotonic() - llm_start) * 1000, 2)
        result["attempt_count"] = attempt_count
        result["structured_output_fallback_used"] = structured_output_fallback_used
    result["raw"] = content
    if not content:
        retry_content = _retry_full_prompt_after_compact_failure()
        if retry_content:
            content = retry_content
            result["raw"] = content
    if not content:
        result["error"] = "empty_response"
        return result

    payload = _parse_policy_core_content(content)
    if not isinstance(payload, dict):
        retry_content = _retry_full_prompt_after_compact_failure()
        if retry_content:
            content = retry_content
            result["raw"] = content
            payload = _parse_policy_core_content(content)
    if not isinstance(payload, dict):
        result["error"] = "invalid_json"
        logger.warning(
            "LLM policy core returned invalid JSON",
            extra={
                "context": {
                    "model_name": model_name_used,
                    "elapsed_ms": elapsed_ms,
                    "raw": content[:500],
                }
            },
        )
        return result

    payload, tool_args_sanitized = _sanitize_policy_core_payload(payload)
    payload = _policy_core_apply_prevalidate_boundary_normalizations(
        payload=payload,
        normalized_memory_profile=normalized_memory_profile,
        current_message=message,
        context_payload=context_payload,
        client_slug=client_slug,
    )
    if tool_args_sanitized:
        result["tool_args_sanitized"] = True
    contract, schema_error = validate_llm_policy_core_output(payload)
    if schema_error:
        retry_content = _retry_full_prompt_after_compact_failure()
        if retry_content:
            content = retry_content
            result["raw"] = content
            payload = _parse_policy_core_content(content)
            if not isinstance(payload, dict):
                result["error"] = "invalid_json"
                logger.warning(
                    "LLM policy core returned invalid JSON after compact full retry",
                    extra={
                        "context": {
                            "model_name": model_name_used,
                            "elapsed_ms": elapsed_ms,
                            "raw": content[:500],
                        }
                    },
                )
                return result
            payload, tool_args_sanitized = _sanitize_policy_core_payload(payload)
            payload = _policy_core_apply_prevalidate_boundary_normalizations(
                payload=payload,
                normalized_memory_profile=normalized_memory_profile,
                current_message=message,
                context_payload=context_payload,
                client_slug=client_slug,
            )
            if tool_args_sanitized:
                result["tool_args_sanitized"] = True
            contract, schema_error = validate_llm_policy_core_output(payload)
    if schema_error and _policy_core_schema_requires_master_query_reclassification(
        payload=payload,
        schema_error=schema_error,
        normalized_memory_profile=normalized_memory_profile,
    ):
        schema_error = "llm_policy_core_error:active_followup_master_query_reclassification_required"
    if schema_error and _policy_core_schema_requires_booking_live_availability_reclassification(
        payload=payload,
        schema_error=schema_error,
        normalized_memory_profile=normalized_memory_profile,
    ):
        schema_error = "llm_policy_core_error:active_booking_live_availability_reclassification_required"
    if (
        schema_error == "llm_policy_core_error:standalone_fact_followup_contract_invalid"
        and not _policy_core_resume_pending_contract(normalized_memory_profile)
        and not _policy_core_active_pending_contract(normalized_memory_profile)
        and isinstance(payload, dict)
    ):
        stripped_payload = dict(payload)
        for field_name in (
            "expected_reply_type",
            "next_question",
            "open_questions",
            "pending_question_act",
            "pending_question_target",
            "active_question_relation",
        ):
            stripped_payload.pop(field_name, None)
        payload = stripped_payload
        contract, schema_error = validate_llm_policy_core_output(payload)
    if contract is not None and schema_error is None:
        schema_error = _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile=normalized_memory_profile,
            current_message=message,
            context_payload=context_payload,
            client_slug=client_slug,
        )
    if (
        schema_error == "llm_policy_core_error:standalone_fact_followup_contract_invalid"
        and not _policy_core_resume_pending_contract(normalized_memory_profile)
        and not _policy_core_active_pending_contract(normalized_memory_profile)
        and isinstance(payload, dict)
    ):
        stripped_payload = dict(payload)
        for field_name in (
            "expected_reply_type",
            "next_question",
            "open_questions",
            "pending_question_act",
            "pending_question_target",
            "active_question_relation",
        ):
            stripped_payload.pop(field_name, None)
        payload = stripped_payload
        contract, schema_error = validate_llm_policy_core_output(payload)
        if contract is not None and schema_error is None:
            schema_error = _validate_policy_core_runtime_contract(
                contract,
                normalized_memory_profile=normalized_memory_profile,
                current_message=message,
                context_payload=context_payload,
                client_slug=client_slug,
            )
    if (
        schema_error == "llm_policy_core_error:mixed_first_turn_hours_location_fact_scope_required"
        and isinstance(payload, dict)
    ):
        normalized_hours_location_payload = _policy_core_build_mixed_first_turn_hours_location_fact_boundary_payload(
            payload=payload,
            normalized_memory_profile=normalized_memory_profile,
            current_message=message,
            context_payload=context_payload,
            client_slug=client_slug,
        )
        if normalized_hours_location_payload is not None:
            payload = normalized_hours_location_payload
            contract, schema_error = validate_llm_policy_core_output(payload)
            if contract is not None and schema_error is None:
                schema_error = _validate_policy_core_runtime_contract(
                    contract,
                    normalized_memory_profile=normalized_memory_profile,
                    current_message=message,
                    context_payload=context_payload,
                    client_slug=client_slug,
                )
    if (
        schema_error == "llm_policy_core_error:mixed_first_turn_location_service_fact_reclassification_required"
        and isinstance(payload, dict)
    ):
        normalized_location_service_payload = _policy_core_build_mixed_first_turn_location_service_fact_boundary_payload(
            payload=payload,
            normalized_memory_profile=normalized_memory_profile,
            current_message=message,
            context_payload=context_payload,
            client_slug=client_slug,
        )
        if normalized_location_service_payload is not None:
            payload = normalized_location_service_payload
            contract, schema_error = validate_llm_policy_core_output(payload)
            if contract is not None and schema_error is None:
                schema_error = _validate_policy_core_runtime_contract(
                    contract,
                    normalized_memory_profile=normalized_memory_profile,
                    current_message=message,
                    context_payload=context_payload,
                    client_slug=client_slug,
                )
    if (
        schema_error == "llm_policy_core_error:service_query_multifact_reclassification_required"
        and isinstance(payload, dict)
    ):
        normalized_service_multifact_payload = _policy_core_build_service_query_multifact_boundary_payload(
            payload=payload,
            normalized_memory_profile=normalized_memory_profile,
            current_message=message,
            context_payload=context_payload,
            client_slug=client_slug,
        )
        if normalized_service_multifact_payload is not None:
            payload = normalized_service_multifact_payload
            contract, schema_error = validate_llm_policy_core_output(payload)
            if contract is not None and schema_error is None:
                schema_error = _validate_policy_core_runtime_contract(
                    contract,
                    normalized_memory_profile=normalized_memory_profile,
                    current_message=message,
                    context_payload=context_payload,
                    client_slug=client_slug,
                )
    if (
        schema_error == "llm_policy_core_error:mixed_first_turn_service_fact_booking_side_precedence_required"
        and isinstance(payload, dict)
    ):
        normalized_service_fact_payload = _policy_core_build_mixed_first_turn_service_fact_booking_side_boundary_payload(
            payload=payload,
            normalized_memory_profile=normalized_memory_profile,
            current_message=message,
            context_payload=context_payload,
            client_slug=client_slug,
        )
        if normalized_service_fact_payload is not None:
            payload = normalized_service_fact_payload
            contract, schema_error = validate_llm_policy_core_output(payload)
            if contract is not None and schema_error is None:
                schema_error = _validate_policy_core_runtime_contract(
                    contract,
                    normalized_memory_profile=normalized_memory_profile,
                    current_message=message,
                    context_payload=context_payload,
                    client_slug=client_slug,
                )
    if (
        schema_error == "llm_policy_core_error:start_booking_exact_datetime_progression_required"
        and isinstance(payload, dict)
    ):
        normalized_start_exact_datetime_payload = (
            _policy_core_build_start_booking_exact_datetime_boundary_payload(
                payload=payload,
                normalized_memory_profile=normalized_memory_profile,
                current_message=message,
                context_payload=context_payload,
                client_slug=client_slug,
            )
        )
        if normalized_start_exact_datetime_payload is not None:
            payload = normalized_start_exact_datetime_payload
            contract, schema_error = validate_llm_policy_core_output(payload)
            if contract is not None and schema_error is None:
                schema_error = _validate_policy_core_runtime_contract(
                    contract,
                    normalized_memory_profile=normalized_memory_profile,
                    current_message=message,
                    context_payload=context_payload,
                    client_slug=client_slug,
                )
    if (
        schema_error == "llm_policy_core_error:promotions_location_booking_followup_reclassification_required"
        and isinstance(payload, dict)
    ):
        normalized_promotions_location_booking_payload = (
            _policy_core_build_promotions_location_booking_followup_boundary_payload(
                payload=payload,
                normalized_memory_profile=normalized_memory_profile,
                current_message=message,
                context_payload=context_payload,
                client_slug=client_slug,
            )
        )
        if normalized_promotions_location_booking_payload is not None:
            payload = normalized_promotions_location_booking_payload
            contract, schema_error = validate_llm_policy_core_output(payload)
            if contract is not None and schema_error is None:
                schema_error = _validate_policy_core_runtime_contract(
                    contract,
                    normalized_memory_profile=normalized_memory_profile,
                    current_message=message,
                    context_payload=context_payload,
                    client_slug=client_slug,
                )
    if (
        schema_error == "llm_policy_core_error:promotions_grounded_service_booking_followup_reclassification_required"
        and isinstance(payload, dict)
    ):
        normalized_promotions_grounded_booking_payload = (
            _policy_core_build_promotions_grounded_service_booking_followup_boundary_payload(
                payload=payload,
                normalized_memory_profile=normalized_memory_profile,
                current_message=message,
                context_payload=context_payload,
                client_slug=client_slug,
            )
        )
        if normalized_promotions_grounded_booking_payload is not None:
            payload = normalized_promotions_grounded_booking_payload
            contract, schema_error = validate_llm_policy_core_output(payload)
            if contract is not None and schema_error is None:
                schema_error = _validate_policy_core_runtime_contract(
                    contract,
                    normalized_memory_profile=normalized_memory_profile,
                    current_message=message,
                    context_payload=context_payload,
                    client_slug=client_slug,
                )
    if (
        schema_error == "llm_policy_core_error:promotions_booking_followup_reclassification_required"
        and isinstance(payload, dict)
    ):
        normalized_promotions_booking_payload = (
            _policy_core_build_promotions_booking_fact_followup_boundary_payload(
                payload=payload,
                normalized_memory_profile=normalized_memory_profile,
                current_message=message,
                context_payload=context_payload,
                client_slug=client_slug,
            )
        )
        if normalized_promotions_booking_payload is not None:
            payload = normalized_promotions_booking_payload
            contract, schema_error = validate_llm_policy_core_output(payload)
            if contract is not None and schema_error is None:
                schema_error = _validate_policy_core_runtime_contract(
                    contract,
                    normalized_memory_profile=normalized_memory_profile,
                    current_message=message,
                    context_payload=context_payload,
                    client_slug=client_slug,
                )
    if (
        schema_error == "llm_policy_core_error:mixed_first_turn_promotions_precedence_reclassification_required"
        and isinstance(payload, dict)
    ):
        normalized_promotions_payload = _policy_core_build_mixed_first_turn_promotions_boundary_payload(
            payload=payload,
            normalized_memory_profile=normalized_memory_profile,
            current_message=message,
        )
        if normalized_promotions_payload is not None:
            payload = normalized_promotions_payload
            contract, schema_error = validate_llm_policy_core_output(payload)
            if contract is not None and schema_error is None:
                schema_error = _validate_policy_core_runtime_contract(
                    contract,
                    normalized_memory_profile=normalized_memory_profile,
                    current_message=message,
                    context_payload=context_payload,
                    client_slug=client_slug,
                )
    if schema_error:
        repair_instruction = _build_policy_core_contract_repair_instruction(
            schema_error=schema_error,
            normalized_memory_profile=normalized_memory_profile,
            contract=contract,
            current_message=message,
            context_payload=context_payload,
            client_slug=client_slug,
        )
        if repair_instruction and _should_attempt_llm(
            timing_context,
            timeout_seconds=timeout_seconds_used,
            stage="policy_core_contract_repair",
        ):
            repair_messages = list(messages)
            repair_messages.append({"role": "assistant", "content": content})
            repair_messages.append({"role": "user", "content": repair_instruction})
            try:
                repair_response = llm.generate(
                    messages=repair_messages,
                    max_tokens=max_tokens_used,
                    model=model_name_used,
                    timeout_seconds=timeout_seconds_used,
                    temperature=temperature_used,
                    response_format=policy_response_format,
                    reasoning_effort=reasoning_effort_used,
                )
                attempt_count += 1
                repaired_content = (repair_response.content or "").strip()
                if repaired_content:
                    result["contract_repair_retry_used"] = True
                    result["contract_repair_reason"] = schema_error
                    result["contract_repair_input"] = repair_instruction
                    result["raw"] = repaired_content
                    content = repaired_content
                    payload = _parse_policy_core_content(repaired_content)
                    if isinstance(payload, dict):
                        payload, repair_tool_args_sanitized = _sanitize_policy_core_payload(payload)
                        if repair_tool_args_sanitized:
                            result["tool_args_sanitized"] = True
                        payload = _policy_core_apply_prevalidate_boundary_normalizations(
                            payload=payload,
                            normalized_memory_profile=normalized_memory_profile,
                            current_message=message,
                            context_payload=context_payload,
                            client_slug=client_slug,
                        )
                        contract, schema_error = validate_llm_policy_core_output(payload)
                        if schema_error and _policy_core_schema_requires_master_query_reclassification(
                            payload=payload,
                            schema_error=schema_error,
                            normalized_memory_profile=normalized_memory_profile,
                        ):
                            schema_error = "llm_policy_core_error:active_followup_master_query_reclassification_required"
                        if schema_error and _policy_core_schema_requires_booking_live_availability_reclassification(
                            payload=payload,
                            schema_error=schema_error,
                            normalized_memory_profile=normalized_memory_profile,
                        ):
                            schema_error = "llm_policy_core_error:active_booking_live_availability_reclassification_required"
                        if (
                            schema_error == "llm_policy_core_error:standalone_fact_followup_contract_invalid"
                            and not _policy_core_resume_pending_contract(normalized_memory_profile)
                            and not _policy_core_active_pending_contract(normalized_memory_profile)
                            and isinstance(payload, dict)
                        ):
                            stripped_payload = dict(payload)
                            for field_name in (
                                "expected_reply_type",
                                "next_question",
                                "open_questions",
                                "pending_question_act",
                                "pending_question_target",
                                "active_question_relation",
                            ):
                                stripped_payload.pop(field_name, None)
                            payload = stripped_payload
                            contract, schema_error = validate_llm_policy_core_output(payload)
                        if contract is not None and schema_error is None:
                            schema_error = _validate_policy_core_runtime_contract(
                                contract,
                                normalized_memory_profile=normalized_memory_profile,
                                current_message=message,
                                context_payload=context_payload,
                                client_slug=client_slug,
                            )
                        if (
                            schema_error
                            == "llm_policy_core_error:standalone_fact_followup_contract_invalid"
                            and not _policy_core_resume_pending_contract(normalized_memory_profile)
                            and not _policy_core_active_pending_contract(normalized_memory_profile)
                            and isinstance(payload, dict)
                        ):
                            stripped_payload = dict(payload)
                            for field_name in (
                                "expected_reply_type",
                                "next_question",
                                "open_questions",
                                "pending_question_act",
                                "pending_question_target",
                                "active_question_relation",
                            ):
                                stripped_payload.pop(field_name, None)
                            payload = stripped_payload
                            contract, schema_error = validate_llm_policy_core_output(payload)
                            if contract is not None and schema_error is None:
                                schema_error = _validate_policy_core_runtime_contract(
                                    contract,
                                    normalized_memory_profile=normalized_memory_profile,
                                    current_message=message,
                                    context_payload=context_payload,
                                    client_slug=client_slug,
                                )
                        if (
                            schema_error
                            == "llm_policy_core_error:mixed_first_turn_hours_location_fact_scope_required"
                            and isinstance(payload, dict)
                        ):
                            normalized_hours_location_payload = (
                                _policy_core_build_mixed_first_turn_hours_location_fact_boundary_payload(
                                    payload=payload,
                                    normalized_memory_profile=normalized_memory_profile,
                                    current_message=message,
                                    context_payload=context_payload,
                                    client_slug=client_slug,
                                )
                            )
                            if normalized_hours_location_payload is not None:
                                payload = normalized_hours_location_payload
                                contract, schema_error = validate_llm_policy_core_output(payload)
                                if contract is not None and schema_error is None:
                                    schema_error = _validate_policy_core_runtime_contract(
                                        contract,
                                        normalized_memory_profile=normalized_memory_profile,
                                        current_message=message,
                                        context_payload=context_payload,
                                        client_slug=client_slug,
                                    )
                        if (
                            schema_error
                            == "llm_policy_core_error:mixed_first_turn_location_service_fact_reclassification_required"
                            and isinstance(payload, dict)
                        ):
                            normalized_location_service_payload = (
                                _policy_core_build_mixed_first_turn_location_service_fact_boundary_payload(
                                    payload=payload,
                                    normalized_memory_profile=normalized_memory_profile,
                                    current_message=message,
                                    context_payload=context_payload,
                                    client_slug=client_slug,
                                )
                            )
                            if normalized_location_service_payload is not None:
                                payload = normalized_location_service_payload
                                contract, schema_error = validate_llm_policy_core_output(payload)
                                if contract is not None and schema_error is None:
                                    schema_error = _validate_policy_core_runtime_contract(
                                        contract,
                                        normalized_memory_profile=normalized_memory_profile,
                                        current_message=message,
                                        context_payload=context_payload,
                                        client_slug=client_slug,
                                    )
                        if (
                            schema_error
                            == "llm_policy_core_error:service_query_multifact_reclassification_required"
                            and isinstance(payload, dict)
                        ):
                            normalized_service_multifact_payload = (
                                _policy_core_build_service_query_multifact_boundary_payload(
                                    payload=payload,
                                    normalized_memory_profile=normalized_memory_profile,
                                    current_message=message,
                                    context_payload=context_payload,
                                    client_slug=client_slug,
                                )
                            )
                            if normalized_service_multifact_payload is not None:
                                payload = normalized_service_multifact_payload
                                contract, schema_error = validate_llm_policy_core_output(payload)
                                if contract is not None and schema_error is None:
                                    schema_error = _validate_policy_core_runtime_contract(
                                        contract,
                                        normalized_memory_profile=normalized_memory_profile,
                                        current_message=message,
                                        context_payload=context_payload,
                                        client_slug=client_slug,
                                    )
                        if (
                            schema_error
                            == "llm_policy_core_error:mixed_first_turn_service_fact_booking_side_precedence_required"
                            and isinstance(payload, dict)
                        ):
                            normalized_service_fact_payload = (
                                _policy_core_build_mixed_first_turn_service_fact_booking_side_boundary_payload(
                                    payload=payload,
                                    normalized_memory_profile=normalized_memory_profile,
                                    current_message=message,
                                    context_payload=context_payload,
                                    client_slug=client_slug,
                                )
                            )
                            if normalized_service_fact_payload is not None:
                                payload = normalized_service_fact_payload
                                contract, schema_error = validate_llm_policy_core_output(payload)
                                if contract is not None and schema_error is None:
                                    schema_error = _validate_policy_core_runtime_contract(
                                        contract,
                                        normalized_memory_profile=normalized_memory_profile,
                                        current_message=message,
                                            context_payload=context_payload,
                                            client_slug=client_slug,
                                        )
                        if (
                            schema_error
                            == "llm_policy_core_error:start_booking_exact_datetime_progression_required"
                            and isinstance(payload, dict)
                        ):
                            normalized_start_exact_datetime_payload = (
                                _policy_core_build_start_booking_exact_datetime_boundary_payload(
                                    payload=payload,
                                    normalized_memory_profile=normalized_memory_profile,
                                    current_message=message,
                                    context_payload=context_payload,
                                    client_slug=client_slug,
                                )
                            )
                            if normalized_start_exact_datetime_payload is not None:
                                payload = normalized_start_exact_datetime_payload
                                contract, schema_error = validate_llm_policy_core_output(payload)
                                if contract is not None and schema_error is None:
                                    schema_error = _validate_policy_core_runtime_contract(
                                        contract,
                                        normalized_memory_profile=normalized_memory_profile,
                                        current_message=message,
                                        context_payload=context_payload,
                                        client_slug=client_slug,
                                    )
                        if (
                            schema_error
                            == "llm_policy_core_error:promotions_location_booking_followup_reclassification_required"
                            and isinstance(payload, dict)
                        ):
                            normalized_promotions_location_booking_payload = (
                                _policy_core_build_promotions_location_booking_followup_boundary_payload(
                                    payload=payload,
                                    normalized_memory_profile=normalized_memory_profile,
                                    current_message=message,
                                    context_payload=context_payload,
                                    client_slug=client_slug,
                                )
                            )
                            if normalized_promotions_location_booking_payload is not None:
                                payload = normalized_promotions_location_booking_payload
                                contract, schema_error = validate_llm_policy_core_output(payload)
                                if contract is not None and schema_error is None:
                                    schema_error = _validate_policy_core_runtime_contract(
                                        contract,
                                        normalized_memory_profile=normalized_memory_profile,
                                        current_message=message,
                                        context_payload=context_payload,
                                        client_slug=client_slug,
                                    )
                        if (
                            schema_error
                            == "llm_policy_core_error:promotions_grounded_service_booking_followup_reclassification_required"
                            and isinstance(payload, dict)
                        ):
                            normalized_promotions_grounded_booking_payload = (
                                _policy_core_build_promotions_grounded_service_booking_followup_boundary_payload(
                                    payload=payload,
                                    normalized_memory_profile=normalized_memory_profile,
                                    current_message=message,
                                    context_payload=context_payload,
                                    client_slug=client_slug,
                                )
                            )
                            if normalized_promotions_grounded_booking_payload is not None:
                                payload = normalized_promotions_grounded_booking_payload
                                contract, schema_error = validate_llm_policy_core_output(payload)
                                if contract is not None and schema_error is None:
                                    schema_error = _validate_policy_core_runtime_contract(
                                        contract,
                                        normalized_memory_profile=normalized_memory_profile,
                                        current_message=message,
                                        context_payload=context_payload,
                                        client_slug=client_slug,
                                    )
                        if (
                            schema_error
                            == "llm_policy_core_error:promotions_booking_followup_reclassification_required"
                            and isinstance(payload, dict)
                        ):
                            normalized_promotions_booking_payload = (
                                _policy_core_build_promotions_booking_fact_followup_boundary_payload(
                                    payload=payload,
                                    normalized_memory_profile=normalized_memory_profile,
                                    current_message=message,
                                    context_payload=context_payload,
                                    client_slug=client_slug,
                                )
                            )
                            if normalized_promotions_booking_payload is not None:
                                payload = normalized_promotions_booking_payload
                                contract, schema_error = validate_llm_policy_core_output(payload)
                                if contract is not None and schema_error is None:
                                    schema_error = _validate_policy_core_runtime_contract(
                                        contract,
                                        normalized_memory_profile=normalized_memory_profile,
                                        current_message=message,
                                        context_payload=context_payload,
                                        client_slug=client_slug,
                                    )
                        if (
                            schema_error
                            == "llm_policy_core_error:mixed_first_turn_promotions_precedence_reclassification_required"
                            and isinstance(payload, dict)
                        ):
                            normalized_promotions_payload = (
                                _policy_core_build_mixed_first_turn_promotions_boundary_payload(
                                    payload=payload,
                                    normalized_memory_profile=normalized_memory_profile,
                                    current_message=message,
                                )
                            )
                            if normalized_promotions_payload is not None:
                                payload = normalized_promotions_payload
                                contract, schema_error = validate_llm_policy_core_output(payload)
                                if contract is not None and schema_error is None:
                                    schema_error = _validate_policy_core_runtime_contract(
                                        contract,
                                        normalized_memory_profile=normalized_memory_profile,
                                        current_message=message,
                                        context_payload=context_payload,
                                        client_slug=client_slug,
                                    )
                elapsed_ms = round((time.monotonic() - llm_start) * 1000, 2)
                result["elapsed_ms"] = elapsed_ms
                result["attempt_count"] = attempt_count
            except Exception as exc:
                logger.warning("LLM policy core contract repair retry failed: %s", exc)
        if schema_error:
            result["error"] = "invalid_schema"
            result["schema_error"] = schema_error
            logger.warning(
                "LLM policy core returned invalid schema",
                extra={
                    "context": {
                        "model_name": model_name_used,
                        "elapsed_ms": elapsed_ms,
                        "schema_error": schema_error,
                        "payload": payload,
                    }
                },
            )
            return result
    allowed_pack_refs = {
        ref.strip()
        for ref in allowed_info_refs + allowed_consult_refs
        if isinstance(ref, str) and ref.strip()
    }
    if any(ref not in allowed_pack_refs for ref in contract.pack_refs):
        result["error"] = "invalid_schema"
        return result

    semantic_frame = contract.model_dump(exclude_none=True)
    for container_field in ("pack_refs", "slots", "open_questions", "risk_signals", "entity_refs", "referents"):
        if not semantic_frame.get(container_field):
            semantic_frame.pop(container_field, None)
    semantic_decision = SemanticDecisionV1.from_policy_core_payload(semantic_frame)
    semantic_decision_payload = semantic_decision.model_dump(mode="python", exclude_none=True)

    binding_plan, projection_trace, projection_error = build_binding_plan(
        semantic_decision=semantic_decision_payload,
        allowed_tool_actions=allowed_tool_actions,
    )
    if projection_error:
        result["error"] = "invalid_projection"
        result["projection_error"] = projection_error
        result["projection_trace"] = {
            "status": "error",
            "projection_source": "policy_tool_projector",
            "tool_action_hint": semantic_frame.get("tool_action_hint"),
            "error": projection_error,
        }
        return result

    result["binding_plan"] = binding_plan.model_dump(mode="python", exclude_none=True)
    result["binding"] = binding_plan.as_compat_binding_payload()
    result["projection_trace"] = dict(projection_trace or {})
    result["ok"] = True
    result["payload"] = semantic_decision_payload
    return result


def interpret_expected_reply(
    message: str,
    *,
    expected_reply_type: str | None,
    carryover: dict | None = None,
    question_context: dict | None = None,
    client_slug: str | None = None,
) -> dict:
    expected_reply_type_cleaned = (
        expected_reply_type.strip().lower()
        if isinstance(expected_reply_type, str)
        else None
    )
    expected_slot = ANSWER_INTERPRETER_SLOT_BY_REPLY_TYPE.get(
        expected_reply_type_cleaned or ""
    )
    logger.warning(
        "Answer interpreter retired; semantic ownership lives in policy-core",
        extra={
            "context": {
                "client_slug": client_slug,
                "expected_reply_type": expected_reply_type_cleaned,
                "question_context_present": bool(question_context),
            }
        },
    )
    return {
        "ok": False,
        "payload": {
            "slot": expected_slot or "",
            "detected_slot": "",
            "value": "",
            "confidence": 0.0,
            "reason": _SECONDARY_SEMANTIC_OWNER_REMOVED,
        },
        "error": _SECONDARY_SEMANTIC_OWNER_REMOVED,
        "raw": None,
    }


def should_escalate(intent: Intent) -> bool:
    """Check if intent requires escalation to human."""
    return intent in ESCALATION_INTENTS


def is_rejection(intent: Intent) -> bool:
    """Check if client is rejecting bot's help."""
    return intent in REJECTION_INTENTS


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    normalized = text.strip().casefold()
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _ensure_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    if isinstance(value, tuple):
        return [str(v) for v in value if v]
    if isinstance(value, str):
        return [value]
    return []


def _get_domain_router_config(client_config: dict | None) -> dict:
    if not isinstance(client_config, dict):
        return {}
    nested = client_config.get("domain_router")
    if isinstance(nested, dict):
        return nested
    if any(
        key in client_config
        for key in (
            "anchors_in",
            "anchors_out",
            "anchors_in_strict",
            "strict_in_anchors",
            "in_threshold",
            "out_threshold",
            "in_hit_threshold",
            "out_hit_threshold",
            "strict_in_hit_threshold",
        )
    ):
        return client_config
    return {}


def _score_against_anchors(
    text_normalized: str,
    tokens: set[str],
    anchors: Iterable[str],
    hit_threshold: float,
) -> tuple[float, str | None, int]:
    best_score = 0.0
    best_anchor = None
    hits = 0
    for anchor in anchors:
        anchor_normalized = _normalize_text(anchor)
        if not anchor_normalized:
            continue
        if anchor_normalized in text_normalized:
            score = 0.95
        else:
            anchor_tokens = set(anchor_normalized.split())
            if not anchor_tokens:
                continue
            score = len(tokens & anchor_tokens) / max(len(anchor_tokens), 1)
        if score > best_score:
            best_score = score
            best_anchor = anchor
        if score >= hit_threshold:
            hits += 1
    return best_score, best_anchor, hits


def classify_domain_with_scores(
    text: str,
    client_config: dict | None,
) -> Tuple[DomainIntent, float, float, dict]:
    """
    Classify message domain using per-client anchors (no network calls).
    Returns (domain_intent, in_score, out_score, meta).
    """
    config = _get_domain_router_config(client_config)
    anchors_in = _ensure_list(config.get("anchors_in"))
    anchors_out = _ensure_list(config.get("anchors_out"))
    strict_in_anchors = _ensure_list(config.get("anchors_in_strict") or config.get("strict_in_anchors"))
    in_threshold = float(config.get("in_threshold", 0.62))
    out_threshold = float(config.get("out_threshold", 0.62))
    margin = float(config.get("margin", 0.08))
    min_len = int(config.get("min_len", 5))
    in_hit_threshold = float(config.get("in_hit_threshold", in_threshold))
    out_hit_threshold = float(config.get("out_hit_threshold", out_threshold))
    strict_in_hit_threshold = float(config.get("strict_in_hit_threshold", in_threshold))

    text_normalized = _normalize_text(text)
    tokens = set(text_normalized.split()) if text_normalized else set()

    if not anchors_in and not anchors_out and not strict_in_anchors:
        return (
            DomainIntent.UNKNOWN,
            0.0,
            0.0,
            {
                "in_threshold": in_threshold,
                "out_threshold": out_threshold,
                "margin": margin,
                "in_hit_threshold": in_hit_threshold,
                "out_hit_threshold": out_hit_threshold,
                "strict_in_hit_threshold": strict_in_hit_threshold,
                "anchors_in": len(anchors_in),
                "anchors_out": len(anchors_out),
                "strict_in_anchors": len(strict_in_anchors),
                "in_hits": 0,
                "out_hits": 0,
                "strict_in_hits": 0,
                "message_len": len(text_normalized),
            },
        )

    in_score, matched_in, in_hits = _score_against_anchors(
        text_normalized, tokens, anchors_in, in_hit_threshold
    )
    out_score, matched_out, out_hits = _score_against_anchors(
        text_normalized, tokens, anchors_out, out_hit_threshold
    )
    _, matched_strict_in, strict_in_hits = _score_against_anchors(
        text_normalized, tokens, strict_in_anchors, strict_in_hit_threshold
    )

    domain_intent = DomainIntent.UNKNOWN
    if len(text_normalized) >= min_len:
        if in_score >= in_threshold and in_score >= out_score + margin:
            domain_intent = DomainIntent.IN_DOMAIN
        elif out_score >= out_threshold and out_score >= in_score + margin:
            domain_intent = DomainIntent.OUT_OF_DOMAIN

    meta = {
        "in_threshold": in_threshold,
        "out_threshold": out_threshold,
        "margin": margin,
        "in_hit_threshold": in_hit_threshold,
        "out_hit_threshold": out_hit_threshold,
        "strict_in_hit_threshold": strict_in_hit_threshold,
        "anchors_in": len(anchors_in),
        "anchors_out": len(anchors_out),
        "strict_in_anchors": len(strict_in_anchors),
        "matched_in": matched_in,
        "matched_out": matched_out,
        "matched_strict_in": matched_strict_in,
        "in_hits": in_hits,
        "out_hits": out_hits,
        "strict_in_hits": strict_in_hits,
        "message_len": len(text_normalized),
    }
    return domain_intent, in_score, out_score, meta


def is_strong_out_of_domain(
    text: str,
    domain_intent: DomainIntent,
    in_score: float,
    out_score: float,
    client_config: dict | None,
) -> tuple[bool, dict]:
    """
    Conservative strong out-of-domain gate.
    Uses stricter thresholds and minimum length to avoid false positives.
    """
    config = _get_domain_router_config(client_config)
    out_threshold = float(config.get("out_threshold", 0.62))
    in_threshold = float(config.get("in_threshold", 0.62))
    anchors_out = _ensure_list(config.get("anchors_out"))
    strict_in_anchors = _ensure_list(config.get("anchors_in_strict") or config.get("strict_in_anchors"))
    out_hit_threshold = float(config.get("out_hit_threshold", out_threshold))
    strict_in_hit_threshold = float(config.get("strict_in_hit_threshold", in_threshold))

    strict_out_threshold = float(config.get("strict_out_threshold", max(out_threshold, 0.8)))
    strong_out_threshold = float(config.get("strong_out_threshold", max(out_threshold, 0.72)))
    strict_margin = float(config.get("strict_margin", 0.18))
    strong_margin = float(config.get("strong_margin", 0.12))
    strict_in_max = float(config.get("strict_in_max", 0.4))
    strong_in_max = float(config.get("strong_in_max", 0.5))
    strict_min_len = int(config.get("strict_min_len", 6))

    text_normalized = _normalize_text(text)
    tokens = set(text_normalized.split()) if text_normalized else set()
    message_len = len(text_normalized)

    _, matched_out, out_hits = _score_against_anchors(text_normalized, tokens, anchors_out, out_hit_threshold)
    _, matched_strict_in, strict_in_hits = _score_against_anchors(
        text_normalized, tokens, strict_in_anchors, strict_in_hit_threshold
    )

    strong = False
    if out_hits > 0 and strict_in_hits == 0:
        strong = True
    elif domain_intent == DomainIntent.OUT_OF_DOMAIN:
        if (
            message_len >= strict_min_len
            and out_score >= strict_out_threshold
            and out_score >= in_score + strict_margin
            and in_score <= strict_in_max
        ):
            strong = True
        elif (
            out_score >= strong_out_threshold
            and out_score >= in_score + strong_margin
            and in_score <= strong_in_max
        ):
            strong = True

    meta = {
        "strict_out_threshold": strict_out_threshold,
        "strong_out_threshold": strong_out_threshold,
        "strict_margin": strict_margin,
        "strong_margin": strong_margin,
        "strict_in_max": strict_in_max,
        "strong_in_max": strong_in_max,
        "strict_min_len": strict_min_len,
        "message_len": message_len,
        "out_hit_threshold": out_hit_threshold,
        "strict_in_hit_threshold": strict_in_hit_threshold,
        "out_hits": out_hits,
        "strict_in_hits": strict_in_hits,
        "matched_out": matched_out,
        "matched_strict_in": matched_strict_in,
    }
    return strong, meta


def _tokenize_for_bm25(text: str) -> list[str]:
    if not text:
        return []
    tokens = re.findall(r"[\w]+", text.casefold())
    return [token for token in tokens if len(token) > 1]


def _build_rag_filter(
    *,
    client_slug: str,
    branch_id: str | None,
    knowledge_tag: str | None,
) -> tuple[dict, dict]:
    filter_payload = {"must": [{"key": "metadata.client_slug", "match": {"value": client_slug}}]}
    filter_meta = {
        "client_slug": client_slug,
        "branch_id": branch_id,
        "knowledge_tag": knowledge_tag,
    }
    if knowledge_tag:
        filter_payload["must"].append(
            {"key": "metadata.knowledge_tag", "match": {"value": knowledge_tag}}
        )
        filter_meta.update({"filter_mode": "branch", "filter_reason": "knowledge_tag"})
    elif branch_id:
        filter_payload["must"].append(
            {"key": "metadata.branch_id", "match": {"value": branch_id}}
        )
        filter_meta.update({"filter_mode": "branch", "filter_reason": "branch_id"})
    else:
        filter_meta.update({"filter_mode": "branch", "filter_reason": "branch_missing"})
    return filter_payload, filter_meta


def _fetch_bm25_corpus(
    client_slug: str,
    *,
    max_docs: int,
    branch_id: str | None = None,
    knowledge_tag: str | None = None,
) -> tuple[list[dict], dict]:
    if not client_slug or max_docs <= 0:
        return [], {"filter_mode": "client", "filter_reason": "missing_client_slug"}
    if not branch_id and not knowledge_tag:
        return [], {"filter_mode": "branch", "filter_reason": "branch_missing"}
    headers = {"api-key": QDRANT_API_KEY} if QDRANT_API_KEY else None
    filter_payload, filter_meta = _build_rag_filter(
        client_slug=client_slug,
        branch_id=branch_id,
        knowledge_tag=knowledge_tag,
    )

    def _scroll_points(payload: dict) -> list[dict]:
        points: list[dict] = []
        offset = None
        limit = min(100, max_docs)
        with httpx.Client(timeout=RAG_BM25_TIMEOUT_SECONDS) as client:
            while len(points) < max_docs:
                request_payload = dict(payload)
                request_payload.update(
                    {
                        "limit": limit,
                        "with_payload": True,
                        "with_vectors": False,
                    }
                )
                if offset is not None:
                    request_payload["offset"] = offset
                response = client.post(
                    f"{QDRANT_HOST}/collections/{QDRANT_COLLECTION}/points/scroll",
                    headers=headers,
                    json=request_payload,
                )
                if response.status_code != 200:
                    logger.warning(
                        "BM25 scroll failed",
                        extra={"context": {"status": response.status_code, "client_slug": client_slug}},
                    )
                    break
                data = response.json().get("result") or {}
                batch = data.get("points") or []
                points.extend(batch)
                offset = data.get("next_page_offset")
                if not offset or not batch:
                    break
                limit = min(100, max_docs - len(points))
        return points[:max_docs]

    points = _scroll_points({"filter": filter_payload})
    if points or filter_meta.get("filter_mode") != "branch":
        return points, filter_meta

    filter_meta.update({"filter_reason": "branch_filter_empty"})
    return points, filter_meta


def _bm25_search(
    query: str,
    client_slug: str,
    *,
    branch_id: str | None = None,
    knowledge_tag: str | None = None,
) -> tuple[list[dict], dict | None]:
    query_tokens = _tokenize_for_bm25(query)
    if not query_tokens:
        return [], None
    try:
        corpus, filter_meta = _fetch_bm25_corpus(
            client_slug,
            max_docs=RAG_BM25_MAX_DOCS,
            branch_id=branch_id,
            knowledge_tag=knowledge_tag,
        )
    except Exception as exc:
        logger.warning(f"BM25 corpus fetch failed: {exc}")
        return [], None
    if not corpus:
        return [], filter_meta

    doc_tokens: list[list[str]] = []
    doc_meta: list[dict] = []
    for point in corpus:
        payload = point.get("payload") or {}
        text = payload.get("content") or ""
        tokens = _tokenize_for_bm25(text)
        if not tokens:
            continue
        doc_tokens.append(tokens)
        doc_meta.append(
            {
                "id": point.get("id"),
                "text": text,
                "source": payload.get("metadata", {}).get("doc_name"),
                "metadata": payload.get("metadata", {}),
            }
        )

    if not doc_tokens:
        return [], filter_meta

    doc_count = len(doc_tokens)
    avg_len = sum(len(tokens) for tokens in doc_tokens) / max(doc_count, 1)
    df: dict[str, int] = {}
    for tokens in doc_tokens:
        for token in set(tokens):
            df[token] = df.get(token, 0) + 1

    k1 = 1.5
    b = 0.75
    scores: list[tuple[int, float]] = []
    for idx, tokens in enumerate(doc_tokens):
        dl = len(tokens)
        tf: dict[str, int] = {}
        for token in tokens:
            tf[token] = tf.get(token, 0) + 1
        score = 0.0
        for term in query_tokens:
            term_df = df.get(term, 0)
            if term_df == 0:
                continue
            idf = math.log((doc_count - term_df + 0.5) / (term_df + 0.5) + 1)
            freq = tf.get(term, 0)
            if freq == 0:
                continue
            denom = freq + k1 * (1 - b + b * (dl / max(avg_len, 1)))
            score += idf * ((freq * (k1 + 1)) / max(denom, 1e-9))
        if score > 0:
            scores.append((idx, score))

    if not scores:
        return [], filter_meta
    scores.sort(key=lambda item: item[1], reverse=True)
    top = scores[: max(RAG_BM25_LIMIT, 1)]
    results: list[dict] = []
    for idx, score in top:
        meta = dict(doc_meta[idx])
        meta["bm25_score"] = score
        results.append(meta)
    return results, filter_meta


def hybrid_retrieve_knowledge(
    *,
    query: str,
    client_slug: str,
    vector_results: list[dict],
    limit: int = 5,
    branch_id: str | None = None,
    knowledge_tag: str | None = None,
    dense_meta: dict | None = None,
) -> tuple[list[dict], dict]:
    bm25_enabled = _is_env_enabled(os.environ.get("RAG_BM25_ENABLED"), default=True)
    if not QDRANT_API_KEY or os.environ.get("PYTEST_CURRENT_TEST"):
        bm25_enabled = False
    bm25_results: list[dict] = []
    bm25_filter_meta: dict | None = None
    if bm25_enabled:
        try:
            bm25_results, bm25_filter_meta = _bm25_search(
                query,
                client_slug,
                branch_id=branch_id,
                knowledge_tag=knowledge_tag,
            )
        except Exception as exc:
            logger.warning(f"BM25 search failed: {exc}")

    by_key: dict[tuple[str | None, str | None], dict] = {}
    vector_max = 0.0
    for item in vector_results or []:
        text = item.get("text")
        source = item.get("source")
        key = (source, text)
        vector_score = float(item.get("score") or 0.0)
        vector_max = max(vector_max, vector_score)
        merged = dict(item)
        merged["vector_score"] = vector_score
        merged["bm25_score"] = 0.0
        by_key[key] = merged

    bm25_max = 0.0
    for item in bm25_results:
        text = item.get("text")
        source = item.get("source")
        key = (source, text)
        bm25_score = float(item.get("bm25_score") or 0.0)
        bm25_max = max(bm25_max, bm25_score)
        if key in by_key:
            by_key[key]["bm25_score"] = bm25_score
            continue
        merged = dict(item)
        merged.setdefault("metadata", {})
        merged["vector_score"] = 0.0
        merged["bm25_score"] = bm25_score
        by_key[key] = merged

    vector_count = len(vector_results or [])
    dense_trace = dict(dense_meta) if isinstance(dense_meta, dict) else {}
    dense_attempted = bool(dense_trace.get("attempted")) or vector_count > 0
    dense_available = dense_trace.get("available")
    if not isinstance(dense_available, bool):
        dense_available = vector_count > 0
    dense_status = str(dense_trace.get("status") or ("ok" if dense_available else "not_attempted"))
    dense_unavailable_reason = dense_trace.get("unavailable_reason")

    vector_weight = max(RAG_HYBRID_VECTOR_WEIGHT, 0.0)
    bm25_weight = max(RAG_HYBRID_BM25_WEIGHT, 0.0)
    if vector_weight + bm25_weight <= 0:
        vector_weight = 0.6
        bm25_weight = 0.4

    for item in by_key.values():
        vector_score = item.get("vector_score", 0.0)
        vector_norm = vector_score / vector_max if vector_max > 0 else 0.0
        bm25_norm = item.get("bm25_score", 0.0) / bm25_max if bm25_max > 0 else 0.0
        item["hybrid_score"] = (vector_weight * vector_norm) + (bm25_weight * bm25_norm)
        item["score"] = max(vector_score, bm25_norm)

    merged_results = sorted(
        by_key.values(),
        key=lambda item: item.get("hybrid_score", 0.0),
        reverse=True,
    )
    merged_results = merged_results[: max(limit, 1)]

    bm25_count = len(bm25_results)
    if vector_count > 0 and bm25_count > 0:
        retrieval_mode = "dense_sparse"
    elif bm25_count > 0:
        retrieval_mode = "sparse_only"
    elif vector_count > 0:
        retrieval_mode = "dense_only"
    else:
        retrieval_mode = "empty"

    bm25_max_norm = 1.0 if bm25_max > 0 else 0.0
    rag_scores = {
        "vector_max": vector_max,
        "bm25_max": bm25_max,
        "bm25_max_norm": bm25_max_norm,
        "hybrid_max": merged_results[0]["hybrid_score"] if merged_results else 0.0,
        "vector_count": vector_count,
        "bm25_count": bm25_count,
        "vector_weight": vector_weight,
        "bm25_weight": bm25_weight,
        "bm25_enabled": bm25_enabled,
        "retrieval_mode": retrieval_mode,
        "dense_attempted": dense_attempted,
        "dense_available": dense_available,
        "dense_status": dense_status,
        "dense_unavailable_reason": dense_unavailable_reason,
    }
    if isinstance(bm25_filter_meta, dict):
        rag_scores["bm25_filter"] = bm25_filter_meta
    return merged_results, rag_scores
