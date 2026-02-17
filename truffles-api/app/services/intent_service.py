import json
import math
import os
import re
import time
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Tuple

import httpx

from app.logging_config import get_logger, record_llm_time
from app.schemas.intent import (
    validate_answer_interpreter_output,
    validate_dialogue_controller_output,
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

logger = get_logger("intent_service")


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
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "truffles_knowledge")

RAG_BM25_LIMIT = int(os.environ.get("RAG_BM25_LIMIT", "5"))
RAG_BM25_MAX_DOCS = int(os.environ.get("RAG_BM25_MAX_DOCS", "200"))
RAG_BM25_TIMEOUT_SECONDS = float(os.environ.get("RAG_BM25_TIMEOUT_SECONDS", "0.8"))
RAG_HYBRID_VECTOR_WEIGHT = float(os.environ.get("RAG_HYBRID_VECTOR_WEIGHT", "0.6"))
RAG_HYBRID_BM25_WEIGHT = float(os.environ.get("RAG_HYBRID_BM25_WEIGHT", "0.4"))

CONTROLLER_PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "intent_classifier.md"
CONTROLLER_TIMEOUT_SECONDS = float(os.environ.get("ROUTER_TIMEOUT_SECONDS", "3.0"))
CONTROLLER_MAX_TOKENS = int(os.environ.get("ROUTER_MAX_TOKENS", "140"))
CONTROLLER_CONFIDENCE_THRESHOLD = float(os.environ.get("ROUTER_CONFIDENCE_THRESHOLD", "0.30"))
_DEFAULT_CONTROLLER_MODEL = (
    "gpt-4o-mini" if FAST_MODEL.strip().lower().startswith("gpt-5") else FAST_MODEL
)
CONTROLLER_MODEL = os.environ.get("ROUTER_MODEL", _DEFAULT_CONTROLLER_MODEL).strip()
PLAN_PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "llm_plan.md"
PLAN_TIMEOUT_SECONDS = float(os.environ.get("LLM_PLAN_TIMEOUT_SECONDS", "3.0"))
PLAN_MAX_TOKENS = int(os.environ.get("LLM_PLAN_MAX_TOKENS", "220"))
PLAN_MODEL = os.environ.get("LLM_PLAN_MODEL", CONTROLLER_MODEL).strip()
PLAN_CONFIDENCE_THRESHOLD = float(os.environ.get("LLM_PLAN_CONFIDENCE_THRESHOLD", "0.3"))
POLICY_CORE_PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "llm_policy_core.md"
POLICY_CORE_TIMEOUT_SECONDS = float(
    os.environ.get("LLM_POLICY_CORE_TIMEOUT_SECONDS", "5.0")
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
    float(os.environ.get("LLM_POLICY_CORE_TIMEOUT_RETRY_SECONDS", "2.5")),
    0.1,
)
POLICY_CORE_RETRY_ON_TIMEOUT = os.environ.get("LLM_POLICY_CORE_RETRY_ON_TIMEOUT")
POLICY_CORE_RETRY_ON_TRANSIENT = os.environ.get("LLM_POLICY_CORE_RETRY_ON_TRANSIENT")
POLICY_CORE_MAX_TOKENS = int(os.environ.get("LLM_POLICY_CORE_MAX_TOKENS", "240"))
POLICY_CORE_MODEL = os.environ.get("LLM_POLICY_CORE_MODEL", PLAN_MODEL).strip()
_DEFAULT_POLICY_CORE_TIMEOUT_FALLBACK_MODEL = (
    _DEFAULT_CONTROLLER_MODEL if _DEFAULT_CONTROLLER_MODEL.strip() else FAST_MODEL
)
POLICY_CORE_TIMEOUT_FALLBACK_MODEL = os.environ.get(
    "LLM_POLICY_CORE_TIMEOUT_FALLBACK_MODEL",
    _DEFAULT_POLICY_CORE_TIMEOUT_FALLBACK_MODEL,
).strip()
POLICY_CORE_CONFIDENCE_THRESHOLD = float(
    os.environ.get("LLM_POLICY_CORE_CONFIDENCE_THRESHOLD", "0.3")
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
POLICY_CORE_STRUCTURED_OUTPUT = os.environ.get("LLM_POLICY_CORE_STRUCTURED_OUTPUT")
POLICY_CORE_MICRO_TIMEOUT_SECONDS = max(
    float(os.environ.get("LLM_POLICY_CORE_MICRO_TIMEOUT_SECONDS", "0.8")),
    0.2,
)
POLICY_CORE_MICRO_MIN_REMAINING_MS = max(
    float(os.environ.get("LLM_POLICY_CORE_MICRO_MIN_REMAINING_MS", "350")),
    0.0,
)
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
    if timeout_seconds <= 0:
        return min(POLICY_CORE_MAX_TOKENS, 120)
    if timeout_seconds < 1.4:
        return min(POLICY_CORE_MAX_TOKENS, 120)
    if timeout_seconds < 2.2:
        return min(POLICY_CORE_MAX_TOKENS, 160)
    if timeout_seconds < 3.0:
        return min(POLICY_CORE_MAX_TOKENS, 200)
    return POLICY_CORE_MAX_TOKENS


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


def _build_policy_core_response_format(allowed_tool_actions: list[str]) -> dict[str, Any]:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "intent",
            "action",
            "tool_action",
            "tool_args",
            "pack_refs",
            "slots",
            "open_questions",
            "needs_manager",
            "risk_signals",
            "confidence",
        ],
        "properties": {
            "intent": {"type": "string", "minLength": 1},
            "action": {"type": "string", "enum": ["fact", "collect", "handoff"]},
            "tool_action": {"type": "string", "enum": allowed_tool_actions},
            "tool_args": {"type": "object", "additionalProperties": True},
            "pack_refs": {"type": "array", "items": {"type": "string"}},
            "slots": {
                "type": "object",
                "additionalProperties": {"type": "string"},
            },
            "next_question": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "open_questions": {"type": "array", "items": {"type": "string"}},
            "needs_manager": {"type": "boolean"},
            "risk_signals": {"type": "array", "items": {"type": "string"}},
            "language": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "reason": {"anyOf": [{"type": "string"}, {"type": "null"}]},
            "goal": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        },
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "llm_policy_core_output",
            "strict": True,
            "schema": schema,
        },
    }


