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
    if isinstance(model_name, str) and model_name.strip().lower().startswith("gpt-5"):
        return max(resolved, POLICY_CORE_GPT5_MIN_MAX_TOKENS)
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
        if normalized_context:
            compact_input["context"] = normalized_context
        else:
            compact_input.pop("context", None)

    return compact_input


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


def _validate_policy_core_runtime_contract(
    contract: LlmPolicyCoreOutput,
    *,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> str | None:
    referents = contract.referents if isinstance(contract.referents, dict) else {}
    has_booking_ref = _policy_core_has_grounded_referent(referents, "booking_ref")
    has_customer = _policy_core_has_grounded_referent(referents, "customer") or bool(
        contract.slots.get("name")
    )

    if (
        contract.intent in _BOOKING_MANAGE_REFERENCE_INTENTS
        and contract.capability == "booking_manage"
        and contract.subject_kind == "booking"
        and not has_booking_ref
    ):
        expected_reply_type = "time" if has_customer else "name"
        expected_next_question = "datetime" if has_customer else "name"
        if contract.action != "fact":
            return "llm_policy_core_error:booking_manage_reference_action_invalid"
        if contract.tool_action_hint != "calendar.get_booking":
            return "llm_policy_core_error:booking_manage_reference_tool_action_invalid"
        if contract.expected_reply_type != expected_reply_type:
            return "llm_policy_core_error:booking_manage_reference_expected_reply_invalid"
        if contract.next_question != expected_next_question:
            return "llm_policy_core_error:booking_manage_reference_next_question_invalid"
        if expected_next_question not in list(contract.open_questions or []):
            return "llm_policy_core_error:booking_manage_reference_open_questions_invalid"
        if (
            not has_customer
            and any(
                (
                    contract.pending_question_act,
                    contract.pending_question_target,
                    contract.active_question_relation,
                )
            )
        ):
            return "llm_policy_core_error:booking_manage_reference_stale_axes"

    pending_contract = _policy_core_active_pending_contract(normalized_memory_profile)
    carry_reply_type = pending_contract.get("expected_reply_type")
    carry_next_question = pending_contract.get("next_question")
    carry_open_questions = pending_contract.get("open_questions") or []
    if (
        contract.action == "fact"
        and contract.active_question_relation == "generic_info_interrupt"
        and isinstance(carry_reply_type, str)
        and carry_reply_type.strip()
        and isinstance(carry_next_question, str)
        and carry_next_question.strip()
    ):
        expected_open_questions = [
            item
            for item in carry_open_questions
            if isinstance(item, str) and item.strip()
        ] or [carry_next_question]
        if contract.expected_reply_type != carry_reply_type:
            return "llm_policy_core_error:generic_info_interrupt_expected_reply_invalid"
        if contract.next_question != carry_next_question:
            return "llm_policy_core_error:generic_info_interrupt_next_question_invalid"
        if list(contract.open_questions or []) != expected_open_questions:
            return "llm_policy_core_error:generic_info_interrupt_open_questions_invalid"
        expected_pending_act = pending_contract.get("pending_question_act")
        if expected_pending_act and contract.pending_question_act != expected_pending_act:
            return "llm_policy_core_error:generic_info_interrupt_pending_act_invalid"
        expected_pending_target = pending_contract.get("pending_question_target")
        if expected_pending_target and contract.pending_question_target != expected_pending_target:
            return "llm_policy_core_error:generic_info_interrupt_pending_target_invalid"

    return None


def _build_policy_core_contract_repair_instruction(
    *,
    schema_error: str,
    normalized_memory_profile: Mapping[str, Any] | None,
) -> str | None:
    if not isinstance(schema_error, str) or not schema_error.strip():
        return None

    token = schema_error.removeprefix("llm_policy_core_error:")
    pending_contract = _policy_core_active_pending_contract(normalized_memory_profile)
    carry_reply_type = pending_contract.get("expected_reply_type")
    carry_next_question = pending_contract.get("next_question")
    carry_open_questions = pending_contract.get("open_questions") or []

    if token.startswith("booking_manage_reference_"):
        has_customer = False
        if isinstance(pending_contract, dict):
            has_customer = pending_contract.get("expected_reply_type") == "time"
        expected_reply_type = "time" if has_customer else "name"
        expected_next_question = "datetime" if has_customer else "name"
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

    if token.startswith("generic_info_interrupt_"):
        if not isinstance(carry_reply_type, str) or not isinstance(carry_next_question, str):
            return None
        open_questions = [
            item
            for item in carry_open_questions
            if isinstance(item, str) and item.strip()
        ] or [carry_next_question]
        pending_parts: list[str] = [
            "The previous JSON violated the governed generic-info-interrupt follow-up contract.",
            "When `active_question_relation=\"generic_info_interrupt\"` and booking carryover is active,",
            "preserve the active follow-up contract from `memory.profile.pending_question_contract` exactly:",
            f'`expected_reply_type="{carry_reply_type}"`,',
            f'`next_question="{carry_next_question}"`,',
            f"`open_questions={json.dumps(open_questions, ensure_ascii=False)}`.",
        ]
        pending_act = pending_contract.get("pending_question_act")
        if isinstance(pending_act, str) and pending_act.strip():
            pending_parts.append(f'Keep `pending_question_act="{pending_act}"`.')
        pending_target = pending_contract.get("pending_question_target")
        if isinstance(pending_target, str) and pending_target.strip():
            pending_parts.append(f'Keep `pending_question_target="{pending_target}"`.')
        pending_parts.append("Return corrected JSON only.")
        return " ".join(pending_parts)

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

    pending_question_contract = profile.get("pending_question_contract")
    if isinstance(pending_question_contract, dict):
        cleaned_pending: dict[str, Any] = {}
        next_question = pending_question_contract.get("next_question") or pending_question_contract.get("slot")
        if isinstance(next_question, str) and next_question.strip():
            slot_token = next_question.strip().casefold()
            slot_token = {"time": "datetime", "date": "datetime"}.get(slot_token, slot_token)
            if slot_token in allowed_next_questions:
                cleaned_pending["next_question"] = slot_token
        open_questions = pending_question_contract.get("open_questions")
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
        pending_expected_reply_type = pending_question_contract.get("expected_reply_type")
        if (
            isinstance(pending_expected_reply_type, str)
            and pending_expected_reply_type.strip()
        ):
            expected_token = pending_expected_reply_type.strip().casefold()
            if expected_token in allowed_expected_reply_types:
                cleaned_pending["expected_reply_type"] = expected_token
        reason = pending_question_contract.get("reason")
        if isinstance(reason, str) and reason.strip():
            cleaned_pending["reason"] = " ".join(reason.split())[
                :POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS
            ]
        pending_question_act = pending_question_contract.get("pending_question_act")
        if isinstance(pending_question_act, str) and pending_question_act.strip():
            act_token = pending_question_act.strip().casefold()
            if act_token in allowed_pending_question_acts:
                cleaned_pending["pending_question_act"] = act_token
        pending_question_target = pending_question_contract.get("pending_question_target")
        if isinstance(pending_question_target, str) and pending_question_target.strip():
            target_token = pending_question_target.strip().casefold()
            if target_token in allowed_pending_question_targets:
                cleaned_pending["pending_question_target"] = target_token
        active_question_relation = pending_question_contract.get("active_question_relation")
        if isinstance(active_question_relation, str) and active_question_relation.strip():
            relation_token = active_question_relation.strip().casefold()
            if relation_token in allowed_active_question_relations:
                cleaned_pending["active_question_relation"] = relation_token
        value = pending_question_contract.get("value")
        if isinstance(value, str) and value.strip():
            cleaned_pending["value"] = " ".join(value.split())[
                :POLICY_CORE_MEMORY_PROFILE_ITEM_MAX_CHARS
            ]
        if cleaned_pending:
            normalized["pending_question_contract"] = cleaned_pending
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
    for attempt_idx, timeout_seconds in enumerate(timeout_attempts):
        attempt_count = attempt_idx + 1
        timeout_seconds_used = timeout_seconds
        max_tokens_used = _resolve_policy_core_max_tokens_with_cap(
            timeout_seconds,
            max_tokens_override,
            POLICY_CORE_MODEL,
        )
        attempt_uses_compact = use_compact_messages
        if attempt_uses_compact and compact_messages is None:
            compact_input = _build_policy_core_compact_input(policy_input)
            compact_messages = _build_policy_core_messages(prompt, compact_input)
        messages_for_attempt = compact_messages if attempt_uses_compact else messages
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
            compact_messages = _build_policy_core_messages(prompt, compact_input)
        fallback_messages = compact_messages if fallback_use_compact else messages
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
            )
            fallback_model_attempted = True
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
    result["raw"] = content
    if not content:
        result["error"] = "empty_response"
        return result

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
    if tool_args_sanitized:
        result["tool_args_sanitized"] = True
    contract, schema_error = validate_llm_policy_core_output(payload)
    if contract is not None and schema_error is None:
        schema_error = _validate_policy_core_runtime_contract(
            contract,
            normalized_memory_profile=normalized_memory_profile,
        )
    if schema_error:
        repair_instruction = _build_policy_core_contract_repair_instruction(
            schema_error=schema_error,
            normalized_memory_profile=normalized_memory_profile,
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
                        contract, schema_error = validate_llm_policy_core_output(payload)
                        if contract is not None and schema_error is None:
                            schema_error = _validate_policy_core_runtime_contract(
                                contract,
                                normalized_memory_profile=normalized_memory_profile,
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