def _normalize_policy_core_memory_summary(summary: str | None) -> str | None:
    if not isinstance(summary, str):
        return None
    compact = " ".join(summary.split())
    if not compact:
        return None
    return compact[:POLICY_CORE_MEMORY_SUMMARY_MAX_CHARS]


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
    expected_reply_type = profile.get("expected_reply_type")
    if isinstance(expected_reply_type, str) and expected_reply_type.strip():
        expected_reply_type = expected_reply_type.strip().casefold()
        if expected_reply_type in {"service_choice", "time", "name"}:
            normalized["expected_reply_type"] = expected_reply_type
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
            if slot not in {"service", "datetime", "name"}:
                continue
            if slot in seen_slots:
                continue
            cleaned_slots.append(slot)
            seen_slots.add(slot)
        if cleaned_slots:
            normalized["active_slots"] = cleaned_slots
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
    return normalized or None


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
CONTROLLER_PROMPT_FALLBACK = """# Dialogue Controller Prompt (pack-ref-only)

Ты Dialogue Controller для сервисного бизнеса. Вход всегда JSON. Верни ТОЛЬКО JSON.
Не придумывай факты о бизнесе и не используй внешний контекст: только текст клиента и входные поля.
service_query должен быть словом/фразой только из сообщения клиента (1-6 слов), иначе пустая строка.

Вход (JSON):
```json
{"task":"controller","message":"...","carryover":{"class":"...","intents":["..."],"info_sections":["..."],"ttl_remaining":0},"expected_reply_type":"..."}
```

или
```json
{"task":"answer_interpreter","message":"...","expected_reply_type":"service_choice|time|name","carryover":{"class":"...","intents":["..."],"info_sections":["..."],"ttl_remaining":0},"question_context":{"prompt_hint":"..."}}
```

Режимы:

1) task="controller" (или task отсутствует) → строго такой вид:
```json
{"class":"...","goal":"...","intents":["..."],"slots":{"service_query":""},"followups":[],"safety_flags":[],"confidence":0.0,"reason":"...","carryover":{}}
```

2) task="answer_interpreter" → строго такой вид:
```json
{"slot":"service|datetime|name","value":"...","confidence":0.0,"reason":"..."}
```

## CLASS (одно значение)
- booking — запись/перенос/отмена/окошко/время записи.
- info_bundle — адрес/как добраться/график/время работы/парковка/гости/ранний приход/цены/длительность.
- consult — совет/подбор/рекомендации по услугам без цены/адреса/записи.
- greeting — привет/спасибо/ок.
- out_of_domain — не по теме (погода, код, рецепты).
- other — остальное/неуверенность.

## GOAL (одно значение)
- booking, info, consult, greeting, out_of_domain, other — выбери наиболее точную цель диалога.

## INTENTS (список)
Разрешённые: booking, pricing, duration, location, hours, consult, greeting, out_of_domain, other.
- Для info_bundle перечисляй info-интенты из текста (pricing/duration/location/hours).
- Для booking/consult/greeting/out_of_domain ставь одноимённый интент.
- Если не уверен — other.

## SLOTS
- service_query: 1–6 слов, только из текста клиента, если услуга названа явно. Иначе пустая строка.

## FOLLOWUPS
- Список коротких подсказок (строки), что спросить дальше. Пустой список, если не нужно.

## SAFETY_FLAGS
- Список коротких меток рисков (например, "payment", "medical", "complaint") если они видны. Иначе пусто.

## CONFIDENCE
- 0.0–1.0. Если сомневаешься — 0.0.

## REASON
- Короткая причина (1–6 слов).

## ANSWER INTERPRETER (task="answer_interpreter")
- slot: service|datetime|name. expected_reply_type: service_choice→service, time→datetime, name→name.
- value: краткий ответ из сообщения клиента (для service 1–6 слов). Если ответа нет — пустая строка.
- confidence: 0.0–1.0. Если сомневаешься — 0.0.
"""

PLAN_PROMPT_FALLBACK = """# Hybrid LLM Plan Prompt
Return JSON only (no markdown). Required fields: outcome, tool_action, confidence.
Optional fields: tool_args, pack_refs, language, reason, goal, slot_state, open_questions.
Use tool_action and pack_refs only from the allowed lists provided in the input.
slot_state and open_questions may only use: service, datetime, name.
For info pricing/duration, include tool_args.service_query (or slot_state.service).
If missing required args, set outcome=collect and list open_questions accordingly.
"""
POLICY_CORE_PROMPT_FALLBACK = """# LLM Policy Core Prompt
Return JSON only (no markdown). Required fields: intent, action, tool_action, slots, confidence.
Optional fields: tool_args, pack_refs, slots, next_question, open_questions, needs_manager,
risk_signals, language, reason, goal.
Use tool_action and pack_refs only from the allowed lists provided in the input.
slots/open_questions/next_question may only use: service, datetime, name.
"""

_CONTROLLER_PROMPT_CACHE: str | None = None
_PLAN_PROMPT_CACHE: str | None = None
_POLICY_CORE_PROMPT_CACHE: str | None = None


def _is_env_enabled(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _load_controller_prompt() -> str:
    global _CONTROLLER_PROMPT_CACHE
    if _CONTROLLER_PROMPT_CACHE is not None:
        return _CONTROLLER_PROMPT_CACHE
    try:
        _CONTROLLER_PROMPT_CACHE = CONTROLLER_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except Exception as exc:
        logger.warning(f"Dialogue controller prompt load failed: {exc}")
        _CONTROLLER_PROMPT_CACHE = ""
    if not _CONTROLLER_PROMPT_CACHE:
        logger.warning("Dialogue controller prompt fallback in use")
        _CONTROLLER_PROMPT_CACHE = CONTROLLER_PROMPT_FALLBACK.strip()
    return _CONTROLLER_PROMPT_CACHE


def _load_plan_prompt() -> str:
    global _PLAN_PROMPT_CACHE
    if _PLAN_PROMPT_CACHE is not None:
        return _PLAN_PROMPT_CACHE
    try:
        _PLAN_PROMPT_CACHE = PLAN_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except Exception as exc:
        logger.warning(f"LLM plan prompt load failed: {exc}")
        _PLAN_PROMPT_CACHE = ""
    if not _PLAN_PROMPT_CACHE:
        logger.warning("LLM plan prompt fallback in use")
        _PLAN_PROMPT_CACHE = PLAN_PROMPT_FALLBACK.strip()
    return _PLAN_PROMPT_CACHE


def _load_policy_core_prompt() -> str:
    global _POLICY_CORE_PROMPT_CACHE
    if _POLICY_CORE_PROMPT_CACHE is not None:
        return _POLICY_CORE_PROMPT_CACHE
    try:
        _POLICY_CORE_PROMPT_CACHE = POLICY_CORE_PROMPT_PATH.read_text(
            encoding="utf-8"
        ).strip()
    except Exception as exc:
        logger.warning(f"LLM policy core prompt load failed: {exc}")
        _POLICY_CORE_PROMPT_CACHE = ""
    if not _POLICY_CORE_PROMPT_CACHE:
        logger.warning("LLM policy core prompt fallback in use")
        _POLICY_CORE_PROMPT_CACHE = POLICY_CORE_PROMPT_FALLBACK.strip()
    return _POLICY_CORE_PROMPT_CACHE


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
    result: dict[str, Any] = {"ok": False, "payload": None, "error": None, "raw": None}
    carryover_input = _build_controller_carryover(carryover)
    normalized = (message or "").strip()
    controller_retry = False
    total_elapsed_ms = 0.0

    def _build_payload(
        *,
        controller_class: str | None = None,
        goal: str | None = None,
        intents: list[str] | None = None,
        slots: dict | None = None,
        followups: list[str] | None = None,
        safety_flags: list[str] | None = None,
        confidence: float = 0.0,
        reason: str = "",
        carryover_payload: dict | None = None,
        controller_llm_ms: float | None = None,
        controller_error: str = "none",
        controller_retry_flag: bool | None = None,
    ) -> dict:
        payload = {
            "class": controller_class,
            "goal": goal,
            "intents": list(intents or []),
            "slots": dict(slots or {}),
            "followups": list(followups or []),
            "safety_flags": list(safety_flags or []),
            "confidence": float(confidence or 0.0),
            "reason": str(reason or ""),
            "carryover": dict(carryover_payload or carryover_input),
            "controller_llm_ms": round(controller_llm_ms or 0.0, 2),
            "controller_error": controller_error,
            "controller_retry": bool(
                controller_retry_flag if controller_retry_flag is not None else controller_retry
            ),
        }
        return payload

    if not _current_openai_api_key():
        result["error"] = "no_api_key"
        result["payload"] = _build_payload(
            controller_class=OFFLINE_CONTROLLER_CLASS,
            goal=OFFLINE_CONTROLLER_GOAL,
            intents=[],
            slots={},
            followups=[],
            safety_flags=[],
            confidence=0.0,
            reason="offline_no_api_key",
            carryover_payload=carryover_input,
            controller_llm_ms=0.0,
            controller_error="no_api_key",
            controller_retry_flag=False,
        )
        return result

    if not normalized:
        result["error"] = "empty_message"
        result["payload"] = _build_payload(controller_error="empty_message")
        return result
    prompt = _load_controller_prompt()
    if not prompt:
        result["error"] = "prompt_missing"
        result["payload"] = _build_payload(controller_error="prompt_missing")
        return result
    if not _should_attempt_llm(
        timing_context,
        timeout_seconds=CONTROLLER_TIMEOUT_SECONDS,
        stage="controller_llm",
    ):
        result["error"] = "deadline_exceeded"
        result["payload"] = _build_payload(
            controller_error="deadline_exceeded",
            controller_llm_ms=0.0,
            reason="deadline_exceeded",
            controller_retry_flag=False,
        )
        return result

    controller_input = {
        "task": "controller",
        "message": message,
        "carryover": carryover_input,
    }
    if isinstance(expected_reply_type, str) and expected_reply_type.strip():
        controller_input["expected_reply_type"] = expected_reply_type.strip()

    budget_meta = consume_llm_budget(
        client_slug=client_slug or "unknown",
        client_config=client_config,
        scope="router",
    )
    _append_llm_budget_event(timing_context, budget_meta)
    if not budget_meta.get("allowed", True):
        result["error"] = "budget_exceeded"
        result["payload"] = _build_payload(
            controller_error="budget_exceeded",
            controller_llm_ms=0.0,
            controller_retry_flag=False,
        )
        return result

    try:
        llm = get_llm_provider()
    except RuntimeError as exc:
        if "OPENAI_API_KEY missing" in str(exc):
            logger.info("Controller skipped: OPENAI_API_KEY missing")
            result["error"] = "no_api_key"
            return result
        logger.warning(f"Controller provider init failed: {exc}")
        result["error"] = _classify_llm_error(exc)
        return result
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(controller_input, ensure_ascii=False)},
    ]
    model_name = CONTROLLER_MODEL.strip().lower()
    temperature = 0.0
    temperature_override: float | None = temperature
    if model_name.startswith("gpt-5"):
        temperature_override = 1.0
    def _call_controller_llm(
        max_tokens: int,
        *,
        temperature_override: float | None,
    ) -> tuple[Any | None, float, str | None]:
        llm_start = time.monotonic()
        try:
            kwargs = {
                "messages": messages,
                "max_tokens": max_tokens,
                "model": CONTROLLER_MODEL,
                "timeout_seconds": CONTROLLER_TIMEOUT_SECONDS,
            }
            if temperature_override is not None:
                kwargs["temperature"] = temperature_override
            response = llm.generate(**kwargs)
        except httpx.TimeoutException as exc:
            elapsed_ms = round((time.monotonic() - llm_start) * 1000, 2)
            _log_timing(
                "controller_llm_ms",
                elapsed_ms,
                timing_context=timing_context,
                extra={
                    "model_name": CONTROLLER_MODEL,
                    "model_tier": "fast",
                    "timeout": True,
                    "timeout_seconds": CONTROLLER_TIMEOUT_SECONDS,
                    "max_tokens": max_tokens,
                    "temperature": temperature_override,
                },
            )
            record_llm_time(client_slug, "controller_llm_ms", elapsed_ms)
            logger.warning(f"Dialogue controller LLM timeout after {CONTROLLER_TIMEOUT_SECONDS}s: {exc}")
            return None, elapsed_ms, "timeout"
        except Exception as exc:
            elapsed_ms = round((time.monotonic() - llm_start) * 1000, 2)
            error_text = str(exc)
            error_code = "error"
            if "temperature" in error_text and "unsupported" in error_text:
                error_code = "unsupported_temperature"
            _log_timing(
                "controller_llm_ms",
                elapsed_ms,
                timing_context=timing_context,
                extra={
                    "model_name": CONTROLLER_MODEL,
                    "model_tier": "fast",
                    "timeout": False,
                    "error": error_text,
                    "max_tokens": max_tokens,
                    "temperature": temperature_override,
                },
            )
            record_llm_time(client_slug, "controller_llm_ms", elapsed_ms)
            logger.warning(f"Dialogue controller LLM failed: {exc}")
            return None, elapsed_ms, error_code

        elapsed_ms = round((time.monotonic() - llm_start) * 1000, 2)
        _log_timing(
            "controller_llm_ms",
            elapsed_ms,
            timing_context=timing_context,
            extra={
                "model_name": CONTROLLER_MODEL,
                "model_tier": "fast",
                "timeout": False,
                "max_tokens": max_tokens,
                "temperature": temperature_override,
            },
        )
        record_llm_time(client_slug, "controller_llm_ms", elapsed_ms)
        return response, elapsed_ms, None

    response, elapsed_ms, error = _call_controller_llm(
        CONTROLLER_MAX_TOKENS, temperature_override=temperature_override
    )
    total_elapsed_ms += elapsed_ms
    if error == "unsupported_temperature":
        controller_retry = True
        temperature_override = 1.0
        response, elapsed_ms, error = _call_controller_llm(
            CONTROLLER_MAX_TOKENS, temperature_override=temperature_override
        )
        total_elapsed_ms += elapsed_ms
    if error == "timeout":
        controller_retry = True
        retry_tokens = _controller_retry_max_tokens(CONTROLLER_MAX_TOKENS)
        response, elapsed_ms, error = _call_controller_llm(
            retry_tokens, temperature_override=temperature_override
        )
        total_elapsed_ms += elapsed_ms
    if error is not None:
        result["error"] = error
        result["payload"] = _build_payload(
            controller_error=error,
            controller_llm_ms=total_elapsed_ms,
            controller_retry_flag=controller_retry,
        )
        return result

    content = (response.content or "").strip()
    result["raw"] = content
    if not content:
        result["error"] = "empty_response"
        result["payload"] = _build_payload(
            controller_error="empty_response",
            controller_llm_ms=total_elapsed_ms,
            controller_retry_flag=controller_retry,
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
        result["payload"] = _build_payload(
            controller_error="invalid_json",
            controller_llm_ms=total_elapsed_ms,
            controller_retry_flag=controller_retry,
        )
        return result
    contract, schema_error = validate_dialogue_controller_output(payload)
    if schema_error:
        result["error"] = "invalid_schema"
        result["payload"] = _build_payload(
            controller_error="invalid_schema",
            controller_llm_ms=total_elapsed_ms,
            controller_retry_flag=controller_retry,
        )
        return result
    payload = contract.model_dump(by_alias=True)

    controller_class = _clean_controller_class(payload.get("class"))
    goal = _clean_controller_goal(payload.get("goal"))
    if not controller_class:
        result["error"] = "invalid_class"
        result["payload"] = _build_payload(
            controller_error="invalid_class",
            controller_llm_ms=total_elapsed_ms,
            controller_retry_flag=controller_retry,
        )
        return result

    intents = _clean_controller_intents(payload.get("intents"))
    confidence = payload.get("confidence")
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(confidence, 1.0))
    reason = payload.get("reason")
    if not isinstance(reason, str):
        reason = ""

    slots = payload.get("slots")
    if not isinstance(slots, dict):
        slots = {}
    slots = dict(slots)
    slots["service_query"] = _clean_controller_service_query(slots.get("service_query"))
    followups = _clean_controller_followups(payload.get("followups"))
    safety_flags = _clean_controller_safety_flags(payload.get("safety_flags"))

    carryover_payload = payload.get("carryover")
    if not isinstance(carryover_payload, dict):
        carryover_payload = {}
    if not carryover_payload and controller_input.get("carryover"):
        carryover_payload = controller_input["carryover"]

    result["ok"] = True
    result["payload"] = _build_payload(
        controller_class=controller_class,
        goal=goal,
        intents=intents,
        slots=slots,
        followups=followups,
        safety_flags=safety_flags,
        confidence=confidence,
        reason=reason,
        carryover_payload=carryover_payload,
        controller_llm_ms=total_elapsed_ms,
        controller_error="none",
        controller_retry_flag=controller_retry,
    )
    return result


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
) -> dict:
    result: dict[str, Any] = {
        "ok": False,
        "payload": None,
        "error": None,
        "raw": None,
        "attempted": False,
        "elapsed_ms": 0.0,
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

    allowed_tool_actions = [
        "info",
        "consult",
        "booking",
        "handoff",
        "collect",
        "calendar.list_slots",
        "calendar.book_slot",
        "calendar.get_booking",
        "calendar.reschedule",
        "calendar.cancel",
        "catalog.service_query",
        "catalog.location",
        "catalog.portfolio",
    ]
    policy_input: dict[str, Any] = {
        "task": "llm_policy_core",
        "message": message,
        "expected_reply_type": expected_reply_type,
        "current_goal": current_goal,
        "slot_state": slot_state or {},
        "allowed": {
            "tool_actions": list(allowed_tool_actions),
            "info_refs": list(info_refs or []),
            "consult_refs": list(consult_refs or []),
        },
    }
    normalized_memory_summary = _normalize_policy_core_memory_summary(memory_summary)
    normalized_memory_profile = _normalize_policy_core_memory_profile(memory_profile)
    if normalized_memory_summary or normalized_memory_profile:
        policy_input["memory"] = {}
        if normalized_memory_summary:
            policy_input["memory"]["summary"] = normalized_memory_summary
        if normalized_memory_profile:
            policy_input["memory"]["profile"] = normalized_memory_profile

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
    temperature = 0.0
    model_name = POLICY_CORE_MODEL.strip().lower()
    if model_name.startswith("gpt-5"):
        temperature = 1.0

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(policy_input, ensure_ascii=False)},
    ]
    structured_output_enabled = _policy_core_structured_output_enabled()
    policy_response_format = (
        _build_policy_core_response_format(allowed_tool_actions)
        if structured_output_enabled
        else None
    )
    retry_on_timeout = _is_env_enabled(POLICY_CORE_RETRY_ON_TIMEOUT, default=True)
    retry_on_transient = _is_env_enabled(POLICY_CORE_RETRY_ON_TRANSIENT, default=True)
    if micro_deadline_mode:
        retry_on_timeout = False
        retry_on_transient = False
    timeout_attempts = [policy_timeout_seconds]
    if retry_on_timeout:
        retry_timeout = min(POLICY_CORE_RETRY_TIMEOUT_SECONDS, policy_timeout_seconds)
        if retry_timeout > 0 and retry_timeout not in timeout_attempts:
            timeout_attempts.append(retry_timeout)
    if retry_on_transient and len(timeout_attempts) == 1:
        timeout_attempts.append(timeout_attempts[0])
    fallback_model = POLICY_CORE_TIMEOUT_FALLBACK_MODEL.strip()
    if fallback_model.casefold() == POLICY_CORE_MODEL.strip().casefold():
        fallback_model = ""

    llm_start = time.monotonic()
    response = None
    error = None
    attempt_count = 0
    model_name_used = POLICY_CORE_MODEL
    fallback_model_attempted = False
    timeout_seconds_used = policy_timeout_seconds
    max_tokens_used = _resolve_policy_core_max_tokens(policy_timeout_seconds)
    transient_retry_used = False
    structured_output_fallback_used = False
    for attempt_idx, timeout_seconds in enumerate(timeout_attempts):
        attempt_count = attempt_idx + 1
        timeout_seconds_used = timeout_seconds
        max_tokens_used = _resolve_policy_core_max_tokens(timeout_seconds)
        if attempt_idx > 0 and not _should_attempt_llm(
            timing_context,
            timeout_seconds=timeout_seconds,
            stage="policy_core_llm_retry",
        ):
            error = "deadline_exceeded"
            break
        try:
            response = llm.generate(
                messages=messages,
                max_tokens=max_tokens_used,
                model=POLICY_CORE_MODEL,
                timeout_seconds=timeout_seconds,
                temperature=temperature,
                response_format=policy_response_format,
            )
            model_name_used = POLICY_CORE_MODEL
            error = None
            break
        except httpx.TimeoutException:
            error = "timeout"
            if not retry_on_timeout:
                break
            if attempt_idx + 1 < len(timeout_attempts):
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
                    response = llm.generate(
                        messages=messages,
                        max_tokens=max_tokens_used,
                        model=POLICY_CORE_MODEL,
                        timeout_seconds=timeout_seconds,
                        temperature=temperature,
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
        fallback_timeout_seconds = min(POLICY_CORE_RETRY_TIMEOUT_SECONDS, policy_timeout_seconds)
        if _should_attempt_llm(
            timing_context,
            timeout_seconds=fallback_timeout_seconds,
            stage="policy_core_llm_fallback",
        ):
            attempt_count += 1
            timeout_seconds_used = fallback_timeout_seconds
            max_tokens_used = _resolve_policy_core_max_tokens(fallback_timeout_seconds)
            fallback_model_attempted = True
            try:
                response = llm.generate(
                    messages=messages,
                    max_tokens=max_tokens_used,
                    model=fallback_model,
                    timeout_seconds=fallback_timeout_seconds,
                    temperature=temperature,
                    response_format=policy_response_format,
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
                        response = llm.generate(
                            messages=messages,
                            max_tokens=max_tokens_used,
                            model=fallback_model,
                            timeout_seconds=fallback_timeout_seconds,
                            temperature=temperature,
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
            "timeout_budgeted": policy_timeout_seconds,
            "temperature": temperature,
            "micro_deadline_mode": micro_deadline_mode,
            "structured_output_enabled": structured_output_enabled,
            "structured_output_fallback_used": structured_output_fallback_used,
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

    contract, schema_error = validate_llm_policy_core_output(payload)
    if schema_error:
        result["error"] = "invalid_schema"
        return result

    result["ok"] = True
    result["payload"] = contract.model_dump()
    return result


def interpret_expected_reply(
    message: str,
    *,
    expected_reply_type: str | None,
    carryover: dict | None = None,
    question_context: dict | None = None,
    client_slug: str | None = None,
) -> dict:
    result: dict[str, Any] = {"ok": False, "payload": None, "error": None, "raw": None}
    expected_reply_type_cleaned = (
        expected_reply_type.strip().lower()
        if isinstance(expected_reply_type, str)
        else None
    )
    expected_slot = ANSWER_INTERPRETER_SLOT_BY_REPLY_TYPE.get(
        expected_reply_type_cleaned or ""
    )
    payload = {
        "slot": expected_slot or "",
        "value": "",
        "confidence": 0.0,
        "reason": "",
    }
    result["payload"] = payload

    normalized = (message or "").strip()
    if not normalized:
        result["error"] = "empty_message"
        return result
    if not expected_slot:
        result["error"] = "unsupported_expected_reply_type"
        return result
    prompt = _load_controller_prompt()
    if not prompt:
        result["error"] = "prompt_missing"
        return result

    carryover_input = _build_controller_carryover(carryover)
    interpreter_input = {
        "task": "answer_interpreter",
        "message": message,
        "expected_reply_type": expected_reply_type_cleaned,
        "carryover": carryover_input,
        "question_context": question_context if isinstance(question_context, dict) else {},
    }
    try:
        llm = get_llm_provider()
    except RuntimeError as exc:
        if "OPENAI_API_KEY missing" in str(exc):
            logger.info("Answer interpreter skipped: OPENAI_API_KEY missing")
            result["error"] = "no_api_key"
            return result
        logger.warning(f"Answer interpreter provider init failed: {exc}")
        result["error"] = _classify_llm_error(exc)
        return result
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(interpreter_input, ensure_ascii=False)},
    ]
    model_name = ANSWER_INTERPRETER_MODEL.strip()
    temperature = 1.0 if model_name.lower().startswith("gpt-5") else 0.0
    llm_start = time.monotonic()
    try:
        response = llm.generate(
            messages,
            temperature=temperature,
            max_tokens=ANSWER_INTERPRETER_MAX_TOKENS,
            model=ANSWER_INTERPRETER_MODEL,
            timeout_seconds=ANSWER_INTERPRETER_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as exc:
        elapsed_ms = round((time.monotonic() - llm_start) * 1000, 2)
        logger.info(
            "Timing",
            extra={
                "context": {
                    "stage": "answer_interpreter_llm_ms",
                    "elapsed_ms": elapsed_ms,
                    "model_name": ANSWER_INTERPRETER_MODEL,
                    "model_tier": "fast",
                    "timeout": True,
                    "timeout_seconds": ANSWER_INTERPRETER_TIMEOUT_SECONDS,
                    "max_tokens": ANSWER_INTERPRETER_MAX_TOKENS,
                    "temperature": temperature,
                }
            },
        )
        record_llm_time(client_slug, "answer_interpreter_llm_ms", elapsed_ms)
        logger.warning(
            f"Answer interpreter timeout after {ANSWER_INTERPRETER_TIMEOUT_SECONDS}s: {exc}"
        )
        result["error"] = "timeout"
        return result
    except Exception as exc:
        elapsed_ms = round((time.monotonic() - llm_start) * 1000, 2)
        logger.info(
            "Timing",
            extra={
                "context": {
                    "stage": "answer_interpreter_llm_ms",
                    "elapsed_ms": elapsed_ms,
                    "model_name": ANSWER_INTERPRETER_MODEL,
                    "model_tier": "fast",
                    "timeout": False,
                    "error": str(exc),
                    "max_tokens": ANSWER_INTERPRETER_MAX_TOKENS,
                    "temperature": temperature,
                }
            },
        )
        record_llm_time(client_slug, "answer_interpreter_llm_ms", elapsed_ms)
        logger.warning(f"Answer interpreter failed: {exc}")
        result["error"] = _classify_llm_error(exc)
        return result

    elapsed_ms = round((time.monotonic() - llm_start) * 1000, 2)
    logger.info(
        "Timing",
        extra={
            "context": {
                "stage": "answer_interpreter_llm_ms",
                "elapsed_ms": elapsed_ms,
                "model_name": ANSWER_INTERPRETER_MODEL,
                "model_tier": "fast",
                "timeout": False,
                "max_tokens": ANSWER_INTERPRETER_MAX_TOKENS,
                "temperature": temperature,
            }
        },
    )
    record_llm_time(client_slug, "answer_interpreter_llm_ms", elapsed_ms)

    content = (response.content or "").strip()
    result["raw"] = content
    if not content:
        result["error"] = "empty_response"
        return result

    parsed = None
    try:
        parsed = json.loads(content)
    except Exception:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except Exception:
                parsed = None
    if not isinstance(parsed, dict):
        result["error"] = "invalid_json"
        return result
    contract, schema_error = validate_answer_interpreter_output(parsed)
    if schema_error:
        result["error"] = "invalid_schema"
        return result
    parsed = contract.model_dump()

    slot = _clean_answer_slot(parsed.get("slot")) or expected_slot
    error = None
    if slot != expected_slot:
        error = "slot_mismatch"
        slot = expected_slot
    value = _clean_answer_value(parsed.get("value"), slot=slot)
    if not value:
        error = error or "empty_value"
    confidence = parsed.get("confidence")
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(confidence, 1.0))
    if error:
        confidence = 0.0
    reason = parsed.get("reason")
    if not isinstance(reason, str):
        reason = ""

    result["payload"] = {
        "slot": slot,
        "value": value,
        "confidence": confidence,
        "reason": reason,
    }
    result["error"] = error
    result["ok"] = error is None
    return result


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

    bm25_max_norm = 1.0 if bm25_max > 0 else 0.0
    rag_scores = {
        "vector_max": vector_max,
        "bm25_max": bm25_max,
        "bm25_max_norm": bm25_max_norm,
        "hybrid_max": merged_results[0]["hybrid_score"] if merged_results else 0.0,
        "vector_count": len(vector_results or []),
        "bm25_count": len(bm25_results),
        "vector_weight": vector_weight,
        "bm25_weight": bm25_weight,
        "bm25_enabled": bm25_enabled,
    }
    if isinstance(bm25_filter_meta, dict):
        rag_scores["bm25_filter"] = bm25_filter_meta
    return merged_results, rag_scores
